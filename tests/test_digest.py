"""
Tests for digest generation module.

Tests semantic summary generation using YAKE keyword extraction.
Covers: sentence splitting, technical term extraction, digest generation.
"""



# =============================================================================
# Sentence Splitting Tests
# =============================================================================

class TestSentenceSplitting:
    """Test split_sentences function."""

    def test_splits_simple_sentences(self):
        """Splits basic sentences correctly."""
        from babel.presentation.digest import split_sentences

        text = "First sentence. Second sentence. Third sentence."
        result = split_sentences(text)

        assert len(result) == 3
        assert result[0] == "First sentence."
        assert result[1] == "Second sentence."
        assert result[2] == "Third sentence."

    def test_handles_abbreviations(self):
        """Preserves abbreviations without splitting."""
        from babel.presentation.digest import split_sentences

        text = "Dr. Smith recommends e.g. caching. This helps performance."
        result = split_sentences(text)

        # Should NOT split on "Dr." or "e.g."
        assert len(result) == 2
        assert "Dr." in result[0]
        assert "e.g." in result[0]

    def test_handles_decimal_numbers(self):
        """Preserves decimal numbers without splitting."""
        from babel.presentation.digest import split_sentences

        text = "The value is 3.14 for pi. Also 2.718 for e."
        result = split_sentences(text)

        assert len(result) == 2
        assert "3.14" in result[0]
        assert "2.718" in result[1]

    def test_handles_empty_string(self):
        """Returns empty list for empty input."""
        from babel.presentation.digest import split_sentences

        assert split_sentences("") == []
        assert split_sentences(None) == []

    def test_handles_single_sentence(self):
        """Returns single sentence without splitting."""
        from babel.presentation.digest import split_sentences

        text = "This is a single sentence without period"
        result = split_sentences(text)

        assert len(result) == 1
        assert result[0] == text


# =============================================================================
# Technical Term Extraction Tests
# =============================================================================

class TestTechnicalTermExtraction:
    """Test extract_technical_terms function."""

    def test_extracts_camelcase(self):
        """Extracts CamelCase terms."""
        from babel.presentation.digest import extract_technical_terms

        text = "Use UserService and OrderManagement for the app."
        terms = extract_technical_terms(text)

        assert "UserService" in terms or "OrderManagement" in terms

    def test_extracts_acronyms(self):
        """Extracts ACRONYM terms."""
        from babel.presentation.digest import extract_technical_terms

        text = "The API uses CRUD operations and SQL queries."
        terms = extract_technical_terms(text)

        assert "API" in terms
        assert "CRUD" in terms
        assert "SQL" in terms

    def test_extracts_snake_case(self):
        """Extracts snake_case terms."""
        from babel.presentation.digest import extract_technical_terms

        text = "Set the rate_limit and max_connections values."
        terms = extract_technical_terms(text)

        assert "rate_limit" in terms
        assert "max_connections" in terms

    def test_extracts_kebab_case(self):
        """Extracts kebab-case terms."""
        from babel.presentation.digest import extract_technical_terms

        text = "Use blue-green deployments and event-sourcing."
        terms = extract_technical_terms(text)

        assert "blue-green" in terms
        assert "event-sourcing" in terms

    def test_extracts_numbers_with_units(self):
        """Extracts numbers with units."""
        from babel.presentation.digest import extract_technical_terms

        text = "Timeout is 30s with rate limit of 1000/min."
        terms = extract_technical_terms(text)

        assert "30s" in terms
        assert "1000/min" in terms

    def test_deduplicates_terms(self):
        """Removes duplicate terms."""
        from babel.presentation.digest import extract_technical_terms

        text = "API calls the API which returns API responses."
        terms = extract_technical_terms(text)

        # Should only have one "API"
        api_count = sum(1 for t in terms if t.upper() == "API")
        assert api_count == 1


# =============================================================================
# DigestGenerator Tests
# =============================================================================

