# Authentication Domain Documentation

The Authentication domain handles all aspects of user authentication, session management, and access control, from traditional login flows to OAuth integration.

## 🎯 Purpose

Authentication flows are responsible for:
- Traditional username/password authentication
- OAuth integration with third-party services
- Session management and token handling
- Security considerations and best practices
- Multi-factor authentication handling

## 📁 Domain Structure

```
flows/authentication/
├── __init__.py              # Domain registry
├── login_flow.py          # Traditional login flow
└── oauth_flow.py          # OAuth authentication flow
```

## 🔧 Core Concepts

### Base Authentication Flow
All authentication flows extend the base authentication functionality:

```python
from src.sites.base.flow import BaseFlow

class AuthenticationFlow(BaseFlow):
    def __init__(self):
        super().__init__()
        self.session_data = {}
        self.auth_tokens = {}
    
    async def is_authenticated(self) -> bool:
        """Check if user is currently authenticated."""
        # Look for authentication indicators
        auth_indicator = await self.selector_engine.find(
            self.page, "auth_status_indicator"
        )
        
        if auth_indicator:
            status = await auth_indicator.get_attribute('data-authenticated')
            return status == 'true'
        
        # Alternative: Check for user menu
        user_menu = await self.selector_engine.find(
            self.page, "user_menu_button"
        )
        
        return user_menu is not None
    
    async def get_session_info(self) -> dict:
        """Get current session information."""
        session_info = {}
        
        # Get user info if authenticated
        if await self.is_authenticated():
            session_info['user'] = await self.get_user_info()
            session_info['tokens'] = self.auth_tokens
            session_info['session_id'] = await self.get_session_id()
        
        return session_info
```

### Session Management
Handle authentication sessions and tokens:

```python
class SessionManager:
    def __init__(self):
        self.sessions = {}
        self.current_session = None
    
    async def create_session(self, auth_data: dict) -> str:
        """Create a new authentication session."""
        session_id = str(uuid.uuid4())
        
        session = {
            'id': session_id,
            'created_at': datetime.now(),
            'auth_data': auth_data,
            'last_activity': datetime.now()
        }
        
        self.sessions[session_id] = session
        self.current_session = session_id
        
        return session_id
    
    async def refresh_session(self, session_id: str) -> bool:
        """Refresh an existing session."""
        if session_id in self.sessions:
            self.sessions[session_id]['last_activity'] = datetime.now()
            return True
        return False
    
    async def is_session_valid(self, session_id: str) -> bool:
        """Check if session is still valid."""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        age = datetime.now() - session['last_activity']
        
        # Sessions expire after 24 hours
        return age.total_seconds() < 86400
```

## 📋 Authentication Patterns

### 1. Traditional Login Flow
Username and password authentication:

```python
class LoginAuthenticationFlow(AuthenticationFlow):
    async def login_with_credentials(self, username: str, password: str):
        """Login using username and password credentials."""
        try:
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
            
            # Store session data
            await self._store_session_data()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False
    
    async def login_with_email(self, email: str, password: str):
        """Login using email and password."""
        # Similar to username login but with email field
        await self.page.goto("https://example.com/login")
        await self.page.wait_for_load_state('networkidle')
        
        # Fill email field
        email_input = await self.selector_engine.find(
            self.page, "email_input"
        )
        
        if email_input:
            await email_input.clear()
            await email_input.type(email)
        
        # Rest of the login process...
        return await self._complete_login_process(password)
    
    async def handle_two_factor_auth(self, code: str):
        """Handle two-factor authentication after initial login."""
        try:
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
            
            return True
            
        except Exception as e:
            self.logger.error(f"2FA verification failed: {e}")
            return False
    
    async def logout(self):
        """Logout from the current session."""
        try:
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
            
            # Clear session data
            await self._clear_session_data()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Logout failed: {e}")
            return False
    
    async def _wait_for_login_completion(self):
        """Wait for login process to complete."""
        try:
            # Wait for either success indicator or error message
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
    
    async def _store_session_data(self):
        """Store authentication session data."""
        # Get authentication cookies
        cookies = await self.page.context.cookies()
        self.session_data['cookies'] = cookies
        
        # Get local storage data
        local_storage = await self.page.evaluate("() => Object.assign({}, localStorage)")
        self.session_data['local_storage'] = local_storage
        
        # Get session storage data
        session_storage = await self.page.evaluate("() => Object.assign({}, sessionStorage)")
        self.session_data['session_storage'] = session_storage
    
    async def _clear_session_data(self):
        """Clear authentication session data."""
        self.session_data = {}
        self.auth_tokens = {}
        
        # Clear cookies
        await self.page.context.clear_cookies()
        
        # Clear local storage
        await self.page.evaluate("() => localStorage.clear()")
        
        # Clear session storage
        await self.page.evaluate("() => sessionStorage.clear()")
```

### 2. OAuth Authentication Flow
Third-party authentication integration:

