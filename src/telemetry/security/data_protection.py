"""
Security review and data protection for telemetry system.

This module provides comprehensive security features including data encryption,
access control, audit logging, and privacy protection for telemetry data.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from dataclasses import dataclass, field
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from ..exceptions import TelemetryError

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security levels for telemetry data."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class DataClassification(Enum):
    """Data classification levels."""
    METADATA = "metadata"  # Performance metrics, timing data
    USAGE = "usage"        # Usage patterns, frequencies
    IDENTIFIABLE = "identifiable"  # User/session identifiers
    SENSITIVE = "sensitive"        # Authentication tokens, personal data


@dataclass
class SecurityPolicy:
    """Security policy configuration."""
    encryption_enabled: bool = True
    encryption_algorithm: str = "AES-256"
    key_rotation_days: int = 90
    data_retention_days: int = 365
    audit_logging_enabled: bool = True
    access_control_enabled: bool = True
    anonymization_enabled: bool = True
    compliance_standards: List[str] = field(default_factory=lambda: ["GDPR", "CCPA"])


@dataclass
class SecurityEvent:
    """Security event for audit logging."""
    event_id: str
    event_type: str
    timestamp: datetime
    user_id: Optional[str]
    resource: str
    action: str
    outcome: str
    details: Dict[str, Any]
    severity: str


class DataEncryption:
    """Data encryption and decryption utilities."""
    
    def __init__(self, master_key: Optional[bytes] = None):
        self.master_key = master_key or self._generate_master_key()
        self.fernet = Fernet(self.master_key)
    
    def _generate_master_key(self) -> bytes:
        """Generate encryption master key."""
        return Fernet.generate_key()
    
    def encrypt_data(self, data: Union[str, bytes, Dict]) -> bytes:
        """Encrypt sensitive data."""
        try:
            if isinstance(data, dict):
                data = json.dumps(data).encode('utf-8')
            elif isinstance(data, str):
                data = data.encode('utf-8')
            
            return self.fernet.encrypt(data)
        except Exception as e:
            raise TelemetryError(f"Failed to encrypt data: {e}")
    
    def decrypt_data(self, encrypted_data: bytes) -> Union[str, Dict]:
        """Decrypt sensitive data."""
        try:
            decrypted = self.fernet.decrypt(encrypted_data)
            
            # Try to parse as JSON first
            try:
                return json.loads(decrypted.decode('utf-8'))
            except json.JSONDecodeError:
                return decrypted.decode('utf-8')
                
        except Exception as e:
            raise TelemetryError(f"Failed to decrypt data: {e}")
    
    def encrypt_field(self, data: Dict, field_name: str) -> Dict:
        """Encrypt specific field in data dictionary."""
        if field_name in data:
            encrypted_data = data.copy()
            encrypted_data[field_name] = self.encrypt_data(data[field_name])
            return encrypted_data
        return data
    
    def decrypt_field(self, data: Dict, field_name: str) -> Dict:
        """Decrypt specific field in data dictionary."""
        if field_name in data and isinstance(data[field_name], bytes):
            decrypted_data = data.copy()
            decrypted_data[field_name] = self.decrypt_data(data[field_name])
            return decrypted_data
        return data


class DataAnonymization:
    """Data anonymization and privacy protection."""
    
    def __init__(self):
        self.salt = os.urandom(32)
    
    def anonymize_selector_id(self, selector_id: str) -> str:
        """Anonymize selector ID with consistent hash."""
        return self._hash_value(f"selector_{selector_id}")
    
    def anonymize_correlation_id(self, correlation_id: str) -> str:
        """Anonymize correlation ID with consistent hash."""
        return self._hash_value(f"correlation_{correlation_id}")
    
    def anonymize_user_id(self, user_id: str) -> str:
        """Anonymize user ID with consistent hash."""
        return self._hash_value(f"user_{user_id}")
    
    def anonymize_ip_address(self, ip_address: str) -> str:
        """Anonymize IP address (keep network, zero out host)."""
        try:
            parts = ip_address.split('.')
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.0.0"
            return "anonymized"
        except Exception:
            return "anonymized"
    
    def anonymize_timestamp(self, timestamp: datetime, precision_hours: int = 1) -> datetime:
        """Anonymize timestamp by reducing precision."""
        # Round down to nearest hour precision
        hours = timestamp.hour // precision_hours * precision_hours
        return timestamp.replace(hour=hours, minute=0, second=0, microsecond=0)
    
    def _hash_value(self, value: str) -> str:
        """Generate consistent hash for value."""
        return hashlib.sha256(self.salt + value.encode('utf-8')).hexdigest()[:16]
    
    def anonymize_telemetry_event(self, event: Dict) -> Dict:
        """Anonymize telemetry event data."""
        anonymized = event.copy()
        
        # Anonymize identifiers
        if 'selector_id' in anonymized:
            anonymized['selector_id'] = self.anonymize_selector_id(anonymized['selector_id'])
        
        if 'correlation_id' in anonymized:
            anonymized['correlation_id'] = self.anonymize_correlation_id(anonymized['correlation_id'])
        
        if 'user_id' in anonymized:
            anonymized['user_id'] = self.anonymize_user_id(anonymized['user_id'])
        
        # Anonymize timestamps
        if 'timestamp' in anonymized:
            if isinstance(anonymized['timestamp'], str):
                timestamp = datetime.fromisoformat(anonymized['timestamp'])
            else:
                timestamp = anonymized['timestamp']
            anonymized['timestamp'] = self.anonymize_timestamp(timestamp)
        
        # Remove sensitive fields
        sensitive_fields = ['auth_token', 'session_cookie', 'personal_data']
        for field in sensitive_fields:
            anonymized.pop(field, None)
        
        return anonymized


class AccessControl:
    """Access control for telemetry data."""
    
    def __init__(self):
        self.roles: Dict[str, Set[str]] = {
            "admin": {"read", "write", "delete", "manage"},
            "analyst": {"read", "write"},
            "viewer": {"read"},
            "system": {"read", "write", "delete"}
        }
        self.user_roles: Dict[str, str] = {}
        self.resource_permissions: Dict[str, Set[str]] = {}
    
    def assign_role(self, user_id: str, role: str) -> None:
        """Assign role to user."""
        if role not in self.roles:
            raise TelemetryError(f"Invalid role: {role}")
        self.user_roles[user_id] = role
    
    def check_permission(self, user_id: str, resource: str, action: str) -> bool:
        """Check if user has permission for action on resource."""
        user_role = self.user_roles.get(user_id, "viewer")
        role_permissions = self.roles.get(user_role, set())
        
        # Check resource-specific permissions
        resource_perms = self.resource_permissions.get(resource, set())
        if resource_perms:
            return action in resource_perms
        
        # Check role-based permissions
        return action in role_permissions
    
    def set_resource_permissions(self, resource: str, permissions: Set[str]) -> None:
        """Set permissions for specific resource."""
        self.resource_permissions[resource] = permissions
    
    def get_accessible_resources(self, user_id: str) -> List[str]:
        """Get list of resources accessible to user."""
        user_role = self.user_roles.get(user_id, "viewer")
        role_permissions = self.roles.get(user_role, set())
        
        accessible = []
        for resource, permissions in self.resource_permissions.items():
            if any(perm in role_permissions for perm in permissions):
                accessible.append(resource)
        
        return accessible


class AuditLogger:
    """Security audit logging."""
    
    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file or "logs/security_audit.log"
        self.events: List[SecurityEvent] = []
    
    def log_event(self, 
                  event_type: str,
                  user_id: Optional[str],
                  resource: str,
                  action: str,
                  outcome: str,
                  details: Dict[str, Any],
                  severity: str = "info") -> None:
        """Log security event."""
        event = SecurityEvent(
            event_id=self._generate_event_id(),
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            resource=resource,
            action=action,
            outcome=outcome,
            details=details,
            severity=severity
        )
        
        self.events.append(event)
        self._write_to_log(event)
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        return f"evt_{int(datetime.now().timestamp() * 1000)}"
    
    def _write_to_log(self, event: SecurityEvent) -> None:
        """Write event to audit log file."""
        try:
            log_entry = {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "timestamp": event.timestamp.isoformat(),
                "user_id": event.user_id,
                "resource": event.resource,
                "action": event.action,
                "outcome": event.outcome,
                "details": event.details,
                "severity": event.severity
            }
            
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
    
    def get_events(self, 
                   event_type: Optional[str] = None,
                   user_id: Optional[str] = None,
                   start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None) -> List[SecurityEvent]:
        """Get filtered security events."""
        filtered_events = self.events
        
        if event_type:
            filtered_events = [e for e in filtered_events if e.event_type == event_type]
        
        if user_id:
            filtered_events = [e for e in filtered_events if e.user_id == user_id]
        
        if start_time:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_time]
        
        if end_time:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_time]
        
        return filtered_events
    
    def generate_security_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate security report for specified period."""
        start_time = datetime.now(timezone.utc) - timedelta(days=days)
        recent_events = [e for e in self.events if e.timestamp >= start_time]
        
        # Calculate statistics
        total_events = len(recent_events)
        events_by_type = {}
        events_by_severity = {}
        events_by_user = {}
        
        for event in recent_events:
            events_by_type[event.event_type] = events_by_type.get(event.event_type, 0) + 1
            events_by_severity[event.severity] = events_by_severity.get(event.severity, 0) + 1
            
            if event.user_id:
                events_by_user[event.user_id] = events_by_user.get(event.user_id, 0) + 1
        
        # Identify security issues
        security_issues = []
        
        # Check for failed authentication attempts
        failed_auth = [e for e in recent_events if e.event_type == "authentication" and e.outcome == "failed"]
        if len(failed_auth) > 10:
            security_issues.append(f"High number of failed authentication attempts: {len(failed_auth)}")
        
        # Check for unauthorized access attempts
        unauthorized = [e for e in recent_events if e.event_type == "access" and e.outcome == "denied"]
        if len(unauthorized) > 5:
            security_issues.append(f"Multiple unauthorized access attempts: {len(unauthorized)}")
        
        return {
            "period_days": days,
            "total_events": total_events,
            "events_by_type": events_by_type,
            "events_by_severity": events_by_severity,
            "events_by_user": events_by_user,
            "security_issues": security_issues,
            "risk_score": self._calculate_risk_score(recent_events)
        }
    
    def _calculate_risk_score(self, events: List[SecurityEvent]) -> float:
        """Calculate security risk score."""
        severity_weights = {"low": 1, "info": 2, "medium": 5, "high": 10, "critical": 25}
        
        total_weight = 0
        for event in events:
            weight = severity_weights.get(event.severity, 1)
            if event.outcome == "failed" or event.outcome == "denied":
                weight *= 2  # Double weight for failures
            total_weight += weight
        
        # Normalize to 0-100 scale
        return min(100.0, (total_weight / len(events)) if events else 0.0)


