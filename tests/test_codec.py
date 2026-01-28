"""
Tests for IDCodec — Hash-based ID aliasing validation

Tests the AA-BB format code generation and resolution.
Validates cross-type collision avoidance (Option A fix).
"""


from babel.presentation.codec import IDCodec, CODE_PATTERN


class TestCodecBasics:
    """Basic codec functionality."""

    def test_encode_returns_aa_bb_format(self):
        """Encoded ID matches AA-BB pattern."""
        codec = IDCodec()
        code = codec.encode("abc12345")
        assert CODE_PATTERN.match(code)

    def test_encode_is_deterministic(self):
        """Same ID always produces same code."""
        codec = IDCodec()
        code1 = codec.encode("test_id_123")
        code2 = codec.encode("test_id_123")
        assert code1 == code2

    def test_encode_empty_returns_empty(self):
        """Empty input returns empty output."""
        codec = IDCodec()
        assert codec.encode("") == ""
        assert codec.encode(None) is None

    def test_is_short_code_validates_pattern(self):
        """is_short_code correctly validates AA-BB format."""
        codec = IDCodec()
        assert codec.is_short_code("AB-CD") is True
        assert codec.is_short_code("ab-cd") is True  # Case insensitive
        assert codec.is_short_code("ABC-D") is False
        assert codec.is_short_code("AB-CDE") is False
        assert codec.is_short_code("ABCD") is False
        assert codec.is_short_code("") is False


class TestCodecDecoding:
    """Decode functionality tests."""

    def test_decode_resolves_from_candidates(self):
        """Decode finds matching candidate."""
        codec = IDCodec()
        candidates = ["id_alpha", "id_beta", "id_gamma"]

        # Get code for one candidate
        code = codec.encode("id_beta")

        # Should resolve back
        resolved = codec.decode(code, candidates)
        assert resolved == "id_beta"

    def test_decode_passthrough_without_candidates(self):
        """Decode returns code when no candidates provided."""
        codec = IDCodec()
        code = "AB-CD"
        assert codec.decode(code, None) == code
        assert codec.decode(code, []) == code

    def test_decode_passthrough_no_match(self):
        """Decode returns code when no candidate matches."""
        codec = IDCodec()
        candidates = ["id_alpha", "id_beta"]
        code = "ZZ-ZZ"  # Unlikely to match
        assert codec.decode(code, candidates) == code


class TestCrossTypeCollisionAvoidance:
    """
    Validates Option A fix: type prefix is preserved in hash.

    Different artifact types with same underlying hash MUST produce
    different codes to avoid confusion in commands like `babel endorse`.
    """

    def test_different_types_same_hash_different_codes(self):
        """decision_X and constraint_X produce different codes."""
        codec = IDCodec()

        # Same underlying hash, different type prefixes
        decision_code = codec.encode("decision_abc12345")
        constraint_code = codec.encode("constraint_abc12345")

        # MUST be different (this was the bug)
        assert decision_code != constraint_code

    def test_all_type_prefixes_produce_unique_codes(self):
        """All standard type prefixes with same hash are unique."""
        codec = IDCodec()
        base_hash = "xyz98765"

        prefixed_ids = [
            f"decision_{base_hash}",
            f"purpose_{base_hash}",
            f"constraint_{base_hash}",
            f"principle_{base_hash}",
            f"requirement_{base_hash}",
            f"tension_{base_hash}",
        ]

        codes = [codec.encode(pid) for pid in prefixed_ids]

        # All codes must be unique
        assert len(codes) == len(set(codes)), "Cross-type collision detected!"

    def test_unprefixed_ids_still_work(self):
        """Raw IDs without type prefix still encode correctly."""
        codec = IDCodec()

        code1 = codec.encode("abc12345")
        code2 = codec.encode("def67890")

        # Should still produce valid codes
        assert CODE_PATTERN.match(code1)
        assert CODE_PATTERN.match(code2)

        # Different IDs should produce different codes
        assert code1 != code2


class TestFormatWithCode:
    """Test format_with_code helper."""

    def test_format_with_code_output(self):
        """format_with_code produces [AA-BB] text format."""
        codec = IDCodec()
        result = codec.format_with_code("some_id", "Use SQLite")

        # Should match [XX-XX] pattern at start
        assert result.startswith("[")
        assert "] Use SQLite" in result
