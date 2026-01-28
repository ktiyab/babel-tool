"""
Scanner -- Context-aware technical advisor

Uses Babel's unique knowledge (purpose, decisions, constraints)
to provide meaningful, project-specific advice.

What makes Babel scan different:
- Generic scanner: "SQL injection risk"
- Babel scan: "SQL injection risk conflicts with your 'sanitize all input' 
               constraint from March. Check entry points X, Y, Z."

Scan types:
- architecture: Design patterns, structure alignment
- security: Vulnerabilities in context
- performance: Bottlenecks given constraints
- dependencies: Upgrade priority based on purpose
- health: Quick overview (default)
"""

import ast
import json
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass, field
from pathlib import Path

from ..core.events import DualEventStore
from ..core.graph import GraphStore
from ..presentation.symbols import get_symbols

if TYPE_CHECKING:
    from .providers import LLMProvider
    from ..core.loader import LazyLoader
    from ..core.vocabulary import Vocabulary


# =============================================================================
# Verification Status Constants
# =============================================================================

VERIFIED_TRUE = "verified_true"      # Confirmed unused (safe to remove)
VERIFIED_FALSE = "verified_false"    # False positive (actually used)
UNCERTAIN = "uncertain"              # Could not determine (needs manual review)


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class ScanFinding:
    """A single finding from scan."""
    severity: str  # "info" | "warning" | "concern" | "critical"
    category: str  # "architecture" | "security" | "performance" | etc.
    title: str
    description: str
    suggestion: str
    references: List[str] = field(default_factory=list)  # Decision IDs referenced
    # Extended fields for clean scan (optional for other types)
    finding_id: Optional[str] = None  # Unique ID for management
    file: Optional[str] = None  # Source file path
    line: Optional[int] = None  # Line number
    code: Optional[str] = None  # Ruff rule code (F401, etc.)
    symbol: Optional[str] = None  # Import/variable name
    status: str = "pending"  # pending | validated | invalidated | resolved
    # Context enrichment (populated by symbol linking)
    containing_symbol: Optional[str] = None  # Symbol containing this line
    linked_decisions: List[str] = field(default_factory=list)  # Decision IDs

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "suggestion": self.suggestion,
            "references": self.references
        }
        # Include extended fields if present
        if self.finding_id:
            data["finding_id"] = self.finding_id
        if self.file:
            data["file"] = self.file
        if self.line:
            data["line"] = self.line
        if self.code:
            data["code"] = self.code
        if self.symbol:
            data["symbol"] = self.symbol
        if self.status != "pending":
            data["status"] = self.status
        if self.containing_symbol:
            data["containing_symbol"] = self.containing_symbol
        if self.linked_decisions:
            data["linked_decisions"] = self.linked_decisions
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScanFinding':
        return cls(
            severity=data.get("severity", "info"),
            category=data.get("category", "general"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            suggestion=data.get("suggestion", ""),
            references=data.get("references", []),
            finding_id=data.get("finding_id"),
            file=data.get("file"),
            line=data.get("line"),
            code=data.get("code"),
            symbol=data.get("symbol"),
            status=data.get("status", "pending"),
            containing_symbol=data.get("containing_symbol"),
            linked_decisions=data.get("linked_decisions", [])
        )


@dataclass
class ScanContext:
    """Project context for scanning (P3 compliant)."""
    need: Optional[str]  # P1: What problem we're solving
    purpose: Optional[str]
    decisions: List[Dict[str, Any]]
    constraints: List[Dict[str, Any]]
    tech_stack: List[str]
    recent_topics: List[str]
    event_count: int
    domain_decisions: Dict[str, List[Dict]]  # P3: Decisions grouped by domain
    
    def to_prompt(self) -> str:
        """Format context for LLM prompt."""
        lines = []
        
        if self.need:
            lines.append(f"NEED (problem being solved): {self.need}")
            lines.append("")
        
        if self.purpose:
            lines.append(f"PURPOSE (what we're building): {self.purpose}")
            lines.append("")
        
        if self.decisions:
            lines.append("DECISIONS MADE:")
            for d in self.decisions[:15]:  # Limit for token efficiency
                summary = d.get("summary", str(d))
                domain = d.get("domain", "")
                domain_tag = f" [{domain}]" if domain else ""
                lines.append(f"  • {summary}{domain_tag}")
            lines.append("")
        
        if self.constraints:
            lines.append("CONSTRAINTS:")
            for c in self.constraints[:10]:
                summary = c.get("summary", str(c))
                lines.append(f"  • {summary}")
            lines.append("")
        
        if self.tech_stack:
            lines.append(f"TECHNOLOGY: {', '.join(self.tech_stack[:20])}")
            lines.append("")
        
        return "\n".join(lines)
    
    def get_decisions_for_domain(self, domain: str) -> List[Dict]:
        """Get decisions relevant to a domain (P3: expertise-weighted)."""
        return self.domain_decisions.get(domain, [])


@dataclass
class ScanResult:
    """Result of a scan."""
    scan_id: str
    timestamp: str
    scan_type: str
    status: str  # "healthy" | "concerns" | "issues"
    findings: List[ScanFinding]
    context_hash: str  # For cache invalidation
    summary: str
    
    @property
    def has_concerns(self) -> bool:
        return any(f.severity in ("warning", "concern", "critical") for f in self.findings)
    
    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "critical")
    
    @property
    def concern_count(self) -> int:
        return sum(1 for f in self.findings if f.severity in ("concern", "critical"))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scan_id": self.scan_id,
            "timestamp": self.timestamp,
            "scan_type": self.scan_type,
            "status": self.status,
            "findings": [f.to_dict() for f in self.findings],
            "context_hash": self.context_hash,
            "summary": self.summary
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScanResult':
        return cls(
            scan_id=data["scan_id"],
            timestamp=data["timestamp"],
            scan_type=data["scan_type"],
            status=data["status"],
            findings=[ScanFinding.from_dict(f) for f in data.get("findings", [])],
            context_hash=data.get("context_hash", ""),
            summary=data.get("summary", "")
        )


# =============================================================================
# Scanner
# =============================================================================

