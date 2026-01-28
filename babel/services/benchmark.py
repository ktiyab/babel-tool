"""
LLM Benchmark — Compare local vs remote extraction quality.

Provides calibrated test cases at three difficulty levels (simple, medium, high)
with side-by-side human-readable output for user evaluation.

Usage:
    from babel.services.benchmark import run_benchmark, format_results
    results = run_benchmark(config)
    print(format_results(results))
"""

import json
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from .extractor import Extractor
from .providers import LLMProvider, MockProvider, get_provider
from ..config import Config, LLMConfig


# =============================================================================
# Test Corpus — 9 calibrated cases (3 per level)
# =============================================================================

TEST_CASES = [
    # ─────────────────────────────────────────────────────────────────────────
    # SIMPLE LEVEL: Explicit statements, obvious types, single artifacts
    # ─────────────────────────────────────────────────────────────────────────
    {
        "id": "S1",
        "name": "Explicit Decision",
        "level": "simple",
        "input": "We decided to use PostgreSQL instead of MongoDB because we need ACID transactions for financial data.",
        "expected_description": "Single decision with database choice and rationale",
        "expected_types": ["decision"],
        "evaluation_hint": "Should capture PostgreSQL choice AND the ACID/financial rationale"
    },
    {
        "id": "S2",
        "name": "Clear Constraint",
        "level": "simple",
        "input": "Due to GDPR, we cannot store user data outside the EU. This is non-negotiable.",
        "expected_description": "Hard constraint with legal context",
        "expected_types": ["constraint"],
        "evaluation_hint": "Should identify as constraint (not decision) with GDPR as the reason"
    },
    {
        "id": "S3",
        "name": "Nothing to Extract",
        "level": "simple",
        "input": "Had a nice chat with the team today. Weather was good. Looking forward to the weekend.",
        "expected_description": "No extractable artifacts (social conversation)",
        "expected_types": [],
        "evaluation_hint": "Should return empty artifacts array — not hallucinate decisions"
    },

    # ─────────────────────────────────────────────────────────────────────────
    # MEDIUM LEVEL: Multiple artifacts, technical terms, some inference
    # ─────────────────────────────────────────────────────────────────────────
    {
        "id": "M1",
        "name": "Multi-Artifact List",
        "level": "medium",
        "input": """After the outage last week, we established three things:
1. All deployments must go through staging first (no exceptions)
2. We're targeting 99.9% uptime as our SLA
3. The current monitoring is insufficient - we need better alerting""",
        "expected_description": "Three distinct artifacts from numbered list",
        "expected_types": ["constraint", "purpose", "requirement"],
        "evaluation_hint": "Should extract 3 separate items, not merge them. Types may vary but count matters."
    },
    {
        "id": "M2",
        "name": "Technical Architecture",
        "level": "medium",
        "input": "The team agreed to implement CQRS with event sourcing. Write models go to PostgreSQL, read models are materialized views in Redis. This gives us audit trails and replay capability.",
        "expected_description": "Architectural decision with technical terminology",
        "expected_types": ["decision"],
        "evaluation_hint": "Should understand CQRS/event sourcing as a coherent decision, capture the why (audit trails)"
    },
    {
        "id": "M3",
        "name": "Decision with Alternatives",
        "level": "medium",
        "input": "We evaluated three auth providers: Auth0, Cognito, and Keycloak. Auth0 was too expensive, Cognito had AWS lock-in concerns. We're going with Keycloak for self-hosting flexibility.",
        "expected_description": "Decision with explicitly rejected alternatives",
        "expected_types": ["decision"],
        "evaluation_hint": "Should capture Keycloak choice AND why others were rejected"
    },

    # ─────────────────────────────────────────────────────────────────────────
    # HIGH LEVEL: Implicit meaning, ambiguity, unresolved tensions
    # ─────────────────────────────────────────────────────────────────────────
    {
        "id": "H1",
        "name": "Implicit Decision",
        "level": "high",
        "input": "We talked about caching strategies. Redis seemed overkill for our scale, and memcached felt dated. In the end, the built-in LRU cache in Python was good enough.",
        "expected_description": "Decision inferred from 'was good enough' (never explicitly stated)",
        "expected_types": ["decision"],
        "evaluation_hint": "Must infer decision from 'was good enough' = chosen. Never says 'we decided'."
    },
    {
        "id": "H2",
        "name": "Unresolved Tension",
        "level": "high",
        "input": "We're stuck between two approaches. The security team wants all data encrypted at rest, but the performance team says encryption adds 15% latency which breaks our SLA. No resolution yet.",
        "expected_description": "Explicit unresolved conflict between teams",
        "expected_types": ["tension"],
        "evaluation_hint": "Should identify as tension (not decision). Key signal: 'No resolution yet'"
    },
    {
        "id": "H3",
        "name": "Ambiguous Discussion",
        "level": "high",
        "input": "We might use GraphQL. Or maybe stick with REST. Sarah likes GraphQL but hasn't convinced everyone yet.",
        "expected_description": "Ambiguous, no decision made",
        "expected_types": ["tension"],
        "evaluation_hint": "Should NOT extract as decision. 'Might' and 'maybe' signal uncertainty. Tension or nothing acceptable."
    },
]


