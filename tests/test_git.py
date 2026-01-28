"""
Tests for Git Integration — Coherence Evidence for Git hooks

These tests validate:
- Hook installation and removal
- Commit capture
- Commit formatting for extraction

Tests use temporary directories and mock git repos.
No actual git operations on real repositories.

SKIP CONDITIONS:
- Tests marked 'requires_git' skip if git is not installed
- Tests marked 'no_git' always run (test pure Python logic)
"""

import pytest
import subprocess
import os

from babel.services.git import GitIntegration, CommitInfo, format_commit_for_extraction


# ============================================================================
# GIT AVAILABILITY CHECK
# ============================================================================

def git_is_available() -> bool:
    """Check if git is installed and working."""
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return False


# Decorator for tests that require git
requires_git = pytest.mark.skipif(
    not git_is_available(),
    reason="Git is not installed or not available"
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_git_repo(tmp_path):
    """Create a temporary git repository for testing."""
    if not git_is_available():
        pytest.skip("Git is not available")

    repo = tmp_path / "test_repo"
    repo.mkdir()

    try:
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, capture_output=True)

        # Create initial commit
        (repo / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, capture_output=True, check=True)

        return repo
    except subprocess.CalledProcessError:
        pytest.skip("Could not create git repository")


@pytest.fixture
def non_git_dir(tmp_path):
    """Create a directory that is not a git repository."""
    d = tmp_path / "not_git"
    d.mkdir()
    return d


# ============================================================================
# GIT DETECTION TESTS (Requires git)
# ============================================================================

@requires_git
class TestGitDetection:
    """Detect git repository."""

    def test_is_git_repo_true(self, temp_git_repo):
        """Detects valid git repository."""
        git = GitIntegration(temp_git_repo)
        assert git.is_git_repo is True

    def test_is_git_repo_false(self, non_git_dir):
        """Detects non-git directory."""
        git = GitIntegration(non_git_dir)
        assert git.is_git_repo is False


# ============================================================================
# COMMIT READING TESTS (Requires git)
# ============================================================================

@requires_git
class TestCommitReading:
    """Read commit information."""

    def test_get_last_commit(self, temp_git_repo):
        """Can read last commit info."""
        git = GitIntegration(temp_git_repo)
        commit = git.get_last_commit()

        assert commit is not None
        assert commit.message == "Initial commit"
        assert commit.author == "Test User"
        assert len(commit.hash) == 40
        assert "README.md" in commit.files

    def test_get_last_commit_non_git(self, non_git_dir):
        """Returns None for non-git directory."""
        git = GitIntegration(non_git_dir)
        commit = git.get_last_commit()

        assert commit is None

    def test_get_commit_with_body(self, temp_git_repo):
        """Can read commit with multiline message."""
        # Create commit with body
        (temp_git_repo / "file.txt").write_text("content")
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add file", "-m", "This is the body explaining why"],
            cwd=temp_git_repo, capture_output=True
        )

        git = GitIntegration(temp_git_repo)
        commit = git.get_last_commit()

        assert commit.message == "Add file"
        assert "body explaining why" in commit.body

    def test_get_specific_commit(self, temp_git_repo):
        """Can read specific commit by hash."""
        git = GitIntegration(temp_git_repo)

        # Get initial commit hash
        first = git.get_last_commit()
        first_hash = first.hash

        # Create another commit
        (temp_git_repo / "file2.txt").write_text("more")
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Second commit"], cwd=temp_git_repo, capture_output=True)

        # Verify last commit changed
        assert git.get_last_commit().message == "Second commit"

        # But can still read first commit by hash
        first_again = git.get_commit(first_hash)
        assert first_again.message == "Initial commit"


# ============================================================================
# HOOK INSTALLATION TESTS (Requires git)
# ============================================================================

