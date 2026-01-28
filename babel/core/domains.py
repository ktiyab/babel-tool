"""
Domains — Unified expertise and semantic mapping (P3 compliant)

P3: Authority and Participation (Expertise Governance)
- Authority derives from declared, bounded expertise
- Participants state which domain their claims apply to
- AI participates as pattern detector, synthesizer, challenger (not arbiter)

Domain unification:
- Capture domain (who knows) ←→ Scan type (what we check) ←→ Vocabulary cluster (terms)
- Auto-inference from vocabulary clusters
- Expertise weighting in scans

This module provides the mapping between domains, scan types, and vocabulary clusters,
enabling meaningful connections across the system.
"""

from typing import Optional, List, Dict
from dataclasses import dataclass


# =============================================================================
# Domain Registry (P3: Expertise Governance)
# =============================================================================

@dataclass
class DomainSpec:
    """Specification for a domain."""
    name: str
    scan_type: str
    vocab_clusters: List[str]
    keywords: List[str]
    description: str


# Core domain registry — maps expertise domains to scan types and vocabulary
DOMAIN_REGISTRY: Dict[str, DomainSpec] = {
    "security": DomainSpec(
        name="security",
        scan_type="security",
        vocab_clusters=["security", "auth"],
        keywords=["bcrypt", "ssl", "tls", "vulnerability", "oauth", "jwt", 
                  "encryption", "password", "credential", "xss", "csrf", "injection"],
        description="Security, authentication, and authorization expertise"
    ),
    "performance": DomainSpec(
        name="performance",
        scan_type="performance",
        vocab_clusters=["caching", "performance"],
        keywords=["cache", "latency", "throughput", "optimization", "scale",
                  "redis", "memcached", "cdn", "load", "benchmark", "profiling"],
        description="Performance optimization and caching expertise"
    ),
    "architecture": DomainSpec(
        name="architecture",
        scan_type="architecture",
        vocab_clusters=["api", "database", "cloud", "backend"],
        keywords=["pattern", "microservice", "monolith", "rest", "graphql",
                  "event-driven", "cqrs", "saga", "domain-driven", "hexagonal"],
        description="System architecture and design patterns expertise"
    ),
    "reliability": DomainSpec(
        name="reliability",
        scan_type="health",
        vocab_clusters=["testing", "offline"],
        keywords=["test", "resilience", "failover", "backup", "recovery",
                  "monitoring", "alerting", "sre", "chaos", "availability"],
        description="Reliability, testing, and operational expertise"
    ),
    "dependencies": DomainSpec(
        name="dependencies",
        scan_type="dependencies",
        vocab_clusters=["frontend", "backend"],
        keywords=["npm", "pip", "package", "version", "upgrade", "dependency",
                  "library", "framework", "breaking", "migration", "deprecation"],
        description="Dependency management and upgrades expertise"
    ),
    "frontend": DomainSpec(
        name="frontend",
        scan_type="architecture",
        vocab_clusters=["frontend"],
        keywords=["react", "vue", "angular", "css", "component", "ui", "ux",
                  "responsive", "accessibility", "a11y", "animation", "state"],
        description="Frontend development and UI/UX expertise"
    ),
    "data": DomainSpec(
        name="data",
        scan_type="architecture",
        vocab_clusters=["database"],
        keywords=["postgresql", "mysql", "mongodb", "schema", "migration",
                  "index", "query", "orm", "nosql", "replication", "sharding"],
        description="Data modeling and database expertise"
    ),
    "devops": DomainSpec(
        name="devops",
        scan_type="health",
        vocab_clusters=["cloud", "testing"],
        keywords=["docker", "kubernetes", "ci", "cd", "pipeline", "deploy",
                  "terraform", "ansible", "helm", "gitops", "infrastructure"],
        description="DevOps, CI/CD, and infrastructure expertise"
    ),
}


# =============================================================================
# Domain Inference
# =============================================================================

def infer_domain_from_text(text: str) -> Optional[str]:
    """
    Infer domain from text content using keyword matching.
    
    Returns the best-matching domain or None if no strong match.
    """
    text_lower = text.lower()
    
    scores: Dict[str, int] = {}
    
    for domain_name, spec in DOMAIN_REGISTRY.items():
        score = 0
        for keyword in spec.keywords:
            if keyword in text_lower:
                score += 1
        if score > 0:
            scores[domain_name] = score
    
    if not scores:
        return None
    
    # Return domain with highest score
    best_domain = max(scores.keys(), key=lambda d: scores[d])
    
    # Only return if reasonably confident (at least 1 keyword match)
    return best_domain if scores[best_domain] >= 1 else None


# =============================================================================
# P10: Cross-Domain Learning
# =============================================================================

