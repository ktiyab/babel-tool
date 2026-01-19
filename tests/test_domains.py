"""
Tests for Domains — P3 Expertise Governance

P3: Authority derives from declared, bounded expertise.
- Domain attribution
- Scan type linkage
- Vocabulary cluster mapping
- AI role boundaries
"""

import pytest
from babel.core.domains import (
    DOMAIN_REGISTRY,
    DomainSpec,
    infer_domain_from_text,
    infer_domain_from_clusters,
    get_domain_for_scan_type,
    get_scan_type_for_domain,
    get_clusters_for_domain,
    suggest_domain_for_capture,
    validate_domain,
    list_domains,
    get_domain_spec,
    score_decision_relevance,
    get_related_domains,
    AIRole,
)


# =============================================================================
# Domain Registry Tests
# =============================================================================

class TestDomainRegistry:
    """Test the domain registry structure."""
    
    def test_registry_has_core_domains(self):
        """Core domains are defined."""
        core_domains = ["security", "performance", "architecture", "reliability"]
        for domain in core_domains:
            assert domain in DOMAIN_REGISTRY
    
    def test_domain_spec_structure(self):
        """Domain specs have required fields."""
        for name, spec in DOMAIN_REGISTRY.items():
            assert isinstance(spec, DomainSpec)
            assert spec.name == name
            assert spec.scan_type is not None
            assert isinstance(spec.vocab_clusters, list)
            assert isinstance(spec.keywords, list)
            assert spec.description is not None
    
    def test_each_domain_has_scan_type(self):
        """Each domain maps to a scan type."""
        for name, spec in DOMAIN_REGISTRY.items():
            assert spec.scan_type in ["health", "architecture", "security", "performance", "dependencies"]


# =============================================================================
# Domain Inference Tests
# =============================================================================

class TestDomainInference:
    """Test domain inference from text and clusters."""
    
    def test_infer_security_from_text(self):
        """Security keywords trigger security domain."""
        texts = [
            "Use bcrypt for password hashing",
            "Add OAuth2 authentication",
            "Fix XSS vulnerability in form",
            "Enable TLS encryption",
        ]
        for text in texts:
            domain = infer_domain_from_text(text)
            assert domain == "security", f"Expected security for: {text}"
    
    def test_infer_performance_from_text(self):
        """Performance keywords trigger performance domain."""
        texts = [
            "Add Redis caching layer",
            "Optimize query latency",
            "Improve throughput with batching",
        ]
        for text in texts:
            domain = infer_domain_from_text(text)
            assert domain == "performance", f"Expected performance for: {text}"
    
    def test_infer_architecture_from_text(self):
        """Architecture keywords trigger architecture domain."""
        texts = [
            "Switch to microservice pattern",
            "Implement REST API",
            "Use event-driven architecture",
        ]
        for text in texts:
            domain = infer_domain_from_text(text)
            assert domain == "architecture", f"Expected architecture for: {text}"
    
    def test_infer_returns_none_for_generic_text(self):
        """Generic text returns None."""
        domain = infer_domain_from_text("We had a meeting yesterday")
        assert domain is None
    
    def test_infer_from_clusters(self):
        """Can infer domain from vocabulary clusters."""
        assert infer_domain_from_clusters(["security"]) == "security"
        assert infer_domain_from_clusters(["caching"]) == "performance"
        assert infer_domain_from_clusters(["database"]) == "architecture"
    
    def test_infer_from_clusters_unknown(self):
        """Unknown clusters return None."""
        assert infer_domain_from_clusters(["unknown_cluster"]) is None


# =============================================================================
# Domain-Scan Mapping Tests
# =============================================================================

class TestDomainScanMapping:
    """Test linkage between domains and scan types."""
    
    def test_get_scan_type_for_domain(self):
        """Domains map to correct scan types."""
        assert get_scan_type_for_domain("security") == "security"
        assert get_scan_type_for_domain("performance") == "performance"
        assert get_scan_type_for_domain("architecture") == "architecture"
        assert get_scan_type_for_domain("reliability") == "health"
    
    def test_get_domain_for_scan_type(self):
        """Scan types map back to domains."""
        # Note: Multiple domains may map to same scan type
        domain = get_domain_for_scan_type("security")
        assert domain == "security"
    
    def test_get_clusters_for_domain(self):
        """Domains map to vocabulary clusters."""
        security_clusters = get_clusters_for_domain("security")
        assert "security" in security_clusters
        assert "auth" in security_clusters
        
        perf_clusters = get_clusters_for_domain("performance")
        assert "caching" in perf_clusters


# =============================================================================
# Suggestion Tests
# =============================================================================

class TestDomainSuggestion:
    """Test domain suggestion for captures."""
    
    def test_suggest_from_text(self):
        """Suggests domain based on text content."""
        domain = suggest_domain_for_capture("Use bcrypt for passwords")
        assert domain == "security"
    
    def test_suggest_from_clusters_takes_precedence(self):
        """Vocabulary clusters take precedence over text inference."""
        # Even with security text, if clusters say otherwise...
        domain = suggest_domain_for_capture(
            "Use bcrypt",  # Would be security
            vocab_clusters=["caching"]  # But clusters say performance
        )
        assert domain == "performance"
    
    def test_suggest_returns_none_for_generic(self):
        """Returns None for generic content."""
        domain = suggest_domain_for_capture("We discussed options")
        assert domain is None


# =============================================================================
# Validation Tests
# =============================================================================

