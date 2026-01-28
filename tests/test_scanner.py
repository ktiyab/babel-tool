"""
Tests for scanner module

Context-aware technical advisor using Babel's knowledge.
"""

import pytest
import json

from babel.services.scanner import (
    Scanner, ScanResult, ScanFinding, ScanContext,
    format_scan_result
)
from babel.core.events import DualEventStore
from babel.core.graph import GraphStore
from babel.services.providers import MockProvider
from babel.core.loader import LazyLoader
from babel.core.refs import RefStore
from babel.core.vocabulary import Vocabulary


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_provider():
    """Create mock LLM provider."""
    return MockProvider()


@pytest.fixture
def setup_scanner(tmp_path, mock_provider):
    """Create scanner with test data."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    babel_dir = project_dir / ".babel"
    babel_dir.mkdir()
    (babel_dir / "shared").mkdir()
    
    events = DualEventStore(project_dir)
    graph = GraphStore(babel_dir / "graph.db")
    refs = RefStore(babel_dir)
    vocab = Vocabulary(babel_dir)
    loader = LazyLoader(events, refs, graph, vocab)
    
    scanner = Scanner(
        events=events,
        graph=graph,
        provider=mock_provider,
        loader=loader,
        vocabulary=vocab,
        cache_path=babel_dir / "scan_cache.json"
    )
    
    return scanner, events, graph


# =============================================================================
# ScanContext Tests
# =============================================================================

class TestScanContext:
    """Test scan context model."""
    
    def test_to_prompt_with_need_and_purpose(self):
        """Context formats need and purpose correctly (P1 compliance)."""
        context = ScanContext(
            need="Field workers lose data when connectivity drops",
            purpose="Build offline-first app",
            decisions=[{"summary": "Use SQLite"}],
            constraints=[{"summary": "Must work offline"}],
            tech_stack=["sqlite", "react"],
            recent_topics=["database", "offline"],
            event_count=10,
            domain_decisions={}
        )
        
        prompt = context.to_prompt()
        
        assert "NEED" in prompt
        assert "Field workers lose data" in prompt
        assert "PURPOSE" in prompt
        assert "Build offline-first app" in prompt
        assert "Use SQLite" in prompt
    
    def test_to_prompt_purpose_only(self):
        """Context works with purpose only (backward compatible)."""
        context = ScanContext(
            need=None,
            purpose="Build offline-first app",
            decisions=[{"summary": "Use SQLite"}],
            constraints=[{"summary": "Must work offline"}],
            tech_stack=["sqlite", "react"],
            recent_topics=["database", "offline"],
            event_count=10,
            domain_decisions={}
        )
        
        prompt = context.to_prompt()
        
        assert "PURPOSE" in prompt
        assert "Build offline-first app" in prompt
        assert "NEED" not in prompt  # Should not appear if None
    
    def test_to_prompt_empty(self):
        """Context handles empty state."""
        context = ScanContext(
            need=None,
            purpose=None,
            decisions=[],
            constraints=[],
            tech_stack=[],
            recent_topics=[],
            event_count=0,
            domain_decisions={}
        )
        
        prompt = context.to_prompt()
        
        # Should not crash, may be empty or minimal
        assert isinstance(prompt, str)
    
    def test_to_prompt_with_domain_tags(self):
        """Context includes domain tags in decisions (P3 compliance)."""
        decisions = [{"summary": "Use bcrypt", "domain": "security"}]
        context = ScanContext(
            need=None,
            purpose="Test",
            decisions=decisions,
            constraints=[],
            tech_stack=[],
            recent_topics=[],
            event_count=1,
            domain_decisions={"security": decisions}
        )
        
        prompt = context.to_prompt()
        
        assert "[security]" in prompt
        assert "Use bcrypt" in prompt


# =============================================================================
# ScanFinding Tests
# =============================================================================

class TestScanFinding:
    """Test scan finding model."""
    
    def test_to_dict(self):
        """Finding serializes correctly."""
        finding = ScanFinding(
            severity="warning",
            category="architecture",
            title="Test Finding",
            description="Test description",
            suggestion="Test suggestion",
            references=["decision_123"]
        )
        
        data = finding.to_dict()
        
        assert data["severity"] == "warning"
        assert data["title"] == "Test Finding"
        assert "decision_123" in data["references"]
    
    def test_from_dict(self):
        """Finding deserializes correctly."""
        data = {
            "severity": "critical",
            "category": "security",
            "title": "Security Issue",
            "description": "Description",
            "suggestion": "Fix it"
        }
        
        finding = ScanFinding.from_dict(data)
        
        assert finding.severity == "critical"
        assert finding.category == "security"


# =============================================================================
# ScanResult Tests
# =============================================================================

class TestScanResult:
    """Test scan result model."""
    
    def test_has_concerns(self):
        """Result correctly identifies concerns."""
        result = ScanResult(
            scan_id="test",
            timestamp="2025-01-14",
            scan_type="health",
            status="concerns",
            findings=[
                ScanFinding(
                    severity="warning",
                    category="test",
                    title="Warning",
                    description="",
                    suggestion=""
                )
            ],
            context_hash="abc",
            summary="Test"
        )
        
        assert result.has_concerns
    
    def test_no_concerns(self):
        """Result correctly identifies healthy state."""
        result = ScanResult(
            scan_id="test",
            timestamp="2025-01-14",
            scan_type="health",
            status="healthy",
            findings=[
                ScanFinding(
                    severity="info",
                    category="test",
                    title="Info",
                    description="",
                    suggestion=""
                )
            ],
            context_hash="abc",
            summary="Test"
        )
        
        assert not result.has_concerns
    
    def test_critical_count(self):
        """Result counts critical findings."""
        result = ScanResult(
            scan_id="test",
            timestamp="2025-01-14",
            scan_type="security",
            status="issues",
            findings=[
                ScanFinding(severity="critical", category="security", 
                           title="Critical", description="", suggestion=""),
                ScanFinding(severity="critical", category="security",
                           title="Critical 2", description="", suggestion=""),
                ScanFinding(severity="concern", category="security",
                           title="Concern", description="", suggestion=""),
            ],
            context_hash="abc",
            summary="Test"
        )
        
        assert result.critical_count == 2
        assert result.concern_count == 3


# =============================================================================
# Scanner Tests
# =============================================================================

class TestScanner:
    """Test scanner core functionality."""
    
    def test_quick_check_no_purpose(self, setup_scanner):
        """Quick check handles missing purpose."""
        scanner, events, graph = setup_scanner
        
        status = scanner.quick_check()
        
        assert "No purpose" in status or "babel init" in status
    
    def test_quick_check_with_purpose(self, setup_scanner):
        """Quick check works with purpose."""
        scanner, events, graph = setup_scanner
        
        # Add purpose to graph
        from babel.core.events import declare_purpose
        purpose_event = declare_purpose("Build a great app")
        events.append(purpose_event)
        graph._project_event(purpose_event)
        
        # Clear cached context
        scanner._context_cache = None
        
        status = scanner.quick_check()
        
        assert "No purpose" not in status
    
    def test_scan_health_mock(self, setup_scanner):
        """Health scan works with mock provider."""
        scanner, events, graph = setup_scanner
        
        result = scanner.scan(scan_type="health")
        
        assert result.scan_type == "health"
        assert isinstance(result.findings, list)
    
    def test_scan_with_query(self, setup_scanner):
        """Query scan accepts question."""
        scanner, events, graph = setup_scanner
        
        result = scanner.scan(query="Is my database choice good?")
        
        assert result.scan_type == "query"
    
    def test_gather_context(self, setup_scanner):
        """Scanner gathers context from stores."""
        scanner, events, graph = setup_scanner
        
        # Add some data
        from babel.core.events import declare_purpose, confirm_artifact
        
        purpose_event = declare_purpose("Build offline app")
        events.append(purpose_event)
        graph._project_event(purpose_event)
        
        decision_event = confirm_artifact(
            proposal_id="prop_1",
            artifact_type="decision",
            content={"summary": "Use SQLite for storage"}
        )
        events.append(decision_event)
        graph._project_event(decision_event)
        
        # Clear cache
        scanner._context_cache = None
        
        context = scanner._gather_context()
        
        assert context.purpose == "Build offline app"
        assert len(context.decisions) > 0
    
    def test_infer_tech_stack(self, setup_scanner):
        """Scanner infers tech stack from decisions."""
        scanner, events, graph = setup_scanner
        
        decisions = [
            {"summary": "Use PostgreSQL for the database"},
            {"summary": "Build frontend with React"},
            {"summary": "Deploy on AWS"}
        ]
        
        tech = scanner._infer_tech_stack(decisions)
        
        assert "postgresql" in tech
        assert "react" in tech
        assert "aws" in tech


class TestScannerCaching:
    """Test scanner caching behavior."""
    
    def test_caches_result(self, setup_scanner):
        """Scanner caches scan results."""
        scanner, events, graph = setup_scanner
        
        # First scan
        result1 = scanner.scan(scan_type="health")
        
        # Second scan should use cache (context unchanged)
        result2 = scanner.scan(scan_type="health")
        
        # Results should have same context hash
        assert result1.context_hash == result2.context_hash
    
    def test_cache_invalidates_on_change(self, setup_scanner):
        """Cache invalidates when context changes."""
        scanner, events, graph = setup_scanner
        
        # First scan
        result1 = scanner.scan(scan_type="health")
        hash1 = result1.context_hash
        
        # Add new event
        from babel.core.events import declare_purpose
        purpose_event = declare_purpose("New purpose")
        events.append(purpose_event)
        graph._project_event(purpose_event)
        
        # Clear context cache
        scanner._context_cache = None
        
        # New scan should have different hash
        result2 = scanner.scan(scan_type="health", deep=True)  # deep bypasses cache
        
        # Context changed, so hash should differ
        assert result2.context_hash != hash1


class TestScannerMockMode:
    """Test scanner behavior with mock provider."""
    
    def test_mock_provider_returns_result(self, setup_scanner):
        """Scan with mock provider returns valid result."""
        scanner, events, graph = setup_scanner
        
        result = scanner.scan(scan_type="health")
        
        # Should return a valid result structure
        assert result.scan_type == "health"
        assert result.scan_id.startswith("scan_")
        assert result.context_hash
    
    def test_quick_check_detects_no_purpose(self, setup_scanner):
        """Quick check detects missing purpose."""
        scanner, events, graph = setup_scanner
        
        status = scanner.quick_check()
        
        # Should mention no purpose or babel init
        assert "No purpose" in status or "babel init" in status
    
    def test_quick_check_with_many_decisions(self, setup_scanner):
        """Quick check works with many decisions."""
        scanner, events, graph = setup_scanner
        
        # Add purpose and many decisions
        from babel.core.events import declare_purpose, confirm_artifact
        
        purpose_event = declare_purpose("Test project")
        events.append(purpose_event)
        graph._project_event(purpose_event)
        
        for i in range(35):
            decision_event = confirm_artifact(
                proposal_id=f"prop_{i}",
                artifact_type="decision",
                content={"summary": f"Decision {i}"}
            )
            events.append(decision_event)
            graph._project_event(decision_event)
        
        scanner._context_cache = None
        
        status = scanner.quick_check()
        
        # Should return a status string
        assert isinstance(status, str)
        assert len(status) > 0


# =============================================================================
# Formatting Tests
# =============================================================================

class TestFormatScanResult:
    """Test scan result formatting."""
    
    def test_format_healthy(self):
        """Formats healthy result correctly."""
        result = ScanResult(
            scan_id="test",
            timestamp="2025-01-14",
            scan_type="health",
            status="healthy",
            findings=[],
            context_hash="abc",
            summary="All good"
        )
        
        output = format_scan_result(result)
        
        assert "✓" in output
        assert "All good" in output
    
    def test_format_concerns(self):
        """Formats concerns correctly."""
        result = ScanResult(
            scan_id="test",
            timestamp="2025-01-14",
            scan_type="health",
            status="concerns",
            findings=[
                ScanFinding(
                    severity="warning",
                    category="test",
                    title="Warning Title",
                    description="Warning description",
                    suggestion="Fix suggestion"
                )
            ],
            context_hash="abc",
            summary="Some concerns"
        )
        
        output = format_scan_result(result)
        
        assert "⚠" in output
        assert "Warning Title" in output
        assert "Fix suggestion" in output
    
    def test_format_verbose_shows_info(self):
        """Verbose mode shows info findings."""
        result = ScanResult(
            scan_id="test",
            timestamp="2025-01-14",
            scan_type="health",
            status="healthy",
            findings=[
                ScanFinding(
                    severity="info",
                    category="test",
                    title="Info Title",
                    description="Info description",
                    suggestion="Info suggestion"
                )
            ],
            context_hash="abc",
            summary="Healthy"
        )
        
        # Non-verbose should hide info
        output_brief = format_scan_result(result, verbose=False)
        assert "Info Title" not in output_brief
        
        # Verbose should show info
        output_verbose = format_scan_result(result, verbose=True)
        assert "Info Title" in output_verbose


# =============================================================================
# Integration Tests
# =============================================================================

class TestScannerIntegration:
    """Test scanner with full system."""
    
    def test_scan_with_decisions_and_constraints(self, setup_scanner):
        """Full scan with decisions and constraints."""
        scanner, events, graph = setup_scanner
        
        from babel.core.events import declare_purpose, confirm_artifact
        
        # Add purpose
        purpose_event = declare_purpose("Build secure offline banking app")
        events.append(purpose_event)
        graph._project_event(purpose_event)
        
        # Add decisions
        decision1 = confirm_artifact(
            proposal_id="prop_1",
            artifact_type="decision",
            content={"summary": "Use SQLite for local storage"}
        )
        events.append(decision1)
        graph._project_event(decision1)
        
        decision2 = confirm_artifact(
            proposal_id="prop_2",
            artifact_type="decision",
            content={"summary": "Implement JWT authentication"}
        )
        events.append(decision2)
        graph._project_event(decision2)
        
        # Add constraint (as a decision with constraint type)
        constraint = confirm_artifact(
            proposal_id="prop_3",
            artifact_type="constraint",
            content={"summary": "All data must be encrypted at rest"}
        )
        events.append(constraint)
        graph._project_event(constraint)
        
        scanner._context_cache = None
        
        # Run scan
        result = scanner.scan(scan_type="health")
        
        # Should complete without error
        assert result.scan_type == "health"
        assert result.context_hash  # Should have context
    
    def test_different_scan_types(self, setup_scanner):
        """Different scan types produce different results."""
        scanner, events, graph = setup_scanner
        
        from babel.core.events import declare_purpose
        purpose_event = declare_purpose("Test app")
        events.append(purpose_event)
        graph._project_event(purpose_event)
        scanner._context_cache = None
        
        # Run different scan types
        health = scanner.scan(scan_type="health")
        arch = scanner.scan(scan_type="architecture")
        security = scanner.scan(scan_type="security")
        
        assert health.scan_type == "health"
        assert arch.scan_type == "architecture"
        assert security.scan_type == "security"


# =============================================================================
# Clean Scan Verification Tests (Hybrid Parser)
# =============================================================================

from babel.services.scanner import VERIFIED_TRUE, VERIFIED_FALSE, UNCERTAIN
from unittest.mock import patch, Mock


@pytest.fixture
def temp_python_file(tmp_path):
    """Create a temporary Python file for testing."""
    def _create(content: str, name: str = "test_module.py"):
        file_path = tmp_path / name
        file_path.write_text(content, encoding='utf-8')
        return file_path
    return _create


class TestIsInitReexport:
    """Test _is_init_reexport pattern detection."""

    def test_detects_init_reexport(self, setup_scanner):
        """Detects top-level import in __init__.py as re-export."""
        scanner, _, _ = setup_scanner

        lines = [
            "from .module import SomeClass",
            "",
            "def some_function():",
            "    pass"
        ]

        result = scanner._is_init_reexport("pkg/__init__.py", 1, lines)

        assert result is True

    def test_ignores_non_init_files(self, setup_scanner):
        """Does not flag imports in non-__init__.py files."""
        scanner, _, _ = setup_scanner

        lines = ["from typing import List"]

        result = scanner._is_init_reexport("pkg/module.py", 1, lines)

        assert result is False

    def test_ignores_indented_imports(self, setup_scanner):
        """Does not flag indented imports (inside functions)."""
        scanner, _, _ = setup_scanner

        lines = [
            "def foo():",
            "    from typing import List",
            "    return []"
        ]

        result = scanner._is_init_reexport("pkg/__init__.py", 2, lines)

        assert result is False

    def test_handles_invalid_line_number(self, setup_scanner):
        """Handles out-of-bounds line numbers gracefully."""
        scanner, _, _ = setup_scanner

        lines = ["import os"]

        assert scanner._is_init_reexport("__init__.py", 0, lines) is False
        assert scanner._is_init_reexport("__init__.py", 999, lines) is False


class TestIsInAllList:
    """Test _is_in_all_list pattern detection."""

    def test_detects_symbol_in_all(self, setup_scanner):
        """Detects symbol listed in __all__."""
        scanner, _, _ = setup_scanner

        content = '__all__ = ["foo", "bar", "baz"]'

        assert scanner._is_in_all_list(content, "foo") is True
        assert scanner._is_in_all_list(content, "bar") is True
        assert scanner._is_in_all_list(content, "baz") is True

    def test_ignores_unlisted_symbol(self, setup_scanner):
        """Returns False for symbols not in __all__."""
        scanner, _, _ = setup_scanner

        content = '__all__ = ["foo", "bar"]'

        assert scanner._is_in_all_list(content, "baz") is False

    def test_handles_single_quotes(self, setup_scanner):
        """Handles single-quoted strings in __all__."""
        scanner, _, _ = setup_scanner

        content = "__all__ = ['foo', 'bar']"

        assert scanner._is_in_all_list(content, "foo") is True

    def test_handles_multiline_all(self, setup_scanner):
        """Handles multiline __all__ definitions."""
        scanner, _, _ = setup_scanner

        content = '''
__all__ = [
    "foo",
    "bar",
    "baz",
]
'''
        assert scanner._is_in_all_list(content, "bar") is True

    def test_handles_plus_equals(self, setup_scanner):
        """Handles __all__ += [...] syntax."""
        scanner, _, _ = setup_scanner

        content = '__all__ += ["extra"]'

        assert scanner._is_in_all_list(content, "extra") is True


class TestRegexSearchAfterImport:
    """Test _regex_search_after_import fast-path."""

    def test_finds_usage_after_import(self, setup_scanner):
        """Finds symbol usage after import line."""
        scanner, _, _ = setup_scanner

        lines = [
            "import json",
            "",
            "def process():",
            "    data = json.loads(text)",
            "    return data"
        ]

        result = scanner._regex_search_after_import(lines, "json", 1)

        assert result is True

    def test_no_usage_after_import(self, setup_scanner):
        """Returns False when symbol not used after import."""
        scanner, _, _ = setup_scanner

        lines = [
            "import json",
            "",
            "def process():",
            "    return {}"
        ]

        result = scanner._regex_search_after_import(lines, "json", 1)

        assert result is False

    def test_skips_comments(self, setup_scanner):
        """Does not count symbol in comments as usage."""
        scanner, _, _ = setup_scanner

        lines = [
            "import json",
            "# json is not used here",
            "def process():",
            "    return {}"
        ]

        result = scanner._regex_search_after_import(lines, "json", 1)

        assert result is False

    def test_word_boundary_matching(self, setup_scanner):
        """Only matches whole word, not substrings."""
        scanner, _, _ = setup_scanner

        lines = [
            "from typing import List",
            "",
            "def process():",
            "    return 'Listing'"  # Contains 'List' as substring
        ]

        result = scanner._regex_search_after_import(lines, "List", 1)

        assert result is False

    def test_handles_invalid_line_number(self, setup_scanner):
        """Handles invalid line numbers gracefully."""
        scanner, _, _ = setup_scanner

        lines = ["import json"]

        assert scanner._regex_search_after_import(lines, "json", 0) is False
        assert scanner._regex_search_after_import(lines, "json", 999) is False


class TestSymbolInAnnotations:
    """Test _symbol_in_annotations type hint detection."""

    def test_detects_return_type(self, setup_scanner):
        """Detects symbol in return type annotation."""
        scanner, _, _ = setup_scanner

        content = "def get_items() -> List:\n    return []"

        assert scanner._symbol_in_annotations(content, "List") is True

    def test_detects_parameter_annotation(self, setup_scanner):
        """Detects symbol in parameter annotation."""
        scanner, _, _ = setup_scanner

        content = "def process(items: List) -> None:\n    pass"

        assert scanner._symbol_in_annotations(content, "List") is True

    def test_detects_variable_annotation(self, setup_scanner):
        """Detects symbol in variable annotation."""
        scanner, _, _ = setup_scanner

        content = "items: List = []"

        assert scanner._symbol_in_annotations(content, "List") is True

    def test_detects_generic_parameter(self, setup_scanner):
        """Detects symbol as generic parameter."""
        scanner, _, _ = setup_scanner

        content = "def process() -> Dict[str, MyType]:\n    pass"

        assert scanner._symbol_in_annotations(content, "MyType") is True

    def test_no_match_in_regular_code(self, setup_scanner):
        """Does not match symbol in regular code."""
        scanner, _, _ = setup_scanner

        content = "x = List"  # Assignment, not annotation

        assert scanner._symbol_in_annotations(content, "List") is False


class TestAstCheckUsage:
    """Test _ast_check_usage AST cross-check."""

    def test_detects_usage_via_ast(self, setup_scanner):
        """AST check finds symbol usage."""
        scanner, _, _ = setup_scanner

        content = '''import json

def process():
    return json.dumps({})
'''

        result = scanner._ast_check_usage(content, "json", 1)

        assert result is True

    def test_no_usage_via_ast(self, setup_scanner):
        """AST check confirms no usage."""
        scanner, _, _ = setup_scanner

        content = '''import json

def process():
    return {}
'''

        result = scanner._ast_check_usage(content, "json", 1)

        assert result is False

    def test_handles_syntax_error(self, setup_scanner):
        """Returns None for invalid Python syntax."""
        scanner, _, _ = setup_scanner

        content = '''import json
def broken(
    # missing closing paren
'''

        result = scanner._ast_check_usage(content, "json", 1)

        assert result is None

    def test_detects_attribute_access(self, setup_scanner):
        """Detects symbol used in attribute access."""
        scanner, _, _ = setup_scanner

        content = '''import os

path = os.path.join("a", "b")
'''

        result = scanner._ast_check_usage(content, "os", 1)

        assert result is True


# =============================================================================
# Remove Symbol from Import Tests
# =============================================================================

class TestRemoveSymbolFromImport:
    """Test _remove_symbol_from_import line manipulation."""

    def test_removes_single_import(self, setup_scanner):
        """Returns None for single import (delete line)."""
        scanner, _, _ = setup_scanner

        result = scanner._remove_symbol_from_import("import json", "json")

        assert result is None

    def test_removes_from_import_single(self, setup_scanner):
        """Returns None for single from-import (delete line)."""
        scanner, _, _ = setup_scanner

        result = scanner._remove_symbol_from_import("from typing import List", "List")

        assert result is None

    def test_removes_from_multi_import(self, setup_scanner):
        """Removes symbol from multi-import line."""
        scanner, _, _ = setup_scanner

        result = scanner._remove_symbol_from_import(
            "from typing import List, Dict, Optional", "Dict"
        )

        assert result == "from typing import List, Optional"

    def test_preserves_indentation(self, setup_scanner):
        """Preserves original indentation."""
        scanner, _, _ = setup_scanner

        result = scanner._remove_symbol_from_import(
            "    from typing import List, Dict", "Dict"
        )

        assert result.startswith("    ")
        assert "List" in result
        assert "Dict" not in result

    def test_handles_as_alias(self, setup_scanner):
        """Handles 'as alias' imports."""
        scanner, _, _ = setup_scanner

        result = scanner._remove_symbol_from_import(
            "import json as j", "json"
        )

        assert result is None

    def test_removes_with_alias_from_multi(self, setup_scanner):
        """Removes aliased import from multi-import."""
        scanner, _, _ = setup_scanner

        result = scanner._remove_symbol_from_import(
            "from typing import List, Dict as D, Optional", "Dict"
        )

        assert result == "from typing import List, Optional"

    def test_returns_unchanged_if_not_found(self, setup_scanner):
        """Returns original line if symbol not found."""
        scanner, _, _ = setup_scanner

        original = "from typing import List"
        result = scanner._remove_symbol_from_import(original, "Dict")

        assert result == original

    def test_handles_parenthesized_imports(self, setup_scanner):
        """Handles parenthesized multi-line imports."""
        scanner, _, _ = setup_scanner

        result = scanner._remove_symbol_from_import(
            "from typing import (List, Dict, Optional)", "Dict"
        )

        assert "List" in result
        assert "Optional" in result
        assert "Dict" not in result


# =============================================================================
# Verify Single Finding Tests
# =============================================================================

class TestVerifySingleFinding:
    """Test _verify_single_finding hybrid verification."""

    def test_returns_uncertain_for_missing_file(self, setup_scanner):
        """Returns UNCERTAIN when file doesn't exist."""
        scanner, _, _ = setup_scanner

        finding = ScanFinding(
            severity="info",
            category="unused-import",
            title="Test",
            description="Test",
            suggestion="Test",
            file="/nonexistent/path/file.py",
            line=1,
            symbol="foo"
        )

        result = scanner._verify_single_finding(finding)

        assert result == UNCERTAIN

    def test_returns_uncertain_for_missing_symbol(self, setup_scanner):
        """Returns UNCERTAIN when symbol is None."""
        scanner, _, _ = setup_scanner

        finding = ScanFinding(
            severity="info",
            category="test",
            title="Test",
            description="Test",
            suggestion="Test",
            file="some_file.py",
            line=1,
            symbol=None
        )

        result = scanner._verify_single_finding(finding)

        assert result == UNCERTAIN

    def test_verifies_unused_import_as_true(self, setup_scanner, temp_python_file):
        """Marks truly unused import as VERIFIED_TRUE."""
        scanner, _, _ = setup_scanner

        file_path = temp_python_file('''import json

def process():
    return {}
''')

        finding = ScanFinding(
            severity="info",
            category="unused-import",
            title="Unused import",
            description="`json` imported but unused",
            suggestion="Remove import",
            file=str(file_path),
            line=1,
            symbol="json"
        )

        result = scanner._verify_single_finding(finding)

        assert result == VERIFIED_TRUE

    def test_verifies_used_import_as_false(self, setup_scanner, temp_python_file):
        """Marks used import as VERIFIED_FALSE."""
        scanner, _, _ = setup_scanner

        file_path = temp_python_file('''import json

def process():
    return json.dumps({})
''')

        finding = ScanFinding(
            severity="info",
            category="unused-import",
            title="Unused import",
            description="`json` imported but unused",
            suggestion="Remove import",
            file=str(file_path),
            line=1,
            symbol="json"
        )

        result = scanner._verify_single_finding(finding)

        assert result == VERIFIED_FALSE

    def test_detects_init_reexport_as_false(self, setup_scanner, tmp_path):
        """Marks __init__.py re-exports as VERIFIED_FALSE."""
        scanner, _, _ = setup_scanner

        # Create __init__.py with re-export
        init_file = tmp_path / "__init__.py"
        init_file.write_text("from .module import SomeClass\n")

        finding = ScanFinding(
            severity="info",
            category="unused-import",
            title="Unused import",
            description="`SomeClass` imported but unused",
            suggestion="Remove import",
            file=str(init_file),
            line=1,
            symbol="SomeClass"
        )

        result = scanner._verify_single_finding(finding)

        assert result == VERIFIED_FALSE

    def test_detects_all_export_as_false(self, setup_scanner, temp_python_file):
        """Marks symbols in __all__ as VERIFIED_FALSE."""
        scanner, _, _ = setup_scanner

        file_path = temp_python_file('''from typing import List

__all__ = ["List", "process"]

def process():
    pass
''')

        finding = ScanFinding(
            severity="info",
            category="unused-import",
            title="Unused import",
            description="`List` imported but unused",
            suggestion="Remove import",
            file=str(file_path),
            line=1,
            symbol="List"
        )

        result = scanner._verify_single_finding(finding)

        assert result == VERIFIED_FALSE


