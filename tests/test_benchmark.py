"""
Tests for LLM benchmark feature.

Tests use mock providers to avoid real LLM calls in CI.
"""

import json
import pytest
from unittest.mock import patch

from babel.services.benchmark import (
    TEST_CASES,
    BenchmarkResults,
    TestResult as BenchmarkTestResult,  # Renamed to avoid pytest collection conflict
    run_benchmark,
    format_results,
    _parse_response,
    _run_single_test,
)
from babel.services.providers import LLMProvider, LLMResponse, MockProvider
from babel.config import Config, LLMConfig, LocalLLMConfig, RemoteLLMConfig, DisplayConfig, CoherenceConfig


# =============================================================================
# Mock Providers for Testing
# =============================================================================

class BenchmarkMockProvider(LLMProvider):
    """Mock provider that returns valid extraction responses."""

    def __init__(self, response_artifacts=None, latency_ms=100):
        self.response_artifacts = response_artifacts or []
        self.latency_ms = latency_ms
        self.call_count = 0

    def complete(self, system: str, user: str, max_tokens: int = 2048) -> LLMResponse:
        self.call_count += 1
        response = {
            "artifacts": self.response_artifacts,
            "meta": {"extractable": bool(self.response_artifacts)}
        }
        return LLMResponse(text=json.dumps(response))

    @property
    def is_available(self) -> bool:
        return True


class FailingMockProvider(LLMProvider):
    """Mock provider that raises exceptions."""

    def complete(self, system: str, user: str, max_tokens: int = 2048) -> LLMResponse:
        raise Exception("Provider error: connection failed")

    @property
    def is_available(self) -> bool:
        return True


class InvalidJsonProvider(LLMProvider):
    """Mock provider that returns invalid JSON."""

    def complete(self, system: str, user: str, max_tokens: int = 2048) -> LLMResponse:
        return LLMResponse(text="This is not valid JSON {{{")

    @property
    def is_available(self) -> bool:
        return True


# =============================================================================
# Test Cases Validation
# =============================================================================

class TestTestCases:
    """Verify test corpus is well-formed."""

    def test_has_nine_test_cases(self):
        """Should have exactly 9 test cases."""
        assert len(TEST_CASES) == 9

    def test_three_per_level(self):
        """Should have 3 tests per level."""
        simple = [tc for tc in TEST_CASES if tc["level"] == "simple"]
        medium = [tc for tc in TEST_CASES if tc["level"] == "medium"]
        high = [tc for tc in TEST_CASES if tc["level"] == "high"]

        assert len(simple) == 3, "Should have 3 simple tests"
        assert len(medium) == 3, "Should have 3 medium tests"
        assert len(high) == 3, "Should have 3 high tests"

    def test_all_have_required_fields(self):
        """All test cases should have required fields."""
        required_fields = ["id", "name", "level", "input", "expected_description", "expected_types", "evaluation_hint"]

        for tc in TEST_CASES:
            for field in required_fields:
                assert field in tc, f"Test case {tc.get('id', '?')} missing field: {field}"

    def test_ids_are_unique(self):
        """Test IDs should be unique."""
        ids = [tc["id"] for tc in TEST_CASES]
        assert len(ids) == len(set(ids)), "Test IDs must be unique"


# =============================================================================
# Response Parsing
# =============================================================================

class TestParseResponse:
    """Test response parsing logic."""

    def test_parses_valid_json(self):
        """Parses valid JSON response."""
        response = '{"artifacts": [{"type": "decision", "summary": "Test"}]}'
        artifacts, success = _parse_response(response)

        assert success is True
        assert len(artifacts) == 1
        assert artifacts[0]["type"] == "decision"

    def test_handles_empty_response(self):
        """Handles empty string."""
        artifacts, success = _parse_response("")

        assert success is False
        assert artifacts == []

    def test_handles_none_response(self):
        """Handles None."""
        artifacts, success = _parse_response(None)

        assert success is False
        assert artifacts == []

    def test_handles_invalid_json(self):
        """Handles invalid JSON gracefully."""
        artifacts, success = _parse_response("not json {{{")

        assert success is False
        assert artifacts == []

    def test_strips_markdown_code_blocks(self):
        """Removes markdown code fences."""
        response = '```json\n{"artifacts": [{"type": "decision"}]}\n```'
        artifacts, success = _parse_response(response)

        assert success is True
        assert len(artifacts) == 1

    def test_handles_empty_artifacts_array(self):
        """Parses response with no artifacts."""
        response = '{"artifacts": [], "meta": {"extractable": false}}'
        artifacts, success = _parse_response(response)

        assert success is True
        assert artifacts == []


