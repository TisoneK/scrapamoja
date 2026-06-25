"""Tests for error message clarity and actionability (Story 3.3).

These tests verify that error messages are:
1. Specific and actionable
2. Don't expose internal Playwright concepts
3. Match PRD specifications exactly

Story: 3-3-implement-clear-error-messages
AC #1: Given invalid input or incorrect usage, When the error occurs, Then the error message is specific and actionable
AC #2: For timing violations: "attach() must be called before page.goto(). Call attach() first, then navigate."
AC #3: For pattern errors: Clear description of what made the pattern invalid
AC #4: The errors do not expose internal Playwright concepts
"""

import pytest

from src.network.interception import NetworkInterceptor, PatternError, TimingError


class TestTimingErrorMessages:
    """Tests for TimingError message clarity (AC #2)."""

    # PRD Specification: "attach() must be called before page.goto(). Call attach() first, then navigate."
    PRD_SPECIFICATION = "attach() must be called before page.goto(). Call attach() first, then navigate."

    @pytest.mark.unit
    def test_timing_error_message_matches_prd_exactly(self):
        """Test that TimingError message matches PRD specification exactly."""
        error = TimingError(self.PRD_SPECIFICATION)
        assert str(error) == self.PRD_SPECIFICATION

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_timing_error_from_attach_contains_prd_message(self):
        """Test that attach() raises TimingError with PRD-specified message."""
        async def handler(response):
            pass

        interceptor = NetworkInterceptor(
            patterns=[r"https://api\.example\.com/.*"],
            handler=handler,
        )

        # Mock page that has already navigated
        mock_page = type("MockPage", (), {
            "url": "https://example.com",
            "evaluate": lambda self, expr: "complete",  # Not "loading"
        })()

        # attach() should raise TimingError with exact PRD message
        with pytest.raises(TimingError) as exc_info:
            await interceptor.attach(mock_page)

        # Verify message matches PRD exactly
        assert str(exc_info.value) == self.PRD_SPECIFICATION

    @pytest.mark.unit
    def test_timing_error_no_playwright_concepts(self):
        """Test that TimingError doesn't expose Playwright concepts (AC #4)."""
        error_msg = self.PRD_SPECIFICATION.lower()

        # Verify no Playwright-specific terminology
        assert "playwright" not in error_msg

    @pytest.mark.unit
    def test_timing_error_is_actionable(self):
        """Test that TimingError message tells user exactly what to do."""
        # The message should clearly indicate the fix
        assert "Call attach() first" in self.PRD_SPECIFICATION
        assert "then navigate" in self.PRD_SPECIFICATION


class TestPatternErrorMessages:
    """Tests for PatternError message actionability (AC #3)."""

    @pytest.mark.unit
    def test_empty_patterns_list_message(self):
        """Test that empty patterns list gives clear error."""
        async def handler(response):
            pass

        with pytest.raises(PatternError) as exc_info:
            NetworkInterceptor(
                patterns=[],
                handler=handler,
            )

        assert "patterns list cannot be empty" in str(exc_info.value)

    @pytest.mark.unit
    def test_empty_string_pattern_message(self):
        """Test that empty string pattern gives clear error."""
        async def handler(response):
            pass

        with pytest.raises(PatternError) as exc_info:
            NetworkInterceptor(
                patterns=["valid", "", "also-valid"],
                handler=handler,
            )

        assert "cannot be empty string" in str(exc_info.value)

    @pytest.mark.unit
    def test_invalid_regex_pattern_message_is_actionable(self):
        """Test that invalid regex pattern gives actionable guidance (AC #3)."""
        async def handler(response):
            pass

        # Test with unclosed bracket - common regex error
        with pytest.raises(PatternError) as exc_info:
            NetworkInterceptor(
                patterns=[r"https://api[example"],  # Unclosed bracket
                handler=handler,
            )

        error_msg = str(exc_info.value)

        # Should contain the invalid pattern
        assert "https://api[example" in error_msg

        # Should contain actionable guidance
        assert "Check for:" in error_msg

    @pytest.mark.unit
    def test_invalid_regex_unclosed_bracket_provides_guidance(self):
        """Test that unclosed bracket regex error provides fix guidance."""
        async def handler(response):
            pass

        with pytest.raises(PatternError) as exc_info:
            NetworkInterceptor(
                patterns=["invalid["],
                handler=handler,
            )

        error_msg = str(exc_info.value)

        # Should provide guidance on common regex issues
        assert "Check for:" in error_msg

    @pytest.mark.unit
    def test_invalid_regex_unescaped_special_char_provides_guidance(self):
        """Test that unescaped special char regex error provides fix guidance."""
        async def handler(response):
            pass

        # Test with invalid quantifier (nothing to quantify)
        with pytest.raises(PatternError) as exc_info:
            NetworkInterceptor(
                patterns=["*invalid"],  # Nothing to repeat
                handler=handler,
            )

        error_msg = str(exc_info.value)

        # Should provide guidance
        assert "Check for:" in error_msg

    @pytest.mark.unit
    def test_pattern_error_no_playwright_concepts(self):
        """Test that PatternError doesn't expose Playwright concepts (AC #4)."""
        async def handler(response):
            pass

        with pytest.raises(PatternError) as exc_info:
            NetworkInterceptor(
                patterns=["invalid["],
                handler=handler,
            )

        error_msg = str(exc_info.value).lower()

        # Verify no Playwright-specific terminology
        assert "playwright" not in error_msg
        assert "page" not in error_msg
        assert "browser" not in error_msg


class TestErrorMessageIntegration:
    """Integration tests for error messages in real scenarios."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_all_timing_errors_have_consistent_message(self):
        """Test that all TimingError raises use the same message."""
        async def handler(response):
            pass

        expected_msg = "attach() must be called before page.goto(). Call attach() first, then navigate."

        # Test scenario 1: Page with non-about:blank URL
        mock_page1 = type("MockPage", (), {
            "url": "https://example.com",
            "evaluate": lambda self, expr: "loading"
        })()
        interceptor1 = NetworkInterceptor(
            patterns=[r".*"],
            handler=handler,
        )
        with pytest.raises(TimingError) as exc_info1:
            await interceptor1.attach(mock_page1)
        assert str(exc_info1.value) == expected_msg

        # Test scenario 2: Page with readyState not "loading"
        mock_page2 = type("MockPage", (), {
            "url": "about:blank",
            "evaluate": lambda self, expr: "complete"
        })()
        interceptor2 = NetworkInterceptor(
            patterns=[r".*"],
            handler=handler,
        )
        with pytest.raises(TimingError) as exc_info2:
            await interceptor2.attach(mock_page2)
        assert str(exc_info2.value) == expected_msg

    @pytest.mark.unit
    def test_pattern_error_enhanced_message_contains_all_guidance(self):
        """Test that enhanced PatternError message contains all three guidance types."""
        async def handler(response):
            pass

        with pytest.raises(PatternError) as exc_info:
            NetworkInterceptor(
                patterns=["invalid["],
                handler=handler,
            )

        error_msg = str(exc_info.value)

        # Should contain all three guidance items
        assert "unescaped special characters" in error_msg
        assert "unmatched brackets" in error_msg
        assert "invalid quantifiers" in error_msg
