"""
Proxy Settings Entity

This module defines the ProxySettings entity for browser proxy configuration.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import structlog

from .enums import ProxyType


@dataclass
class ProxySettings:
    """Browser proxy configuration settings."""
    server: str
    port: int
    proxy_type: ProxyType = ProxyType.HTTP
    username: Optional[str] = None
    password: Optional[str] = None
    bypass_list: List[str] = None
    dns_servers: List[str] = None
    pac_script_url: Optional[str] = None
    auto_detect: bool = False
    system_proxy: bool = False
    
    def __post_init__(self):
        """Validate proxy settings after initialization."""
        self.logger = structlog.get_logger("browser.proxy")
        
        if self.bypass_list is None:
            self.bypass_list = []
        if self.dns_servers is None:
            self.dns_servers = []
            
        # Validate required fields
        if not self.server:
            raise ValueError("Proxy server cannot be empty")
        if not self.port or self.port <= 0 or self.port > 65535:
            raise ValueError(f"Invalid proxy port: {self.port}")
            
        # Validate proxy type
        if not isinstance(self.proxy_type, ProxyType):
            self.logger.warning(
                "Invalid proxy type, defaulting to HTTP",
                proxy_type=self.proxy_type
            )
            self.proxy_type = ProxyType.HTTP
            
    def get_proxy_url(self) -> str:
        """Get the complete proxy URL."""
        if self.username and self.password:
            return f"{self.proxy_type.value}://{self.username}:{self.password}@{self.server}:{self.port}"
        else:
            return f"{self.proxy_type.value}://{self.server}:{self.port}"
            
    def get_server_address(self) -> str:
        """Get server address without credentials."""
        return f"{self.server}:{self.port}"
        
    def has_credentials(self) -> bool:
        """Check if proxy has authentication credentials."""
        return self.username is not None and self.password is not None
        
    def is_bypassed(self, hostname: str) -> bool:
        """Check if hostname should bypass proxy."""
        if not self.bypass_list:
            return False
            
        hostname_lower = hostname.lower()
        
        for bypass_pattern in self.bypass_list:
            bypass_lower = bypass_pattern.lower()
            
            # Exact match
            if hostname_lower == bypass_lower:
                return True
                
            # Wildcard match
            if bypass_lower.startswith('*.'):
                domain = bypass_lower[2:]
                if hostname_lower.endswith(domain) or hostname_lower == domain:
                    return True
                    
            # Subnet match
            if '/' in bypass_lower:
                try:
                    import ipaddress
                    hostname_ip = ipaddress.ip_address(hostname)
                    bypass_network = ipaddress.ip_network(bypass_lower)
                    if hostname_ip in bypass_network:
                        return True
                except ValueError:
                    pass  # Not an IP address
                    
        return False
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "proxy_type": self.proxy_type.value,
            "server": self.server,
            "port": self.port,
            "username": self.username,
            "password": "***" if self.password else None,  # Mask password
            "bypass_list": self.bypass_list.copy(),
            "dns_servers": self.dns_servers.copy(),
            "pac_script_url": self.pac_script_url,
            "auto_detect": self.auto_detect,
            "system_proxy": self.system_proxy,
            "has_credentials": self.has_credentials(),
            "proxy_url": self.get_proxy_url(),
            "server_address": self.get_server_address()
        }
        
    def to_playwright_format(self) -> Dict[str, Any]:
        """Convert to Playwright proxy configuration format."""
        proxy_config = {
            "server": self.get_proxy_url()
        }
        
        if self.bypass_list:
            proxy_config["bypass"] = self.bypass_list
            
        return proxy_config
        
    def to_curl_format(self) -> str:
        """Convert to cURL proxy format."""
        if self.username and self.password:
            return f"{self.proxy_type.value}://{self.username}:{self.password}@{self.server}:{self.port}"
        else:
            return f"{self.proxy_type.value}://{self.server}:{self.port}"
            
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProxySettings":
        """Create ProxySettings from dictionary."""
        # Handle proxy_type conversion
        proxy_type = data.get("proxy_type", "HTTP")
        if isinstance(proxy_type, str):
            proxy_type = ProxyType(proxy_type)
            
        return cls(
            proxy_type=proxy_type,
            server=data["server"],
            port=data["port"],
            username=data.get("username"),
            password=data.get("password"),
            bypass_list=data.get("bypass_list", []),
            dns_servers=data.get("dns_servers", []),
            pac_script_url=data.get("pac_script_url"),
            auto_detect=data.get("auto_detect", False),
            system_proxy=data.get("system_proxy", False)
        )
        
    @classmethod
    def from_url(cls, proxy_url: str) -> "ProxySettings":
        """Create ProxySettings from proxy URL."""
        import re
        from urllib.parse import urlparse
        
        try:
            parsed = urlparse(proxy_url)
            
            # Extract proxy type
            if parsed.scheme:
                try:
                    proxy_type = ProxyType(parsed.scheme)
                except ValueError:
                    proxy_type = ProxyType.HTTP
            else:
                proxy_type = ProxyType.HTTP
                
            # Extract server and port
            server = parsed.hostname
            port = parsed.port or (80 if proxy_type == ProxyType.HTTP else 1080)
            
            # Extract credentials
            username = parsed.username
            password = parsed.password
            
            return cls(
                proxy_type=proxy_type,
                server=server,
                port=port,
                username=username,
                password=password
            )
            
        except Exception as e:
            raise ValueError(f"Invalid proxy URL: {proxy_url}") from e
            
    @classmethod
    def get_common_proxy_presets(cls) -> Dict[str, "ProxySettings"]:
        """Get common proxy configuration presets."""
        return {
            "http_proxy": cls(
                proxy_type=ProxyType.HTTP,
                server="proxy.example.com",
                port=8080,
                bypass_list=["localhost", "127.0.0.1", "*.local"]
            ),
            "https_proxy": cls(
                proxy_type=ProxyType.HTTPS,
                server="secure-proxy.example.com",
                port=8080,
                bypass_list=["localhost", "127.0.0.1", "*.local"]
            ),
            "socks5_proxy": cls(
                proxy_type=ProxyType.SOCKS5,
                server="socks5.example.com",
                port=1080,
                bypass_list=["localhost", "127.0.0.1", "*.local"]
            ),
            "residential_proxy": cls(
                proxy_type=ProxyType.HTTP,
                server="residential.example.com",
                port=8080,
                username="user123",
                password="pass123",
                bypass_list=["localhost", "127.0.0.1", "*.local", "*.example.com"]
            )
        }
        
    @classmethod
    def create_http_proxy(
        cls,
        server: str,
        port: int = 8080,
        username: Optional[str] = None,
        password: Optional[str] = None,
        bypass_list: Optional[List[str]] = None
    ) -> "ProxySettings":
        """Create HTTP proxy configuration."""
        return cls(
            proxy_type=ProxyType.HTTP,
            server=server,
            port=port,
            username=username,
            password=password,
            bypass_list=bypass_list or ["localhost", "127.0.0.1"]
        )
        
    @classmethod
    def create_https_proxy(
        cls,
        server: str,
        port: int = 8080,
        username: Optional[str] = None,
        password: Optional[str] = None,
        bypass_list: Optional[List[str]] = None
    ) -> "ProxySettings":
        """Create HTTPS proxy configuration."""
        return cls(
            proxy_type=ProxyType.HTTPS,
            server=server,
            port=port,
            username=username,
            password=password,
            bypass_list=bypass_list or ["localhost", "127.0.0.1"]
        )
        
    @classmethod
    def create_socks5_proxy(
        cls,
        server: str,
        port: int = 1080,
        username: Optional[str] = None,
        password: Optional[str] = None,
        bypass_list: Optional[List[str]] = None
    ) -> "ProxySettings":
        """Create SOCKS5 proxy configuration."""
        return cls(
            proxy_type=ProxyType.SOCKS5,
            server=server,
            port=port,
            username=username,
            password=password,
            bypass_list=bypass_list or ["localhost", "127.0.0.1"]
        )
        
    def validate_connection(self) -> Dict[str, Any]:
        """Validate proxy connection and return status."""
        try:
            import socket
            import time
            
            start_time = time.time()
            
            # Test socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)  # 10 second timeout
            
            try:
                result = sock.connect_ex((self.server, self.port))
                connection_time = time.time() - start_time
                
                sock.close()
                
                if result == 0:
                    return {
                        "valid": True,
                        "server": self.server,
                        "port": self.port,
                        "connection_time_ms": connection_time * 1000,
                        "error": None
                    }
                else:
                    return {
                        "valid": False,
                        "server": self.server,
                        "port": self.port,
                        "connection_time_ms": None,
                        "error": f"Connection failed with code: {result}"
                    }
                    
            except Exception as e:
                return {
                    "valid": False,
                    "server": self.server,
                    "port": self.port,
                    "connection_time_ms": None,
                    "error": str(e)
                }
                
        except Exception as e:
            return {
                "valid": False,
                "server": self.server,
                "port": self.port,
                "connection_time_ms": None,
                "error": f"Validation error: {str(e)}"
            }
            
    def rotate_credentials(self, new_username: str, new_password: str) -> None:
        """Rotate proxy credentials."""
        old_username = self.username
        old_password = self.password
        
        self.username = new_username
        self.password = new_password
        
        self.logger.info(
            "Proxy credentials rotated",
            server=self.server,
            port=self.port,
            old_username=old_username,
            new_username=new_username
        )
        
    def __str__(self) -> str:
        """String representation."""
        if self.has_credentials():
            return f"ProxySettings({self.proxy_type.value}://{self.server}:{self.port} with credentials)"
        else:
            return f"ProxySettings({self.proxy_type.value}://{self.server}:{self.port})"
            
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"ProxySettings(proxy_type={self.proxy_type.value}, "
                f"server='{self.server}', port={self.port}, "
                f"username={'*' * len(self.username) if self.username else None}, "
                f"bypass_list={len(self.bypass_list)} items, "
                f"has_credentials={self.has_credentials()})")
        
    def __eq__(self, other) -> bool:
        """Check equality."""
        if not isinstance(other, ProxySettings):
            return False
        return (self.proxy_type == other.proxy_type and
                self.server == other.server and
                self.port == other.port and
                self.username == other.username)
        
    def __hash__(self) -> int:
        """Hash based on proxy configuration."""
        return hash((self.proxy_type, self.server, self.port, self.username))
