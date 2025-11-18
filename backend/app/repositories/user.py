"""
User repository for UserAccount model.
Handles user authentication, lookup, and management.
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models import UserAccount, UserRole, UserStatus
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[UserAccount]):
    """Repository for user account operations."""

    def __init__(self, db: Session):
        super().__init__(UserAccount, db)

    def get_by_email(self, email: str) -> Optional[UserAccount]:
        """
        Get user by email address.

        Args:
            email: User email

        Returns:
            UserAccount or None if not found
        """
        return self.db.query(UserAccount).filter(
            UserAccount.email == email
        ).first()

    def get_by_email_with_profile(self, email: str) -> Optional[UserAccount]:
        """
        Get user by email with eagerly loaded profile.

        Args:
            email: User email

        Returns:
            UserAccount with loaded profile or None
        """
        query = self.db.query(UserAccount).filter(UserAccount.email == email)

        # Eager load appropriate profile based on role
        query = query.options(
            joinedload(UserAccount.agent_profile),
            joinedload(UserAccount.staff_profile),
            joinedload(UserAccount.student_profile)
        )

        return query.first()

    def get_by_id_with_profile(self, user_id: UUID) -> Optional[UserAccount]:
        """
        Get user by ID with eagerly loaded profile.

        Args:
            user_id: User UUID

        Returns:
            UserAccount with loaded profile or None
        """
        query = self.db.query(UserAccount).filter(UserAccount.id == user_id)

        query = query.options(
            joinedload(UserAccount.agent_profile),
            joinedload(UserAccount.staff_profile),
            joinedload(UserAccount.student_profile)
        )

        return query.first()

    def get_by_role(
        self,
        role: UserRole,
        skip: int = 0,
        limit: int = 100
    ) -> List[UserAccount]:
        """
        Get all users with specific role.

        Args:
            role: User role enum
            skip: Pagination offset
            limit: Max results

        Returns:
            List of users with role
        """
        return self.db.query(UserAccount).filter(
            UserAccount.role == role
        ).offset(skip).limit(limit).all()

    def update_last_login(self, user_id: UUID) -> bool:
        """
        Update last login timestamp.

        Args:
            user_id: User UUID

        Returns:
            True if updated, False if user not found
        """
        from datetime import datetime

        user = self.get_by_id(user_id)
        if not user:
            return False

        user.last_login_at = datetime.utcnow()
        self.db.flush()
        return True

    def create_user_with_profile(
        self,
        email: str,
        password_hash: str,
        role: UserRole,
        rto_profile_id: UUID,
        profile_data: dict
    ) -> UserAccount:
        """
        Create user account with associated profile.

        Args:
            email: User email
            password_hash: Hashed password
            role: User role
            rto_profile_id: RTO profile UUID
            profile_data: Profile-specific data

        Returns:
            Created UserAccount with profile
        """
        # Create user account
        user = self.create(
            email=email,
            password_hash=password_hash,
            role=role,
            rto_profile_id=rto_profile_id,
            status=UserStatus.ACTIVE
        )

        # Create associated profile based on role
        from app.models import AgentProfile, StaffProfile, StudentProfile

        if role == UserRole.AGENT:
            agent = AgentProfile(
                user_account_id=user.id,
                **profile_data
            )
            self.db.add(agent)
        elif role == UserRole.STAFF or role == UserRole.ADMIN:
            staff = StaffProfile(
                user_account_id=user.id,
                **profile_data
            )
            self.db.add(staff)
        elif role == UserRole.STUDENT:
            student = StudentProfile(
                user_account_id=user.id,
                **profile_data
            )
            self.db.add(student)

        self.db.flush()
        self.db.refresh(user)
        return user

    def is_active(self, user_id: UUID) -> bool:
        """
        Check if user account is active.

        Args:
            user_id: User UUID

        Returns:
            True if active, False otherwise
        """
        user = self.get_by_id(user_id)
        return user is not None and user.status == UserStatus.ACTIVE

    def deactivate(self, user_id: UUID) -> bool:
        """
        Deactivate user account.

        Args:
            user_id: User UUID

        Returns:
            True if deactivated, False if not found
        """
        user = self.get_by_id(user_id)
        if not user:
            return False

        user.status = UserStatus.INACTIVE
        self.db.flush()
        return True

    def activate(self, user_id: UUID) -> bool:
        """
        Activate user account.

        Args:
            user_id: User UUID

        Returns:
            True if activated, False if not found
        """
        user = self.get_by_id(user_id)
        if not user:
            return False

        user.status = UserStatus.ACTIVE
        self.db.flush()
        return True