@requires_git
class TestHookInstallation:
    """Git hook management."""

    def test_install_hooks(self, temp_git_repo):
        """Can install post-commit hook."""
        git = GitIntegration(temp_git_repo)

        success, message = git.install_hooks()

        assert success is True
        assert "installed" in message.lower() or "already" in message.lower()

        hook_path = temp_git_repo / ".git" / "hooks" / "post-commit"
        assert hook_path.exists()
        assert "babel capture-commit" in hook_path.read_text()

    def test_install_hooks_idempotent(self, temp_git_repo):
        """Installing twice doesn't duplicate."""
        git = GitIntegration(temp_git_repo)

        git.install_hooks()
        git.install_hooks()

        hook_path = temp_git_repo / ".git" / "hooks" / "post-commit"
        content = hook_path.read_text()

        # Should only appear once
        assert content.count("babel capture-commit") == 1

    def test_uninstall_hooks(self, temp_git_repo):
        """Can uninstall hooks."""
        git = GitIntegration(temp_git_repo)

        git.install_hooks()
        success, message = git.uninstall_hooks()

        assert success is True

        hook_path = temp_git_repo / ".git" / "hooks" / "post-commit"
        # Either removed entirely or our line removed
        if hook_path.exists():
            assert "babel capture-commit" not in hook_path.read_text()

    def test_hooks_status_not_installed(self, temp_git_repo):
        """Status shows not installed."""
        git = GitIntegration(temp_git_repo)

        status = git.hooks_status()
        assert "not installed" in status.lower()

    def test_hooks_status_installed(self, temp_git_repo):
        """Status shows installed after install."""
        git = GitIntegration(temp_git_repo)

        git.install_hooks()
        status = git.hooks_status()

        assert "installed" in status.lower()

    def test_preserves_existing_hooks(self, temp_git_repo):
        """Preserves existing hook content."""
        hook_path = temp_git_repo / ".git" / "hooks" / "post-commit"
        hook_path.parent.mkdir(parents=True, exist_ok=True)

        # Create existing hook
        hook_path.write_text("#!/bin/sh\necho 'Existing hook'\n")
        os.chmod(hook_path, 0o755)

        git = GitIntegration(temp_git_repo)
        git.install_hooks()

        content = hook_path.read_text()

        # Both should be present
        assert "Existing hook" in content
        assert "babel capture-commit" in content


# ============================================================================
# COMMIT FORMATTING TESTS (No git required — pure Python)
# ============================================================================

class TestCommitFormatting:
    """Format commits for extraction. No git required."""

    def test_format_simple_commit(self):
        """Formats simple commit message."""
        commit = CommitInfo(
            hash="abc123def456",
            message="Fix auth bug",
            body="",
            author="Dev",
            email="dev@test.com",
            files=["auth.py"]
        )

        text = format_commit_for_extraction(commit)

        assert "Fix auth bug" in text
        assert "auth.py" in text

    def test_format_commit_with_body(self):
        """Formats commit with body."""
        commit = CommitInfo(
            hash="abc123",
            message="Refactor auth",
            body="Switched to JWT because sessions were too complex",
            author="Dev",
            email="dev@test.com",
            files=["auth.py", "tokens.py"]
        )

        text = format_commit_for_extraction(commit)

        assert "Refactor auth" in text
        assert "JWT" in text
        assert "sessions were too complex" in text

    def test_format_commit_many_files(self):
        """Truncates long file lists."""
        commit = CommitInfo(
            hash="abc123",
            message="Big refactor",
            body="",
            author="Dev",
            email="dev@test.com",
            files=[f"file{i}.py" for i in range(20)]
        )

        text = format_commit_for_extraction(commit)

        assert "file0.py" in text  # First files included
        assert "+10 more" in text  # Truncation indicator


# ============================================================================
# EVENT INTEGRATION TESTS (No git required — pure Python)
# ============================================================================

class TestCommitEvents:
    """Commit capture creates proper events. No git required."""

    def test_capture_commit_event_type(self):
        """Commit event has correct type."""
        from babel.core.events import EventType, capture_commit

        event = capture_commit(
            commit_hash="abc123",
            message="Test commit",
            body="",
            author="Dev",
            files=["test.py"]
        )

        assert event.type == EventType.COMMIT_CAPTURED
        assert event.data['hash'] == "abc123"
        assert event.data['message'] == "Test commit"
        assert "test.py" in event.data['files']


# ============================================================================
# GIT INTEGRATION CLASS TESTS (No git required for basic tests)
# ============================================================================

class TestGitIntegrationBasic:
    """Basic GitIntegration tests that don't need git."""

    def test_non_git_directory(self, non_git_dir):
        """Correctly identifies non-git directory."""
        git = GitIntegration(non_git_dir)
        assert git.is_git_repo is False

    def test_get_commit_non_git(self, non_git_dir):
        """Returns None for non-git directory."""
        git = GitIntegration(non_git_dir)
        commit = git.get_last_commit()
        assert commit is None

    def test_install_non_git(self, non_git_dir):
        """Install fails gracefully for non-git directory."""
        git = GitIntegration(non_git_dir)
        success, message = git.install_hooks()
        assert success is False
        assert "not a git repository" in message.lower()


# ============================================================================
# STRUCTURAL CHANGES TESTS (No git required — pure Python)
# ============================================================================