# =============================================================================
# Verify Findings (Batch) Tests
# =============================================================================

class TestVerifyFindings:
    """Test verify_findings batch verification."""

    def test_empty_findings_returns_zero_counts(self, setup_scanner):
        """Returns zero counts when no findings exist."""
        scanner, _, _ = setup_scanner

        result = scanner.verify_findings("clean")

        assert result["verified_true"] == 0
        assert result["verified_false"] == 0
        assert result["uncertain"] == 0
        assert result["findings"] == []

    def test_skips_already_verified_findings(self, setup_scanner, temp_python_file):
        """Skips findings that are already verified."""
        scanner, _, _ = setup_scanner

        file_path = temp_python_file("import json\n")

        finding = ScanFinding(
            severity="info",
            category="unused-import",
            title="Test",
            description="Test",
            suggestion="Test",
            finding_id="test_already_verified",
            file=str(file_path),
            line=1,
            symbol="json",
            status=VERIFIED_TRUE  # Already verified
        )

        scanner._save_findings("clean", [finding])

        result = scanner.verify_findings("clean")

        # Should count existing status, not re-verify
        assert result["verified_true"] == 1

    def test_updates_findings_file(self, setup_scanner, temp_python_file):
        """Persists verification results to findings file."""
        scanner, _, _ = setup_scanner

        file_path = temp_python_file('''import json

def process():
    return {}
''')

        finding = ScanFinding(
            severity="info",
            category="unused-import",
            title="Test",
            description="Test",
            suggestion="Test",
            finding_id="test_persist",
            file=str(file_path),
            line=1,
            symbol="json",
            status="pending"
        )

        scanner._save_findings("clean", [finding])
        scanner.verify_findings("clean")

        # Reload and check status was updated
        loaded = scanner._load_findings("clean")
        assert len(loaded) == 1
        assert loaded[0].status == VERIFIED_TRUE


