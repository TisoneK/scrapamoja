"""
Shared OAuth authentication component for reusable authentication across sites.

This module provides OAuth 1.0a and OAuth 2.0 authentication functionality
that can be easily integrated into any site scraper.
"""

from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timedelta
import asyncio
import json
import base64
import hashlib
import secrets
from urllib.parse import urlencode, parse_qs, urlparse

from src.sites.base.component_interface import BaseComponent, ComponentContext, ComponentResult


class OAuthAuthenticationComponent(BaseComponent):
    """Shared OAuth authentication component for cross-site usage."""
    
    def __init__(
        self,
        component_id: str = "shared_oauth_auth",
        name: str = "Shared OAuth Authentication Component",
        version: str = "1.0.0",
        description: str = "Reusable OAuth authentication for multiple sites"
    ):
        """
        Initialize shared OAuth authentication component.
        
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
            component_type="AUTHENTICATION"
        )
        
        # OAuth configurations for different sites
        self._site_configs: Dict[str, Dict[str, Any]] = {}
        
        # Token storage per site
        self._tokens: Dict[str, Dict[str, Any]] = {}
        
        # Authentication state per site
        self._auth_states: Dict[str, Dict[str, Any]] = {}
        
        # Callback handlers
        self._success_callbacks: Dict[str, List[Callable]] = {}
        self._error_callbacks: Dict[str, List[Callable]] = {}
        
        # Component metadata
        self._supported_sites = [
            'github', 'google', 'facebook', 'twitter', 'linkedin',
            'microsoft', 'amazon', 'reddit', 'discord', 'slack'
        ]
        
        self._oauth_versions = {
            'github': '2.0',
            'google': '2.0',
            'facebook': '2.0',
            'twitter': '1.0a',
            'linkedin': '2.0',
            'microsoft': '2.0',
            'amazon': '2.0',
            'reddit': '2.0',
            'discord': '2.0',
            'slack': '2.0'
        }
    
    async def initialize(self, context: ComponentContext) -> bool:
        """
        Initialize shared OAuth component with site configurations.
        
        Args:
            context: Component context
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Load OAuth configurations from context
            config = context.config_manager.get_config(context.environment) if context.config_manager else {}
            
            # Initialize default site configurations
            await self._initialize_default_configs()
            
            # Load custom site configurations
            custom_configs = config.get('oauth_site_configs', {})
            for site, site_config in custom_configs.items():
                self.register_site(site, site_config)
            
            self._log_operation("initialize", f"Shared OAuth component initialized with {len(self._site_configs)} site configurations")
            return True
            
        except Exception as e:
            self._log_operation("initialize", f"Shared OAuth initialization failed: {str(e)}", "error")
            return False
    
    async def execute(self, **kwargs) -> ComponentResult:
        """
        Execute OAuth authentication for a specific site.
        
        Args:
            **kwargs: Authentication parameters including 'site', 'page', etc.
            
        Returns:
            Authentication result
        """
        try:
            start_time = datetime.utcnow()
            
            # Extract parameters
            site = kwargs.get('site')
            page = kwargs.get('page')
            auth_code = kwargs.get('authorization_code')
            verifier = kwargs.get('verifier')
            force_refresh = kwargs.get('force_refresh', False)
            
            if not site:
                return ComponentResult(
                    success=False,
                    data={'error': 'Site parameter is required'},
                    errors=['Site parameter is required']
                )
            
            if site not in self._site_configs:
                return ComponentResult(
                    success=False,
                    data={'error': f'Site {site} not configured'},
                    errors=[f'Site {site} not configured']
                )
            
            # Check if already authenticated
            if not force_refresh and self._is_authenticated(site):
                return ComponentResult(
                    success=True,
                    data={
                        'site': site,
                        'authenticated': True,
                        'access_token': self._tokens[site].get('access_token'),
                        'expires_at': self._tokens[site].get('expires_at')
                    },
                    execution_time_ms=0
                )
            
            # Perform authentication based on OAuth version
            oauth_version = self._oauth_versions.get(site, '2.0')
            
            if oauth_version == "2.0":
                auth_result = await self._oauth2_flow(site, page, auth_code, force_refresh)
            else:
                auth_result = await self._oauth1_flow(site, page, verifier, force_refresh)
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            return ComponentResult(
                success=auth_result['success'],
                data={
                    'site': site,
                    'oauth_version': oauth_version,
                    **auth_result
                },
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            self._log_operation("execute", f"OAuth authentication failed: {str(e)}", "error")
            return ComponentResult(
                success=False,
                data={'error': str(e)},
                errors=[str(e)]
            )
    
    def register_site(self, site: str, config: Dict[str, Any]) -> None:
        """
        Register OAuth configuration for a site.
        
        Args:
            site: Site identifier
            config: OAuth configuration
        """
        required_fields = ['client_id', 'client_secret']
        
        if not all(field in config for field in required_fields):
            raise ValueError(f"OAuth configuration for {site} missing required fields: {required_fields}")
        
        self._site_configs[site] = {
            'oauth_version': config.get('oauth_version', '2.0'),
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
            'redirect_uri': config.get('redirect_uri'),
            'scope': config.get('scope', ''),
            'authorization_url': config.get('authorization_url'),
            'token_url': config.get('token_url'),
            'refresh_token_url': config.get('refresh_token_url'),
            'request_token_url': config.get('request_token_url'),
            'access_token_url': config.get('access_token_url')
        }
        
        self._oauth_versions[site] = config.get('oauth_version', '2.0')
        
        self._log_operation("register_site", f"Registered OAuth configuration for site: {site}")
    
    async def _initialize_default_configs(self) -> None:
        """Initialize default OAuth configurations for common sites."""
        default_configs = {
            'github': {
                'oauth_version': '2.0',
                'authorization_url': 'https://github.com/login/oauth/authorize',
                'token_url': 'https://github.com/login/oauth/access_token',
                'scope': 'user repo'
            },
            'google': {
                'oauth_version': '2.0',
                'authorization_url': 'https://accounts.google.com/o/oauth2/v2/auth',
                'token_url': 'https://oauth2.googleapis.com/token',
                'scope': 'openid email profile'
            },
            'facebook': {
                'oauth_version': '2.0',
                'authorization_url': 'https://www.facebook.com/v18.0/dialog/oauth',
                'token_url': 'https://graph.facebook.com/v18.0/oauth/access_token',
                'scope': 'email public_profile'
            },
            'twitter': {
                'oauth_version': '1.0a',
                'request_token_url': 'https://api.twitter.com/oauth/request_token',
                'authorization_url': 'https://api.twitter.com/oauth/authorize',
                'access_token_url': 'https://api.twitter.com/oauth/access_token'
            },
            'linkedin': {
                'oauth_version': '2.0',
                'authorization_url': 'https://www.linkedin.com/oauth/v2/authorization',
                'token_url': 'https://www.linkedin.com/oauth/v2/accessToken',
                'scope': 'r_liteprofile r_emailaddress'
            }
        }
        
        for site, config in default_configs.items():
            if site not in self._site_configs:
                # Note: These are template configs - actual client_id/secret needed
                self._site_configs[site] = config
    
    async def _oauth2_flow(self, site: str, page, auth_code: str, force_refresh: bool) -> Dict[str, Any]:
        """Execute OAuth 2.0 flow."""
        try:
            config = self._site_configs[site]
            
            # Check for refresh token
            if not force_refresh and site in self._tokens:
                refresh_token = self._tokens[site].get('refresh_token')
                if refresh_token and not self._is_token_valid(site):
                    refresh_result = await self._refresh_oauth2_token(site, refresh_token)
                    if refresh_result['success']:
                        return refresh_result
            
            # Generate authorization URL if no auth code provided
            if not auth_code:
                auth_url = self._generate_oauth2_auth_url(site, config)
                return {
                    'success': False,
                    'requires_auth': True,
                    'authorization_url': auth_url,
                    'message': 'Authorization code required'
                }
            
            # Exchange authorization code for access token
            token_result = await self._exchange_oauth2_code(site, config, auth_code)
            
            return token_result
            
        except Exception as e:
            self._log_operation("_oauth2_flow", f"OAuth 2.0 flow failed for {site}: {str(e)}", "error")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _oauth1_flow(self, site: str, page, verifier: str, force_refresh: bool) -> Dict[str, Any]:
        """Execute OAuth 1.0a flow."""
        try:
            config = self._site_configs[site]
            
            # Step 1: Get request token
            request_token_result = await self._get_oauth1_request_token(site, config)
            if not request_token_result['success']:
                return request_token_result
            
            # Step 2: Generate authorization URL
            auth_url = self._generate_oauth1_auth_url(site, config)
            
            # Step 3: Get verifier if not provided
            if not verifier:
                return {
                    'success': False,
                    'requires_auth': True,
                    'authorization_url': auth_url,
                    'request_token': request_token_result['request_token'],
                    'message': 'Authorization verifier required'
                }
            
            # Step 4: Exchange request token for access token
            token_result = await self._exchange_oauth1_token(site, config, verifier)
            
            return token_result
            
        except Exception as e:
            self._log_operation("_oauth1_flow", f"OAuth 1.0a flow failed for {site}: {str(e)}", "error")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_oauth2_auth_url(self, site: str, config: Dict[str, Any]) -> str:
        """Generate OAuth 2.0 authorization URL."""
        params = {
            'client_id': config['client_id'],
            'redirect_uri': config.get('redirect_uri', ''),
            'response_type': 'code',
            'scope': config.get('scope', ''),
            'state': self._generate_state(site)
        }
        
        return f"{config['authorization_url']}?{urlencode(params)}"
    
    def _generate_oauth1_auth_url(self, site: str, config: Dict[str, Any]) -> str:
        """Generate OAuth 1.0a authorization URL."""
        request_token = self._auth_states.get(site, {}).get('request_token', '')
        params = {
            'oauth_token': request_token,
            'oauth_callback': config.get('redirect_uri', '')
        }
        
        return f"{config['authorization_url']}?{urlencode(params)}"
    
    async def _exchange_oauth2_code(self, site: str, config: Dict[str, Any], auth_code: str) -> Dict[str, Any]:
        """Exchange OAuth 2.0 authorization code for access token."""
        try:
            # In a real implementation, make HTTP request to token URL
            # For demonstration, we'll simulate the response
            simulated_response = {
                'access_token': f'oauth2_access_token_{site}_{secrets.token_hex(16)}',
                'refresh_token': f'oauth2_refresh_token_{site}_{secrets.token_hex(16)}',
                'expires_in': 3600,
                'token_type': 'Bearer'
            }
            
            # Store tokens
            self._tokens[site] = {
                'access_token': simulated_response['access_token'],
                'refresh_token': simulated_response.get('refresh_token'),
                'expires_at': datetime.utcnow() + timedelta(seconds=simulated_response['expires_in']),
                'token_type': simulated_response['token_type'],
                'oauth_version': '2.0'
            }
            
            self._log_operation("_exchange_oauth2_code", f"OAuth 2.0 token obtained for {site}")
            
            # Call success callbacks
            await self._call_success_callbacks(site, simulated_response)
            
            return {
                'success': True,
                'access_token': simulated_response['access_token'],
                'refresh_token': simulated_response.get('refresh_token'),
                'expires_at': self._tokens[site]['expires_at'].isoformat(),
                'token_type': simulated_response['token_type']
            }
            
        except Exception as e:
            self._log_operation("_exchange_oauth2_code", f"OAuth 2.0 token exchange failed for {site}: {str(e)}", "error")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _refresh_oauth2_token(self, site: str, refresh_token: str) -> Dict[str, Any]:
        """Refresh OAuth 2.0 access token."""
        try:
            config = self._site_configs[site]
            
            # In a real implementation, make HTTP request to refresh token URL
            simulated_response = {
                'access_token': f'refreshed_oauth2_token_{site}_{secrets.token_hex(16)}',
                'expires_in': 3600,
                'token_type': 'Bearer'
            }
            
            # Update tokens
            self._tokens[site]['access_token'] = simulated_response['access_token']
            self._tokens[site]['expires_at'] = datetime.utcnow() + timedelta(seconds=simulated_response['expires_in'])
            
            self._log_operation("_refresh_oauth2_token", f"OAuth 2.0 token refreshed for {site}")
            
            return {
                'success': True,
                'access_token': simulated_response['access_token'],
                'expires_at': self._tokens[site]['expires_at'].isoformat()
            }
            
        except Exception as e:
            self._log_operation("_refresh_oauth2_token", f"OAuth 2.0 token refresh failed for {site}: {str(e)}", "error")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _get_oauth1_request_token(self, site: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get OAuth 1.0a request token."""
        try:
            # In a real implementation, make HTTP request to request token URL
            simulated_response = {
                'oauth_token': f'oauth1_request_token_{site}_{secrets.token_hex(16)}',
                'oauth_token_secret': f'oauth1_request_secret_{site}_{secrets.token_hex(16)}',
                'oauth_callback_confirmed': 'true'
            }
            
            # Store request token
            self._auth_states[site] = {
                'request_token': simulated_response['oauth_token'],
                'request_token_secret': simulated_response['oauth_token_secret']
            }
            
            self._log_operation("_get_oauth1_request_token", f"OAuth 1.0a request token obtained for {site}")
            
            return {
                'success': True,
                'request_token': simulated_response['oauth_token'],
                'request_token_secret': simulated_response['oauth_token_secret']
            }
            
        except Exception as e:
            self._log_operation("_get_oauth1_request_token", f"OAuth 1.0a request token failed for {site}: {str(e)}", "error")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _exchange_oauth1_token(self, site: str, config: Dict[str, Any], verifier: str) -> Dict[str, Any]:
        """Exchange OAuth 1.0a request token for access token."""
        try:
            request_token = self._auth_states.get(site, {}).get('request_token', '')
            
            # In a real implementation, make HTTP request to access token URL
            simulated_response = {
                'oauth_token': f'oauth1_access_token_{site}_{secrets.token_hex(16)}',
                'oauth_token_secret': f'oauth1_access_secret_{site}_{secrets.token_hex(16)}',
                'oauth_expires_in': '3600'
            }
            
            # Store access token
            self._tokens[site] = {
                'access_token': simulated_response['oauth_token'],
                'token_secret': simulated_response['oauth_token_secret'],
                'expires_at': datetime.utcnow() + timedelta(seconds=int(simulated_response['oauth_expires_in'])),
                'oauth_version': '1.0a'
            }
            
            self._log_operation("_exchange_oauth1_token", f"OAuth 1.0a access token obtained for {site}")
            
            # Call success callbacks
            await self._call_success_callbacks(site, simulated_response)
            
            return {
                'success': True,
                'access_token': simulated_response['oauth_token'],
                'expires_at': self._tokens[site]['expires_at'].isoformat()
            }
            
        except Exception as e:
            self._log_operation("_exchange_oauth1_token", f"OAuth 1.0a token exchange failed for {site}: {str(e)}", "error")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_state(self, site: str) -> str:
        """Generate OAuth state parameter."""
        state = secrets.token_hex(16)
        self._auth_states[site] = self._auth_states.get(site, {})
        self._auth_states[site]['state'] = state
        return state
    
    def _is_authenticated(self, site: str) -> bool:
        """Check if site is authenticated."""
        if site not in self._tokens:
            return False
        
        return self._is_token_valid(site)
    
    def _is_token_valid(self, site: str) -> bool:
        """Check if token is valid and not expired."""
        if site not in self._tokens:
            return False
        
        token_data = self._tokens[site]
        if not token_data.get('access_token'):
            return False
        
        expires_at = token_data.get('expires_at')
        if expires_at:
            return datetime.utcnow() < expires_at
        
        return True
    
    def get_auth_headers(self, site: str) -> Dict[str, str]:
        """Get authentication headers for API requests."""
        if not self._is_authenticated(site):
            return {}
        
        token_data = self._tokens[site]
        oauth_version = token_data.get('oauth_version', '2.0')
        
        if oauth_version == "2.0":
            return {
                'Authorization': f"Bearer {token_data['access_token']}"
            }
        else:  # OAuth 1.0a
            return {
                'Authorization': f'OAuth oauth_token="{token_data["access_token"]}"'
            }
    
    def add_success_callback(self, site: str, callback: Callable) -> None:
        """Add success callback for site authentication."""
        if site not in self._success_callbacks:
            self._success_callbacks[site] = []
        self._success_callbacks[site].append(callback)
    
    def add_error_callback(self, site: str, callback: Callable) -> None:
        """Add error callback for site authentication."""
        if site not in self._error_callbacks:
            self._error_callbacks[site] = []
        self._error_callbacks[site].append(callback)
    
    async def _call_success_callbacks(self, site: str, data: Dict[str, Any]) -> None:
        """Call success callbacks for site."""
        if site in self._success_callbacks:
            for callback in self._success_callbacks[site]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(site, data)
                    else:
                        callback(site, data)
                except Exception as e:
                    self._log_operation("_call_success_callbacks", f"Success callback failed for {site}: {str(e)}", "error")
    
    def get_supported_sites(self) -> List[str]:
        """Get list of supported sites."""
        return list(self._supported_sites)
    
    def get_site_config(self, site: str) -> Optional[Dict[str, Any]]:
        """Get OAuth configuration for a site."""
        return self._site_configs.get(site)
    
    def get_token_info(self, site: str) -> Optional[Dict[str, Any]]:
        """Get token information for a site."""
        if site not in self._tokens:
            return None
        
        token_data = self._tokens[site].copy()
        if 'expires_at' in token_data and isinstance(token_data['expires_at'], datetime):
            token_data['expires_at'] = token_data['expires_at'].isoformat()
        
        return token_data
    
    def revoke_token(self, site: str) -> bool:
        """Revoke token for a site."""
        try:
            if site in self._tokens:
                del self._tokens[site]
            
            if site in self._auth_states:
                del self._auth_states[site]
            
            self._log_operation("revoke_token", f"Token revoked for site: {site}")
            return True
            
        except Exception as e:
            self._log_operation("revoke_token", f"Token revocation failed for {site}: {str(e)}", "error")
            return False
    
    async def cleanup(self) -> None:
        """Clean up shared OAuth component."""
        try:
            # Clear all tokens and states
            self._tokens.clear()
            self._auth_states.clear()
            self._success_callbacks.clear()
            self._error_callbacks.clear()
            
            self._log_operation("cleanup", "Shared OAuth component cleaned up")
            
        except Exception as e:
            self._log_operation("cleanup", f"Shared OAuth cleanup failed: {str(e)}", "error")


# Factory function for easy component creation
def create_oauth_component() -> OAuthAuthenticationComponent:
    """Create a shared OAuth authentication component."""
    return OAuthAuthenticationComponent()


# Component metadata for discovery
COMPONENT_METADATA = {
    'id': 'shared_oauth_auth',
    'name': 'Shared OAuth Authentication Component',
    'version': '1.0.0',
    'type': 'AUTHENTICATION',
    'description': 'Reusable OAuth authentication for multiple sites',
    'supported_sites': ['github', 'google', 'facebook', 'twitter', 'linkedin', 'microsoft', 'amazon', 'reddit', 'discord', 'slack'],
    'oauth_versions': ['1.0a', '2.0'],
    'features': [
        'multi_site_support',
        'token_management',
        'automatic_refresh',
        'callback_system',
        'state_management'
    ],
    'dependencies': [],
    'configuration_required': ['client_id', 'client_secret'],
    'optional_configuration': ['redirect_uri', 'scope', 'authorization_url', 'token_url']
}
