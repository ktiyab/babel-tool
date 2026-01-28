"""
Vocabulary — Emergent semantic clusters for query expansion (P2 compliant)

P2: Emergent Ontology
- No fixed vocabulary assumed upfront (COMMON_PATTERNS are suggestions only)
- Terms can be introduced, challenged, refined, or discarded
- Definitions are artifacts, not truths
- Project-level definitions take precedence over common patterns

Layered vocabulary (highest to lowest priority):
1. Project overrides — Team's explicit definitions and challenges
2. Learned terms — Discovered through use
3. Common patterns — Suggestions, can be overridden

Grows with use, reduces LLM calls over time.
"""

import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Set
from datetime import datetime, timezone


# Common patterns (P2: suggestions only, not fixed vocabulary)
# These can be overridden by project-level definitions
COMMON_PATTERNS = {
    "database": ["database", "db", "postgresql", "postgres", "pg", "mysql", 
                 "sqlite", "sql", "nosql", "dynamodb", "mongodb", "supabase"],
    "caching": ["cache", "caching", "redis", "memcached", "memoization"],
    "api": ["api", "rest", "graphql", "grpc", "endpoint", "http"],
    "auth": ["auth", "authentication", "authorization", "oauth", "jwt", "login", "session"],
    "frontend": ["frontend", "ui", "react", "vue", "angular", "component", "css"],
    "backend": ["backend", "server", "node", "python", "java", "go", "rust"],
    "cloud": ["cloud", "aws", "gcp", "azure", "serverless", "lambda", "kubernetes", "k8s", "docker"],
    "offline": ["offline", "offline-first", "local-first", "sync", "pwa", "service-worker"],
    "testing": ["test", "testing", "unit", "integration", "e2e", "coverage"],
    "performance": ["performance", "latency", "throughput", "optimization", "scale", "scaling"],
    "security": ["security", "encryption", "ssl", "tls", "https", "vulnerability"],
}

# For backward compatibility
DEFAULT_CLUSTERS = COMMON_PATTERNS


