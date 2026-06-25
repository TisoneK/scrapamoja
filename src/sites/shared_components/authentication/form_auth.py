"""
Shared form-based authentication component for reusable authentication across sites.

This module provides form-based authentication functionality that can be easily
integrated into any site scraper with username/password login forms.
"""

from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timedelta
import asyncio
import json
import re
from urllib.parse import urlparse

from src.sites.base.component_interface import BaseComponent, ComponentContext, ComponentResult


class FormAuthenticationComponent(BaseComponent):
    """Shared form-based authentication component for cross-site usage."""
    
    def __init__(
        self,
        component_id: str = "shared_form_auth",
        name: str = "Shared Form Authentication Component",
        version: str = "1.0.0",
        description: str = "Reusable form-based authentication for multiple sites"
    ):
        """
        Initialize shared form authentication component.
        
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
        
        # Form configurations for different sites
        self._site_configs: Dict[str, Dict[str, Any]] = {}
        
        # Authentication state per site
        self._auth_states: Dict[str, Dict[str, Any]] = {}
        
        # Session storage per site
        self._sessions: Dict[str, Dict[str, Any]] = {}
        
        # Callback handlers
        self._success_callbacks: Dict[str, List[Callable]] = {}
        self._error_callbacks: Dict[str, List[Callable]] = {}
        
        # Component metadata
        self._supported_sites = [
            'linkedin', 'facebook', 'twitter', 'instagram', 'reddit',
            'github', 'stackoverflow', 'amazon', 'ebay', 'craigslist'
        ]
        
        # Common form field patterns
        self._username_patterns = [
            'username', 'email', 'user', 'login', 'user_email', 'session_key',
            'signin_username', 'login_username', 'auth_user', 'account'
        ]
        
        self._password_patterns = [
            'password', 'passwd', 'pass', 'pwd', 'user_password',
            'login_password', 'signin_password', 'auth_pass'
        ]
        
        self._submit_patterns = [
            'submit', 'login', 'signin', 'sign-in', 'log-in', 'auth',
            'login_button', 'signin_button', 'submit_button', 'continue'
        ]
    
    async def initialize(self, context: ComponentContext) -> bool:
        """
        Initialize shared form authentication component.
        
        Args:
            context: Component context
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Load form authentication configurations from context
            config = context.config_manager.get_config(context.environment) if context.config_manager else {}
            
            # Initialize default site configurations
            await self._initialize_default_configs()
            
            # Load custom site configurations
            custom_configs = config.get('form_auth_site_configs', {})
            for site, site_config in custom_configs.items():
                self.register_site(site, site_config)
            
            self._log_operation("initialize", f"Shared form auth component initialized with {len(self._site_configs)} site configurations")
            return True
            
        except Exception as e:
            self._log_operation("initialize", f"Shared form auth initialization failed: {str(e)}", "error")
            return False
    
    async def execute(self, **kwargs) -> ComponentResult:
        """
        Execute form-based authentication for a specific site.
        
        Args:
            **kwargs: Authentication parameters including 'site', 'page', 'username', 'password'
            
        Returns:
            Authentication result
        """
        try:
            start_time = datetime.utcnow()
            
            # Extract parameters
            site = kwargs.get('site')
            page = kwargs.get('page')
            username = kwargs.get('username')
            password = kwargs.get('password')
            auto_detect = kwargs.get('auto_detect', True)
            wait_time = kwargs.get('wait_time', 3000)
            
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
            
            if not username or not password:
                return ComponentResult(
                    success=False,
                    data={'error': 'Username and password are required'},
                    errors=['Username and password are required']
                )
            
            # Check if already authenticated
            if self._is_authenticated(site):
                return ComponentResult(
                    success=True,
                    data={
                        'site': site,
                        'authenticated': True,
                        'session_info': self._sessions[site],
                        'message': 'Already authenticated'
                    },
                    execution_time_ms=0
                )
            
            # Perform authentication
            auth_result = await self._authenticate(site, page, username, password, auto_detect, wait_time)
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            return ComponentResult(
                success=auth_result['success'],
                data={
                    'site': site,
                    'username': username,
                    **auth_result
                },
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            self._log_operation("execute", f"Form authentication failed: {str(e)}", "error")
            return ComponentResult(
                success=False,
                data={'error': str(e)},
                errors=[str(e)]
            )
    
    def register_site(self, site: str, config: Dict[str, Any]) -> None:
        """
        Register form authentication configuration for a site.
        
        Args:
            site: Site identifier
            config: Form authentication configuration
        """
        self._site_configs[site] = {
            'login_url': config.get('login_url'),
            'username_selector': config.get('username_selector'),
            'password_selector': config.get('password_selector'),
            'submit_selector': config.get('submit_selector'),
            'success_indicators': config.get('success_indicators', []),
            'failure_indicators': config.get('failure_indicators', []),
            'wait_for_selector': config.get('wait_for_selector'),
            'additional_fields': config.get('additional_fields', {}),
            'required_headers': config.get('required_headers', {}),
            'csrf_protection': config.get('csrf_protection', True),
            'session_timeout': config.get('session_timeout', 3600)
        }
        
        self._log_operation("register_site", f"Registered form auth configuration for site: {site}")
    
    async def _initialize_default_configs(self) -> None:
        """Initialize default form authentication configurations for common sites."""
        default_configs = {
            'linkedin': {
                'login_url': 'https://www.linkedin.com/login',
                'username_selector': 'input[name="session_key"]',
                'password_selector': 'input[name="session_password"]',
                'submit_selector': 'button[type="submit"]',
                'success_indicators': ['.feed-container', '.global-nav__primary-link'],
                'failure_indicators': ['.alert-error', '.form-error'],
                'csrf_protection': True
            },
            'github': {
                'login_url': 'https://github.com/login',
                'username_selector': 'input[name="login"]',
                'password_selector': 'input[name="password"]',
                'submit_selector': 'input[type="submit"]',
                'success_indicators': ['.Header-link--profile', '.user-profile-nav'],
                'failure_indicators': ['.flash-error', '.js-flash-alert'],
                'csrf_protection': True
            },
            'stackoverflow': {
                'login_url': 'https://stackoverflow.com/users/login',
                'username_selector': 'input[name="email"]',
                'password_selector': 'input[name="password"]',
                'submit_selector': 'button[id="submit-button"]',
                'success_indicators': ['.my-profile', '.top-bar'],
                'failure_indicators': ['.error-message', '.js-error'],
                'csrf_protection': True
            },
            'amazon': {
                'login_url': 'https://www.amazon.com/ap/signin',
                'username_selector': 'input[name="email"]',
                'password_selector': 'input[name="password"]',
                'submit_selector': 'input[name="signInSubmit"]',
                'success_indicators': ['#nav-tools', '.nav-line-1'],
                'failure_indicators': ['.a-alert-error', '.a-alert-warning'],
                'csrf_protection': True
            }
        }
        
        for site, config in default_configs.items():
            if site not in self._site_configs:
                self._site_configs[site] = config
    
    async def _authenticate(self, site: str, page, username: str, password: str, auto_detect: bool, wait_time: int) -> Dict[str, Any]:
        """Perform form-based authentication."""
        try:
            config = self._site_configs[site]
            
            # Navigate to login page if needed
            if config.get('login_url'):
                await page.goto(config['login_url'])
                await asyncio.sleep(1)  # Wait for page to load
            
            # Wait for login form to be ready
            if config.get('wait_for_selector'):
                await page.wait_for_selector(config['wait_for_selector'], timeout=10000)
            
            # Auto-detect form fields if not configured
            if auto_detect:
                detected_fields = await self._detect_form_fields(page)
                username_selector = config.get('username_selector') or detected_fields.get('username')
                password_selector = config.get('password_selector') or detected_fields.get('password')
                submit_selector = config.get('submit_selector') or detected_fields.get('submit')
            else:
                username_selector = config['username_selector']
                password_selector = config['password_selector']
                submit_selector = config['submit_selector']
            
            if not username_selector or not password_selector:
                return {
                    'success': False,
                    'error': 'Could not find username or password field',
                    'detected_fields': detected_fields if auto_detect else None
                }
            
            # Fill in form fields
            await self._fill_form_fields(page, config, username_selector, password_selector, username, password)
            
            # Handle additional fields if configured
            if config.get('additional_fields'):
                await self._fill_additional_fields(page, config['additional_fields'])
            
            # Submit form
            if submit_selector:
                await page.click(submit_selector)
            else:
                # Try to submit form by pressing Enter
                await page.press(password_selector, 'Enter')
            
            # Wait for authentication result
            await asyncio.sleep(wait_time / 1000.0)
            
            # Check authentication result
            auth_result = await self._check_authentication_result(page, config)
            
            if auth_result['success']:
                # Store session information
                self._sessions[site] = {
                    'authenticated_at': datetime.utcnow(),
                    'username': username,
                    'session_timeout': config.get('session_timeout', 3600),
                    'page_url': page.url
                }
                
                # Call success callbacks
                await self._call_success_callbacks(site, auth_result)
            
            return auth_result
            
        except Exception as e:
            self._log_operation("_authenticate", f"Form authentication failed for {site}: {str(e)}", "error")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _detect_form_fields(self, page) -> Dict[str, str]:
        """Auto-detect form fields on the page."""
        try:
            detected_fields = {}
            
            # Find username field
            for pattern in self._username_patterns:
                selector = f'input[type="text"][name*="{pattern}"], input[type="email"][name*="{pattern}"], input[name*="{pattern}"]'
                elements = await page.query_selector_all(selector)
                if elements:
                    detected_fields['username'] = selector
                    break
            
            # Find password field
            for pattern in self._password_patterns:
                selector = f'input[type="password"][name*="{pattern}"], input[name*="{pattern}"]'
                elements = await page.query_selector_all(selector)
                if elements:
                    detected_fields['password'] = selector
                    break
            
            # Find submit button
            for pattern in self._submit_patterns:
                selectors = [
                    f'button[type="submit"][name*="{pattern}"], button[name*="{pattern}"]',
                    f'input[type="submit"][name*="{pattern}"], input[name*="{pattern}"]',
                    f'button[type="submit"][class*="{pattern}"], button[class*="{pattern}"]'
                ]
                for selector in selectors:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        detected_fields['submit'] = selector
                        break
                if 'submit' in detected_fields:
                    break
            
            self._log_operation("_detect_form_fields", f"Detected form fields: {detected_fields}")
            return detected_fields
            
        except Exception as e:
            self._log_operation("_detect_form_fields", f"Form field detection failed: {str(e)}", "error")
            return {}
    
    async def _fill_form_fields(self, page, config: Dict[str, Any], username_selector: str, password_selector: str, username: str, password: str) -> None:
        """Fill in username and password fields."""
        try:
            # Clear and fill username field
            await page.fill(username_selector, '')
            await page.type(username_selector, username, delay=100)
            
            # Clear and fill password field
            await page.fill(password_selector, '')
            await page.type(password_selector, password, delay=100)
            
            # Handle CSRF protection if enabled
            if config.get('csrf_protection'):
                await self._handle_csrf_protection(page)
            
            self._log_operation("_fill_form_fields", "Form fields filled successfully")
            
        except Exception as e:
            self._log_operation("_fill_form_fields", f"Failed to fill form fields: {str(e)}", "error")
            raise
    
    async def _fill_additional_fields(self, page, additional_fields: Dict[str, Any]) -> None:
        """Fill in additional form fields."""
        try:
            for field_name, field_config in additional_fields.items():
                selector = field_config.get('selector')
                value = field_config.get('value')
                field_type = field_config.get('type', 'text')
                
                if selector and value is not None:
                    if field_type == 'text':
                        await page.fill(selector, value)
                    elif field_type == 'select':
                        await page.select_option(selector, value)
                    elif field_type == 'checkbox':
                        if value:
                            await page.check(selector)
                        else:
                            await page.uncheck(selector)
            
            self._log_operation("_fill_additional_fields", f"Filled {len(additional_fields)} additional fields")
            
        except Exception as e:
            self._log_operation("_fill_additional_fields", f"Failed to fill additional fields: {str(e)}", "error")
    
    async def _handle_csrf_protection(self, page) -> None:
        """Handle CSRF protection by extracting and preserving tokens."""
        try:
            # Look for common CSRF token selectors
            csrf_selectors = [
                'input[name="csrf_token"]',
                'input[name="csrfmiddlewaretoken"]',
                'input[name="_token"]',
                'input[name="authenticity_token"]',
                'meta[name="csrf-token"]'
            ]
            
            for selector in csrf_selectors:
                element = await page.query_selector(selector)
                if element:
                    # CSRF token is already in the form, no additional action needed
                    break
            
        except Exception as e:
            self._log_operation("_handle_csrf_protection", f"CSRF protection handling failed: {str(e)}", "error")
    
    async def _check_authentication_result(self, page, config: Dict[str, Any]) -> Dict[str, Any]:
        """Check if authentication was successful."""
        try:
            # Check for success indicators
            success_indicators = config.get('success_indicators', [])
            for indicator in success_indicators:
                element = await page.query_selector(indicator)
                if element:
                    return {
                        'success': True,
                        'message': 'Authentication successful',
                        'indicator': indicator,
                        'current_url': page.url
                    }
            
            # Check for failure indicators
            failure_indicators = config.get('failure_indicators', [])
            for indicator in failure_indicators:
                element = await page.query_selector(indicator)
                if element:
                    error_text = await element.text_content()
                    return {
                        'success': False,
                        'message': 'Authentication failed',
                        'error': error_text or 'Authentication error',
                        'indicator': indicator,
                        'current_url': page.url
                    }
            
            # If no clear indicators, check URL change
            current_url = page.url
            if 'login' not in current_url.lower() and 'signin' not in current_url.lower():
                return {
                    'success': True,
                    'message': 'Authentication successful (URL changed)',
                    'current_url': current_url
                }
            
            # Default to failure if unclear
            return {
                'success': False,
                'message': 'Authentication result unclear',
                'current_url': current_url
            }
            
        except Exception as e:
            self._log_operation("_check_authentication_result", f"Failed to check authentication result: {str(e)}", "error")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _is_authenticated(self, site: str) -> bool:
        """Check if site is authenticated."""
        if site not in self._sessions:
            return False
        
        session = self._sessions[site]
        authenticated_at = session.get('authenticated_at')
        session_timeout = session.get('session_timeout', 3600)
        
        if not authenticated_at:
            return False
        
        # Check if session has expired
        elapsed = (datetime.utcnow() - authenticated_at).total_seconds()
        return elapsed < session_timeout
    
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
        """Get form authentication configuration for a site."""
        return self._site_configs.get(site)
    
    def get_session_info(self, site: str) -> Optional[Dict[str, Any]]:
        """Get session information for a site."""
        if site not in self._sessions:
            return None
        
        session = self._sessions[site].copy()
        if 'authenticated_at' in session and isinstance(session['authenticated_at'], datetime):
            session['authenticated_at'] = session['authenticated_at'].isoformat()
        
        return session
    
    def logout(self, site: str) -> bool:
        """Logout from a site."""
        try:
            if site in self._sessions:
                del self._sessions[site]
            
            if site in self._auth_states:
                del self._auth_states[site]
            
            self._log_operation("logout", f"Logged out from site: {site}")
            return True
            
        except Exception as e:
            self._log_operation("logout", f"Logout failed for {site}: {str(e)}", "error")
            return False
    
    async def cleanup(self) -> None:
        """Clean up shared form authentication component."""
        try:
            # Clear all sessions and states
            self._sessions.clear()
            self._auth_states.clear()
            self._success_callbacks.clear()
            self._error_callbacks.clear()
            
            self._log_operation("cleanup", "Shared form auth component cleaned up")
            
        except Exception as e:
            self._log_operation("cleanup", f"Shared form auth cleanup failed: {str(e)}", "error")


# Factory function for easy component creation
def create_form_auth_component() -> FormAuthenticationComponent:
    """Create a shared form authentication component."""
    return FormAuthenticationComponent()


# Component metadata for discovery
COMPONENT_METADATA = {
    'id': 'shared_form_auth',
    'name': 'Shared Form Authentication Component',
    'version': '1.0.0',
    'type': 'AUTHENTICATION',
    'description': 'Reusable form-based authentication for multiple sites',
    'supported_sites': ['linkedin', 'facebook', 'twitter', 'instagram', 'reddit', 'github', 'stackoverflow', 'amazon', 'ebay', 'craigslist'],
    'features': [
        'multi_site_support',
        'auto_field_detection',
        'csrf_protection',
        'session_management',
        'callback_system',
        'additional_fields'
    ],
    'dependencies': [],
    'configuration_required': ['login_url'],
    'optional_configuration': ['username_selector', 'password_selector', 'submit_selector', 'success_indicators', 'failure_indicators']
}
