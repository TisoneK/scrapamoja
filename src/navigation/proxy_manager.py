"""
Proxy management integration for production use

Provides proxy management, rotation, and health checking for navigation operations
with support for multiple proxy types and automatic failover.
"""

import asyncio
import random
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .logging_config import get_navigation_logger


@dataclass
class ProxyConfig:
    """Proxy configuration"""
    proxy_id: str
    proxy_type: str  # "http", "https", "socks5"
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    is_active: bool = True
    success_rate: float = 1.0
    last_used: Optional[datetime] = None


class ProxyManager:
    """Proxy management for navigation operations"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize proxy manager"""
        self.logger = get_navigation_logger("proxy_manager")
        self.config = config or {}
        
        self.proxies: Dict[str, ProxyConfig] = {}
        self.rotation_index = 0
        
        self.logger.info("Proxy manager initialized")
    
    def add_proxy(self, proxy_config: ProxyConfig) -> None:
        """Add proxy configuration"""
        self.proxies[proxy_config.proxy_id] = proxy_config
        self.logger.info("Proxy added", proxy_id=proxy_config.proxy_id)
    
    def get_proxy(self, exclude_failed: bool = True) -> Optional[ProxyConfig]:
        """Get next available proxy"""
        active_proxies = [
            p for p in self.proxies.values() 
            if p.is_active and (not exclude_failed or p.success_rate > 0.3)
        ]
        
        if not active_proxies:
            return None
        
        # Rotate through proxies
        proxy = active_proxies[self.rotation_index % len(active_proxies)]
        self.rotation_index += 1
        
        proxy.last_used = datetime.utcnow()
        return proxy
    
    def mark_proxy_success(self, proxy_id: str) -> None:
        """Mark proxy as successful"""
        if proxy_id in self.proxies:
            proxy = self.proxies[proxy_id]
            proxy.success_rate = min(1.0, proxy.success_rate * 1.1)
    
    def mark_proxy_failure(self, proxy_id: str) -> None:
        """Mark proxy as failed"""
        if proxy_id in self.proxies:
            proxy = self.proxies[proxy_id]
            proxy.success_rate = max(0.0, proxy.success_rate * 0.9)
            
            if proxy.success_rate < 0.1:
                proxy.is_active = False


def create_proxy_manager(config: Optional[Dict[str, Any]] = None) -> ProxyManager:
    """Create proxy manager"""
    return ProxyManager(config)
