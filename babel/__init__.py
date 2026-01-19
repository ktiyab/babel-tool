"""
Babel — Intent Preservation Tool

Captures reasoning. Answers 'why?'. Quiet until needed.

Git-informed scalability:
- Refs for O(1) lookup (like Git branches)
- Lazy loading (only what's traversed)
- Token-efficient by design

Usage:
    babel init "Build something great"
    babel capture "We decided to use Python"
    babel capture "Share this decision" --share
    babel why "Python"
    babel status
    babel coherence
    babel share <event_id>
    babel sync
    babel config
    babel hooks install
"""

__version__ = "0.1.0"

# Core layer (data)
from .core.events import EventStore, DualEventStore, Event, EventType
from .core.scope import EventScope, get_default_scope, scope_display_marker
from .core.graph import GraphStore, Node, Edge
from .core.horizon import EventHorizon, DigestBuilder, ArtifactDigest, CoherenceContext, HorizonSnapshot
from .core.refs import RefStore, Ref, extract_topics
from .core.loader import LazyLoader, LoadResult, TokenBudget

# Tracking layer
from .tracking.coherence import CoherenceChecker, CoherenceResult, EntityStatus
from .tracking.validation import ValidationStatus, DecisionValidation, ValidationTracker
from .tracking.tensions import TensionTracker, Challenge
from .tracking.ambiguity import OpenQuestion, QuestionTracker

# Services layer
from .services.extractor import Extractor, Proposal
from .services.providers import get_provider, LLMProvider
from .services.git import GitIntegration, CommitInfo, StructuralChanges
from .services.scanner import Scanner, ScanResult, ScanFinding, ScanContext, format_scan_result

# Presentation layer
from .presentation.symbols import get_symbols, SymbolSet, UNICODE, ASCII

# Config (stays at root)
from .config import Config, ConfigManager, get_config, DisplayConfig, CoherenceConfig

# Core knowledge modules (now in core/)
from .core.vocabulary import Vocabulary, expand_query, merge_vocabularies
from .core.domains import DomainSpec, infer_domain_from_text, suggest_domain_for_capture
from .core.resolver import IDResolver, ResolveStatus, ResolveResult

__all__ = [
    # Core
    'EventStore', 'DualEventStore', 'Event', 'EventType',
    'EventScope', 'get_default_scope', 'scope_display_marker',
    'GraphStore', 'Node', 'Edge',
    'EventHorizon', 'DigestBuilder', 'ArtifactDigest', 'CoherenceContext', 'HorizonSnapshot',
    'RefStore', 'Ref', 'extract_topics',
    'LazyLoader', 'LoadResult', 'TokenBudget',
    # Tracking
    'CoherenceChecker', 'CoherenceResult', 'EntityStatus',
    'ValidationStatus', 'DecisionValidation', 'ValidationTracker',
    'TensionTracker', 'Challenge',
    'OpenQuestion', 'QuestionTracker',
    # Services
    'Extractor', 'Proposal',
    'get_provider', 'LLMProvider',
    'GitIntegration', 'CommitInfo', 'StructuralChanges',
    'Scanner', 'ScanResult', 'ScanFinding', 'ScanContext', 'format_scan_result',
    # Presentation
    'get_symbols', 'SymbolSet', 'UNICODE', 'ASCII',
    # Config
    'Config', 'ConfigManager', 'get_config', 'DisplayConfig', 'CoherenceConfig',
    # Core knowledge
    'Vocabulary', 'expand_query', 'merge_vocabularies',
    'DomainSpec', 'infer_domain_from_text', 'suggest_domain_for_capture',
    'IDResolver', 'ResolveStatus', 'ResolveResult',
]
