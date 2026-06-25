"""
Stealth handler component template for the modular site scraper template.

This module provides stealth functionality to avoid detection by anti-bot
systems through human behavior emulation and browser fingerprint randomization.
"""

from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import asyncio
import random
import json
import secrets
from urllib.parse import urlparse

from src.sites.base.component_interface import BaseComponent, ComponentContext, ComponentResult


class StealthHandlerComponent(BaseComponent):
    """Stealth handler component for anti-bot detection avoidance."""
    
    def __init__(
        self,
        component_id: str = "stealth_handler",
        name: str = "Stealth Handler Component",
        version: str = "1.0.0",
        description: str = "Handles stealth functionality to avoid anti-bot detection"
    ):
        """
        Initialize stealth handler component.
        
        Args:
            component_id: Unique identifier for the component
            name: Human-readable name for the component
            version: Component version
            description: Component description
        """
        super().__init__(
            component_id=component_id,
            name=name,
            version=version,
            description=description,
            component_type="STEALTH"
        )
        
        # Stealth configuration
        self._enable_stealth: bool = True
        self._randomize_user_agent: bool = True
        self._randomize_viewport: bool = True
        self._randomize_timezone: bool = True
        self._randomize_language: bool = True
        self._randomize_platform: bool = True
        self._enable_mouse_movement: bool = True
        self._enable_keyboard_typing: bool = True
        self._enable_scroll_simulation: bool = True
        self._enable_timing_randomization: bool = True
        
        # User agent pools
        self._user_agents: List[str] = []
        self._current_user_agent: Optional[str] = None
        
        # Viewport configurations
        self._viewport_sizes: List[Dict[str, int]] = [
            {'width': 1920, 'height': 1080},
            {'width': 1366, 'height': 768},
            {'width': 1440, 'height': 900},
            {'width': 1536, 'height': 864},
            {'width': 1280, 'height': 720}
        ]
        self._current_viewport: Optional[Dict[str, int]] = None
        
        # Timezone configurations
        self._timezones: List[str] = [
            'America/New_York',
            'America/Los_Angeles',
            'America/Chicago',
            'Europe/London',
            'Europe/Paris',
            'Europe/Berlin',
            'Asia/Tokyo',
            'Asia/Shanghai',
            'Australia/Sydney'
        ]
        self._current_timezone: Optional[str] = None
        
        # Language configurations
        self._languages: List[str] = [
            'en-US,en;q=0.9',
            'en-GB,en;q=0.9',
            'en;q=0.8',
            'es-ES,es;q=0.9',
            'fr-FR,fr;q=0.9',
            'de-DE,de;q=0.9',
            'it-IT,it;q=0.9',
            'pt-BR,pt;q=0.9',
            'ja-JP,ja;q=0.9',
            'zh-CN,zh;q=0.9'
        ]
        self._current_language: Optional[str] = None
        
        # Platform configurations
        self._platforms: List[str] = [
            'Win32',
            'MacIntel',
            'Linux x86_64',
            'X11'
        ]
        self._current_platform: Optional[str] = None
        
        # Timing configurations
        self._min_delay_ms: int = 100
        self._max_delay_ms: int = 3000
        self._typing_delay_ms: int = 50
        self._typing_variance_ms: int = 30
        
        # Mouse movement configurations
        self._mouse_speed_range: tuple = (100, 500)  # pixels per second
        self._mouse_pause_range: tuple = (100, 500)  # milliseconds
        
        # Callbacks
        self._stealth_applied_callback: Optional[Callable] = None
        
        # Statistics
        self._statistics = {
            'stealth_applications': 0,
            'user_agent_changes': 0,
            'viewport_changes': 0,
            'mouse_movements': 0,
            'keyboard_typing': 0,
            'scroll_simulations': 0
        }
    
    async def initialize(self, context: ComponentContext) -> bool:
        """
        Initialize stealth handler component.
        
        Args:
            context: Component context
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Load stealth configuration from context
            config = context.config_manager.get_config(context.environment) if context.config_manager else {}
            
            self._enable_stealth = config.get('enable_stealth', True)
            self._randomize_user_agent = config.get('randomize_user_agent', True)
            self._randomize_viewport = config.get('randomize_viewport', True)
            self._randomize_timezone = config.get('randomize_timezone', True)
            self._randomize_language = config.get('randomize_language', True)
            self._randomize_platform = config.get('randomize_platform', True)
            self._enable_mouse_movement = config.get('enable_mouse_movement', True)
            self._enable_keyboard_typing = config.get('enable_keyboard_typing', True)
            self._enable_scroll_simulation = config.get('enable_scroll_simulation', True)
            self._enable_timing_randomization = config.get('enable_timing_randomization', True)
            
            # Load user agents
            self._user_agents = config.get('user_agents', self._get_default_user_agents())
            
            # Load timing configurations
            self._min_delay_ms = config.get('min_delay_ms', 100)
            self._max_delay_ms = config.get('max_delay_ms', 3000)
            self._typing_delay_ms = config.get('typing_delay_ms', 50)
            self._typing_variance_ms = config.get('typing_variance_ms', 30)
            
            # Initialize random values
            if self._enable_stealth:
                await self._randomize_fingerprint()
            
            self._log_operation("initialize", f"Stealth handler initialized (enabled: {self._enable_stealth})")
            return True
            
        except Exception as e:
            self._log_operation("initialize", f"Stealth handler initialization failed: {str(e)}", "error")
            return False
    
    async def execute(self, **kwargs) -> ComponentResult:
        """
        Apply stealth settings to the browser page.
        
        Args:
            **kwargs: Stealth parameters including 'page', 'apply_all', etc.
            
        Returns:
            Stealth application result
        """
        try:
            start_time = datetime.utcnow()
            
            if not self._enable_stealth:
                return ComponentResult(
                    success=True,
                    data={'stealth_enabled': False, 'message': 'Stealth is disabled'},
                    execution_time_ms=0
                )
            
            page = kwargs.get('page')
            if not page:
                return ComponentResult(
                    success=False,
                    data={'error': 'Page object is required'},
                    errors=['Page object is required']
                )
            
            apply_all = kwargs.get('apply_all', True)
            stealth_settings = kwargs.get('stealth_settings', {})
            
            # Apply stealth settings
            applied_settings = {}
            
            if apply_all or 'user_agent' in stealth_settings:
                await self._apply_user_agent(page)
                applied_settings['user_agent'] = self._current_user_agent
            
            if apply_all or 'viewport' in stealth_settings:
                await self._apply_viewport(page)
                applied_settings['viewport'] = self._current_viewport
            
            if apply_all or 'timezone' in stealth_settings:
                await self._apply_timezone(page)
                applied_settings['timezone'] = self._current_timezone
            
            if apply_all or 'language' in stealth_settings:
                await self._apply_language(page)
                applied_settings['language'] = self._current_language
            
            if apply_all or 'platform' in stealth_settings:
                await self._apply_platform(page)
                applied_settings['platform'] = self._current_platform
            
            # Apply additional stealth measures
            if apply_all or 'extra_headers' in stealth_settings:
                await self._apply_extra_headers(page)
                applied_settings['extra_headers'] = True
            
            if apply_all or 'permissions' in stealth_settings:
                await self._apply_permissions(page)
                applied_settings['permissions'] = True
            
            # Update statistics
            self._statistics['stealth_applications'] += 1
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            # Call stealth applied callback
            if self._stealth_applied_callback:
                await self._stealth_applied_callback(applied_settings)
            
            return ComponentResult(
                success=True,
                data={
                    'stealth_enabled': True,
                    'applied_settings': applied_settings,
                    'statistics': self._statistics.copy(),
                    'execution_time_ms': execution_time
                },
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            self._log_operation("execute", f"Stealth application failed: {str(e)}", "error")
            return ComponentResult(
                success=False,
                data={'error': str(e)},
                errors=[str(e)]
            )
    
    async def _randomize_fingerprint(self) -> None:
        """Randomize browser fingerprint."""
        try:
            if self._randomize_user_agent:
                self._current_user_agent = random.choice(self._user_agents)
                self._statistics['user_agent_changes'] += 1
            
            if self._randomize_viewport:
                self._current_viewport = random.choice(self._viewport_sizes)
                self._statistics['viewport_changes'] += 1
            
            if self._randomize_timezone:
                self._current_timezone = random.choice(self._timezones)
            
            if self._randomize_language:
                self._current_language = random.choice(self._languages)
            
            if self._randomize_platform:
                self._current_platform = random.choice(self._platforms)
            
        except Exception as e:
            self._log_operation("_randomize_fingerprint", f"Fingerprint randomization failed: {str(e)}", "error")
    
    async def _apply_user_agent(self, page) -> None:
        """Apply random user agent to the page."""
        try:
            if not self._current_user_agent:
                self._current_user_agent = random.choice(self._user_agents)
            
            await page.set_extra_http_headers({
                'User-Agent': self._current_user_agent
            })
            
            self._log_operation("_apply_user_agent", f"User agent set: {self._current_user_agent[:50]}...")
            
        except Exception as e:
            self._log_operation("_apply_user_agent", f"Failed to set user agent: {str(e)}", "error")
    
    async def _apply_viewport(self, page) -> None:
        """Apply random viewport to the page."""
        try:
            if not self._current_viewport:
                self._current_viewport = random.choice(self._viewport_sizes)
            
            await page.set_viewport_size(
                width=self._current_viewport['width'],
                height=self._current_viewport['height']
            )
            
            self._log_operation("_apply_viewport", f"Viewport set: {self._current_viewport['width']}x{self._current_viewport['height']}")
            
        except Exception as e:
            self._log_operation("_apply_viewport", f"Failed to set viewport: {str(e)}", "error")
    
    async def _apply_timezone(self, page) -> None:
        """Apply random timezone to the page."""
        try:
            if not self._current_timezone:
                self._current_timezone = random.choice(self._timezones)
            
            # Set timezone via JavaScript
            await page.evaluate(f"""
                Object.defineProperty(Intl.DateTimeFormat.prototype, 'resolvedOptions', {{
                    get: function() {{
                        return {{
                            timeZone: '{self._current_timezone}'
                        }};
                    }}
                }});
                
                // Override Date constructor to use the timezone
                const originalDate = window.Date;
                window.Date = function(...args) {{
                    if (args.length === 0) {{
                        return new originalDate();
                    }}
                    const date = new originalDate(...args);
                    return new Date(date.toLocaleString('en-US', {{ timeZone: '{self._current_timezone}' }}));
                }};
                
                // Copy static methods
                Object.setPrototypeOf(window.Date, originalDate);
                Object.setPrototypeOf(window.Date.prototype, originalDate.prototype);
            """)
            
            self._log_operation("_apply_timezone", f"Timezone set: {self._current_timezone}")
            
        except Exception as e:
            self._log_operation("_apply_timezone", f"Failed to set timezone: {str(e)}", "error")
    
    async def _apply_language(self, page) -> None:
        """Apply random language to the page."""
        try:
            if not self._current_language:
                self._current_language = random.choice(self._languages)
            
            await page.set_extra_http_headers({
                'Accept-Language': self._current_language
            })
            
            self._log_operation("_apply_language", f"Language set: {self._current_language}")
            
        except Exception as e:
            self._log_operation("_apply_language", f"Failed to set language: {str(e)}", "error")
    
    async def _apply_platform(self, page) -> None:
        """Apply random platform to the page."""
        try:
            if not self._current_platform:
                self._current_platform = random.choice(self._platforms)
            
            # Set platform via JavaScript
            await page.evaluate(f"""
                Object.defineProperty(navigator, 'platform', {{
                    get: function() {{
                        return '{self._current_platform}';
                    }}
                }});
                
                Object.defineProperty(navigator, 'userAgentData', {{
                    get: function() {{
                        return {{
                            platform: '{self._current_platform}'
                        }};
                    }}
                }});
            """)
            
            self._log_operation("_apply_platform", f"Platform set: {self._current_platform}")
            
        except Exception as e:
            self._log_operation("_apply_platform", f"Failed to set platform: {str(e)}", "error")
    
    async def _apply_extra_headers(self, page) -> None:
        """Apply extra stealth headers."""
        try:
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': self._current_language or 'en-US,en;q=0.9',
                'Cache-Control': 'max-age=0',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'DNT': '1',
                'Connection': 'keep-alive'
            }
            
            await page.set_extra_http_headers(headers)
            
            self._log_operation("_apply_extra_headers", "Extra headers applied")
            
        except Exception as e:
            self._log_operation("_apply_extra_headers", f"Failed to apply extra headers: {str(e)}", "error")
    
    async def _apply_permissions(self, page) -> None:
        """Apply browser permissions for stealth."""
        try:
            # Grant common permissions
            permissions = [
                'geolocation',
                'notifications',
                'camera',
                'microphone'
            ]
            
            # This would typically be handled in browser context creation
            # For demonstration, we'll just log it
            self._log_operation("_apply_permissions", f"Permissions considered: {permissions}")
            
        except Exception as e:
            self._log_operation("_apply_permissions", f"Failed to apply permissions: {str(e)}", "error")
    
    async def simulate_mouse_movement(self, page, target_element=None) -> None:
        """Simulate human-like mouse movement."""
        try:
            if not self._enable_mouse_movement or not page:
                return
            
            # Get page dimensions
            viewport = page.viewport_size
            
            if target_element:
                # Move to element
                box = await target_element.bounding_box()
                target_x = box['x'] + box['width'] / 2
                target_y = box['y'] + box['height'] / 2
            else:
                # Random movement
                target_x = random.randint(0, viewport['width'])
                target_y = random.randint(0, viewport['height'])
            
            # Get current mouse position
            current_pos = await page.mouse.position()
            
            # Calculate path with intermediate points
            steps = random.randint(5, 15)
            for i in range(steps):
                progress = (i + 1) / steps
                
                # Add some randomness to the path
                x = current_pos['x'] + (target_x - current_pos['x']) * progress + random.randint(-20, 20)
                y = current_pos['y'] + (target_y - current_pos['y']) * progress + random.randint(-20, 20)
                
                await page.mouse.move(x, y)
                
                # Random pause
                pause = random.randint(*self._mouse_pause_range)
                await asyncio.sleep(pause / 1000.0)
            
            self._statistics['mouse_movements'] += 1
            self._log_operation("simulate_mouse_movement", f"Mouse moved to ({int(target_x)}, {int(target_y)})")
            
        except Exception as e:
            self._log_operation("simulate_mouse_movement", f"Mouse movement simulation failed: {str(e)}", "error")
    
    async def simulate_keyboard_typing(self, page, text, selector=None) -> None:
        """Simulate human-like keyboard typing."""
        try:
            if not self._enable_keyboard_typing or not page:
                return
            
            # Find element if selector provided
            if selector:
                element = await page.query_selector(selector)
                if element:
                    await element.click()
                    await asyncio.sleep(random.randint(100, 300) / 1000.0)
            
            # Type text with random delays
            for char in text:
                await page.keyboard.type(char)
                
                # Random delay between characters
                delay = self._typing_delay_ms + random.randint(-self._typing_variance_ms, self._typing_variance_ms)
                await asyncio.sleep(max(0, delay) / 1000.0)
            
            self._statistics['keyboard_typing'] += 1
            self._log_operation("simulate_keyboard_typing", f"Typed text: {text[:20]}...")
            
        except Exception as e:
            self._log_operation("simulate_keyboard_typing", f"Keyboard typing simulation failed: {str(e)}", "error")
    
    async def simulate_scroll(self, page, direction='down', distance=None) -> None:
        """Simulate human-like scrolling."""
        try:
            if not self._enable_scroll_simulation or not page:
                return
            
            if distance is None:
                distance = random.randint(200, 800)
            
            # Scroll in steps
            steps = random.randint(3, 8)
            step_distance = distance / steps
            
            for i in range(steps):
                if direction == 'down':
                    await page.mouse.wheel(0, step_distance)
                elif direction == 'up':
                    await page.mouse.wheel(0, -step_distance)
                
                # Random pause between scrolls
                pause = random.randint(100, 500)
                await asyncio.sleep(pause / 1000.0)
            
            self._statistics['scroll_simulations'] += 1
            self._log_operation("simulate_scroll", f"Scrolled {direction} {distance}px")
            
        except Exception as e:
            self._log_operation("simulate_scroll", f"Scroll simulation failed: {str(e)}", "error")
    
    async def random_delay(self, min_ms: int = None, max_ms: int = None) -> None:
        """Apply random delay."""
        try:
            if not self._enable_timing_randomization:
                return
            
            min_delay = min_ms or self._min_delay_ms
            max_delay = max_ms or self._max_delay_ms
            
            delay = random.randint(min_delay, max_delay)
            await asyncio.sleep(delay / 1000.0)
            
        except Exception as e:
            self._log_operation("random_delay", f"Random delay failed: {str(e)}", "error")
    
    def _get_default_user_agents(self) -> List[str]:
        """Get default user agent strings."""
        return [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]
    
    def set_stealth_callbacks(self, applied_callback: Callable = None) -> None:
        """
        Set stealth callback functions.
        
        Args:
            applied_callback: Function to call when stealth is applied
        """
        self._stealth_applied_callback = applied_callback
    
    def get_current_fingerprint(self) -> Dict[str, Any]:
        """Get current browser fingerprint."""
        return {
            'user_agent': self._current_user_agent,
            'viewport': self._current_viewport,
            'timezone': self._current_timezone,
            'language': self._current_language,
            'platform': self._current_platform
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get stealth handler statistics."""
        return self._statistics.copy()
    
    def reset_statistics(self) -> None:
        """Reset stealth handler statistics."""
        self._statistics = {
            'stealth_applications': 0,
            'user_agent_changes': 0,
            'viewport_changes': 0,
            'mouse_movements': 0,
            'keyboard_typing': 0,
            'scroll_simulations': 0
        }
    
    def configure_stealth(
        self,
        enable_stealth: bool = None,
        randomize_user_agent: bool = None,
        randomize_viewport: bool = None,
        randomize_timezone: bool = None,
        randomize_language: bool = None,
        randomize_platform: bool = None,
        enable_mouse_movement: bool = None,
        enable_keyboard_typing: bool = None,
        enable_scroll_simulation: bool = None,
        enable_timing_randomization: bool = None,
        min_delay_ms: int = None,
        max_delay_ms: int = None,
        typing_delay_ms: int = None,
        typing_variance_ms: int = None
    ) -> None:
        """
        Configure stealth settings.
        
        Args:
            enable_stealth: Enable stealth functionality
            randomize_user_agent: Randomize user agent
            randomize_viewport: Randomize viewport size
            randomize_timezone: Randomize timezone
            randomize_language: Randomize language
            randomize_platform: Randomize platform
            enable_mouse_movement: Enable mouse movement simulation
            enable_keyboard_typing: Enable keyboard typing simulation
            enable_scroll_simulation: Enable scroll simulation
            enable_timing_randomization: Enable timing randomization
            min_delay_ms: Minimum delay in milliseconds
            max_delay_ms: Maximum delay in milliseconds
            typing_delay_ms: Base typing delay in milliseconds
            typing_variance_ms: Typing variance in milliseconds
        """
        if enable_stealth is not None:
            self._enable_stealth = enable_stealth
        if randomize_user_agent is not None:
            self._randomize_user_agent = randomize_user_agent
        if randomize_viewport is not None:
            self._randomize_viewport = randomize_viewport
        if randomize_timezone is not None:
            self._randomize_timezone = randomize_timezone
        if randomize_language is not None:
            self._randomize_language = randomize_language
        if randomize_platform is not None:
            self._randomize_platform = randomize_platform
        if enable_mouse_movement is not None:
            self._enable_mouse_movement = enable_mouse_movement
        if enable_keyboard_typing is not None:
            self._enable_keyboard_typing = enable_keyboard_typing
        if enable_scroll_simulation is not None:
            self._enable_scroll_simulation = enable_scroll_simulation
        if enable_timing_randomization is not None:
            self._enable_timing_randomization = enable_timing_randomization
        if min_delay_ms is not None:
            self._min_delay_ms = min_delay_ms
        if max_delay_ms is not None:
            self._max_delay_ms = max_delay_ms
        if typing_delay_ms is not None:
            self._typing_delay_ms = typing_delay_ms
        if typing_variance_ms is not None:
            self._typing_variance_ms = typing_variance_ms
    
    def get_stealth_configuration(self) -> Dict[str, Any]:
        """Get current stealth configuration."""
        return {
            'enable_stealth': self._enable_stealth,
            'randomize_user_agent': self._randomize_user_agent,
            'randomize_viewport': self._randomize_viewport,
            'randomize_timezone': self._randomize_timezone,
            'randomize_language': self._randomize_language,
            'randomize_platform': self._randomize_platform,
            'enable_mouse_movement': self._enable_mouse_movement,
            'enable_keyboard_typing': self._enable_keyboard_typing,
            'enable_scroll_simulation': self._enable_scroll_simulation,
            'enable_timing_randomization': self._enable_timing_randomization,
            'min_delay_ms': self._min_delay_ms,
            'max_delay_ms': self._max_delay_ms,
            'typing_delay_ms': self._typing_delay_ms,
            'typing_variance_ms': self._typing_variance_ms,
            'current_fingerprint': self.get_current_fingerprint(),
            'statistics': self._statistics,
            **self.get_configuration()
        }
    
    async def cleanup(self) -> None:
        """Clean up stealth handler component."""
        try:
            # Clear fingerprint data
            self._current_user_agent = None
            self._current_viewport = None
            self._current_timezone = None
            self._current_language = None
            self._current_platform = None
            
            # Reset statistics
            self.reset_statistics()
            
            self._log_operation("cleanup", "Stealth handler component cleaned up")
            
        except Exception as e:
            self._log_operation("cleanup", f"Stealth handler cleanup failed: {str(e)}", "error")