class TestDigestGenerator:
    """Test DigestGenerator class."""

    def test_returns_short_content_unchanged(self):
        """Short content returned as-is."""
        from babel.presentation.digest import DigestGenerator

        gen = DigestGenerator()
        short = "Short content here."

        result = gen.generate(short)
        assert result == short

    def test_extracts_first_sentence(self):
        """Extracts first sentence for digest."""
        from babel.presentation.digest import DigestGenerator

        gen = DigestGenerator()
        text = "Use Redis for caching. This helps with rate limits. Performance improves significantly."

        result = gen.generate(text)

        # First sentence should be at the start
        assert result.startswith("Use Redis for caching.")

    def test_appends_keywords(self):
        """Appends keywords not in first sentence."""
        from babel.presentation.digest import DigestGenerator

        gen = DigestGenerator()
        text = "Use Redis for caching. The API has rate limits. Performance improves with local storage."

        result = gen.generate(text)

        # Should have keywords in brackets
        assert "[" in result
        assert "]" in result

    def test_handles_empty_content(self):
        """Returns empty string for empty input."""
        from babel.presentation.digest import DigestGenerator

        gen = DigestGenerator()

        assert gen.generate("") == ""
        assert gen.generate(None) == ""

    def test_respects_max_keywords(self):
        """Limits keywords to max_keywords parameter."""
        from babel.presentation.digest import DigestGenerator

        gen = DigestGenerator(max_keywords=2)
        text = "First sentence here. API calls CRUD operations SQL queries HTTP requests REST endpoints."

        result = gen.generate(text, max_keywords=2)

        # Count keywords in brackets
        if "[" in result:
            bracket_content = result[result.index("[") + 1:result.index("]")]
            keywords = [k.strip() for k in bracket_content.split(",")]
            assert len(keywords) <= 2


# =============================================================================
# Module Function Tests
# =============================================================================

class TestModuleFunctions:
    """Test module-level convenience functions."""

    def test_generate_digest_function(self):
        """generate_digest() works correctly."""
        from babel.presentation.digest import generate_digest

        text = "Use Redis for caching. This helps performance. Rate limits are strict."
        result = generate_digest(text)

        assert isinstance(result, str)
        assert len(result) > 0
        assert "Redis" in result or "caching" in result

    def test_generate_digest_with_content_type(self):
        """generate_digest() accepts content_type parameter."""
        from babel.presentation.digest import generate_digest

        text = "All migrations must be backward-compatible. We run blue-green deployments."
        result = generate_digest(text, content_type="constraint")

        assert isinstance(result, str)
        assert len(result) > 0


# =============================================================================
# Integration Tests
# =============================================================================

class TestFormatterIntegration:
    """Test integration with formatters module."""

    def test_generate_summary_available(self):
        """generate_summary is available from formatters."""
        from babel.presentation.formatters import generate_summary

        text = "Use Redis for caching. This helps with API rate limits."
        result = generate_summary(text)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_summary_full_mode(self):
        """generate_summary respects full=True."""
        from babel.presentation.formatters import generate_summary

        text = "Use Redis for caching. This helps with API rate limits. Performance is critical."
        result = generate_summary(text, full=True)

        # Full mode returns complete text
        assert result == text

    def test_presentation_package_exports(self):
        """Digest functions exported from presentation package."""
        from babel.presentation import generate_summary, generate_digest

        assert callable(generate_summary)
        assert callable(generate_digest)


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_unicode(self):
        """Handles unicode characters correctly."""
        from babel.presentation.digest import generate_digest

        text = "Use Redis pour le caching. Les limites sont strictes."
        result = generate_digest(text)

        assert isinstance(result, str)

    def test_handles_special_characters(self):
        """Handles special characters in content."""
        from babel.presentation.digest import generate_digest

        text = "Use Redis (v7.0+) for caching. Supports: JSON, Streams & more."
        result = generate_digest(text)

        assert isinstance(result, str)

    def test_handles_very_long_content(self):
        """Handles very long content efficiently."""
        from babel.presentation.digest import generate_digest

        # Create long content
        long_text = "First sentence is important. " + "Additional context. " * 100
        result = generate_digest(long_text)

        # Should be much shorter than original
        assert len(result) < len(long_text)

    def test_handles_no_sentences(self):
        """Handles content without sentence boundaries."""
        from babel.presentation.digest import generate_digest

        text = "content without any sentence ending punctuation at all"
        result = generate_digest(text)

        # Should return something reasonable
        assert isinstance(result, str)