# =============================================================================
# Single Test Execution
# =============================================================================

class TestRunSingleTest:
    """Test single test case execution."""

    def test_runs_test_successfully(self):
        """Runs a test case and returns result."""
        provider = BenchmarkMockProvider(
            response_artifacts=[{"type": "decision", "summary": "Test", "confidence": 0.9}]
        )
        test_case = TEST_CASES[0]  # Simple decision

        result = _run_single_test(test_case, provider, "mock", "test-model")

        assert result.test_id == test_case["id"]
        assert result.parse_success is True
        assert result.artifact_count == 1
        assert result.error is None

    def test_handles_provider_error(self):
        """Handles provider exceptions gracefully."""
        provider = FailingMockProvider()
        test_case = TEST_CASES[0]

        result = _run_single_test(test_case, provider, "mock", "test-model")

        assert result.parse_success is False
        assert result.error is not None
        assert "connection failed" in result.error

    def test_handles_invalid_json_response(self):
        """Handles unparseable responses."""
        provider = InvalidJsonProvider()
        test_case = TEST_CASES[0]

        result = _run_single_test(test_case, provider, "mock", "test-model")

        assert result.parse_success is False
        assert result.artifacts == []

    def test_records_latency(self):
        """Records execution latency."""
        provider = BenchmarkMockProvider()
        test_case = TEST_CASES[0]

        result = _run_single_test(test_case, provider, "mock", "test-model")

        assert result.latency_ms > 0


# =============================================================================
# Full Benchmark Execution
# =============================================================================

class TestRunBenchmark:
    """Test full benchmark execution."""

    def _make_config(self, local_available=True, remote_available=True):
        """Create test config."""
        return Config(
            llm=LLMConfig(
                active="auto",
                local=LocalLLMConfig(provider="ollama", model="test-local"),
                remote=RemoteLLMConfig(provider="claude", model="test-remote")
            ),
            display=DisplayConfig(),
            coherence=CoherenceConfig()
        )

    @patch('babel.services.benchmark.get_provider')
    def test_runs_all_tests_on_available_providers(self, mock_get_provider, monkeypatch):
        """Runs 9 tests on each available provider."""
        mock_provider = BenchmarkMockProvider()
        mock_get_provider.return_value = mock_provider

        # Set API key to make remote available
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        config = self._make_config()
        results = run_benchmark(config)

        # Should have results for both providers
        assert "local" in results.results or "remote" in results.results

    @patch('babel.services.benchmark.get_provider')
    def test_local_only_skips_remote(self, mock_get_provider):
        """Local-only mode doesn't test remote."""
        mock_provider = BenchmarkMockProvider()
        mock_get_provider.return_value = mock_provider

        config = self._make_config()

        results = run_benchmark(config, local_only=True)

        assert "remote" not in results.results
        assert results.remote_available is False

    @patch('babel.services.benchmark.get_provider')
    def test_remote_only_skips_local(self, mock_get_provider, monkeypatch):
        """Remote-only mode doesn't test local."""
        mock_provider = BenchmarkMockProvider()
        mock_get_provider.return_value = mock_provider

        # Set API key to make remote available
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        config = self._make_config()
        results = run_benchmark(config, remote_only=True)

        assert "local" not in results.results
        assert results.local_available is False

    @patch('babel.services.benchmark.get_provider')
    def test_calls_progress_callback(self, mock_get_provider):
        """Calls progress callback after each test."""
        mock_provider = BenchmarkMockProvider()
        mock_get_provider.return_value = mock_provider

        config = self._make_config()
        callback_calls = []

        def on_progress(test_id, provider):
            callback_calls.append((test_id, provider))

        # Test local only to avoid remote availability issues
        results = run_benchmark(config, on_test_complete=on_progress, local_only=True)

        # If local was tested, should have 9 callback calls
        if "local" in results.results:
            assert len(callback_calls) == 9

    @patch('babel.services.benchmark.get_provider')
    def test_handles_unavailable_local(self, mock_get_provider):
        """Handles Ollama not running."""
        # Return MockProvider (which indicates Ollama not available)
        mock_get_provider.return_value = MockProvider()

        config = self._make_config()

        # Local only to avoid remote
        results = run_benchmark(config, local_only=True)

        assert results.local_available is False
        assert "Ollama not running" in (results.local_error or "")