class TestStructuralChanges:
    """StructuralChanges dataclass tests. No git required."""

    def test_to_dict(self):
        """Converts to dictionary correctly."""
        from babel.services.git import StructuralChanges
        
        changes = StructuralChanges(
            added=['new.py'],
            modified=['old.py'],
            deleted=['removed.py'],
            renamed=[('before.py', 'after.py')]
        )
        
        d = changes.to_dict()
        
        assert d['added'] == ['new.py']
        assert d['modified'] == ['old.py']
        assert d['deleted'] == ['removed.py']
        assert d['renamed'] == [{'from': 'before.py', 'to': 'after.py'}]

    def test_from_dict(self):
        """Creates from dictionary correctly."""
        from babel.services.git import StructuralChanges
        
        d = {
            'added': ['a.py'],
            'modified': ['m.py'],
            'deleted': [],
            'renamed': [{'from': 'x.py', 'to': 'y.py'}]
        }
        
        changes = StructuralChanges.from_dict(d)
        
        assert changes.added == ['a.py']
        assert changes.renamed == [('x.py', 'y.py')]

    def test_summary(self):
        """Human-readable summary."""
        from babel.services.git import StructuralChanges
        
        changes = StructuralChanges(
            added=['a.py', 'b.py'],
            modified=['c.py'],
            deleted=[],
            renamed=[]
        )
        
        summary = changes.summary
        
        assert "+2 added" in summary
        assert "~1 modified" in summary

    def test_summary_empty(self):
        """Summary for no changes."""
        from babel.services.git import StructuralChanges
        
        changes = StructuralChanges()
        assert changes.summary == "no changes"

    def test_total_files(self):
        """Total file count."""
        from babel.services.git import StructuralChanges
        
        changes = StructuralChanges(
            added=['a.py'],
            modified=['b.py', 'c.py'],
            deleted=['d.py'],
            renamed=[('e.py', 'f.py')]
        )
        
        assert changes.total_files == 5


# ============================================================================
# COMMENT DETECTION TESTS (No git required — pure Python)
# ============================================================================

class TestCommentDetection:
    """Comment pattern detection. No git required."""

    def test_python_hash_comment(self):
        """Detects Python # comments."""
        from babel.services.git import GitIntegration
        
        git = GitIntegration()
        
        assert git._is_comment("# This is a comment", ".py") is True
        assert git._is_comment("code = 1", ".py") is False

    def test_js_slash_comment(self):
        """Detects JavaScript // comments."""
        from babel.services.git import GitIntegration
        
        git = GitIntegration()
        
        assert git._is_comment("// This is a comment", ".js") is True
        assert git._is_comment("/* block comment */", ".js") is True
        assert git._is_comment("const x = 1;", ".js") is False

    def test_rust_doc_comment(self):
        """Detects Rust doc comments."""
        from babel.services.git import GitIntegration
        
        git = GitIntegration()
        
        assert git._is_comment("/// Doc comment", ".rs") is True
        assert git._is_comment("//! Module doc", ".rs") is True
        assert git._is_comment("// Regular comment", ".rs") is True

    def test_empty_line(self):
        """Empty lines are not comments."""
        from babel.services.git import GitIntegration
        
        git = GitIntegration()
        
        assert git._is_comment("", ".py") is False
        assert git._is_comment("   ", ".py") is False


# ============================================================================
# ENHANCED COMMIT FORMATTING TESTS (No git required — pure Python)
# ============================================================================

class TestEnhancedCommitFormatting:
    """Enhanced commit formatting. No git required."""

    def test_format_with_structural_changes(self):
        """Formats commit with structural changes."""
        from babel.services.git import CommitInfo, StructuralChanges, format_commit_for_extraction
        
        commit = CommitInfo(
            hash="abc123",
            message="Add feature",
            body="",
            author="Dev",
            email="dev@test.com",
            files=["new.py"],
            structural=StructuralChanges(added=["new.py"]),
            comment_diff=None
        )
        
        text = format_commit_for_extraction(commit)
        
        assert "Add feature" in text
        assert "+1 added" in text

    def test_format_with_comment_diff(self):
        """Formats commit with comment diff."""
        from babel.services.git import CommitInfo, format_commit_for_extraction
        
        commit = CommitInfo(
            hash="abc123",
            message="Update auth",
            body="",
            author="Dev",
            email="dev@test.com",
            files=["auth.py"],
            structural=None,
            comment_diff="[auth.py] # Switch to JWT for stateless operation"
        )
        
        text = format_commit_for_extraction(commit)
        
        assert "Update auth" in text
        assert "Code comments added:" in text
        assert "JWT for stateless" in text

    def test_format_with_both(self):
        """Formats commit with both structural and comments."""
        from babel.services.git import CommitInfo, StructuralChanges, format_commit_for_extraction
        
        commit = CommitInfo(
            hash="abc123",
            message="Refactor",
            body="Major cleanup",
            author="Dev",
            email="dev@test.com",
            files=["a.py", "b.py"],
            structural=StructuralChanges(modified=["a.py", "b.py"]),
            comment_diff="[a.py] # Extracted to helper function"
        )
        
        text = format_commit_for_extraction(commit)
        
        assert "Refactor" in text
        assert "Major cleanup" in text
        assert "~2 modified" in text
        assert "helper function" in text

    def test_diff_id_property(self):
        """CommitInfo has diff_id for deduplication."""
        from babel.services.git import CommitInfo
        
        commit = CommitInfo(
            hash="abc123def456",
            message="Test",
            body="",
            author="Dev",
            email="dev@test.com",
            files=[]
        )
        
        assert commit.diff_id == "abc123def456"


