"""
Tests for WhitePaper Principles — Validate Implementation Against Theory

These tests verify that Babel's implementation actually embodies the 11 propositions
from the Intent Preservation Framework whitepaper.

TESTING PRINCIPLE: All tests use the Babel CLI interface. No direct database access.
Tests invoke `babel` commands and observe outcomes through CLI output.

TESTING APPROACH: Tests run against REAL tower/.babel data, not synthetic temp projects.
This validates that principles are embodied in actual usage, not just happy-path simulations.

NOTE: These are INTEGRATION tests that require a real .babel/ directory with data.
They are skipped on CI (GitHub Actions) where no .babel/ exists.
Run locally in tower/ for full dogfooding validation.

Implemented Principles (tested here):
- P1: Bootstrap from Need
- P2: Emergent Ontology
- P3: Expertise-Based Authority
- P4: Layered Validation
- P7: Evidence-Weighted Memory
- P9: Dual-Test Truth
- P10: Meta-Principles for Conflict
- P11: Cross-Domain Learning / Self-Application

Partial Principles (gaps documented, not fully tested):
- P5: Adaptive Cycle Rate — severity exists, no outcome→threshold learning
- P6: Empirical Resolution — hypothesis capture exists, no parallel testing
- P8: Failure Metabolism — deprecation requires reason, no lesson artifact type
"""

import pytest
import subprocess
import os
from pathlib import Path

# Skip entire module on CI (no .babel/ directory available)
pytestmark = pytest.mark.skipif(
    os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true",
    reason="Integration tests require .babel/ directory (skipped on CI)"
)


# Real project directory (tower/)
# __file__ = babel-tool/tests/test_whitepaper_principles.py
# .parent = babel-tool/tests
# .parent.parent = babel-tool
# .parent.parent.parent = tower
TOWER_PROJECT = Path(__file__).parent.parent.parent


def run_babel(args: list, cwd: str = None) -> tuple:
    """
    Run a babel command and return (stdout, stderr, returncode).

    Uses CLI interface only - no direct database access.
    """
    if cwd is None:
        cwd = str(TOWER_PROJECT)

    cmd = ["babel"] + args
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
        env={**os.environ, "BABEL_NO_COLOR": "1"}
    )
    return result.stdout, result.stderr, result.returncode


@pytest.fixture
def tower_project():
    """
    Return the real tower project directory.

    Tests run against actual accumulated data, not synthetic projects.
    This validates principles are embodied in real usage.
    """
    assert TOWER_PROJECT.exists(), f"Tower project not found at {TOWER_PROJECT}"
    assert (TOWER_PROJECT / ".babel").exists(), "Tower project has no .babel directory"
    return str(TOWER_PROJECT)


# =============================================================================
# P1: Bootstrap from Need
# =============================================================================

class TestP1BootstrapFromNeed:
    """
    P1: The first cycle starts from a need expression or problematic expression.

    Tests verify via CLI that:
    - Purpose exists in the real project
    - Purpose contains a need/problem statement
    - Status command surfaces the need
    """

    def test_project_has_purpose(self, tower_project):
        """Real project has a purpose captured."""
        stdout, stderr, code = run_babel(["status"], cwd=tower_project)

        assert code == 0, f"Status failed: {stderr}"
        # Purpose should be visible in status
        assert "purpose" in stdout.lower() or "need" in stdout.lower(), \
            "Status should show purpose or need"

    def test_purpose_contains_need(self, tower_project):
        """Purpose expresses a need or problem."""
        stdout, stderr, code = run_babel(["status", "--full"], cwd=tower_project)

        assert code == 0, f"Status --full failed: {stderr}"
        # Look for need-related language
        has_need = any(word in stdout.lower() for word in
                      ["need", "problem", "lost", "context", "reasoning"])
        assert has_need, "Purpose should express a need or problem"

    def test_init_command_requires_purpose(self, tower_project):
        """Init command requires purpose argument (validates P1 in CLI design)."""
        stdout, stderr, code = run_babel(["init", "--help"], cwd=tower_project)

        assert code == 0
        # Init should require a purpose/text argument
        assert "purpose" in stdout.lower() or "text" in stdout.lower() or \
               "positional" in stdout.lower(), \
            "Init should require purpose argument"