class Scanner:
    """
    Context-aware technical scanner.
    
    Uses Babel's knowledge for project-specific advice.
    """
    
    def __init__(
        self,
        events: DualEventStore,
        graph: GraphStore,
        provider: 'LLMProvider',
        loader: 'LazyLoader' = None,
        vocabulary: 'Vocabulary' = None,
        cache_path: Path = None
    ):
        self.events = events
        self.graph = graph
        self.provider = provider
        self.loader = loader
        self.vocabulary = vocabulary
        self.cache_path = cache_path
        
        self._context_cache: Optional[ScanContext] = None
    
    # =========================================================================
    # Public Interface
    # =========================================================================
    
    def scan(
        self,
        scan_type: str = "health",
        deep: bool = False,
        query: str = None
    ) -> ScanResult:
        """
        Run a scan.

        Args:
            scan_type: Type of scan (health, architecture, security, clean, etc.)
            deep: Run comprehensive analysis
            query: Specific question to answer

        Returns:
            ScanResult with findings and suggestions
        """
        # Clean scan is special - doesn't need context, runs ruff directly
        if scan_type == "clean":
            return self._scan_clean(deep)

        # Gather context
        context = self._gather_context()
        context_hash = self._hash_context(context)

        # Check cache (unless deep scan)
        if not deep and not query:
            cached = self._load_cache(scan_type, context_hash)
            if cached:
                return cached

        # Run appropriate scan
        if query:
            result = self._scan_query(context, query)
        elif scan_type == "health":
            result = self._scan_health(context, deep)
        elif scan_type == "architecture":
            result = self._scan_architecture(context, deep)
        elif scan_type == "security":
            result = self._scan_security(context, deep)
        elif scan_type == "performance":
            result = self._scan_performance(context, deep)
        elif scan_type == "dependencies":
            result = self._scan_dependencies(context, deep)
        else:
            result = self._scan_health(context, deep)
        
        # Cache result
        self._save_cache(result)
        
        return result
    
    # =========================================================================
    # Finding Management (public interface for commands)
    # =========================================================================

    def get_findings(self, scan_type: str) -> List[ScanFinding]:
        """Get persisted findings for scan type.

        Returns list of findings from last scan.
        """
        return self._load_findings(scan_type)

    def get_finding(self, scan_type: str, finding_id: str) -> Optional[ScanFinding]:
        """Get specific finding by ID (supports prefix matching)."""
        findings = self._load_findings(scan_type)
        for f in findings:
            # Support prefix matching (display shows 8 chars, full ID is 12)
            if f.finding_id and f.finding_id.startswith(finding_id):
                return f
        return None

    def update_finding_status(
        self,
        scan_type: str,
        finding_id: str,
        status: str
    ) -> Optional[ScanFinding]:
        """Update finding status (validate/resolve).

        Args:
            scan_type: Type of scan (clean, etc.)
            finding_id: ID of finding to update
            status: New status (validated, resolved)

        Returns:
            Updated finding or None if not found
        """
        findings = self._load_findings(scan_type)
        updated = None

        for f in findings:
            # Support prefix matching (display shows 8 chars, full ID is 12)
            if f.finding_id and f.finding_id.startswith(finding_id):
                f.status = status
                updated = f
                break

        if updated:
            self._save_findings(scan_type, findings)

        return updated

    def add_exclusion(
        self,
        scan_type: str,
        finding_id: str,
        reason: str,
        finding: Optional[ScanFinding] = None
    ) -> bool:
        """Add exclusion (invalidate as false positive).

        Args:
            scan_type: Type of scan
            finding_id: ID of finding to exclude
            reason: Why it's a false positive
            finding: Optional finding for metadata

        Returns:
            True if added, False if already excluded
        """
        exclusions = self._load_exclusions(scan_type)

        if finding_id in exclusions:
            return False  # Already excluded

        exclusion_data = {
            "reason": reason,
            "excluded_at": datetime.now(timezone.utc).isoformat()
        }

        # Add finding metadata for reference
        if finding:
            exclusion_data["file"] = finding.file
            exclusion_data["line"] = finding.line
            exclusion_data["code"] = finding.code
            exclusion_data["symbol"] = finding.symbol

        # Use full finding_id if we have the finding object
        full_id = finding.finding_id if finding and finding.finding_id else finding_id
        exclusions[full_id] = exclusion_data
        self._save_exclusions(scan_type, exclusions)

        # Remove from active findings (use prefix matching for consistency)
        findings = self._load_findings(scan_type)
        findings = [f for f in findings if not (f.finding_id and f.finding_id.startswith(finding_id))]
        self._save_findings(scan_type, findings)

        return True

    def remove_exclusion(self, scan_type: str, finding_id: str) -> bool:
        """Remove exclusion (re-enable finding).

        Returns:
            True if removed, False if not found
        """
        exclusions = self._load_exclusions(scan_type)

        if finding_id not in exclusions:
            return False

        del exclusions[finding_id]
        self._save_exclusions(scan_type, exclusions)
        return True

    def get_exclusions(self, scan_type: str) -> Dict[str, Dict[str, Any]]:
        """Get all exclusions for scan type."""
        return self._load_exclusions(scan_type)

    def get_findings_summary(self, scan_type: str) -> Dict[str, int]:
        """Get summary counts for findings.

        Returns dict with counts: pending, validated, resolved, excluded
        """
        findings = self._load_findings(scan_type)
        exclusions = self._load_exclusions(scan_type)

        counts = {
            "pending": 0,
            "validated": 0,
            "resolved": 0,
            "excluded": len(exclusions),
            "verified_true": 0,
            "verified_false": 0,
            "uncertain": 0
        }

        for f in findings:
            if f.status in counts:
                counts[f.status] += 1
            else:
                counts["pending"] += 1  # Default to pending

        return counts

    # =========================================================================
    # Verification (Hybrid Parser: regex fast-path + AST cross-check)
    # =========================================================================

    def verify_findings(self, scan_type: str) -> Dict[str, Any]:
        """
        Verify all findings using hybrid parser approach.

        Uses regex fast-path for obvious cases, AST cross-check for validation.
        Updates findings.json with verification status.

        Args:
            scan_type: Type of scan (e.g., "clean")

        Returns:
            Dict with verification summary:
            {
                "verified_true": count,
                "verified_false": count,
                "uncertain": count,
                "findings": [updated findings]
            }
        """
        findings = self._load_findings(scan_type)
        if not findings:
            return {
                "verified_true": 0,
                "verified_false": 0,
                "uncertain": 0,
                "findings": []
            }

        results = {
            "verified_true": 0,
            "verified_false": 0,
            "uncertain": 0,
            "findings": []
        }

        for finding in findings:
            # Skip already processed findings
            if finding.status in (VERIFIED_TRUE, VERIFIED_FALSE, UNCERTAIN, "resolved"):
                results[finding.status] = results.get(finding.status, 0) + 1
                results["findings"].append(finding)
                continue

            # Verify this finding
            status = self._verify_single_finding(finding)
            finding.status = status
            results[status] += 1
            results["findings"].append(finding)

        # Persist updated findings
        self._save_findings(scan_type, findings)

        return results

    def _verify_single_finding(self, finding: ScanFinding) -> str:
        """
        Verify a single finding using hybrid parser.

        Algorithm:
        1. Pattern rules (fast reject false positives)
        2. Regex negative search
        3. AST cross-check for uncertain cases

        Args:
            finding: The finding to verify

        Returns:
            Status: VERIFIED_TRUE, VERIFIED_FALSE, or UNCERTAIN
        """
        if not finding.file or not finding.symbol:
            return UNCERTAIN

        try:
            file_path = Path(finding.file)
            if not file_path.exists():
                return UNCERTAIN

            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')

            # RULE 1: __init__.py at top level = likely re-export
            if self._is_init_reexport(finding.file, finding.line, lines):
                return VERIFIED_FALSE

            # RULE 2: Symbol in __all__ = explicitly exported
            if self._is_in_all_list(content, finding.symbol):
                return VERIFIED_FALSE

            # RULE 3: Import inside TYPE_CHECKING block
            if self._is_type_checking_import(lines, finding.line):
                # Check if used in type annotations
                if self._symbol_in_annotations(content, finding.symbol):
                    return VERIFIED_FALSE

            # REGEX FAST-PATH: Search for symbol after import line
            if self._regex_search_after_import(lines, finding.symbol, finding.line):
                return VERIFIED_FALSE  # Found usage

            # AST CROSS-CHECK: For higher confidence
            ast_used = self._ast_check_usage(content, finding.symbol, finding.line)
            if ast_used is True:
                return VERIFIED_FALSE
            elif ast_used is False:
                return VERIFIED_TRUE
            else:
                return UNCERTAIN

        except Exception:
            return UNCERTAIN

    def _is_init_reexport(self, file_path: str, line: int, lines: List[str]) -> bool:
        """
        Check if this is a re-export pattern in __init__.py.

        Re-exports are imports at module level in __init__.py files
        that exist to expose symbols to package users.
        """
        # Check if file is __init__.py
        if not file_path.endswith('__init__.py'):
            return False

        # Check if import is at module level (not inside function/class)
        if line <= 0 or line > len(lines):
            return False

        # Simple heuristic: if the line starts without indentation, it's top-level
        import_line = lines[line - 1]  # 1-indexed to 0-indexed
        if import_line and not import_line[0].isspace():
            return True

        return False

    def _is_in_all_list(self, content: str, symbol: str) -> bool:
        """
        Check if symbol is in __all__ list.

        Symbols in __all__ are explicitly exported and should not be removed.
        """
        import re

        # Match __all__ = [...] or __all__ += [...]
        all_pattern = r'__all__\s*[+]?=\s*\[([^\]]*)\]'
        match = re.search(all_pattern, content, re.DOTALL)

        if match:
            all_content = match.group(1)
            # Check if symbol appears as a string in the list
            # Handles: "symbol", 'symbol'
            if re.search(rf'''["']{re.escape(symbol)}["']''', all_content):
                return True

        return False

    def _is_type_checking_import(self, lines: List[str], import_line: int) -> bool:
        """
        Check if import is inside a TYPE_CHECKING block.

        TYPE_CHECKING imports are only used for type hints and
        may not have runtime references.
        """
        if import_line <= 0 or import_line > len(lines):
            return False

        # Look backwards for TYPE_CHECKING
        for i in range(import_line - 2, max(0, import_line - 20), -1):
            line = lines[i].strip()
            if line.startswith('if TYPE_CHECKING'):
                return True
            # If we hit a non-indented line that's not empty, stop
            if line and not lines[i][0].isspace() and not line.startswith('#'):
                break

        return False

    def _symbol_in_annotations(self, content: str, symbol: str) -> bool:
        """
        Check if symbol appears in type annotations.

        Looks for patterns like:
        - def foo() -> Symbol:
        - x: Symbol = ...
        - List[Symbol]
        """
        import re

        # Pattern for type annotations
        patterns = [
            rf'->\s*[^:]*\b{re.escape(symbol)}\b',  # Return type
            rf':\s*[^=]*\b{re.escape(symbol)}\b',   # Variable annotation
            rf'\[\s*{re.escape(symbol)}\s*[,\]]',   # Generic parameter
        ]

        for pattern in patterns:
            if re.search(pattern, content):
                return True

        return False

    def _regex_search_after_import(self, lines: List[str], symbol: str, import_line: int) -> bool:
        """
        Regex fast-path: search for symbol usage after import line.

        Args:
            lines: File content split by lines
            symbol: Symbol name to search for
            import_line: Line number of import (1-indexed)

        Returns:
            True if symbol found after import, False otherwise
        """
        import re

        if import_line <= 0 or import_line > len(lines):
            return False

        # Search lines after the import
        for i in range(import_line, len(lines)):  # import_line is 1-indexed, so this starts at next line
            line = lines[i]

            # Skip comments
            stripped = line.strip()
            if stripped.startswith('#'):
                continue

            # Word boundary search for symbol
            if re.search(rf'\b{re.escape(symbol)}\b', line):
                return True

        return False

    def _ast_check_usage(self, content: str, symbol: str, import_line: int) -> Optional[bool]:
        """
        AST cross-check: verify symbol usage via AST parsing.

        Args:
            content: Full file content
            symbol: Symbol name to check
            import_line: Line of import (1-indexed)

        Returns:
            True if used, False if not used, None if AST parsing failed
        """
        import ast

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return None

        # Collect all Name nodes after the import line
        class NameCollector(ast.NodeVisitor):
            def __init__(self):
                self.names = []
                self.target_line = import_line

            def visit_Name(self, node):
                if node.lineno > self.target_line:
                    self.names.append(node.id)
                self.generic_visit(node)

            def visit_Attribute(self, node):
                # Handle attribute access like symbol.method
                if isinstance(node.value, ast.Name):
                    if node.value.lineno > self.target_line:
                        self.names.append(node.value.id)
                self.generic_visit(node)

        collector = NameCollector()
        collector.visit(tree)

        return symbol in collector.names

    # =========================================================================
    # Removal (Safe deletion with git checkpoint)
    # =========================================================================

    def remove_verified_imports(self, scan_type: str, run_tests: bool = True) -> Dict[str, Any]:
        """
        Remove verified unused imports with safety checkpoint.

        Only removes findings with VERIFIED_TRUE status.
        Creates git commit before modifications for rollback.
        All-or-nothing: reverts on any failure OR test failure.

        Args:
            scan_type: Type of scan (e.g., "clean")
            run_tests: Whether to run affected tests after removal (default True)

        Returns:
            Dict with removal summary:
            {
                "success": bool,
                "removed_count": int,
                "files_modified": [{"file": str, "removals": [...]}],
                "checkpoint_sha": str,
                "test_results": {...} (if tests were run),
                "error": str (if failed)
            }
        """
        findings = self._load_findings(scan_type)
        if not findings:
            return {
                "success": False,
                "removed_count": 0,
                "files_modified": [],
                "checkpoint_sha": None,
                "error": "No findings to remove"
            }

        # Filter to only VERIFIED_TRUE findings
        to_remove = [f for f in findings if f.status == VERIFIED_TRUE]
        if not to_remove:
            return {
                "success": False,
                "removed_count": 0,
                "files_modified": [],
                "checkpoint_sha": None,
                "error": "No verified findings to remove. Run --verify first."
            }

        # Group by file for efficient processing
        by_file: Dict[str, List[ScanFinding]] = {}
        for f in to_remove:
            if f.file:
                if f.file not in by_file:
                    by_file[f.file] = []
                by_file[f.file].append(f)

        # Sort findings by line number descending (remove from bottom up)
        for file_path in by_file:
            by_file[file_path].sort(key=lambda x: x.line or 0, reverse=True)

        # Create git checkpoint
        files_to_modify = list(by_file.keys())
        checkpoint_sha = self._git_create_checkpoint(files_to_modify)
        if not checkpoint_sha:
            return {
                "success": False,
                "removed_count": 0,
                "files_modified": [],
                "checkpoint_sha": None,
                "error": "Failed to create git checkpoint. Ensure working directory is clean."
            }

        # Perform removals
        files_modified = []
        total_removed = 0

        try:
            for file_path, file_findings in by_file.items():
                file_result = {
                    "file": file_path,
                    "removals": []
                }

                for finding in file_findings:
                    success = self._remove_import_from_file(
                        file_path, finding.line, finding.symbol
                    )
                    if success:
                        file_result["removals"].append({
                            "line": finding.line,
                            "symbol": finding.symbol,
                            "finding_id": finding.finding_id
                        })
                        total_removed += 1
                        # Mark as resolved
                        finding.status = "resolved"

                if file_result["removals"]:
                    files_modified.append(file_result)

            # Save updated findings
            self._save_findings(scan_type, findings)

            # Run affected tests if requested
            test_results = None
            if run_tests and files_modified:
                modified_paths = [f["file"] for f in files_modified]
                test_results = self._run_affected_tests(modified_paths)

                if not test_results["success"]:
                    # Tests failed - auto-revert (all-or-nothing)
                    self._git_revert_checkpoint(checkpoint_sha)
                    return {
                        "success": False,
                        "removed_count": 0,
                        "files_modified": [],
                        "checkpoint_sha": checkpoint_sha,
                        "test_results": test_results,
                        "error": f"Tests failed, auto-reverted. {test_results.get('error', '')}"
                    }

            return {
                "success": True,
                "removed_count": total_removed,
                "files_modified": files_modified,
                "checkpoint_sha": checkpoint_sha,
                "test_results": test_results,
                "error": None
            }

        except Exception as e:
            # All-or-nothing: revert on failure
            self._git_revert_checkpoint(checkpoint_sha)
            return {
                "success": False,
                "removed_count": 0,
                "files_modified": [],
                "checkpoint_sha": checkpoint_sha,
                "test_results": None,
                "error": f"Removal failed, reverted: {str(e)}"
            }

    def _git_create_checkpoint(self, files: List[str]) -> Optional[str]:
        """
        Create git commit checkpoint before modifications.

        Args:
            files: List of files that will be modified

        Returns:
            Commit SHA or None if failed
        """
        import subprocess

        try:
            # Check for uncommitted changes in target files
            result = subprocess.run(
                ["git", "status", "--porcelain"] + files,
                capture_output=True,
                text=True,
                cwd=str(Path.cwd())
            )

            if result.stdout.strip():
                # Files have uncommitted changes - can't proceed safely
                return None

            # Create checkpoint commit with current state
            # First, stage the files
            subprocess.run(
                ["git", "add"] + files,
                capture_output=True,
                cwd=str(Path.cwd())
            )

            # Create checkpoint commit
            result = subprocess.run(
                ["git", "commit", "--allow-empty", "-m",
                 "[babel] Pre-cleanup checkpoint (auto-revert on failure)"],
                capture_output=True,
                text=True,
                cwd=str(Path.cwd())
            )

            # Get the commit SHA
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=str(Path.cwd())
            )

            return result.stdout.strip() if result.returncode == 0 else None

        except Exception:
            return None

    def _git_revert_checkpoint(self, checkpoint_sha: str) -> bool:
        """
        Revert to checkpoint commit on failure.

        Args:
            checkpoint_sha: SHA of checkpoint commit

        Returns:
            True if reverted successfully
        """
        import subprocess

        try:
            # Reset to checkpoint
            subprocess.run(
                ["git", "reset", "--hard", checkpoint_sha],
                capture_output=True,
                cwd=str(Path.cwd())
            )
            return True
        except Exception:
            return False

    def _remove_import_from_file(
        self,
        file_path: str,
        line_number: int,
        symbol: str
    ) -> bool:
        """
        Remove an import from a file using hybrid AST validation.

        Handles both single imports and multi-imports:
        - "import json" -> delete line
        - "from typing import List, Optional" removing Optional -> "from typing import List"
        - Multi-line imports with parentheses

        Uses hybrid approach per [UW-NI]:
        1. AST validates symbol exists in import
        2. String parser performs removal (preserves formatting)
        3. AST validates result is still valid Python

        Args:
            file_path: Path to file
            line_number: Line number of import (1-indexed)
            symbol: Symbol to remove

        Returns:
            True if removed successfully
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return False

            source = path.read_text(encoding='utf-8')
            lines = source.split('\n')

            if line_number <= 0 or line_number > len(lines):
                return False

            line_idx = line_number - 1  # Convert to 0-indexed
            import_line = lines[line_idx]

            # HYBRID STEP 1: Refuse compound statements (e.g., "import x; y = 1")
            if self._is_compound_statement(import_line):
                return False  # Unsafe to modify

            # HYBRID STEP 2: AST validates symbol exists before modification
            is_valid, _ = self._validate_import_with_ast(source, line_number, symbol)
            if not is_valid:
                return False

            # Check if this is part of a multi-line import
            if self._is_multiline_import_continuation(lines, line_idx):
                return self._remove_from_multiline_import(path, lines, line_idx, symbol)

            # Try to remove symbol from single-line import
            new_line = self._remove_symbol_from_import(import_line, symbol)

            if new_line is None:
                # Delete entire line
                del lines[line_idx]
            elif new_line != import_line:
                # Replace with modified line
                lines[line_idx] = new_line
            else:
                # No change needed (symbol not found)
                return False

            # HYBRID STEP 3: AST validates result is still valid Python
            modified_source = '\n'.join(lines)
            is_valid, _ = self._validate_result_with_ast(modified_source)
            if not is_valid:
                return False  # Don't write invalid Python

            # Write back
            path.write_text(modified_source, encoding='utf-8')
            return True

        except Exception:
            return False

    def _is_multiline_import_continuation(self, lines: List[str], line_idx: int) -> bool:
        """
        Check if a line is part of a multi-line import (inside parentheses).

        Looks backwards for 'from ... import (' pattern without closing ')'.
        """
        # Look backwards for the import statement start
        for i in range(line_idx, max(-1, line_idx - 20), -1):
            line = lines[i].strip()

            # Found closing paren before opening - not in multi-line
            if line.endswith(')') and i != line_idx:
                return False

            # Found opening: from x import (
            if 'import' in line and line.endswith('('):
                return True

            # Found complete single-line import
            if line.startswith('from ') and 'import' in line and '(' not in line:
                return False

        return False

    def _remove_from_multiline_import(
        self,
        path: Path,
        lines: List[str],
        line_idx: int,
        symbol: str
    ) -> bool:
        """
        Remove a symbol from a multi-line import block.

        Handles:
        - from x import (
              A,
              B,   <- remove B
              C,
          )

        Uses item-based parsing for safety (avoids regex comma issues).
        """
        import re

        current_line = lines[line_idx]

        # Check if symbol is on this line (word boundary match)
        if not re.search(rf'\b{re.escape(symbol)}\b', current_line):
            return False

        # Extract indentation
        indent = len(current_line) - len(current_line.lstrip())

        # Parse items on this line (strip comments first)
        line_content = re.sub(r'#.*$', '', current_line)  # Remove comments
        items = [item.strip() for item in line_content.split(',') if item.strip()]

        # Find and remove the symbol (handle 'symbol as alias' pattern)
        new_items = []
        found = False
        for item in items:
            name = item.split()[0] if ' ' in item else item
            if name == symbol:
                found = True  # Skip this item
            else:
                new_items.append(item)

        if not found:
            return False

        if not new_items:
            # All items removed - delete the entire line
            del lines[line_idx]
        else:
            # Reconstruct the line with remaining items
            content = ', '.join(new_items)
            # Add trailing comma (multi-line imports conventionally have trailing commas)
            if not content.endswith(','):
                content += ','
            lines[line_idx] = ' ' * indent + content

        # Write back
        path.write_text('\n'.join(lines), encoding='utf-8')
        return True

    def _remove_symbol_from_import(self, import_line: str, symbol: str) -> Optional[str]:
        """
        Remove a symbol from an import line.

        Handles comma-aware removal for multi-imports.
        Preserves trailing suffixes (semicolons, comments).

        Args:
            import_line: The import line text
            symbol: Symbol to remove

        Returns:
            Modified line, or None if entire line should be deleted
        """
        import re

        # Extract suffix (semicolon, comment) before processing
        clean_line, suffix = self._extract_import_suffix(import_line)
        stripped = clean_line.strip()

        # Case 1: "import symbol" or "import symbol as alias"
        if re.match(rf'^import\s+{re.escape(symbol)}(\s+as\s+\w+)?$', stripped):
            return None  # Delete entire line

        # Case 2: "from x import symbol" (single import)
        if re.match(rf'^from\s+\S+\s+import\s+{re.escape(symbol)}(\s+as\s+\w+)?$', stripped):
            return None  # Delete entire line

        # Case 3: "from x import a, symbol, b" (multi-import)
        # Need to remove symbol and handle commas correctly
        match = re.match(r'^(from\s+\S+\s+import\s+)(.+)$', stripped)
        if match:
            prefix = match.group(1)
            imports_part = match.group(2)

            # Handle parentheses: from x import (a, b, c)
            has_parens = imports_part.startswith('(') and imports_part.endswith(')')
            if has_parens:
                imports_part = imports_part[1:-1]

            # Split by comma, handling "as alias" patterns
            # Pattern: symbol or symbol as alias
            import_items = []
            for item in imports_part.split(','):
                item = item.strip()
                if item:
                    import_items.append(item)

            # Find and remove the symbol
            new_items = []
            for item in import_items:
                # Check if this item is the symbol (with or without alias)
                item_name = item.split()[0] if ' ' in item else item
                if item_name != symbol:
                    new_items.append(item)

            if not new_items:
                return None  # All imports removed, delete line

            if len(new_items) == len(import_items):
                # Symbol not found in this import
                return import_line

            # Reconstruct the line with suffix
            new_imports = ', '.join(new_items)
            if has_parens:
                new_imports = f'({new_imports})'

            # Preserve original indentation and reattach suffix
            indent = len(import_line) - len(import_line.lstrip())
            result = ' ' * indent + prefix + new_imports
            if suffix:
                result += suffix
            return result

        return import_line  # No match, return unchanged

    # =========================================================================
    # AST Validation Helpers (Hybrid approach per [UW-NI])
    # =========================================================================

    def _validate_import_with_ast(
        self,
        source: str,
        line_number: int,
        symbol: str
    ) -> tuple[bool, str]:
        """
        Validate that an import can be safely modified using AST.

        Args:
            source: Full file source code
            line_number: 1-indexed line number of import
            symbol: Symbol to verify exists in import

        Returns:
            (is_valid, error_message) - True if safe to modify
        """
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return False, f"File has syntax error: {e}"

        # Find import statement at the given line
        for node in ast.walk(tree):
            if not hasattr(node, 'lineno'):
                continue

            if node.lineno != line_number:
                continue

            # Check Import: import x, y, z
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == symbol:
                        return True, ""
                return False, f"Symbol '{symbol}' not found in import at line {line_number}"

            # Check ImportFrom: from x import y, z
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == symbol:
                        return True, ""
                return False, f"Symbol '{symbol}' not found in import at line {line_number}"

        return False, f"No import found at line {line_number}"

    def _is_compound_statement(self, line: str) -> bool:
        """
        Detect if line contains code after the import (compound statement).

        Example: 'from os import path; x = 1' -> True (should not modify)

        Returns:
            True if line has code after import (unsafe to modify)
        """
        # Strip the line
        stripped = line.strip()

        # Remove comments first
        comment_idx = stripped.find('#')
        if comment_idx != -1:
            stripped = stripped[:comment_idx].strip()

        # Check for semicolon followed by non-empty content
        # Valid: 'from os import path;' (trailing semicolon only)
        # Invalid: 'from os import path; x = 1' (code after)
        if ';' in stripped:
            parts = stripped.split(';')
            # If any part after the first is non-empty, it's compound
            for part in parts[1:]:
                if part.strip():
                    return True

        return False

    def _extract_import_suffix(self, line: str) -> tuple[str, str]:
        """
        Extract trailing suffix (semicolon and/or comment) from import line.

        Args:
            line: The import line

        Returns:
            (import_part, suffix) where suffix includes ; and # comment with spacing
        """
        # Find comment (preserve spacing before #)
        comment_with_spacing = ""
        comment_idx = line.find('#')
        if comment_idx != -1:
            # Find where the actual content ends (before spacing + comment)
            content_before = line[:comment_idx]
            content_stripped = content_before.rstrip()
            spacing_before_comment = content_before[len(content_stripped):]
            comment_with_spacing = spacing_before_comment + line[comment_idx:]
            line = content_stripped

        # Find trailing semicolon
        semicolon = ""
        if line.rstrip().endswith(';'):
            semicolon = ";"
            line = line.rstrip()[:-1]

        # Rebuild suffix: semicolon first, then spacing + comment
        suffix = ""
        if semicolon:
            suffix += semicolon
        if comment_with_spacing:
            suffix += comment_with_spacing

        return line.rstrip(), suffix

    def _validate_result_with_ast(self, modified_source: str) -> tuple[bool, str]:
        """
        Validate that modified source is still valid Python.

        Args:
            modified_source: Source code after modification

        Returns:
            (is_valid, error_message)
        """
        try:
            ast.parse(modified_source)
            return True, ""
        except SyntaxError as e:
            return False, f"Modification produced invalid Python: {e}"

    # =========================================================================
    # Test Execution (Affected tests only)
    # =========================================================================

    def _find_test_files(self, source_files: List[str]) -> List[str]:
        """
        Find test files related to source files.

        Searches for test files that likely test the modified source files.
        Uses naming conventions: test_<module>.py, <module>_test.py

        Args:
            source_files: List of modified source file paths

        Returns:
            List of test file paths
        """
        test_files = []
        tests_dir = Path.cwd() / "tests"

        for source_file in source_files:
            source_path = Path(source_file)
            module_name = source_path.stem  # e.g., "scanner" from "scanner.py"

            # Look for test files matching this module
            patterns = [
                f"test_{module_name}.py",
                f"{module_name}_test.py",
                f"**/test_{module_name}.py",
                f"**/{module_name}_test.py",
            ]

            if tests_dir.exists():
                for pattern in patterns:
                    for test_file in tests_dir.glob(pattern):
                        if str(test_file) not in test_files:
                            test_files.append(str(test_file))

        return test_files

    def _run_affected_tests(self, files_modified: List[str]) -> Dict[str, Any]:
        """
        Run tests for affected files.

        Args:
            files_modified: List of source files that were modified

        Returns:
            Dict with test results:
            {
                "success": bool,
                "tests_run": int,
                "tests_passed": int,
                "tests_failed": int,
                "test_files": List[str],
                "output": str,
                "error": str (if failed)
            }
        """
        import subprocess

        test_files = self._find_test_files(files_modified)

        if not test_files:
            # No matching test files - consider success (nothing to test)
            return {
                "success": True,
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "test_files": [],
                "output": "No matching test files found",
                "error": None
            }

        try:
            # Run pytest on affected test files
            cmd = ["python3", "-m", "pytest"] + test_files + ["-v", "--tb=short"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(Path.cwd()),
                timeout=120  # 2 minute timeout
            )

            # Parse pytest output for counts
            output = result.stdout + result.stderr
            tests_run = 0
            tests_passed = 0
            tests_failed = 0

            # Look for pytest summary line: "X passed, Y failed"
            import re
            summary_match = re.search(
                r'(\d+)\s+passed',
                output
            )
            if summary_match:
                tests_passed = int(summary_match.group(1))
                tests_run += tests_passed

            failed_match = re.search(
                r'(\d+)\s+failed',
                output
            )
            if failed_match:
                tests_failed = int(failed_match.group(1))
                tests_run += tests_failed

            return {
                "success": result.returncode == 0,
                "tests_run": tests_run,
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "test_files": test_files,
                "output": output[-2000:] if len(output) > 2000 else output,  # Truncate
                "error": None if result.returncode == 0 else f"Tests failed (exit code {result.returncode})"
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "test_files": test_files,
                "output": "",
                "error": "Test execution timed out (120s)"
            }
        except Exception as e:
            return {
                "success": False,
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "test_files": test_files,
                "output": "",
                "error": f"Test execution error: {str(e)}"
            }

    # =========================================================================
    # Auto-Capture (One capture per file for granularity)
    # =========================================================================

    def create_cleanup_captures(
        self,
        files_modified: List[Dict[str, Any]],
        test_results: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Create capture proposals for cleanup operations (one per file).

        Follows HC2: Creates batch proposals for human review.
        Each capture includes: file path, symbols removed, test proof.

        Args:
            files_modified: List of file info dicts from removal result
            test_results: Optional test results to include as proof

        Returns:
            List of capture proposal dicts (for batch queue)
        """
        from ..core.events import propose_structure

        captures = []
        test_proof = None

        # Build test proof string if tests passed
        if test_results and test_results.get("success"):
            test_proof = (
                f"Tests passed: {test_results['tests_passed']}/{test_results['tests_run']} "
                f"in {len(test_results.get('test_files', []))} test file(s)"
            )

        for file_info in files_modified:
            file_path = file_info["file"]
            removals = file_info["removals"]

            # Build symbol list
            symbols_removed = [r["symbol"] for r in removals]
            symbol_list = ", ".join(symbols_removed[:5])
            if len(symbols_removed) > 5:
                symbol_list += f" (+{len(symbols_removed) - 5} more)"

            # Build capture summary
            try:
                rel_path = Path(file_path).relative_to(Path.cwd())
            except ValueError:
                rel_path = file_path

            summary = f"Cleaned {len(symbols_removed)} unused import(s) from {rel_path}"

            # Build detail with symbols and proof
            detail = {
                "what": f"Removed unused imports: {symbol_list}",
                "why": "Automated cleanup verified by hybrid parser (regex + AST)",
                "file": str(file_path),
                "symbols": symbols_removed,
                "lines": [r["line"] for r in removals],
            }

            if test_proof:
                detail["proof"] = test_proof

            # Create proposal event using propose_structure
            # source_id is "cleanup" since this is from automated cleanup
            proposal = propose_structure(
                source_id="cleanup",
                proposed={
                    "type": "decision",
                    "summary": summary,
                    "detail": detail
                },
                confidence=1.0  # High confidence - verified by hybrid parser
            )

            captures.append({
                "proposal": proposal,
                "file": str(file_path),
                "symbols": symbols_removed
            })

        return captures

    def quick_check(self) -> str:
        """
        Quick one-line health status.
        
        For use in prompts or status display.
        """
        context = self._gather_context()
        
        if not context.purpose:
            return "No purpose defined -- run `babel init`"
        
        if not context.decisions:
            return "No decisions captured yet"
        
        # Quick heuristic checks (no LLM)
        issues = []
        
        # Check for constraints without matching decisions
        constraint_topics = set()
        for c in context.constraints:
            keywords = c.get("summary", "").lower().split()
            constraint_topics.update(keywords)
        
        decision_topics = set()
        for d in context.decisions:
            keywords = d.get("summary", "").lower().split()
            decision_topics.update(keywords)
        
        # Very basic coherence check
        if constraint_topics and not (constraint_topics & decision_topics):
            issues.append("constraints may lack supporting decisions")
        
        if len(context.decisions) > 20 and len(context.constraints) == 0:
            issues.append("many decisions but no constraints defined")
        
        if issues:
            return f"Review suggested: {'; '.join(issues)}"
        
        return f"Healthy: {len(context.decisions)} decisions aligned with purpose"
    
    # =========================================================================
    # Context Gathering
    # =========================================================================
    
    def _gather_context(self) -> ScanContext:
        """Gather project context from Babel stores (P3 compliant)."""
        if self._context_cache:
            return self._context_cache
        
        # Get need and purpose (P1: need grounds purpose)
        need = None
        purpose = None
        purpose_nodes = self.graph.get_nodes_by_type("purpose")
        if purpose_nodes:
            latest = purpose_nodes[-1].content
            purpose = latest.get("purpose", "")
            need = latest.get("need")  # P1: Bootstrap from Need
        
        # Get decisions
        decisions = []
        decision_nodes = self.graph.get_nodes_by_type("decision")
        for node in decision_nodes:
            decisions.append(node.content)
        
        # Get constraints
        constraints = []
        constraint_nodes = self.graph.get_nodes_by_type("constraint")
        for node in constraint_nodes:
            constraints.append(node.content)
        
        # Infer tech stack from vocabulary and decisions
        tech_stack = self._infer_tech_stack(decisions)
        
        # Get recent topics
        recent_topics = []
        if self.vocabulary:
            recent_topics = self.vocabulary.list_clusters()
        
        # Event count
        event_count = self.events.count()
        
        # P3: Group decisions by domain for expertise-weighted analysis
        domain_decisions = self._group_by_domain(decisions)
        
        context = ScanContext(
            need=need,
            purpose=purpose,
            decisions=decisions,
            constraints=constraints,
            tech_stack=tech_stack,
            recent_topics=recent_topics,
            event_count=event_count,
            domain_decisions=domain_decisions
        )
        
        self._context_cache = context
        return context
    
    def _group_by_domain(self, decisions: List[Dict]) -> Dict[str, List[Dict]]:
        """Group decisions by domain (P3: expertise-weighted analysis)."""
        from ..core.domains import infer_domain_from_text
        
        grouped: Dict[str, List[Dict]] = {}
        
        for d in decisions:
            # Use explicit domain if present
            domain = d.get("domain")
            
            # Otherwise infer from content
            if not domain:
                summary = d.get("summary", str(d))
                domain = infer_domain_from_text(summary)
            
            if domain:
                if domain not in grouped:
                    grouped[domain] = []
                grouped[domain].append(d)
        
        return grouped
    
    def _infer_tech_stack(self, decisions: List[Dict]) -> List[str]:
        """Infer technology stack from decisions."""
        tech_keywords = {
            "python", "javascript", "typescript", "rust", "go", "java",
            "react", "vue", "angular", "svelte",
            "postgresql", "mysql", "sqlite", "mongodb", "redis",
            "docker", "kubernetes", "aws", "gcp", "azure",
            "rest", "graphql", "grpc"
        }
        
        found = set()
        for d in decisions:
            text = str(d).lower()
            for tech in tech_keywords:
                if tech in text:
                    found.add(tech)
        
        return list(found)
    
    def _hash_context(self, context: ScanContext) -> str:
        """Hash context for cache invalidation."""
        content = json.dumps({
            "purpose": context.purpose,
            "decisions": len(context.decisions),
            "constraints": len(context.constraints),
            "events": context.event_count
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    # =========================================================================
    # Scan Implementations
    # =========================================================================
    
    def _scan_health(self, context: ScanContext, deep: bool) -> ScanResult:
        """Quick health scan."""
        if not self.provider.is_available:
            return self._mock_scan(context, "health")
        
        prompt = self._build_prompt(context, "health", deep)
        response = self.provider.complete(SCAN_SYSTEM_PROMPT, prompt, max_tokens=1500)

        return self._parse_response(response.text, context, "health")
    
    def _scan_architecture(self, context: ScanContext, deep: bool) -> ScanResult:
        """Architecture-focused scan."""
        if not self.provider.is_available:
            return self._mock_scan(context, "architecture")
        
        prompt = self._build_prompt(context, "architecture", deep)
        response = self.provider.complete(ARCHITECTURE_SYSTEM_PROMPT, prompt, max_tokens=2000)

        return self._parse_response(response.text, context, "architecture")
    
    def _scan_security(self, context: ScanContext, deep: bool) -> ScanResult:
        """Security-focused scan."""
        if not self.provider.is_available:
            return self._mock_scan(context, "security")
        
        prompt = self._build_prompt(context, "security", deep)
        response = self.provider.complete(SECURITY_SYSTEM_PROMPT, prompt, max_tokens=2000)

        return self._parse_response(response.text, context, "security")
    
    def _scan_performance(self, context: ScanContext, deep: bool) -> ScanResult:
        """Performance-focused scan."""
        if not self.provider.is_available:
            return self._mock_scan(context, "performance")
        
        prompt = self._build_prompt(context, "performance", deep)
        response = self.provider.complete(PERFORMANCE_SYSTEM_PROMPT, prompt, max_tokens=2000)

        return self._parse_response(response.text, context, "performance")
    
    def _scan_dependencies(self, context: ScanContext, deep: bool) -> ScanResult:
        """Dependencies-focused scan."""
        if not self.provider.is_available:
            return self._mock_scan(context, "dependencies")

        prompt = self._build_prompt(context, "dependencies", deep)
        response = self.provider.complete(DEPENDENCIES_SYSTEM_PROMPT, prompt, max_tokens=1500)

        return self._parse_response(response.text, context, "dependencies")

    def _scan_clean(self, deep: bool = False) -> ScanResult:
        """
        Code cleanup scan using ruff.

        Detects cleanup candidates (no auto-fix - scan informs, human decides):
        - F401: Unused imports (primary target for post-refactoring)
        - F841: Unused variables (deep mode)
        - I001: Unsorted imports (deep mode)
        - ERA001: Commented-out code (deep mode)
        - PIE790: Unnecessary pass statements (deep mode)

        Args:
            deep: Include all cleanup rules (not just unused imports)

        Returns:
            ScanResult with findings from ruff
        """
        import subprocess
        import shutil

        # Check if ruff is available (HC3: graceful fallback)
        ruff_path = shutil.which("ruff")
        if not ruff_path:
            return ScanResult(
                scan_id=f"scan_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                scan_type="clean",
                status="concerns",
                findings=[
                    ScanFinding(
                        severity="warning",
                        category="setup",
                        title="Ruff Not Installed",
                        description="ruff is required for clean scan but not found in PATH.",
                        suggestion="Install with: pip install ruff  or  pip install babel-tool[clean]"
                    )
                ],
                context_hash="",
                summary="Clean scan unavailable: ruff not installed"
            )

        # Build rule selection
        # Normal: just unused imports (safest, most common after refactoring)
        # Deep: include more cleanup rules
        if deep:
            rules = ["F401", "F841", "I001", "ERA001", "PIE790"]
        else:
            rules = ["F401"]  # Unused imports only

        # Build ruff command (no --fix, scan only informs)
        cmd = [
            ruff_path, "check",
            "--output-format", "json",
            "--select", ",".join(rules),
            "."  # Current directory
        ]

        # Run ruff
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(Path.cwd())
            )
            # ruff exits with 1 if findings exist, 0 if clean
            output = result.stdout if result.stdout else result.stderr
        except subprocess.TimeoutExpired:
            return ScanResult(
                scan_id=f"scan_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                scan_type="clean",
                status="concerns",
                findings=[
                    ScanFinding(
                        severity="warning",
                        category="clean",
                        title="Ruff Timeout",
                        description="ruff took too long to complete. Try running on a smaller scope.",
                        suggestion="Run ruff directly with specific paths: ruff check src/"
                    )
                ],
                context_hash="",
                summary="Clean scan timed out"
            )
        except Exception as e:
            return ScanResult(
                scan_id=f"scan_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                scan_type="clean",
                status="concerns",
                findings=[
                    ScanFinding(
                        severity="warning",
                        category="clean",
                        title="Ruff Error",
                        description=f"Error running ruff: {e}",
                        suggestion="Check ruff installation and try again."
                    )
                ],
                context_hash="",
                summary=f"Clean scan failed: {e}"
            )

        # Load exclusions to filter false positives
        exclusions = self._load_exclusions("clean")

        # Parse ruff JSON output
        findings = []
        excluded_count = 0
        try:
            if output.strip():
                ruff_findings = json.loads(output)
                for rf in ruff_findings:
                    # Map ruff finding to ScanFinding
                    code = rf.get("code", "")
                    message = rf.get("message", "")
                    filename = rf.get("filename", "")
                    location = rf.get("location", {})
                    row = location.get("row", 0)

                    # Extract symbol name from message (e.g., "`foo` imported but unused")
                    symbol = None
                    if "`" in message:
                        # Extract text between backticks
                        parts = message.split("`")
                        if len(parts) >= 2:
                            full_symbol = parts[1]
                            # Extract just the base name (e.g., ".config.get_config" -> "get_config")
                            # This matches what appears in the import statement
                            symbol = full_symbol.split(".")[-1] if "." in full_symbol else full_symbol

                    # Generate deterministic finding ID
                    finding_id = self._generate_finding_id(filename, row, code)

                    # Skip excluded findings (false positives)
                    if self._is_excluded(finding_id, exclusions):
                        excluded_count += 1
                        continue

                    # Determine severity based on rule and fix applicability
                    fix_info = rf.get("fix")
                    if fix_info and fix_info.get("applicability") == "safe":
                        severity = "info"  # Safe to auto-fix
                    else:
                        severity = "warning"

                    # Map code to category
                    category_map = {
                        "F401": "unused-import",
                        "F841": "unused-variable",
                        "I001": "import-order",
                        "ERA001": "dead-code",
                        "PIE790": "unnecessary-code",
                    }
                    category = category_map.get(code, "clean")

                    # Build description with location
                    location_str = f"{filename}:{row}" if filename else ""
                    description = f"{message}"
                    if location_str:
                        description = f"[{location_str}] {description}"

                    # Build suggestion (no auto-fix, human reviews)
                    if fix_info and fix_info.get("applicability") == "safe":
                        suggestion = f"Safe to remove. Run: ruff check --fix --select {code}"
                    else:
                        suggestion = f"Review and remove manually."

                    findings.append(ScanFinding(
                        severity=severity,
                        category=category,
                        title=f"{code}: {self._ruff_code_title(code)}",
                        description=description,
                        suggestion=suggestion,
                        # Extended fields for management
                        finding_id=finding_id,
                        file=filename,
                        line=row,
                        code=code,
                        symbol=symbol,
                        status="pending"
                    ))
        except json.JSONDecodeError:
            # If JSON parsing fails, ruff might have output text errors
            if output.strip():
                findings.append(ScanFinding(
                    severity="warning",
                    category="clean",
                    title="Ruff Output Parse Error",
                    description=f"Could not parse ruff output: {output[:200]}",
                    suggestion="Run ruff directly: ruff check ."
                ))

        # Link findings to symbols (provides context for AI review)
        if findings:
            self._link_findings_to_symbols(findings)

        # Determine status and build summary
        if not findings:
            status = "healthy"
            summary = "No cleanup needed" + (" (deep scan)" if deep else " (unused imports only)")
            if excluded_count > 0:
                summary += f" ({excluded_count} excluded)"
        else:
            status = "concerns"
            summary = f"Found {len(findings)} cleanup candidate(s)" + (" (deep scan)" if deep else "")
            if excluded_count > 0:
                summary += f" ({excluded_count} excluded)"

        # Persist findings for management (validate/invalidate/resolve workflow)
        self._save_findings("clean", findings)

        return ScanResult(
            scan_id=f"scan_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            scan_type="clean",
            status=status,
            findings=findings,
            context_hash="",  # Clean scan doesn't use context
            summary=summary
        )

    def _ruff_code_title(self, code: str) -> str:
        """Get human-readable title for ruff rule code."""
        titles = {
            "F401": "Unused import",
            "F841": "Unused variable",
            "I001": "Unsorted imports",
            "ERA001": "Commented-out code",
            "PIE790": "Unnecessary pass",
        }
        return titles.get(code, code)

    def _scan_query(self, context: ScanContext, query: str) -> ScanResult:
        """Answer specific question."""
        if not self.provider.is_available:
            return self._mock_scan(context, "query", query)
        
        prompt = f"""{context.to_prompt()}

QUESTION: {query}

Analyze this question in the context of the project above.
Provide a direct answer that references specific decisions and constraints.
"""
        
        response = self.provider.complete(QUERY_SYSTEM_PROMPT, prompt, max_tokens=1500)

        return self._parse_response(response.text, context, "query")
    
    def _build_prompt(self, context: ScanContext, scan_type: str, deep: bool) -> str:
        """Build scan prompt."""
        depth = "comprehensive" if deep else "quick"
        
        return f"""{context.to_prompt()}

Perform a {depth} {scan_type} review.

{"Analyze all aspects thoroughly." if deep else "Focus on top 3 most important findings."}

Return JSON:
{{
    "status": "healthy" | "concerns" | "issues",
    "summary": "one-line summary",
    "findings": [
        {{
            "severity": "info" | "warning" | "concern" | "critical",
            "category": "{scan_type}",
            "title": "short title",
            "description": "what and why, referencing decisions",
            "suggestion": "actionable recommendation"
        }}
    ]
}}
"""
    
    def _parse_response(self, response: str, context: ScanContext, scan_type: str) -> ScanResult:
        """Parse LLM response into ScanResult."""
        try:
            # Extract JSON from response
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            
            data = json.loads(json_str.strip())
            
            findings = [
                ScanFinding.from_dict(f)
                for f in data.get("findings", [])
            ]
            
            return ScanResult(
                scan_id=f"scan_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                scan_type=scan_type,
                status=data.get("status", "healthy"),
                findings=findings,
                context_hash=self._hash_context(context),
                summary=data.get("summary", "Scan complete")
            )
        except (json.JSONDecodeError, KeyError, IndexError):
            # Fallback for non-JSON response
            return ScanResult(
                scan_id=f"scan_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                scan_type=scan_type,
                status="healthy",
                findings=[
                    ScanFinding(
                        severity="info",
                        category=scan_type,
                        title="Analysis Complete",
                        description=response[:500],
                        suggestion="Review the analysis above."
                    )
                ],
                context_hash=self._hash_context(context),
                summary="Scan complete"
            )
    
    def _mock_scan(self, context: ScanContext, scan_type: str, query: str = None) -> ScanResult:
        """Mock scan when LLM unavailable."""
        findings = []
        
        # Basic heuristic findings
        if not context.purpose:
            findings.append(ScanFinding(
                severity="warning",
                category="setup",
                title="No Purpose Defined",
                description="Project has no declared purpose. This makes it hard to evaluate decisions.",
                suggestion="Run `babel init \"your purpose\"` to set project purpose."
            ))
        
        if context.decisions and not context.constraints:
            findings.append(ScanFinding(
                severity="info",
                category="architecture",
                title="No Constraints Defined",
                description=f"Project has {len(context.decisions)} decisions but no constraints.",
                suggestion="Consider defining constraints to guide future decisions."
            ))
        
        if len(context.decisions) > 30:
            findings.append(ScanFinding(
                severity="info",
                category="maintenance",
                title="Many Decisions",
                description=f"Project has {len(context.decisions)} decisions. Consider reviewing for coherence.",
                suggestion="Run `babel coherence` to check alignment."
            ))
        
        status = "healthy" if not findings else "concerns"
        summary = f"Basic scan: {len(findings)} finding(s) (LLM unavailable for deep analysis)"
        
        return ScanResult(
            scan_id=f"scan_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            scan_type=scan_type,
            status=status,
            findings=findings,
            context_hash=self._hash_context(context),
            summary=summary
        )
    
    # =========================================================================
    # Findings Storage (for clean scan management)
    # =========================================================================

    def _get_scan_storage_path(self, scan_type: str) -> Path:
        """Get storage directory for scan type findings.

        Returns: .babel/scan/<type>/
        """
        if self.cache_path:
            # cache_path is typically .babel/scan_cache.json
            # We want .babel/scan/<type>/
            babel_root = self.cache_path.parent
        else:
            babel_root = Path.cwd() / ".babel"

        return babel_root / "scan" / scan_type

    def _generate_finding_id(self, file: str, line: int, code: str) -> str:
        """Generate deterministic ID for a finding.

        Uses file:line:code to create stable ID that persists across scans.
        This allows validate/invalidate/resolve to reference specific findings.
        """
        content = f"{file}:{line}:{code}"
        return hashlib.sha256(content.encode()).hexdigest()[:12]

    def _load_findings(self, scan_type: str) -> List[ScanFinding]:
        """Load persisted findings for scan type."""
        storage_path = self._get_scan_storage_path(scan_type)
        findings_file = storage_path / "findings.json"

        if not findings_file.exists():
            return []

        try:
            data = json.loads(findings_file.read_text())
            return [ScanFinding.from_dict(f) for f in data.get("findings", [])]
        except (json.JSONDecodeError, IOError):
            return []

    def _save_findings(self, scan_type: str, findings: List[ScanFinding]) -> None:
        """Persist findings for scan type."""
        storage_path = self._get_scan_storage_path(scan_type)
        storage_path.mkdir(parents=True, exist_ok=True)
        findings_file = storage_path / "findings.json"

        data = {
            "scan_type": scan_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "findings": [f.to_dict() for f in findings]
        }

        try:
            findings_file.write_text(json.dumps(data, indent=2))
        except IOError:
            pass  # Graceful failure

    def _load_exclusions(self, scan_type: str) -> Dict[str, Dict[str, Any]]:
        """Load exclusions for scan type.

        Returns: Dict mapping finding_id to exclusion info:
            {finding_id: {"reason": "...", "excluded_at": "...", "file": "...", ...}}
        """
        storage_path = self._get_scan_storage_path(scan_type)
        exclusions_file = storage_path / "exclusions.json"

        if not exclusions_file.exists():
            return {}

        try:
            data = json.loads(exclusions_file.read_text())
            return data.get("exclusions", {})
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_exclusions(self, scan_type: str, exclusions: Dict[str, Dict[str, Any]]) -> None:
        """Persist exclusions for scan type."""
        storage_path = self._get_scan_storage_path(scan_type)
        storage_path.mkdir(parents=True, exist_ok=True)
        exclusions_file = storage_path / "exclusions.json"

        data = {
            "scan_type": scan_type,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "exclusions": exclusions
        }

        try:
            exclusions_file.write_text(json.dumps(data, indent=2))
        except IOError:
            pass  # Graceful failure

    def _is_excluded(self, finding_id: str, exclusions: Dict[str, Dict[str, Any]]) -> bool:
        """Check if a finding is excluded (supports prefix matching)."""
        # Check both exact match and prefix match
        if finding_id in exclusions:
            return True
        # Check if any exclusion key is a prefix of finding_id
        for excl_id in exclusions:
            if finding_id.startswith(excl_id):
                return True
        return False

    def _find_containing_symbol(self, file_path: str, line: int) -> Optional[str]:
        """Find the symbol containing a specific line.

        Queries graph for code_symbol nodes and finds the one
        that contains the given line (line_start <= line <= line_end).

        Args:
            file_path: Relative file path
            line: Line number (1-indexed)

        Returns:
            Symbol qualified name or None if not found
        """
        code_symbols = self.graph.get_nodes_by_type("code_symbol")

        best_match = None
        best_range = float('inf')

        for node in code_symbols:
            content = node.content
            sym_file = content.get('file_path', '')

            # Normalize paths for comparison
            if not sym_file or not file_path:
                continue

            # Check if file matches (handle relative paths)
            if not (sym_file == file_path or file_path.endswith(sym_file) or sym_file.endswith(file_path)):
                continue

            line_start = content.get('line_start', 0)
            line_end = content.get('line_end', 0)

            # Check if line is within symbol range
            if line_start <= line <= line_end:
                # Prefer smallest containing symbol (most specific)
                range_size = line_end - line_start
                if range_size < best_range:
                    best_match = content.get('qualified_name')
                    best_range = range_size

        return best_match

    def _find_linked_decisions(self, symbol_name: str) -> List[str]:
        """Find decisions linked to a symbol.

        Note: Per architecture [PI-XM], code symbols do NOT have explicit
        edges to decisions. Linking is done dynamically via semantic matching.
        This method returns empty list - the linked_decisions field is
        reserved for future semantic matching integration.

        Args:
            symbol_name: Symbol qualified name

        Returns:
            Empty list (no explicit edges exist by design)
        """
        # Code symbols are cache, not intent [PI-XM]
        # No explicit edges exist between code_symbols and decisions
        # Matching is done dynamically via semantic/keyword matching in `babel why`
        return []

    def _link_findings_to_symbols(self, findings: List[ScanFinding]) -> None:
        """Enrich findings with containing symbol and linked decisions.

        Modifies findings in place to add:
        - containing_symbol: The symbol (class/function) containing the finding
        - linked_decisions: Decisions linked to that symbol

        This provides context for AI review of findings.
        """
        for finding in findings:
            if not finding.file or not finding.line:
                continue

            # Find containing symbol
            containing = self._find_containing_symbol(finding.file, finding.line)
            if containing:
                finding.containing_symbol = containing

                # Find linked decisions for that symbol
                decisions = self._find_linked_decisions(containing)
                if decisions:
                    finding.linked_decisions = decisions

    # =========================================================================
    # Caching
    # =========================================================================

    def _load_cache(self, scan_type: str, context_hash: str) -> Optional[ScanResult]:
        """Load cached scan result if valid."""
        if not self.cache_path or not self.cache_path.exists():
            return None
        
        try:
            data = json.loads(self.cache_path.read_text())
            cached = data.get(scan_type)
            
            if cached and cached.get("context_hash") == context_hash:
                result = ScanResult.from_dict(cached)
                return result
        except (json.JSONDecodeError, KeyError):
            pass
        
        return None
    
    def _save_cache(self, result: ScanResult):
        """Save scan result to cache."""
        if not self.cache_path:
            return
        
        try:
            if self.cache_path.exists():
                data = json.loads(self.cache_path.read_text())
            else:
                data = {}
            
            data[result.scan_type] = result.to_dict()
            
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(data, indent=2))
        except (json.JSONDecodeError, IOError):
            pass


