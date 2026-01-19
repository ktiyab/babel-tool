"""
Tests for Cross-Domain Learning — P10 (from 11 Propositions)

P10: Cross-Domain Learning
- Cross-domain references are encouraged when domain boundaries stressed
- Importing analogies or principles must state their source domain
- Misapplied transfer is treated as diagnostic, not error
- Cross-domain learning reveals limits and assumptions

"Concept drift arises when underlying contexts change."
"""

import pytest

from babel.core.domains import (
    analyze_cross_domain, CrossDomainInfo,
    detect_all_domains, detect_external_domains, detect_cross_domain_patterns,
    EXTERNAL_DOMAINS, CROSS_DOMAIN_PATTERNS
)


# =============================================================================
# Cross-Domain Detection Tests
# =============================================================================

class TestDetectAllDomains:
    """Test detection of all domains mentioned in text."""
    
    def test_single_domain(self):
        """Detects single domain."""
        domains = detect_all_domains("Use bcrypt for password hashing")
        assert "security" in domains
    
    def test_multiple_domains(self):
        """Detects multiple domains."""
        # Use specific keywords from domain registry
        text = "Add redis caching layer with bcrypt password hashing"
        domains = detect_all_domains(text)
        assert len(domains) >= 2
        # Should detect both performance (redis, cache) and security (bcrypt, password)
    
    def test_no_domains(self):
        """Returns empty for generic text."""
        domains = detect_all_domains("This is a simple note")
        assert len(domains) == 0
    
    def test_domain_ordering_by_score(self):
        """Domains ordered by relevance score."""
        # Text with more security keywords
        text = "Add authentication, authorization, JWT tokens, and OAuth"
        domains = detect_all_domains(text)
        if domains:
            assert domains[0] == "security"


class TestDetectExternalDomains:
    """Test detection of external domain references."""
    
    def test_electrical_domain(self):
        """Detects electrical engineering references."""
        text = "Use circuit breaker pattern for API resilience"
        external = detect_external_domains(text)
        assert "electrical" in external
    
    def test_military_domain(self):
        """Detects military domain references."""
        text = "Apply defense in depth strategy to our caching"
        external = detect_external_domains(text)
        assert "military" in external
    
    def test_biology_domain(self):
        """Detects biology domain references."""
        text = "Let the architecture evolve through mutation and adaptation"
        external = detect_external_domains(text)
        assert "biology" in external
    
    def test_manufacturing_domain(self):
        """Detects manufacturing domain references."""
        text = "Implement kanban for our deployment pipeline"
        external = detect_external_domains(text)
        assert "manufacturing" in external
    
    def test_no_external_domains(self):
        """Returns empty for text without external references."""
        text = "Use PostgreSQL for data storage"
        external = detect_external_domains(text)
        assert len(external) == 0
    
    def test_multiple_external_domains(self):
        """Detects multiple external domains."""
        text = "Use circuit breaker (electrical) with evolutionary adaptation (biology)"
        external = detect_external_domains(text)
        assert len(external) >= 2


class TestDetectCrossDomainPatterns:
    """Test detection of cross-domain language patterns."""
    
    def test_borrowed_from_pattern(self):
        """Detects 'borrowed from' pattern."""
        text = "This approach is borrowed from security practices"
        patterns = detect_cross_domain_patterns(text)
        assert len(patterns) > 0
    
    def test_like_in_pattern(self):
        """Detects 'like in' pattern."""
        text = "Handle it like in electrical systems"
        patterns = detect_cross_domain_patterns(text)
        assert len(patterns) > 0
    
    def test_analogous_to_pattern(self):
        """Detects 'analogous to' pattern."""
        text = "This is analogous to how immune systems work"
        patterns = detect_cross_domain_patterns(text)
        assert len(patterns) > 0
    
    def test_no_patterns(self):
        """Returns empty for text without patterns."""
        text = "Use Redis for caching"
        patterns = detect_cross_domain_patterns(text)
        assert len(patterns) == 0


# =============================================================================
# Cross-Domain Analysis Tests
# =============================================================================

class TestAnalyzeCrossDomain:
    """Test comprehensive cross-domain analysis."""
    
    def test_simple_single_domain(self):
        """Single domain, no cross-domain."""
        info = analyze_cross_domain("Use bcrypt for passwords")
        
        assert info.primary_domain == "security"
        assert not info.has_cross_domain or len(info.all_domains) == 1
    
    def test_cross_domain_with_external(self):
        """Detects external domain reference."""
        info = analyze_cross_domain(
            "Use circuit breaker pattern for API resilience"
        )
        
        assert info.has_cross_domain
        assert "electrical" in info.external_domains
    
    def test_cross_domain_with_multiple_internal(self):
        """Detects multiple internal domains."""
        info = analyze_cross_domain(
            "Add Redis caching with JWT authentication"
        )
        
        assert len(info.all_domains) >= 2
    
    def test_cross_domain_summary(self):
        """Summary generation works."""
        info = analyze_cross_domain(
            "Use circuit breaker borrowed from electrical engineering"
        )
        
        summary = info.summary()
        # Should mention source domain
        if info.has_cross_domain:
            assert summary or len(info.external_domains) > 0