```python
class OAuthAuthenticationFlow(AuthenticationFlow):
    async def login_with_google(self):
        """Login using Google OAuth."""
        try:
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
                
                # Store OAuth tokens
                await self._store_oauth_tokens()
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Google OAuth login failed: {e}")
            return False
    
    async def login_with_facebook(self):
        """Login using Facebook OAuth."""
        try:
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
                
                # Store OAuth tokens
                await self._store_oauth_tokens()
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Facebook OAuth login failed: {e}")
            return False
    
    async def login_with_custom_oauth(self, provider_name: str):
        """Login with a custom OAuth provider."""
        try:
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
                
                # Store OAuth tokens
                await self._store_oauth_tokens()
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Custom OAuth login failed: {e}")
            return False
    
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
    
    async def _store_oauth_tokens(self):
        """Store OAuth authentication tokens."""
        # Extract OAuth tokens from page or cookies
        oauth_data = {}
        
        # Check for tokens in URL parameters
        url = self.page.url
        if 'access_token=' in url:
            # Extract token from URL
            import re
            token_match = re.search(r'access_token=([^&]+)', url)
            if token_match:
                oauth_data['access_token'] = token_match.group(1)
        
        # Check for tokens in cookies
        cookies = await self.page.context.cookies()
        for cookie in cookies:
            if 'token' in cookie['name'].lower():
                oauth_data[cookie['name']] = cookie['value']
        
        # Check for tokens in local storage
        local_storage = await self.page.evaluate("() => Object.assign({}, localStorage)")
        for key, value in local_storage.items():
            if 'token' in key.lower():
                oauth_data[key] = value
        
        self.auth_tokens = oauth_data
    
    async def refresh_oauth_token(self, provider: str) -> bool:
        """Refresh OAuth token for a specific provider."""
        try:
            # Implement token refresh logic
            refresh_endpoint = await self._get_refresh_endpoint(provider)
            
            if refresh_endpoint:
                # Use refresh token to get new access token
                refresh_token = self.auth_tokens.get('refresh_token')
                
                if refresh_token:
                    response = await self.page.evaluate(f"""
                        fetch('{refresh_endpoint}', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json'
                            }},
                            body: JSON.stringify({{
                                'refresh_token': '{refresh_token}'
                            }})
                        }}).then(response => response.json())
                    """)
                    
                    if response.get('access_token'):
                        self.auth_tokens['access_token'] = response['access_token']
                        return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"OAuth token refresh failed: {e}")
            return False
```

## 🎯 Use Cases

### Social Media Authentication
```python
class SocialMediaAuthFlow(LoginAuthenticationFlow, OAuthAuthenticationFlow):
    async def authenticate_user(self, method: str = 'traditional', **kwargs):
        """Authenticate user using specified method."""
        if method == 'traditional':
            return await self.login_with_credentials(
                kwargs.get('username'),
                kwargs.get('password')
            )
        elif method == 'google':
            return await self.login_with_google()
        elif method == 'facebook':
            return await self.login_with_facebook()
        else:
            raise ValueError(f"Unsupported authentication method: {method}")
    
    async def handle_authentication_flow(self):
        """Handle complete authentication flow including 2FA."""
        # Initial login
        login_success = await self.authenticate_user('traditional', 
            username='user@example.com', 
            password='password'
        )
        
        if not login_success:
            return False
        
        # Check if 2FA is required
        if await self._is_2fa_required():
            # Get 2FA code (this would come from user input or other source)
            two_factor_code = await self._get_2fa_code()
            
            if two_factor_code:
                return await self.handle_two_factor_auth(two_factor_code)
        
        return True
```

### Enterprise Authentication
```python
class EnterpriseAuthFlow(LoginAuthenticationFlow):
    async def login_with_sso(self, sso_provider: str):
        """Login using Single Sign-On (SSO)."""
        # Navigate to SSO login page
        await self.page.goto(f"https://example.com/sso/{sso_provider}")
        await self.page.wait_for_load_state('networkidle')
        
        # Handle SSO provider-specific login
        if sso_provider == 'saml':
            await self._handle_saml_sso()
        elif sso_provider == 'oidc':
            await self._handle_oidc_sso()
        
        # Wait for SSO completion
        await self._wait_for_login_completion()
        
        return True
    
    async def _handle_saml_sso(self):
        """Handle SAML SSO flow."""
        # Wait for SAML redirect
        await self.page.wait_for_url("**/saml/sso", timeout=10000)
        
        # Complete SAML authentication (implementation depends on IdP)
        # This is a placeholder for SAML-specific logic
        pass
```

## ⚡ Performance Optimization

### 1. Session Persistence
Persist authentication sessions across runs:

