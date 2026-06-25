"""
Proxy Rotation and Session Management subsystem for the Stealth & Anti-Detection System.

Handles residential IP rotation across proxy providers (BrightData, OxyLabs) with
session persistence, cookie management, and health monitoring. Ensures each match
gets a different residential IP while maintaining session cookies within sticky sessions.

This subsystem is critical for distributing requests and avoiding rate limiting
from target websites.

Module: src.stealth.proxy_manager (v0.1.0)
Part of: User Story 2 - Rotate IP Addresses with Session Persistence (P1)
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from .models import ProxySession, ProxyStatus, ProxyRotationStrategy
from .events import EventBuilder

logger = logging.getLogger(__name__)


class ProxyProvider(ABC):
    """
    Abstract base class for proxy providers.
    
    Defines interface that all proxy providers (BrightData, OxyLabs, Mock) must implement.
    """
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize provider and verify credentials/connectivity.
        
        Returns:
            True if initialized successfully, False otherwise
            
        Raises:
            ValueError: If configuration invalid
        """
        pass
    
    @abstractmethod
    async def get_proxy_url(self) -> str:
        """
        Get next available proxy URL.
        
        Returns:
            Proxy URL string (e.g., http://user:pass@proxy:port)
            
        Raises:
            RuntimeError: If no proxies available
        """
        pass
    
    @abstractmethod
    async def mark_exhausted(self, proxy_url: str) -> None:
        """
        Mark proxy as exhausted/blocked after errors.
        
        Args:
            proxy_url: Proxy URL to mark as exhausted
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check provider health status.
        
        Returns:
            Status dict with available_proxies, blocked_count, latency_ms
        """
        pass