# Patterns that indicate cross-domain reference
CROSS_DOMAIN_PATTERNS = [
    "borrowed from", "from the", "from a", "like in",
    "similar to how", "analogous to", "applying",
    "thinking to", "approach to", "style",
    "(from", "inspired by", "taken from",
    "pattern from", "principle from", "concept from",
    "security thinking", "performance thinking", "architecture thinking"
]

# External domains (not in our registry but commonly referenced)
EXTERNAL_DOMAINS = {
    "electrical": ["circuit breaker", "fuse", "load balancing", "impedance"],
    "biology": ["evolution", "mutation", "adaptation", "organism", "ecosystem"],
    "economics": ["market", "supply", "demand", "equilibrium", "scarcity"],
    "physics": ["entropy", "momentum", "inertia", "force", "energy"],
    "military": ["strategy", "tactics", "defense in depth", "flanking"],
    "medicine": ["diagnosis", "prognosis", "symptom", "treatment", "triage"],
    "psychology": ["cognitive", "behavioral", "mental model", "bias"],
    "manufacturing": ["lean", "kanban", "just in time", "assembly line"],
}


@dataclass
class CrossDomainInfo:
    """Information about cross-domain references in text."""
    primary_domain: Optional[str]
    all_domains: List[str]
    external_domains: List[str]
    cross_domain_phrases: List[str]
    has_cross_domain: bool
    
    def summary(self) -> str:
        """Generate summary of cross-domain references."""
        if not self.has_cross_domain:
            return ""
        
        parts = []
        if self.external_domains:
            parts.append(f"from {', '.join(self.external_domains)}")
        if len(self.all_domains) > 1:
            secondary = [d for d in self.all_domains if d != self.primary_domain]
            if secondary:
                parts.append(f"references {', '.join(secondary)}")
        
        return " | ".join(parts) if parts else ""


def detect_all_domains(text: str) -> List[str]:
    """
    Detect ALL domains mentioned in text (not just primary).
    
    Used for cross-domain reference detection.
    """
    text_lower = text.lower()
    found_domains = []
    
    for domain_name, spec in DOMAIN_REGISTRY.items():
        score = 0
        for keyword in spec.keywords:
            if keyword in text_lower:
                score += 1
        if score > 0:
            found_domains.append((domain_name, score))
    
    # Sort by score descending
    found_domains.sort(key=lambda x: x[1], reverse=True)
    
    return [d[0] for d in found_domains]


def detect_external_domains(text: str) -> List[str]:
    """
    Detect references to external domains (outside our registry).
    
    P10: Cross-domain learning reveals limits and assumptions.
    """
    text_lower = text.lower()
    found = []
    
    for domain_name, keywords in EXTERNAL_DOMAINS.items():
        for keyword in keywords:
            if keyword in text_lower:
                found.append(domain_name)
                break  # One match per domain is enough
    
    return found


def detect_cross_domain_patterns(text: str) -> List[str]:
    """
    Detect phrases indicating cross-domain borrowing.
    
    P10: Importing analogies or principles must state their source domain.
    """
    text_lower = text.lower()
    found = []
    
    for pattern in CROSS_DOMAIN_PATTERNS:
        if pattern in text_lower:
            # Extract context around the pattern
            idx = text_lower.index(pattern)
            start = max(0, idx - 20)
            end = min(len(text), idx + len(pattern) + 30)
            context = text[start:end].strip()
            found.append(context)
    
    return found


def analyze_cross_domain(text: str) -> CrossDomainInfo:
    """
    Analyze text for cross-domain references (P10 compliance).
    
    P10: Cross-Domain Learning
    - Cross-domain references are encouraged when domain boundaries stressed
    - Importing analogies must state source domain
    - Misapplied transfer is diagnostic, not error
    
    Returns CrossDomainInfo with all detected cross-domain signals.
    """
    # Get all domains mentioned
    all_domains = detect_all_domains(text)
    primary = all_domains[0] if all_domains else None
    
    # Get external domain references
    external = detect_external_domains(text)
    
    # Get cross-domain patterns
    phrases = detect_cross_domain_patterns(text)
    
    # Determine if this is a cross-domain capture
    has_cross = (
        len(all_domains) > 1 or  # Multiple internal domains
        len(external) > 0 or     # External domain references
        len(phrases) > 0         # Cross-domain language patterns
    )
    
    return CrossDomainInfo(
        primary_domain=primary,
        all_domains=all_domains,
        external_domains=external,
        cross_domain_phrases=phrases,
        has_cross_domain=has_cross
    )


def infer_domain_from_clusters(clusters: List[str]) -> Optional[str]:
    """
    Infer domain from vocabulary clusters.
    
    Used when vocabulary has already identified clusters in content.
    """
    for domain_name, spec in DOMAIN_REGISTRY.items():
        for cluster in clusters:
            if cluster in spec.vocab_clusters:
                return domain_name
    
    return None