```python
async def save_session_to_file(self, filename: str):
    """Save current session to file."""
    session_data = {
        'cookies': await self.page.context.cookies(),
        'local_storage': await self.page.evaluate("() => Object.assign({}, localStorage)"),
        'session_storage': await self.page.evaluate("() => Object.assign({}, sessionStorage)"),
        'auth_tokens': self.auth_tokens
    }
    
    with open(filename, 'w') as f:
        json.dump(session_data, f)

async def load_session_from_file(self, filename: str) -> bool:
    """Load session from file."""
    try:
        with open(filename, 'r') as f:
            session_data = json.load(f)
        
        # Restore cookies
        await self.page.context.add_cookies(session_data['cookies'])
        
        # Restore local storage
        await self.page.evaluate(f"""
            Object.assign(localStorage, {json.dumps(session_data['local_storage'])})
        """)
        
        # Restore session storage
        await self.page.evaluate(f"""
            Object.assign(sessionStorage, {json.dumps(session_data['session_storage'])})
        """)
        
        # Restore auth tokens
        self.auth_tokens = session_data['auth_tokens']
        
        return True
        
    except Exception as e:
        self.logger.error(f"Failed to load session: {e}")
        return False
```

### 2. Token Refresh Automation
Automatically refresh expired tokens:

```python
async def auto_refresh_tokens(self):
    """Automatically refresh expired tokens."""
    for provider, tokens in self.auth_tokens.items():
        if await self._is_token_expired(tokens):
            success = await self.refresh_oauth_token(provider)
            if not success:
                self.logger.warning(f"Failed to refresh token for {provider}")
```

## 🛡️ Security Considerations

### 1. Credential Protection
```python
async def secure_login(self, username: str, password: str):
    """Secure login with credential protection."""
    # Clear any existing sensitive data
    await self._clear_sensitive_data()
    
    try:
        # Perform login
        result = await self.login_with_credentials(username, password)
        
        # Clear credentials from memory
        username = None
        password = None
        
        return result
        
    except Exception as e:
        # Clear credentials even on error
        username = None
        password = None
        raise

async def _clear_sensitive_data(self):
    """Clear sensitive data from page."""
    # Clear form fields
    await self.page.evaluate("""
        document.querySelectorAll('input[type="password"]').forEach(input => {
            input.value = '';
        });
    """)
    
    # Clear sensitive storage
    await self.page.evaluate("""
        Object.keys(localStorage).forEach(key => {
            if (key.toLowerCase().includes('password') || 
                key.toLowerCase().includes('token')) {
                localStorage.removeItem(key);
            }
        });
    """)
```

### 2. Session Validation
```python
async def validate_session_security(self) -> bool:
    """Validate session security."""
    # Check for session hijacking indicators
    current_ip = await self.page.evaluate("() => fetch('https://api.ipify.org?format=json').then(r => r.json()).then(d => d.ip)")
    
    # Compare with stored IP if available
    stored_ip = self.session_data.get('ip_address')
    if stored_ip and stored_ip != current_ip:
        self.logger.warning("IP address changed - possible session hijacking")
        return False
    
    # Update current IP
    self.session_data['ip_address'] = current_ip
    
    return True
```

## 📊 Best Practices

### 1. Security
- Never store credentials in plain text
- Use secure token storage
- Implement session timeout handling
- Validate session integrity

### 2. Error Handling
- Handle authentication failures gracefully
- Provide clear error messages
- Implement retry logic for network issues
- Log authentication events for auditing

### 3. Performance
- Persist sessions to avoid repeated logins
- Implement automatic token refresh
- Use efficient session management
- Minimize authentication overhead

### 4. Maintainability
- Separate authentication logic from business logic
- Use consistent authentication patterns
- Document authentication flows
- Implement comprehensive testing

## 🔍 Testing Authentication Flows

### Unit Tests
```python
async def test_login_with_credentials():
    """Test traditional login functionality."""
    flow = LoginAuthenticationFlow()
    await flow.setup()
    
    # Mock login page
    await flow.page.set_content("""
        <div>
            <input id="username_input" type="text">
            <input id="password_input" type="password">
            <button id="login_button">Login</button>
            <div id="login_success_indicator" style="display:none">Success</div>
        </div>
    """)
    
    # Test login
    result = await flow.login_with_credentials("testuser", "testpass")
    
    # Verify login was attempted
    username_input = await flow.page.query_selector("#username_input")
    username_value = await username_input.input_value()
    
    assert username_value == "testuser"
```

### Integration Tests
```python
async def test_oauth_flow():
    """Test OAuth authentication flow."""
    flow = OAuthAuthenticationFlow()
    await flow.setup()
    
    # Navigate to login page
    await flow.page.goto("https://example.com/login")
    
    # Test OAuth login
    result = await flow.login_with_google()
    
    # Verify authentication
    assert await flow.is_authenticated()
    assert flow.auth_tokens is not None
```

## 📚 Additional Resources

- [Navigation Domain](./NAVIGATION.md)
- [Extraction Domain](./EXTRACTION.md)
- [Filtering Domain](./FILTERING.md)
- [Real-World Examples](../REAL_WORLD_EXAMPLES.md)
