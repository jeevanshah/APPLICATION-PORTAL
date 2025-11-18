"""
Authentication service.
Handles user authentication, JWT token generation, and password management.
"""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models import UserAccount, UserRole, UserStatus
from app.repositories.user import UserRepository


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class AuthorizationError(Exception):
    """Raised when authorization fails."""
    pass


class AuthService:
    """Authentication and authorization service."""

    def __init__(self, db: Session):
        """
        Initialize auth service.

        Args:
            db: Database session
        """
        self.db = db
        self.user_repo = UserRepository(db)

    def authenticate(self, email: str, password: str) -> Optional[UserAccount]:
        """
        Authenticate user with email and password.

        Args:
            email: User email
            password: Plain text password

        Returns:
            UserAccount if authenticated

        Raises:
            AuthenticationError: If credentials are invalid
        """
        # Get user by email
        user = self.user_repo.get_by_email_with_profile(email)

        if not user:
            raise AuthenticationError("Invalid email or password")

        # Check account status
        if user.status != UserStatus.ACTIVE:
            raise AuthenticationError(f"Account is {user.status.value}")

        # Verify password
        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password")

        # Update last login
        self.user_repo.update_last_login(user.id)
        self.db.commit()

        return user

    def create_token(self, user: UserAccount) -> dict:
        """
        Create JWT access token for user.

        Args:
            user: UserAccount

        Returns:
            Dictionary with token and token type
        """
        # Prepare token data
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
        }

        # Add profile ID based on role
        if user.role == UserRole.AGENT and user.agent_profile:
            token_data["agent_profile_id"] = str(user.agent_profile.id)
        elif user.role == UserRole.STUDENT and user.student_profile:
            token_data["student_profile_id"] = str(user.student_profile.id)
        elif user.role in [UserRole.STAFF, UserRole.ADMIN] and user.staff_profile:
            token_data["staff_profile_id"] = str(user.staff_profile.id)

        # Create access token
        access_token = create_access_token(data=token_data)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # in seconds
        }

    def login(self, email: str, password: str) -> dict:
        """
        Complete login flow: authenticate and return token.

        Args:
            email: User email
            password: Plain text password

        Returns:
            Dictionary with token, user info

        Raises:
            AuthenticationError: If authentication fails
        """
        user = self.authenticate(email, password)
        token_data = self.create_token(user)

        # Return token with user info
        return {
            **token_data,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role.value,
                "status": user.status.value,
            }
        }

    def get_current_user(self, user_id: UUID) -> Optional[UserAccount]:
        """
        Get current user from token payload.

        Args:
            user_id: User UUID from JWT token

        Returns:
            UserAccount with loaded profile

        Raises:
            AuthenticationError: If user not found or inactive
        """
        user = self.user_repo.get_by_id_with_profile(user_id)

        if not user:
            raise AuthenticationError("User not found")

        if user.status != UserStatus.ACTIVE:
            raise AuthenticationError(f"Account is {user.status.value}")

        return user

    def check_permission(
        self,
        user: UserAccount,
        required_roles: list[UserRole]
    ) -> bool:
        """
        Check if user has one of the required roles.

        Args:
            user: UserAccount
            required_roles: List of allowed roles

        Returns:
            True if user has permission

        Raises:
            AuthorizationError: If user lacks permission
        """
        if user.role not in required_roles:
            raise AuthorizationError(
                f"Permission denied. Required roles: {[r.value for r in required_roles]}"
            )

        return True

    def register_user(
        self,
        email: str,
        password: str,
        role: UserRole,
        rto_profile_id: UUID,
        profile_data: dict
    ) -> UserAccount:
        """
        Register new user with profile.

        Args:
            email: User email
            password: Plain text password
            role: User role
            rto_profile_id: RTO profile UUID
            profile_data: Role-specific profile data

        Returns:
            Created UserAccount

        Raises:
            ValueError: If email already exists
        """
        # Check if email exists
        existing = self.user_repo.get_by_email(email)
        if existing:
            raise ValueError("Email already registered")

        # Hash password
        password_hash = get_password_hash(password)

        # Create user with profile
        user = self.user_repo.create_user_with_profile(
            email=email,
            password_hash=password_hash,
            role=role,
            rto_profile_id=rto_profile_id,
            profile_data=profile_data
        )

        self.db.commit()
        return user

    def change_password(
        self,
        user_id: UUID,
        old_password: str,
        new_password: str
    ) -> bool:
        """
        Change user password.

        Args:
            user_id: User UUID
            old_password: Current password
            new_password: New password

        Returns:
            True if changed successfully

        Raises:
            AuthenticationError: If old password is incorrect
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")

        # Verify old password
        if not verify_password(old_password, user.password_hash):
            raise AuthenticationError("Current password is incorrect")

        # Update to new password
        new_hash = get_password_hash(new_password)
        user.password_hash = new_hash

        self.db.commit()
        return True

    def reset_password(
        self,
        email: str,
        new_password: str
    ) -> bool:
        """
        Reset user password (admin function).

        Args:
            email: User email
            new_password: New password

        Returns:
            True if reset successfully

        Raises:
            ValueError: If user not found
        """
        user = self.user_repo.get_by_email(email)
        if not user:
            raise ValueError("User not found")

        # Update password
        new_hash = get_password_hash(new_password)
        user.password_hash = new_hash

        self.db.commit()
        return True

    def deactivate_user(self, user_id: UUID) -> bool:
        """
        Deactivate user account.

        Args:
            user_id: User UUID

        Returns:
            True if deactivated
        """
        result = self.user_repo.deactivate(user_id)
        if result:
            self.db.commit()
        return result

    def activate_user(self, user_id: UUID) -> bool:
        """
        Activate user account.

        Args:
            user_id: User UUID

        Returns:
            True if activated
        """
        result = self.user_repo.activate(user_id)
        if result:
            self.db.commit()
        return result
