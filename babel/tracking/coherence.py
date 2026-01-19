"""
Coherence — Drift detection and checkpoint management (P3)

Observes alignment between purpose and artifacts.
Uses checkpoints for token efficiency.
Surfaces tensions without being alarming.

Token efficiency via horizon.py:
- Artifact digests instead of full content
- Keyword-based conflict detection (no LLM for basic checks)
- Event horizon for old event compression
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field
from pathlib import Path

from ..core.events import EventStore, Event, EventType, record_coherence_check, detect_tension
from ..core.graph import GraphStore, Node
from ..presentation.symbols import get_symbols, SymbolSet, format_artifact, format_status_line, truncate, SUMMARY_LENGTH
from ..config import Config
from ..core.horizon import DigestBuilder, ArtifactDigest, CoherenceContext, _keywords_conflict, _extract_keywords

if TYPE_CHECKING:
    from ..services.providers import LLMProvider


def _short_id(full_id: str) -> str:
    """
    Extract short display ID from full node ID.

    Node IDs are formatted as 'type_hash' (e.g., 'constraint_8e039da3').
    This extracts the hash part for display, not just first 8 chars.

    Examples:
        'constraint_8e039da33828a1d2' -> '8e039da3'
        'decision_abc12345' -> 'abc12345'
        'simple_id' -> 'simple_i'
    """
    if '_' in full_id:
        return full_id.split('_', 1)[1][:8]
    return full_id[:8]


# =============================================================================
# Resolution Hints (guide users to existing mechanisms)
# =============================================================================

RESOLUTION_HINTS = {
    "duplicate": 'Deprecate one: babel deprecate {deprecate_id} "duplicate of {keep_id}"',
    "low_alignment": "Link to purpose: babel link {id}\n  Or deprecate if obsolete: babel deprecate {id} \"no longer relevant\"",
    "tension": "Review conflict: babel challenge {id} \"reason for tension\"",
    "drift": "Challenge the drift: babel challenge {id} \"drifted from original intent\"",
}


# =============================================================================
# AI Resolution System Prompt (P4: Layered Expertise Validation)
# =============================================================================

RESOLUTION_SYSTEM_PROMPT = """You analyze coherence issues in a Babel project to suggest resolutions.

You will receive ENRICHED CONTEXT including:
- PROJECT: Purpose and need (why this project exists)
- PRINCIPLES: Relevant framework principles for this issue type
- ARTIFACT: The issue details with temporal context (when created)
- RELATED: Connected artifacts that provide context
- METADATA: Validation state (endorsements, evidence, purpose links)

Use ALL provided context to make informed suggestions. Pay special attention to:
- TEMPORAL CONTEXT: Recently created artifacts (< 1 hour) may not yet have validation
- PROJECT PURPOSE: Ensure suggestions align with stated project goals
- PRINCIPLES: Apply the specific principles provided for this issue type

Analysis requirements:
1. ANALYZE: Why did this happen? Consider temporal and relational context.
2. RECOMMEND: Best action based on evidence, endorsements, purpose links, AND age.
3. LESSON (P8): What should we learn? Reference specific context.
4. PRINCIPLE (P11): Should this become a principle? Only if pattern is generalizable.

IMPORTANT - Command syntax (use EXACTLY as shown):
- link:      babel link <artifact_id>
- deprecate: babel deprecate <artifact_id> "<reason>"
- challenge: babel challenge <artifact_id> "<reason>"

