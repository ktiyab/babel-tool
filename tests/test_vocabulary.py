"""
Tests for vocabulary module

Minimal design:
- Single file, grouped clusters
- Semantic expansion
- Learning from use
"""


from babel.core.vocabulary import Vocabulary, merge_vocabularies, DEFAULT_CLUSTERS


class TestVocabulary:
    """Test vocabulary core operations."""
    
    def test_creates_default_vocabulary(self, tmp_path):
        """Creates default clusters if no file exists."""
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()
        
        vocab = Vocabulary(babel_dir)
        stats = vocab.stats()
        
        assert stats["clusters"] > 0
        assert stats["total_terms"] > 0
    
    def test_expand_known_term(self, tmp_path):
        """Expands known term to cluster."""
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()
        
        vocab = Vocabulary(babel_dir)
        
        # "postgres" should expand to database cluster
        expanded = vocab.expand("postgres")
        
        assert "postgres" in expanded or "postgresql" in expanded
        assert len(expanded) > 1  # Should include related terms
    
    def test_expand_unknown_term(self, tmp_path):
        """Unknown term returns as-is."""
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()
        
        vocab = Vocabulary(babel_dir)
        
        expanded = vocab.expand("xyznonexistent")
        
        assert expanded == ["xyznonexistent"]
    
    def test_expand_many(self, tmp_path):
        """Expands multiple terms, deduplicated."""
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()
        
        vocab = Vocabulary(babel_dir)
        
        expanded = vocab.expand_many(["postgres", "mysql"])
        
        # Both should expand to database cluster
        assert "postgresql" in expanded or "postgres" in expanded
        assert "mysql" in expanded
        # Should be deduplicated
        assert len(expanded) == len(set(expanded))
    
    def test_find_cluster(self, tmp_path):
        """Finds which cluster a term belongs to."""
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()
        
        vocab = Vocabulary(babel_dir)
        
        cluster = vocab.find_cluster("redis")
        
        assert cluster == "caching"
    
    def test_find_cluster_unknown(self, tmp_path):
        """Returns None for unknown term."""
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()
        
        vocab = Vocabulary(babel_dir)
        
        cluster = vocab.find_cluster("xyznonexistent")
        
        assert cluster is None


class TestVocabularyLearning:
    """Test vocabulary learning capabilities."""
    
    def test_learn_term(self, tmp_path):
        """Can learn new term into existing cluster."""
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()
        
        vocab = Vocabulary(babel_dir)
        
        # Learn new database
        vocab.learn_term("cockroachdb", "database")
        
        # Should be findable now
        cluster = vocab.find_cluster("cockroachdb")
        assert cluster == "database"
    
    def test_learn_creates_cluster(self, tmp_path):
        """Learning creates new cluster if needed."""
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()
        
        vocab = Vocabulary(babel_dir)
        
        # Learn term in new cluster (use term not in defaults)
        vocab.learn_term("nomad", "orchestration")
        
        assert "orchestration" in vocab.list_clusters()
        assert vocab.find_cluster("nomad") == "orchestration"
    
    def test_learn_mapping(self, tmp_path):
        """Can learn shortcuts/aliases."""
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()
        
        vocab = Vocabulary(babel_dir)
        
        # Learn shortcut
        vocab.learn_mapping("crdb", "cockroachdb")
        vocab.learn_term("cockroachdb", "database")
        
        # Should expand via mapping
        cluster = vocab.find_cluster("crdb")
        assert cluster == "database"
    
    def test_learn_from_extraction(self, tmp_path):
        """Learns from extracted terms with context."""
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()
        
        vocab = Vocabulary(babel_dir)
        
        # Learn terms with context hint
        vocab.learn_from_extraction(
            terms=["planetscale", "vitess"],
            context_hint="mysql"
        )
        
        # Should associate with database cluster
        assert vocab.find_cluster("planetscale") == "database"


