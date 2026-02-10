"""Behavior Emulation Module - Simulate realistic human interaction patterns.

This module implements timing and movement patterns that mimic human behavior:
- Click hesitation: Normal distribution timing before clicking
- Mouse movement: Bézier curves with ease-in-out acceleration
- Scroll timing: Variable speed with natural reading pauses
- Micro-delays: Realistic delays between rapid actions

All timing is configurable per behavior_intensity profile:
- 'conservative': High variance, slower (100-500ms click hesitation)
- 'moderate': Default variance, balanced (50-400ms click hesitation)  
- 'aggressive': Low variance, faster (20-200ms click hesitation)

Example:
    >>> emulator = BehaviorEmulator(
    ...     intensity="moderate",
    ...     event_builder=event_builder,
    ... )
    >>> await emulator.click_with_delay(page, "button.accept")
    >>> await emulator.scroll_naturally(page, direction="down", amount=500)
    >>> await emulator.add_micro_delay()
"""

import asyncio
import math
import random
import time
from dataclasses import dataclass
from typing import Literal, Optional, Tuple

from .models import AntiDetectionEvent
from .events import EventBuilder


@dataclass
class BehaviorTimingProfile:
    """Timing profile for behavior emulation under specific intensity level."""

    intensity: Literal["conservative", "moderate", "aggressive"]
    # (mean_ms, std_dev_ms, min_ms, max_ms) tuples for normal distribution
    click_hesitation: Tuple[float, float, float, float]  # Pre-click delay
    mouse_travel_time: Tuple[float, float, float, float]  # Mouse movement duration
    micro_delay: Tuple[float, float, float, float]  # Rapid action delays
    scroll_pause: Tuple[float, float, float, float]  # Natural reading pauses


# Predefined timing profiles based on human behavior research
TIMING_PROFILES = {
    "conservative": BehaviorTimingProfile(
        intensity="conservative",
        click_hesitation=(250, 100, 100, 500),  # More cautious, variable
        mouse_travel_time=(300, 150, 100, 800),  # Slower cursor movement
        micro_delay=(50, 30, 10, 150),  # Longer inter-action delays
        scroll_pause=(500, 300, 200, 1500),  # Extended reading pauses
    ),
    "moderate": BehaviorTimingProfile(
        intensity="moderate",
        click_hesitation=(150, 75, 50, 400),  # Balanced hesitation
        mouse_travel_time=(200, 100, 50, 600),  # Typical cursor speed
        micro_delay=(30, 20, 5, 100),  # Normal rapid-action spacing
        scroll_pause=(300, 200, 100, 1000),  # Normal reading pauses
    ),
    "aggressive": BehaviorTimingProfile(
        intensity="aggressive",
        click_hesitation=(75, 40, 20, 200),  # Quick decision-making
        mouse_travel_time=(100, 50, 20, 300),  # Fast cursor movement
        micro_delay=(15, 10, 2, 50),  # Minimal action spacing
        scroll_pause=(100, 75, 30, 400),  # Brief scanning pauses
    ),
}


