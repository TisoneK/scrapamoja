"""
OAuth authentication component template for the modular site scraper template.

This module provides OAuth authentication functionality with support for
OAuth 1.0a, OAuth 2.0, and common authentication flows.
"""

from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import asyncio
import json
import base64
import hashlib
import secrets
from urllib.parse import urlencode, parse_qs

from src.sites.base.component_interface import BaseComponent, ComponentContext, ComponentResult


class OAuthAuthComponent(BaseComponent):
    """OAuth authentication component with support for OAuth 1.0a and OAuth 2.0."""
    
    def __init__(
        self,
        component_id: str = "oauth_auth",
        name: str = "OAuth Authentication Component",
        version: str = "1.0.0",
        description: str = "Handles OAuth authentication flows for web scraping"
    ):
        """
        Initialize OAuth authentication component.
        
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
        
        # OAuth configuration
        self._oauth_version: str = "2.0"  # "1.0a" or "2.0"
        self._client_id: Optional[str] = None
        self._client_secret: Optional[str] = None
        self._redirect_uri: Optional[str] = None
        self._scope: Optional[str] = None
        self._authorization_url: Optional[str] = None
        self._token_url: Optional[str] = None
        self._refresh_token_url: Optional[str] = None
        
        # OAuth 1.0a specific
        self._request_token_url: Optional[str] = None
        self._access_token_url: Optional[str] = None
        
        # Token storage
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._request_token: Optional[str] = None
        self._request_token_secret: Optional[str] = None
        
        # Authentication state
        self._is_authenticated: bool = False
        self._auth_state: Optional[str] = None
        
        # Callback handlers
        self._auth_success_callback: Optional[Callable] = None
        self._auth_error_callback: Optional[Callable] = None
    
    async def initialize(self, context: ComponentContext) -> bool:
        """
        Initialize OAuth authentication component.
        
        Args:
            context: Component context
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Load OAuth configuration from context
            config = context.config_manager.get_config(context.environment) if context.config_manager else {}
            
            self._oauth_version = config.get('oauth_version', '2.0')
            self._client_id = config.get('oauth_client_id')
            self._client_secret = config.get('oauth_client_secret')
            self._redirect_uri = config.get('oauth_redirect_uri')
            self._scope = config.get('oauth_scope')
            
            if self._oauth_version == "2.0":
                self._authorization_url = config.get('oauth_authorization_url')
                self._token_url = config.get('oauth_token_url')
                self._refresh_token_url = config.get('oauth_refresh_token_url')
            else:  # OAuth 1.0a
                self._request_token_url = config.get('oauth_request_token_url')
                self._access_token_url = config.get('oauth_access_token_url')
                self._authorization_url = config.get('oauth_authorization_url')
            
            # Validate required configuration
            if not self._client_id or not self._client_secret:
                self._log_operation("initialize", "OAuth client ID and secret are required", "error")
                return False
            
            self._log_operation("initialize", f"OAuth {self._oauth_version} component initialized")
            return True
            
        except Exception as e:
            self._log_operation("initialize", f"OAuth initialization failed: {str(e)}", "error")
            return False
    
    async def execute(self, **kwargs) -> ComponentResult:
        """
        Execute OAuth authentication flow.
        
        Args:
            **kwargs: Authentication parameters
            
        Returns:
            Authentication result
        """
        try:
            start_time = datetime.utcnow()
            
            # Check if already authenticated
            if self._is_authenticated and self._is_token_valid():
                return ComponentResult(
                    success=True,
                    data={
                        'authenticated': True,
                        'access_token': self._access_token,
                        'expires_at': self._token_expires_at.isoformat() if self._token_expires_at else None
                    },
                    execution_time_ms=0
                )
            
            # Perform authentication based on OAuth version
            if self._oauth_version == "2.0":
                auth_result = await self._oauth2_flow(**kwargs)
            else:
                auth_result = await self._oauth1_flow(**kwargs)
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            return ComponentResult(
                success=auth_result['success'],
                data=auth_result,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            self._log_operation("execute", f"OAuth authentication failed: {str(e)}", "error")
            return ComponentResult(
                success=False,
                data={'error': str(e)},
                errors=[str(e)]
            )
    
    async def _oauth2_flow(self, **kwargs) -> Dict[str, Any]:
        """Execute OAuth 2.0 authentication flow."""
        try:
            # Check if we have a refresh token
            if self._refresh_token and not self._is_token_valid():
                refresh_result = await self._refresh_access_token()
                if refresh_result['success']:
                    return refresh_result
            
            # Generate authorization URL
            auth_url = await self._generate_oauth2_auth_url()
            
            # In a real implementation, you would redirect the user to auth_url
            # For scraping, we might need to handle this differently
            self._log_operation("_oauth2_flow", f"Authorization URL generated: {auth_url}")
            
            # For demonstration, we'll simulate getting authorization code
            auth_code = kwargs.get('authorization_code')
            if not auth_code:
                return {
                    'success': False,
                    'error': 'Authorization code required',
                    'authorization_url': auth_url
                }
            
            # Exchange authorization code for access token
            token_result = await self._exchange_code_for_token(auth_code)
            
            return token_result
            
        except Exception as e:
            self._log_operation("_oauth2_flow", f"OAuth 2.0 flow failed: {str(e)}", "error")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _oauth1_flow(self, **kwargs) -> Dict[str, Any]:
        """Execute OAuth 1.0a authentication flow."""
        try:
            # Step 1: Get request token
            request_token_result = await self._get_request_token()
            if not request_token_result['success']:
                return request_token_result
            
            # Step 2: Generate authorization URL
            auth_url = await self._generate_oauth1_auth_url()
            
            self._log_operation("_oauth1_flow", f"Authorization URL generated: {auth_url}")
            
            # Step 3: Get authorization verifier
            verifier = kwargs.get('verifier')
            if not verifier:
                return {
                    'success': False,
                    'error': 'Authorization verifier required',
                    'authorization_url': auth_url
                }
            
            # Step 4: Exchange request token for access token
            token_result = await self._exchange_request_token_for_access_token(verifier)
            
            return token_result
            
        except Exception as e:
            self._log_operation("_oauth1_flow", f"OAuth 1.0a flow failed: {str(e)}", "error")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _generate_oauth2_auth_url(self) -> str:
        """Generate OAuth 2.0 authorization URL."""
        if not self._authorization_url:
            raise ValueError("Authorization URL not configured")
        
        params = {
            'client_id': self._client_id,
            'redirect_uri': self._redirect_uri,
            'response_type': 'code',
            'scope': self._scope or '',
            'state': self._generate_state()
        }
        
        return f"{self._authorization_url}?{urlencode(params)}"
    
    async def _generate_oauth1_auth_url(self) -> str:
        """Generate OAuth 1.0a authorization URL."""
        if not self._authorization_url or not self._request_token:
            raise ValueError("Authorization URL or request token not available")
        
        params = {
            'oauth_token': self._request_token,
            'oauth_callback': self._redirect_uri
        }
        
        return f"{self._authorization_url}?{urlencode(params)}"
    
    async def _exchange_code_for_token(self, auth_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        try:
            if not self._token_url:
                raise ValueError("Token URL not configured")
            
            # Prepare token request data
            token_data = {
                'grant_type': 'authorization_code',
                'client_id': self._client_id,
                'client_secret': self._client_secret,
                'code': auth_code,
                'redirect_uri': self._redirect_uri
            }
            
            # In a real implementation, make HTTP request to token URL
            # For demonstration, we'll simulate the response
            simulated_response = {
                'access_token': 'simulated_access_token_' + secrets.token_hex(16),
                'refresh_token': 'simulated_refresh_token_' + secrets.token_hex(16),
                'expires_in': 3600,
                'token_type': 'Bearer'
            }
            
            # Store tokens
            self._access_token = simulated_response['access_token']
            self._refresh_token = simulated_response.get('refresh_token')
            self._token_expires_at = datetime.utcnow() + timedelta(seconds=simulated_response['expires_in'])
            self._is_authenticated = True
            
            self._log_operation("_exchange_code_for_token", "Access token obtained successfully")
            
            # Call success callback if set
            if self._auth_success_callback:
                await self._auth_success_callback(simulated_response)
            
            return {
                'success': True,
                'access_token': self._access_token,
                'refresh_token': self._refresh_token,
                'expires_at': self._token_expires_at.isoformat(),
                'token_type': simulated_response['token_type']
            }
            
        except Exception as e:
            self._log_operation("_exchange_code_for_token", f"Token exchange failed: {str(e)}", "error")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _get_request_token(self) -> Dict[str, Any]:
        """Get OAuth 1.0a request token."""
        try:
            if not self._request_token_url:
                raise ValueError("Request token URL not configured")
            
            # Generate OAuth 1.0a parameters
            oauth_params = {
                'oauth_consumer_key': self._client_id,
                'oauth_nonce': secrets.token_hex(16),
                'oauth_signature_method': 'HMAC-SHA1',
                'oauth_timestamp': str(int(datetime.utcnow().timestamp())),
                'oauth_version': '1.0',
                'oauth_callback': self._redirect_uri
            }
            
            # In a real implementation, sign the request and make HTTP call
            # For demonstration, we'll simulate the response
            simulated_response = {
                'oauth_token': 'simulated_request_token_' + secrets.token_hex(16),
                'oauth_token_secret': 'simulated_request_secret_' + secrets.token_hex(16),
                'oauth_callback_confirmed': 'true'
            }
            
            self._request_token = simulated_response['oauth_token']
            self._request_token_secret = simulated_response['oauth_token_secret']
            
            self._log_operation("_get_request_token", "Request token obtained successfully")
            
            return {
                'success': True,
                'request_token': self._request_token,
                'request_token_secret': self._request_token_secret
            }
            
        except Exception as e:
            self._log_operation("_get_request_token", f"Request token failed: {str(e)}", "error")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _exchange_request_token_for_access_token(self, verifier: str) -> Dict[str, Any]:
        """Exchange OAuth 1.0a request token for access token."""
        try:
            if not self._access_token_url:
                raise ValueError("Access token URL not configured")
            
            # Prepare access token request data
            token_data = {
                'oauth_consumer_key': self._client_id,
                'oauth_token': self._request_token,
                'oauth_verifier': verifier,
                'oauth_signature_method': 'HMAC-SHA1',
                'oauth_timestamp': str(int(datetime.utcnow().timestamp())),
                'oauth_nonce': secrets.token_hex(16),
                'oauth_version': '1.0'
            }
            
            # In a real implementation, sign the request and make HTTP call
            # For demonstration, we'll simulate the response
            simulated_response = {
                'oauth_token': 'simulated_access_token_' + secrets.token_hex(16),
                'oauth_token_secret': 'simulated_access_secret_' + secrets.token_hex(16),
                'oauth_expires_in': '3600'
            }
            
            # Store access token
            self._access_token = simulated_response['oauth_token']
            self._token_expires_at = datetime.utcnow() + timedelta(seconds=int(simulated_response['oauth_expires_in']))
            self._is_authenticated = True
            
            self._log_operation("_exchange_request_token_for_access_token", "Access token obtained successfully")
            
            # Call success callback if set
            if self._auth_success_callback:
                await self._auth_success_callback(simulated_response)
            
            return {
                'success': True,
                'access_token': self._access_token,
                'expires_at': self._token_expires_at.isoformat()
            }
            
        except Exception as e:
            self._log_operation("_exchange_request_token_for_access_token", f"Access token exchange failed: {str(e)}", "error")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _refresh_access_token(self) -> Dict[str, Any]:
        """Refresh OAuth 2.0 access token."""
        try:
            if not self._refresh_token_url or not self._refresh_token:
                return {
                    'success': False,
                    'error': 'Refresh token not available'
                }
            
            # Prepare refresh token request data
            refresh_data = {
                'grant_type': 'refresh_token',
                'refresh_token': self._refresh_token,
                'client_id': self._client_id,
                'client_secret': self._client_secret
            }
            
            # In a real implementation, make HTTP request to refresh token URL
            # For demonstration, we'll simulate the response
            simulated_response = {
                'access_token': 'refreshed_access_token_' + secrets.token_hex(16),
                'expires_in': 3600,
                'token_type': 'Bearer'
            }
            
            # Update access token
            self._access_token = simulated_response['access_token']
            self._token_expires_at = datetime.utcnow() + timedelta(seconds=simulated_response['expires_in'])
            
            self._log_operation("_refresh_access_token", "Access token refreshed successfully")
            
            return {
                'success': True,
                'access_token': self._access_token,
                'expires_at': self._token_expires_at.isoformat()
            }
            
        except Exception as e:
            self._log_operation("_refresh_access_token", f"Token refresh failed: {str(e)}", "error")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _is_token_valid(self) -> bool:
        """Check if the current access token is valid."""
        if not self._access_token:
            return False
        
        if self._token_expires_at:
            return datetime.utcnow() < self._token_expires_at
        
        return True
    
    def _generate_state(self) -> str:
        """Generate OAuth state parameter."""
        self._auth_state = secrets.token_hex(16)
        return self._auth_state
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests."""
        if not self._is_authenticated or not self._access_token:
            return {}
        
        if self._oauth_version == "2.0":
            return {
                'Authorization': f'Bearer {self._access_token}'
            }
        else:  # OAuth 1.0a
            return {
                'Authorization': f'OAuth oauth_token="{self._access_token}"'
            }
    
    def is_authenticated(self) -> bool:
        """Check if the component is authenticated."""
        return self._is_authenticated and self._is_token_valid()
    
    def set_auth_callbacks(self, success_callback: Callable = None, error_callback: Callable = None):
        """
        Set authentication callback functions.
        
        Args:
            success_callback: Function to call on successful authentication
            error_callback: Function to call on authentication error
        """
        self._auth_success_callback = success_callback
        self._auth_error_callback = error_callback
    
    def configure_oauth(
        self,
        oauth_version: str = "2.0",
        client_id: str = None,
        client_secret: str = None,
        redirect_uri: str = None,
        scope: str = None,
        authorization_url: str = None,
        token_url: str = None,
        refresh_token_url: str = None,
        request_token_url: str = None,
        access_token_url: str = None
    ) -> None:
        """
        Configure OAuth settings.
        
        Args:
            oauth_version: OAuth version ("1.0a" or "2.0")
            client_id: OAuth client ID
            client_secret: OAuth client secret
            redirect_uri: OAuth redirect URI
            scope: OAuth scope
            authorization_url: Authorization endpoint URL
            token_url: Token endpoint URL
            refresh_token_url: Refresh token endpoint URL
            request_token_url: Request token endpoint URL (OAuth 1.0a)
            access_token_url: Access token endpoint URL (OAuth 1.0a)
        """
        self._oauth_version = oauth_version
        if client_id is not None:
            self._client_id = client_id
        if client_secret is not None:
            self._client_secret = client_secret
        if redirect_uri is not None:
            self._redirect_uri = redirect_uri
        if scope is not None:
            self._scope = scope
        if authorization_url is not None:
            self._authorization_url = authorization_url
        if token_url is not None:
            self._token_url = token_url
        if refresh_token_url is not None:
            self._refresh_token_url = refresh_token_url
        if request_token_url is not None:
            self._request_token_url = request_token_url
        if access_token_url is not None:
            self._access_token_url = access_token_url
    
    def get_oauth_configuration(self) -> Dict[str, Any]:
        """Get current OAuth configuration."""
        return {
            'oauth_version': self._oauth_version,
            'client_id': self._client_id,
            'redirect_uri': self._redirect_uri,
            'scope': self._scope,
            'authorization_url': self._authorization_url,
            'token_url': self._token_url,
            'refresh_token_url': self._refresh_token_url,
            'request_token_url': self._request_token_url,
            'access_token_url': self._access_token_url,
            'is_authenticated': self._is_authenticated,
            'token_expires_at': self._token_expires_at.isoformat() if self._token_expires_at else None,
            **self.get_configuration()
        }
    
    async def cleanup(self) -> None:
        """Clean up OAuth authentication component."""
        try:
            # Clear sensitive data
            self._access_token = None
            self._refresh_token = None
            self._request_token = None
            self._request_token_secret = None
            self._client_secret = None
            self._is_authenticated = False
            
            self._log_operation("cleanup", "OAuth authentication component cleaned up")
            
        except Exception as e:
            self._log_operation("cleanup", f"OAuth cleanup failed: {str(e)}", "error")