class SecurityManager:
    """Main security manager for telemetry system."""
    
    def __init__(self, policy: Optional[SecurityPolicy] = None):
        self.policy = policy or SecurityPolicy()
        self.encryption = DataEncryption()
        self.anonymization = DataAnonymization()
        self.access_control = AccessControl()
        self.audit_logger = AuditLogger()
        
        # Setup default roles
        self._setup_default_roles()
    
    def _setup_default_roles(self) -> None:
        """Setup default access control roles."""
        self.access_control.assign_role("system", "admin")
        self.access_control.assign_role("telemetry_service", "system")
        
        # Set resource permissions
        self.access_control.set_resource_permissions("telemetry_data", {"read", "write"})
        self.access_control.set_resource_permissions("security_config", {"manage"})
        self.access_control.set_resource_permissions("audit_logs", {"read"})
    
    async def secure_telemetry_data(self, 
                                   data: Dict, 
                                   classification: DataClassification,
                                   user_id: Optional[str] = None) -> Dict:
        """Apply security measures to telemetry data."""
        # Check access permissions
        if user_id and not self.access_control.check_permission(user_id, "telemetry_data", "write"):
            self.audit_logger.log_event(
                event_type="access",
                user_id=user_id,
                resource="telemetry_data",
                action="secure_data",
                outcome="denied",
                details={"classification": classification.value},
                severity="warning"
            )
            raise TelemetryError("Access denied")
        
        secured_data = data.copy()
        
        # Apply anonymization
        if self.policy.anonymization_enabled:
            secured_data = self.anonymization.anonymize_telemetry_event(secured_data)
        
        # Apply encryption for sensitive data
        if self.policy.encryption_enabled and classification == DataClassification.SENSITIVE:
            secured_data = self.encryption.encrypt_field(secured_data, "sensitive_data")
        
        # Log security event
        self.audit_logger.log_event(
            event_type="data_processing",
            user_id=user_id,
            resource="telemetry_data",
            action="secure",
            outcome="success",
            details={"classification": classification.value, "encrypted": self.policy.encryption_enabled},
            severity="info"
        )
        
        return secured_data
    
    async def access_telemetry_data(self,
                                   data: Dict,
                                   classification: DataClassification,
                                   user_id: Optional[str] = None) -> Dict:
        """Access telemetry data with security checks."""
        # Check access permissions
        if user_id and not self.access_control.check_permission(user_id, "telemetry_data", "read"):
            self.audit_logger.log_event(
                event_type="access",
                user_id=user_id,
                resource="telemetry_data",
                action="read",
                outcome="denied",
                details={"classification": classification.value},
                severity="warning"
            )
            raise TelemetryError("Access denied")
        
        accessed_data = data.copy()
        
        # Decrypt sensitive data if needed
        if self.policy.encryption_enabled and classification == DataClassification.SENSITIVE:
            accessed_data = self.encryption.decrypt_field(accessed_data, "sensitive_data")
        
        # Log access event
        self.audit_logger.log_event(
            event_type="access",
            user_id=user_id,
            resource="telemetry_data",
            action="read",
            outcome="success",
            details={"classification": classification.value},
            severity="info"
        )
        
        return accessed_data
    
    def rotate_encryption_key(self) -> None:
        """Rotate encryption key."""
        old_key = self.encryption.master_key
        self.encryption = DataEncryption()
        
        self.audit_logger.log_event(
            event_type="key_rotation",
            user_id="system",
            resource="encryption_key",
            action="rotate",
            outcome="success",
            details={"key_length": len(self.encryption.master_key)},
            severity="info"
        )
        
        logger.info("Encryption key rotated successfully")
    
    def generate_security_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive security report."""
        return self.audit_logger.generate_security_report(days)
    
    def check_compliance(self, standards: List[str]) -> Dict[str, bool]:
        """Check compliance with security standards."""
        compliance_status = {}
        
        for standard in standards:
            if standard == "GDPR":
                compliance_status[standard] = self._check_gdpr_compliance()
            elif standard == "CCPA":
                compliance_status[standard] = self._check_ccpa_compliance()
            elif standard == "SOC2":
                compliance_status[standard] = self._check_soc2_compliance()
            else:
                compliance_status[standard] = False
        
        return compliance_status
    
    def _check_gdpr_compliance(self) -> bool:
        """Check GDPR compliance."""
        # Basic GDPR checks
        return (
            self.policy.anonymization_enabled and
            self.policy.audit_logging_enabled and
            self.policy.encryption_enabled
        )
    
    def _check_ccpa_compliance(self) -> bool:
        """Check CCPA compliance."""
        # Basic CCPA checks
        return (
            self.policy.audit_logging_enabled and
            self.policy.access_control_enabled
        )
    
    def _check_soc2_compliance(self) -> bool:
        """Check SOC2 compliance."""
        # Basic SOC2 checks
        return (
            self.policy.encryption_enabled and
            self.policy.audit_logging_enabled and
            self.policy.access_control_enabled
        )


# Global security manager instance
_security_manager = None


def get_security_manager() -> SecurityManager:
    """Get global security manager instance."""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager


async def secure_telemetry_event(event: Dict, classification: DataClassification, user_id: Optional[str] = None) -> Dict:
    """Secure telemetry event with global security manager."""
    security_manager = get_security_manager()
    return await security_manager.secure_telemetry_data(event, classification, user_id)


async def access_telemetry_event(event: Dict, classification: DataClassification, user_id: Optional[str] = None) -> Dict:
    """Access telemetry event with global security manager."""
    security_manager = get_security_manager()
    return await security_manager.access_telemetry_data(event, classification, user_id)
