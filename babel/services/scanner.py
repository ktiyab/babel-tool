"""
Scanner -- Context-aware technical advisor

Uses Babel's unique knowledge (purpose, decisions, constraints)
to provide meaningful, project-specific advice.

What makes Babel scan different:
- Generic scanner: "SQL injection risk"
- Babel scan: "SQL injection risk conflicts with your 'sanitize all input' 
               constraint from March. Check entry points X, Y, Z."

Scan types:
- architecture: Design patterns, structure alignment
- security: Vulnerabilities in context
- performance: Bottlenecks given constraints
- dependencies: Upgrade priority based on purpose
- health: Quick overview (default)
"""

import json
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass, field
from pathlib import Path

from ..core.events import Event, EventType, DualEventStore
from ..core.graph import GraphStore, Node
from ..presentation.symbols import get_symbols

if TYPE_CHECKING:
    from .providers import LLMProvider
    from ..core.loader import LazyLoader
    from ..core.vocabulary import Vocabulary


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class ScanFinding:
    """A single finding from scan."""
    severity: str  # "info" | "warning" | "concern" | "critical"
    category: str  # "architecture" | "security" | "performance" | etc.
    title: str
    description: str
    suggestion: str
    references: List[str] = field(default_factory=list)  # Decision IDs referenced
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "suggestion": self.suggestion,
            "references": self.references
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScanFinding':
        return cls(
            severity=data.get("severity", "info"),
            category=data.get("category", "general"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            suggestion=data.get("suggestion", ""),
            references=data.get("references", [])
        )


@dataclass
class ScanContext:
    """Project context for scanning (P3 compliant)."""
    need: Optional[str]  # P1: What problem we're solving
    purpose: Optional[str]
    decisions: List[Dict[str, Any]]
    constraints: List[Dict[str, Any]]
    tech_stack: List[str]
    recent_topics: List[str]
    event_count: int
    domain_decisions: Dict[str, List[Dict]]  # P3: Decisions grouped by domain
    
    def to_prompt(self) -> str:
        """Format context for LLM prompt."""
        lines = []
        
        if self.need:
            lines.append(f"NEED (problem being solved): {self.need}")
            lines.append("")
        
        if self.purpose:
            lines.append(f"PURPOSE (what we're building): {self.purpose}")
            lines.append("")
        
        if self.decisions:
            lines.append("DECISIONS MADE:")
            for d in self.decisions[:15]:  # Limit for token efficiency
                summary = d.get("summary", str(d))
                domain = d.get("domain", "")
                domain_tag = f" [{domain}]" if domain else ""
                lines.append(f"  • {summary}{domain_tag}")
            lines.append("")
        
        if self.constraints:
            lines.append("CONSTRAINTS:")
            for c in self.constraints[:10]:
                summary = c.get("summary", str(c))
                lines.append(f"  • {summary}")
            lines.append("")
        
        if self.tech_stack:
            lines.append(f"TECHNOLOGY: {', '.join(self.tech_stack[:20])}")
            lines.append("")
        
        return "\n".join(lines)
    
    def get_decisions_for_domain(self, domain: str) -> List[Dict]:
        """Get decisions relevant to a domain (P3: expertise-weighted)."""
        return self.domain_decisions.get(domain, [])


@dataclass
class ScanResult:
    """Result of a scan."""
    scan_id: str
    timestamp: str
    scan_type: str
    status: str  # "healthy" | "concerns" | "issues"
    findings: List[ScanFinding]
    context_hash: str  # For cache invalidation
    summary: str
    
    @property
    def has_concerns(self) -> bool:
        return any(f.severity in ("warning", "concern", "critical") for f in self.findings)
    
    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "critical")
    
    @property
    def concern_count(self) -> int:
        return sum(1 for f in self.findings if f.severity in ("concern", "critical"))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scan_id": self.scan_id,
            "timestamp": self.timestamp,
            "scan_type": self.scan_type,
            "status": self.status,
            "findings": [f.to_dict() for f in self.findings],
            "context_hash": self.context_hash,
            "summary": self.summary
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScanResult':
        return cls(
            scan_id=data["scan_id"],
            timestamp=data["timestamp"],
            scan_type=data["scan_type"],
            status=data["status"],
            findings=[ScanFinding.from_dict(f) for f in data.get("findings", [])],
            context_hash=data.get("context_hash", ""),
            summary=data.get("summary", "")
        )


# =============================================================================
# Scanner
# =============================================================================

