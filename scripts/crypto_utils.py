"""
Encryption utilities for the Telegram Expense Bot.
Provides functions to securely encrypt and decrypt expense data.
"""
import os
import base64
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Tuple, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

def derive_key(passphrase: str, salt: bytes = None) -> Tuple[bytes, bytes]:
    """
    Derive a secure encryption key from a passphrase.
    
    Args:
        passphrase: User's secret passphrase
        salt: Optional salt (generated if not provided)
        
    Returns:
        Tuple of (key, salt) where key is bytes and salt is bytes
    """
    if salt is None:
        salt = os.urandom(16)  # 16 bytes = 128 bits
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 32 bytes = 256 bits
        salt=salt,
        iterations=480000,  # OWASP recommended minimum as of 2023
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
    return key, salt

class ExpenseEncryptor:
    """Handles encryption and decryption of expense data."""
    
    def __init__(self, passphrase: str, salt: bytes = None):
        """
        Initialize with a passphrase and optional salt.
        
        Args:
            passphrase: User's secret passphrase
            salt: Optional salt (generated if not provided)
        """
        self.passphrase = passphrase
        self.key, self.salt = derive_key(passphrase, salt)
        self.fernet = Fernet(self.key)
    
    def encrypt_expense(self, expense_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt sensitive fields in expense data.
        
        Args:
            expense_data: Dictionary containing expense fields
            
        Returns:
            New dictionary with encrypted fields
        """
        encrypted = expense_data.copy()
        
        # Encrypt sensitive fields
        if 'date' in expense_data:
            encrypted['date'] = self.fernet.encrypt(
                expense_data['date'].encode()
            ).decode()

        if 'amount' in expense_data:
            encrypted['amount'] = self.fernet.encrypt(
                str(expense_data['amount']).encode()
            ).decode()
            
        if 'category' in expense_data:
            encrypted['category'] = self.fernet.encrypt(
                expense_data['category'].encode()
            ).decode()
            
        if 'description' in expense_data and expense_data['description']:
            encrypted['description'] = self.fernet.encrypt(
                expense_data['description'].encode()
            ).decode()
            
        return encrypted
    
    def decrypt_expense(self, encrypted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt sensitive fields in expense data.
        
        Args:
            encrypted_data: Dictionary containing encrypted fields
            
        Returns:
            New dictionary with decrypted fields
            
        Raises:
            InvalidToken: If decryption fails (wrong key or corrupted data)
        """
        decrypted = encrypted_data.copy()
        
        try:
            if 'date' in encrypted_data and encrypted_data['date']:
                decrypted['date'] = self.fernet.decrypt(
                    encrypted_data['date'].encode()
                ).decode()
            
            if 'amount' in encrypted_data and encrypted_data['amount']:
                decrypted['amount'] = float(self.fernet.decrypt(
                    encrypted_data['amount'].encode()
                ).decode())
                
            if 'category' in encrypted_data and encrypted_data['category']:
                decrypted['category'] = self.fernet.decrypt(
                    encrypted_data['category'].encode()
                ).decode()
                
            if 'description' in encrypted_data and encrypted_data['description']:
                decrypted['description'] = self.fernet.decrypt(
                    encrypted_data['description'].encode()
                ).decode()
                
        except (ValueError, TypeError) as e:
            logger.error(f"Decryption error: {e}")
            raise InvalidToken("Failed to decrypt data - invalid or corrupted data")
            
        return decrypted

    @property
    def salt_hex(self) -> str:
        """Get the salt as a hex string for storage."""
        return self.salt.hex()
    
    @classmethod
    def from_salt_hex(cls, passphrase: str, salt_hex: str) -> 'ExpenseEncryptor':
        """Create an encryptor using a previously generated salt."""
        salt = bytes.fromhex(salt_hex)
        return cls(passphrase, salt)
