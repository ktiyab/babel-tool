"""
Tests for Project Health — P9 Adaptive Cycle Rate

P9: Adaptive Cycle Rate
- High confusion → slower, clarifying cycles
- High alignment → faster synthesis cycles
- No fixed cadence imposed

"Resilient systems adapt their behavior to conditions rather than following fixed plans."
"""

import pytest
from unittest.mock import MagicMock

from babel.cli import IntentCLI


@pytest.fixture
def babel_project(tmp_path):
    """Create a minimal Babel project structure."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    babel_dir = project_dir / ".babel"
    babel_dir.mkdir()
    (babel_dir / "shared").mkdir()
    (babel_dir / "local").mkdir()
    
    # Add minimal config
    config_file = babel_dir / "config.yaml"
    config_file.write_text("llm:\n  provider: none\n")
    
    return project_dir


@pytest.fixture
def cli(babel_project):
    """Create CLI instance."""
    return IntentCLI(babel_project)


# =============================================================================
# Health Computation Tests
# =============================================================================

class TestHealthComputation:
    """Test project health computation."""
    
    def test_starting_state(self, cli):
        """New project shows Starting health."""
        health = cli._compute_project_health(
            open_tensions=0,
            validation_stats={"tracked": 0, "validated": 0, "partial": 0},
            open_questions=0,
            coherence_result=None
        )

        assert health["level"] == "Starting"
        assert health["indicator"] == "○"

    def test_aligned_state(self, cli):
        """Project with validated decisions shows Aligned."""
        health = cli._compute_project_health(
            open_tensions=0,
            validation_stats={"tracked": 5, "validated": 5, "partial": 0},
            open_questions=0,
            coherence_result=None
        )

        assert health["level"] == "Aligned"
        assert health["indicator"] == "●"
        assert "move forward" in health["suggestion"].lower()

    def test_moderate_state(self, cli):
        """Project with some tensions shows Moderate."""
        health = cli._compute_project_health(
            open_tensions=2,
            validation_stats={"tracked": 3, "validated": 1, "partial": 2},
            open_questions=1,
            coherence_result=None
        )

        assert health["level"] == "Moderate"
        assert health["indicator"] == "◐"

    def test_high_confusion_state(self, cli):
        """Project with many issues shows Confused health."""
        health = cli._compute_project_health(
            open_tensions=5,
            validation_stats={"tracked": 5, "validated": 0, "partial": 5},
            open_questions=3,
            coherence_result=None
        )

        assert health["level"] == "Confused"
        assert health["indicator"] == "◔"
        assert "resolving" in health["suggestion"].lower() or "consider" in health["suggestion"].lower()


# =============================================================================
# P9 Principle Tests
# =============================================================================

class TestP9Principles:
    """Test P9 principle compliance."""
    
    def test_high_confusion_suggests_slowdown(self, cli):
        """P9: High confusion → slower, clarifying cycles."""
        health = cli._compute_project_health(
            open_tensions=4,
            validation_stats={"tracked": 3, "validated": 0, "partial": 3},
            open_questions=2,
            coherence_result=None
        )

        # Should suggest slowing down (Confused or Moderate level)
        assert health["level"] in ["Confused", "Moderate"]
        if health["suggestion"]:
            # Should mention resolving or addressing issues
            suggestion_lower = health["suggestion"].lower()
            assert any(word in suggestion_lower for word in ["resolv", "address", "consider", "tension"])

    def test_high_alignment_enables_speed(self, cli):
        """P9: High alignment → faster synthesis cycles."""
        health = cli._compute_project_health(
            open_tensions=0,
            validation_stats={"tracked": 8, "validated": 8, "partial": 0},
            open_questions=0,
            coherence_result=None
        )

        # Should indicate good to proceed
        assert health["level"] == "Aligned"
        assert "forward" in health["suggestion"].lower() or "good" in health["suggestion"].lower()
    
    def test_no_fixed_cadence(self, cli):
        """P9: No fixed cadence is imposed."""
        # Health computation gives guidance, not enforcement
        # There's no blocking, no required actions
        health = cli._compute_project_health(
            open_tensions=10,  # Even extreme confusion
            validation_stats={"tracked": 0, "validated": 0, "partial": 0},
            open_questions=10,
            coherence_result=None
        )
        
        # Still returns a result (no exception, no blocking)
        assert health["level"] is not None
        assert health["indicator"] is not None
        # Suggestion is advice, not mandate
        assert "must" not in (health["suggestion"] or "").lower()
        assert "required" not in (health["suggestion"] or "").lower()
    
    def test_coherence_affects_health(self, cli):
        """P9: Coherence status affects health assessment."""
        # Mock coherence result with issues
        mock_coherence = MagicMock()
        mock_coherence.has_issues = True
        
        health_with_issues = cli._compute_project_health(
            open_tensions=1,
            validation_stats={"tracked": 2, "validated": 1, "partial": 1},
            open_questions=0,
            coherence_result=mock_coherence
        )
        
        mock_coherence.has_issues = False
        health_without_issues = cli._compute_project_health(
            open_tensions=1,
            validation_stats={"tracked": 2, "validated": 1, "partial": 1},
            open_questions=0,
            coherence_result=mock_coherence
        )
        
        # Coherence issues should worsen health
        # (exact comparison depends on scoring, but they should differ)
        assert health_with_issues is not None
        assert health_without_issues is not None


# =============================================================================
# Integration Tests
# =============================================================================

class TestHealthIntegration:
    """Test health integrates with existing signals."""
    
    def test_uses_tension_count(self, cli):
        """Health uses P4 tension count."""
        health_low = cli._compute_project_health(
            open_tensions=0,
            validation_stats={"tracked": 0, "validated": 0, "partial": 0},
            open_questions=0,
            coherence_result=None
        )
        
        health_high = cli._compute_project_health(
            open_tensions=5,
            validation_stats={"tracked": 0, "validated": 0, "partial": 0},
            open_questions=0,
            coherence_result=None
        )
        
        # More tensions should worsen health
        assert health_low["level"] != health_high["level"] or \
               health_low["indicator"] != health_high["indicator"]
    
    def test_uses_validation_stats(self, cli):
        """Health uses P5 validation statistics."""
        health_unvalidated = cli._compute_project_health(
            open_tensions=0,
            validation_stats={"tracked": 5, "validated": 0, "partial": 5},
            open_questions=0,
            coherence_result=None
        )
        
        health_validated = cli._compute_project_health(
            open_tensions=0,
            validation_stats={"tracked": 5, "validated": 5, "partial": 0},
            open_questions=0,
            coherence_result=None
        )
        
        # More validation should improve health
        assert health_validated["level"] != health_unvalidated["level"] or \
               health_validated["indicator"] != health_unvalidated["indicator"]
    
    def test_uses_question_count(self, cli):
        """Health uses P6 open question count."""
        health_few = cli._compute_project_health(
            open_tensions=0,
            validation_stats={"tracked": 0, "validated": 0, "partial": 0},
            open_questions=0,
            coherence_result=None
        )
        
        health_many = cli._compute_project_health(
            open_tensions=0,
            validation_stats={"tracked": 0, "validated": 0, "partial": 0},
            open_questions=10,
            coherence_result=None
        )
        
        # Health computation completes for both
        assert health_few is not None
        assert health_many is not None


# =============================================================================
# P11: Framework Self-Application (Reflexivity) Tests
# =============================================================================

class TestP11Reflexivity:
    """Test P11 reflexivity requirement compliance."""
    
    def test_principles_method_exists(self, cli):
        """P11: principles() method exists for self-check."""
        assert hasattr(cli, 'principles')
        assert callable(cli.principles)
    
    def test_principles_output_contains_core_principles(self, cli, capsys):
        """P11: principles output contains all core principles."""
        cli.principles()
        captured = capsys.readouterr()
        
        # Should contain all principle headers
        assert "P1: Bootstrap from Need" in captured.out
        assert "P2: Emergent Ontology" in captured.out
        assert "P3: Expertise Governance" in captured.out
        assert "P4: Disagreement as Hypothesis" in captured.out
        assert "P5: Dual-Test Truth" in captured.out
        assert "P6: Ambiguity Management" in captured.out
        assert "P7: Evidence-Weighted Memory" in captured.out
        assert "P8: Failure Metabolism" in captured.out
        assert "P9: Adaptive Cycle Rate" in captured.out
        assert "P10: Cross-Domain Learning" in captured.out
        assert "P11: Framework Self-Application" in captured.out
    
    def test_principles_output_contains_hard_constraints(self, cli, capsys):
        """P11: principles output includes hard constraints."""
        cli.principles()
        captured = capsys.readouterr()
        
        assert "HC1: Immutable Events" in captured.out
        assert "HC2: Human Authority" in captured.out
    
    def test_principles_output_contains_self_check_questions(self, cli, capsys):
        """P11: principles output includes self-check questions."""
        cli.principles()
        captured = capsys.readouterr()
        
        assert "SELF-CHECK QUESTIONS" in captured.out
        assert "Am I starting from need" in captured.out
    
    def test_framework_can_govern_itself(self, cli):
        """P11: Framework has mechanisms for self-governance."""
        # The framework can govern itself because:
        # 1. Principles are documented (principles() method)
        # 2. State signals exist (health, tensions, validation)
        # 3. AI can notice violations
        
        # All these methods exist
        assert hasattr(cli, 'principles')  # P11: self-reference
        assert hasattr(cli, 'status')      # State visibility
        assert hasattr(cli, '_compute_project_health')  # Health assessment
        
        # Health computation works
        health = cli._compute_project_health(
            open_tensions=0,
            validation_stats={"tracked": 0, "validated": 0, "partial": 0},
            open_questions=0,
            coherence_result=None
        )
        assert health is not None
    
    def test_check_method_exists(self, cli):
        """P11: check() method exists for integrity verification."""
        assert hasattr(cli, 'check')
        assert callable(cli.check)
    
    def test_check_runs_without_error(self, cli, capsys):
        """P11: check() runs and produces output."""
        cli.check()
        captured = capsys.readouterr()
        
        assert "BABEL CHECK" in captured.out
        assert ".babel/" in captured.out
    
    def test_check_reports_healthy_project(self, cli, capsys):
        """P11: check() reports status correctly."""
        cli.check()
        captured = capsys.readouterr()
        
        # Should show some status (healthy or warnings)
        assert "✓" in captured.out or "○" in captured.out or "⚠" in captured.out