# =============================================================================
# Result Data Structures
# =============================================================================

@dataclass
class TestResult:
    """Result of a single test case on a single provider."""
    test_id: str
    test_name: str
    level: str
    provider_name: str
    model: str
    latency_ms: float
    raw_response: str
    artifacts: List[Dict[str, Any]]
    parse_success: bool
    error: Optional[str] = None

    @property
    def artifact_count(self) -> int:
        return len(self.artifacts)

    @property
    def artifact_types(self) -> List[str]:
        return [a.get("type", "unknown") for a in self.artifacts]


@dataclass
class BenchmarkResults:
    """Complete benchmark results for all providers."""
    local_provider: Optional[str] = None
    local_model: Optional[str] = None
    local_available: bool = False
    local_error: Optional[str] = None

    remote_provider: Optional[str] = None
    remote_model: Optional[str] = None
    remote_available: bool = False
    remote_error: Optional[str] = None

    results: Dict[str, List[TestResult]] = field(default_factory=dict)

    def get_results_by_level(self, level: str) -> Dict[str, List[TestResult]]:
        """Get results grouped by provider for a specific level."""
        output = {}
        for provider, results in self.results.items():
            output[provider] = [r for r in results if r.level == level]
        return output


# =============================================================================
# Benchmark Execution
# =============================================================================

def _parse_response(response_text: str) -> tuple:
    """Parse LLM response into artifacts list. Returns (artifacts, success)."""
    if not response_text:
        return [], False

    try:
        clean = response_text.strip()
        # Handle markdown code blocks
        if clean.startswith("```"):
            lines = clean.split('\n')
            end_idx = -1 if lines[-1].strip() in ("```", "```json") else len(lines)
            clean = '\n'.join(lines[1:end_idx]).strip()

        data = json.loads(clean)
        return data.get("artifacts", []), True
    except (json.JSONDecodeError, KeyError, ValueError):
        return [], False


def _run_single_test(
    test_case: Dict,
    provider: LLMProvider,
    provider_name: str,
    model: str,
    timeout_ms: int = 120000
) -> TestResult:
    """Run a single test case on a single provider."""
    start = time.time()

    try:
        response = provider.complete(
            system=Extractor.SYSTEM_PROMPT,
            user=f"Extract artifacts from this text:\n\n{test_case['input']}",
            max_tokens=2048
        )
        latency = (time.time() - start) * 1000

        artifacts, parse_success = _parse_response(response.text)

        return TestResult(
            test_id=test_case["id"],
            test_name=test_case["name"],
            level=test_case["level"],
            provider_name=provider_name,
            model=model,
            latency_ms=latency,
            raw_response=response.text,
            artifacts=artifacts,
            parse_success=parse_success
        )

    except Exception as e:
        latency = (time.time() - start) * 1000
        return TestResult(
            test_id=test_case["id"],
            test_name=test_case["name"],
            level=test_case["level"],
            provider_name=provider_name,
            model=model,
            latency_ms=latency,
            raw_response="",
            artifacts=[],
            parse_success=False,
            error=str(e)
        )