# =============================================================================
# Remove Verified Imports Tests
# =============================================================================

class TestRemoveVerifiedImports:
    """Test remove_verified_imports safe removal with mocked git."""

    def test_requires_findings(self, setup_scanner):
        """Returns error when no findings exist."""
        scanner, _, _ = setup_scanner

        result = scanner.remove_verified_imports("clean")

        assert result["success"] is False
        assert "No findings" in result["error"]

    def test_requires_verified_status(self, setup_scanner, temp_python_file):
        """Returns error when findings exist but not verified."""
        scanner, _, _ = setup_scanner

        file_path = temp_python_file("import json\n")

        finding = ScanFinding(
            severity="info",
            category="unused-import",
            title="Test",
            description="Test",
            suggestion="Test",
            finding_id="test_not_verified",
            file=str(file_path),
            line=1,
            symbol="json",
            status="pending"  # Not verified
        )

        scanner._save_findings("clean", [finding])

        result = scanner.remove_verified_imports("clean")

        assert result["success"] is False
        assert "Run --verify first" in result["error"]

    @patch('babel.services.scanner.Scanner._git_create_checkpoint')
    def test_fails_on_dirty_working_directory(self, mock_checkpoint, setup_scanner, temp_python_file):
        """Fails when git checkpoint cannot be created (dirty directory)."""
        scanner, _, _ = setup_scanner
        mock_checkpoint.return_value = None  # Simulates dirty directory

        file_path = temp_python_file("import json\n")

        finding = ScanFinding(
            severity="info",
            category="unused-import",
            title="Test",
            description="Test",
            suggestion="Test",
            finding_id="test_dirty",
            file=str(file_path),
            line=1,
            symbol="json",
            status=VERIFIED_TRUE
        )

        scanner._save_findings("clean", [finding])

        result = scanner.remove_verified_imports("clean")

        assert result["success"] is False
        assert "checkpoint" in result["error"].lower()

    @patch('babel.services.scanner.Scanner._git_create_checkpoint')
    @patch('babel.services.scanner.Scanner._run_affected_tests')
    def test_removes_verified_imports(self, mock_tests, mock_checkpoint, setup_scanner, temp_python_file):
        """Successfully removes verified imports."""
        scanner, _, _ = setup_scanner
        mock_checkpoint.return_value = "abc123sha"
        mock_tests.return_value = {"success": True, "tests_run": 0}

        file_path = temp_python_file('''import json

def process():
    return {}
''')

        finding = ScanFinding(
            severity="info",
            category="unused-import",
            title="Test",
            description="Test",
            suggestion="Test",
            finding_id="test_remove",
            file=str(file_path),
            line=1,
            symbol="json",
            status=VERIFIED_TRUE
        )

        scanner._save_findings("clean", [finding])

        result = scanner.remove_verified_imports("clean", run_tests=True)

        assert result["success"] is True
        assert result["removed_count"] == 1
        assert result["checkpoint_sha"] == "abc123sha"

        # Verify file was modified
        content = file_path.read_text()
        assert "import json" not in content

    @patch('babel.services.scanner.Scanner._git_create_checkpoint')
    @patch('babel.services.scanner.Scanner._git_revert_checkpoint')
    @patch('babel.services.scanner.Scanner._run_affected_tests')
    def test_reverts_on_test_failure(self, mock_tests, mock_revert, mock_checkpoint, setup_scanner, temp_python_file):
        """Auto-reverts when tests fail (all-or-nothing atomicity)."""
        scanner, _, _ = setup_scanner
        mock_checkpoint.return_value = "checkpoint123"
        mock_tests.return_value = {"success": False, "error": "Tests failed"}

        file_path = temp_python_file('''import json

def process():
    return {}
''')

        finding = ScanFinding(
            severity="info",
            category="unused-import",
            title="Test",
            description="Test",
            suggestion="Test",
            finding_id="test_revert",
            file=str(file_path),
            line=1,
            symbol="json",
            status=VERIFIED_TRUE
        )

        scanner._save_findings("clean", [finding])

        result = scanner.remove_verified_imports("clean", run_tests=True)

        mock_revert.assert_called_once_with("checkpoint123")
        assert result["success"] is False
        assert "auto-reverted" in result["error"].lower()

    @patch('babel.services.scanner.Scanner._git_create_checkpoint')
    def test_skips_tests_when_disabled(self, mock_checkpoint, setup_scanner, temp_python_file):
        """Skips test execution when run_tests=False."""
        scanner, _, _ = setup_scanner
        mock_checkpoint.return_value = "sha456"

        file_path = temp_python_file('''import json

def foo():
    pass
''')

        finding = ScanFinding(
            severity="info",
            category="unused-import",
            title="Test",
            description="Test",
            suggestion="Test",
            finding_id="test_no_tests",
            file=str(file_path),
            line=1,
            symbol="json",
            status=VERIFIED_TRUE
        )

        scanner._save_findings("clean", [finding])

        result = scanner.remove_verified_imports("clean", run_tests=False)

        assert result["success"] is True
        assert result["test_results"] is None


