import configparser
from cryptography.fernet import Fernet
from logging_setup import setup_logging

# Load configurations from config.ini
config = configparser.ConfigParser()
config.read('config.ini')

# Configuration
ENCRYPTION_KEY = config['SECURITY']['ENCRYPTION_KEY'].encode()

# Set up logging
logger = setup_logging("encrypt_decrypt")

# Encryption Setup
def encrypt_data(data: str) -> bytes:
    """
    Encrypt data using Fernet symmetric encryption.
    """
    cipher = Fernet(ENCRYPTION_KEY)
    return cipher.encrypt(data.encode())

def decrypt_data(data: bytes) -> str:
    """
    Decrypt data using Fernet symmetric encryption.
    """
    cipher = Fernet(ENCRYPTION_KEY)
    return cipher.decrypt(data).decode()

if __name__ == "__main__":
    # Example usage
    data = "This is a test string."
    encrypted = encrypt_data(data)
    logger.info(f"Encrypted: {encrypted}")
    decrypted = decrypt_data(encrypted)
    logger.info(f"Decrypted: {decrypted}")