def run_benchmark(
    config: Config,
    local_only: bool = False,
    remote_only: bool = False,
    on_test_complete: callable = None
) -> BenchmarkResults:
    """
    Run the full benchmark suite.

    Args:
        config: Application configuration
        local_only: Only test local provider
        remote_only: Only test remote provider
        on_test_complete: Callback(test_id, provider) called after each test

    Returns:
        BenchmarkResults with all test outcomes
    """
    results = BenchmarkResults()
    providers_to_test = []

    # Always populate provider info for display
    local_cfg = config.llm.local
    remote_cfg = config.llm.remote

    results.local_provider = local_cfg.provider
    results.local_model = local_cfg.effective_model
    results.remote_provider = remote_cfg.provider
    results.remote_model = remote_cfg.effective_model

    # Setup local provider (if not skipped)
    if not remote_only:
        try:
            # Create config forcing local
            local_llm = LLMConfig(
                active="local",
                local=local_cfg,
                remote=remote_cfg
            )
            test_config = Config(
                llm=local_llm,
                display=config.display,
                coherence=config.coherence
            )
            local_provider = get_provider(test_config)

            if isinstance(local_provider, MockProvider):
                results.local_available = False
                results.local_error = f"Ollama not running at {local_cfg.base_url}"
            else:
                results.local_available = True
                providers_to_test.append(("local", local_cfg.provider, local_cfg.effective_model, local_provider))
        except Exception as e:
            results.local_available = False
            results.local_error = str(e)
    else:
        # Skipped by flag
        results.local_available = False
        results.local_error = "Skipped (--remote-only)"

    # Setup remote provider (if not skipped)
    if not local_only:
        if remote_cfg.is_available:
            try:
                # Create config forcing remote
                remote_llm = LLMConfig(
                    active="remote",
                    local=local_cfg,
                    remote=remote_cfg
                )
                test_config = Config(
                    llm=remote_llm,
                    display=config.display,
                    coherence=config.coherence
                )
                remote_provider = get_provider(test_config)
                results.remote_available = True
                providers_to_test.append(("remote", remote_cfg.provider, remote_cfg.effective_model, remote_provider))
            except Exception as e:
                results.remote_available = False
                results.remote_error = str(e)
        else:
            results.remote_available = False
            results.remote_error = f"No API key for {remote_cfg.provider} (set {remote_cfg.api_key_env})"
    else:
        # Skipped by flag
        results.remote_available = False
        results.remote_error = "Skipped (--local-only)"

    # Run tests
    for mode, pname, model, provider in providers_to_test:
        results.results[mode] = []
        for test_case in TEST_CASES:
            result = _run_single_test(test_case, provider, pname, model)
            results.results[mode].append(result)
            if on_test_complete:
                on_test_complete(test_case["id"], mode)

    return results


# =============================================================================
# Output Formatting — Side-by-Side Human-Readable
# =============================================================================

def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def _format_artifact(artifact: Dict, width: int) -> List[str]:
    """Format a single artifact for display."""
    lines = []
    atype = artifact.get("type", "?")
    conf = artifact.get("confidence", 0)
    summary = artifact.get("summary", "")

    # Header line
    lines.append(f"{atype} (conf: {conf:.2f})")

    # Summary wrapped to width
    summary_lines = []
    words = summary.split()
    current_line = ""
    for word in words:
        if len(current_line) + len(word) + 1 <= width - 4:
            current_line += (" " if current_line else "") + word
        else:
            if current_line:
                summary_lines.append(f'  "{current_line}')
            current_line = word
    if current_line:
        summary_lines.append(f'  "{current_line}"' if not summary_lines else f'   {current_line}"')

    lines.extend(summary_lines if summary_lines else ['  "(no summary)"'])
    return lines


def _pad_lines(lines: List[str], target_len: int, width: int) -> List[str]:
    """Pad list of lines to target length with empty strings."""
    result = [line.ljust(width) for line in lines]
    while len(result) < target_len:
        result.append(" " * width)
    return result


