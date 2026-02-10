"""
Plugin permission system for the plugin system.

This module provides comprehensive permission management for plugins, including
permission definitions, validation, enforcement, and security controls.
"""

import os
import sys
import json
import threading
from typing import Dict, Any, List, Optional, Set, Union, Callable, Type
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .plugin_interface import PluginMetadata, PluginType, get_plugin_registry


class PermissionType(Enum):
    """Permission type enumeration."""
    FILE_SYSTEM = "file_system"
    NETWORK = "network"
    SYSTEM = "system"
    BROWSER_CONTROL = "browser_control"
    DATA_ACCESS = "data_access"
    CONFIGURATION = "configuration"
    LOGGING = "logging"
    NOTIFICATION = "notification"
    STORAGE = "storage"
    EXECUTION = "execution"
    DEBUG = "debug"
    CUSTOM = "custom"


class PermissionLevel(Enum):
    """Permission level enumeration."""
    READ_ONLY = "read_only"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


class PermissionScope(Enum):
    """Permission scope enumeration."""
    GLOBAL = "global"
    PLUGIN_SPECIFIC = "plugin_specific"
    SITE_SPECIFIC = "site_specific"
    SESSION_SPECIFIC = "session_specific"


@dataclass
class Permission:
    """Plugin permission definition."""
    id: str
    name: str
    description: str
    permission_type: PermissionType
    level: PermissionLevel
    scope: PermissionScope
    default_granted: bool = False
    required_for: List[str] = field(default_factory=list)
    conflicts_with: List[str] = field(default_factory=list)
    auto_grant_for: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = builtins.dict()


@dataclass
class PermissionRequest:
    """Permission request."""
    plugin_id: str
    permission_id: str
    reason: str
    context: Dict[str, Any] = field(default_factory=dict)
    requested_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    requestor: Optional[str] = None


@dataclass
class PermissionGrant:
    """Permission grant."""
    plugin_id: str
    permission_id: str
    granted: bool
    granted_at: datetime = field(default_factory=datetime.utcnow)
    granted_by: Optional[str] = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PermissionAuditLog:
    """Permission audit log entry."""
    plugin_id: str
    permission_id: str
        action: str  # requested, granted, revoked, expired
        result: bool
        reason: str
        context: Dict[str, Any] = field(default_factory=dict)
        timestamp: datetime = field(default_factory=datetime.utcnow)
        requestor: Optional[str] = None
        expires_at: Optional[datetime] = None