# ============================================================================
# DEDUPLICATION TESTS (No git required — pure Python)
# ============================================================================

class TestDeduplication:
    """Commit deduplication logic. No git required."""

    def test_is_commit_captured(self):
        """Checks if commit was already captured."""
        from babel.services.git import is_commit_captured
        
        captured = {"abc123", "def456"}
        
        assert is_commit_captured("abc123", captured) is True
        assert is_commit_captured("xyz789", captured) is False

    def test_capture_commit_with_diff_id(self):
        """capture_commit includes diff_id for deduplication."""
        from babel.core.events import capture_commit
        
        event = capture_commit(
            commit_hash="abc123",
            message="Test",
            body="",
            author="Dev",
            files=["test.py"],
            structural={'added': ['test.py'], 'modified': [], 'deleted': [], 'renamed': []},
            comment_diff="# New test"
        )
        
        assert event.data['diff_id'] == "abc123"
        assert event.data['structural'] == {'added': ['test.py'], 'modified': [], 'deleted': [], 'renamed': []}
        assert event.data['comment_diff'] == "# New test"


# ============================================================================
# STRUCTURAL EXTRACTION TESTS (Requires git)
# ============================================================================

@requires_git
class TestStructuralExtraction:
    """Structural change extraction from real git repos."""

    def test_get_structural_changes(self, temp_git_repo):
        """Extracts structural changes from commit."""
        # Create a new file and commit
        (temp_git_repo / "added.py").write_text("# New file\nprint('hello')")
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add file"], cwd=temp_git_repo, capture_output=True)
        
        git = GitIntegration(temp_git_repo)
        changes = git.get_structural_changes()
        
        assert changes is not None
        assert "added.py" in changes.added

    def test_modified_file_detection(self, temp_git_repo):
        """Detects modified files."""
        # Modify existing file
        (temp_git_repo / "README.md").write_text("# Updated\nNew content")
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Update readme"], cwd=temp_git_repo, capture_output=True)
        
        git = GitIntegration(temp_git_repo)
        changes = git.get_structural_changes()
        
        assert changes is not None
        assert "README.md" in changes.modified


# ============================================================================
# COMMENT EXTRACTION TESTS (Requires git)
# ============================================================================

@requires_git
class TestCommentExtraction:
    """Comment extraction from real git repos."""

    def test_extract_python_comments(self, temp_git_repo):
        """Extracts Python comments from diff."""
        # Create Python file with comments
        code = '''# This is a new module
# It handles authentication

def auth():
    # Validate user credentials
    pass
'''
        (temp_git_repo / "auth.py").write_text(code)
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add auth"], cwd=temp_git_repo, capture_output=True)
        
        git = GitIntegration(temp_git_repo)
        comments = git.extract_comment_diff()
        
        assert comments is not None
        assert "new module" in comments or "authentication" in comments

    def test_no_comments_returns_none(self, temp_git_repo):
        """Returns None when no comments in diff."""
        # Create file without comments
        (temp_git_repo / "nocomment.txt").write_text("Just text\nNo comments here")
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add text"], cwd=temp_git_repo, capture_output=True)
        
        git = GitIntegration(temp_git_repo)
        comments = git.extract_comment_diff()
        
        # .txt is not a supported extension, so no comments extracted
        assert comments is None

    def test_enhanced_commit_info(self, temp_git_repo):
        """get_commit returns enhanced info."""
        # Create file with comment
        (temp_git_repo / "feature.py").write_text("# Feature X implementation\nx = 1")
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add feature X"], cwd=temp_git_repo, capture_output=True)
        
        git = GitIntegration(temp_git_repo)
        commit = git.get_commit("HEAD", include_diff=True)
        
        assert commit is not None
        assert commit.structural is not None
        assert "feature.py" in commit.structural.added
        assert commit.comment_diff is not None
        assert "Feature X" in commit.comment_diff