class TestValidation:
    """Test domain validation."""
    
    def test_validate_known_domain(self):
        """Known domains validate."""
        assert validate_domain("security") is True
        assert validate_domain("performance") is True
    
    def test_validate_unknown_domain(self):
        """Unknown domains don't validate."""
        assert validate_domain("unknown") is False
        assert validate_domain("") is False
    
    def test_list_domains(self):
        """Can list all domains."""
        domains = list_domains()
        assert "security" in domains
        assert "performance" in domains
        assert len(domains) >= 5
    
    def test_get_domain_spec(self):
        """Can get full domain specification."""
        spec = get_domain_spec("security")
        assert spec is not None
        assert spec.name == "security"
        assert "bcrypt" in spec.keywords


# =============================================================================
# Relevance Scoring Tests
# =============================================================================

class TestRelevanceScoring:
    """Test decision relevance scoring for scans."""
    
    def test_base_score(self):
        """Decisions without domain get base score."""
        decision = {"summary": "Some decision"}
        score = score_decision_relevance(decision, "security")
        assert score == 0.5  # Base score
    
    def test_domain_match_bonus(self):
        """Matching domain gets bonus."""
        decision = {"summary": "Use bcrypt", "domain": "security"}
        score = score_decision_relevance(decision, "security")
        assert score > 0.5  # Should have bonus
    
    def test_related_domain_smaller_bonus(self):
        """Related domains get smaller bonus."""
        decision = {"summary": "Secure API", "domain": "architecture"}
        score = score_decision_relevance(decision, "security")
        # Architecture is related to security
        assert score >= 0.5  # At least base
    
    def test_get_related_domains(self):
        """Can get related domains."""
        related = get_related_domains("security")
        assert "architecture" in related
        assert "devops" in related


# =============================================================================
# AI Role Tests (P3: AI not arbiter)
# =============================================================================

class TestAIRole:
    """Test AI role declarations for P3 compliance."""
    
    def test_role_constants(self):
        """AI roles are defined."""
        assert AIRole.PATTERN_DETECTOR == "pattern_detector"
        assert AIRole.SYNTHESIZER == "synthesizer"
        assert AIRole.CHALLENGER == "challenger"
    
    def test_format_output(self):
        """Can format output with role declaration."""
        output = AIRole.format_output(AIRole.PATTERN_DETECTOR, "Found 3 patterns")
        assert "[Pattern detected]" in output
        assert "Found 3 patterns" in output
    
    def test_is_arbiter_claim_positive(self):
        """Detects arbiter-like language."""
        arbiter_texts = [
            "You must use PostgreSQL",
            "You should definitely switch to React",
            "The only way to do this is...",
            "This is the correct approach",
        ]
        for text in arbiter_texts:
            assert AIRole.is_arbiter_claim(text), f"Should detect arbiter claim: {text}"
    
    def test_is_arbiter_claim_negative(self):
        """Non-arbiter language passes."""
        ok_texts = [
            "Consider using PostgreSQL",
            "You might want to try React",
            "One approach is...",
            "Based on your constraints, this could work",
        ]
        for text in ok_texts:
            assert not AIRole.is_arbiter_claim(text), f"Should not be arbiter: {text}"


# =============================================================================
# Integration with Events
# =============================================================================

class TestDomainEventIntegration:
    """Test domain integration with event system."""
    
    def test_capture_with_domain(self, tmp_path):
        """Captures can include domain."""
        from babel.core.events import capture_conversation
        
        event = capture_conversation(
            "Use bcrypt for password hashing",
            domain="security"
        )
        
        assert event.data["domain"] == "security"
    
    def test_capture_without_domain(self, tmp_path):
        """Captures without domain still work."""
        from babel.core.events import capture_conversation
        
        event = capture_conversation("Generic text")
        
        assert "domain" not in event.data or event.data.get("domain") is None


# =============================================================================
# Integration with Scanner
# =============================================================================

class TestDomainScannerIntegration:
    """Test domain integration with scanner."""
    
    def test_scan_context_includes_domain_decisions(self, tmp_path):
        """ScanContext groups decisions by domain."""
        from babel.services.scanner import ScanContext
        
        decisions = [
            {"summary": "Use bcrypt", "domain": "security"},
            {"summary": "Add Redis cache", "domain": "performance"},
            {"summary": "Use REST API", "domain": "architecture"},
        ]
        
        context = ScanContext(
            need=None,
            purpose="Test project",
            decisions=decisions,
            constraints=[],
            tech_stack=[],
            recent_topics=[],
            event_count=3,
            domain_decisions={
                "security": [decisions[0]],
                "performance": [decisions[1]],
                "architecture": [decisions[2]],
            }
        )
        
        assert len(context.get_decisions_for_domain("security")) == 1
        assert len(context.get_decisions_for_domain("performance")) == 1
        assert len(context.get_decisions_for_domain("unknown")) == 0
    
    def test_to_prompt_includes_domain_tags(self, tmp_path):
        """Prompt output includes domain tags."""
        from babel.services.scanner import ScanContext
        
        decisions = [
            {"summary": "Use bcrypt", "domain": "security"},
        ]
        
        context = ScanContext(
            need=None,
            purpose="Test",
            decisions=decisions,
            constraints=[],
            tech_stack=[],
            recent_topics=[],
            event_count=1,
            domain_decisions={"security": decisions}
        )
        
        prompt = context.to_prompt()
        assert "[security]" in prompt
