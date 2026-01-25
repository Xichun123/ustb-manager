"""
BYYT API encryption utility.

BYYT system requires AES-CBC encrypted request data for certain APIs.
"""
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad


# BYYT uses a fixed key and IV (hex string representing "1234567890123456")
SECRET_KEY = bytes.fromhex("31323334353637383930313233343536")
SECRET_IV = bytes.fromhex("31323334353637383930313233343536")


def encrypt(data: str) -> str:
    """
    Encrypt data using AES-CBC with zero padding.

    Args:
        data: The plaintext string to encrypt (usually JSON or empty string)

    Returns:
        Base64 encoded ciphertext
    """
    if data is None:
        data = "null"

    # Convert to bytes
    plaintext = data.encode('utf-8')

    # Pad to AES block size (16 bytes) using zero padding
    block_size = AES.block_size
    if len(plaintext) % block_size != 0:
        plaintext = plaintext + b'\x00' * (block_size - len(plaintext) % block_size)

    # Create cipher and encrypt
    cipher = AES.new(SECRET_KEY, AES.MODE_CBC, SECRET_IV)
    ciphertext = cipher.encrypt(plaintext)

    # Return base64 encoded
    return base64.b64encode(ciphertext).decode('utf-8')


def encrypt_empty() -> str:
    """Encrypt empty/null data - common case for BYYT APIs."""
    return encrypt("{}")