Return JSON only:
{
    "pattern_analysis": "Why this issue occurred, referencing provided context",
    "recommended_action": "deprecate_first" | "deprecate_second" | "link" | "challenge" | "merge",
    "keep_id": "id to keep (for duplicates)",
    "deprecate_id": "id to deprecate (for duplicates)",
    "suggested_lesson": "What we learned, grounded in context",
    "suggested_principle": "Principle to capture (or null if not warranted)",
    "resolution_command": "Use exact syntax from above. Examples: babel link constraint_abc123 | babel deprecate decision_xyz \\"superseded\\" | babel challenge principle_def \\"needs evidence\\"",
    "confidence": 0.85,
    "reasoning": "Why this recommendation, citing specific context"
}"""


# =============================================================================
# Issue-Specific Principles Registry (Hardcoded from Whitepaper)
# =============================================================================
# Maps issue_type → relevant principles with definitions
# Used to provide targeted context to remote AI without querying DB
# Only relevant principles are sent, not the full whitepaper

ISSUE_PRINCIPLES = {
    "duplicate": {
        "P7": "Evidence-Weighted Memory: Living artifacts, not archives. Deprecated items de-prioritized, not deleted.",
        "P8": "Failure Metabolism: Failures → Lessons → Principles. No silent abandonment - every resolution must extract learning.",
    },
    "low_alignment": {
        "P9": "Coherence Observable: Drift becomes visible early through continuous observation.",
        "Living Cycle": "Coherence observation yields signal (coherent or tension), which triggers re-negotiation: surface to purpose space, revise artifacts, reconcile interpretations.",
    },
    "tension": {
        "P4": "Disagreement as Hypothesis: Disputes are testable claims, not authority-resolved. Require evidence before resolution.",
        "P6": "Empirical Resolution: Build evidence through testing, then resolve based on results.",
    },
    "drift": {
        "P9": "Coherence Observable: Drift becomes visible early. Detection should trigger re-negotiation.",
        "P8": "Failure Metabolism: Learn from drift - understand why it happened, capture lesson, prevent recurrence.",
    },
}


@dataclass
class EntityStatus:
    """Status of a single entity in coherence check."""
    id: str
    node_type: str
    summary: str
    status: str  # "coherent" | "tension" | "drift" | "low_alignment" | "duplicate"
    reason: Optional[str] = None
    related_to: Optional[List[str]] = None  # IDs of related entities (for conflicts)
    resolution_hint: Optional[str] = None  # Suggested command for resolution
    duplicate_of: Optional[str] = None  # ID of duplicate artifact (if status=duplicate)
    severity: Optional[str] = None  # "critical" | "warning" | "info" (P5: graded response)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.node_type,
            "summary": self.summary,
            "status": self.status,
            "reason": self.reason,
            "related_to": self.related_to,
            "resolution_hint": self.resolution_hint,
            "duplicate_of": self.duplicate_of,
            "severity": self.severity
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EntityStatus':
        return cls(
            id=data["id"],
            node_type=data.get("type", "unknown"),
            summary=data.get("summary", ""),
            status=data["status"],
            reason=data.get("reason"),
            related_to=data.get("related_to"),
            resolution_hint=data.get("resolution_hint"),
            duplicate_of=data.get("duplicate_of"),
            severity=data.get("severity")
        )


@dataclass
class ResolutionSuggestion:
    """
    AI-generated suggestion for resolving a coherence issue.

    Follows P4 (Layered Expertise Validation):
    - Remote AI analyzes patterns, suggests action
    - Current AI surfaces to human
    - Human decides

    Ensures P8 (Failure Metabolism) and P11 (Cross-Domain Learning):
    - Always extracts lesson from resolution
    - Offers principle capture for meta-knowledge
    """
    issue_id: str
    issue_type: str  # "duplicate" | "low_alignment" | "tension" | "drift"

    # Analysis from remote AI
    pattern_analysis: str  # WHY this happened
    recommended_action: str  # "deprecate_first" | "deprecate_second" | "link" | "challenge"
    reasoning: str  # Why this recommendation

    # For duplicates
    keep_id: Optional[str] = None
    deprecate_id: Optional[str] = None

    # Meta-knowledge (P8, P11)
    suggested_lesson: Optional[str] = None  # P8: What we learned
    suggested_principle: Optional[str] = None  # P11: Should this become a principle?

    # Executable
    resolution_command: str = ""  # Exact babel command to execute
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "issue_type": self.issue_type,
            "pattern_analysis": self.pattern_analysis,
            "recommended_action": self.recommended_action,
            "reasoning": self.reasoning,
            "keep_id": self.keep_id,
            "deprecate_id": self.deprecate_id,
            "suggested_lesson": self.suggested_lesson,
            "suggested_principle": self.suggested_principle,
            "resolution_command": self.resolution_command,
            "confidence": self.confidence
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResolutionSuggestion':
        return cls(
            issue_id=data.get("issue_id", ""),
            issue_type=data.get("issue_type", "unknown"),
            pattern_analysis=data.get("pattern_analysis", ""),
            recommended_action=data.get("recommended_action", ""),
            reasoning=data.get("reasoning", ""),
            keep_id=data.get("keep_id"),
            deprecate_id=data.get("deprecate_id"),
            suggested_lesson=data.get("suggested_lesson"),
            suggested_principle=data.get("suggested_principle"),
            resolution_command=data.get("resolution_command", ""),
            confidence=data.get("confidence", 0.5)
        )


@dataclass
class CoherenceScope:
    """What was checked in a coherence check."""
    purpose_ids: List[str]
    artifact_ids: List[str]
    since: Optional[str] = None  # Timestamp of last checkpoint
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "purpose_ids": self.purpose_ids,
            "artifact_ids": self.artifact_ids,
            "since": self.since
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CoherenceScope':
        return cls(
            purpose_ids=data.get("purpose_ids", []),
            artifact_ids=data.get("artifact_ids", []),
            since=data.get("since")
        )


@dataclass
class CoherenceResult:
    """Result of a coherence check."""
    checkpoint_id: str
    timestamp: str
    status: str  # "coherent" | "tension" | "drift"
    scope: CoherenceScope
    signals: List[str]
    entities: List[EntityStatus]
    trigger: str
    triggered_by: Optional[str] = None
    from_cache: bool = False
    
    @property
    def has_issues(self) -> bool:
        """Only tensions and drift are issues. Unlinked is informational."""
        return self.status in ("tension", "drift")

    @property
    def tension_count(self) -> int:
        return sum(1 for e in self.entities if e.status == "tension")

    @property
    def drift_count(self) -> int:
        return sum(1 for e in self.entities if e.status == "drift")

    @property
    def low_alignment_count(self) -> int:
        return sum(1 for e in self.entities if e.status == "low_alignment")

    @property
    def coherent_count(self) -> int:
        return sum(1 for e in self.entities if e.status == "coherent")

    @property
    def duplicate_count(self) -> int:
        return sum(1 for e in self.entities if e.status == "duplicate")

    def get_issues(self) -> List[EntityStatus]:
        """Get all entities that need resolution (duplicates, tensions, low_alignment)."""
        return [e for e in self.entities if e.status in ("duplicate", "tension", "drift", "low_alignment")]


class CoherenceChecker:
    """
    Checks alignment between purpose and artifacts.
    
    Token efficiency via:
    - Checkpoint caching (reuse if nothing changed)
    - Incremental checks (only new artifacts)
    - Summary-only comparison (not full content)
    """
    
    # Keywords suggesting different artifact purposes
    PURPOSE_KEYWORDS = {'goal', 'purpose', 'success', 'objective', 'aim', 'build', 'create'}
    CONSTRAINT_KEYWORDS = {'must', 'cannot', 'never', 'always', 'require', 'limit', 'offline', 'only'}
    DECISION_KEYWORDS = {'decided', 'chose', 'use', 'pick', 'select', 'went with'}
    
    def __init__(
        self,
        events: EventStore,
        graph: GraphStore,
        config: Config,
        provider: Optional[Any] = None
    ):
        self.events = events
        self.graph = graph
        self.config = config
        self.provider = provider
        self.symbols = get_symbols(config.display.symbols)
        self.digest_builder = DigestBuilder(graph)
    
    def check(
        self,
        trigger: str = "manual",
        triggered_by: Optional[str] = None,
        force_full: bool = False
    ) -> CoherenceResult:
        """
        Run coherence check.
        
        Args:
            trigger: What triggered this check
            triggered_by: Identifier for trigger source
            force_full: Skip cache, do full check
            
        Returns:
            CoherenceResult with status and entity details
        """
        # Get current state
        purposes = self.graph.get_nodes_by_type("purpose")
        if not purposes:
            return self._empty_result(trigger, triggered_by, "No purpose defined")
        
        # Try to use cached checkpoint
        if not force_full:
            cached = self._try_cache()
            if cached:
                return cached
        
        # Get last checkpoint for incremental check
        last_checkpoint = self._get_last_checkpoint()
        since = last_checkpoint.timestamp if last_checkpoint else None
        
        # Get artifacts to check
        if since and not force_full:
            artifacts = self._get_artifacts_since(since)
        else:
            artifacts = self._get_all_artifacts()
        
        if not artifacts:
            # No artifacts to check - project is coherent by default
            return self._create_result(
                status="coherent",
                scope=CoherenceScope(
                    purpose_ids=[p.id for p in purposes],
                    artifact_ids=[],
                    since=since
                ),
                signals=["No artifacts to check"],
                entities=[],
                trigger=trigger,
                triggered_by=triggered_by
            )
        
        # Run comparison
        entities = self._check_artifacts(purposes, artifacts)
        
        # Determine overall status
        status = self._determine_status(entities)
        
        # Create and save result
        result = self._create_result(
            status=status,
            scope=CoherenceScope(
                purpose_ids=[p.id for p in purposes],
                artifact_ids=[a.id for a in artifacts],
                since=since
            ),
            signals=self._generate_signals(entities),
            entities=entities,
            trigger=trigger,
            triggered_by=triggered_by
        )
        
        self._save_checkpoint(result)
        
        return result
    
    def get_last_result(self) -> Optional[CoherenceResult]:
        """Get most recent coherence check result."""
        checkpoint = self._get_last_checkpoint()
        if not checkpoint:
            return None
        return self._checkpoint_to_result(checkpoint)
    
    def _try_cache(self) -> Optional[CoherenceResult]:
        """Try to return cached result if still valid."""
        last = self._get_last_checkpoint()
        if not last:
            return None
        
        # Check if any new artifacts since checkpoint
        since = last.timestamp  # Event timestamp, not data
        new_artifacts = self._get_artifacts_since(since)
        
        if not new_artifacts:
            # Cache is valid
            result = self._checkpoint_to_result(last)
            result.from_cache = True
            return result
        
        return None
    
    def _get_last_checkpoint(self) -> Optional[Event]:
        """Get most recent coherence checkpoint event."""
        checkpoints = self.events.read_by_type(EventType.COHERENCE_CHECKED)
        return checkpoints[-1] if checkpoints else None
    
    def _get_artifacts_since(self, since: str) -> List[Node]:
        """Get artifacts created after timestamp, excluding deprecated ones."""
        deprecated_ids = self._get_deprecated_ids()
        artifacts = []

        for event in self.events.read_all():
            if event.timestamp <= since:
                continue
            if event.type == EventType.ARTIFACT_CONFIRMED:
                node = self.graph.get_node(f"{event.data['artifact_type']}_{event.id}")
                if node and node.id not in deprecated_ids:
                    artifacts.append(node)

        return artifacts
    
    def _get_deprecated_ids(self) -> set:
        """
        Get all deprecated artifact IDs.

        Reads ARTIFACT_DEPRECATED events to build set of deprecated IDs.
        Used to filter deprecated artifacts from coherence checks.
        """
        deprecated = set()
        events = self.events.read_by_type(EventType.ARTIFACT_DEPRECATED)
        for event in events:
            artifact_id = event.data.get("artifact_id", "")
            if artifact_id:
                deprecated.add(artifact_id)
        return deprecated

    def _get_all_artifacts(self) -> List[Node]:
        """Get all artifacts except purposes and deprecated ones."""
        deprecated_ids = self._get_deprecated_ids()
        artifacts = []
        for node_type in ['decision', 'constraint', 'principle', 'tension']:
            for node in self.graph.get_nodes_by_type(node_type):
                if node.id not in deprecated_ids:
                    artifacts.append(node)
        return artifacts
    
    def _check_artifacts(self, purposes: List[Node], artifacts: List[Node]) -> List[EntityStatus]:
        """
        Check artifacts against purposes using four-tier approach.

        Tier 0: Duplicate detection - same/similar summaries across artifacts
        Tier 1: Graph edges (authoritative) - if linked to purpose → coherent
        Tier 2: Keyword conflicts - check for constraint violations
        Tier 3: Keyword alignment (informational) - low overlap → low_alignment

        Each issue includes resolution_hint pointing to existing mechanisms.
        """
        entities = []
        purpose_ids = {p.id for p in purposes}

        # Build efficient context using digests
        context = self.digest_builder.build_coherence_context(purposes, artifacts)

        # Build purpose keywords for alignment checking
        purpose_keywords = set()
        for p in purposes:
            text = p.content.get('purpose', p.content.get('summary', ''))
            purpose_keywords.update(_extract_keywords(text))

        # Build artifact lookup for graph checks
        artifact_lookup = {a.id: a for a in artifacts}

        # TIER 0: Detect duplicates by summary similarity
        duplicates = self._detect_duplicates(context.artifact_digests)
        duplicate_ids = set()  # Track which IDs are part of duplicate pairs

        for dup_id, original_id in duplicates.items():
            duplicate_ids.add(dup_id)
            duplicate_ids.add(original_id)
            hint = RESOLUTION_HINTS["duplicate"].format(
                deprecate_id=_short_id(dup_id),
                keep_id=_short_id(original_id)
            )
            entities.append(EntityStatus(
                id=dup_id,
                node_type=artifact_lookup.get(dup_id, artifacts[0]).type if artifact_lookup.get(dup_id) else "unknown",
                summary=next((d.summary for d in context.artifact_digests if d.id == dup_id), ""),
                status="duplicate",
                reason=f"Duplicate of [{_short_id(original_id)}]",
                duplicate_of=original_id,
                resolution_hint=hint
            ))

        for digest in context.artifact_digests:
            # Skip if already marked as duplicate
            if digest.id in duplicate_ids and digest.id in duplicates:
                continue

            artifact = artifact_lookup.get(digest.id)

            # TIER 1: Check graph edges (authoritative)
            if artifact:
                incoming = self.graph.get_incoming(artifact.id)
                has_purpose_link = any(
                    edge.source_id in purpose_ids and edge.relation == "supports"
                    for edge, _ in incoming
                )

                if has_purpose_link:
                    entities.append(EntityStatus(
                        id=digest.id,
                        node_type=digest.artifact_type,
                        summary=digest.summary,
                        status="coherent",
                        reason="Linked to purpose"
                    ))
                    continue

            # TIER 2: Fast conflict check using keywords
            conflicts = self.digest_builder.check_conflicts_fast(
                digest,
                context.constraint_keywords
            )

            if conflicts:
                # Grade severity based on conflict characteristics (P5: Adaptive Cycle Rate)
                severity = self._grade_tension_severity(digest, conflicts, context)
                hint = RESOLUTION_HINTS["tension"].format(id=_short_id(digest.id))

                entities.append(EntityStatus(
                    id=digest.id,
                    node_type=digest.artifact_type,
                    summary=digest.summary,
                    status="tension",
                    reason="May conflict with constraints",
                    related_to=conflicts,
                    resolution_hint=hint,
                    severity=severity
                ))

                # Emit TENSION_DETECTED event for auto-detection (P4: AI as pattern detector)
                # This creates graph edges for tensions_with relation
                for conflict_id in conflicts:
                    tension_event = detect_tension(
                        artifact_a_id=digest.id,
                        artifact_b_id=conflict_id,
                        severity=severity,
                        reason=f"Keyword conflict detected between {digest.artifact_type} and constraint",
                        detection_method="auto",
                        author="coherence_checker"
                    )
                    self.events.append(tension_event)

                continue

            # TIER 3: Check keyword alignment (informational)
            artifact_keywords = set(digest.keywords)
            alignment = self._keyword_alignment(artifact_keywords, purpose_keywords)

            # Skip low alignment check for recent artifacts (temporal grace period)
            # Recent artifacts haven't had time to be linked to purpose yet
            is_recent = artifact and self._is_recent_artifact(artifact)

            if alignment < 0.2 and not is_recent:
                hint = RESOLUTION_HINTS["low_alignment"].format(id=_short_id(digest.id))
                entities.append(EntityStatus(
                    id=digest.id,
                    node_type=digest.artifact_type,
                    summary=digest.summary,
                    status="low_alignment",
                    reason="Weak keyword alignment with purpose",
                    resolution_hint=hint
                ))
            else:
                reason = "Recently created (grace period)" if is_recent and alignment < 0.2 else None
                entities.append(EntityStatus(
                    id=digest.id,
                    node_type=digest.artifact_type,
                    summary=digest.summary,
                    status="coherent",
                    reason=reason
                ))

        return entities

    def _detect_duplicates(self, digests: List[ArtifactDigest], threshold: float = 0.85) -> Dict[str, str]:
        """
        Detect duplicate artifacts by summary similarity.

        Returns dict mapping duplicate_id -> original_id (first seen wins).
        Uses Jaccard similarity on keywords for efficiency (no LLM needed).
        """
        duplicates = {}
        seen_summaries: List[Tuple[str, str, set]] = []  # (id, summary, keywords)

        for digest in digests:
            summary_lower = digest.summary.lower().strip()
            keywords = set(digest.keywords)

            # Check against already seen
            for seen_id, seen_summary, seen_keywords in seen_summaries:
                # Exact match
                if summary_lower == seen_summary.lower().strip():
                    duplicates[digest.id] = seen_id
                    break

                # High keyword similarity
                if seen_keywords and keywords:
                    intersection = keywords & seen_keywords
                    union = keywords | seen_keywords
                    similarity = len(intersection) / len(union) if union else 0

                    if similarity >= threshold:
                        duplicates[digest.id] = seen_id
                        break
            else:
                # Not a duplicate, add to seen
                seen_summaries.append((digest.id, digest.summary, keywords))

        return duplicates
    
    def _keyword_alignment(self, artifact_kw: set, purpose_kw: set) -> float:
        """Check keyword overlap as alignment proxy."""
        if not artifact_kw or not purpose_kw:
            return 0.5  # Neutral if can't compare

        intersection = artifact_kw & purpose_kw
        union = artifact_kw | purpose_kw

        return len(intersection) / len(union) if union else 0.5

    def _grade_tension_severity(
        self,
        digest: ArtifactDigest,
        conflicts: List[str],
        context: CoherenceContext
    ) -> str:
        """
        Grade tension severity based on conflict characteristics (P5: Adaptive Cycle Rate).

        Args:
            digest: The artifact digest in tension
            conflicts: List of conflicting artifact IDs
            context: Coherence context with constraint info

        Returns:
            "critical" | "warning" | "info"

        Severity grading:
        - CRITICAL: Multiple conflicts OR conflicts with hard constraints OR fundamental purpose conflict
        - WARNING: Single conflict with soft constraint OR unclear conflict scope
        - INFO: Minor keyword overlap without semantic conflict
        """
        # Multiple conflicts → CRITICAL (compounding issues)
        if len(conflicts) > 2:
            return "critical"

        # Check if any conflict is with a hard constraint
        # Note: constraint_keywords is a dict mapping constraint_id -> keyword list
        for conflict_id in conflicts:
            if conflict_id in context.constraint_keywords:
                # Look up the constraint summary from artifact digests
                for art_digest in context.artifact_digests:
                    if art_digest.id == conflict_id:
                        constraint_text = art_digest.summary.lower()
                        # Hard constraint indicators
                        if any(word in constraint_text for word in ['must', 'never', 'cannot', 'always', 'required']):
                            return "critical"
                        break

        # Check artifact type - some types are more critical
        if digest.artifact_type in ('constraint', 'principle'):
            return "warning"  # Constraints/principles in tension are at least warning-level

        # Default to info for minor keyword overlaps
        if len(conflicts) == 1:
            return "info"

        return "warning"

    def _is_recent_artifact(self, node: Node, grace_seconds: int = 3600) -> bool:
        """
        Check if artifact was created within the grace period.

        Recent artifacts (default < 1 hour) should not be flagged for low alignment
        as they haven't had time to be linked to purpose yet.

        Args:
            node: The artifact node to check
            grace_seconds: Grace period in seconds (default 1 hour)

        Returns:
            True if artifact is within grace period
        """
        if not node.event_id:
            return False

        # Find the source event
        for event in self.events.read_all():
            if event.id == node.event_id:
                try:
                    event_time = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))
                    now = datetime.now(timezone.utc)
                    age_seconds = (now - event_time).total_seconds()
                    return age_seconds < grace_seconds
                except (ValueError, TypeError):
                    return False

        return False
    
    def _determine_status(self, entities: List[EntityStatus]) -> str:
        """Determine overall status from entity statuses."""
        if any(e.status == "drift" for e in entities):
            return "drift"
        if any(e.status == "tension" for e in entities):
            return "tension"
        if any(e.status == "duplicate" for e in entities):
            return "tension"  # Duplicates are a form of tension requiring resolution
        # "low_alignment" is informational, not a problem - project remains coherent
        return "coherent"

    def _generate_signals(self, entities: List[EntityStatus]) -> List[str]:
        """Generate human-readable signals from entity statuses."""
        signals = []

        duplicates = [e for e in entities if e.status == "duplicate"]
        tensions = [e for e in entities if e.status == "tension"]
        low_alignment = [e for e in entities if e.status == "low_alignment"]

        if duplicates:
            signals.append(f"{len(duplicates)} duplicate artifact(s) detected")
        if tensions:
            signals.append(f"{len(tensions)} artifact(s) may conflict with constraints")
        if low_alignment:
            signals.append(f"{len(low_alignment)} artifact(s) have weak alignment with purpose")
        if not duplicates and not tensions and not low_alignment:
            signals.append("All artifacts align with purpose")

        return signals
    
    def _create_result(
        self,
        status: str,
        scope: CoherenceScope,
        signals: List[str],
        entities: List[EntityStatus],
        trigger: str,
        triggered_by: Optional[str]
    ) -> CoherenceResult:
        """Create a coherence result."""
        checkpoint_id = f"chk_{hashlib.sha256(f'{datetime.now(timezone.utc).isoformat()}{status}'.encode()).hexdigest()[:12]}"
        
        return CoherenceResult(
            checkpoint_id=checkpoint_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            status=status,
            scope=scope,
            signals=signals,
            entities=entities,
            trigger=trigger,
            triggered_by=triggered_by
        )
    
    def _save_checkpoint(self, result: CoherenceResult):
        """Save checkpoint as event."""
        event = record_coherence_check(
            checkpoint_id=result.checkpoint_id,
            status=result.status,
            scope=result.scope.to_dict(),
            signals=result.signals,
            entities=[e.to_dict() for e in result.entities],
            trigger=result.trigger,
            triggered_by=result.triggered_by
        )
        self.events.append(event)
    
    def _checkpoint_to_result(self, event: Event) -> CoherenceResult:
        """Convert checkpoint event to result."""
        data = event.data
        return CoherenceResult(
            checkpoint_id=data["checkpoint_id"],
            timestamp=event.timestamp,
            status=data["status"],
            scope=CoherenceScope.from_dict(data["scope"]),
            signals=data["signals"],
            entities=[EntityStatus.from_dict(e) for e in data["entities"]],
            trigger=data["trigger"],
            triggered_by=data.get("triggered_by")
        )
    
    def _empty_result(self, trigger: str, triggered_by: Optional[str], reason: str) -> CoherenceResult:
        """Create empty result when check can't be performed."""
        return CoherenceResult(
            checkpoint_id="none",
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="ambiguous",
            scope=CoherenceScope([], [], None),
            signals=[reason],
            entities=[],
            trigger=trigger,
            triggered_by=triggered_by
        )

    # =========================================================================
    # Context Gathering Helpers (for AI Resolution)
    # =========================================================================

    def _get_project_context(self) -> Dict[str, str]:
        """
        Gather project context for AI resolution.

        Reuses Scanner pattern - aggregates from graph without transformation.
        Returns purpose and need as raw strings.
        """
        context = {}

        # Get purpose
        purposes = self.graph.get_nodes_by_type("purpose")
        if purposes:
            purpose_node = purposes[0]
            context["purpose"] = purpose_node.content.get("purpose", "")
            context["need"] = purpose_node.content.get("need", "")

        return context

    def _get_artifact_age(self, artifact_id: str) -> Optional[str]:
        """
        Calculate artifact age from creation event.

        Returns human-readable age string (e.g., "2 hours ago", "3 days ago").
        Returns None if event not found.
        """
        # Find the creation event for this artifact
        for event in self.events.read_all():
            if event.type == EventType.ARTIFACT_CONFIRMED:
                # Event ID is embedded in artifact ID (e.g., "decision_abc123")
                if artifact_id.endswith(event.id) or event.id in artifact_id:
                    return _format_age(event.timestamp)

        return None

    def _get_related_artifacts(self, artifact_id: str) -> List[Dict[str, str]]:
        """
        Get artifacts related to the given one (incoming and outgoing edges).

        Returns list of dicts with id, type, summary, relation for context.
        """
        related = []

        # Get incoming edges (artifacts that point TO this one)
        incoming = self.graph.get_incoming(artifact_id)
        for edge, source_node in incoming:
            if source_node:
                related.append({
                    "id": source_node.id,
                    "type": source_node.type,
                    "summary": source_node.content.get("summary", "")[:100],
                    "relation": f"{edge.relation} (incoming)"
                })

        # Get outgoing edges (artifacts this one points TO)
        outgoing = self.graph.get_outgoing(artifact_id)
        for edge, target_node in outgoing:
            if target_node:
                related.append({
                    "id": target_node.id,
                    "type": target_node.type,
                    "summary": target_node.content.get("summary", "")[:100],
                    "relation": f"{edge.relation} (outgoing)"
                })

        return related

    # =========================================================================
    # AI-Assisted Resolution (P4: Layered Expertise Validation)
    # =========================================================================

    def suggest_resolution(self, entity: EntityStatus) -> Optional[ResolutionSuggestion]:
        """
        Ask remote AI to suggest resolution for a coherence issue.

        Follows P4 (Layered Expertise Validation):
        - Remote AI analyzes patterns, suggests action
        - Returns suggestion for current AI to surface to human
        - Human makes final decision

        Ensures P8 (Failure Metabolism) and P11 (Cross-Domain Learning):
        - Always suggests lesson extraction
        - Offers principle capture when pattern detected

        Returns None if LLM unavailable (falls back to hint-only mode).
        """
        if not self.provider or not getattr(self.provider, 'is_available', False):
            return None

        # Build context for the AI
        context = self._build_resolution_context(entity)

        try:
            response = self.provider.complete(
                system=RESOLUTION_SYSTEM_PROMPT,
                user=context,
                max_tokens=1000
            )
            return self._parse_resolution_response(response.text, entity)
        except Exception:
            return None

    def _build_resolution_context(self, entity: EntityStatus) -> str:
        """
        Build enriched context for resolution AI.

        Aggregates from local queries WITHOUT transformation:
        - PROJECT: Purpose and need from graph
        - PRINCIPLES: Relevant framework principles from ISSUE_PRINCIPLES registry
        - ARTIFACT: Issue details with temporal context
        - RELATED: Connected artifacts for context
        - METADATA: Validation state (endorsements, evidence, purpose links)
        """
        lines = []

        # === PROJECT CONTEXT (from graph) ===
        project = self._get_project_context()
        lines.append("PROJECT:")
        lines.append(f"  Purpose: {project.get('purpose', 'Not defined')}")
        if project.get('need'):
            lines.append(f"  Need: {project.get('need')}")
        lines.append("")

        # === RELEVANT PRINCIPLES (from ISSUE_PRINCIPLES registry) ===
        principles = ISSUE_PRINCIPLES.get(entity.status, {})
        if principles:
            lines.append("PRINCIPLES (relevant to this issue type):")
            for p_id, p_text in principles.items():
                lines.append(f"  {p_id}: {p_text}")
            lines.append("")

        # === ARTIFACT DETAILS ===
        lines.append("ARTIFACT:")
        lines.append(f"  Issue type: {entity.status}")
        lines.append(f"  ID: {entity.id}")
        lines.append(f"  Type: {entity.node_type}")
        lines.append(f"  Summary: {entity.summary}")

        # Temporal context
        age = self._get_artifact_age(entity.id)
        if age:
            lines.append(f"  Age: {age}")
        else:
            lines.append(f"  Age: Unknown (new or no event found)")

        if entity.reason:
            lines.append(f"  Detection reason: {entity.reason}")

        if entity.duplicate_of:
            lines.append(f"  Duplicate of: {entity.duplicate_of}")
            # Get the original artifact's info
            original = self.graph.get_node(entity.duplicate_of)
            if original:
                lines.append(f"  Original summary: {original.content.get('summary', '')}")
                original_age = self._get_artifact_age(entity.duplicate_of)
                if original_age:
                    lines.append(f"  Original age: {original_age}")
        lines.append("")

        # === RELATED ARTIFACTS (from graph edges) ===
        related = self._get_related_artifacts(entity.id)
        if related:
            lines.append("RELATED ARTIFACTS:")
            for r in related[:5]:  # Limit to 5 for token efficiency
                lines.append(f"  [{_short_id(r['id'])}] {r['type']}: {r['summary']}")
                lines.append(f"    Relation: {r['relation']}")
            lines.append("")

        # === VALIDATION METADATA (from graph edges) ===
        artifact = self.graph.get_node(entity.id)
        if artifact:
            incoming = self.graph.get_incoming(entity.id)
            endorsements = sum(1 for e, _ in incoming if e.relation == "endorses")
            evidence = sum(1 for e, _ in incoming if e.relation == "evidences")
            purpose_links = sum(1 for e, _ in incoming if e.relation == "supports")

            lines.append("METADATA:")
            lines.append(f"  Endorsements: {endorsements}")
            lines.append(f"  Evidence items: {evidence}")
            lines.append(f"  Purpose links: {purpose_links}")

            # Derive validation state
            if endorsements > 0 and evidence > 0:
                lines.append(f"  Validation: VALIDATED (consensus + evidence)")
            elif endorsements > 0:
                lines.append(f"  Validation: Consensus only (no evidence)")
            elif evidence > 0:
                lines.append(f"  Validation: Evidence only (no consensus)")
            else:
                lines.append(f"  Validation: Proposed (neither)")
            lines.append("")

        lines.append("Analyze this issue using ALL context above. Apply the PRINCIPLES provided.")

        return "\n".join(lines)

    def _parse_resolution_response(self, response: str, entity: EntityStatus) -> Optional[ResolutionSuggestion]:
        """Parse AI response into ResolutionSuggestion."""
        try:
            # Handle markdown code blocks
            clean = response.strip()
            if "```json" in clean:
                clean = clean.split("```json")[1].split("```")[0]
            elif "```" in clean:
                clean = clean.split("```")[1].split("```")[0]

            data = json.loads(clean.strip())

            return ResolutionSuggestion(
                issue_id=entity.id,
                issue_type=entity.status,
                pattern_analysis=data.get("pattern_analysis", "Unable to determine pattern"),
                recommended_action=data.get("recommended_action", ""),
                reasoning=data.get("reasoning", ""),
                keep_id=data.get("keep_id"),
                deprecate_id=data.get("deprecate_id"),
                suggested_lesson=data.get("suggested_lesson"),
                suggested_principle=data.get("suggested_principle"),
                resolution_command=data.get("resolution_command", ""),
                confidence=float(data.get("confidence", 0.5))
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            return None


def format_coherence_status(result: CoherenceResult, symbols: SymbolSet, verbose: bool = False, full: bool = False) -> str:
    """
    Format coherence result for CLI display.

    Args:
        result: Coherence check result
        symbols: Symbol set for display
        verbose: Show detailed counts
        full: Show full content without truncation

    Includes resolution hints per Living Cycle re-negotiation step.
    """
    lines = []

    # Status line
    if result.from_cache:
        age = _format_age(result.timestamp)
        status_detail = f"checked {age} (cached)"
    else:
        status_detail = "just checked"

    lines.append(format_status_line(symbols, result.status, status_detail))

    has_issues = result.has_issues or result.duplicate_count > 0
    if not has_issues and result.low_alignment_count == 0 and not verbose:
        return "\n".join(lines)

    # Show duplicates (require resolution) - grouped by original
    if result.duplicate_count > 0:
        lines.append("")
        # Group duplicates by their original
        originals: Dict[str, List[EntityStatus]] = {}
        for entity in result.entities:
            if entity.status == "duplicate" and entity.duplicate_of:
                if entity.duplicate_of not in originals:
                    originals[entity.duplicate_of] = []
                originals[entity.duplicate_of].append(entity)

        lines.append(f"Duplicates ({result.duplicate_count} duplicate(s) of {len(originals)} original(s)):")
        for original_id, duplicates in originals.items():
            # Show original (to keep)
            original_short = _short_id(original_id)
            # Get original summary from first duplicate's similar content
            original_summary = truncate(duplicates[0].summary, SUMMARY_LENGTH - 10, full)
            lines.append(f"  {symbols.coherent} [{original_short}] {original_summary} (KEEP)")
            # Show duplicates (to deprecate)
            for dup in duplicates:
                dup_short = _short_id(dup.id)
                lines.append(f"      {symbols.arrow} [{dup_short}] duplicate (deprecate)")
            if full and duplicates[0].resolution_hint:
                lines.append(f"      Hint: {duplicates[0].resolution_hint}")

    # Show tensions (issues) - grouped by severity (P5: Adaptive Cycle Rate)
    if result.tension_count > 0:
        lines.append("")
        # Group by severity for prioritized display
        severity_order = {'critical': 0, 'warning': 1, 'info': 2, None: 3}
        tension_entities = [e for e in result.entities if e.status in ("tension", "drift")]
        tension_entities.sort(key=lambda e: severity_order.get(e.severity, 3))

        lines.append(f"Tensions ({result.tension_count}):")
        for entity in tension_entities:
            short_id = _short_id(entity.id)
            summary = truncate(entity.summary, SUMMARY_LENGTH, full)
            # Show severity indicator
            severity_icon = {
                'critical': '!!',
                'warning': '!',
                'info': '~'
            }.get(entity.severity, '')
            severity_suffix = f" [{entity.severity}]" if entity.severity else ""
            lines.append(f"  {severity_icon}[{short_id}] {summary}{severity_suffix}")
            if entity.reason:
                lines.append(f"      {entity.reason}")
            if entity.related_to:
                lines.append(f"      Related: {', '.join(entity.related_to)}")
            if full and entity.resolution_hint:
                lines.append(f"      {symbols.arrow} {entity.resolution_hint}")

    # Show low alignment (informational, not issues)
    # Dual-Display: [ID] + summary for comprehension AND action
    if result.low_alignment_count > 0:
        lines.append("")
        lines.append(f"Low alignment ({result.low_alignment_count}):")
        for entity in result.entities:
            if entity.status == "low_alignment":
                short_id = _short_id(entity.id)
                summary = truncate(entity.summary, SUMMARY_LENGTH, full)
                lines.append(f"  [{short_id}] {summary}")
                if full and entity.reason:
                    lines.append(f"      {entity.reason}")
                if full and entity.resolution_hint:
                    lines.append(f"      {symbols.arrow} {entity.resolution_hint}")

    # Summary counts
    lines.append("")
    lines.append(f"Checked {len(result.entities)} artifact(s):")
    lines.append(f"  {symbols.coherent} {result.coherent_count} coherent")
    if result.duplicate_count:
        lines.append(f"  {symbols.tension} {result.duplicate_count} duplicate")
    if result.tension_count:
        lines.append(f"  {symbols.tension} {result.tension_count} tension")
    if result.low_alignment_count:
        lines.append(f"  [~] {result.low_alignment_count} low alignment")

    # Resolution guidance (Living Cycle: re-negotiation step)
    issue_count = result.duplicate_count + result.tension_count + result.low_alignment_count
    if issue_count > 0:
        lines.append("")
        if result.from_cache:
            age = _format_age(result.timestamp)
            lines.append(f"(Cached result from {age}. Run --force for fresh check)")
        lines.append(f"{symbols.arrow} Next: babel coherence --resolve  (Walk through issues with AI guidance)")

    return "\n".join(lines)


def format_coherence_report(result: CoherenceResult, symbols: SymbolSet, purposes: List[Node], full: bool = False) -> str:
    """
    Format full coherence report for QA/QC.

    Args:
        result: Coherence check result
        symbols: Symbol set for display
        purposes: List of purpose nodes
        full: Show full content without truncation
    """
    lines = [
        "COHERENCE REPORT",
        "=" * 40,
        f"Timestamp: {result.timestamp}",
        f"Trigger: {result.trigger}",
        f"Checkpoint: {result.checkpoint_id}",
        ""
    ]

    # Purpose(s)
    for p in purposes:
        purpose_text = p.content.get('purpose', p.content.get('summary', ''))
        lines.append(f"{symbols.purpose} Purpose: {truncate(purpose_text, SUMMARY_LENGTH, full)}")
        lines.append(f"   Status: {symbols.coherent if result.status == 'coherent' else symbols.tension} {result.status}")

    lines.append("")

    # Findings
    if result.entities:
        lines.append("Findings:")
        for i, entity in enumerate(result.entities, 1):
            summary = truncate(entity.summary, SUMMARY_LENGTH, full)
            lines.append(f"  {i}. {format_artifact(symbols, entity.node_type, summary, entity.status)}")
            if entity.reason:
                lines.append(f"     - {entity.reason}")
            if entity.related_to:
                lines.append(f"     - Related: {', '.join(entity.related_to)}")
        lines.append("")

    # Summary
    lines.append(f"Summary: {result.tension_count} tension, {result.coherent_count} coherent, {result.low_alignment_count} low alignment")

    if result.low_alignment_count > 0:
        lines.append("")
        lines.append("Low alignment artifacts have weak keyword overlap with purpose.")
        lines.append("This is informational - consider reviewing if alignment matters.")

    return "\n".join(lines)


def _format_age(timestamp: str) -> str:
    """Format timestamp as human-readable age."""
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        delta = now - dt
        
        seconds = delta.total_seconds()
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            mins = int(seconds / 60)
            return f"{mins}m ago"
        if seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours}h ago"
        days = int(seconds / 86400)
        return f"{days}d ago"
    except Exception:
        return "unknown"