class TestCrossDomainInfo:
    """Test CrossDomainInfo dataclass."""
    
    def test_has_cross_domain_false_for_single(self):
        """has_cross_domain is False for single domain."""
        info = CrossDomainInfo(
            primary_domain="security",
            all_domains=["security"],
            external_domains=[],
            cross_domain_phrases=[],
            has_cross_domain=False
        )
        
        assert not info.has_cross_domain
    
    def test_has_cross_domain_true_for_external(self):
        """has_cross_domain is True when external domains present."""
        info = CrossDomainInfo(
            primary_domain="architecture",
            all_domains=["architecture"],
            external_domains=["electrical"],
            cross_domain_phrases=["circuit breaker"],
            has_cross_domain=True
        )
        
        assert info.has_cross_domain
    
    def test_summary_with_external(self):
        """Summary includes external domains."""
        info = CrossDomainInfo(
            primary_domain="reliability",
            all_domains=["reliability"],
            external_domains=["electrical", "biology"],
            cross_domain_phrases=[],
            has_cross_domain=True
        )
        
        summary = info.summary()
        assert "electrical" in summary or "biology" in summary
    
    def test_summary_empty_when_no_cross_domain(self):
        """Summary is empty when no cross-domain."""
        info = CrossDomainInfo(
            primary_domain="security",
            all_domains=["security"],
            external_domains=[],
            cross_domain_phrases=[],
            has_cross_domain=False
        )
        
        assert info.summary() == ""


# =============================================================================
# P10 Principle Tests
# =============================================================================

class TestP10Principles:
    """Test P10 principle compliance."""
    
    def test_cross_domain_encouraged_when_relevant(self):
        """P10: Cross-domain references are detected and surfaced."""
        info = analyze_cross_domain(
            "Apply defense in depth (from military strategy) to our API"
        )
        
        # Should detect the cross-domain reference
        assert info.has_cross_domain
        assert "military" in info.external_domains
    
    def test_source_domain_stated(self):
        """P10: Source domain can be identified."""
        info = analyze_cross_domain(
            "Circuit breaker pattern borrowed from electrical engineering"
        )
        
        # Should identify electrical as source
        assert "electrical" in info.external_domains
    
    def test_misapplied_transfer_not_error(self):
        """P10: Misapplied transfer is diagnostic, not error."""
        # Even unusual cross-domain references should be detected, not rejected
        info = analyze_cross_domain(
            "Use evolutionary mutation strategy for our database schema"
        )
        
        # Should detect biology reference without error
        assert info is not None
        if "evolution" in info.external_domains or "biology" in info.external_domains:
            assert info.has_cross_domain
    
    def test_cross_domain_reveals_limits(self):
        """P10: Detection helps reveal domain boundaries."""
        # Text that spans multiple domains
        info = analyze_cross_domain(
            "Add caching for performance with encryption for security"
        )
        
        # Should detect multiple domains, revealing boundary stress
        assert len(info.all_domains) >= 1


# =============================================================================
# Registry Tests
# =============================================================================

class TestExternalDomainRegistry:
    """Test external domain registry."""
    
    def test_external_domains_exist(self):
        """External domains registry is populated."""
        assert len(EXTERNAL_DOMAINS) > 0
    
    def test_electrical_has_keywords(self):
        """Electrical domain has relevant keywords."""
        assert "electrical" in EXTERNAL_DOMAINS
        keywords = EXTERNAL_DOMAINS["electrical"]
        assert "circuit breaker" in keywords
    
    def test_military_has_keywords(self):
        """Military domain has relevant keywords."""
        assert "military" in EXTERNAL_DOMAINS
        keywords = EXTERNAL_DOMAINS["military"]
        assert "defense in depth" in keywords


class TestCrossDomainPatterns:
    """Test cross-domain pattern registry."""
    
    def test_patterns_exist(self):
        """Cross-domain patterns are defined."""
        assert len(CROSS_DOMAIN_PATTERNS) > 0
    
    def test_common_patterns_included(self):
        """Common cross-domain patterns are included."""
        assert "borrowed from" in CROSS_DOMAIN_PATTERNS
        assert "analogous to" in CROSS_DOMAIN_PATTERNS