# =============================================================================
# Finding Persistence Tests
# =============================================================================

class TestFindingPersistence:
    """Test findings save/load functionality."""

    def test_save_and_load_findings(self, setup_scanner):
        """Findings are persisted and loaded correctly."""
        scanner, _, _ = setup_scanner

        findings = [
            ScanFinding(
                severity="info",
                category="unused-import",
                title="Test 1",
                description="Desc 1",
                suggestion="Sugg 1",
                finding_id="persist_id1",
                file="test.py",
                line=1,
                symbol="os"
            ),
            ScanFinding(
                severity="warning",
                category="unused-import",
                title="Test 2",
                description="Desc 2",
                suggestion="Sugg 2",
                finding_id="persist_id2",
                file="test.py",
                line=5,
                symbol="json"
            )
        ]

        scanner._save_findings("clean", findings)
        loaded = scanner._load_findings("clean")

        assert len(loaded) == 2
        assert loaded[0].finding_id == "persist_id1"
        assert loaded[1].finding_id == "persist_id2"

    def test_get_finding_by_full_id(self, setup_scanner):
        """get_finding finds by full ID."""
        scanner, _, _ = setup_scanner

        findings = [
            ScanFinding(
                severity="info",
                category="test",
                title="Test",
                description="Test",
                suggestion="Test",
                finding_id="abcdef123456"
            )
        ]

        scanner._save_findings("clean", findings)

        found = scanner.get_finding("clean", "abcdef123456")
        assert found is not None
        assert found.finding_id == "abcdef123456"

    def test_get_finding_by_prefix(self, setup_scanner):
        """get_finding supports prefix matching."""
        scanner, _, _ = setup_scanner

        findings = [
            ScanFinding(
                severity="info",
                category="test",
                title="Test",
                description="Test",
                suggestion="Test",
                finding_id="abcdef123456"
            )
        ]

        scanner._save_findings("clean", findings)

        # Prefix match (8 chars as displayed)
        found = scanner.get_finding("clean", "abcdef12")
        assert found is not None

    def test_get_finding_not_found(self, setup_scanner):
        """get_finding returns None when not found."""
        scanner, _, _ = setup_scanner

        scanner._save_findings("clean", [])

        found = scanner.get_finding("clean", "nonexistent")
        assert found is None


