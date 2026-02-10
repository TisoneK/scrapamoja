"""
Login authentication flow.

Handles traditional username/password authentication, form-based login,
and session management for websites requiring authentication.
"""

from src.sites.base.flow import BaseFlow


class LoginAuthenticationFlow(BaseFlow):
    """Login authentication flow."""
    
    async def login_with_credentials(self, username: str, password: str):
        """Login using username and password credentials."""
        # Navigate to login page
        await self.page.goto("https://example.com/login")
        await self.page.wait_for_load_state('networkidle')
        
        # Fill username field
        username_input = await self.selector_engine.find(
            self.page, "username_input"
        )
        
        if username_input:
            await username_input.clear()
            await username_input.type(username)
        
        # Fill password field
        password_input = await self.selector_engine.find(
            self.page, "password_input"
        )
        
        if password_input:
            await password_input.clear()
            await password_input.type(password)
        
        # Handle remember me checkbox (optional)
        remember_checkbox = await self.selector_engine.find(
            self.page, "remember_me_checkbox"
        )
        
        if remember_checkbox:
            await remember_checkbox.check()
        
        # Submit login form
        login_button = await self.selector_engine.find(
            self.page, "login_button"
        )
        
        if login_button:
            await login_button.click()
            await self.page.wait_for_load_state('networkidle')
        
        # Wait for login to complete
        await self._wait_for_login_completion()
    
    async def login_with_email(self, email: str, password: str):
        """Login using email and password."""
        # Navigate to login page
        await self.page.goto("https://example.com/login")
        await self.page.wait_for_load_state('networkidle')
        
        # Fill email field
        email_input = await self.selector_engine.find(
            self.page, "email_input"
        )
        
        if email_input:
            await email_input.clear()
            await email_input.type(email)
        
        # Fill password field
        password_input = await self.selector_engine.find(
            self.page, "password_input"
        )
        
        if password_input:
            await password_input.clear()
            await password_input.type(password)
        
        # Submit login form
        login_button = await self.selector_engine.find(
            self.page, "login_button"
        )
        
        if login_button:
            await login_button.click()
            await self.page.wait_for_load_state('networkidle')
        
        # Wait for login to complete
        await self._wait_for_login_completion()
    
    async def login_with_phone(self, phone: str, password: str):
        """Login using phone number and password."""
        # Navigate to login page
        await self.page.goto("https://example.com/login")
        await self.page.wait_for_load_state('networkidle')
        
        # Switch to phone login tab if needed
        phone_tab = await self.selector_engine.find(
            self.page, "phone_login_tab"
        )
        
        if phone_tab:
            await phone_tab.click()
            await self.page.wait_for_timeout(1000)
        
        # Fill phone field
        phone_input = await self.selector_engine.find(
            self.page, "phone_input"
        )
        
        if phone_input:
            await phone_input.clear()
            await phone_input.type(phone)
        
        # Fill password field
        password_input = await self.selector_engine.find(
            self.page, "password_input"
        )
        
        if password_input:
            await password_input.clear()
            await password_input.type(password)
        
        # Submit login form
        login_button = await self.selector_engine.find(
            self.page, "login_button"
        )
        
        if login_button:
            await login_button.click()
            await self.page.wait_for_load_state('networkidle')
        
        # Wait for login to complete
        await self._wait_for_login_completion()
    
    async def handle_two_factor_auth(self, code: str):
        """Handle two-factor authentication after initial login."""
        # Wait for 2FA input to appear
        await self.page.wait_for_selector("two_factor_input", timeout=10000)
        
        # Fill 2FA code
        two_factor_input = await self.selector_engine.find(
            self.page, "two_factor_input"
        )
        
        if two_factor_input:
            await two_factor_input.clear()
            await two_factor_input.type(code)
        
        # Submit 2FA code
        verify_button = await self.selector_engine.find(
            self.page, "verify_2fa_button"
        )
        
        if verify_button:
            await verify_button.click()
            await self.page.wait_for_load_state('networkidle')
        
        # Wait for verification to complete
        await self._wait_for_login_completion()
    
    async def handle_captcha(self):
        """Handle CAPTCHA challenge during login."""
        # Wait for CAPTCHA to load
        captcha_element = await self.selector_engine.find(
            self.page, "captcha_element"
        )
        
        if captcha_element:
            # For automated systems, you might need to use a CAPTCHA solving service
            # This is a placeholder for CAPTCHA handling logic
            await self.page.wait_for_timeout(5000)
            
            # Try to click "I'm not a robot" if present
            not_robot_checkbox = await self.selector_engine.find(
                self.page, "not_robot_checkbox"
            )
            
            if not_robot_checkbox:
                await not_robot_checkbox.click()
                await self.page.wait_for_timeout(2000)
    
    async def logout(self):
        """Logout from the current session."""
        # Click user menu/profile
        user_menu = await self.selector_engine.find(
            self.page, "user_menu_button"
        )
        
        if user_menu:
            await user_menu.click()
            await self.page.wait_for_timeout(1000)
        
        # Click logout button
        logout_button = await self.selector_engine.find(
            self.page, "logout_button"
        )
        
        if logout_button:
            await logout_button.click()
            await self.page.wait_for_load_state('networkidle')
    
    async def is_logged_in(self):
        """Check if user is currently logged in."""
        # Look for login status indicator
        login_indicator = await self.selector_engine.find(
            self.page, "login_status_indicator"
        )
        
        if login_indicator:
            status = await login_indicator.get_attribute('data-logged-in')
            return status == 'true'
        
        # Alternative: check for user menu presence
        user_menu = await self.selector_engine.find(
            self.page, "user_menu_button"
        )
        
        return user_menu is not None
    
    async def get_user_info(self):
        """Get current user information."""
        if not await self.is_logged_in():
            return None
        
        user_info = {}
        
        # Get username
        username_element = await self.selector_engine.find(
            self.page, "user_username"
        )
        user_info['username'] = await username_element.inner_text() if username_element else None
        
        # Get email
        email_element = await self.selector_engine.find(
            self.page, "user_email"
        )
        user_info['email'] = await email_element.inner_text() if email_element else None
        
        # Get user role/membership
        role_element = await self.selector_engine.find(
            self.page, "user_role"
        )
        user_info['role'] = await role_element.inner_text() if role_element else None
        
        return user_info
    
    async def _wait_for_login_completion(self):
        """Wait for login process to complete."""
        # Wait for either success indicator or error message
        try:
            await self.page.wait_for_selector(
                "login_success_indicator, login_error_message",
                timeout=15000
            )
            
            # Check if login was successful
            error_message = await self.selector_engine.find(
                self.page, "login_error_message"
            )
            
            if error_message:
                error_text = await error_message.inner_text()
                raise Exception(f"Login failed: {error_text}")
            
        except Exception as e:
            if "Login failed" in str(e):
                raise
            # Timeout might mean login succeeded but no clear indicator
            pass
    
    async def handle_login_error(self):
        """Handle login errors and extract error messages."""
        error_element = await self.selector_engine.find(
            self.page, "login_error_message"
        )
        
        if error_element:
            error_text = await error_element.inner_text()
            return error_text
        
        return None