class BehaviorEmulator:
    """Emulates human interaction behavior patterns to avoid automation detection.

    Provides methods to simulate human-like:
    - Click hesitation with normal distribution timing
    - Mouse movement with Bézier curve acceleration
    - Scroll behavior with natural pauses
    - Micro-delays between rapid actions

    Attributes:
        intensity: Behavior intensity level (conservative/moderate/aggressive)
        profile: Resolved BehaviorTimingProfile for this emulator
        event_builder: EventBuilder for logging behavior events
    """

    def __init__(
        self,
        intensity: Literal["conservative", "moderate", "aggressive"] = "moderate",
        event_builder: Optional[EventBuilder] = None,
    ):
        """Initialize behavior emulator with timing profile.

        Args:
            intensity: Behavior intensity level controlling timing variance
            event_builder: Optional EventBuilder for logging behavior telemetry

        Raises:
            ValueError: If intensity is not one of allowed values
        """
        if intensity not in TIMING_PROFILES:
            raise ValueError(
                f"intensity must be one of {list(TIMING_PROFILES.keys())}, "
                f"got {intensity}"
            )

        self.intensity = intensity
        self.profile = TIMING_PROFILES[intensity]
        self.event_builder = event_builder

    async def click_with_delay(
        self,
        page,
        selector: str,
        verify_success: bool = True,
    ) -> dict:
        """Click with realistic pre-click hesitation timing.

        Simulates human delay before clicking by:
        1. Waiting a random duration from normal distribution
        2. Clicking the target element
        3. Optionally verifying element state changed

        Args:
            page: Playwright Page object
            selector: CSS selector of element to click
            verify_success: If True, verify element exists after click

        Returns:
            dict with keys:
                - success: bool indicating click succeeded
                - hesitation_ms: Actual delay before click
                - selector_used: The selector passed
                - duration_total_ms: Total time including click
                - error: Optional error message if failed

        Example:
            >>> result = await emulator.click_with_delay(page, "button.submit")
            >>> print(f"Clicked after {result['hesitation_ms']}ms")
        """
        start_time = time.time()
        hesitation_ms = self._sample_from_profile(self.profile.click_hesitation)

        try:
            # Wait with realistic human hesitation
            await asyncio.sleep(hesitation_ms / 1000.0)

            # Perform click
            await page.click(selector)

            # Verify element still exists (not removed by click)
            if verify_success:
                try:
                    await page.locator(selector).is_enabled(timeout=100)
                except Exception:
                    pass  # Element may have been removed, that's fine

            total_duration = (time.time() - start_time) * 1000

            result = {
                "success": True,
                "hesitation_ms": hesitation_ms,
                "selector_used": selector,
                "duration_total_ms": total_duration,
                "error": None,
            }

            # Log event
            if self.event_builder:
                self.event_builder.build(
                    event_type="behavior_click",
                    description=f"Clicked {selector} after {hesitation_ms:.0f}ms hesitation",
                    severity="INFO",
                    metadata=result,
                )

            return result

        except Exception as e:
            total_duration = (time.time() - start_time) * 1000

            result = {
                "success": False,
                "hesitation_ms": hesitation_ms,
                "selector_used": selector,
                "duration_total_ms": total_duration,
                "error": str(e),
            }

            if self.event_builder:
                self.event_builder.build(
                    event_type="behavior_click_error",
                    description=f"Click failed: {str(e)}",
                    severity="WARNING",
                    metadata=result,
                )

            return result

    async def move_mouse_naturally(
        self,
        page,
        from_pos: Tuple[float, float],
        to_pos: Tuple[float, float],
    ) -> dict:
        """Move mouse with Bézier curve (ease-in-out) acceleration.

        Simulates human mouse movement by:
        1. Sampling travel time from normal distribution
        2. Using ease-in-out (smoothstep) Bézier curve for acceleration
        3. Moving mouse through interpolated positions at 60fps

        The ease-in-out curve creates natural acceleration:
        - Slow start (human aim refinement phase)
        - Fast middle (committed movement)
        - Slow end (approach and click preparation)

        Args:
            page: Playwright Page object
            from_pos: Starting position tuple (x, y)
            to_pos: Ending position tuple (x, y)

        Returns:
            dict with keys:
                - success: bool
                - from_pos: Starting position
                - to_pos: Ending position
                - duration_ms: Actual movement duration
                - steps: Number of interpolation steps
                - acceleration: Bézier curve used (always "ease_in_out")

        Example:
            >>> result = await emulator.move_mouse_naturally(
            ...     page, (100, 100), (500, 300)
            ... )
            >>> print(f"Moved mouse in {result['duration_ms']}ms")
        """
        start_time = time.time()
        duration_ms = self._sample_from_profile(self.profile.mouse_travel_time)

        try:
            # Calculate steps at 60fps resolution
            steps = max(2, int(duration_ms / 16.67))
            step_duration = duration_ms / (steps - 1) if steps > 1 else 0

            for i in range(steps):
                # Normalize time: t goes from 0 to 1
                t = i / (steps - 1) if steps > 1 else 1.0

                # Ease-in-out (smoothstep): slow start, fast middle, slow end
                # Formula: 3*t^2 - 2*t^3
                ease_t = 3 * (t**2) - 2 * (t**3)

                # Interpolate position
                current_pos = (
                    from_pos[0] + (to_pos[0] - from_pos[0]) * ease_t,
                    from_pos[1] + (to_pos[1] - from_pos[1]) * ease_t,
                )

                # Move mouse
                await page.mouse.move(current_pos[0], current_pos[1])

                # Wait for next step
                if i < steps - 1:
                    await asyncio.sleep(step_duration / 1000.0)

            total_duration = (time.time() - start_time) * 1000

            result = {
                "success": True,
                "from_pos": from_pos,
                "to_pos": to_pos,
                "duration_ms": total_duration,
                "steps": steps,
                "acceleration": "ease_in_out",
            }

            if self.event_builder:
                self.event_builder.build(
                    event_type="behavior_mouse_move",
                    description=f"Mouse moved from {from_pos} to {to_pos} in {total_duration:.0f}ms",
                    severity="INFO",
                    metadata=result,
                )

            return result

        except Exception as e:
            total_duration = (time.time() - start_time) * 1000

            result = {
                "success": False,
                "from_pos": from_pos,
                "to_pos": to_pos,
                "duration_ms": total_duration,
                "steps": 0,
                "acceleration": "ease_in_out",
                "error": str(e),
            }

            if self.event_builder:
                self.event_builder.build(
                    event_type="behavior_mouse_error",
                    description=f"Mouse move failed: {str(e)}",
                    severity="WARNING",
                    metadata=result,
                )

            return result

    async def scroll_naturally(
        self,
        page,
        direction: Literal["up", "down"],
        amount: float = 500,
        scroll_speed_variation: float = 0.3,
    ) -> dict:
        """Scroll with variable speed and natural reading pauses.

        Simulates human scroll behavior by:
        1. Dividing scroll into segments (pause points for reading)
        2. Varying scroll speed per segment
        3. Adding pauses at segment boundaries

        Args:
            page: Playwright Page object
            direction: Scroll direction ("up" or "down")
            amount: Pixels to scroll
            scroll_speed_variation: Variance in scroll speed (0.0-1.0)

        Returns:
            dict with keys:
                - success: bool
                - direction: Direction scrolled
                - amount: Total pixels scrolled
                - segments: Number of scroll segments
                - pauses_count: Number of pauses taken
                - total_duration_ms: Total time for operation

        Example:
            >>> result = await emulator.scroll_naturally(
            ...     page, direction="down", amount=500
            ... )
            >>> print(f"Scrolled {result['amount']}px in {result['total_duration_ms']}ms")
        """
        start_time = time.time()

        if direction not in ("up", "down"):
            return {
                "success": False,
                "direction": direction,
                "error": f"direction must be 'up' or 'down', got {direction}",
            }

        if amount <= 0:
            return {
                "success": False,
                "direction": direction,
                "error": f"amount must be positive, got {amount}",
            }

        try:
            # Divide scroll into 2-4 segments with pauses between
            num_segments = random.randint(2, 4)
            segment_size = amount / num_segments

            pauses_taken = 0
            total_scrolled = 0

            for segment_idx in range(num_segments):
                # Vary scroll speed for this segment (±variation)
                speed_factor = 1.0 + (random.random() - 0.5) * scroll_speed_variation
                segment_scroll = segment_size * speed_factor

                # Scroll segment
                direction_delta = segment_scroll if direction == "down" else -segment_scroll
                await page.evaluate(f"window.scrollBy(0, {direction_delta})")
                total_scrolled += abs(direction_delta)

                # Pause between segments (simulate reading/scanning)
                if segment_idx < num_segments - 1:
                    pause_ms = self._sample_from_profile(self.profile.scroll_pause)
                    await asyncio.sleep(pause_ms / 1000.0)
                    pauses_taken += 1

            total_duration = (time.time() - start_time) * 1000

            result = {
                "success": True,
                "direction": direction,
                "amount": amount,
                "segments": num_segments,
                "pauses_count": pauses_taken,
                "total_scrolled": total_scrolled,
                "total_duration_ms": total_duration,
            }

            if self.event_builder:
                self.event_builder.build(
                    event_type="behavior_scroll",
                    description=f"Scrolled {direction} {amount}px in {total_duration:.0f}ms "
                    f"({num_segments} segments, {pauses_taken} pauses)",
                    severity="INFO",
                    metadata=result,
                )

            return result

        except Exception as e:
            total_duration = (time.time() - start_time) * 1000

            result = {
                "success": False,
                "direction": direction,
                "amount": amount,
                "total_duration_ms": total_duration,
                "error": str(e),
            }

            if self.event_builder:
                self.event_builder.build(
                    event_type="behavior_scroll_error",
                    description=f"Scroll failed: {str(e)}",
                    severity="WARNING",
                    metadata=result,
                )

            return result

    async def add_micro_delay(self) -> dict:
        """Add realistic micro-delay between rapid actions.

        Simulates human cognitive processing delay between:
        - Rapid form fills
        - Dialog handling
        - Sequential element interactions

        Returns:
            dict with keys:
                - success: bool (always True)
                - delay_ms: Actual delay applied
                - intensity: The intensity level used

        Example:
            >>> await emulator.add_micro_delay()  # Brief pause for human response time
        """
        try:
            delay_ms = self._sample_from_profile(self.profile.micro_delay)
            await asyncio.sleep(delay_ms / 1000.0)

            result = {
                "success": True,
                "delay_ms": delay_ms,
                "intensity": self.intensity,
            }

            if self.event_builder:
                self.event_builder.build(
                    event_type="behavior_micro_delay",
                    description=f"Added {delay_ms:.0f}ms micro-delay",
                    severity="DEBUG",
                    metadata=result,
                )

            return result

        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
            }

            if self.event_builder:
                self.event_builder.build(
                    event_type="behavior_micro_delay_error",
                    description=f"Micro-delay failed: {str(e)}",
                    severity="WARNING",
                    metadata=result,
                )

            return result

    def get_profile(self) -> BehaviorTimingProfile:
        """Get the timing profile in use.

        Returns:
            BehaviorTimingProfile with timing ranges for this emulator
        """
        return self.profile

    def _sample_from_profile(
        self, timing_tuple: Tuple[float, float, float, float]
    ) -> float:
        """Sample a value from normal distribution with bounds.

        Args:
            timing_tuple: (mean, std_dev, min, max) for normal distribution

        Returns:
            Sampled value clamped to [min, max] range
        """
        mean_ms, std_dev_ms, min_ms, max_ms = timing_tuple

        # Sample from normal distribution
        value = random.gauss(mean_ms, std_dev_ms)

        # Clamp to allowed range
        return max(min_ms, min(max_ms, value))
