"""
Tests for scanner module

Context-aware technical advisor using Babel's knowledge.
"""

import pytest
import json
from pathlib import Path
from datetime import datetime, timezone

from babel.services.scanner import (
    Scanner, ScanResult, ScanFinding, ScanContext,
    format_scan_result
)
from babel.core.events import Event, EventType, DualEventStore
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
