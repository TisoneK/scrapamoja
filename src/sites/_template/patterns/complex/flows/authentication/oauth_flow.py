"""
OAuth authentication flow.

Handles OAuth-based authentication including social media login,
third-party authentication, and token management.
"""

from src.sites.base.flow import BaseFlow
import time


class OAuthAuthenticationFlow(BaseFlow):
    """OAuth authentication flow."""
    
    async def login_with_google(self):
        """Login using Google OAuth."""
        # Click Google login button
        google_button = await self.selector_engine.find(
            self.page, "google_login_button"
        )
        
        if google_button:
            await google_button.click()
            
            # Wait for OAuth popup or redirect
            await self.page.wait_for_load_state('networkidle')
            
            # Handle Google OAuth flow
            await self._handle_google_oauth()
    
    async def login_with_facebook(self):
        """Login using Facebook OAuth."""
        # Click Facebook login button
        facebook_button = await self.selector_engine.find(
            self.page, "facebook_login_button"
        )
        
        if facebook_button:
            await facebook_button.click()
            
            # Wait for OAuth popup or redirect
            await self.page.wait_for_load_state('networkidle')
            
            # Handle Facebook OAuth flow
            await self._handle_facebook_oauth()
    
    async def login_with_twitter(self):
        """Login using Twitter OAuth."""
        # Click Twitter login button
        twitter_button = await self.selector_engine.find(
            self.page, "twitter_login_button"
        )
        
        if twitter_button:
            await twitter_button.click()
            
            # Wait for OAuth popup or redirect
            await self.page.wait_for_load_state('networkidle')
            
            # Handle Twitter OAuth flow
            await self._handle_twitter_oauth()
    
    async def login_with_github(self):
        """Login using GitHub OAuth."""
        # Click GitHub login button
        github_button = await self.selector_engine.find(
            self.page, "github_login_button"
        )
        
        if github_button:
            await github_button.click()
            
            # Wait for OAuth popup or redirect
            await self.page.wait_for_load_state('networkidle')
            
            # Handle GitHub OAuth flow
            await self._handle_github_oauth()
    
    async def login_with_custom_oauth(self, provider_name: str):
        """Login with a custom OAuth provider."""
        # Click custom OAuth button
        custom_button = await self.selector_engine.find(
            self.page, f"oauth_button_{provider_name.lower()}"
        )
        
        if custom_button:
            await custom_button.click()
            
            # Wait for OAuth popup or redirect
            await self.page.wait_for_load_state('networkidle')
            
            # Handle custom OAuth flow
            await self._handle_custom_oauth(provider_name)
    
    async def _handle_google_oauth(self):
        """Handle Google OAuth authentication flow."""
        # Wait for Google OAuth page
        await self.page.wait_for_selector("input[type='email']", timeout=10000)
        
        # Enter email
        email_input = await self.page.query_selector("input[type='email']")
        if email_input:
            await email_input.type("your-email@gmail.com")  # Replace with actual email
            await self.page.click("#identifierNext")
            
            # Wait for password page
            await self.page.wait_for_selector("input[type='password']", timeout=10000)
            
            # Enter password
            password_input = await self.page.query_selector("input[type='password']")
            if password_input:
                await password_input.type("your-password")  # Replace with actual password
                await self.page.click("#passwordNext")
        
        # Wait for redirect back to original site
        await self.page.wait_for_load_state('networkidle')
        
        # Handle any consent screens
        await self._handle_oauth_consent()
    
    async def _handle_facebook_oauth(self):
        """Handle Facebook OAuth authentication flow."""
        # Wait for Facebook OAuth page
        await self.page.wait_for_selector("#email", timeout=10000)
        
        # Enter email
        email_input = await self.page.query_selector("#email")
        if email_input:
            await email_input.type("your-facebook-email")  # Replace with actual email
        
        # Enter password
        password_input = await self.page.query_selector("#pass")
        if password_input:
            await password_input.type("your-facebook-password")  # Replace with actual password
        
        # Click login button
        login_button = await self.page.query_selector("button[name='login']")
        if login_button:
            await login_button.click()
        
        # Wait for redirect back to original site
        await self.page.wait_for_load_state('networkidle')
        
        # Handle any consent screens
        await self._handle_oauth_consent()
    
    async def _handle_twitter_oauth(self):
        """Handle Twitter OAuth authentication flow."""
        # Wait for Twitter OAuth page
        await self.page.wait_for_selector("input[name='session[username_or_email]']", timeout=10000)
        
        # Enter username/email
        username_input = await self.page.query_selector("input[name='session[username_or_email]']")
        if username_input:
            await username_input.type("your-twitter-username")  # Replace with actual username
        
        # Enter password
        password_input = await self.page.query_selector("input[name='session[password]']")
        if password_input:
            await password_input.type("your-twitter-password")  # Replace with actual password
        
        # Click login button
        login_button = await self.page.query_selector("div[data-testid='LoginForm_Login_Button']")
        if login_button:
            await login_button.click()
        
        # Wait for redirect back to original site
        await self.page.wait_for_load_state('networkidle')
        
        # Handle any consent screens
        await self._handle_oauth_consent()
    
    async def _handle_github_oauth(self):
        """Handle GitHub OAuth authentication flow."""
        # Wait for GitHub OAuth page
        await self.page.wait_for_selector("#login_field", timeout=10000)
        
        # Enter username
        username_input = await self.page.query_selector("#login_field")
        if username_input:
            await username_input.type("your-github-username")  # Replace with actual username
        
        # Enter password
        password_input = await self.page.query_selector("#password")
        if password_input:
            await password_input.type("your-github-password")  # Replace with actual password
        
        # Click login button
        login_button = await self.page.query_selector("input[type='submit']")
        if login_button:
            await login_button.click()
        
        # Wait for redirect back to original site
        await self.page.wait_for_load_state('networkidle')
        
        # Handle any consent screens
        await self._handle_oauth_consent()
    
    async def _handle_custom_oauth(self, provider_name: str):
        """Handle custom OAuth provider authentication."""
        # This is a generic handler for custom OAuth providers
        # Implementation would depend on the specific provider's OAuth flow
        
        # Wait for OAuth provider page to load
        await self.page.wait_for_timeout(3000)
        
        # Look for common OAuth input patterns
        username_selectors = [
            "input[type='email']",
            "input[name='username']",
            "input[name='login']",
            "#username",
            "#email"
        ]
        
        password_selectors = [
            "input[type='password']",
            "#password",
            "input[name='password']"
        ]
        
        # Try to find and fill username/email
        for selector in username_selectors:
            username_input = await self.page.query_selector(selector)
            if username_input:
                await username_input.type(f"your-{provider_name}-username")
                break
        
        # Try to find and fill password
        for selector in password_selectors:
            password_input = await self.page.query_selector(selector)
            if password_input:
                await password_input.type(f"your-{provider_name}-password")
                break
        
        # Try to find and click login button
        login_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            ".login-button",
            "#login-button"
        ]
        
        for selector in login_selectors:
            login_button = await self.page.query_selector(selector)
            if login_button:
                await login_button.click()
                break
        
        # Wait for redirect back to original site
        await self.page.wait_for_load_state('networkidle')
        
        # Handle any consent screens
        await self._handle_oauth_consent()
    
    async def _handle_oauth_consent(self):
        """Handle OAuth consent screens."""
        # Wait a moment for consent screen to potentially appear
        await self.page.wait_for_timeout(2000)
        
        # Look for consent/authorize buttons
        consent_selectors = [
            "button[data-testid='approve']",
            "button[name='authorize']",
            ".consent-button",
            "#authorize-button",
            "button[type='submit']"
        ]
        
        for selector in consent_selectors:
            consent_button = await self.page.query_selector(selector)
            if consent_button:
                await consent_button.click()
                await self.page.wait_for_load_state('networkidle')
                break
    
    async def revoke_oauth_access(self, provider: str):
        """Revoke OAuth access for a specific provider."""
        # Navigate to account settings
        await self.page.goto("https://example.com/account/settings")
        await self.page.wait_for_load_state('networkidle')
        
        # Find connected accounts section
        connected_accounts = await self.selector_engine.find(
            self.page, "connected_accounts_section"
        )
        
        if connected_accounts:
            # Find the specific provider
            provider_connection = await self.selector_engine.find(
                self.page, f"oauth_connection_{provider.lower()}"
            )
            
            if provider_connection:
                # Click disconnect/revoke button
                revoke_button = await self.selector_engine.find(
                    self.page, f"revoke_oauth_{provider.lower()}"
                )
                
                if revoke_button:
                    await revoke_button.click()
                    
                    # Handle confirmation dialog
                    confirm_button = await self.selector_engine.find(
                        self.page, "confirm_revoke_oauth"
                    )
                    
                    if confirm_button:
                        await confirm_button.click()
                        await self.page.wait_for_load_state('networkidle')
    
    async def get_connected_oauth_accounts(self):
        """Get list of connected OAuth accounts."""
        # Navigate to account settings
        await self.page.goto("https://example.com/account/settings")
        await self.page.wait_for_load_state('networkidle')
        
        connected_accounts = []
        
        # Find all connected OAuth accounts
        account_elements = await self.page.query_selector_all(".oauth-connection")
        
        for element in account_elements:
            account_info = {}
            
            # Get provider name
            provider = await element.query_selector(".oauth-provider")
            account_info['provider'] = await provider.inner_text() if provider else None
            
            # Get connected date
            connected_date = await element.query_selector(".oauth-connected-date")
            account_info['connected_date'] = await connected_date.inner_text() if connected_date else None
            
            # Get permissions scope
            permissions = await element.query_selector(".oauth-permissions")
            account_info['permissions'] = await permissions.inner_text() if permissions else None
            
            connected_accounts.append(account_info)
        
        return connected_accounts