# =============================================================================
# System Prompts
# =============================================================================

SCAN_SYSTEM_PROMPT = """You are a senior technical advisor reviewing a software project.

You have access to the project's PURPOSE, DECISIONS, and CONSTRAINTS from Babel.

Your role:
1. Validate alignment between implementation and stated intent
2. Identify conflicts between decisions and constraints
3. Surface risks specific to THIS project's context
4. Suggest improvements that RESPECT existing decisions

Rules:
- Reference specific decisions when making observations
- Acknowledge when choices are appropriate for the context
- Prioritize findings by impact on stated purpose
- Every concern needs an actionable suggestion
- Be constructive, not alarmist

Return valid JSON with status, summary, and findings array."""

ARCHITECTURE_SYSTEM_PROMPT = """You are a senior software architect reviewing a project's design.

Given the project's PURPOSE, DECISIONS, and CONSTRAINTS from Babel:

Focus on:
1. Design pattern appropriateness for stated purpose
2. Structural alignment with constraints
3. Scalability given tech choices
4. Separation of concerns
5. Dependency direction

Reference specific decisions. Suggest patterns that fit the existing architecture.

Return valid JSON with status, summary, and findings array."""

SECURITY_SYSTEM_PROMPT = """You are a security engineer reviewing a project.

Given the project's PURPOSE, DECISIONS, and CONSTRAINTS from Babel:

Focus on:
1. Data handling relative to stated constraints
2. Authentication/authorization patterns
3. Input validation coverage
4. Dependency security implications
5. Secrets management

Reference specific decisions. Consider the project's actual threat model based on its purpose.

Return valid JSON with status, summary, and findings array."""