class PermissionManager:
    """Plugin permission manager."""
    
    def __init__(self):
        """Initialize permission manager."""
        self._permissions: Dict[str, Permission] = {}
        self._plugin_permissions: Dict[str, Set[str]] = {}
        self._permission_requests: Dict[str, List[PermissionRequest]] = {}
        self._permission_grants: Dict[str, Dict[str, PermissionGrant]] = {}
        self._audit_log: List[PermissionAuditLog] = []
        self._lock = threading.RLock()
        
        # Permission settings
        self._auto_grant_safe_permissions = True
        self._default_permission_level = PermissionLevel.READ_ONLY
        self._max_permission_level = PermissionLevel.EXECUTE
        self._permission_cache_ttl = timedelta(hours=1)
        
        # Built-in permissions
        self._register_builtin_permissions()
    
    def _register_builtin_permissions(self) -> None:
        """Register built-in permissions."""
        # File system permissions
        self.register_permission(Permission(
            id="file_read",
            name="File Read Access",
            description="Read access to file system",
            permission_type=PermissionType.FILE_SYSTEM,
            level=PermissionLevel.READ_ONLY,
            scope=PermissionScope.GLOBAL,
            default_granted=False,
            description="Allows reading files from the file system"
        ))
        
        self.register_permission(Permission(
            id="file_write",
            name="File Write Access",
            description="Write access to file system",
            permission_type=PermissionType.FILE_SYSTEM,
            level=PermissionLevel.WRITE,
            scope=PermissionScope.GLOBAL,
            default_granted=False,
            conflicts_with=["file_read"],
            description="Allows writing files to the file system"
        ))
        
        # Network permissions
        self.register_permission(Permission(
            id="network_access",
            name="Network Access",
            description="Network access",
            permission_type=PermissionType.NETWORK,
            level=PermissionLevel.EXECUTE,
            scope=PermissionScope.GLOBAL,
            default_granted=False,
            description="Allows making network requests"
        ))
        
        # Browser control permissions
        self.register_permission(Permission(
            id="browser_control",
            name="Browser Control",
            description="Browser control",
            permission_type=PermissionType.BROWSER_CONTROL,
            level=PermissionLevel.EXECUTE,
            scope=PermissionScope.GLOBAL,
            default_granted=False,
            description="Control browser behavior"
        ))
        
        # System permissions
        self.register_permission(Permission(
            id="system_access",
            name="System Access",
            description="System access",
            permission_type=PermissionType.SYSTEM,
            level=PermissionLevel.ADMIN,
            scope=PermissionScope.GLOBAL,
            default_granted=False,
            description="Access system-level functions"
        ))
        
        # Data access permissions
        self.register_permission(Permission(
            id="data_access",
            name="Data Access",
            description="Data access",
            permission_type=PermissionType.DATA_ACCESS,
            level=PermissionLevel.READ_ONLY,
            scope=PermissionScope.GLOBAL,
            default_granted=True,
            description="Access scraped data"
        ))
        
        # Configuration permissions
        self.register_permission(Permission(
            id="config_access",
            name="Configuration Access",
            description="Configuration access",
            permission_type=PermissionType.CONFIGURATION,
            level=PermissionLevel.WRITE,
            scope=PermissionScope.GLOBAL,
            default_granted=True,
            description="Access configuration"
        ))
        
        # Logging permissions
        self.register_permission(Permission(
            id="logging",
            name="Logging",
            description="Logging",
            permission_type=PermissionType.LOGGING,
            level=PermissionLevel.WRITE,
            scope=PermissionScope.GLOBAL,
            default_granted=True,
            description="Write to logs"
        ))
        
        # Notification permissions
        self.register_permission(Permission(
            id="notifications",
            name="Notifications",
            description="Send notifications",
            permission_type=PermissionType.NOTIFICATION,
            level=PermissionLevel.WRITE,
            scope=PermissionScope.GLOBAL,
            default_granted=False,
            description="Send notifications"
        ))
        
        # Execution permissions
        self.register_permission(Permission(
            id="code_execution",
            name="Code Execution",
            description="Code execution",
            permission_type=PermissionType.EXECUTION,
            level=PermissionLevel.EXECUTE,
            scope=PermissionScope.GLOBAL,
            default_granted=False,
            description="Execute code"
        ))
        
        # Debug permissions
        self.register_permission(Permission(
            id="debug_access",
            name="Debug Access",
            description="Debug access",
            permission_type=PermissionType.DEBUG,
            level=PermissionLevel.READ_ONLY,
            scope=PermissionScope.GLOBAL,
            default_granted=True,
            description="Access debug information"
        ))
    
    def register_permission(self, permission: Permission) -> None:
        """Register a permission."""
        with self._lock:
            self._permissions[permission.id] = permission
            
            # Update plugin permissions for auto-grant
            if self._auto_grant_safe_permissions:
                for plugin_id in permission.auto_grant_for:
                    if plugin_id not in self._plugin_permissions:
                        self._plugin_permissions[plugin_id] = set()
                    
                    self._plugin_permissions[plugin_id].add(permission.id)
            
            # Update conflicts
            for conflict_id in permission.conflicts_with:
                for plugin_id in self._plugin_permissions:
                    if conflict_id in self._plugin_permissions[plugin_id]:
                        self._plugin_permissions[plugin_id].remove(conflict_id)
    
    def unregister_permission(self, permission_id: str) -> bool:
        """Unregister a permission."""
        with self._lock:
            if permission_id not in self._permissions:
                return False
            
            del self._permissions[permission_id]
            
            # Remove from all plugin permissions
            for plugin_id in self._plugin_permissions:
                if permission_id in self._plugin_permissions[plugin_id]:
                    self._plugin_permissions[plugin_id].remove(permission_id)
            
            return True
    
    def get_permission(self, permission_id: str) -> Optional[Permission]:
        """Get a permission by ID."""
        return self._permissions.get(permission_id)
    
    def get_all_permissions(self) -> Dict[str, Permission]:
        """Get all permissions."""
        with self._lock:
            return self._permissions.copy()
    
    def get_plugin_permissions(self, plugin_id: str) -> Set[str]:
        """Get permissions for a plugin."""
        return self._plugin_permissions.get(plugin_id, set())
    
    def has_permission(self, plugin_id: str, permission_id: str) -> bool:
        """Check if a plugin has a specific permission."""
        return permission_id in self._plugin_permissions.get(plugin_id, set())
    
    def request_permission(self, plugin_id: str, permission_id: str, 
                         reason: str, context: Optional[Dict[str, Any]] = None,
                         expires_at: Optional[datetime] = None,
                         requestor: Optional[str] = None) -> str:
        """
        Request a permission.
        
        Args:
            permission_id: Permission ID
            plugin_id: Plugin ID
            reason: Request reason
            context: Additional context
            expires_at: Expiration time
            requestor: Requestor identifier
            
        Returns:
            Request ID
        """
        request_id = f"{plugin_id}_{permission_id}_{int(datetime.utcnow().timestamp())}"
        
        request = PermissionRequest(
            plugin_id=plugin_id,
            permission_id=permission_id,
            reason=reason,
            context=context or {},
            expires_at=expires_at,
            requestor=requestor
        )
        
        with self._lock:
            if plugin_id not in self._permission_requests:
                self._permission_requests[plugin_id] = []
            
            self._permission_requests[plugin_id].append(request)
            
            # Auto-approve safe permissions
            permission = self.get_permission(permission_id)
            if (permission and 
                permission.level.value <= self._default_permission_level.value and
                permission.scope == PermissionScope.GLOBAL and
                permission.default_granted):
                
                grant = PermissionGrant(
                    plugin_id=plugin_id,
                    permission_id=permission_id,
                    granted=True,
                    granted_by="auto_grant"
                )
                
                self._permission_grants[plugin_id][permission_id] = grant
                
                # Update plugin permissions
                if plugin_id not in self._plugin_permissions:
                    self._plugin_permissions[plugin_id] = set()
                
                self._plugin_permissions[plugin_id].add(permission_id)
                
                # Log the grant
                self._audit_log.append(PermissionAuditLog(
                    plugin_id=plugin_id,
                    permission_id=permission_id,
                    action="granted",
                    result=True,
                    reason=f"Auto-granted safe permission",
                    context=context or {},
                    granted_by="auto_grant"
                ))
                
                return request_id
            
            return request_id
    
    async def approve_permission(self, request_id: str, granted: bool, 
                             reason: str, approver: Optional[str] = None) -> bool:
        """
        Approve or deny a permission request.
        
        Args:
            request_id: Request ID
            granted: Whether to grant the permission
            reason: Approval/denial reason
            approver: Approver identifier
            
        Returns:
            True if successful
        """
        with self._lock:
            # Find the request
            request_found = False
            plugin_id = None
            request_obj = None
            
            for pid, requests in self._permission_requests.items():
                for req in requests:
                    if req.request_id == request_id:
                        request_obj = req
                        plugin_id = pid
                        request_found = True
                        break
            
            if not request_found:
                return False
            
            # Get permission
            permission = self.get_permission(request.permission_id)
            if not permission:
                return False
            
            # Create grant
            grant = PermissionGrant(
                plugin_id=request.plugin_id,
                permission_id=request.permission_id,
                granted=granted,
                granted_by=approver or "manual"
            )
            
            # Update grants
            if plugin_id not in self._permission_grants:
                self._permission_grants[plugin_id] = {}
            
            self._permission_grants[plugin_id][request.permission_id] = grant
            
            # Update plugin permissions
            if granted:
                if plugin_id not in self._plugin_permissions:
                    self._plugin_permissions[plugin_id] = set()
                
                self._plugin_permissions[plugin_id].add(request.permission_id)
            
            # Log the action
            self._audit_log.append(PermissionAuditLog(
                plugin_id=request.plugin_id,
                permission_id=request.permission_id,
                action="approved" if granted else "denied",
                result=granted,
                reason=reason,
                context=request.context or {},
                granted_by=approver or "manual"
            ))
            
            return True
    
    def revoke_permission(self, plugin_id: str, permission_id: str, 
                         reason: str, revoker: Optional[str] = None) -> bool:
        """
        Revoke a permission.
        
        args:
            plugin_id: Plugin ID
            permission_id: Permission ID
            reason: Revocation reason
            revoker: Revoker identifier
            
        Returns:
            True if successful
        """
        with self._lock:
            # Get current grant
            if (plugin_id not in self._permission_grants or 
                permission_id not in self._permission_grants[plugin_id]):
                return False
            
            grant = self._permission_grants[plugin_id][permission_id]
            
            # Remove grant
            del self._permission_grants[plugin_id][permission_id]
            
            # Update plugin permissions
            if plugin_id in self._plugin_permissions:
                self._plugin_permissions[plugin_id].discard(permission_id)
            
            # Log the revocation
            self._audit_log.append(PermissionAuditLog(
                plugin_id=plugin_id,
                permission_id=permission_id,
                action="revoked",
                result=not grant.granted,
                reason=reason,
                context={},
                revoked_by=revoker or "manual"
            ))
            
            return True
    
    def check_permission(self, plugin_id: str, permission_id: str, 
                        context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if a plugin has a permission.
        
        Args:
            plugin_id: Plugin ID
            permission_id: Permission ID
            context: Additional context
            
        Returns:
            True if permission is granted
        """
        with self._lock:
            # Check if plugin has permission
            if not self.has_permission(plugin_id, permission_id):
                return False
            
            # Check if permission is granted
            if plugin_id in self._permission_grants:
                grant = self._permission_grants[plugin_id].get(permission_id)
                if grant and grant.granted:
                    # Check if grant is expired
                    if grant.expires_at and datetime.utcnow() > grant.expires_at:
                        return False
                    
                    # Check scope
                    permission = self.get_permission(permission_id)
                    if permission.scope == PermissionScope.GLOBAL:
                        return True
                    elif permission.scope == PermissionType.PLUGIN_SPECIFIC:
                        return plugin_id == permission_id
                    elif permission.scope == PermissionType.SITE_SPECIFIC:
                        # Check if plugin belongs to a specific site
                        if context and 'site_id' in context:
                            return context['site_id'] == permission_id
                    return False
                else:
                    return False
            else:
                # Check if permission is default granted
                permission = self.get_permission(permission_id)
                if permission and permission.default_granted:
                    return True
                
                # Check if permission is safe and auto-granted
                if (permission and 
                    permission.level.value <= self._default_permission_level.value and
                    permission.scope == PermissionScope.GLOBAL and
                    permission.default_granted):
                    return True
            
            return False
    
    def get_permission_status(self, plugin_id: str, permission_id: str) -> Dict[str, Any]:
        """Get permission status."""
        with self._permission_grants:
            if plugin_id in self._permission_grants:
                grant = self._permission_grants[plugin_id].get(permission_id)
                return {
                    'granted': grant.granted,
                    'granted_at': grant.granted_at.isoformat() if grant.granted_at else None,
                    'granted_by': grant.granted_by,
                    'expires_at': grant.expires_at.isoformat() if grant.expires_at else None,
                    'expired': grant.expires_at and datetime.utcnow() > grant.expires_at
                }
        
        return {
            'granted': False,
            'exists': permission_id in self._permissions
        }
    
    def get_all_permissions_status(self, plugin_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Get all permissions status for a plugin."""
        status = {}
        
        if plugin_id:
            # Get specific plugin permissions
            plugin_perms = self.get_plugin_permissions(plugin_id)
            for perm_id in plugin_perms:
                status[perm_id] = self.get_permission_status(plugin_id, perm_id)
        else:
            # Get all permissions
            for perm_id, permission in self.get_all_permissions().items():
                status[perm_id] = self.get_permission_status("", perm_id)
        
        return status
    
    def get_permission_requests(self, plugin_id: Optional[str] = None, 
                           status: Optional[str] = None) -> List[PermissionRequest]:
        """Get permission requests for a plugin."""
        requests = []
        
        if plugin_id:
            requests = self._permission_requests.get(plugin_id, [])
        elif status:
            requests = [
                req for req in self._permission_requests.values()
                if status is None or req.status == status
            ]
        
        return requests
    
    def get_permission_grants(self, plugin_id: Optional[str] = None) -> Dict[str, PermissionGrant]:
        """Get permission grants for a plugin."""
        if plugin_id and plugin_id in self._permission_grants:
            return self._permission_grants[plugin_id]
        
        return {}
    
    def get_audit_log(self, plugin_id: Optional[str] = None, 
                        permission_id: Optional[str] = None,
                        limit: Optional[int] = None) -> List[PermissionAuditLog]:
        """Get audit log entries."""
        log = self._audit_log
        
        if plugin_id:
            log = [entry for entry in log if entry.plugin_id == plugin_id]
        
        if permission_id:
            log = [entry for entry in log if entry.permission_id == permission_id]
        
        if limit:
            log = log[-limit:]
        
        return log
    
    def clear_expired_grants(self) -> int:
        """Clear expired permission grants."""
        now = datetime.utcnow()
        expired_count = 0
        
        with self._lock:
            for plugin_id, grants in list(self._permission_grants.items()):
                expired_grants = [
                    grant_id for grant_id, grant in grants.items()
                    if grant.expires_at and now > grant.expires_at
                ]
                
                for grant_id in expired_grants:
                    del grants[grant_id]
                    expired_count += 1
                
                if not grants:
                    del self._permission_grants[plugin_id]
            
            return expired_count
    
    def clear_audit_log(self) -> int:
        """Clear audit log."""
        count = len(self._audit_log)
        self._audit_log.clear()
        return count
    
    def export_permissions(self) -> Dict[str, Any]:
        """Export all permissions to dictionary format."""
        return {
            'permissions': {
                perm_id: {
                    'name': perm.name,
                    'description': perm.description,
                    'type': perm.permission_type.value,
                    'level': perm.level.value,
                    'scope': perm.scope.value,
                    'default_granted': perm.default_granted,
                    'required_for': perm.required_for,
                    'conflicts_with': perm.conflicts_with,
                    'auto_grant_for': perm.auto_grant_for,
                    'created_at': perm.created_at.isoformat(),
                    'updated_at': perm.updated_at.isoformat()
                }
                for perm_id, perm in self._permissions.items()
            },
            'plugin_permissions': {
                plugin_id: list(perms) for plugin_id, permiss in self._plugin_permissions.items()
            },
            'permission_grants': {
                plugin_id: {
                    grant_id: {
                        'granted': grant.granted,
                        'granted_at': grant.granted_at.isoformat() if grant.granted_at else None,
                        'granted_by': grant.granted_by,
                        'expires_at': grant.expires_at.isoformat() if grant.expires_at else None
                    }
                    for grant_id, grant in grants.items()
                }
            },
            'audit_log': [
                {
                    'plugin_id': entry.plugin_id,
                    'permission_id': entry.permission_id,
                    'action': entry.action,
                    'result': entry.result,
                    'reason': entry.reason,
                    'timestamp': entry.timestamp.isoformat(),
                    'requestor': entry.requestor
                }
                for entry in self._audit_log
            ],
            'statistics': self._stats.copy()
        }
    
    def import_permissions(self, permissions_data: Dict[str, Any]) -> None:
        """Import permissions from dictionary data."""
        for perm_data in permissions_data.get('permissions', []):
            permission = Permission(
                id=perm_data['id'],
                name=perm_data['name'],
                description=perm_data['description'],
                permission_type=PermissionType(perm_data['type']),
                level=PermissionLevel(perm_data['level']),
                scope=PermissionScope(perm_data['scope']),
                default_granted=perm_data.get('default_granted', False),
                required_for=perm_data.get('required_for', []),
                conflicts_with=perm_data.get('conflicts_with', []),
                auto_grant_for=perm_data.get('auto_grant_for', []),
                created_at=datetime.fromisoformat(perm_data['created_at']) if perm_data.get('created_at') else datetime.utcnow(),
                updated_at=datetime.fromisoformat(perm_data['updated_at']) if perm_data.get('updated_at') else datetime.utcnow(),
                metadata=perm_data.get('metadata', {})
            )
            
            self.register_permission(permission)
    
    def export_plugin_permissions(self, plugin_id: str) -> Dict[str, Any]:
        """Export permissions for a specific plugin."""
        permissions = self.get_plugin_permissions(plugin_id)
        grants = self.get_permission_grants(plugin_id)
        
        return {
            'plugin_id': plugin_id,
            'permissions': [
                self.get_permission(perm_id).__dict__ for perm_id in permissions
            ],
            'grants': grants
        }
    
    def import_plugin_permissions(self, plugin_id: str, permissions_data: Dict[str, Any]) -> None:
        """Import permissions for a specific plugin."""
        for perm_data in permissions_data.get('permissions', []):
            if perm_data.get('id') == permission_id:
                permission = Permission(
                    id=perm_data['id'],
                    name=perm_data['name'],
                    description=perm_data['description'],
                    permission_type=PermissionType(perm_data['type']),
                    level=PermissionLevel(perm_data['level']),
                    scope=PermissionScope(perm_data['scope']),
                    default_granted=perm_data.get('default_granted', False),
                    required_for=perm_data.get('required_for', []),
                    conflicts_with=perm_data.get('conflicts_with', []),
                    auto_grant_for=perm_data.get('auto_grant_for', []),
                    created_at=datetime.fromisoformat(perm_data['created_at']) if perm_data.get('created_at') else datetime.utcnow(),
                    updated_at=datetime.fromisoformat(perm_data['updated_at']) if perm_data.get('updated_at') else datetime.utcnow(),
                    metadata=perm_data.get('metadata', {})
                )
                
                self.register_permission(permission)
                break


# Global permission manager instance
_permission_manager = PermissionManager()


# Convenience functions
def register_permission(permission: Permission) -> None:
    """Register a permission."""
    _permission_manager.register_permission(permission)


def unregister_permission(permission_id: str) -> bool:
    """Unregister a permission."""
    return _permission_manager.unregister_permission(permission_id)


def get_permission(permission_id: str) -> Optional[Permission]:
    """Get a permission by ID."""
    return _permission_manager.get_permission(permission_id)


def has_permission(plugin_id: str, permission_id: str, 
                     context: Optional[Dict[str, Any]] = None) -> bool:
    """Check if a plugin has a permission."""
    return _permission_manager.check_permission(plugin_id, permission_id, context)


def request_permission(plugin_id: str, permission_id: str, reason: str, 
                     context: Optional[Dict[str, Any]] = None,
                     expires_at: Optional[datetime] = None,
                     requestor: Optional[str] = None) -> str:
    """Request a permission."""
    return _permission_manager.request_permission(
        plugin_id, permission_id, reason, context, expires_at, requestor
    )


def approve_permission(request_id: str, granted: bool, reason: str, 
                     approver: Optional[str] = None) -> bool:
    """Approve or deny a permission request."""
    return _permission_manager.approve_permission(request_id, granted, reason, approver)


def revoke_permission(plugin_id: str, permission_id: str, reason: str, 
                     revoker: Optional[str] = None) -> bool:
    """Revoke a permission."""
    return _permission_manager.revoke_permission(plugin_id, permission_id, reason, revoker)


def get_permission_status(plugin_id: Optional[str] = None, 
                           permission_id: Optional[str] = None) -> Dict[str, Any]:
    """Get permission status."""
    return _permission_manager.get_permission_status(plugin_id, permission_id)


def get_all_permissions() -> Dict[str, Permission]:
    """Get all permissions."""
    return _permission_manager.get_all_permissions()


def get_plugin_permissions(plugin_id: str) -> Set[str]:
    """Get permissions for a plugin."""
    return _permission_manager.get_plugin_permissions(plugin_id)


def get_plugin_grants(plugin_id: str) -> Dict[str, PermissionGrant]:
    """Get permission grants for a plugin."""
    return _permission_manager.get_permission_grants(plugin_id)


def get_audit_log(plugin_id: Optional[str] = None, 
                     permission_id: Optional[str] = None,
                     limit: Optional[int] = None) -> List[PermissionAuditLog]:
    """Get audit log entries."""
    return _permission_manager.get_audit_log(plugin_id, permission_id, limit)


def export_permissions() -> Dict[str, Any]:
    """Export all permissions."""
    return _permission_manager.export_permissions()


def import_permissions(permissions_data: Dict[str, Any]) -> None:
    """Import permissions from dictionary data."""
    _permission_manager.import_permissions(permissions_data)


def clear_expired_grants() -> int:
    """Clear expired permission grants."""
    return _permission_manager.clear_expired_grants()


def clear_audit_log() -> int:
    """Clear audit log."""
    return _permission_manager.clear_audit_log()


def get_permission_statistics() -> Dict[str, Any]:
    """Get permission statistics."""
    return _permission_manager.get_statistics()
