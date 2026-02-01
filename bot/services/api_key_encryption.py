"""
API Key Encryption Service
Securely encrypts and decrypts Binance API keys using Fernet (symmetric encryption)
"""

import os
from cryptography.fernet import Fernet
import base64
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class APIKeyEncryption:
    """Handles encryption and decryption of API keys."""
    
    def __init__(self):
        """Initialize encryption with key from environment."""
        encryption_key = os.getenv('API_KEY_ENCRYPTION_KEY')
        
        if not encryption_key:
            # Generate new key if not found (ONLY for first-time setup)
            logger.warning("⚠️  API_KEY_ENCRYPTION_KEY not found in environment!")
            logger.warning("Generating new encryption key. ADD THIS TO YOUR .env FILE:")
            new_key = Fernet.generate_key().decode()
            logger.warning(f"API_KEY_ENCRYPTION_KEY={new_key}")
            logger.warning("⚠️  DO NOT LOSE THIS KEY! All encrypted API keys depend on it!")
            
            # Use the generated key for this session
            encryption_key = new_key
        
        try:
            self.cipher = Fernet(encryption_key.encode())
            logger.info("✅ API key encryption initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize encryption: {e}")
            raise
    
    def encrypt_api_key(self, api_key: str) -> str:
        """
        Encrypt an API key.
        
        Args:
            api_key: Plain text API key
            
        Returns:
            Encrypted API key as base64 string
        """
        try:
            if not api_key:
                raise ValueError("API key cannot be empty")
            
            encrypted = self.cipher.encrypt(api_key.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"❌ Failed to encrypt API key: {e}")
            raise
    
    def decrypt_api_key(self, encrypted_key: str) -> str:
        """
        Decrypt an API key.
        
        Args:
            encrypted_key: Encrypted API key as base64 string
            
        Returns:
            Decrypted plain text API key
        """
        try:
            if not encrypted_key:
                raise ValueError("Encrypted key cannot be empty")
            
            decrypted = self.cipher.decrypt(encrypted_key.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"❌ Failed to decrypt API key: {e}")
            raise
    
    def encrypt_key_pair(self, api_key: str, api_secret: str) -> Tuple[str, str]:
        """
        Encrypt both API key and secret.
        
        Args:
            api_key: Plain text API key
            api_secret: Plain text API secret
            
        Returns:
            Tuple of (encrypted_key, encrypted_secret)
        """
        encrypted_key = self.encrypt_api_key(api_key)
        encrypted_secret = self.encrypt_api_key(api_secret)
        return encrypted_key, encrypted_secret
    
    def decrypt_key_pair(self, encrypted_key: str, encrypted_secret: str) -> Tuple[str, str]:
        """
        Decrypt both API key and secret.
        
        Args:
            encrypted_key: Encrypted API key
            encrypted_secret: Encrypted API secret
            
        Returns:
            Tuple of (decrypted_key, decrypted_secret)
        """
        decrypted_key = self.decrypt_api_key(encrypted_key)
        decrypted_secret = self.decrypt_api_key(encrypted_secret)
        return decrypted_key, decrypted_secret
    
    def mask_api_key(self, api_key: str, show_chars: int = 4) -> str:
        """
        Mask an API key for display purposes.
        
        Args:
            api_key: Plain text API key
            show_chars: Number of characters to show at start and end
            
        Returns:
            Masked API key (e.g., "ABC...XYZ")
        """
        if not api_key or len(api_key) <= show_chars * 2:
            return "****"
        
        return f"{api_key[:show_chars]}...{api_key[-show_chars:]}"


# Singleton instance
_encryption_instance = None

def get_encryption_service() -> APIKeyEncryption:
    """Get or create the encryption service singleton."""
    global _encryption_instance
    if _encryption_instance is None:
        _encryption_instance = APIKeyEncryption()
    return _encryption_instance


# Generate encryption key helper function
def generate_encryption_key() -> str:
    """Generate a new Fernet encryption key."""
    return Fernet.generate_key().decode()


if __name__ == "__main__":
    # Test the encryption
    print("🔐 API Key Encryption Test\n")
    
    # Generate a test key
    print("Generating new encryption key...")
    key = generate_encryption_key()
    print(f"Encryption Key: {key}")
    print("⚠️  Save this to your .env file as API_KEY_ENCRYPTION_KEY\n")
    
    # Test encryption/decryption
    test_api_key = "test_api_key_12345"
    test_api_secret = "test_api_secret_67890"
    
    print(f"Original API Key: {test_api_key}")
    print(f"Original API Secret: {test_api_secret}\n")
    
    os.environ['API_KEY_ENCRYPTION_KEY'] = key
    encryption = APIKeyEncryption()
    
    # Encrypt
    encrypted_key, encrypted_secret = encryption.encrypt_key_pair(test_api_key, test_api_secret)
    print(f"Encrypted API Key: {encrypted_key}")
    print(f"Encrypted API Secret: {encrypted_secret}\n")
    
    # Decrypt
    decrypted_key, decrypted_secret = encryption.decrypt_key_pair(encrypted_key, encrypted_secret)
    print(f"Decrypted API Key: {decrypted_key}")
    print(f"Decrypted API Secret: {decrypted_secret}\n")
    
    # Verify
    if decrypted_key == test_api_key and decrypted_secret == test_api_secret:
        print("✅ Encryption/Decryption test PASSED!")
    else:
        print("❌ Encryption/Decryption test FAILED!")
    
    # Test masking
    print(f"\nMasked API Key: {encryption.mask_api_key(test_api_key)}")