# =============================================================================
# Exclusion Tests
# =============================================================================

class TestExclusions:
    """Test exclusion (false positive) management."""

    def test_add_exclusion(self, setup_scanner):
        """Adds exclusion and removes from active findings."""
        scanner, _, _ = setup_scanner

        findings = [
            ScanFinding(
                severity="info",
                category="test",
                title="Test",
                description="Test",
                suggestion="Test",
                finding_id="exclude_me_123"
            )
        ]

        scanner._save_findings("clean", findings)

        result = scanner.add_exclusion("clean", "exclude_me_123", "False positive - re-export")

        assert result is True

        # Check exclusion stored
        exclusions = scanner.get_exclusions("clean")
        assert "exclude_me_123" in exclusions

        # Check finding removed from active list
        remaining = scanner._load_findings("clean")
        assert len(remaining) == 0

    def test_remove_exclusion(self, setup_scanner):
        """Removes exclusion to re-enable finding."""
        scanner, _, _ = setup_scanner

        # Add exclusion first
        scanner.add_exclusion("clean", "test_remove_id", "Was false positive")

        # Remove it
        result = scanner.remove_exclusion("clean", "test_remove_id")

        assert result is True

        exclusions = scanner.get_exclusions("clean")
        assert "test_remove_id" not in exclusions

    def test_cannot_add_duplicate_exclusion(self, setup_scanner):
        """Returns False when exclusion already exists."""
        scanner, _, _ = setup_scanner

        scanner.add_exclusion("clean", "dup_test_id", "Reason 1")
        result = scanner.add_exclusion("clean", "dup_test_id", "Reason 2")

        assert result is False

    def test_remove_nonexistent_exclusion(self, setup_scanner):
        """Returns False when removing nonexistent exclusion."""
        scanner, _, _ = setup_scanner

        result = scanner.remove_exclusion("clean", "does_not_exist")

        assert result is False


