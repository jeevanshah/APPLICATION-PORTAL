"""
Authentication endpoints: login, register, MFA setup, token refresh.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_password_reset_token,
    decode_token,
    generate_mfa_secret,
    get_password_hash,
    get_totp_provisioning_uri,
    verify_password_reset_token,
    verify_totp_token,
)
from app.db.database import get_db
from app.models import RtoProfile, UserAccount, UserRole, UserStatus
from app.services.auth import AuthenticationError, AuthService

router = APIRouter()


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str
    role: UserRole
    rto_profile_id: UUID
    given_name: str | None = None
    family_name: str | None = None


class LoginResponse(BaseModel):
    """Login response with tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: UUID
    email: str
    role: str
    mfa_required: bool = False


class MfaSetupResponse(BaseModel):
    """MFA setup response with QR code URI."""
    secret: str
    qr_code_uri: str


class MfaVerifyRequest(BaseModel):
    """MFA verification request."""
    token: str


class TokenRefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    """Forgot password request."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password request."""
    token: str
    new_password: str


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/register", response_model=LoginResponse,
             status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.

    **Note**: In production, add email verification and captcha.
    """
    # Check if email already exists
    existing_user = db.query(UserAccount).filter(
        UserAccount.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Validate RTO profile exists
    rto = db.query(RtoProfile).filter(
        RtoProfile.id == request.rto_profile_id).first()
    if not rto:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid RTO profile ID"
        )

    # Create user account
    hashed_password = get_password_hash(request.password)
    new_user = UserAccount(
        email=request.email,
        password_hash=hashed_password,
        role=request.role,
        rto_profile_id=request.rto_profile_id,
        status=UserStatus.ACTIVE
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create access and refresh tokens
    token_data = {
        "sub": str(new_user.id),
        "email": new_user.email,
        "role": new_user.role.value,
        "rto_profile_id": str(new_user.rto_profile_id)
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token({"sub": str(new_user.id)})

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=new_user.id,
        email=new_user.email,
        role=new_user.role.value,
        mfa_required=new_user.mfa_enabled
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login with email and password.
    Returns JWT access and refresh tokens.
    """
    auth_service = AuthService(db)

    try:
        # Authenticate and get token
        result = auth_service.login(
            email=form_data.username,
            password=form_data.password
        )

        # Get user for additional info
        user = auth_service.get_current_user(UUID(result["user"]["id"]))

        # Create refresh token (not in service yet, keep existing logic)
        refresh_token = create_refresh_token({"sub": result["user"]["id"]})

        return LoginResponse(
            access_token=result["access_token"],
            refresh_token=refresh_token,
            user_id=UUID(result["user"]["id"]),
            email=result["user"]["email"],
            role=result["user"]["role"],
            mfa_required=user.mfa_enabled
        )

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    request: TokenRefreshRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    payload = decode_token(request.refresh_token)

    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    user_id = payload.get("sub")
    user = db.query(UserAccount).filter(UserAccount.id == user_id).first()

    if not user or user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Create new tokens
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "rto_profile_id": str(user.rto_profile_id)
    }
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token({"sub": str(user.id)})

    return LoginResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        user_id=user.id,
        email=user.email,
        role=user.role.value,
        mfa_required=user.mfa_enabled
    )


@router.post("/mfa/setup", response_model=MfaSetupResponse)
async def setup_mfa(
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate MFA secret and QR code URI for TOTP setup.
    User must verify with /mfa/verify before MFA is enabled.
    """
    if current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA already enabled"
        )

    # Generate new secret
    secret = generate_mfa_secret()
    current_user.mfa_secret = secret
    db.commit()

    # Generate QR code URI for authenticator apps
    qr_uri = get_totp_provisioning_uri(secret, current_user.email)

    return MfaSetupResponse(
        secret=secret,
        qr_code_uri=qr_uri
    )


@router.post("/mfa/verify")
async def verify_mfa(
    request: MfaVerifyRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify TOTP token and enable MFA.
    """
    if not current_user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA not set up. Call /mfa/setup first"
        )

    # Verify TOTP token
    if not verify_totp_token(current_user.mfa_secret, request.token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA token"
        )

    # Enable MFA
    current_user.mfa_enabled = True
    db.commit()

    return {"message": "MFA enabled successfully"}


@router.post("/mfa/disable")
async def disable_mfa(
    request: MfaVerifyRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disable MFA after verifying current TOTP token.
    """
    if not current_user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA not enabled"
        )

    # Verify TOTP token before disabling
    if not verify_totp_token(current_user.mfa_secret, request.token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MFA token"
        )

    # Disable MFA
    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    db.commit()

    return {"message": "MFA disabled successfully"}


@router.get("/me")
async def get_current_user_info(
        current_user: UserAccount = Depends(get_current_user)):
    """
    Get current authenticated user information.
    """
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "role": current_user.role.value,
        "status": current_user.status.value,
        "rto_profile_id": current_user.rto_profile_id,
        "mfa_enabled": current_user.mfa_enabled,
        "created_at": current_user.created_at,
        "last_login_at": current_user.last_login_at
    }


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Request password reset email.
    Sends an email with a reset token that expires in 30 minutes.
    
    **Security Note**: Returns success even if email doesn't exist
    to prevent email enumeration attacks.
    """
    # Look up user
    user = db.query(UserAccount).filter(
        UserAccount.email == request.email
    ).first()
    
    # Always return success to prevent email enumeration
    # But only send email if user exists
    if user:
        # Generate reset token
        reset_token = create_password_reset_token(user.email)
        
        # In production, send email here
        # For now, we'll log it or use a simple email utility
        from app.utils.email import send_password_reset_email
        try:
            send_password_reset_email(
                email=user.email,
                token=reset_token,
                user_name=user.email.split('@')[0]
            )
        except Exception as e:
            # Log error but don't expose it to user
            print(f"Failed to send password reset email: {e}")
    
    # Always return success message
    return {
        "message": "If the email exists, a password reset link has been sent."
    }


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Reset password using the token from forgot-password email.
    """
    # Verify token and get email
    email = verify_password_reset_token(request.token)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token"
        )
    
    # Get user
    user = db.query(UserAccount).filter(
        UserAccount.email == email
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update password
    user.password_hash = get_password_hash(request.new_password)
    db.commit()
    
    return {
        "message": "Password has been reset successfully. You can now log in with your new password."
    }
