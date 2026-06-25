"""
Authentication domain flows.

This package contains authentication-specific flows for complex sites.
Authentication flows handle login, logout, session management,
and OAuth operations.
"""

from .login_flow import LoginAuthenticationFlow
from .oauth_flow import OAuthAuthenticationFlow

__all__ = [
    'LoginAuthenticationFlow',
    'OAuthAuthenticationFlow'
]