# =============================================================================
# Finding Summary Tests
# =============================================================================

class TestGetFindingsSummary:
    """Test get_findings_summary counts."""

    def test_empty_findings(self, setup_scanner):
        """Returns zero counts for empty findings."""
        scanner, _, _ = setup_scanner

        summary = scanner.get_findings_summary("clean")

        assert summary["pending"] == 0
        assert summary["verified_true"] == 0
        assert summary["verified_false"] == 0
        assert summary["resolved"] == 0

    def test_counts_by_status(self, setup_scanner):
        """Correctly counts findings by status."""
        scanner, _, _ = setup_scanner

        findings = [
            ScanFinding(severity="info", category="t", title="t", description="d",
                       suggestion="s", finding_id="a", status="pending"),
            ScanFinding(severity="info", category="t", title="t", description="d",
                       suggestion="s", finding_id="b", status=VERIFIED_TRUE),
            ScanFinding(severity="info", category="t", title="t", description="d",
                       suggestion="s", finding_id="c", status=VERIFIED_TRUE),
            ScanFinding(severity="info", category="t", title="t", description="d",
                       suggestion="s", finding_id="d", status=VERIFIED_FALSE),
            ScanFinding(severity="info", category="t", title="t", description="d",
                       suggestion="s", finding_id="e", status="resolved"),
        ]

        scanner._save_findings("clean", findings)

        summary = scanner.get_findings_summary("clean")

        assert summary["pending"] == 1
        assert summary["verified_true"] == 2
        assert summary["verified_false"] == 1
        assert summary["resolved"] == 1

    def test_counts_exclusions(self, setup_scanner):
        """Includes exclusion count in summary."""
        scanner, _, _ = setup_scanner

        scanner.add_exclusion("clean", "excl1", "Reason")
        scanner.add_exclusion("clean", "excl2", "Reason")

        summary = scanner.get_findings_summary("clean")

        assert summary["excluded"] == 2


