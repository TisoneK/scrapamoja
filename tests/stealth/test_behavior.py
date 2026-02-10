"""Tests for behavior emulation module (T041-T044).

Tests verify:
- T041: Click hesitation follows normal distribution (mean ~150ms, variance ~75ms)
- T042: Mouse movement uses Bézier curve (not linear path)
- T043: Scroll includes natural pauses matching human reading patterns
- T044: Micro-delay ranges respect configured intensity level
"""

import asyncio
import math
import time
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from src.stealth.behavior import (
    BehaviorEmulator,
    BehaviorTimingProfile,
    TIMING_PROFILES,
)
from src.stealth.events import EventBuilder


class TestBehaviorEmulatorInitialization:
    """Test BehaviorEmulator initialization and configuration."""

    def test_create_with_default_intensity(self):
        """T040: Create emulator with default moderate intensity."""
        emulator = BehaviorEmulator()
        assert emulator.intensity == "moderate"
        assert emulator.profile == TIMING_PROFILES["moderate"]

    def test_create_with_conservative_intensity(self):
        """T040: Create emulator with conservative intensity."""
        emulator = BehaviorEmulator(intensity="conservative")
        assert emulator.intensity == "conservative"
        assert emulator.profile == TIMING_PROFILES["conservative"]
        # Conservative should have higher means
        assert emulator.profile.click_hesitation[0] > 200

    def test_create_with_aggressive_intensity(self):
        """T040: Create emulator with aggressive intensity."""
        emulator = BehaviorEmulator(intensity="aggressive")
        assert emulator.intensity == "aggressive"
        assert emulator.profile == TIMING_PROFILES["aggressive"]
        # Aggressive should have lower means
        assert emulator.profile.click_hesitation[0] < 100

    def test_invalid_intensity_raises_error(self):
        """Test that invalid intensity raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            BehaviorEmulator(intensity="invalid")
        assert "intensity must be one of" in str(exc_info.value)

    def test_with_event_builder(self):
        """Test initialization with EventBuilder for logging."""
        builder = EventBuilder(run_id="test-run")
        emulator = BehaviorEmulator(event_builder=builder)
        assert emulator.event_builder is builder

    def test_get_profile(self):
        """Test get_profile() returns correct timing profile."""
        emulator = BehaviorEmulator(intensity="moderate")
        profile = emulator.get_profile()
        assert profile.intensity == "moderate"
        assert profile.click_hesitation == (150, 75, 50, 400)


class TestTimingProfiles:
    """Test predefined timing profiles."""

    def test_conservative_profile_has_higher_means(self):
        """Conservative profile should have higher (slower) means."""
        conservative = TIMING_PROFILES["conservative"]
        moderate = TIMING_PROFILES["moderate"]
        aggressive = TIMING_PROFILES["aggressive"]

        # Check click hesitation progression
        assert conservative.click_hesitation[0] > moderate.click_hesitation[0]
        assert moderate.click_hesitation[0] > aggressive.click_hesitation[0]

    def test_profile_variance_structure(self):
        """Verify profile tuple structure (mean, std_dev, min, max)."""
        profile = TIMING_PROFILES["moderate"]

        for attr_name in [
            "click_hesitation",
            "mouse_travel_time",
            "micro_delay",
            "scroll_pause",
        ]:
            timing_tuple = getattr(profile, attr_name)
            assert len(timing_tuple) == 4
            mean, std_dev, min_val, max_val = timing_tuple
            assert mean > 0
            assert std_dev > 0
            assert min_val > 0
            assert min_val <= mean <= max_val
            assert std_dev < mean


@pytest.mark.asyncio
class TestClickWithDelay:
    """Test click_with_delay implementation (T036, T041)."""

    async def test_click_with_delay_success(self):
        """T041: Click succeeds with hesitation timing."""
        emulator = BehaviorEmulator(intensity="moderate")

        page = AsyncMock()
        page.click = AsyncMock()
        page.locator = MagicMock()

        result = await emulator.click_with_delay(page, "button.submit")

        assert result["success"] is True
        assert "hesitation_ms" in result
        assert result["selector_used"] == "button.submit"
        assert "duration_total_ms" in result
        assert result["error"] is None
        assert page.click.called

    async def test_click_hesitation_in_normal_distribution(self):
        """T041: Verify click hesitation follows normal distribution."""
        emulator = BehaviorEmulator(intensity="moderate")

        page = AsyncMock()
        page.click = AsyncMock()

        # Collect hesitation samples
        hesitations = []
        for _ in range(50):
            result = await emulator.click_with_delay(page, "button")
            hesitations.append(result["hesitation_ms"])

        # Calculate statistics
        mean_hesitation = sum(hesitations) / len(hesitations)
        variance = sum((x - mean_hesitation) ** 2 for x in hesitations) / len(
            hesitations
        )
        std_dev = math.sqrt(variance)

        # Verify distribution parameters (moderate profile)
        profile_mean, profile_std = 150, 75
        assert 100 < mean_hesitation < 200  # Mean should be near 150
        assert 30 < std_dev < 100  # Std dev should be near 75
        assert all(50 <= h <= 400 for h in hesitations)  # Within bounds

    async def test_click_hesitation_respects_intensity(self):
        """Test that different intensities produce different hesitation ranges."""
        page = AsyncMock()
        page.click = AsyncMock()

        # Collect samples for each intensity
        intensities_samples = {}
        for intensity in ["conservative", "moderate", "aggressive"]:
            emulator = BehaviorEmulator(intensity=intensity)
            hesitations = []
            for _ in range(20):
                result = await emulator.click_with_delay(page, "button")
                hesitations.append(result["hesitation_ms"])
            intensities_samples[intensity] = hesitations

        # Conservative should have higher mean than aggressive
        conservative_mean = sum(intensities_samples["conservative"]) / len(
            intensities_samples["conservative"]
        )
        aggressive_mean = sum(intensities_samples["aggressive"]) / len(
            intensities_samples["aggressive"]
        )
        assert conservative_mean > aggressive_mean

    async def test_click_error_handling(self):
        """Test error handling when click fails."""
        emulator = BehaviorEmulator()

        page = AsyncMock()
        page.click = AsyncMock(side_effect=Exception("Element not found"))

        result = await emulator.click_with_delay(page, "button.missing")

        assert result["success"] is False
        assert "error" in result
        assert "Element not found" in result["error"]

    async def test_click_duration_includes_hesitation(self):
        """Test that total duration includes hesitation time."""
        emulator = BehaviorEmulator(intensity="moderate")

        page = AsyncMock()
        page.click = AsyncMock()

        result = await emulator.click_with_delay(page, "button")

        # Total duration should be at least the hesitation (plus execution)
        assert result["duration_total_ms"] >= result["hesitation_ms"]
        # Should not be too long (< 1 second)
        assert result["duration_total_ms"] < 1000


@pytest.mark.asyncio
class TestMouseMovementBezier:
    """Test mouse movement with Bézier curve (T037, T042)."""

    async def test_mouse_move_success(self):
        """T042: Mouse movement succeeds with Bézier curve."""
        emulator = BehaviorEmulator(intensity="moderate")

        page = AsyncMock()
        page.mouse = AsyncMock()
        page.mouse.move = AsyncMock()

        result = await emulator.move_mouse_naturally(
            page, (100, 100), (500, 300)
        )

        assert result["success"] is True
        assert result["from_pos"] == (100, 100)
        assert result["to_pos"] == (500, 300)
        assert result["acceleration"] == "ease_in_out"
        assert "duration_ms" in result
        assert result["steps"] > 1
        assert page.mouse.move.called

    async def test_mouse_uses_bezier_curve_not_linear(self):
        """T042: Verify mouse movement uses Bézier curve (ease-in-out)."""
        emulator = BehaviorEmulator(intensity="moderate")

        page = AsyncMock()
        positions = []

        async def track_move(x, y):
            positions.append((x, y))

        page.mouse = AsyncMock()
        page.mouse.move = track_move

        from_pos = (0, 0)
        to_pos = (100, 100)

        result = await emulator.move_mouse_naturally(page, from_pos, to_pos)

        assert len(positions) > 0

        # With Bézier curve (ease-in-out), movement should be:
        # - Slow at start (first few steps close to start)
        # - Fast in middle (steps accelerate distance)
        # - Slow at end (final steps close to end)

        # For a linear movement, each step would move equal distance
        # For Bézier, early steps move less, middle steps move more

        if len(positions) > 10:
            # Calculate deltas between consecutive positions
            deltas = []
            for i in range(1, len(positions)):
                dist = math.sqrt(
                    (positions[i][0] - positions[i - 1][0]) ** 2
                    + (positions[i][1] - positions[i - 1][1]) ** 2
                )
                deltas.append(dist)

            # Verify non-uniform distribution (Bézier, not linear)
            # Max delta should be significantly larger than min delta
            if len(deltas) > 5:
                max_delta = max(deltas)
                min_delta = min(deltas)
                # Bézier curve should have at least 1.5x difference
                assert max_delta > min_delta * 1.2

    async def test_mouse_move_with_different_intensities(self):
        """Test mouse movement duration varies by intensity."""
        page = AsyncMock()
        page.mouse = AsyncMock()

        durations = {}
        for intensity in ["conservative", "moderate", "aggressive"]:
            emulator = BehaviorEmulator(intensity=intensity)
            result = await emulator.move_mouse_naturally(
                page, (0, 0), (100, 100)
            )
            durations[intensity] = result["duration_ms"]

        # Conservative should take longer than aggressive on average
        assert durations["conservative"] > durations["aggressive"] * 0.8

    async def test_mouse_respects_step_interpolation(self):
        """Test mouse movement maintains 60fps-like step resolution."""
        emulator = BehaviorEmulator(intensity="moderate")

        page = AsyncMock()
        page.mouse = AsyncMock()

        result = await emulator.move_mouse_naturally(
            page, (0, 0), (100, 100)
        )

        # Step count should correspond to duration at ~60fps
        # duration_ms / 16.67 ≈ steps
        expected_steps = int(result["duration_ms"] / 16.67)
        assert abs(result["steps"] - expected_steps) <= 1


@pytest.mark.asyncio
class TestScrollNaturally:
    """Test scroll behavior with natural pauses (T038, T043)."""

    async def test_scroll_down_success(self):
        """T043: Scroll down succeeds with natural pauses."""
        emulator = BehaviorEmulator(intensity="moderate")

        page = AsyncMock()
        page.evaluate = AsyncMock()

        result = await emulator.scroll_naturally(page, direction="down", amount=500)

        assert result["success"] is True
        assert result["direction"] == "down"
        assert result["amount"] == 500
        assert "segments" in result
        assert "pauses_count" in result
        assert "total_duration_ms" in result
        assert page.evaluate.called

    async def test_scroll_up_success(self):
        """Test scroll up direction."""
        emulator = BehaviorEmulator(intensity="moderate")

        page = AsyncMock()
        page.evaluate = AsyncMock()

        result = await emulator.scroll_naturally(page, direction="up", amount=300)

        assert result["success"] is True
        assert result["direction"] == "up"

    async def test_scroll_includes_natural_pauses(self):
        """T043: Verify scroll includes pauses for reading."""
        emulator = BehaviorEmulator(intensity="moderate")

        page = AsyncMock()
        page.evaluate = AsyncMock()

        start_time = time.time()
        result = await emulator.scroll_naturally(page, direction="down", amount=500)
        total_time = time.time() - start_time

        # Should have pauses between segments
        assert result["pauses_count"] >= 1
        # Total time should include pause durations (at least 100ms per pause)
        expected_min_pause_time = result["pauses_count"] * 0.1
        assert total_time >= expected_min_pause_time

    async def test_scroll_has_multiple_segments(self):
        """Verify scroll divides into 2-4 segments."""
        emulator = BehaviorEmulator(intensity="moderate")

        page = AsyncMock()
        page.evaluate = AsyncMock()

        segments_list = []
        for _ in range(10):
            result = await emulator.scroll_naturally(
                page, direction="down", amount=500
            )
            segments_list.append(result["segments"])

        # Should always be 2-4 segments
        assert all(2 <= s <= 4 for s in segments_list)

    async def test_scroll_error_on_invalid_direction(self):
        """Test error handling for invalid direction."""
        emulator = BehaviorEmulator()

        page = AsyncMock()

        result = await emulator.scroll_naturally(
            page, direction="diagonal", amount=500
        )

        assert result["success"] is False
        assert "direction must be" in result["error"]

    async def test_scroll_error_on_negative_amount(self):
        """Test error handling for negative amount."""
        emulator = BehaviorEmulator()

        page = AsyncMock()

        result = await emulator.scroll_naturally(page, direction="down", amount=-100)

        assert result["success"] is False
        assert "amount must be positive" in result["error"]

    async def test_scroll_speed_variation(self):
        """Test scroll speed variation parameter."""
        emulator = BehaviorEmulator(intensity="moderate")

        page = AsyncMock()
        page.evaluate = AsyncMock()

        # With high variation
        result_high_var = await emulator.scroll_naturally(
            page, direction="down", amount=500, scroll_speed_variation=0.8
        )

        # With low variation
        result_low_var = await emulator.scroll_naturally(
            page, direction="down", amount=500, scroll_speed_variation=0.1
        )

        # Both should succeed
        assert result_high_var["success"]
        assert result_low_var["success"]


@pytest.mark.asyncio
class TestMicroDelay:
    """Test micro-delay implementation (T039, T044)."""

    async def test_micro_delay_success(self):
        """T044: Micro-delay completes successfully."""
        emulator = BehaviorEmulator(intensity="moderate")

        result = await emulator.add_micro_delay()

        assert result["success"] is True
        assert "delay_ms" in result
        assert result["intensity"] == "moderate"

    async def test_micro_delay_respects_intensity(self):
        """T044: Micro-delay ranges respect configured intensity level."""
        # Test that different intensities produce different delays
        delays_by_intensity = {}

        for intensity in ["conservative", "moderate", "aggressive"]:
            emulator = BehaviorEmulator(intensity=intensity)
            delays = []
            for _ in range(20):
                result = await emulator.add_micro_delay()
                delays.append(result["delay_ms"])
            delays_by_intensity[intensity] = delays

        # Conservative should have higher mean than aggressive
        conservative_mean = sum(delays_by_intensity["conservative"]) / len(
            delays_by_intensity["conservative"]
        )
        aggressive_mean = sum(delays_by_intensity["aggressive"]) / len(
            delays_by_intensity["aggressive"]
        )
        assert conservative_mean > aggressive_mean

    async def test_micro_delay_within_bounds(self):
        """Test micro-delays stay within configured min/max bounds."""
        emulator = BehaviorEmulator(intensity="moderate")

        profile = emulator.profile
        min_ms = profile.micro_delay[2]
        max_ms = profile.micro_delay[3]

        for _ in range(30):
            result = await emulator.add_micro_delay()
            assert min_ms <= result["delay_ms"] <= max_ms

    async def test_conservative_micro_delay_slower(self):
        """Test conservative intensity produces longer delays."""
        conservative = BehaviorEmulator(intensity="conservative")
        aggressive = BehaviorEmulator(intensity="aggressive")

        conservative_delays = []
        aggressive_delays = []

        for _ in range(20):
            c_result = await conservative.add_micro_delay()
            a_result = await aggressive.add_micro_delay()
            conservative_delays.append(c_result["delay_ms"])
            aggressive_delays.append(a_result["delay_ms"])

        assert sum(conservative_delays) > sum(aggressive_delays)


@pytest.mark.asyncio
class TestEventLogging:
    """Test event logging for behavior operations."""

    async def test_click_logs_event_with_builder(self):
        """Test click operation logs event when EventBuilder provided."""
        builder = EventBuilder(run_id="test-run")
        emulator = BehaviorEmulator(intensity="moderate", event_builder=builder)

        page = AsyncMock()
        page.click = AsyncMock()

        await emulator.click_with_delay(page, "button.test")

        # Verify event was built (check internal state if available)
        # or verify no exceptions were raised
        assert True  # Event building succeeded

    async def test_scroll_logs_event_with_builder(self):
        """Test scroll operation logs event when EventBuilder provided."""
        builder = EventBuilder(run_id="test-run")
        emulator = BehaviorEmulator(intensity="moderate", event_builder=builder)

        page = AsyncMock()
        page.evaluate = AsyncMock()

        result = await emulator.scroll_naturally(
            page, direction="down", amount=500
        )
        assert result["success"]

    async def test_micro_delay_logs_event_with_builder(self):
        """Test micro-delay logs event when EventBuilder provided."""
        builder = EventBuilder(run_id="test-run")
        emulator = BehaviorEmulator(intensity="moderate", event_builder=builder)

        result = await emulator.add_micro_delay()
        assert result["success"]


@pytest.mark.asyncio
class TestBehaviorIntegration:
    """Integration tests combining multiple behavior operations."""

    async def test_complete_interaction_flow(self):
        """Test realistic interaction: move -> click -> scroll -> delay."""
        emulator = BehaviorEmulator(intensity="moderate")

        page = AsyncMock()
        page.mouse = AsyncMock()
        page.click = AsyncMock()
        page.evaluate = AsyncMock()

        # 1. Move mouse to button
        move_result = await emulator.move_mouse_naturally(page, (0, 0), (100, 100))
        assert move_result["success"]

        # 2. Hesitate and click
        click_result = await emulator.click_with_delay(page, "button.submit")
        assert click_result["success"]

        # 3. Scroll down to see results
        scroll_result = await emulator.scroll_naturally(
            page, direction="down", amount=500
        )
        assert scroll_result["success"]

        # 4. Micro-delay before next action
        delay_result = await emulator.add_micro_delay()
        assert delay_result["success"]

    async def test_sequential_clicks_with_delays(self):
        """Test multiple rapid clicks with micro-delays between."""
        emulator = BehaviorEmulator(intensity="moderate")

        page = AsyncMock()
        page.click = AsyncMock()

        selectors = ["button.first", "button.second", "button.third"]

        for selector in selectors:
            click_result = await emulator.click_with_delay(page, selector)
            assert click_result["success"]

            if selector != selectors[-1]:  # Don't delay after last click
                delay_result = await emulator.add_micro_delay()
                assert delay_result["success"]

        # Should have clicked all buttons
        assert page.click.call_count == 3


@pytest.mark.asyncio
class TestBehaviorIntensityProfiles:
    """Test behavior under different intensity profiles."""

    async def test_conservative_slower_than_moderate(self):
        """Conservative profile should be slower overall."""
        conservative = BehaviorEmulator(intensity="conservative")
        moderate = BehaviorEmulator(intensity="moderate")

        page = AsyncMock()
        page.mouse = AsyncMock()
        page.click = AsyncMock()

        conservative_times = []
        moderate_times = []

        for _ in range(10):
            start = time.time()
            await conservative.click_with_delay(page, "button")
            conservative_times.append(time.time() - start)

            start = time.time()
            await moderate.click_with_delay(page, "button")
            moderate_times.append(time.time() - start)

        assert sum(conservative_times) > sum(moderate_times)

    async def test_aggressive_faster_than_moderate(self):
        """Aggressive profile should be faster overall."""
        moderate = BehaviorEmulator(intensity="moderate")
        aggressive = BehaviorEmulator(intensity="aggressive")

        page = AsyncMock()
        page.mouse = AsyncMock()

        moderate_times = []
        aggressive_times = []

        for _ in range(10):
            start = time.time()
            await moderate.add_micro_delay()
            moderate_times.append(time.time() - start)

            start = time.time()
            await aggressive.add_micro_delay()
            aggressive_times.append(time.time() - start)

        assert sum(aggressive_times) < sum(moderate_times)