PERFORMANCE_SYSTEM_PROMPT = """You are a performance engineer reviewing a project.

Given the project's PURPOSE, DECISIONS, and CONSTRAINTS from Babel:

Focus on:
1. Bottleneck risks given tech choices
2. Scalability alignment with purpose
3. Resource efficiency
4. Caching opportunities
5. Query patterns

Reference specific decisions. Consider actual load expectations based on purpose.

Return valid JSON with status, summary, and findings array."""

DEPENDENCIES_SYSTEM_PROMPT = """You are reviewing a project's dependencies.

Given the project's PURPOSE, DECISIONS, and CONSTRAINTS from Babel:

Focus on:
1. Dependency necessity relative to purpose
2. Maintenance burden vs. value
3. Security update priority
4. Bundle size impact (if relevant)
5. Upgrade paths

Reference why each dependency was likely chosen. Suggest removals only if purpose allows.

Return valid JSON with status, summary, and findings array."""

QUERY_SYSTEM_PROMPT = """You are answering a specific technical question about a project.

You have context from Babel: the project's PURPOSE, DECISIONS, and CONSTRAINTS.

Answer the question directly, referencing specific decisions.
Explain how the answer relates to the project's stated purpose.
If the question reveals a gap or concern, suggest how to address it.

Return valid JSON with status, summary, and a single finding that answers the question."""