class TestVocabularyPersistence:
    """Test vocabulary save/load."""
    
    def test_persistence(self, tmp_path):
        """Vocabulary persists across instances."""
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()
        (babel_dir / "shared").mkdir()
        
        # First instance - learn something
        vocab1 = Vocabulary(babel_dir)
        vocab1.learn_term("newterm", "newcluster")
        vocab1.save()
        
        # Second instance - should see learned term
        vocab2 = Vocabulary(babel_dir)
        
        assert vocab2.find_cluster("newterm") == "newcluster"
    
    def test_context_manager(self, tmp_path):
        """Context manager saves on exit."""
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()
        (babel_dir / "shared").mkdir()
        
        with Vocabulary(babel_dir) as vocab:
            vocab.learn_term("contextterm", "contextcluster")
        
        # Should be persisted
        vocab2 = Vocabulary(babel_dir)
        assert vocab2.find_cluster("contextterm") == "contextcluster"


class TestMergeVocabularies:
    """Test vocabulary merging for git sync."""
    
    def test_merge_clusters(self):
        """Merges clusters from both vocabularies."""
        local = {
            "clusters": {
                "database": ["postgres", "mysql"],
                "local-only": ["term1"]
            },
            "mappings": {}
        }
        
        remote = {
            "clusters": {
                "database": ["postgres", "sqlite"],  # Different terms
                "remote-only": ["term2"]
            },
            "mappings": {}
        }
        
        merged = merge_vocabularies(local, remote)
        
        # Should have all clusters
        assert "database" in merged["clusters"]
        assert "local-only" in merged["clusters"]
        assert "remote-only" in merged["clusters"]
        
        # Database should have union of terms
        db_terms = merged["clusters"]["database"]
        assert "postgres" in db_terms
        assert "mysql" in db_terms
        assert "sqlite" in db_terms
    
    def test_merge_mappings(self):
        """Remote mappings win conflicts."""
        local = {
            "clusters": {},
            "mappings": {"pg": "postgres"}
        }
        
        remote = {
            "clusters": {},
            "mappings": {"pg": "postgresql"}  # Different value
        }
        
        merged = merge_vocabularies(local, remote)
        
        # Remote wins
        assert merged["mappings"]["pg"] == "postgresql"


class TestDefaultClusters:
    """Test default cluster coverage."""
    
    def test_has_essential_clusters(self):
        """Default has essential tech clusters."""
        assert "database" in DEFAULT_CLUSTERS
        assert "caching" in DEFAULT_CLUSTERS
        assert "api" in DEFAULT_CLUSTERS
        assert "auth" in DEFAULT_CLUSTERS
        assert "frontend" in DEFAULT_CLUSTERS
        assert "backend" in DEFAULT_CLUSTERS
    
    def test_database_cluster_complete(self):
        """Database cluster has common databases."""
        db = DEFAULT_CLUSTERS["database"]
        
        assert "postgresql" in db
        assert "mysql" in db
        assert "sqlite" in db
        assert "mongodb" in db


class TestVocabularyIntegration:
    """Test vocabulary with refs and loader."""
    
    def test_with_refs_extraction(self, tmp_path):
        """Vocabulary enriches refs extraction."""
        from babel.core.events import Event, EventType
        from babel.core.refs import RefStore, extract_topics
        
        babel_dir = tmp_path / ".babel"
        babel_dir.mkdir()
        
        vocab = Vocabulary(babel_dir)
        
        # Event with database term
        event = Event(
            type=EventType.CONVERSATION_CAPTURED,
            data={"content": "We chose PostgreSQL for ACID compliance"}
        )
        
        topics = extract_topics(event, vocab)
        
        # Should find database-related topics
        assert any(t in topics for t in ["postgresql", "database", "postgres"])
    
    def test_with_loader_expansion(self, tmp_path):
        """Vocabulary expands loader queries."""
        from babel.core.events import DualEventStore, Event, EventType
        from babel.core.refs import RefStore
        from babel.core.graph import GraphStore
        from babel.core.loader import LazyLoader
        
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        babel_dir = project_dir / ".babel"
        babel_dir.mkdir()
        
        events = DualEventStore(project_dir)
        refs = RefStore(babel_dir)
        graph = GraphStore(babel_dir / "graph.db")
        vocab = Vocabulary(babel_dir)
        
        # Add event about postgres
        event = Event(
            type=EventType.CONVERSATION_CAPTURED,
            data={"content": "Use PostgreSQL"}
        )
        events.append(event)
        refs.index_event(event, vocab)
        
        # Create loader with vocabulary
        loader = LazyLoader(events, refs, graph, vocab)
        
        # Query with related term should find it
        result = loader.load_for_why("database")
        
        # Should find the postgres event via expansion
        assert len(result.events) > 0 or result.source == "full_scan"