def format_results(results: BenchmarkResults) -> str:
    """Format benchmark results as human-readable side-by-side comparison."""
    lines = []
    col_width = 35
    separator = "═" * 78

    # Header
    lines.append(separator)
    lines.append("                        BABEL LLM BENCHMARK")
    lines.append(separator)

    # Provider info
    local_info = f"{results.local_provider}/{results.local_model}" if results.local_provider else "not configured"
    remote_info = f"{results.remote_provider}/{results.remote_model}" if results.remote_provider else "not configured"

    local_status = "✓" if results.local_available else "✗"
    remote_status = "✓" if results.remote_available else "✗"

    lines.append(f"Local:  {local_status} {local_info}")
    if results.local_error:
        lines.append(f"        ({results.local_error})")
    lines.append(f"Remote: {remote_status} {remote_info}")
    if results.remote_error:
        lines.append(f"        ({results.remote_error})")
    lines.append(separator)

    # Group test cases by level
    levels = [
        ("simple", "SIMPLE LEVEL", "Basic extraction: explicit statements, obvious types, valid JSON"),
        ("medium", "MEDIUM LEVEL", "Real-world complexity: multiple artifacts, technical terms, inference"),
        ("high", "HIGH LEVEL", "Nuanced understanding: implicit meaning, ambiguity, unresolved tensions"),
    ]

    for level_key, level_name, level_desc in levels:
        level_cases = [tc for tc in TEST_CASES if tc["level"] == level_key]

        lines.append("")
        lines.append("━" * 78)
        lines.append(f"                           {level_name}")
        lines.append(f"  {level_desc}")
        lines.append("━" * 78)

        for test_case in level_cases:
            # Test header
            lines.append("")
            lines.append(f"┌─ {test_case['id']}: {test_case['name']} " + "─" * (70 - len(test_case['id']) - len(test_case['name'])) + "┐")

            # Input (wrapped)
            input_text = test_case["input"].replace("\n", " ")
            lines.append(f"│ INPUT: {_truncate(input_text, 68)}")
            lines.append(f"│ EXPECTED: {test_case['expected_description']}")
            lines.append(f"│ HINT: {test_case['evaluation_hint']}")
            lines.append("└" + "─" * 76 + "┘")

            # Get results for this test
            local_result = None
            remote_result = None

            if "local" in results.results:
                for r in results.results["local"]:
                    if r.test_id == test_case["id"]:
                        local_result = r
                        break

            if "remote" in results.results:
                for r in results.results["remote"]:
                    if r.test_id == test_case["id"]:
                        remote_result = r
                        break

            # Column headers
            lines.append("")
            local_header = "LOCAL" if local_result else "LOCAL (unavailable)"
            remote_header = "REMOTE" if remote_result else "REMOTE (unavailable)"
            lines.append(f"        {local_header:<35}  {remote_header:<35}")
            lines.append(f"        {'─' * 35}  {'─' * 35}")

            # Timing and status
            local_time = f"{local_result.latency_ms:,.0f} ms" if local_result else "—"
            remote_time = f"{remote_result.latency_ms:,.0f} ms" if remote_result else "—"
            lines.append(f"Time:   {local_time:<35}  {remote_time:<35}")

            local_status = "✓ Parsed" if local_result and local_result.parse_success else ("✗ " + (local_result.error[:30] if local_result and local_result.error else "Parse failed") if local_result else "—")
            remote_status = "✓ Parsed" if remote_result and remote_result.parse_success else ("✗ " + (remote_result.error[:30] if remote_result and remote_result.error else "Parse failed") if remote_result else "—")
            lines.append(f"Status: {local_status:<35}  {remote_status:<35}")

            local_count = f"{local_result.artifact_count} artifact(s)" if local_result else "—"
            remote_count = f"{remote_result.artifact_count} artifact(s)" if remote_result else "—"
            lines.append(f"Found:  {local_count:<35}  {remote_count:<35}")

            # Artifacts side by side
            local_artifacts = local_result.artifacts if local_result else []
            remote_artifacts = remote_result.artifacts if remote_result else []
            max_artifacts = max(len(local_artifacts), len(remote_artifacts), 1)

            lines.append("")

            for i in range(max_artifacts):
                local_art = local_artifacts[i] if i < len(local_artifacts) else None
                remote_art = remote_artifacts[i] if i < len(remote_artifacts) else None

                local_lines = _format_artifact(local_art, col_width) if local_art else ["(none)"]
                remote_lines = _format_artifact(remote_art, col_width) if remote_art else ["(none)" if i == 0 else ""]

                max_lines = max(len(local_lines), len(remote_lines))
                local_lines = _pad_lines(local_lines, max_lines, col_width)
                remote_lines = _pad_lines(remote_lines, max_lines, col_width)

                for j in range(max_lines):
                    prefix = f"[{i+1}] " if j == 0 else "    "
                    lines.append(f"{prefix}{local_lines[j]}  {prefix if j == 0 else '    '}{remote_lines[j]}")

            lines.append("─" * 78)

    # Summary
    lines.append("")
    lines.append(separator)
    lines.append("                              SUMMARY")
    lines.append(separator)
    lines.append("")

    # Stats by level
    lines.append(f"                         {'LOCAL':<20}  {'REMOTE':<20}")
    lines.append(f"                         {'─' * 20}  {'─' * 20}")

    for level_key, level_name, _ in levels:
        local_tests = [r for r in results.results.get("local", []) if r.level == level_key]
        remote_tests = [r for r in results.results.get("remote", []) if r.level == level_key]

        local_passed = sum(1 for r in local_tests if r.parse_success)
        remote_passed = sum(1 for r in remote_tests if r.parse_success)

        local_total = len(local_tests) or 3
        remote_total = len(remote_tests) or 3

        local_stat = f"{local_passed}/{local_total} ✓" if local_tests else "—"
        remote_stat = f"{remote_passed}/{remote_total} ✓" if remote_tests else "—"

        local_avg = f"avg {sum(r.latency_ms for r in local_tests) / len(local_tests):,.0f}ms" if local_tests else ""
        remote_avg = f"avg {sum(r.latency_ms for r in remote_tests) / len(remote_tests):,.0f}ms" if remote_tests else ""

        lines.append(f"{level_name.split()[0]:<12} ({len([tc for tc in TEST_CASES if tc['level'] == level_key])} tests)   {local_stat:<10} {local_avg:<10}  {remote_stat:<10} {remote_avg:<10}")

    lines.append("")
    lines.append(separator)
    lines.append("Evaluate the extractions above. Which captures intent more accurately?")
    lines.append("Consider: correct types, complete rationale, no hallucinations.")
    lines.append(separator)

    return "\n".join(lines)
