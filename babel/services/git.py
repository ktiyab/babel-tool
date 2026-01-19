"""
Git Integration — Auto-capture commits (P-FRICTION: zero friction)

Hooks into Git workflow to capture commits automatically.
Extraction happens async to avoid blocking commits.

Enhanced with:
- Structural change detection (add/modify/delete/rename)
- Language-aware comment diff extraction
- Deduplication via diff_id
"""

import subprocess
import os
import re
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Set
from dataclasses import dataclass, field


# Language-specific comment patterns
# We check added lines (+) against these patterns
COMMENT_MARKERS: Dict[str, List[str]] = {
    '.py': ['#', '"""', "'''"],
    '.js': ['//', '/*', '*'],
    '.ts': ['//', '/*', '*'],
    '.jsx': ['//', '/*', '*'],
    '.tsx': ['//', '/*', '*'],
    '.java': ['//', '/*', '*'],
    '.go': ['//', '/*', '*'],
    '.rs': ['//', '/*', '*', '///', '//!'],
    '.rb': ['#'],
    '.sh': ['#'],
    '.yaml': ['#'],
    '.yml': ['#'],
}

# Supported extensions for comment extraction
SUPPORTED_EXTENSIONS: Set[str] = set(COMMENT_MARKERS.keys())


@dataclass
class FileChange:
    """Represents a single file change in a commit."""
    path: str
    status: str  # A=added, M=modified, D=deleted, R=renamed
    old_path: Optional[str] = None  # For renames


