"""
Login flow template for the modular site scraper template.

This module provides a template for implementing login functionality
with common authentication patterns and security considerations.
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import asyncio

from .base_flow import BaseTemplateFlow
from src.sites.base.component_interface import ComponentResult


class LoginFlow(BaseTemplateFlow):
    """Login flow template with common authentication functionality."""
    
    def __init__(
        self,
        component_id: str = "login_flow",
        name: str = "Login Flow",
        version: str = "1.0.0",
        description: str = "Handles user authentication with configurable login patterns",
        page: Any = None,
        selector_engine: Any = None
    ):
        """
        Initialize login flow.
        
        Args:
            component_id: Unique identifier for the flow
            name: Human-readable name for the flow
            version: Flow version
            description: Flow description
            page: Playwright page object
            selector_engine: Selector engine instance
        """
        super().__init__(
            component_id=component_id,
            name=name,
            version=version,
            description=description,
            flow_type="LOGIN",
            page=page,
            selector_engine=selector_engine
        )
        
        # Login-specific configuration
        self._username_selector: str = "username_input"
        self._password_selector: str = "password_input"
        self._login_button_selector: str = "login_button"
        self._logout_button_selector: str = "logout_button"
        self._error_message_selector: str = "error_message"
        self._success_indicator_selector: str = "login_success"
        self._login_url: Optional[str] = None
        self._max_login_attempts: int = 3
        self._login_delay_ms: int = 1000
        self._stealth_mode: bool = True
        
        # Configure success and error indicators
        self._success_indicators = [
            "login_success",
            "dashboard",
            "welcome",
            "profile"
        ]
        
        self._error_indicators = [
            "error_message",
            "invalid",
            "failed",
            "incorrect"
        ]
    
    async def _execute_flow_logic(self, **kwargs) -> Dict[str, Any]:
        """
        Execute login flow logic.
        
        Args:
            **kwargs: Login parameters including 'username', 'password', etc.
            
        Returns:
            Login execution result
        """
        try:
            # Extract login parameters
            username = kwargs.get('username', '')
            password = kwargs.get('password', '')
            login_url = kwargs.get('login_url', self._login_url)
            max_attempts = kwargs.get('max_attempts', self._max_login_attempts)
            
            if not username or not password:
                raise ValueError("Username and password are required")
            
            # Navigate to login page if URL provided
            if login_url:
                await self.navigate_to_url(login_url)
                await self.wait_for_page_load()
            
            # Perform login with retry logic
            login_result = await self._perform_login_with_retry(
                username, password, max_attempts
            )
            
            # Verify login success
            login_verified = await self._verify_login_success()
            
            # Extract login metadata
            login_metadata = await self._extract_login_metadata()
            
            return {
                'success': login_result['success'] and login_verified,
                'username': username,
                'attempts': login_result['attempts'],
                'login_result': login_result,
                'verified': login_verified,
                'metadata': login_metadata,
                'timestamp': datetime.utcnow().isoformat(),
                'url': self._flow_state.current_url if self._flow_state else None
            }
            
        except Exception as e:
            self._log_operation("_execute_flow_logic", f"Login failed: {str(e)}", "error")
            return {
                'success': False,
                'error': str(e),
                'username': kwargs.get('username', ''),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def _perform_login_with_retry(
        self,
        username: str,
        password: str,
        max_attempts: int
    ) -> Dict[str, Any]:
        """
        Perform login with retry logic.
        
        Args:
            username: Username
            password: Password
            max_attempts: Maximum number of attempts
            
        Returns:
            Login result with attempt information
        """
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                self._log_operation(
                    "_perform_login_with_retry",
                    f"Login attempt {attempt + 1}/{max_attempts}"
                )
                
                # Perform single login attempt
                login_success = await self._perform_single_login(username, password)
                
                if login_success:
                    self._log_operation(
                        "_perform_login_with_retry",
                        f"Login successful on attempt {attempt + 1}"
                    )
                    return {
                        'success': True,
                        'attempts': attempt + 1,
                        'last_error': None
                    }
                
                # Wait before retry (with exponential backoff)
                if attempt < max_attempts - 1:
                    delay = self._login_delay_ms * (2 ** attempt)
                    await asyncio.sleep(delay / 1000.0)
                
            except Exception as e:
                last_error = str(e)
                self._log_operation(
                    "_perform_login_with_retry",
                    f"Login attempt {attempt + 1} failed: {last_error}",
                    "error"
                )
                
                if attempt < max_attempts - 1:
                    delay = self._login_delay_ms * (2 ** attempt)
                    await asyncio.sleep(delay / 1000.0)
        
        return {
            'success': False,
            'attempts': max_attempts,
            'last_error': last_error
        }
    
    async def _perform_single_login(self, username: str, password: str) -> bool:
        """
        Perform a single login attempt.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            True if login successful, False otherwise
        """
        try:
            # Apply stealth mode if enabled
            if self._stealth_mode:
                await self._apply_stealth_mode()
            
            # Fill username field
            if not await self.fill_form(self._username_selector, username):
                raise Exception("Failed to fill username field")
            
            # Wait a moment to simulate human typing
            await asyncio.sleep(0.5)
            
            # Fill password field
            if not await self.fill_form(self._password_selector, password):
                raise Exception("Failed to fill password field")
            
            # Wait a moment before submitting
            await asyncio.sleep(0.5)
            
            # Submit login
            if not await self._submit_login():
                raise Exception("Failed to submit login")
            
            # Wait for login to process
            await asyncio.sleep(self._login_delay_ms / 1000.0)
            
            return True
            
        except Exception as e:
            self._log_operation("_perform_single_login", f"Single login attempt failed: {str(e)}", "error")
            return False
    
    async def _apply_stealth_mode(self) -> None:
        """Apply stealth mode techniques to avoid detection."""
        try:
            # Random mouse movements
            await self._page.mouse.move(
                self._page.viewport_size['width'] // 2,
                self._page.viewport_size['height'] // 2
            )
            
            # Random delays
            await asyncio.sleep(0.1 + (hash(datetime.utcnow().isoformat()) % 5) / 10)
            
            # Set realistic user agent if not already set
            user_agent = await self._page.evaluate("navigator.userAgent")
            if "Headless" in user_agent or "Playwright" in user_agent:
                await self._page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                })
            
            self._log_operation("_apply_stealth_mode", "Stealth mode applied")
            
        except Exception as e:
            self._log_operation("_apply_stealth_mode", f"Failed to apply stealth mode: {str(e)}", "error")
    
    async def _submit_login(self) -> bool:
        """Submit the login form."""
        try:
            # Try clicking login button first
            login_button = await self.wait_for_element(self._login_button_selector, timeout_ms=5000)
            if login_button:
                await self.click_element(self._login_button_selector)
                self._log_operation("_submit_login", "Login submitted via button click")
                return True
            
            # Fallback: press Enter in password field
            password_field = await self.wait_for_element(self._password_selector)
            if password_field:
                await password_field.press('Enter')
                self._log_operation("_submit_login", "Login submitted via Enter key")
                return True
            
            return False
            
        except Exception as e:
            self._log_operation("_submit_login", f"Failed to submit login: {str(e)}", "error")
            return False
    
    async def _verify_login_success(self) -> bool:
        """Verify that login was successful."""
        try:
            # Check for success indicators
            for indicator in self._success_indicators:
                element = await self.wait_for_element(indicator, timeout_ms=3000)
                if element:
                    self._log_operation("_verify_login_success", f"Login verified via indicator: {indicator}")
                    return True
            
            # Check for error indicators
            for indicator in self._error_indicators:
                element = await self.wait_for_element(indicator, timeout_ms=2000)
                if element:
                    self._log_operation("_verify_login_success", f"Login failed via indicator: {indicator}", "error")
                    return False
            
            # Check URL change (common success indicator)
            current_url = self._flow_state.current_url if self._flow_state else ""
            if "login" not in current_url.lower() and "auth" not in current_url.lower():
                self._log_operation("_verify_login_success", "Login verified via URL change")
                return True
            
            # Default to success if no clear indicators found
            self._log_operation("_verify_login_success", "Login verification inconclusive, assuming success")
            return True
            
        except Exception as e:
            self._log_operation("_verify_login_success", f"Login verification failed: {str(e)}", "error")
            return False
    
    async def _extract_login_metadata(self) -> Dict[str, Any]:
        """Extract metadata from login result page."""
        try:
            metadata = {}
            
            # Extract current URL
            metadata['current_url'] = self._flow_state.current_url if self._flow_state else None
            
            # Extract page title
            metadata['page_title'] = await self._page.title()
            
            # Check for welcome message or user info
            try:
                welcome_element = await self.wait_for_element("welcome_message", timeout_ms=2000)
                if welcome_element:
                    metadata['welcome_message'] = await welcome_element.text_content()
            except:
                pass
            
            # Check for user profile info
            try:
                profile_element = await self.wait_for_element("user_profile", timeout_ms=2000)
                if profile_element:
                    metadata['user_profile'] = await profile_element.text_content()
            except:
                pass
            
            # Check for session cookies
            cookies = await self._page.context.cookies()
            metadata['session_cookies'] = len(cookies)
            
            return metadata
            
        except Exception as e:
            self._log_operation("_extract_login_metadata", f"Failed to extract metadata: {str(e)}", "error")
            return {}
    
    async def logout(self) -> bool:
        """
        Logout from the current session.
        
        Returns:
            True if logout successful, False otherwise
        """
        try:
            # Look for logout button
            logout_button = await self.wait_for_element(self._logout_button_selector, timeout_ms=5000)
            if logout_button:
                await self.click_element(self._logout_button_selector)
                await self.wait_for_page_load()
                
                self._log_operation("logout", "Logout successful")
                return True
            
            # Try alternative logout methods
            return await self._try_alternative_logout()
            
        except Exception as e:
            self._log_operation("logout", f"Logout failed: {str(e)}", "error")
            return False
    
    async def _try_alternative_logout(self) -> bool:
        """Try alternative logout methods."""
        try:
            # Check for logout link
            logout_link = await self.wait_for_element("logout_link", timeout_ms=3000)
            if logout_link:
                await logout_link.click()
                await self.wait_for_page_load()
                return True
            
            # Navigate to logout URL if configured
            logout_url = getattr(self, '_logout_url', None)
            if logout_url:
                await self.navigate_to_url(logout_url)
                return True
            
            return False
            
        except Exception as e:
            self._log_operation("_try_alternative_logout", f"Alternative logout failed: {str(e)}", "error")
            return False
    
    async def is_logged_in(self) -> bool:
        """
        Check if currently logged in.
        
        Returns:
            True if logged in, False otherwise
        """
        try:
            # Check for login success indicators
            for indicator in self._success_indicators:
                element = await self.wait_for_element(indicator, timeout_ms=2000)
                if element:
                    return True
            
            # Check for logout button (indicates logged in)
            logout_button = await self.wait_for_element(self._logout_button_selector, timeout_ms=2000)
            if logout_button:
                return True
            
            return False
            
        except Exception as e:
            self._log_operation("is_logged_in", f"Failed to check login status: {str(e)}", "error")
            return False
    
    def configure_login(
        self,
        username_selector: Optional[str] = None,
        password_selector: Optional[str] = None,
        login_button_selector: Optional[str] = None,
        logout_button_selector: Optional[str] = None,
        error_message_selector: Optional[str] = None,
        success_indicator_selector: Optional[str] = None,
        login_url: Optional[str] = None,
        max_login_attempts: Optional[int] = None,
        login_delay_ms: Optional[int] = None,
        stealth_mode: Optional[bool] = None
    ) -> None:
        """
        Configure login-specific parameters.
        
        Args:
            username_selector: Selector for username input
            password_selector: Selector for password input
            login_button_selector: Selector for login button
            logout_button_selector: Selector for logout button
            error_message_selector: Selector for error messages
            success_indicator_selector: Selector for success indicators
            login_url: URL for login page
            max_login_attempts: Maximum login attempts
            login_delay_ms: Delay after login
            stealth_mode: Enable stealth mode
        """
        if username_selector is not None:
            self._username_selector = username_selector
        if password_selector is not None:
            self._password_selector = password_selector
        if login_button_selector is not None:
            self._login_button_selector = login_button_selector
        if logout_button_selector is not None:
            self._logout_button_selector = logout_button_selector
        if error_message_selector is not None:
            self._error_message_selector = error_message_selector
        if success_indicator_selector is not None:
            self._success_indicator_selector = success_indicator_selector
        if login_url is not None:
            self._login_url = login_url
        if max_login_attempts is not None:
            self._max_login_attempts = max_login_attempts
        if login_delay_ms is not None:
            self._login_delay_ms = login_delay_ms
        if stealth_mode is not None:
            self._stealth_mode = stealth_mode
    
    def get_login_configuration(self) -> Dict[str, Any]:
        """Get current login configuration."""
        return {
            'username_selector': self._username_selector,
            'password_selector': self._password_selector,
            'login_button_selector': self._login_button_selector,
            'logout_button_selector': self._logout_button_selector,
            'error_message_selector': self._error_message_selector,
            'success_indicator_selector': self._success_indicator_selector,
            'login_url': self._login_url,
            'max_login_attempts': self._max_login_attempts,
            'login_delay_ms': self._login_delay_ms,
            'stealth_mode': self._stealth_mode,
            **self.get_configuration()
        }
