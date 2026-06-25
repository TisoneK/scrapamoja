"""Tests for exception classes."""

import pytest

from src.network.interception import PatternError, TimingError


class TestTimingError:
    """Tests for TimingError exception."""

    def test_timing_error_is_exception(self):
        """Test that TimingError inherits from Exception."""
        assert issubclass(TimingError, Exception)

    def test_timing_error_can_be_raised(self):
        """Test that TimingError can be raised with message."""
        with pytest.raises(TimingError) as exc_info:
            raise TimingError("attach() must be called before page.goto()")
        
        assert "attach() must be called before page.goto()" in str(exc_info.value)

    def test_timing_error_default_message(self):
        """Test TimingError with default message."""
        with pytest.raises(TimingError):
            raise TimingError()


class TestPatternError:
    """Tests for PatternError exception."""

    def test_pattern_error_is_exception(self):
        """Test that PatternError inherits from Exception."""
        assert issubclass(PatternError, Exception)

    def test_pattern_error_can_be_raised(self):
        """Test that PatternError can be raised with message."""
        with pytest.raises(PatternError) as exc_info:
            raise PatternError("Invalid regex pattern: [unclosed")
        
        assert "Invalid regex pattern" in str(exc_info.value)

    def test_pattern_error_default_message(self):
        """Test PatternError with default message."""
        with pytest.raises(PatternError):
            raise PatternError()
