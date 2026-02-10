"""
Shared user agent rotation component for reusable stealth functionality across sites.

This module provides user agent rotation functionality that can be easily
integrated into any site scraper for avoiding detection through user agent variation.
"""

from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timedelta
import asyncio
import json
import random
import secrets
from urllib.parse import urlparse

from src.sites.base.component_interface import BaseComponent, ComponentContext, ComponentResult


class UserAgentRotationComponent(BaseComponent):
    """Shared user agent rotation component for cross-site usage."""
    
    def __init__(
        self,
        component_id: str = "shared_user_agent_rotation",
        name: str = "Shared User Agent Rotation Component",
        version: str = "1.0.0",
        description: str = "Reusable user agent rotation for multiple sites"
    ):
        """
        Initialize shared user agent rotation component.
        
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
        
        # User agent rotation configurations for different sites
        self._site_configs: Dict[str, Dict[str, Any]] = {}
        
        # User agent pools for different browsers and platforms
        self._user_agent_pools: Dict[str, List[str]] = {}
        
        # Rotation state and statistics
        self._rotation_state: Dict[str, Dict[str, Any]] = {}
        self._rotation_stats: Dict[str, Dict[str, Any]] = {}
        
        # Callback handlers
        self._rotation_callbacks: Dict[str, List[Callable]] = {}
        
        # Component metadata
        self._supported_sites = [
            'google', 'facebook', 'twitter', 'instagram', 'linkedin',
            'amazon', 'ebay', 'reddit', 'youtube', 'tiktok'
        ]
        
        # Initialize default user agent pools
        self._initialize_user_agent_pools()
    
    async def initialize(self, context: ComponentContext) -> bool:
        """
        Initialize shared user agent rotation component.
        
        Args:
            context: Component context
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Load user agent rotation configurations from context
            config = context.config_manager.get_config(context.environment) if context.config_manager else {}
            
            # Initialize default site configurations
            await self._initialize_default_configs()
            
            # Load custom site configurations
            custom_configs = config.get('user_agent_rotation_site_configs', {})
            for site, site_config in custom_configs.items():
                self.register_site(site, site_config)
            
            self._log_operation("initialize", f"Shared user agent rotation component initialized with {len(self._site_configs)} site configurations")
            return True
            
        except Exception as e:
            self._log_operation("initialize", f"Shared user agent rotation initialization failed: {str(e)}", "error")
            return False
    
    async def execute(self, **kwargs) -> ComponentResult:
        """
        Execute user agent rotation for a specific site.
        
        Args:
            **kwargs: Rotation parameters including 'site', 'page', 'rotation_strategy', etc.
            
        Returns:
            User agent rotation result
        """
        try:
            start_time = datetime.utcnow()
            
            # Extract parameters
            site = kwargs.get('site')
            page = kwargs.get('page')
            rotation_strategy = kwargs.get('rotation_strategy', 'random')
            force_rotation = kwargs.get('force_rotation', False)
            
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
            
            # Initialize rotation state
            self._initialize_rotation_state(site)
            
            # Perform user agent rotation
            rotation_result = await self._rotate_user_agent(
                site, page, rotation_strategy, force_rotation
            )
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            # Update statistics
            self._update_rotation_stats(site, rotation_result, execution_time)
            
            # Call rotation callbacks
            await self._call_rotation_callbacks(site, rotation_result)
            
            return ComponentResult(
                success=rotation_result['success'],
                data={
                    'site': site,
                    'rotation_timestamp': start_time.isoformat(),
                    **rotation_result
                },
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            self._log_operation("execute", f"User agent rotation failed: {str(e)}", "error")
            return ComponentResult(
                success=False,
                data={'error': str(e)},
                errors=[str(e)]
            )
    
    def register_site(self, site: str, config: Dict[str, Any]) -> None:
        """
        Register user agent rotation configuration for a site.
        
        Args:
            site: Site identifier
            config: User agent rotation configuration
        """
        self._site_configs[site] = {
            'rotation_strategy': config.get('rotation_strategy', 'random'),
            'rotation_interval': config.get('rotation_interval', 3600),  # seconds
            'user_agent_pools': config.get('user_agent_pools', ['chrome', 'firefox', 'safari']),
            'platform_targets': config.get('platform_targets', ['windows', 'macos', 'linux']),
            'version_targets': config.get('version_targets', ['latest', 'stable', 'recent']),
            'mobile_probability': config.get('mobile_probability', 0.2),
            'custom_user_agents': config.get('custom_user_agents', []),
            'exclude_user_agents': config.get('exclude_user_agents', []),
            'persist_user_agent': config.get('persist_user_agent', True),
            'rotation_on_error': config.get('rotation_on_error', True)
        }
        
        self._log_operation("register_site", f"Registered user agent rotation configuration for site: {site}")
    
    def _initialize_user_agent_pools(self) -> None:
        """Initialize default user agent pools for different browsers."""
        # Chrome user agents
        self._user_agent_pools['chrome'] = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'
        ]
        
        # Firefox user agents
        self._user_agent_pools['firefox'] = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/118.0'
        ]
        
        # Safari user agents
        self._user_agent_pools['safari'] = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1'
        ]
        
        # Edge user agents
        self._user_agent_pools['edge'] = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
        ]
        
        # Mobile user agents
        self._user_agent_pools['mobile'] = [
            'Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
        ]
        
        # Bot user agents (for testing)
        self._user_agent_pools['bot'] = [
            'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
            'Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)',
            'Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)'
        ]
    
    async def _initialize_default_configs(self) -> None:
        """Initialize default user agent rotation configurations for common sites."""
        default_configs = {
            'google': {
                'rotation_strategy': 'weighted_random',
                'user_agent_pools': ['chrome', 'firefox', 'edge'],
                'mobile_probability': 0.3,
                'persist_user_agent': True,
                'rotation_interval': 1800
            },
            'facebook': {
                'rotation_strategy': 'random',
                'user_agent_pools': ['chrome', 'firefox', 'safari'],
                'mobile_probability': 0.4,
                'persist_user_agent': True,
                'rotation_interval': 3600
            },
            'twitter': {
                'rotation_strategy': 'random',
                'user_agent_pools': ['chrome', 'firefox', 'safari'],
                'mobile_probability': 0.5,
                'persist_user_agent': True,
                'rotation_interval': 2400
            },
            'amazon': {
                'rotation_strategy': 'random',
                'user_agent_pools': ['chrome', 'firefox', 'edge'],
                'mobile_probability': 0.2,
                'persist_user_agent': True,
                'rotation_interval': 3600
            },
            'linkedin': {
                'rotation_strategy': 'weighted_random',
                'user_agent_pools': ['chrome', 'firefox', 'edge'],
                'mobile_probability': 0.1,
                'persist_user_agent': True,
                'rotation_interval': 3600
            }
        }
        
        for site, config in default_configs.items():
            if site not in self._site_configs:
                self._site_configs[site] = config
    
    def _initialize_rotation_state(self, site: str) -> None:
        """Initialize rotation state for a site."""
        if site not in self._rotation_state:
            self._rotation_state[site] = {
                'current_user_agent': None,
                'last_rotation_time': None,
                'rotation_count': 0,
                'user_agent_history': [],
                'rotation_interval': self._site_configs.get(site, {}).get('rotation_interval', 3600)
            }
    
    async def _rotate_user_agent(self, site: str, page, rotation_strategy: str, force_rotation: bool) -> Dict[str, Any]:
        """Perform user agent rotation."""
        try:
            config = self._site_configs[site]
            state = self._rotation_state[site]
            
            # Check if rotation is needed
            if not force_rotation and self._should_keep_current_user_agent(site, state):
                return {
                    'success': True,
                    'user_agent': state['current_user_agent'],
                    'rotation_applied': False,
                    'reason': 'current_user_agent_still_valid'
                }
            
            # Select new user agent
            new_user_agent = await self._select_user_agent(site, rotation_strategy, config)
            
            if not new_user_agent:
                return {
                    'success': False,
                    'error': 'No suitable user agent found'
                }
            
            # Apply user agent to page
            await page.set_extra_http_headers({
                'User-Agent': new_user_agent
            })
            
            # Update state
            state['current_user_agent'] = new_user_agent
            state['last_rotation_time'] = datetime.utcnow()
            state['rotation_count'] += 1
            state['user_agent_history'].append({
                'user_agent': new_user_agent,
                'timestamp': state['last_rotation_time'].isoformat(),
                'strategy': rotation_strategy
            })
            
            # Limit history size
            if len(state['user_agent_history']) > 100:
                state['user_agent_history'] = state['user_agent_history'][-50:]
            
            return {
                'success': True,
                'user_agent': new_user_agent,
                'rotation_applied': True,
                'rotation_count': state['rotation_count'],
                'strategy_used': rotation_strategy
            }
            
        except Exception as e:
            self._log_operation("_rotate_user_agent", f"User agent rotation failed for {site}: {str(e)}", "error")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _should_keep_current_user_agent(self, site: str, state: Dict[str, Any]) -> bool:
        """Check if current user agent should be kept."""
        try:
            if not state.get('current_user_agent'):
                return False
            
            if not state.get('persist_user_agent', True):
                return False
            
            last_rotation = state.get('last_rotation_time')
            if not last_rotation:
                return False
            
            rotation_interval = state.get('rotation_interval', 3600)
            elapsed = (datetime.utcnow() - last_rotation).total_seconds()
            
            return elapsed < rotation_interval
            
        except Exception:
            return False
    
    async def _select_user_agent(self, site: str, rotation_strategy: str, config: Dict[str, Any]) -> Optional[str]:
        """Select a user agent based on strategy."""
        try:
            # Get available user agents
            available_user_agents = self._get_available_user_agents(config)
            
            if not available_user_agents:
                return None
            
            # Apply exclusion filters
            excluded_agents = config.get('exclude_user_agents', [])
            available_user_agents = [ua for ua in available_user_agents if not any(excluded in ua for excluded in excluded_agents)]
            
            if not available_user_agents:
                return None
            
            # Add custom user agents
            custom_agents = config.get('custom_user_agents', [])
            if custom_agents:
                available_user_agents.extend(custom_agents)
            
            # Select based on strategy
            if rotation_strategy == 'random':
                return random.choice(available_user_agents)
            elif rotation_strategy == 'weighted_random':
                return self._weighted_random_selection(available_user_agents, config)
            elif rotation_strategy == 'round_robin':
                return self._round_robin_selection(site, available_user_agents)
            elif rotation_strategy == 'sequential':
                return self._sequential_selection(site, available_user_agents)
            else:
                return random.choice(available_user_agents)
            
        except Exception as e:
            self._log_operation("_select_user_agent", f"User agent selection failed: {str(e)}", "error")
            return None
    
    def _get_available_user_agents(self, config: Dict[str, Any]) -> List[str]:
        """Get available user agents based on configuration."""
        try:
            user_agents = []
            
            # Get user agents from specified pools
            pools = config.get('user_agent_pools', ['chrome', 'firefox'])
            for pool in pools:
                if pool in self._user_agent_pools:
                    user_agents.extend(self._user_agent_pools[pool])
            
            # Add mobile user agents if probability allows
            mobile_probability = config.get('mobile_probability', 0.2)
            if random.random() < mobile_probability:
                if 'mobile' in self._user_agent_pools:
                    user_agents.extend(self._user_agent_pools['mobile'])
            
            return list(set(user_agents))  # Remove duplicates
            
        except Exception as e:
            self._log_operation("_get_available_user_agents", f"Failed to get available user agents: {str(e)}", "error")
            return []
    
    def _weighted_random_selection(self, user_agents: List[str], config: Dict[str, Any]) -> str:
        """Select user agent using weighted random selection."""
        try:
            # Create weights based on browser preferences
            weights = []
            pools = config.get('user_agent_pools', ['chrome', 'firefox'])
            
            for ua in user_agents:
                weight = 1.0
                
                # Higher weight for Chrome
                if 'Chrome' in ua and 'chrome' in pools:
                    weight *= 2.0
                
                # Higher weight for Firefox
                if 'Firefox' in ua and 'firefox' in pools:
                    weight *= 1.5
                
                # Lower weight for mobile if not explicitly requested
                if 'Mobile' in ua and 'mobile' not in pools:
                    weight *= 0.5
                
                weights.append(weight)
            
            # Weighted random selection
            total_weight = sum(weights)
            if total_weight == 0:
                return random.choice(user_agents)
            
            r = random.uniform(0, total_weight)
            upto = 0
            
            for i, weight in enumerate(weights):
                if upto + weight >= r:
                    return user_agents[i]
                upto += weight
            
            return user_agents[-1]  # Fallback
            
        except Exception:
            return random.choice(user_agents)
    
    def _round_robin_selection(self, site: str, user_agents: List[str]) -> str:
        """Select user agent using round-robin strategy."""
        try:
            state = self._rotation_state[site]
            rotation_count = state.get('rotation_count', 0)
            
            index = rotation_count % len(user_agents)
            return user_agents[index]
            
        except Exception:
            return random.choice(user_agents)
    
    def _sequential_selection(self, site: str, user_agents: List[str]) -> str:
        """Select user agent using sequential strategy."""
        try:
            state = self._rotation_state[site]
            rotation_count = state.get('rotation_count', 0)
            
            # Shuffle once, then use sequential
            if rotation_count == 0:
                random.shuffle(user_agents)
                state['_shuffled_agents'] = user_agents
            
            shuffled_agents = state.get('_shuffled_agents', user_agents)
            index = rotation_count % len(shuffled_agents)
            return shuffled_agents[index]
            
        except Exception:
            return random.choice(user_agents)
    
    def _update_rotation_stats(self, site: str, result: Dict[str, Any], execution_time: float) -> None:
        """Update rotation statistics for a site."""
        try:
            if site not in self._rotation_stats:
                self._rotation_stats[site] = {
                    'rotations_performed': 0,
                    'total_rotation_time_ms': 0.0,
                    'average_rotation_time_ms': 0.0,
                    'last_rotation_time': None,
                    'success_count': 0,
                    'error_count': 0
                }
            
            stats = self._rotation_stats[site]
            stats['rotations_performed'] += 1
            stats['last_rotation_time'] = datetime.utcnow()
            
            if result['success']:
                stats['success_count'] += 1
            else:
                stats['error_count'] += 1
            
            # Update average execution time
            total_time = stats.get('total_rotation_time_ms', 0) + execution_time
            stats['total_rotation_time_ms'] = total_time
            stats['average_rotation_time_ms'] = total_time / stats['rotations_performed']
            
        except Exception as e:
            self._log_operation("_update_rotation_stats", f"Failed to update rotation stats: {str(e)}", "error")
    
    def add_rotation_callback(self, site: str, callback: Callable) -> None:
        """Add callback for user agent rotation events."""
        if site not in self._rotation_callbacks:
            self._rotation_callbacks[site] = []
        self._rotation_callbacks[site].append(callback)
    
    async def _call_rotation_callbacks(self, site: str, data: Dict[str, Any]) -> None:
        """Call rotation callbacks for site."""
        if site in self._rotation_callbacks:
            for callback in self._rotation_callbacks[site]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(site, data)
                    else:
                        callback(site, data)
                except Exception as e:
                    self._log_operation("_call_rotation_callbacks", f"Rotation callback failed for {site}: {str(e)}", "error")
    
    def get_current_user_agent(self, site: str) -> Optional[str]:
        """Get current user agent for a site."""
        state = self._rotation_state.get(site)
        return state.get('current_user_agent') if state else None
    
    def get_rotation_history(self, site: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get rotation history for a site."""
        state = self._rotation_state.get(site)
        if not state:
            return []
        
        history = state.get('user_agent_history', [])
        return history[-limit:] if limit > 0 else history
    
    def force_rotation(self, site: str) -> bool:
        """Force user agent rotation for a site."""
        try:
            state = self._rotation_state.get(site)
            if state:
                state['last_rotation_time'] = None  # This will force rotation on next call
                return True
            return False
        except Exception:
            return False
    
    def get_supported_sites(self) -> List[str]:
        """Get list of supported sites."""
        return list(self._supported_sites)
    
    def get_site_config(self, site: str) -> Optional[Dict[str, Any]]:
        """Get user agent rotation configuration for a site."""
        return self._site_configs.get(site)
    
    def get_rotation_stats(self, site: str) -> Optional[Dict[str, Any]]:
        """Get rotation statistics for a site."""
        if site not in self._rotation_stats:
            return None
        
        stats = self._rotation_stats[site].copy()
        if 'last_rotation_time' in stats and isinstance(stats['last_rotation_time'], datetime):
            stats['last_rotation_time'] = stats['last_rotation_time'].isoformat()
        
        return stats
    
    def reset_rotation_state(self, site: str) -> None:
        """Reset rotation state for a site."""
        if site in self._rotation_state:
            del self._rotation_state[site]
        if site in self._rotation_stats:
            del self._rotation_stats[site]
    
    def add_custom_user_agent(self, site: str, user_agent: str) -> None:
        """Add custom user agent for a site."""
        try:
            if site not in self._site_configs:
                self._site_configs[site] = {}
            
            if 'custom_user_agents' not in self._site_configs[site]:
                self._site_configs[site]['custom_user_agents'] = []
            
            self._site_configs[site]['custom_user_agents'].append(user_agent)
            
            self._log_operation("add_custom_user_agent", f"Added custom user agent for site: {site}")
            
        except Exception as e:
            self._log_operation("add_custom_user_agent", f"Failed to add custom user agent: {str(e)}", "error")
    
    async def cleanup(self) -> None:
        """Clean up shared user agent rotation component."""
        try:
            # Clear all states and callbacks
            self._rotation_state.clear()
            self._rotation_stats.clear()
            self._rotation_callbacks.clear()
            
            self._log_operation("cleanup", "Shared user agent rotation component cleaned up")
            
        except Exception as e:
            self._log_operation("cleanup", f"Shared user agent rotation cleanup failed: {str(e)}", "error")


# Factory function for easy component creation
def create_user_agent_rotation_component() -> UserAgentRotationComponent:
    """Create a shared user agent rotation component."""
    return UserAgentRotationComponent()


# Component metadata for discovery
COMPONENT_METADATA = {
    'id': 'shared_user_agent_rotation',
    'name': 'Shared User Agent Rotation Component',
    'version': '1.0.0',
    'type': 'STEALTH',
    'description': 'Reusable user agent rotation for multiple sites',
    'supported_sites': ['google', 'facebook', 'twitter', 'instagram', 'linkedin', 'amazon', 'ebay', 'reddit', 'youtube', 'tiktok'],
    'features': [
        'multi_site_support',
        'multiple_rotation_strategies',
        'browser_pool_support',
        'mobile_support',
        'custom_user_agents',
        'rotation_history',
        'statistics_tracking',
        'callback_system'
    ],
    'dependencies': [],
    'configuration_required': [],
    'optional_configuration': ['rotation_strategy', 'rotation_interval', 'user_agent_pools', 'mobile_probability', 'custom_user_agents']
}