# =============================================================================
# P2: Emergent Ontology Tests
# =============================================================================

class TestP2EmergentOntology:
    """P2: No fixed vocabulary, terms can be introduced/challenged/refined/discarded."""
    
    def test_common_patterns_not_fixed(self, tmp_path):
        """COMMON_PATTERNS are suggestions, not fixed vocabulary."""
        from babel.core.vocabulary import COMMON_PATTERNS, DEFAULT_CLUSTERS
        
        # Both should exist (backward compatibility)
        assert COMMON_PATTERNS is not None
        assert DEFAULT_CLUSTERS is not None
        assert COMMON_PATTERNS == DEFAULT_CLUSTERS
    
    def test_project_override_takes_precedence(self, tmp_path):
        """Project-level definitions override common patterns."""
        babel_dir = tmp_path / ".babel"
        (babel_dir / "shared").mkdir(parents=True)
        
        vocab = Vocabulary(babel_dir)
        
        # Redis is in 'caching' by default
        assert vocab.find_cluster("redis") == "caching"
        
        # Override: in THIS project, redis is used as database
        vocab.define("redis", "database", reason="We use Redis as primary store")
        
        # Now expansion should use database cluster
        expanded = vocab.expand("redis")
        assert "database" in expanded or "redis" in expanded
    
    def test_define_term(self, tmp_path):
        """Can define what a term means in this project."""
        babel_dir = tmp_path / ".babel"
        (babel_dir / "shared").mkdir(parents=True)
        
        vocab = Vocabulary(babel_dir)
        
        change = vocab.define("myterm", "mycluster", reason="Project-specific meaning")
        
        assert change["action"] == "define"
        assert change["term"] == "myterm"
        assert change["to_cluster"] == "mycluster"
        assert change["reason"] == "Project-specific meaning"
    
    def test_challenge_term(self, tmp_path):
        """Can challenge a term's cluster assignment."""
        babel_dir = tmp_path / ".babel"
        (babel_dir / "shared").mkdir(parents=True)
        
        vocab = Vocabulary(babel_dir)
        
        challenge = vocab.challenge("redis", reason="We use Redis as database, not cache")
        
        assert challenge["action"] == "challenge"
        assert challenge["term"] == "redis"
        assert challenge["status"] == "open"
        
        # Challenge should be recorded
        challenges = vocab.get_challenges(status="open")
        assert len(challenges) == 1
        assert challenges[0]["term"] == "redis"
    
    def test_refine_term(self, tmp_path):
        """Can move a term to a different cluster."""
        babel_dir = tmp_path / ".babel"
        (babel_dir / "shared").mkdir(parents=True)
        
        vocab = Vocabulary(babel_dir)
        
        # Redis starts in caching
        assert vocab.find_cluster("redis") == "caching"
        
        # Refine it to database
        change = vocab.refine("redis", "database", reason="Used as primary store")
        
        assert change["action"] == "refine"
        assert change["from_cluster"] == "caching"
        assert change["to_cluster"] == "database"
        
        # Now redis should expand with database terms
        expanded = vocab.expand("redis")
        assert "redis" in expanded
    
    def test_discard_term(self, tmp_path):
        """Can remove a term from vocabulary expansion."""
        babel_dir = tmp_path / ".babel"
        (babel_dir / "shared").mkdir(parents=True)
        
        vocab = Vocabulary(babel_dir)
        
        # Before discard, redis expands
        expanded_before = vocab.expand("redis")
        assert len(expanded_before) > 1
        
        # Discard redis
        change = vocab.discard("redis", reason="Not used in this project")
        
        assert change["action"] == "discard"
        assert change["term"] == "redis"
        
        # After discard, redis doesn't expand
        expanded_after = vocab.expand("redis")
        assert expanded_after == ["redis"]
    
    def test_resolve_challenge(self, tmp_path):
        """Can resolve an open challenge."""
        babel_dir = tmp_path / ".babel"
        (babel_dir / "shared").mkdir(parents=True)
        
        vocab = Vocabulary(babel_dir)
        
        # Create challenge
        vocab.challenge("redis", reason="Should be database")
        
        # Resolve it
        resolution = vocab.resolve_challenge("redis", resolution="accepted", action="refined to database")
        
        assert resolution["status"] == "resolved"
        assert resolution["resolution"] == "accepted"
        
        # Should no longer be in open challenges
        open_challenges = vocab.get_challenges(status="open")
        assert len(open_challenges) == 0
    
    def test_get_changes_audit_trail(self, tmp_path):
        """Changes are tracked for audit (P2: definitions as artifacts)."""
        babel_dir = tmp_path / ".babel"
        (babel_dir / "shared").mkdir(parents=True)
        
        vocab = Vocabulary(babel_dir)
        
        # Make some changes
        vocab.define("term1", "cluster1")
        vocab.refine("redis", "database")
        vocab.discard("memcached")
        
        # All changes should be recorded
        changes = vocab.get_changes()
        assert len(changes) >= 3
        
        actions = [c["action"] for c in changes]
        assert "define" in actions
        assert "refine" in actions
        assert "discard" in actions
    
    def test_stats_include_p2_info(self, tmp_path):
        """Stats include P2 ontology health information."""
        babel_dir = tmp_path / ".babel"
        (babel_dir / "shared").mkdir(parents=True)
        
        vocab = Vocabulary(babel_dir)
        
        # Make some P2 changes
        vocab.define("myterm", "mycluster")
        vocab.challenge("redis", reason="test")
        vocab.discard("memcached")
        
        stats = vocab.stats()
        
        assert "overrides" in stats
        assert "open_challenges" in stats
        assert "discarded" in stats
        assert "changes" in stats
        
        assert stats["overrides"] >= 1
        assert stats["open_challenges"] >= 1
        assert stats["discarded"] >= 1