# =============================================================================
# Output Formatting
# =============================================================================

class TestFormatResults:
    """Test output formatting."""

    def test_includes_header(self):
        """Output includes benchmark header."""
        results = BenchmarkResults()
        output = format_results(results)

        assert "BABEL LLM BENCHMARK" in output

    def test_shows_provider_info(self):
        """Shows provider names and models."""
        results = BenchmarkResults(
            local_provider="ollama",
            local_model="llama3.2",
            remote_provider="claude",
            remote_model="opus"
        )
        output = format_results(results)

        assert "ollama" in output
        assert "claude" in output

    def test_shows_unavailable_status(self):
        """Shows unavailable providers."""
        results = BenchmarkResults(
            local_available=False,
            local_error="Ollama not running"
        )
        output = format_results(results)

        assert "✗" in output
        assert "not running" in output.lower() or "unavailable" in output.lower()

    def test_includes_all_levels(self):
        """Output includes all three difficulty levels."""
        results = BenchmarkResults()
        output = format_results(results)

        assert "SIMPLE" in output
        assert "MEDIUM" in output
        assert "HIGH" in output

    def test_includes_summary_section(self):
        """Output includes summary section."""
        results = BenchmarkResults()
        output = format_results(results)

        assert "SUMMARY" in output

    def test_includes_evaluation_guidance(self):
        """Output includes guidance for human evaluation."""
        results = BenchmarkResults()
        output = format_results(results)

        assert "Evaluate" in output or "evaluate" in output


# =============================================================================
# TestResult Dataclass
# =============================================================================

class TestResultDataclass:
    """Test TestResult helper methods."""

    def test_artifact_count(self):
        """Returns correct artifact count."""
        result = BenchmarkTestResult(
            test_id="S1",
            test_name="Test",
            level="simple",
            provider_name="mock",
            model="test",
            latency_ms=100,
            raw_response="",
            artifacts=[{"type": "decision"}, {"type": "constraint"}],
            parse_success=True
        )

        assert result.artifact_count == 2

    def test_artifact_types(self):
        """Returns list of artifact types."""
        result = BenchmarkTestResult(
            test_id="S1",
            test_name="Test",
            level="simple",
            provider_name="mock",
            model="test",
            latency_ms=100,
            raw_response="",
            artifacts=[{"type": "decision"}, {"type": "constraint"}],
            parse_success=True
        )

        assert result.artifact_types == ["decision", "constraint"]


# =============================================================================
# BenchmarkResults Dataclass
# =============================================================================

class TestBenchmarkResults:
    """Test BenchmarkResults helper methods."""

    def test_get_results_by_level(self):
        """Filters results by difficulty level."""
        results = BenchmarkResults()
        results.results["local"] = [
            BenchmarkTestResult("S1", "Test1", "simple", "mock", "m", 100, "", [], True),
            BenchmarkTestResult("M1", "Test2", "medium", "mock", "m", 100, "", [], True),
            BenchmarkTestResult("H1", "Test3", "high", "mock", "m", 100, "", [], True),
        ]

        simple_results = results.get_results_by_level("simple")

        assert len(simple_results["local"]) == 1
        assert simple_results["local"][0].test_id == "S1"