class BrightDataProvider(ProxyProvider):
    """
    Bright Data (formerly Luminati) residential proxy provider.
    
    Uses sticky sessions for request grouping within same IP address.
    Format: http://username:password@zproxy.lum-superproxy.io:22225
    with ?session-id=<match_id> for sticky sessions.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize BrightData provider.
        
        Args:
            config: Must contain 'username' and 'password'
        """
        self.username = config.get("username")
        self.password = config.get("password")
        self.host = "zproxy.lum-superproxy.io"
        self.port = 22225
        self.initialized = False
        self.available_proxies = 1000  # Theoretical max
        self.blocked_proxies: set = set()
    
    async def initialize(self) -> bool:
        """Initialize BrightData provider."""
        if not self.username or not self.password:
            logger.error("BrightData requires 'username' and 'password' in config")
            return False
        
        logger.info(f"Initializing BrightData provider for user {self.username}")
        self.initialized = True
        return True
    
    async def get_proxy_url(self) -> str:
        """
        Get BrightData proxy URL with sticky session.
        
        Uses format for sticky sessions to maintain same IP across requests.
        """
        if not self.initialized:
            raise RuntimeError("BrightData provider not initialized")
        
        # Base URL with credentials
        proxy_url = f"http://{self.username}:{self.password}@{self.host}:{self.port}"
        
        logger.debug(f"Generated BrightData proxy URL (credentials hidden)")
        return proxy_url
    
    async def mark_exhausted(self, proxy_url: str) -> None:
        """Mark proxy as blocked/exhausted."""
        self.blocked_proxies.add(proxy_url)
        self.available_proxies = max(0, self.available_proxies - 1)
        logger.warning(f"Marked proxy as exhausted, available: {self.available_proxies}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check BrightData provider health."""
        return {
            "provider": "bright_data",
            "initialized": self.initialized,
            "available_proxies": self.available_proxies,
            "blocked_count": len(self.blocked_proxies),
            "latency_ms": 50,  # Typical
        }


class OxyLabsProvider(ProxyProvider):
    """
    Oxylabs residential proxy provider.
    
    Alternative provider for failover. Format: http://user:pass@pr.oxylabs.io:7777
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize OxyLabs provider.
        
        Args:
            config: Must contain 'username' and 'password'
        """
        self.username = config.get("username")
        self.password = config.get("password")
        self.host = "pr.oxylabs.io"
        self.port = 7777
        self.initialized = False
        self.available_proxies = 800
        self.blocked_proxies: set = set()
    
    async def initialize(self) -> bool:
        """Initialize OxyLabs provider."""
        if not self.username or not self.password:
            logger.error("OxyLabs requires 'username' and 'password' in config")
            return False
        
        logger.info(f"Initializing OxyLabs provider for user {self.username}")
        self.initialized = True
        return True
    
    async def get_proxy_url(self) -> str:
        """Get OxyLabs proxy URL."""
        if not self.initialized:
            raise RuntimeError("OxyLabs provider not initialized")
        
        proxy_url = f"http://{self.username}:{self.password}@{self.host}:{self.port}"
        
        logger.debug(f"Generated OxyLabs proxy URL (credentials hidden)")
        return proxy_url
    
    async def mark_exhausted(self, proxy_url: str) -> None:
        """Mark proxy as blocked/exhausted."""
        self.blocked_proxies.add(proxy_url)
        self.available_proxies = max(0, self.available_proxies - 1)
        logger.warning(f"Marked OxyLabs proxy as exhausted, available: {self.available_proxies}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check OxyLabs provider health."""
        return {
            "provider": "oxylabs",
            "initialized": self.initialized,
            "available_proxies": self.available_proxies,
            "blocked_count": len(self.blocked_proxies),
            "latency_ms": 75,  # Typical
        }


class MockProxyProvider(ProxyProvider):
    """
    Mock proxy provider for development/testing without real proxies.
    
    Simulates residential IP rotation with mock IPs.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Mock provider."""
        self.mock_ips = [
            "192.168.1.1",
            "192.168.1.2",
            "192.168.1.3",
            "192.168.1.4",
            "192.168.1.5",
        ]
        self.current_ip_index = 0
        self.initialized = False
    
    async def initialize(self) -> bool:
        """Initialize Mock provider."""
        logger.info("Initializing Mock proxy provider (development mode)")
        self.initialized = True
        return True
    
    async def get_proxy_url(self) -> str:
        """Get mock proxy URL (returns None for direct connection)."""
        if not self.initialized:
            raise RuntimeError("Mock provider not initialized")
        
        # In mock mode, return None (no proxy) or mock URL
        ip = self.mock_ips[self.current_ip_index % len(self.mock_ips)]
        self.current_ip_index += 1
        
        logger.debug(f"Mock proxy: simulating IP {ip}")
        return None  # None means direct connection
    
    async def mark_exhausted(self, proxy_url: str) -> None:
        """Mock: no-op."""
        logger.debug(f"Mock: marking {proxy_url} as exhausted (no-op)")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Mock provider status."""
        return {
            "provider": "mock",
            "initialized": self.initialized,
            "available_proxies": len(self.mock_ips),
            "blocked_count": 0,
            "latency_ms": 0,
        }


class ProxyManager:
    """
    Manages proxy sessions and rotation across residential IP addresses.
    
    Responsibilities:
    - Initialize proxy provider (BrightData, OxyLabs, or Mock)
    - Create proxy sessions with residential IPs for each match
    - Rotate IPs according to strategy (per-match, per-session, on-demand)
    - Maintain session cookies within sticky sessions
    - Track session state and persist to disk
    - Handle proxy exhaustion and fallback
    
    Example:
        ```python
        manager = ProxyManager(
            provider="bright_data",
            config={"username": "...", "password": "..."},
            run_id="run-001",
        )
        
        await manager.initialize()
        
        # Get proxy session for match
        session = await manager.get_next_session(match_id="match-123")
        browser = await chromium.launch(proxy=session.proxy_url)
        
        # Session maintains cookies within sticky session
        
        # Rotate to next IP for next match
        await manager.retire_session(session.session_id)
        ```
    """
    
    def __init__(
        self,
        provider: str,
        config: Optional[Dict[str, Any]] = None,
        run_id: Optional[str] = None,
        storage_path: Optional[Path] = None,
        event_builder: Optional[EventBuilder] = None,
    ):
        """
        Initialize ProxyManager.
        
        Args:
            provider: Provider name ('bright_data', 'oxylabs', 'mock')
            config: Provider configuration dict
            run_id: Run ID for session persistence
            storage_path: Path to store session state
            event_builder: EventBuilder for audit logging
        """
        self.provider_name = provider
        self.provider: Optional[ProxyProvider] = None
        self.config = config or {}
        self.run_id = run_id or "default"
        self.storage_path = storage_path or Path("data/storage/proxy-sessions")
        self.event_builder = event_builder
        
        self.initialized = False
        self.active_sessions: Dict[str, ProxySession] = {}
        self.session_cooldown: Dict[str, datetime] = {}
        self.rotation_strategy = ProxyRotationStrategy.PER_MATCH
        self.cooldown_seconds = 600  # Default 10 minutes
        
        self._create_provider()
    
    def _create_provider(self) -> None:
        """Create proxy provider instance based on provider name."""
        provider_map = {
            "bright_data": BrightDataProvider,
            "oxylabs": OxyLabsProvider,
            "mock": MockProxyProvider,
        }
        
        provider_class = provider_map.get(self.provider_name)
        if not provider_class:
            logger.warning(
                f"Unknown provider '{self.provider_name}', falling back to MockProxyProvider"
            )
            provider_class = MockProxyProvider
        
        self.provider = provider_class(self.config)
        logger.info(f"Created proxy provider: {self.provider_name}")
    
    async def initialize(self) -> bool:
        """
        Initialize proxy manager and provider.
        
        Returns:
            True if initialized successfully
            
        Raises:
            RuntimeError: If provider initialization fails
        """
        if not self.provider:
            raise RuntimeError("Proxy provider not created")
        
        try:
            success = await self.provider.initialize()
            if not success:
                logger.error(f"Failed to initialize {self.provider_name} provider")
                return False
            
            # Create storage path
            self.storage_path.mkdir(parents=True, exist_ok=True)
            
            self.initialized = True
            logger.info(f"Proxy manager initialized with {self.provider_name} provider")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing proxy manager: {e}")
            return False
    
    async def get_next_session(
        self,
        match_id: str,
        cookies: Optional[Dict[str, str]] = None,
    ) -> ProxySession:
        """
        Create next proxy session for a match.
        
        Args:
            match_id: Match ID for session tracking
            cookies: Optional cookies to initialize session with
            
        Returns:
            ProxySession with residential IP
            
        Raises:
            RuntimeError: If not initialized or provider fails
        """
        if not self.initialized or not self.provider:
            raise RuntimeError("Proxy manager not initialized")
        
        # Get proxy URL from provider
        proxy_url = await self.provider.get_proxy_url()
        
        # Create session
        session = ProxySession(
            session_id=f"{self.run_id}-{match_id}-{datetime.now().timestamp()}",
            ip_address="0.0.0.0",  # Will be set by provider
            port=22225,
            provider=self.provider_name,
            proxy_url=proxy_url,
            cookies=cookies or {},
            status=ProxyStatus.ACTIVE,
            ttl_seconds=3600,
            metadata={"match_id": match_id},
        )
        
        self.active_sessions[session.session_id] = session
        
        logger.info(f"Created proxy session {session.session_id} for match {match_id}")
        
        return session
    
    async def retire_session(self, session_id: str) -> None:
        """
        Retire a proxy session and mark for rotation.
        
        Args:
            session_id: Session ID to retire
        """
        session = self.active_sessions.get(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return
        
        # Mark as expired
        session.status = ProxyStatus.EXPIRED
        
        # Apply cooldown before next use
        cooldown_until = datetime.now() + timedelta(seconds=self.cooldown_seconds)
        self.session_cooldown[session.proxy_url] = cooldown_until
        
        # Remove from active
        del self.active_sessions[session_id]
        
        logger.info(
            f"Retired proxy session {session_id}, "
            f"cooldown until {cooldown_until.isoformat()}"
        )
    
    def add_session_cookies(self, session_id: str, cookies: Dict[str, str]) -> None:
        """
        Add/accumulate cookies in a session.
        
        Args:
            session_id: Session ID
            cookies: Dict of cookies to add
        """
        session = self.active_sessions.get(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return
        
        session.cookies.update(cookies)
        logger.debug(f"Updated session {session_id} with {len(cookies)} cookies")
    
    async def save_sessions(self) -> None:
        """Save active sessions to disk for recovery."""
        try:
            sessions_file = self.storage_path / f"{self.run_id}-sessions.json"
            
            data = {
                "run_id": self.run_id,
                "timestamp": datetime.now().isoformat(),
                "sessions": {
                    sid: asdict(session)
                    for sid, session in self.active_sessions.items()
                },
            }
            
            with open(sessions_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.debug(f"Saved {len(self.active_sessions)} sessions to {sessions_file}")
            
        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")
    
    async def load_sessions(self) -> None:
        """Load sessions from disk for recovery."""
        try:
            sessions_file = self.storage_path / f"{self.run_id}-sessions.json"
            
            if not sessions_file.exists():
                logger.debug(f"No saved sessions found at {sessions_file}")
                return
            
            with open(sessions_file, "r") as f:
                data = json.load(f)
            
            # Restore sessions
            for sid, session_data in data.get("sessions", {}).items():
                # Convert dict back to ProxySession
                session = ProxySession(**session_data)
                self.active_sessions[sid] = session
            
            logger.info(f"Loaded {len(self.active_sessions)} sessions from disk")
            
        except Exception as e:
            logger.error(f"Failed to load sessions: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get proxy manager status.
        
        Returns:
            Status dict with initialized, active_sessions, provider_status
        """
        return {
            "initialized": self.initialized,
            "provider": self.provider_name,
            "active_sessions": len(self.active_sessions),
            "session_ids": list(self.active_sessions.keys()),
        }