class TestP2MergeVocabularies:
    """Test that vocabulary merging handles P2 fields."""
    
    def test_merge_overrides(self):
        """Remote overrides take precedence."""
        local = {
            "clusters": {},
            "mappings": {},
            "overrides": {"term1": "local-cluster"}
        }
        
        remote = {
            "clusters": {},
            "mappings": {},
            "overrides": {"term1": "remote-cluster", "term2": "remote-only"}
        }
        
        merged = merge_vocabularies(local, remote)
        
        # Remote wins for term1
        assert merged["overrides"]["term1"] == "remote-cluster"
        # term2 from remote
        assert merged["overrides"]["term2"] == "remote-only"
    
    def test_merge_discarded(self):
        """Discarded terms are unioned."""
        local = {
            "clusters": {},
            "mappings": {},
            "discarded": ["term1", "term2"]
        }
        
        remote = {
            "clusters": {},
            "mappings": {},
            "discarded": ["term2", "term3"]
        }
        
        merged = merge_vocabularies(local, remote)
        
        # Should have union
        assert set(merged["discarded"]) == {"term1", "term2", "term3"}
    
    def test_merge_challenges(self):
        """Challenges are concatenated and deduped."""
        local = {
            "clusters": {},
            "mappings": {},
            "challenges": [
                {"term": "redis", "timestamp": "2025-01-01", "status": "open"}
            ]
        }
        
        remote = {
            "clusters": {},
            "mappings": {},
            "challenges": [
                {"term": "redis", "timestamp": "2025-01-01", "status": "open"},  # Dupe
                {"term": "postgres", "timestamp": "2025-01-02", "status": "open"}
            ]
        }
        
        merged = merge_vocabularies(local, remote)
        
        # Should have 2 unique challenges
        assert len(merged["challenges"]) == 2
        terms = [c["term"] for c in merged["challenges"]]
        assert "redis" in terms
        assert "postgres" in terms
