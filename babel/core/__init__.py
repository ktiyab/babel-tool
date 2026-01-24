"""
Core — Data layer for Babel CLI

Contains the foundational data structures:
- Events: Immutable event store (source of truth)
- Graph: SQLite projection for queries
- Scope: Shared/local layer management
- Refs: O(1) topic lookups
- Horizon: Token-efficient compression
- Loader: Lazy loading for efficiency
- Domains: P3 expertise governance and domain mapping
- Vocabulary: P2 semantic term learning and expansion
- Resolver: Fuzzy ID resolution for artifact references
- Symbols: Processor-backed code symbol index
"""

from .scope import EventScope, get_default_scope, scope_display_marker, scope_from_string
from .events import (
    Event, EventType, EventStore, DualEventStore,
    capture_conversation, declare_purpose, confirm_artifact, propose_structure,
    capture_commit, record_coherence_check,
    define_term, challenge_term, refine_term, discard_term,
    raise_challenge, add_evidence, resolve_challenge,
    register_decision_for_validation, endorse_decision, evidence_decision,
    raise_question, resolve_question,
    deprecate_artifact
)
from .graph import GraphStore, Node, Edge
from .refs import Ref, RefStore
from .horizon import EventDigest, ArtifactDigest, estimate_tokens
from .loader import LazyLoader, LoadResult
from .domains import (
    DomainSpec, CrossDomainInfo, AIRole,
    infer_domain_from_text, detect_all_domains, detect_external_domains,
    detect_cross_domain_patterns, analyze_cross_domain,
    infer_domain_from_clusters, get_domain_for_scan_type, get_scan_type_for_domain,
    get_clusters_for_domain, list_domains, get_domain_spec,
    score_decision_relevance, get_related_domains,
    suggest_domain_for_capture, validate_domain, get_domain_description,
    CROSS_DOMAIN_PATTERNS, EXTERNAL_DOMAINS
)
from .vocabulary import Vocabulary, expand_query, merge_vocabularies, DEFAULT_CLUSTERS, COMMON_PATTERNS
from .resolver import ResolveStatus, ResolveResult, IDResolver, format_resolve_prompt, resolve_with_prompt
from .symbols import Symbol, CodeSymbolStore

__all__ = [
    # Scope
    "EventScope", "get_default_scope", "scope_display_marker", "scope_from_string",
    # Events
    "Event", "EventType", "EventStore", "DualEventStore",
    "capture_conversation", "declare_purpose", "confirm_artifact", "propose_structure",
    "capture_commit", "record_coherence_check",
    "define_term", "challenge_term", "refine_term", "discard_term",
    "raise_challenge", "add_evidence", "resolve_challenge",
    "register_decision_for_validation", "endorse_decision", "evidence_decision",
    "raise_question", "resolve_question",
    "deprecate_artifact",
    # Graph
    "GraphStore", "Node", "Edge",
    # Refs
    "Ref", "RefStore",
    # Horizon
    "EventDigest", "ArtifactDigest", "estimate_tokens",
    # Loader
    "LazyLoader", "LoadResult",
    # Domains
    "DomainSpec", "CrossDomainInfo", "AIRole",
    "infer_domain_from_text", "detect_all_domains", "detect_external_domains",
    "detect_cross_domain_patterns", "analyze_cross_domain",
    "infer_domain_from_clusters", "get_domain_for_scan_type", "get_scan_type_for_domain",
    "get_clusters_for_domain", "list_domains", "get_domain_spec",
    "score_decision_relevance", "get_related_domains",
    "suggest_domain_for_capture", "validate_domain", "get_domain_description",
    "CROSS_DOMAIN_PATTERNS", "EXTERNAL_DOMAINS",
    # Vocabulary
    "Vocabulary", "expand_query", "merge_vocabularies", "DEFAULT_CLUSTERS", "COMMON_PATTERNS",
    # Resolver
    "ResolveStatus", "ResolveResult", "IDResolver", "format_resolve_prompt", "resolve_with_prompt",
    # Symbols
    "Symbol", "CodeSymbolStore",
]