class Scanner:
    """
    Context-aware technical scanner.
    
    Uses Babel's knowledge for project-specific advice.
    """
    
    def __init__(
        self,
        events: DualEventStore,
        graph: GraphStore,
        provider: 'LLMProvider',
        loader: 'LazyLoader' = None,
        vocabulary: 'Vocabulary' = None,
        cache_path: Path = None
    ):
        self.events = events
        self.graph = graph
        self.provider = provider
        self.loader = loader
        self.vocabulary = vocabulary
        self.cache_path = cache_path
        
        self._context_cache: Optional[ScanContext] = None
    
    # =========================================================================
    # Public Interface
    # =========================================================================
    
    def scan(
        self,
        scan_type: str = "health",
        deep: bool = False,
        query: str = None
    ) -> ScanResult:
        """
        Run a scan.
        
        Args:
            scan_type: Type of scan (health, architecture, security, etc.)
            deep: Run comprehensive analysis
            query: Specific question to answer
            
        Returns:
            ScanResult with findings and suggestions
        """
        # Gather context
        context = self._gather_context()
        context_hash = self._hash_context(context)
        
        # Check cache (unless deep scan)
        if not deep and not query:
            cached = self._load_cache(scan_type, context_hash)
            if cached:
                return cached
        
        # Run appropriate scan
        if query:
            result = self._scan_query(context, query)
        elif scan_type == "health":
            result = self._scan_health(context, deep)
        elif scan_type == "architecture":
            result = self._scan_architecture(context, deep)
        elif scan_type == "security":
            result = self._scan_security(context, deep)
        elif scan_type == "performance":
            result = self._scan_performance(context, deep)
        elif scan_type == "dependencies":
            result = self._scan_dependencies(context, deep)
        else:
            result = self._scan_health(context, deep)
        
        # Cache result
        self._save_cache(result)
        
        return result
    
    def quick_check(self) -> str:
        """
        Quick one-line health status.
        
        For use in prompts or status display.
        """
        context = self._gather_context()
        
        if not context.purpose:
            return "No purpose defined -- run `babel init`"
        
        if not context.decisions:
            return "No decisions captured yet"
        
        # Quick heuristic checks (no LLM)
        issues = []
        
        # Check for constraints without matching decisions
        constraint_topics = set()
        for c in context.constraints:
            keywords = c.get("summary", "").lower().split()
            constraint_topics.update(keywords)
        
        decision_topics = set()
        for d in context.decisions:
            keywords = d.get("summary", "").lower().split()
            decision_topics.update(keywords)
        
        # Very basic coherence check
        if constraint_topics and not (constraint_topics & decision_topics):
            issues.append("constraints may lack supporting decisions")
        
        if len(context.decisions) > 20 and len(context.constraints) == 0:
            issues.append("many decisions but no constraints defined")
        
        if issues:
            return f"Review suggested: {'; '.join(issues)}"
        
        return f"Healthy: {len(context.decisions)} decisions aligned with purpose"
    
    # =========================================================================
    # Context Gathering
    # =========================================================================
    
    def _gather_context(self) -> ScanContext:
        """Gather project context from Babel stores (P3 compliant)."""
        if self._context_cache:
            return self._context_cache
        
        # Get need and purpose (P1: need grounds purpose)
        need = None
        purpose = None
        purpose_nodes = self.graph.get_nodes_by_type("purpose")
        if purpose_nodes:
            latest = purpose_nodes[-1].content
            purpose = latest.get("purpose", "")
            need = latest.get("need")  # P1: Bootstrap from Need
        
        # Get decisions
        decisions = []
        decision_nodes = self.graph.get_nodes_by_type("decision")
        for node in decision_nodes:
            decisions.append(node.content)
        
        # Get constraints
        constraints = []
        constraint_nodes = self.graph.get_nodes_by_type("constraint")
        for node in constraint_nodes:
            constraints.append(node.content)
        
        # Infer tech stack from vocabulary and decisions
        tech_stack = self._infer_tech_stack(decisions)
        
        # Get recent topics
        recent_topics = []
        if self.vocabulary:
            recent_topics = self.vocabulary.list_clusters()
        
        # Event count
        event_count = self.events.count()
        
        # P3: Group decisions by domain for expertise-weighted analysis
        domain_decisions = self._group_by_domain(decisions)
        
        context = ScanContext(
            need=need,
            purpose=purpose,
            decisions=decisions,
            constraints=constraints,
            tech_stack=tech_stack,
            recent_topics=recent_topics,
            event_count=event_count,
            domain_decisions=domain_decisions
        )
        
        self._context_cache = context
        return context
    
    def _group_by_domain(self, decisions: List[Dict]) -> Dict[str, List[Dict]]:
        """Group decisions by domain (P3: expertise-weighted analysis)."""
        from ..core.domains import infer_domain_from_text
        
        grouped: Dict[str, List[Dict]] = {}
        
        for d in decisions:
            # Use explicit domain if present
            domain = d.get("domain")
            
            # Otherwise infer from content
            if not domain:
                summary = d.get("summary", str(d))
                domain = infer_domain_from_text(summary)
            
            if domain:
                if domain not in grouped:
                    grouped[domain] = []
                grouped[domain].append(d)
        
        return grouped
    
    def _infer_tech_stack(self, decisions: List[Dict]) -> List[str]:
        """Infer technology stack from decisions."""
        tech_keywords = {
            "python", "javascript", "typescript", "rust", "go", "java",
            "react", "vue", "angular", "svelte",
            "postgresql", "mysql", "sqlite", "mongodb", "redis",
            "docker", "kubernetes", "aws", "gcp", "azure",
            "rest", "graphql", "grpc"
        }
        
        found = set()
        for d in decisions:
            text = str(d).lower()
            for tech in tech_keywords:
                if tech in text:
                    found.add(tech)
        
        return list(found)
    
    def _hash_context(self, context: ScanContext) -> str:
        """Hash context for cache invalidation."""
        content = json.dumps({
            "purpose": context.purpose,
            "decisions": len(context.decisions),
            "constraints": len(context.constraints),
            "events": context.event_count
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    # =========================================================================
    # Scan Implementations
    # =========================================================================
    
    def _scan_health(self, context: ScanContext, deep: bool) -> ScanResult:
        """Quick health scan."""
        if not self.provider.is_available:
            return self._mock_scan(context, "health")
        
        prompt = self._build_prompt(context, "health", deep)
        response = self.provider.complete(SCAN_SYSTEM_PROMPT, prompt, max_tokens=1500)

        return self._parse_response(response.text, context, "health")
    
    def _scan_architecture(self, context: ScanContext, deep: bool) -> ScanResult:
        """Architecture-focused scan."""
        if not self.provider.is_available:
            return self._mock_scan(context, "architecture")
        
        prompt = self._build_prompt(context, "architecture", deep)
        response = self.provider.complete(ARCHITECTURE_SYSTEM_PROMPT, prompt, max_tokens=2000)

        return self._parse_response(response.text, context, "architecture")
    
    def _scan_security(self, context: ScanContext, deep: bool) -> ScanResult:
        """Security-focused scan."""
        if not self.provider.is_available:
            return self._mock_scan(context, "security")
        
        prompt = self._build_prompt(context, "security", deep)
        response = self.provider.complete(SECURITY_SYSTEM_PROMPT, prompt, max_tokens=2000)

        return self._parse_response(response.text, context, "security")
    
    def _scan_performance(self, context: ScanContext, deep: bool) -> ScanResult:
        """Performance-focused scan."""
        if not self.provider.is_available:
            return self._mock_scan(context, "performance")
        
        prompt = self._build_prompt(context, "performance", deep)
        response = self.provider.complete(PERFORMANCE_SYSTEM_PROMPT, prompt, max_tokens=2000)

        return self._parse_response(response.text, context, "performance")
    
    def _scan_dependencies(self, context: ScanContext, deep: bool) -> ScanResult:
        """Dependencies-focused scan."""
        if not self.provider.is_available:
            return self._mock_scan(context, "dependencies")
        
        prompt = self._build_prompt(context, "dependencies", deep)
        response = self.provider.complete(DEPENDENCIES_SYSTEM_PROMPT, prompt, max_tokens=1500)

        return self._parse_response(response.text, context, "dependencies")
    
    def _scan_query(self, context: ScanContext, query: str) -> ScanResult:
        """Answer specific question."""
        if not self.provider.is_available:
            return self._mock_scan(context, "query", query)
        
        prompt = f"""{context.to_prompt()}

QUESTION: {query}

Analyze this question in the context of the project above.
Provide a direct answer that references specific decisions and constraints.
"""
        
        response = self.provider.complete(QUERY_SYSTEM_PROMPT, prompt, max_tokens=1500)

        return self._parse_response(response.text, context, "query")
    
    def _build_prompt(self, context: ScanContext, scan_type: str, deep: bool) -> str:
        """Build scan prompt."""
        depth = "comprehensive" if deep else "quick"
        
        return f"""{context.to_prompt()}

Perform a {depth} {scan_type} review.

{"Analyze all aspects thoroughly." if deep else "Focus on top 3 most important findings."}

Return JSON:
{{
    "status": "healthy" | "concerns" | "issues",
    "summary": "one-line summary",
    "findings": [
        {{
            "severity": "info" | "warning" | "concern" | "critical",
            "category": "{scan_type}",
            "title": "short title",
            "description": "what and why, referencing decisions",
            "suggestion": "actionable recommendation"
        }}
    ]
}}
"""
    
    def _parse_response(self, response: str, context: ScanContext, scan_type: str) -> ScanResult:
        """Parse LLM response into ScanResult."""
        try:
            # Extract JSON from response
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            
            data = json.loads(json_str.strip())
            
            findings = [
                ScanFinding.from_dict(f)
                for f in data.get("findings", [])
            ]
            
            return ScanResult(
                scan_id=f"scan_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                scan_type=scan_type,
                status=data.get("status", "healthy"),
                findings=findings,
                context_hash=self._hash_context(context),
                summary=data.get("summary", "Scan complete")
            )
        except (json.JSONDecodeError, KeyError, IndexError):
            # Fallback for non-JSON response
            return ScanResult(
                scan_id=f"scan_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                scan_type=scan_type,
                status="healthy",
                findings=[
                    ScanFinding(
                        severity="info",
                        category=scan_type,
                        title="Analysis Complete",
                        description=response[:500],
                        suggestion="Review the analysis above."
                    )
                ],
                context_hash=self._hash_context(context),
                summary="Scan complete"
            )
    
    def _mock_scan(self, context: ScanContext, scan_type: str, query: str = None) -> ScanResult:
        """Mock scan when LLM unavailable."""
        findings = []
        
        # Basic heuristic findings
        if not context.purpose:
            findings.append(ScanFinding(
                severity="warning",
                category="setup",
                title="No Purpose Defined",
                description="Project has no declared purpose. This makes it hard to evaluate decisions.",
                suggestion="Run `babel init \"your purpose\"` to set project purpose."
            ))
        
        if context.decisions and not context.constraints:
            findings.append(ScanFinding(
                severity="info",
                category="architecture",
                title="No Constraints Defined",
                description=f"Project has {len(context.decisions)} decisions but no constraints.",
                suggestion="Consider defining constraints to guide future decisions."
            ))
        
        if len(context.decisions) > 30:
            findings.append(ScanFinding(
                severity="info",
                category="maintenance",
                title="Many Decisions",
                description=f"Project has {len(context.decisions)} decisions. Consider reviewing for coherence.",
                suggestion="Run `babel coherence` to check alignment."
            ))
        
        status = "healthy" if not findings else "concerns"
        summary = f"Basic scan: {len(findings)} finding(s) (LLM unavailable for deep analysis)"
        
        return ScanResult(
            scan_id=f"scan_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            scan_type=scan_type,
            status=status,
            findings=findings,
            context_hash=self._hash_context(context),
            summary=summary
        )
    
    # =========================================================================
    # Caching
    # =========================================================================
    
    def _load_cache(self, scan_type: str, context_hash: str) -> Optional[ScanResult]:
        """Load cached scan result if valid."""
        if not self.cache_path or not self.cache_path.exists():
            return None
        
        try:
            data = json.loads(self.cache_path.read_text())
            cached = data.get(scan_type)
            
            if cached and cached.get("context_hash") == context_hash:
                result = ScanResult.from_dict(cached)
                return result
        except (json.JSONDecodeError, KeyError):
            pass
        
        return None
    
    def _save_cache(self, result: ScanResult):
        """Save scan result to cache."""
        if not self.cache_path:
            return
        
        try:
            if self.cache_path.exists():
                data = json.loads(self.cache_path.read_text())
            else:
                data = {}
            
            data[result.scan_type] = result.to_dict()
            
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(data, indent=2))
        except (json.JSONDecodeError, IOError):
            pass


# =============================================================================
# System Prompts
# =============================================================================

SCAN_SYSTEM_PROMPT = """You are a senior technical advisor reviewing a software project.

You have access to the project's PURPOSE, DECISIONS, and CONSTRAINTS from Babel.

Your role:
1. Validate alignment between implementation and stated intent
2. Identify conflicts between decisions and constraints
3. Surface risks specific to THIS project's context
4. Suggest improvements that RESPECT existing decisions

Rules:
- Reference specific decisions when making observations
- Acknowledge when choices are appropriate for the context
- Prioritize findings by impact on stated purpose
- Every concern needs an actionable suggestion
- Be constructive, not alarmist

Return valid JSON with status, summary, and findings array."""

ARCHITECTURE_SYSTEM_PROMPT = """You are a senior software architect reviewing a project's design.

Given the project's PURPOSE, DECISIONS, and CONSTRAINTS from Babel:

Focus on:
1. Design pattern appropriateness for stated purpose
2. Structural alignment with constraints
3. Scalability given tech choices
4. Separation of concerns
5. Dependency direction

Reference specific decisions. Suggest patterns that fit the existing architecture.

Return valid JSON with status, summary, and findings array."""

SECURITY_SYSTEM_PROMPT = """You are a security engineer reviewing a project.

Given the project's PURPOSE, DECISIONS, and CONSTRAINTS from Babel:

Focus on:
1. Data handling relative to stated constraints
2. Authentication/authorization patterns
3. Input validation coverage
4. Dependency security implications
5. Secrets management

Reference specific decisions. Consider the project's actual threat model based on its purpose.

Return valid JSON with status, summary, and findings array."""

PERFORMANCE_SYSTEM_PROMPT = """You are a performance engineer reviewing a project.

Given the project's PURPOSE, DECISIONS, and CONSTRAINTS from Babel:

Focus on:
1. Bottleneck risks given tech choices
2. Scalability alignment with purpose
3. Resource efficiency
4. Caching opportunities
5. Query patterns

Reference specific decisions. Consider actual load expectations based on purpose.

Return valid JSON with status, summary, and findings array."""

DEPENDENCIES_SYSTEM_PROMPT = """You are reviewing a project's dependencies.

Given the project's PURPOSE, DECISIONS, and CONSTRAINTS from Babel:

Focus on:
1. Dependency necessity relative to purpose
2. Maintenance burden vs. value
3. Security update priority
4. Bundle size impact (if relevant)
5. Upgrade paths

Reference why each dependency was likely chosen. Suggest removals only if purpose allows.

Return valid JSON with status, summary, and findings array."""

QUERY_SYSTEM_PROMPT = """You are answering a specific technical question about a project.

You have context from Babel: the project's PURPOSE, DECISIONS, and CONSTRAINTS.

Answer the question directly, referencing specific decisions.
Explain how the answer relates to the project's stated purpose.
If the question reveals a gap or concern, suggest how to address it.

Return valid JSON with status, summary, and a single finding that answers the question."""


# =============================================================================
# Formatting
# =============================================================================

def format_scan_result(result: ScanResult, verbose: bool = False) -> str:
    """Format scan result for display."""
    symbols = get_symbols()
    lines = []

    # Status header
    status_icon = {
        "healthy": symbols.check_pass,
        "concerns": symbols.check_warn,
        "issues": symbols.check_fail
    }.get(result.status, "?")
    
    lines.append(f"{status_icon} {result.summary}")
    lines.append("")
    
    if not result.findings:
        lines.append("No findings.")
        return "\n".join(lines)
    
    # Group by severity
    critical = [f for f in result.findings if f.severity == "critical"]
    concerns = [f for f in result.findings if f.severity in ("concern", "warning")]
    info = [f for f in result.findings if f.severity == "info"]
    
    def format_finding(f: ScanFinding, index: int) -> List[str]:
        finding_lines = []
        severity_icon = {
            "critical": symbols.check_fail,
            "concern": symbols.check_warn,
            "warning": symbols.check_warn,
            "info": "[i]"
        }.get(f.severity, symbols.bullet)

        finding_lines.append(f"{index}. {severity_icon} {f.title}")
        finding_lines.append(f"   {f.description}")
        finding_lines.append(f"   {symbols.arrow} {f.suggestion}")
        finding_lines.append("")
        return finding_lines
    
    index = 1
    
    if critical:
        lines.append("CRITICAL:")
        for f in critical:
            lines.extend(format_finding(f, index))
            index += 1
    
    if concerns:
        if critical:
            lines.append("CONCERNS:")
        for f in concerns:
            lines.extend(format_finding(f, index))
            index += 1
    
    if info and verbose:
        lines.append("INFO:")
        for f in info:
            lines.extend(format_finding(f, index))
            index += 1
    elif info and not verbose:
        lines.append(f"({len(info)} additional info items -- use --verbose to see)")
    
    return "\n".join(lines)
