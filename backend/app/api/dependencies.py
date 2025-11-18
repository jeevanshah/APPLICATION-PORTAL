"""
Authentication and authorization dependencies.
Provides JWT token validation, current user extraction, and role-based access control.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.database import get_db
from app.models import UserAccount, UserRole, UserStatus

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> UserAccount:
    """
    Extract and validate current user from JWT token.

    Raises:
        HTTPException 401: If token is invalid or user not found
        HTTPException 403: If user account is not active
    """
    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user_id from token
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user from database
    user = db.query(UserAccount).filter(UserAccount.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check user status
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.status.value}"
        )

    return user


async def get_current_active_user(
    current_user: UserAccount = Depends(get_current_user)
) -> UserAccount:
    """
    Alias for get_current_user (for compatibility with common patterns).
    """
    return current_user


class RoleChecker:
    """
    Dependency class for role-based access control.

    Usage:
        @app.get("/admin")
        async def admin_only(user: UserAccount = Depends(RoleChecker([UserRole.ADMIN]))):
            ...
    """

    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: UserAccount = Depends(
            get_current_user)) -> UserAccount:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in self.allowed_roles]}"
            )
        return current_user


# Convenience role checkers
require_admin = RoleChecker([UserRole.ADMIN])
require_staff = RoleChecker([UserRole.ADMIN, UserRole.STAFF])
require_agent = RoleChecker([UserRole.ADMIN, UserRole.STAFF, UserRole.AGENT])
require_student = RoleChecker([UserRole.STUDENT])


def get_rto_filter(current_user: UserAccount = Depends(
        get_current_user)) -> str:
    """
    Extract RTO profile ID for multi-tenancy filtering.

    Returns:
        RTO profile UUID string for filtering queries

    Usage:
        @app.get("/applications")
        async def list_applications(
            rto_id: str = Depends(get_rto_filter),
            db: Session = Depends(get_db)
        ):
            applications = db.query(Application).join(StudentProfile).join(UserAccount).filter(
                UserAccount.rto_profile_id == rto_id
            ).all()
    """
    return str(current_user.rto_profile_id)