# =============================================================================
# Formatting
# =============================================================================

def format_scan_result(result: ScanResult, verbose: bool = False) -> str:
    """Format scan result for display."""
    symbols = get_symbols()
    lines = []

    # Status header
    status_icon = {
        "healthy": symbols.check_pass,
        "concerns": symbols.check_warn,
        "issues": symbols.check_fail
    }.get(result.status, "?")
    
    lines.append(f"{status_icon} {result.summary}")
    lines.append("")
    
    if not result.findings:
        lines.append("No findings.")
        return "\n".join(lines)
    
    # Group by severity
    critical = [f for f in result.findings if f.severity == "critical"]
    concerns = [f for f in result.findings if f.severity in ("concern", "warning")]
    info = [f for f in result.findings if f.severity == "info"]
    
    def format_finding(f: ScanFinding, index: int) -> List[str]:
        finding_lines = []
        severity_icon = {
            "critical": symbols.check_fail,
            "concern": symbols.check_warn,
            "warning": symbols.check_warn,
            "info": "[i]"
        }.get(f.severity, symbols.bullet)

        finding_lines.append(f"{index}. {severity_icon} {f.title}")
        finding_lines.append(f"   {f.description}")
        finding_lines.append(f"   {symbols.arrow} {f.suggestion}")
        finding_lines.append("")
        return finding_lines
    
    index = 1
    
    if critical:
        lines.append("CRITICAL:")
        for f in critical:
            lines.extend(format_finding(f, index))
            index += 1
    
    if concerns:
        if critical:
            lines.append("CONCERNS:")
        for f in concerns:
            lines.extend(format_finding(f, index))
            index += 1
    
    if info and verbose:
        lines.append("INFO:")
        for f in info:
            lines.extend(format_finding(f, index))
            index += 1
    elif info and not verbose:
        lines.append(f"({len(info)} additional info items -- use --verbose to see)")
    
    return "\n".join(lines)