@dataclass
class StructuralChanges:
    """Structural changes in a commit (no content, just metadata)."""
    added: List[str] = field(default_factory=list)
    modified: List[str] = field(default_factory=list)
    deleted: List[str] = field(default_factory=list)
    renamed: List[Tuple[str, str]] = field(default_factory=list)  # (old, new)

    def to_dict(self) -> Dict:
        return {
            'added': self.added,
            'modified': self.modified,
            'deleted': self.deleted,
            'renamed': [{'from': old, 'to': new} for old, new in self.renamed]
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'StructuralChanges':
        renamed = [(r['from'], r['to']) for r in data.get('renamed', [])]
        return cls(
            added=data.get('added', []),
            modified=data.get('modified', []),
            deleted=data.get('deleted', []),
            renamed=renamed
        )

    @property
    def summary(self) -> str:
        """Human-readable summary."""
        parts = []
        if self.added:
            parts.append(f"+{len(self.added)} added")
        if self.modified:
            parts.append(f"~{len(self.modified)} modified")
        if self.deleted:
            parts.append(f"-{len(self.deleted)} deleted")
        if self.renamed:
            parts.append(f">{len(self.renamed)} renamed")
        return ", ".join(parts) if parts else "no changes"

    @property
    def total_files(self) -> int:
        return len(self.added) + len(self.modified) + len(self.deleted) + len(self.renamed)


@dataclass
class CommitInfo:
    """Information about a git commit."""
    hash: str
    message: str
    body: str
    author: str
    email: str
    files: List[str]
    # Enhanced fields
    structural: Optional[StructuralChanges] = None
    comment_diff: Optional[str] = None

    @property
    def diff_id(self) -> str:
        """Unique identifier for deduplication."""
        return self.hash


# Post-commit hook script
POST_COMMIT_HOOK = '''#!/bin/sh
# Babel hook - captures commits automatically
# Installed by: babel hooks install

# Run async to avoid blocking
babel capture-commit --async 2>/dev/null &
'''

# Pre-commit hook for future use (optional rationale prompt)
PRE_COMMIT_HOOK_OPTIONAL = '''#!/bin/sh
# Babel hook - optional rationale capture
# Uncomment to enable rationale prompts before commit

# echo "Why this change? (optional, enter to skip)"
# read rationale
# if [ -n "$rationale" ]; then
#     echo "$rationale" >> .git/COMMIT_RATIONALE
# fi
'''


class GitIntegration:
    """Git repository integration."""

    def __init__(self, repo_path: Optional[Path] = None):
        """
        Initialize git integration.

        Args:
            repo_path: Path to git repository. If None, uses current directory.
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.git_dir = self.repo_path / ".git"
        self.hooks_dir = self.git_dir / "hooks"

    @property
    def is_git_repo(self) -> bool:
        """Check if current directory is a git repository."""
        return self.git_dir.exists() and self.git_dir.is_dir()

    def _run_git(self, args: List[str], check: bool = True) -> Optional[str]:
        """Run a git command and return stdout."""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=check
            )
            return result.stdout
        except subprocess.CalledProcessError:
            return None
        except Exception:
            return None

    def get_structural_changes(self, commit_hash: str = "HEAD") -> Optional[StructuralChanges]:
        """
        Extract structural changes (file status) from a commit.
        
        Returns metadata only, no content.
        Handles initial commits (no parent) specially.
        """
        if not self.is_git_repo:
            return None

        # First try normal diff-tree
        output = self._run_git([
            "diff-tree", "--no-commit-id", "-r", "--name-status", "-M", commit_hash
        ])

        # If empty, might be initial commit - try with --root flag
        if output is not None and not output.strip():
            output = self._run_git([
                "diff-tree", "--no-commit-id", "-r", "--name-status", "--root", commit_hash
            ])

        if output is None:
            return None

        changes = StructuralChanges()

        for line in output.strip().split('\n'):
            if not line:
                continue

            parts = line.split('\t')
            status = parts[0]

            if status == 'A':
                changes.added.append(parts[1])
            elif status == 'M':
                changes.modified.append(parts[1])
            elif status == 'D':
                changes.deleted.append(parts[1])
            elif status.startswith('R'):
                # Rename: R100 old_path new_path
                if len(parts) >= 3:
                    changes.renamed.append((parts[1], parts[2]))

        return changes

    def get_commit_diff(self, commit_hash: str = "HEAD") -> Optional[str]:
        """Get the full diff for a commit."""
        if not self.is_git_repo:
            return None

        return self._run_git(["show", "--format=", commit_hash])

    def extract_comment_diff(self, commit_hash: str = "HEAD", max_length: int = 8000) -> Optional[str]:
        """
        Extract only added comment lines from supported file types.
        
        Args:
            commit_hash: Commit to analyze
            max_length: Maximum characters to return (prevents bloat)
            
        Returns:
            Extracted comments or None if no comments found
        """
        if not self.is_git_repo:
            return None

        # Get diff with file names
        diff_output = self._run_git([
            "show", "--format=", "--unified=0", commit_hash
        ])

        if not diff_output:
            return None

        comments = []
        current_file = None
        current_extension = None

        for line in diff_output.split('\n'):
            # Track current file
            if line.startswith('diff --git'):
                # Extract filename: diff --git a/path/file.py b/path/file.py
                match = re.search(r'b/(.+)$', line)
                if match:
                    current_file = match.group(1)
                    current_extension = Path(current_file).suffix.lower()
                continue

            # Only process supported file types
            if current_extension not in SUPPORTED_EXTENSIONS:
                continue

            # Only process added lines (not removed or context)
            if not line.startswith('+') or line.startswith('+++'):
                continue

            # Extract the actual content (remove leading +)
            content = line[1:].strip()
            
            if self._is_comment(content, current_extension):
                # Include file context for first comment from each file
                file_tag = f"[{current_file}] " if current_file else ""
                comments.append(f"{file_tag}{content}")

        if not comments:
            return None

        # Deduplicate while preserving order
        seen = set()
        unique_comments = []
        for c in comments:
            if c not in seen:
                seen.add(c)
                unique_comments.append(c)

        result = '\n'.join(unique_comments)

        # Truncate if too long
        if len(result) > max_length:
            result = result[:max_length] + "\n... (truncated)"

        return result

    def _is_comment(self, line: str, extension: str) -> bool:
        """Check if a line is a comment for the given file type."""
        if not line:
            return False

        markers = COMMENT_MARKERS.get(extension, [])
        return any(line.startswith(marker) for marker in markers)

    def get_last_commit(self, include_diff: bool = True) -> Optional[CommitInfo]:
        """
        Get information about the last commit.
        
        Args:
            include_diff: If True, includes structural changes and comment diff
        """
        return self.get_commit("HEAD", include_diff)

    def get_commit(self, commit_hash: str, include_diff: bool = True) -> Optional[CommitInfo]:
        """
        Get information about a specific commit.
        
        Args:
            commit_hash: Commit hash or reference
            include_diff: If True, includes structural changes and comment diff
        """
        if not self.is_git_repo:
            return None

        try:
            # Get basic commit info
            result = self._run_git([
                "log", "-1", "--format=%H|%s|%b|%an|%ae", commit_hash
            ])

            if result is None:
                return None

            parts = result.strip().split("|", 4)
            if len(parts) < 5:
                parts.extend([""] * (5 - len(parts)))

            commit_hash_full, message, body, author, email = parts

            # Get changed files (simple list)
            # Try normal diff-tree first, then with --root for initial commits
            files_output = self._run_git([
                "diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash
            ])
            
            if files_output is not None and not files_output.strip():
                # Might be initial commit
                files_output = self._run_git([
                    "diff-tree", "--no-commit-id", "--name-only", "-r", "--root", commit_hash
                ])

            files = [f for f in (files_output or "").strip().split("\n") if f]

            # Build base commit info
            commit = CommitInfo(
                hash=commit_hash_full,
                message=message,
                body=body,
                author=author,
                email=email,
                files=files
            )

            # Optionally include enhanced diff info
            if include_diff:
                commit.structural = self.get_structural_changes(commit_hash)
                commit.comment_diff = self.extract_comment_diff(commit_hash)

            return commit

        except Exception:
            return None

    def install_hooks(self) -> Tuple[bool, str]:
        """
        Install git hooks for automatic capture.

        Returns:
            Tuple of (success, message)
        """
        if not self.is_git_repo:
            return False, "Not a git repository"

        # Create hooks directory if needed
        self.hooks_dir.mkdir(parents=True, exist_ok=True)

        hook_path = self.hooks_dir / "post-commit"

        # Check for existing hook
        if hook_path.exists():
            content = hook_path.read_text()
            if "babel capture-commit" in content:
                return True, "Hook already installed"
            else:
                # Append to existing hook
                with open(hook_path, 'a') as f:
                    f.write("\n\n# Added by babel\n")
                    f.write("babel capture-commit --async 2>/dev/null &\n")
                return True, "Hook added to existing post-commit"

        # Create new hook
        hook_path.write_text(POST_COMMIT_HOOK)

        # Make executable
        os.chmod(hook_path, 0o755)

        return True, "Hook installed successfully"

    def uninstall_hooks(self) -> Tuple[bool, str]:
        """
        Remove git hooks.

        Returns:
            Tuple of (success, message)
        """
        if not self.is_git_repo:
            return False, "Not a git repository"

        hook_path = self.hooks_dir / "post-commit"

        if not hook_path.exists():
            return True, "No hook to remove"

        content = hook_path.read_text()

        if "babel capture-commit" not in content:
            return True, "Hook not installed by babel"

        # Check if it's our hook entirely or mixed
        if content.strip() == POST_COMMIT_HOOK.strip():
            # Our hook only - remove file
            hook_path.unlink()
            return True, "Hook removed"
        else:
            # Mixed - remove our lines
            lines = content.split("\n")
            new_lines = [
                line for line in lines
                if "babel capture-commit" not in line and "Added by babel" not in line
            ]
            hook_path.write_text("\n".join(new_lines))
            return True, "Babel hook removed (other hooks preserved)"

    def hooks_status(self) -> str:
        """Get status of git hooks."""
        if not self.is_git_repo:
            return "Not a git repository"

        hook_path = self.hooks_dir / "post-commit"

        if not hook_path.exists():
            return "Not installed"

        content = hook_path.read_text()

        if "babel capture-commit" in content:
            return "Installed"
        else:
            return "Not installed (other hooks present)"


def format_commit_for_extraction(commit: CommitInfo) -> str:
    """
    Format commit info for LLM extraction.
    
    Enhanced to include structural changes and comment diffs.
    """
    parts = [f"Commit: {commit.message}"]

    if commit.body:
        parts.append(f"\n{commit.body}")

    # Structural changes summary
    if commit.structural:
        parts.append(f"\nChanges: {commit.structural.summary}")
        
        # Detail for small change sets
        if commit.structural.total_files <= 10:
            if commit.structural.added:
                parts.append(f"\n  Added: {', '.join(commit.structural.added)}")
            if commit.structural.modified:
                parts.append(f"\n  Modified: {', '.join(commit.structural.modified)}")
            if commit.structural.deleted:
                parts.append(f"\n  Deleted: {', '.join(commit.structural.deleted)}")
            if commit.structural.renamed:
                renames = [f"{old} -> {new}" for old, new in commit.structural.renamed]
                parts.append(f"\n  Renamed: {', '.join(renames)}")
    elif commit.files:
        # Fallback to simple file list
        parts.append(f"\nFiles changed: {', '.join(commit.files[:10])}")
        if len(commit.files) > 10:
            parts.append(f" (+{len(commit.files) - 10} more)")

    # Comment diff (the valuable reasoning)
    if commit.comment_diff:
        parts.append(f"\n\nCode comments added:\n{commit.comment_diff}")

    return "".join(parts)


def is_commit_captured(diff_id: str, captured_ids: Set[str]) -> bool:
    """Check if a commit has already been captured (deduplication)."""
    return diff_id in captured_ids
