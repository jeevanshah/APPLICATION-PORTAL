"""
Security utilities: password hashing, JWT tokens, MFA.
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
import pyotp

from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password."""
    # Encode strings to bytes
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def get_password_hash(password: str) -> str:
    """Hash a plain password."""
    # Encode password to bytes and hash
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    # Return as string
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.
    
    Args:
        data: Payload data (include user_id, email, role, rto_profile_id)
        expires_delta: Optional custom expiration time
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Create JWT refresh token (longer expiration).
    
    Args:
        data: Payload data (minimal: user_id only)
    
    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and verify JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded payload dict or None if invalid
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_mfa_secret() -> str:
    """Generate random base32 secret for TOTP MFA."""
    return pyotp.random_base32()


def verify_totp_token(secret: str, token: str) -> bool:
    """
    Verify TOTP token against secret.
    
    Args:
        secret: Base32 encoded secret
        token: 6-digit TOTP code
    
    Returns:
        True if valid, False otherwise
    """
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=1)  # Allow 30s time drift


def get_totp_provisioning_uri(secret: str, email: str) -> str:
    """
    Get TOTP provisioning URI for QR code generation.
    
    Args:
        secret: Base32 encoded secret
        email: User email
    
    Returns:
        otpauth:// URI string
    """
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=settings.APP_NAME)
