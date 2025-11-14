#!/usr/bin/env python3
"""Cryptography utilities for email encryption keys"""

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
import base64
import json

def generate_email_keypair():
    """
    Generate RSA key pair for email encryption

    Returns:
        tuple: (private_key, public_key) as cryptography objects
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()

    return private_key, public_key


def serialize_public_key(public_key):
    """
    Convert public key to PEM format string

    Args:
        public_key: RSA public key object

    Returns:
        str: PEM-encoded public key
    """
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return pem.decode('utf-8')


def serialize_private_key(private_key):
    """
    Convert private key to PEM format string (unencrypted)

    Args:
        private_key: RSA private key object

    Returns:
        str: PEM-encoded private key
    """
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    return pem.decode('utf-8')


def deserialize_public_key(pem_string):
    """
    Convert PEM string to public key object

    Args:
        pem_string: PEM-encoded public key

    Returns:
        RSA public key object
    """
    return serialization.load_pem_public_key(
        pem_string.encode('utf-8'),
        backend=default_backend()
    )


def deserialize_private_key(pem_string):
    """
    Convert PEM string to private key object

    Args:
        pem_string: PEM-encoded private key

    Returns:
        RSA private key object
    """
    return serialization.load_pem_private_key(
        pem_string.encode('utf-8'),
        password=None,
        backend=default_backend()
    )


def encrypt_private_key_with_recovery_key(private_key_pem, recovery_key):
    """
    Encrypt private key using PortID recovery key (AES encryption)

    This uses the same AES encryption as PortID SDK to maintain compatibility.

    Args:
        private_key_pem: PEM-encoded private key string
        recovery_key: PortID recovery key (hex string)

    Returns:
        str: Base64-encoded encrypted private key
    """
    # Convert recovery key from hex to bytes
    key_bytes = bytes.fromhex(recovery_key)

    # Prepare data
    data = {"private_key": private_key_pem}
    data_json = json.dumps(data).encode('utf-8')

    # Pad data to AES block size
    padded_data = pad(data_json, AES.block_size)

    # Generate random IV
    iv = get_random_bytes(AES.block_size)

    # Encrypt with AES-CBC
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(padded_data)

    # Combine IV + ciphertext and encode
    encrypted = iv + ciphertext
    return base64.b64encode(encrypted).decode('utf-8')


def decrypt_private_key_with_recovery_key(encrypted_data, recovery_key):
    """
    Decrypt private key using PortID recovery key

    Args:
        encrypted_data: Base64-encoded encrypted private key
        recovery_key: PortID recovery key (hex string)

    Returns:
        str: PEM-encoded private key
    """
    try:
        # Convert recovery key from hex to bytes
        key_bytes = bytes.fromhex(recovery_key)

        # Decode base64
        encrypted = base64.b64decode(encrypted_data)

        # Extract IV and ciphertext
        iv = encrypted[:AES.block_size]
        ciphertext = encrypted[AES.block_size:]

        # Decrypt with AES-CBC
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
        padded_data = cipher.decrypt(ciphertext)

        # Unpad
        data_json = unpad(padded_data, AES.block_size)

        # Parse JSON
        data = json.loads(data_json.decode('utf-8'))

        return data['private_key']

    except Exception as e:
        print(f"Error decrypting private key: {e}")
        return None


def encrypt_email_content(content, public_key_pem):
    """
    Encrypt email content with recipient's public key

    Args:
        content: Email content (string)
        public_key_pem: Recipient's PEM-encoded public key

    Returns:
        str: Base64-encoded encrypted content
    """
    public_key = deserialize_public_key(public_key_pem)

    # Encrypt with RSA-OAEP
    encrypted = public_key.encrypt(
        content.encode('utf-8'),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    return base64.b64encode(encrypted).decode('utf-8')


def decrypt_email_content(encrypted_content, private_key_pem):
    """
    Decrypt email content with own private key

    Args:
        encrypted_content: Base64-encoded encrypted content
        private_key_pem: Own PEM-encoded private key

    Returns:
        str: Decrypted email content
    """
    try:
        private_key = deserialize_private_key(private_key_pem)

        # Decode base64
        encrypted = base64.b64decode(encrypted_content)

        # Decrypt with RSA-OAEP
        decrypted = private_key.decrypt(
            encrypted,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        return decrypted.decode('utf-8')

    except Exception as e:
        print(f"Error decrypting email content: {e}")
        return None