# =============================================================================
# Remove Import From File Tests
# =============================================================================

class TestRemoveImportFromFile:
    """Test _remove_import_from_file file modification."""

    def test_removes_single_import_line(self, setup_scanner, temp_python_file):
        """Removes entire line for single import."""
        scanner, _, _ = setup_scanner

        file_path = temp_python_file('''import json

def process():
    return {}
''')

        result = scanner._remove_import_from_file(str(file_path), 1, "json")

        assert result is True
        content = file_path.read_text()
        assert "import json" not in content
        assert "def process" in content

    def test_modifies_multi_import_line(self, setup_scanner, temp_python_file):
        """Modifies line to remove one symbol from multi-import."""
        scanner, _, _ = setup_scanner

        file_path = temp_python_file('''from typing import List, Dict, Optional

def process() -> List:
    return []
''')

        result = scanner._remove_import_from_file(str(file_path), 1, "Dict")

        assert result is True
        content = file_path.read_text()
        assert "List" in content
        assert "Optional" in content
        assert "Dict" not in content

    def test_returns_false_for_nonexistent_file(self, setup_scanner):
        """Returns False when file doesn't exist."""
        scanner, _, _ = setup_scanner

        result = scanner._remove_import_from_file("/nonexistent/file.py", 1, "json")

        assert result is False

    def test_returns_false_for_invalid_line(self, setup_scanner, temp_python_file):
        """Returns False for out-of-bounds line number."""
        scanner, _, _ = setup_scanner

        file_path = temp_python_file("import json\n")

        assert scanner._remove_import_from_file(str(file_path), 0, "json") is False
        assert scanner._remove_import_from_file(str(file_path), 999, "json") is False

    def test_returns_false_when_symbol_not_found(self, setup_scanner, temp_python_file):
        """Returns False when symbol not in import line."""
        scanner, _, _ = setup_scanner

        file_path = temp_python_file("from typing import List\n")

        result = scanner._remove_import_from_file(str(file_path), 1, "Dict")

        assert result is False


