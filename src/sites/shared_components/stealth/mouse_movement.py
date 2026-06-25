"""
Shared mouse movement simulation component for reusable stealth functionality across sites.

This module provides mouse movement simulation functionality that can be easily
integrated into any site scraper for avoiding detection through human-like mouse behavior.
"""

from typing import Dict, Any, Optional, List, Callable, Union, Tuple
from datetime import datetime, timedelta
import asyncio
import json
import random
import math
from urllib.parse import urlparse

from src.sites.base.component_interface import BaseComponent, ComponentContext, ComponentResult


class MouseMovementComponent(BaseComponent):
    """Shared mouse movement simulation component for cross-site usage."""
    
    def __init__(
        self,
        component_id: str = "shared_mouse_movement",
        name: str = "Shared Mouse Movement Component",
        version: str = "1.0.0",
        description: str = "Reusable mouse movement simulation for multiple sites"
    ):
        """
        Initialize shared mouse movement component.
        
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
        
        # Mouse movement configurations for different sites
        self._site_configs: Dict[str, Dict[str, Any]] = {}
        
        # Movement state and statistics
        self._movement_state: Dict[str, Dict[str, Any]] = {}
        self._movement_stats: Dict[str, Dict[str, Any]] = {}
        
        # Callback handlers
        self._movement_callbacks: Dict[str, List[Callable]] = {}
        
        # Component metadata
        self._supported_sites = [
            'google', 'facebook', 'twitter', 'instagram', 'linkedin',
            'amazon', 'ebay', 'reddit', 'youtube', 'tiktok'
        ]
        
        # Movement patterns
        self._movement_patterns = {
            'linear': self._linear_movement,
            'bezier': self._bezier_movement,
            'random': self._random_movement,
            'human': self._human_movement,
            'circular': self._circular_movement,
            'spiral': self._spiral_movement
        }
    
    async def initialize(self, context: ComponentContext) -> bool:
        """
        Initialize shared mouse movement component.
        
        Args:
            context: Component context
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Load mouse movement configurations from context
            config = context.config_manager.get_config(context.environment) if context.config_manager else {}
            
            # Initialize default site configurations
            await self._initialize_default_configs()
            
            # Load custom site configurations
            custom_configs = config.get('mouse_movement_site_configs', {})
            for site, site_config in custom_configs.items():
                self.register_site(site, site_config)
            
            self._log_operation("initialize", f"Shared mouse movement component initialized with {len(self._site_configs)} site configurations")
            return True
            
        except Exception as e:
            self._log_operation("initialize", f"Shared mouse movement initialization failed: {str(e)}", "error")
            return False
    
    async def execute(self, **kwargs) -> ComponentResult:
        """
        Execute mouse movement simulation for a specific site.
        
        Args:
            **kwargs: Movement parameters including 'site', 'page', 'target_element', etc.
            
        Returns:
            Mouse movement result
        """
        try:
            start_time = datetime.utcnow()
            
            # Extract parameters
            site = kwargs.get('site')
            page = kwargs.get('page')
            target_element = kwargs.get('target_element')
            target_coordinates = kwargs.get('target_coordinates')
            movement_pattern = kwargs.get('movement_pattern', 'human')
            duration_ms = kwargs.get('duration_ms', 1000)
            intermediate_points = kwargs.get('intermediate_points', 5)
            
            if not site:
                return ComponentResult(
                    success=False,
                    data={'error': 'Site parameter is required'},
                    errors=['Site parameter is required']
                )
            
            if not page:
                return ComponentResult(
                    success=False,
                    data={'error': 'Page parameter is required'},
                    errors=['Page parameter is required']
                )
            
            if not target_element and not target_coordinates:
                return ComponentResult(
                    success=False,
                    data={'error': 'Either target_element or target_coordinates is required'},
                    errors=['Either target_element or target_coordinates is required']
                )
            
            # Initialize movement state
            self._initialize_movement_state(site)
            
            # Perform mouse movement
            movement_result = await self._simulate_mouse_movement(
                site, page, target_element, target_coordinates, 
                movement_pattern, duration_ms, intermediate_points
            )
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            # Update statistics
            self._update_movement_stats(site, movement_result, execution_time)
            
            # Call movement callbacks
            await self._call_movement_callbacks(site, movement_result)
            
            return ComponentResult(
                success=movement_result['success'],
                data={
                    'site': site,
                    'movement_timestamp': start_time.isoformat(),
                    **movement_result
                },
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            self._log_operation("execute", f"Mouse movement simulation failed: {str(e)}", "error")
            return ComponentResult(
                success=False,
                data={'error': str(e)},
                errors=[str(e)]
            )
    
    def register_site(self, site: str, config: Dict[str, Any]) -> None:
        """
        Register mouse movement configuration for a site.
        
        Args:
            site: Site identifier
            config: Mouse movement configuration
        """
        self._site_configs[site] = {
            'movement_pattern': config.get('movement_pattern', 'human'),
            'default_duration_ms': config.get('default_duration_ms', 1000),
            'speed_variation': config.get('speed_variation', 0.3),
            'path_variation': config.get('path_variation', 0.2),
            'pause_probability': config.get('pause_probability', 0.2),
            'pause_duration_ms': config.get('pause_duration_ms', 200),
            'intermediate_points': config.get('intermediate_points', 5),
            'realistic_acceleration': config.get('realistic_acceleration', True),
            'random_deviation': config.get('random_deviation', True),
            'scroll_simulation': config.get('scroll_simulation', False),
            'click_simulation': config.get('click_simulation', False)
        }
        
        self._log_operation("register_site", f"Registered mouse movement configuration for site: {site}")
    
    async def _initialize_default_configs(self) -> None:
        """Initialize default mouse movement configurations for common sites."""
        default_configs = {
            'google': {
                'movement_pattern': 'human',
                'default_duration_ms': 800,
                'speed_variation': 0.4,
                'path_variation': 0.3,
                'pause_probability': 0.1,
                'realistic_acceleration': True
            },
            'facebook': {
                'movement_pattern': 'human',
                'default_duration_ms': 1200,
                'speed_variation': 0.5,
                'path_variation': 0.4,
                'pause_probability': 0.2,
                'realistic_acceleration': True
            },
            'twitter': {
                'movement_pattern': 'human',
                'default_duration_ms': 1000,
                'speed_variation': 0.6,
                'path_variation': 0.5,
                'pause_probability': 0.3,
                'realistic_acceleration': True
            },
            'amazon': {
                'movement_pattern': 'human',
                'default_duration_ms': 900,
                'speed_variation': 0.3,
                'path_variation': 0.2,
                'pause_probability': 0.15,
                'realistic_acceleration': True
            },
            'linkedin': {
                'movement_pattern': 'human',
                'default_duration_ms': 1100,
                'speed_variation': 0.4,
                'path_variation': 0.3,
                'pause_probability': 0.2,
                'realistic_acceleration': True
            }
        }
        
        for site, config in default_configs.items():
            if site not in self._site_configs:
                self._site_configs[site] = config
    
    def _initialize_movement_state(self, site: str) -> None:
        """Initialize movement state for a site."""
        if site not in self._movement_state:
            self._movement_state[site] = {
                'movements_performed': 0,
                'total_distance_pixels': 0,
                'total_duration_ms': 0,
                'last_movement_time': None,
                'movement_history': []
            }
    
    async def _simulate_mouse_movement(
        self, site: str, page, target_element, target_coordinates: Tuple[int, int],
        movement_pattern: str, duration_ms: int, intermediate_points: int
    ) -> Dict[str, Any]:
        """Simulate mouse movement."""
        try:
            config = self._site_configs[site]
            state = self._movement_state[site]
            
            # Get start position
            current_pos = await page.mouse.position()
            start_x, start_y = current_pos['x'], current_pos['y']
            
            # Get target position
            if target_element:
                target_box = await target_element.bounding_box()
                target_x = target_box['x'] + target_box['width'] / 2
                target_y = target_box['y'] + target_box['height'] / 2
            else:
                target_x, target_y = target_coordinates
            
            # Calculate distance
            distance = math.sqrt((target_x - start_x) ** 2 + (target_y - start_y) ** 2)
            
            # Get movement pattern function
            pattern_func = self._movement_patterns.get(movement_pattern, self._human_movement)
            
            # Generate movement path
            path = await pattern_func(start_x, start_y, target_x, target_y, intermediate_points, config)
            
            # Apply path variation if enabled
            if config.get('random_deviation', True):
                path = self._apply_path_variation(path, config)
            
            # Execute movement
            await self._execute_movement_path(page, path, duration_ms, config)
            
            # Update state
            state['movements_performed'] += 1
            state['total_distance_pixels'] += distance
            state['total_duration_ms'] += duration_ms
            state['last_movement_time'] = datetime.utcnow()
            
            # Record movement in history
            movement_record = {
                'start_position': (start_x, start_y),
                'target_position': (target_x, target_y),
                'distance': distance,
                'duration_ms': duration_ms,
                'pattern': movement_pattern,
                'intermediate_points': len(path),
                'timestamp': state['last_movement_time'].isoformat()
            }
            state['movement_history'].append(movement_record)
            
            # Limit history size
            if len(state['movement_history']) > 100:
                state['movement_history'] = state['movement_history'][-50:]
            
            return {
                'success': True,
                'start_position': (start_x, start_y),
                'target_position': (target_x, target_y),
                'distance': distance,
                'duration_ms': duration_ms,
                'pattern': movement_pattern,
                'intermediate_points': len(path),
                'path': path
            }
            
        except Exception as e:
            self._log_operation("_simulate_mouse_movement", f"Mouse movement simulation failed for {site}: {str(e)}", "error")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _linear_movement(self, start_x: float, start_y: float, target_x: float, target_y: float, 
                              intermediate_points: int, config: Dict[str, Any]) -> List[Tuple[float, float]]:
        """Generate linear movement path."""
        path = []
        for i in range(intermediate_points + 1):
            t = i / intermediate_points
            x = start_x + (target_x - start_x) * t
            y = start_y + (target_y - start_y) * t
            path.append((x, y))
        return path
    
    async def _bezier_movement(self, start_x: float, start_y: float, target_x: float, target_y: float,
                           intermediate_points: int, config: Dict[str, Any]) -> List[Tuple[float, float]]:
        """Generate Bezier curve movement path."""
        path = []
        
        # Control points for Bezier curve
        control_offset = 100
        cp1_x = start_x + random.uniform(-control_offset, control_offset)
        cp1_y = start_y + random.uniform(-control_offset, control_offset)
        cp2_x = target_x + random.uniform(-control_offset, control_offset)
        cp2_y = target_y + random.uniform(-control_offset, control_offset)
        
        for i in range(intermediate_points + 1):
            t = i / intermediate_points
            
            # Cubic Bezier formula
            x = ((1-t)**3 * start_x + 
                 3*(1-t)**2*t * cp1_x + 
                 3*(1-t)*t**2 * cp2_x + 
                 t**3 * target_x)
            
            y = ((1-t)**3 * start_y + 
                 3*(1-t)**2*t * cp1_y + 
                 3*(1-t)*t**2 * cp2_y + 
                 t**3 * target_y)
            
            path.append((x, y))
        
        return path
    
    async def _random_movement(self, start_x: float, start_y: float, target_x: float, target_y: float,
                           intermediate_points: int, config: Dict[str, Any]) -> List[Tuple[float, float]]:
        """Generate random movement path."""
        path = [(start_x, start_y)]
        
        for i in range(intermediate_points):
            t = (i + 1) / (intermediate_points + 1)
            
            # Random deviation from linear path
            max_deviation = min(50, abs(target_x - start_x), abs(target_y - start_y))
            deviation_x = random.uniform(-max_deviation, max_deviation)
            deviation_y = random.uniform(-max_deviation, max_deviation)
            
            x = start_x + (target_x - start_x) * t + deviation_x
            y = start_y + (target_y - start_y) * t + deviation_y
            
            path.append((x, y))
        
        path.append((target_x, target_y))
        return path
    
    async def _human_movement(self, start_x: float, start_y: float, target_x: float, target_y: float,
                          intermediate_points: int, config: Dict[str, Any]) -> List[Tuple[float, float]]:
        """Generate human-like movement path."""
        path = []
        
        # Human movement characteristics
        speed_variation = config.get('speed_variation', 0.3)
        path_variation = config.get('path_variation', 0.2)
        
        for i in range(intermediate_points + 1):
            t = i / intermediate_points
            
            # Base linear interpolation
            x = start_x + (target_x - start_x) * t
            y = start_y + (target_y - start_y) * t
            
            # Add human-like variations
            if i > 0 and i < intermediate_points:
                # Speed variation (slight acceleration/deceleration)
                speed_factor = 1.0 + random.uniform(-speed_variation, speed_variation)
                t = min(1.0, t * speed_factor)
                
                # Recalculate with speed variation
                x = start_x + (target_x - start_x) * t
                y = start_y + (target_y - start_y) * t
            
            # Path variation (slight curve)
            if i > 0 and i < intermediate_points:
                max_deviation = min(30, abs(target_x - start_x), abs(target_y - start_y))
                deviation = max_deviation * path_variation
                x += random.uniform(-deviation, deviation)
                y += random.uniform(-deviation, deviation)
            
            path.append((x, y))
        
        return path
    
    async def _circular_movement(self, start_x: float, start_y: float, target_x: float, target_y: float,
                              intermediate_points: int, config: Dict[str, Any]) -> List[Tuple[float, float]]:
        """Generate circular movement path."""
        path = []
        
        # Calculate circle parameters
        center_x = (start_x + target_x) / 2
        center_y = (start_y + target_y) / 2
        radius = math.sqrt((target_x - start_x) ** 2 + (target_y - start_y) ** 2) / 2
        
        # Calculate angles
        start_angle = math.atan2(start_y - center_y, start_x - center_x)
        end_angle = math.atan2(target_y - center_y, target_x - center_x)
        
        # Determine rotation direction
        if end_angle < start_angle:
            end_angle += 2 * math.pi
        
        for i in range(intermediate_points + 1):
            angle = start_angle + (end_angle - start_angle) * i / intermediate_points
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            path.append((x, y))
        
        return path
    
    async def _spiral_movement(self, start_x: float, start_y: float, target_x: float, target_y: float,
                           intermediate_points: int, config: Dict[str, Any]) -> List[Tuple[float, float]]:
        """Generate spiral movement path."""
        path = []
        
        # Calculate spiral parameters
        center_x = (start_x + target_x) / 2
        center_y = (start_y + target_y) / 2
        max_radius = math.sqrt((target_x - start_x) ** 2 + (target_y - start_y) ** 2) / 2
        
        for i in range(intermediate_points + 1):
            t = i / intermediate_points
            
            # Spiral: radius increases linearly, angle increases exponentially
            radius = max_radius * t
            angle = t * 4 * math.pi  # 2 full rotations
            
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            path.append((x, y))
        
        return path
    
    def _apply_path_variation(self, path: List[Tuple[float, float]], config: Dict[str, Any]) -> List[Tuple[float, float]]:
        """Apply random variation to movement path."""
        try:
            variation = config.get('path_variation', 0.2)
            if variation <= 0:
                return path
            
            varied_path = []
            for i, (x, y) in enumerate(path):
                if i == 0 or i == len(path) - 1:
                    # Keep start and end points fixed
                    varied_path.append((x, y))
                else:
                    # Add random deviation
                    max_deviation = 20 * variation
                    x += random.uniform(-max_deviation, max_deviation)
                    y += random.uniform(-max_deviation, max_deviation)
                    varied_path.append((x, y))
            
            return varied_path
            
        except Exception:
            return path
    
    async def _execute_movement_path(self, page, path: List[Tuple[float, float]], 
                                   duration_ms: int, config: Dict[str, Any]) -> None:
        """Execute the movement path on the page."""
        try:
            if not path:
                return
            
            # Calculate timing for each segment
            total_segments = len(path) - 1
            if total_segments == 0:
                return
            
            segment_duration = duration_ms / total_segments
            pause_probability = config.get('pause_probability', 0.2)
            pause_duration = config.get('pause_duration_ms', 200)
            speed_variation = config.get('speed_variation', 0.3)
            
            for i in range(total_segments):
                start_x, start_y = path[i]
                end_x, end_y = path[i + 1]
                
                # Apply speed variation
                if speed_variation > 0:
                    speed_factor = 1.0 + random.uniform(-speed_variation, speed_variation)
                    current_segment_duration = segment_duration * speed_factor
                else:
                    current_segment_duration = segment_duration
                
                # Move to next position
                await page.mouse.move(end_x, end_y)
                
                # Random pause
                if random.random() < pause_probability:
                    await asyncio.sleep(pause_duration / 1000.0)
                
                # Small delay between movements
                await asyncio.sleep(current_segment_duration / 1000.0)
            
        except Exception as e:
            self._log_operation("_execute_movement_path", f"Failed to execute movement path: {str(e)}", "error")
    
    def _update_movement_stats(self, site: str, result: Dict[str, Any], execution_time: float) -> None:
        """Update movement statistics for a site."""
        try:
            if site not in self._movement_stats:
                self._movement_stats[site] = {
                    'movements_performed': 0,
                    'total_distance_pixels': 0,
                    'total_duration_ms': 0,
                    'average_movement_time_ms': 0.0,
                    'last_movement_time': None,
                    'success_count': 0,
                    'error_count': 0
                }
            
            stats = self._movement_stats[site]
            stats['movements_performed'] += 1
            stats['last_movement_time'] = datetime.utcnow()
            
            if result['success']:
                stats['success_count'] += 1
                stats['total_distance_pixels'] += result.get('distance', 0)
                stats['total_duration_ms'] += result.get('duration_ms', 0)
            else:
                stats['error_count'] += 1
            
            # Update average execution time
            total_time = stats.get('total_execution_time_ms', 0) + execution_time
            stats['total_execution_time_ms'] = total_time
            stats['average_movement_time_ms'] = total_time / stats['movements_performed']
            
        except Exception as e:
            self._log_operation("_update_movement_stats", f"Failed to update movement stats: {str(e)}", "error")
    
    def add_movement_callback(self, site: str, callback: Callable) -> None:
        """Add callback for mouse movement events."""
        if site not in self._movement_callbacks:
            self._movement_callbacks[site] = []
        self._movement_callbacks[site].append(callback)
    
    async def _call_movement_callbacks(self, site: str, data: Dict[str, Any]) -> None:
        """Call movement callbacks for site."""
        if site in self._movement_callbacks:
            for callback in self._movement_callbacks[site]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(site, data)
                    else:
                        callback(site, data)
                except Exception as e:
                    self._log_operation("_call_movement_callbacks", f"Movement callback failed for {site}: {str(e)}", "error")
    
    async def click_element(self, page, element, button: str = 'left', delay_ms: int = 100) -> bool:
        """Click on an element with human-like delay."""
        try:
            # Get element position
            box = await element.bounding_box()
            x = box['x'] + box['width'] / 2
            y = box['y'] + box['height'] / 2
            
            # Move to element
            await page.mouse.move(x, y)
            
            # Small delay before click
            await asyncio.sleep(delay_ms / 1000.0)
            
            # Click
            await page.mouse.click(button)
            
            return True
            
        except Exception as e:
            self._log_operation("click_element", f"Failed to click element: {str(e)}", "error")
            return False
    
    def get_movement_history(self, site: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get movement history for a site."""
        state = self._movement_state.get(site)
        if not state:
            return []
        
        history = state.get('movement_history', [])
        return history[-limit:] if limit > 0 else history
    
    def get_movement_stats(self, site: str) -> Optional[Dict[str, Any]]:
        """Get movement statistics for a site."""
        if site not in self._movement_stats:
            return None
        
        stats = self._movement_stats[site].copy()
        if 'last_movement_time' in stats and isinstance(stats['last_movement_time'], datetime):
            stats['last_movement_time'] = stats['last_movement_time'].isoformat()
        
        return stats
    
    def reset_movement_state(self, site: str) -> None:
        """Reset movement state for a site."""
        if site in self._movement_state:
            del self._movement_state[site]
        if site in self._movement_stats:
            del self._movement_stats[site]
    
    def get_supported_sites(self) -> List[str]:
        """Get list of supported sites."""
        return list(self._supported_sites)
    
    def get_site_config(self, site: str) -> Optional[Dict[str, Any]]:
        """Get mouse movement configuration for a site."""
        return self._site_configs.get(site)
    
    async def cleanup(self) -> None:
        """Clean up shared mouse movement component."""
        try:
            # Clear all states and callbacks
            self._movement_state.clear()
            self._movement_stats.clear()
            self._movement_callbacks.clear()
            
            self._log_operation("cleanup", "Shared mouse movement component cleaned up")
            
        except Exception as e:
            self._log_operation("cleanup", f"Shared mouse movement cleanup failed: {str(e)}", "error")


# Factory function for easy component creation
def create_mouse_movement_component() -> MouseMovementComponent:
    """Create a shared mouse movement component."""
    return MouseMovementComponent()


# Component metadata for discovery
COMPONENT_METADATA = {
    'id': 'shared_mouse_movement',
    'name': 'Shared Mouse Movement Component',
    'version': '1.0.0',
    'type': 'STEALTH',
    'description': 'Reusable mouse movement simulation for multiple sites',
    'supported_sites': ['google', 'facebook', 'twitter', 'instagram', 'linkedin', 'amazon', 'ebay', 'reddit', 'youtube', 'tiktok'],
    'features': [
        'multi_site_support',
        'multiple_movement_patterns',
        'human_like_behavior',
        'path_variation',
        'speed_variation',
        'click_simulation',
        'movement_history',
        'statistics_tracking',
        'callback_system'
    ],
    'dependencies': [],
    'configuration_required': [],
    'optional_configuration': ['movement_pattern', 'default_duration_ms', 'speed_variation', 'path_variation', 'pause_probability']
}