class Vocabulary:
    """
    Emergent semantic vocabulary for query expansion (P2 compliant).
    
    P2: Definitions are artifacts, not truths.
    - Project overrides take precedence over common patterns
    - Terms can be challenged, refined, or discarded
    - Changes are tracked for traceability
    """
    
    def __init__(self, babel_dir: Path):
        self.babel_dir = Path(babel_dir)
        self.vocab_path = self.babel_dir / "shared" / "vocabulary.json"
        self._data: Optional[Dict] = None
        self._dirty = False
    
    # =========================================================================
    # Core Operations
    # =========================================================================
    
    def expand(self, term: str) -> List[str]:
        """
        Expand a term to include related terms from same cluster.
        
        P2: Project overrides take precedence over common patterns.
        
        "postgres" → ["postgres", "postgresql", "pg", "database", "db", ...]
        """
        data = self._load()
        term_lower = term.lower().strip()
        
        # Check if term is discarded (P2: terms can be discarded)
        if term_lower in data.get("discarded", []):
            return [term_lower]  # No expansion for discarded terms
        
        # Check project overrides first (P2: project definitions take precedence)
        overrides = data.get("overrides", {})
        if term_lower in overrides:
            override_cluster = overrides[term_lower]
            if override_cluster and override_cluster in data["clusters"]:
                expanded = set(data["clusters"][override_cluster])
                expanded.add(term_lower)
                return list(expanded)
            elif override_cluster is None:
                # Explicitly undefined — no expansion
                return [term_lower]
        
        # Find which cluster contains this term
        for cluster_name, terms in data["clusters"].items():
            if term_lower in [t.lower() for t in terms]:
                # Return all terms in cluster (deduplicated)
                expanded = set(terms)
                expanded.add(term_lower)
                return list(expanded)
        
        # Check mappings (shortcuts/aliases)
        if term_lower in data.get("mappings", {}):
            canonical = data["mappings"][term_lower]
            return self.expand(canonical)  # Expand the canonical term
        
        # Unknown term — return as-is
        return [term_lower]
    
    def expand_many(self, terms: List[str]) -> List[str]:
        """Expand multiple terms, deduplicated."""
        expanded: Set[str] = set()
        for term in terms:
            expanded.update(self.expand(term))
        return list(expanded)
    
    def find_cluster(self, term: str) -> Optional[str]:
        """Find which cluster a term belongs to."""
        data = self._load()
        term_lower = term.lower().strip()
        
        for cluster_name, terms in data["clusters"].items():
            if term_lower in [t.lower() for t in terms]:
                return cluster_name
        
        # Check mappings
        if term_lower in data.get("mappings", {}):
            canonical = data["mappings"][term_lower]
            return self.find_cluster(canonical)
        
        return None
    
    def get_cluster(self, cluster_name: str) -> List[str]:
        """Get all terms in a cluster."""
        data = self._load()
        return data["clusters"].get(cluster_name, [])
    
    def list_clusters(self) -> List[str]:
        """List all cluster names."""
        data = self._load()
        return list(data["clusters"].keys())
    
    # =========================================================================
    # Learning (called during extraction)
    # =========================================================================
    
    def learn_term(self, term: str, cluster: str):
        """
        Add a term to a cluster.
        
        Called when LLM extraction discovers new terms.
        """
        data = self._load()
        term_lower = term.lower().strip()
        cluster_lower = cluster.lower().strip()
        
        # Create cluster if needed
        if cluster_lower not in data["clusters"]:
            data["clusters"][cluster_lower] = []
        
        # Add term if not already present
        cluster_terms = [t.lower() for t in data["clusters"][cluster_lower]]
        if term_lower not in cluster_terms:
            data["clusters"][cluster_lower].append(term_lower)
            self._dirty = True
    
    def learn_mapping(self, alias: str, canonical: str):
        """
        Add a shortcut/alias mapping.
        
        "ddb" → "dynamodb"
        "k8s" → "kubernetes"
        """
        data = self._load()
        alias_lower = alias.lower().strip()
        canonical_lower = canonical.lower().strip()
        
        if "mappings" not in data:
            data["mappings"] = {}
        
        if alias_lower not in data["mappings"]:
            data["mappings"][alias_lower] = canonical_lower
            self._dirty = True
    
    def learn_from_extraction(self, terms: List[str], context_hint: Optional[str] = None):
        """
        Learn from LLM extraction results.
        
        Groups related terms, infers clusters.
        Called automatically during topic extraction.
        """
        data = self._load()
        
        for term in terms:
            term_lower = term.lower().strip()
            
            # Skip if already known
            if self.find_cluster(term_lower):
                continue
            
            # Try to infer cluster from context hint
            if context_hint:
                hint_cluster = self.find_cluster(context_hint)
                if hint_cluster:
                    self.learn_term(term_lower, hint_cluster)
                    continue
            
            # Try to match by common patterns
            inferred = self._infer_cluster(term_lower)
            if inferred:
                self.learn_term(term_lower, inferred)
    
    def _infer_cluster(self, term: str) -> Optional[str]:
        """Infer cluster from term patterns."""
        term_lower = term.lower()
        
        # Common suffixes/patterns
        patterns = {
            "db": "database",
            "sql": "database",
            "cache": "caching",
            "api": "api",
            "auth": "auth",
            "js": "frontend",
            "ui": "frontend",
            "test": "testing",
            "spec": "testing",
        }
        
        for pattern, cluster in patterns.items():
            if pattern in term_lower:
                return cluster
        
        return None
    
    # =========================================================================
    # P2: Emergent Ontology — Challenge, Refine, Discard, Define
    # =========================================================================
    
    def define(self, term: str, cluster: Optional[str], reason: str = None) -> Dict:
        """
        Define or redefine what a term means in this project (P2 compliance).
        
        Project-level definitions override common patterns.
        
        Args:
            term: The term to define
            cluster: Which cluster it belongs to (None to mark as standalone)
            reason: Why this definition (for traceability)
            
        Returns:
            Event data for recording
        """
        data = self._load()
        term_lower = term.lower().strip()
        
        if "overrides" not in data:
            data["overrides"] = {}
        
        old_cluster = self.find_cluster(term_lower)
        data["overrides"][term_lower] = cluster
        self._dirty = True
        
        # Track change for audit (P2: definitions as artifacts)
        change = {
            "action": "define",
            "term": term_lower,
            "from_cluster": old_cluster,
            "to_cluster": cluster,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        self._record_change(change)
        return change
    
    def challenge(self, term: str, reason: str) -> Dict:
        """
        Challenge a term's current cluster assignment (P2 compliance).
        
        Records the challenge for team discussion. Doesn't change assignment
        until refined or resolved.
        
        Args:
            term: The term being challenged
            reason: Why the current assignment is questioned
            
        Returns:
            Event data for recording
        """
        data = self._load()
        term_lower = term.lower().strip()
        
        if "challenges" not in data:
            data["challenges"] = []
        
        current_cluster = self.find_cluster(term_lower)
        
        challenge = {
            "action": "challenge",
            "term": term_lower,
            "current_cluster": current_cluster,
            "reason": reason,
            "status": "open",  # open | resolved | rejected
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        data["challenges"].append(challenge)
        self._dirty = True
        
        self._record_change(challenge)
        return challenge
    
    def refine(self, term: str, new_cluster: str, reason: str = None) -> Dict:
        """
        Move a term to a different cluster (P2 compliance).
        
        This creates a project-level override.
        
        Args:
            term: The term to refine
            new_cluster: The new cluster assignment
            reason: Why this refinement
            
        Returns:
            Event data for recording
        """
        data = self._load()
        term_lower = term.lower().strip()
        new_cluster_lower = new_cluster.lower().strip()
        
        old_cluster = self.find_cluster(term_lower)
        
        # Create override
        if "overrides" not in data:
            data["overrides"] = {}
        
        data["overrides"][term_lower] = new_cluster_lower
        
        # Ensure new cluster exists
        if new_cluster_lower not in data["clusters"]:
            data["clusters"][new_cluster_lower] = []
        
        # Add term to new cluster
        if term_lower not in data["clusters"][new_cluster_lower]:
            data["clusters"][new_cluster_lower].append(term_lower)
        
        self._dirty = True
        
        change = {
            "action": "refine",
            "term": term_lower,
            "from_cluster": old_cluster,
            "to_cluster": new_cluster_lower,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        self._record_change(change)
        return change
    
    def discard(self, term: str, reason: str = None) -> Dict:
        """
        Remove a term from vocabulary expansion (P2 compliance).
        
        Discarded terms won't be expanded, treating them as standalone.
        
        Args:
            term: The term to discard
            reason: Why discarding
            
        Returns:
            Event data for recording
        """
        data = self._load()
        term_lower = term.lower().strip()
        
        if "discarded" not in data:
            data["discarded"] = []
        
        old_cluster = self.find_cluster(term_lower)
        
        if term_lower not in data["discarded"]:
            data["discarded"].append(term_lower)
            self._dirty = True
        
        change = {
            "action": "discard",
            "term": term_lower,
            "from_cluster": old_cluster,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        self._record_change(change)
        return change
    
    def resolve_challenge(self, term: str, resolution: str, action: str = None) -> Dict:
        """
        Resolve an open challenge (P2 compliance).
        
        Args:
            term: The challenged term
            resolution: "accepted" (will refine) | "rejected" (keep current)
            action: If accepted, which action was taken
            
        Returns:
            Resolution data
        """
        data = self._load()
        term_lower = term.lower().strip()
        
        # Find and update the challenge
        for challenge in data.get("challenges", []):
            if challenge["term"] == term_lower and challenge["status"] == "open":
                challenge["status"] = "resolved"
                challenge["resolution"] = resolution
                challenge["resolved_at"] = datetime.now(timezone.utc).isoformat()
                if action:
                    challenge["action_taken"] = action
                self._dirty = True
                return challenge
        
        return {"error": f"No open challenge found for '{term}'"}
    
    def get_challenges(self, status: str = None) -> List[Dict]:
        """Get challenges, optionally filtered by status."""
        data = self._load()
        challenges = data.get("challenges", [])
        
        if status:
            return [c for c in challenges if c.get("status") == status]
        return challenges
    
    def get_changes(self, limit: int = 20) -> List[Dict]:
        """Get recent vocabulary changes (P2: definitions as artifacts)."""
        data = self._load()
        changes = data.get("changes", [])
        return changes[-limit:] if limit else changes
    
    def _record_change(self, change: Dict):
        """Record a vocabulary change for audit trail."""
        data = self._load()
        
        if "changes" not in data:
            data["changes"] = []
        
        data["changes"].append(change)
        
        # Keep last 100 changes (prevent unbounded growth)
        if len(data["changes"]) > 100:
            data["changes"] = data["changes"][-100:]
    
    # =========================================================================
    # Persistence
    # =========================================================================
    
    def _load(self) -> Dict:
        """Load vocabulary from disk or create default."""
        if self._data is not None:
            return self._data
        
        if self.vocab_path.exists():
            try:
                self._data = json.loads(self.vocab_path.read_text())
            except (json.JSONDecodeError, IOError):
                self._data = self._default_data()
        else:
            self._data = self._default_data()
        
        return self._data
    
    def _default_data(self) -> Dict:
        """Create default vocabulary structure (P2 compliant)."""
        return {
            "clusters": COMMON_PATTERNS.copy(),  # P2: Common patterns, not fixed vocabulary
            "mappings": {
                "pg": "postgresql",
                "ddb": "dynamodb",
                "k8s": "kubernetes",
                "js": "javascript",
                "ts": "typescript",
                "py": "python",
            },
            "overrides": {},     # P2: Project-level definitions (take precedence)
            "challenges": [],    # P2: Open challenges for team discussion
            "discarded": [],     # P2: Terms removed from expansion
            "changes": [],       # P2: Audit trail (definitions as artifacts)
            "updated": datetime.now(timezone.utc).isoformat()
        }
    
    def save(self):
        """Persist vocabulary to disk if changed."""
        if not self._dirty or self._data is None:
            return
        
        # Ensure directory exists
        self.vocab_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Update timestamp
        self._data["updated"] = datetime.now(timezone.utc).isoformat()
        
        # Write atomically
        temp_path = self.vocab_path.with_suffix('.tmp')
        temp_path.write_text(json.dumps(self._data, indent=2))
        os.replace(temp_path, self.vocab_path)
        
        self._dirty = False
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.save()
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    def stats(self) -> Dict:
        """Get vocabulary statistics (P2: includes ontology health)."""
        data = self._load()
        
        total_terms = sum(len(terms) for terms in data["clusters"].values())
        open_challenges = len([c for c in data.get("challenges", []) if c.get("status") == "open"])
        
        return {
            "clusters": len(data["clusters"]),
            "total_terms": total_terms,
            "mappings": len(data.get("mappings", {})),
            "overrides": len(data.get("overrides", {})),      # P2: Project definitions
            "open_challenges": open_challenges,                # P2: Disputed terms
            "discarded": len(data.get("discarded", [])),      # P2: Removed terms
            "changes": len(data.get("changes", [])),          # P2: Audit trail
            "updated": data.get("updated", "never")
        }


# =============================================================================
# Helper Functions
# =============================================================================

def expand_query(term: str, vocab: Vocabulary) -> List[str]:
    """Convenience function for query expansion."""
    return vocab.expand(term)


def merge_vocabularies(local: Dict, remote: Dict) -> Dict:
    """
    Merge two vocabularies (for git sync, P2 compliant).
    
    Strategy:
    - Clusters: Union of terms
    - Mappings: Remote wins conflicts
    - Overrides: Remote wins conflicts (P2: latest project definitions)
    - Challenges: Concatenate all
    - Discarded: Union
    - Changes: Concatenate and dedupe by timestamp
    """
    merged = {
        "clusters": {},
        "mappings": {},
        "overrides": {},
        "challenges": [],
        "discarded": [],
        "changes": [],
        "updated": datetime.now(timezone.utc).isoformat()
    }
    
    # Merge clusters (union)
    all_clusters = set(local.get("clusters", {}).keys()) | set(remote.get("clusters", {}).keys())
    
    for cluster in all_clusters:
        local_terms = set(local.get("clusters", {}).get(cluster, []))
        remote_terms = set(remote.get("clusters", {}).get(cluster, []))
        merged["clusters"][cluster] = list(local_terms | remote_terms)
    
    # Merge mappings (remote wins)
    merged["mappings"] = {
        **local.get("mappings", {}),
        **remote.get("mappings", {})
    }
    
    # Merge overrides (remote wins — P2: latest project definitions take precedence)
    merged["overrides"] = {
        **local.get("overrides", {}),
        **remote.get("overrides", {})
    }
    
    # Merge challenges (concatenate, dedupe by term+timestamp)
    local_challenges = local.get("challenges", [])
    remote_challenges = remote.get("challenges", [])
    seen = set()
    for c in local_challenges + remote_challenges:
        key = (c.get("term"), c.get("timestamp"))
        if key not in seen:
            merged["challenges"].append(c)
            seen.add(key)
    
    # Merge discarded (union)
    merged["discarded"] = list(set(local.get("discarded", [])) | set(remote.get("discarded", [])))
    
    # Merge changes (concatenate, sort by timestamp, keep last 100)
    all_changes = local.get("changes", []) + remote.get("changes", [])
    # Dedupe by timestamp
    seen_timestamps = set()
    unique_changes = []
    for c in all_changes:
        ts = c.get("timestamp")
        if ts not in seen_timestamps:
            unique_changes.append(c)
            seen_timestamps.add(ts)
    # Sort and limit
    unique_changes.sort(key=lambda x: x.get("timestamp", ""))
    merged["changes"] = unique_changes[-100:]
    
    return merged