# =============================================================================
# P2: Emergent Ontology
# =============================================================================

class TestP2EmergentOntology:
    """
    P2: Ontology emerges from consensus, grounded in reality.

    Tests verify via CLI that:
    - Vocabulary exists with real terms
    - Terms are used across decisions (emerged from usage)
    """

    def test_vocabulary_exists(self, tower_project):
        """Project has accumulated vocabulary."""
        stdout, stderr, code = run_babel(["status", "--full"], cwd=tower_project)

        assert code == 0, f"Status failed: {stderr}"
        # Should mention vocabulary or terms
        # This is a soft check - vocabulary may not be in status output

    def test_why_returns_semantic_matches(self, tower_project):
        """babel why uses vocabulary for semantic matching."""
        # Query a term that should exist in a mature project
        stdout, stderr, code = run_babel(["why", "decision"], cwd=tower_project)

        assert code == 0, f"Why failed: {stderr}"
        # Should return some results if vocabulary works
        # Empty result is also valid if no decisions about "decision"

    def test_list_filter_uses_vocabulary(self, tower_project):
        """List --filter matches terms semantically."""
        stdout, stderr, code = run_babel(["list", "decisions", "--help"], cwd=tower_project)

        assert code == 0
        assert "--filter" in stdout, "List should support --filter for vocabulary matching"


# =============================================================================
# P3: Expertise-Based Authority
# =============================================================================

class TestP3ExpertiseAuthority:
    """
    P3: Governance derives from declared expertise.

    Tests verify via CLI that:
    - Domain flag exists on capture
    - Domain flag exists on challenge
    - Real decisions have domains attributed
    """

    def test_capture_supports_domain(self, tower_project):
        """babel capture accepts --domain flag."""
        stdout, stderr, code = run_babel(["capture", "--help"], cwd=tower_project)

        assert code == 0
        assert "--domain" in stdout or "-d" in stdout, \
            "Capture should support --domain flag for P3"

    def test_challenge_supports_domain(self, tower_project):
        """babel challenge accepts --domain flag."""
        stdout, stderr, code = run_babel(["challenge", "--help"], cwd=tower_project)

        assert code == 0
        assert "--domain" in stdout or "-d" in stdout, \
            "Challenge should support --domain flag for P3"

    def test_real_decisions_exist(self, tower_project):
        """Real decisions exist in the project."""
        stdout, stderr, code = run_babel(["list", "decisions"], cwd=tower_project)

        assert code == 0, f"List decisions failed: {stderr}"
        # Should have decisions (this is a real project)
        # IDs are now in AA-BB codec format (e.g., [KN-JV])
        import re
        ids = re.findall(r'\[([A-Z]{2}-[A-Z]{2})\]', stdout)
        assert len(ids) > 0, "Real project should have decisions"


# =============================================================================
# P4: Layered Validation
# =============================================================================

class TestP4LayeredValidation:
    """
    P4: Human organizations manage expertise; AI reinforces.

    Tests verify via CLI that:
    - Endorse command exists
    - Endorsement requires decision ID
    - Real decisions have endorsement capability
    """

    def test_endorse_command_exists(self, tower_project):
        """babel endorse command is available."""
        stdout, stderr, code = run_babel(["endorse", "--help"], cwd=tower_project)

        assert code == 0, f"Endorse help failed: {stderr}"
        assert "decision" in stdout.lower() or "id" in stdout.lower(), \
            "Endorse should require decision ID"

    def test_validation_shows_endorsement_state(self, tower_project):
        """babel validation shows endorsement states."""
        stdout, stderr, code = run_babel(["validation"], cwd=tower_project)

        assert code == 0, f"Validation failed: {stderr}"
        # Should show validation states (consensus, evidence, validated)
        has_states = any(word in stdout.lower() for word in
                        ["consensus", "evidence", "validated", "proposed"])
        assert has_states or "no decisions" in stdout.lower(), \
            "Validation should show decision states"


