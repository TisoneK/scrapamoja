"""
State Encryption Utilities

This module provides encryption utilities for browser state data,
particularly for authentication tokens and sensitive information.
"""

import base64
import json
import hashlib
from typing import Dict, Any, Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import structlog


class StateEncryption:
    """Handles encryption and decryption of browser state data."""
    
    def __init__(self, encryption_key: str, salt: Optional[bytes] = None):
        self.encryption_key = encryption_key
        self.salt = salt or b'scorewise_browser_state_v1'
        self.logger = structlog.get_logger("browser.encryption")
        
        # Initialize cipher suites
        self._fernet_cipher = self._create_fernet_cipher()
        
    def _create_fernet_cipher(self) -> Fernet:
        """Create Fernet cipher for general encryption."""
        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self.salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.encryption_key.encode()))
            return Fernet(key)
        except Exception as e:
            self.logger.error(
                "Failed to create Fernet cipher",
                error=str(e),
                error_type=type(e).__name__
            )
            raise ValueError(f"Failed to initialize encryption: {e}")
            
    def encrypt_authentication_tokens(self, tokens: Dict[str, Any]) -> bytes:
        """Encrypt authentication tokens with additional security."""
        try:
            # Add metadata to tokens
            encrypted_data = {
                "tokens": tokens,
                "timestamp": self._get_timestamp(),
                "version": "1.0",
                "type": "auth_tokens"
            }
            
            # Serialize and encrypt
            token_json = json.dumps(encrypted_data, ensure_ascii=False)
            return self._fernet_cipher.encrypt(token_json.encode('utf-8'))
            
        except Exception as e:
            self.logger.error(
                "Failed to encrypt authentication tokens",
                error=str(e),
                error_type=type(e).__name__
            )
            raise ValueError(f"Failed to encrypt tokens: {e}")
            
    def decrypt_authentication_tokens(self, encrypted_data: bytes) -> Dict[str, Any]:
        """Decrypt authentication tokens with validation."""
        try:
            # Decrypt
            decrypted_data = self._fernet_cipher.decrypt(encrypted_data)
            token_data = json.loads(decrypted_data.decode('utf-8'))
            
            # Validate structure
            if not self._validate_token_structure(token_data):
                raise ValueError("Invalid token structure")
                
            return token_data["tokens"]
            
        except Exception as e:
            self.logger.error(
                "Failed to decrypt authentication tokens",
                error=str(e),
                error_type=type(e).__name__
            )
            raise ValueError(f"Failed to decrypt tokens: {e}")
            
    def encrypt_cookies(self, cookies: list) -> bytes:
        """Encrypt cookie data."""
        try:
            # Add metadata
            encrypted_data = {
                "cookies": cookies,
                "timestamp": self._get_timestamp(),
                "version": "1.0",
                "type": "cookies"
            }
            
            # Serialize and encrypt
            cookie_json = json.dumps(encrypted_data, ensure_ascii=False)
            return self._fernet_cipher.encrypt(cookie_json.encode('utf-8'))
            
        except Exception as e:
            self.logger.error(
                "Failed to encrypt cookies",
                error=str(e),
                error_type=type(e).__name__
            )
            raise ValueError(f"Failed to encrypt cookies: {e}")
            
    def decrypt_cookies(self, encrypted_data: bytes) -> list:
        """Decrypt cookie data."""
        try:
            # Decrypt
            decrypted_data = self._fernet_cipher.decrypt(encrypted_data)
            cookie_data = json.loads(decrypted_data.decode('utf-8'))
            
            # Validate structure
            if not self._validate_cookie_structure(cookie_data):
                raise ValueError("Invalid cookie structure")
                
            return cookie_data["cookies"]
            
        except Exception as e:
            self.logger.error(
                "Failed to decrypt cookies",
                error=str(e),
                error_type=type(e).__name__
            )
            raise ValueError(f"Failed to decrypt cookies: {e}")
            
    def encrypt_storage_data(self, storage_data: Dict[str, str], storage_type: str) -> bytes:
        """Encrypt local/session storage data."""
        try:
            # Add metadata
            encrypted_data = {
                "storage": storage_data,
                "storage_type": storage_type,
                "timestamp": self._get_timestamp(),
                "version": "1.0",
                "type": "storage"
            }
            
            # Serialize and encrypt
            storage_json = json.dumps(encrypted_data, ensure_ascii=False)
            return self._fernet_cipher.encrypt(storage_json.encode('utf-8'))
            
        except Exception as e:
            self.logger.error(
                "Failed to encrypt storage data",
                storage_type=storage_type,
                error=str(e),
                error_type=type(e).__name__
            )
            raise ValueError(f"Failed to encrypt {storage_type}: {e}")
            
    def decrypt_storage_data(self, encrypted_data: bytes) -> tuple[Dict[str, str], str]:
        """Decrypt storage data."""
        try:
            # Decrypt
            decrypted_data = self._fernet_cipher.decrypt(encrypted_data)
            storage_data = json.loads(decrypted_data.decode('utf-8'))
            
            # Validate structure
            if not self._validate_storage_structure(storage_data):
                raise ValueError("Invalid storage structure")
                
            return storage_data["storage"], storage_data["storage_type"]
            
        except Exception as e:
            self.logger.error(
                "Failed to decrypt storage data",
                error=str(e),
                error_type=type(e).__name__
            )
            raise ValueError(f"Failed to decrypt storage: {e}")
            
    def create_secure_hash(self, data: Union[str, bytes, Dict[str, Any]]) -> str:
        """Create secure hash of data for integrity verification."""
        try:
            if isinstance(data, dict):
                data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
            elif isinstance(data, str):
                data_str = data
            else:
                data_str = data.decode('utf-8') if isinstance(data, bytes) else str(data)
                
            # Create hash
            hash_obj = hashlib.sha256()
            hash_obj.update(data_str.encode('utf-8'))
            hash_obj.update(self.salt)
            
            return base64.urlsafe_b64encode(hash_obj.digest()).decode('utf-8')
            
        except Exception as e:
            self.logger.error(
                "Failed to create secure hash",
                error=str(e),
                error_type=type(e).__name__
            )
            raise ValueError(f"Failed to create hash: {e}")
            
    def verify_integrity(self, data: Union[str, bytes, Dict[str, Any]], expected_hash: str) -> bool:
        """Verify data integrity using secure hash."""
        try:
            actual_hash = self.create_secure_hash(data)
            return actual_hash == expected_hash
            
        except Exception as e:
            self.logger.error(
                "Failed to verify integrity",
                error=str(e),
                error_type=type(e).__name__
            )
            return False
            
    def encrypt_sensitive_field(self, field_value: str, field_name: str) -> str:
        """Encrypt a single sensitive field."""
        try:
            field_data = {
                "value": field_value,
                "field_name": field_name,
                "timestamp": self._get_timestamp(),
                "version": "1.0"
            }
            
            field_json = json.dumps(field_data, ensure_ascii=False)
            encrypted_bytes = self._fernet_cipher.encrypt(field_json.encode('utf-8'))
            
            # Return as base64 string for storage
            return base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')
            
        except Exception as e:
            self.logger.error(
                "Failed to encrypt sensitive field",
                field_name=field_name,
                error=str(e),
                error_type=type(e).__name__
            )
            raise ValueError(f"Failed to encrypt field {field_name}: {e}")
            
    def decrypt_sensitive_field(self, encrypted_field: str) -> tuple[str, str]:
        """Decrypt a single sensitive field."""
        try:
            # Decode from base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_field.encode('utf-8'))
            
            # Decrypt
            decrypted_data = self._fernet_cipher.decrypt(encrypted_bytes)
            field_data = json.loads(decrypted_data.decode('utf-8'))
            
            # Validate structure
            if not isinstance(field_data, dict) or "value" not in field_data:
                raise ValueError("Invalid encrypted field structure")
                
            return field_data["value"], field_data.get("field_name", "unknown")
            
        except Exception as e:
            self.logger.error(
                "Failed to decrypt sensitive field",
                error=str(e),
                error_type=type(e).__name__
            )
            raise ValueError(f"Failed to decrypt field: {e}")
            
    def _validate_token_structure(self, token_data: Dict[str, Any]) -> bool:
        """Validate authentication token structure."""
        required_fields = ["tokens", "timestamp", "version", "type"]
        return all(field in token_data for field in required_fields) and token_data["type"] == "auth_tokens"
        
    def _validate_cookie_structure(self, cookie_data: Dict[str, Any]) -> bool:
        """Validate cookie data structure."""
        required_fields = ["cookies", "timestamp", "version", "type"]
        return all(field in cookie_data for field in required_fields) and cookie_data["type"] == "cookies"
        
    def _validate_storage_structure(self, storage_data: Dict[str, Any]) -> bool:
        """Validate storage data structure."""
        required_fields = ["storage", "storage_type", "timestamp", "version", "type"]
        return all(field in storage_data for field in required_fields) and storage_data["type"] == "storage"
        
    def _get_timestamp(self) -> int:
        """Get current timestamp."""
        import time
        return int(time.time())
        
    def rotate_key(self, new_key: str) -> bool:
        """Rotate encryption key."""
        try:
            old_cipher = self._fernet_cipher
            self.encryption_key = new_key
            self._fernet_cipher = self._create_fernet_cipher()
            
            # Test new cipher
            test_data = b"test"
            encrypted = self._fernet_cipher.encrypt(test_data)
            decrypted = self._fernet_cipher.decrypt(encrypted)
            
            if decrypted != test_data:
                # Rollback on failure
                self._fernet_cipher = old_cipher
                self.encryption_key = new_key
                return False
                
            self.logger.info("Encryption key rotated successfully")
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to rotate encryption key",
                error=str(e),
                error_type=type(e).__name__
            )
            return False


# Global encryption instance
_encryption_instance: Optional[StateEncryption] = None


def get_encryption_manager(encryption_key: Optional[str] = None) -> StateEncryption:
    """Get or create encryption manager instance."""
    global _encryption_instance
    
    if _encryption_instance is None:
        if encryption_key is None:
            raise ValueError("Encryption key required for first initialization")
        _encryption_instance = StateEncryption(encryption_key)
        
    return _encryption_instance


def initialize_encryption(encryption_key: str) -> StateEncryption:
    """Initialize encryption with a specific key."""
    global _encryption_instance
    _encryption_instance = StateEncryption(encryption_key)
    return _encryption_instance