def get_domain_for_scan_type(scan_type: str) -> Optional[str]:
    """Get the primary domain associated with a scan type."""
    for domain_name, spec in DOMAIN_REGISTRY.items():
        if spec.scan_type == scan_type:
            return domain_name
    return None


def get_scan_type_for_domain(domain: str) -> Optional[str]:
    """Get the scan type associated with a domain."""
    if domain in DOMAIN_REGISTRY:
        return DOMAIN_REGISTRY[domain].scan_type
    return None


def get_clusters_for_domain(domain: str) -> List[str]:
    """Get vocabulary clusters associated with a domain."""
    if domain in DOMAIN_REGISTRY:
        return DOMAIN_REGISTRY[domain].vocab_clusters
    return []


def list_domains() -> List[str]:
    """List all available domains."""
    return list(DOMAIN_REGISTRY.keys())


def get_domain_spec(domain: str) -> Optional[DomainSpec]:
    """Get full specification for a domain."""
    return DOMAIN_REGISTRY.get(domain)


# =============================================================================
# Domain Relevance Scoring (for Scanner)
# =============================================================================

def score_decision_relevance(
    decision: Dict,
    scan_type: str,
    domain_experts: Dict[str, List[str]] = None
) -> float:
    """
    Score how relevant a decision is for a scan type.
    
    Factors:
    - Domain match (decision domain matches scan domain)
    - Author expertise (author has declared expertise in domain)
    - Content relevance (keywords present)
    
    Returns score 0.0 to 1.0
    """
    score = 0.5  # Base score
    
    decision_domain = decision.get("domain")
    scan_domain = get_domain_for_scan_type(scan_type)
    
    # Domain match bonus
    if decision_domain and scan_domain:
        if decision_domain == scan_domain:
            score += 0.3  # Strong match
        elif decision_domain in get_related_domains(scan_domain):
            score += 0.1  # Related domain
    
    # Author expertise bonus
    if domain_experts and decision_domain:
        author = decision.get("author", "")
        if author in domain_experts.get(decision_domain, []):
            score += 0.2  # Author has expertise in this domain
    
    return min(score, 1.0)


def get_related_domains(domain: str) -> List[str]:
    """Get domains related to the given domain."""
    relationships = {
        "security": ["architecture", "devops"],
        "performance": ["architecture", "data", "devops"],
        "architecture": ["security", "performance", "data", "frontend"],
        "reliability": ["devops", "performance"],
        "dependencies": ["devops", "frontend"],
        "frontend": ["architecture", "dependencies"],
        "data": ["architecture", "performance"],
        "devops": ["reliability", "dependencies", "security"],
    }
    return relationships.get(domain, [])


# =============================================================================
# AI Role Declarations (P3: AI as pattern detector, synthesizer, challenger)
# =============================================================================

class AIRole:
    """AI role declarations for P3 compliance."""
    
    PATTERN_DETECTOR = "pattern_detector"
    SYNTHESIZER = "synthesizer"
    CHALLENGER = "challenger"
    
    @staticmethod
    def format_output(role: str, content: str) -> str:
        """Format AI output with role declaration."""
        prefixes = {
            AIRole.PATTERN_DETECTOR: "Pattern detected",
            AIRole.SYNTHESIZER: "Synthesis",
            AIRole.CHALLENGER: "Challenge",
        }
        prefix = prefixes.get(role, "AI")
        return f"[{prefix}] {content}"
    
    @staticmethod
    def is_arbiter_claim(text: str) -> bool:
        """
        Check if text makes authoritative claims (AI should not be arbiter).
        
        Returns True if text contains arbiter-like language.
        """
        arbiter_phrases = [
            "you must",
            "you should definitely",
            "the only way",
            "you have to",
            "this is the correct",
            "this is wrong",
        ]
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in arbiter_phrases)


# =============================================================================
# Helper Functions
# =============================================================================

def suggest_domain_for_capture(text: str, vocab_clusters: List[str] = None) -> Optional[str]:
    """
    Suggest a domain for a capture based on content and vocabulary.
    
    Priority:
    1. Vocabulary cluster inference (if clusters provided)
    2. Keyword inference from text
    """
    # Try vocabulary clusters first (more accurate)
    if vocab_clusters:
        domain = infer_domain_from_clusters(vocab_clusters)
        if domain:
            return domain
    
    # Fall back to keyword inference
    return infer_domain_from_text(text)


def validate_domain(domain: str) -> bool:
    """Check if a domain is valid."""
    return domain in DOMAIN_REGISTRY


def get_domain_description(domain: str) -> str:
    """Get human-readable description of a domain."""
    if domain in DOMAIN_REGISTRY:
        return DOMAIN_REGISTRY[domain].description
    return f"Unknown domain: {domain}"