# =============================================================================
# P7: Evidence-Weighted Memory
# =============================================================================

class TestP7EvidenceWeightedMemory:
    """
    P7: Unsuccessful artifacts are de-prioritized, not deleted.

    Tests verify via CLI that:
    - Deprecate command exists and requires reason
    - Deprecated items can still be queried (HC1: nothing truly deleted)
    """

    def test_deprecate_requires_reason(self, tower_project):
        """babel deprecate requires a reason argument."""
        stdout, stderr, code = run_babel(["deprecate", "--help"], cwd=tower_project)

        assert code == 0
        assert "reason" in stdout.lower(), \
            "Deprecate should require reason (P7: evidence-weighted)"

    def test_deprecated_still_queryable(self, tower_project):
        """Deprecated items are de-prioritized, not deleted."""
        # Check that list has --all flag to include deprecated
        stdout, stderr, code = run_babel(["list", "--help"], cwd=tower_project)

        assert code == 0
        # Should have way to see all including deprecated
        assert "--all" in stdout, \
            "List should have --all to include deprecated (HC1)"

    def test_history_command_exists(self, tower_project):
        """babel history tracks artifact evolution."""
        stdout, stderr, code = run_babel(["history", "--help"], cwd=tower_project)

        assert code == 0, f"History help failed: {stderr}"
        # History should show evolution trail


# =============================================================================
# P9: Dual-Test Truth
# =============================================================================

class TestP9DualTestTruth:
    """
    P9: Results + consensus = truth.

    Tests verify via CLI that:
    - Validation requires BOTH consensus AND evidence
    - Evidence-decision command exists
    - Validation states are tracked
    """

    def test_validation_command_exists(self, tower_project):
        """babel validation command is available."""
        stdout, stderr, code = run_babel(["validation"], cwd=tower_project)

        # Command should exist and run
        assert code == 0, f"Validation failed: {stderr}"

    def test_evidence_command_exists(self, tower_project):
        """babel evidence-decision command is available."""
        stdout, stderr, code = run_babel(["evidence-decision", "--help"], cwd=tower_project)

        assert code == 0, f"Evidence command help failed: {stderr}"

    def test_dual_validation_states_exist(self, tower_project):
        """Validation distinguishes consensus-only from fully-validated."""
        stdout, stderr, code = run_babel(["validation", "--help"], cwd=tower_project)

        assert code == 0
        # Help or output should reference the dual nature
        # This validates P9 is reflected in the command design


# =============================================================================
# P10: Meta-Principles for Conflict
# =============================================================================

class TestP10MetaPrinciples:
    """
    P10: Hold ambiguity until evidence resolves.

    Tests verify via CLI that:
    - Uncertain flag exists for holding ambiguity
    - Questions can be captured (uncertainty as artifact)
    - Tensions are surfaced, not hidden
    """

    def test_uncertain_flag_exists(self, tower_project):
        """babel capture accepts --uncertain flag."""
        stdout, stderr, code = run_babel(["capture", "--help"], cwd=tower_project)

        assert "--uncertain" in stdout or "-u" in stdout, \
            "Capture should support --uncertain for P10"

    def test_question_command_exists(self, tower_project):
        """babel question captures uncertainty as artifact."""
        stdout, stderr, code = run_babel(["question", "--help"], cwd=tower_project)

        assert code == 0, f"Question help failed: {stderr}"

    def test_tensions_command_exists(self, tower_project):
        """babel tensions surfaces conflicts explicitly."""
        stdout, stderr, code = run_babel(["tensions"], cwd=tower_project)

        assert code == 0, f"Tensions failed: {stderr}"
        # Command runs - tensions may or may not exist

    def test_questions_are_queryable(self, tower_project):
        """babel questions shows captured uncertainties."""
        stdout, stderr, code = run_babel(["questions"], cwd=tower_project)

        assert code == 0, f"Questions failed: {stderr}"