# =============================================================================
# Clean Scan Tests (with mocked ruff)
# =============================================================================

class TestCleanScan:
    """Test _scan_clean with mocked ruff."""

    @patch('shutil.which')
    def test_returns_warning_when_ruff_not_installed(self, mock_which, setup_scanner):
        """Returns warning when ruff is not available."""
        scanner, _, _ = setup_scanner
        mock_which.return_value = None  # ruff not found

        result = scanner._scan_clean()

        assert result.scan_type == "clean"
        assert result.status == "concerns"
        assert len(result.findings) == 1
        assert "Ruff Not Installed" in result.findings[0].title

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_parses_ruff_findings(self, mock_run, mock_which, setup_scanner):
        """Parses ruff JSON output into ScanFindings."""
        scanner, _, _ = setup_scanner
        mock_which.return_value = "/usr/bin/ruff"

        # Mock ruff JSON output
        ruff_output = json.dumps([
            {
                "code": "F401",
                "message": "`json` imported but unused",
                "filename": "test.py",
                "location": {"row": 1, "column": 1},
                "fix": {"applicability": "safe"}
            }
        ])
        mock_run.return_value = Mock(stdout=ruff_output, stderr="", returncode=1)

        result = scanner._scan_clean()

        assert result.scan_type == "clean"
        assert len(result.findings) == 1
        assert result.findings[0].code == "F401"
        assert result.findings[0].symbol == "json"
        assert result.findings[0].file == "test.py"
        assert result.findings[0].line == 1

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_handles_empty_ruff_output(self, mock_run, mock_which, setup_scanner):
        """Handles empty ruff output (no findings)."""
        scanner, _, _ = setup_scanner
        mock_which.return_value = "/usr/bin/ruff"
        mock_run.return_value = Mock(stdout="", stderr="", returncode=0)

        result = scanner._scan_clean()

        assert result.scan_type == "clean"
        assert result.status == "healthy"
        assert len(result.findings) == 0

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_excludes_findings_in_exclusion_list(self, mock_run, mock_which, setup_scanner):
        """Filters out excluded findings."""
        scanner, _, _ = setup_scanner
        mock_which.return_value = "/usr/bin/ruff"

        # Add an exclusion
        scanner._save_exclusions("clean", {"finding_abc": {"reason": "False positive"}})

        # Mock ruff output with finding that matches exclusion
        ruff_output = json.dumps([
            {
                "code": "F401",
                "message": "`json` imported but unused",
                "filename": "test.py",
                "location": {"row": 1, "column": 1}
            }
        ])
        mock_run.return_value = Mock(stdout=ruff_output, stderr="", returncode=1)

        # Patch _generate_finding_id to return our excluded ID
        with patch.object(scanner, '_generate_finding_id', return_value="finding_abc"):
            result = scanner._scan_clean()

        # Finding should be excluded
        assert len(result.findings) == 0