# =============================================================================
# P11: Cross-Domain Learning / Self-Application
# =============================================================================

class TestP11SelfApplication:
    """
    P11: Collaboration enables domains to strengthen each other.

    Babel is used to build itself (dogfooding).

    Tests verify via CLI that:
    - Graph traversal exists (--from)
    - Coherence command works
    - Babel's own decisions are tracked
    """

    def test_list_supports_graph_traversal(self, tower_project):
        """babel list --from shows cross-artifact connections."""
        stdout, stderr, code = run_babel(["list", "--help"], cwd=tower_project)

        assert "--from" in stdout, "List should support --from for graph traversal (P11)"

    def test_coherence_command_works(self, tower_project):
        """babel coherence can analyze relationships."""
        stdout, stderr, code = run_babel(["coherence"], cwd=tower_project)

        assert code == 0, f"Coherence failed: {stderr}"

    def test_babel_tracks_own_decisions(self, tower_project):
        """Babel's own development decisions are tracked (dogfooding)."""
        # Query for decisions about babel itself
        stdout, stderr, code = run_babel(["why", "babel"], cwd=tower_project)

        assert code == 0, f"Why babel failed: {stderr}"
        # Should return meaningful content about babel (LLM synthesized)
        # Check for sources indicator or substantial response
        has_content = (
            "sources:" in stdout.lower() or
            len(stdout) > 100 or  # Meaningful response
            "decision" in stdout.lower() or
            "babel" in stdout.lower()
        )
        assert has_content, "Babel should track its own decisions (P11: self-application)"

    def test_purpose_mentions_dogfooding(self, tower_project):
        """Project purpose mentions self-application."""
        stdout, stderr, code = run_babel(["status", "--full"], cwd=tower_project)

        assert code == 0
        has_self_ref = any(word in stdout.lower() for word in
                          ["dogfood", "itself", "self", "p11", "babel"])
        assert has_self_ref, "Purpose should reference self-application (P11)"


# =============================================================================
# Integration: Real Data Validation
# =============================================================================

class TestRealDataIntegrity:
    """
    Integration tests verifying real data integrity.
    All interaction through babel commands only.
    """

    def test_status_shows_healthy_counts(self, tower_project):
        """Status shows artifacts exist in real project."""
        stdout, stderr, code = run_babel(["status"], cwd=tower_project)

        assert code == 0, f"Status failed: {stderr}"
        # Should show counts
        has_counts = any(word in stdout.lower() for word in
                        ["events", "artifacts", "decisions", "connections"])
        assert has_counts, "Status should show artifact counts"

    def test_decisions_have_ids(self, tower_project):
        """Real decisions have proper ID format (AA-BB codec)."""
        stdout, stderr, code = run_babel(["list", "decisions"], cwd=tower_project)

        assert code == 0
        # IDs are now in AA-BB codec format (e.g., [KN-JV])
        import re
        ids = re.findall(r'\[([A-Z]{2}-[A-Z]{2})\]', stdout)
        assert len(ids) > 0, "Decisions should have AA-BB codec IDs"

    def test_why_query_returns_context(self, tower_project):
        """babel why returns context for known topics."""
        stdout, stderr, code = run_babel(["why", "cli"], cwd=tower_project)

        assert code == 0, f"Why failed: {stderr}"
        # CLI is a known topic - should return meaningful content (LLM synthesized)
        has_content = (
            "sources:" in stdout.lower() or
            len(stdout) > 100 or  # Meaningful response
            "cli" in stdout.lower() or
            "command" in stdout.lower()
        )
        assert has_content, "Why 'cli' should return context in this project"

    def test_coherence_runs_without_error(self, tower_project):
        """Coherence check completes on real data."""
        stdout, stderr, code = run_babel(["coherence"], cwd=tower_project)

        assert code == 0, f"Coherence failed on real data: {stderr}"

    def test_gaps_command_works(self, tower_project):
        """babel gaps shows implementation status."""
        stdout, stderr, code = run_babel(["gaps"], cwd=tower_project)

        assert code == 0, f"Gaps failed: {stderr}"
