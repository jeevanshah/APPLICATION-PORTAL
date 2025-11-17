"""
Student profile repository.
Handles student-specific data operations.
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session, joinedload

from app.models import StudentProfile
from app.repositories.base import BaseRepository


class StudentRepository(BaseRepository[StudentProfile]):
    """Repository for student profile operations."""
    
    def __init__(self, db: Session):
        super().__init__(StudentProfile, db)
    
    def get_by_user_id(self, user_id: UUID) -> Optional[StudentProfile]:
        """
        Get student profile by user account ID.
        
        Args:
            user_id: User account UUID
            
        Returns:
            StudentProfile or None if not found
        """
        return self.db.query(StudentProfile).filter(
            StudentProfile.user_account_id == user_id
        ).first()
    
    def get_by_user_id_with_account(self, user_id: UUID) -> Optional[StudentProfile]:
        """
        Get student profile with user account eagerly loaded.
        
        Args:
            user_id: User account UUID
            
        Returns:
            StudentProfile with account or None
        """
        return self.db.query(StudentProfile).filter(
            StudentProfile.user_account_id == user_id
        ).options(
            joinedload(StudentProfile.user_account)
        ).first()
    
    def get_by_passport(self, passport_number: str) -> Optional[StudentProfile]:
        """
        Get student by passport number.
        
        Args:
            passport_number: Passport number
            
        Returns:
            StudentProfile or None if not found
        """
        return self.db.query(StudentProfile).filter(
            StudentProfile.passport_number == passport_number
        ).first()
    
    def get_with_applications(self, student_id: UUID) -> Optional[StudentProfile]:
        """
        Get student with all applications eagerly loaded.
        
        Args:
            student_id: Student profile UUID
            
        Returns:
            StudentProfile with applications or None
        """
        return self.db.query(StudentProfile).filter(
            StudentProfile.id == student_id
        ).options(
            joinedload(StudentProfile.applications)
        ).first()
    
    def search_by_name(
        self, 
        search_term: str, 
        skip: int = 0, 
        limit: int = 50
    ) -> List[StudentProfile]:
        """
        Search students by name (given or family).
        
        Args:
            search_term: Search string
            skip: Pagination offset
            limit: Max results
            
        Returns:
            List of matching students
        """
        search_pattern = f"%{search_term}%"
        return self.db.query(StudentProfile).filter(
            (StudentProfile.given_name.ilike(search_pattern)) |
            (StudentProfile.family_name.ilike(search_pattern))
        ).offset(skip).limit(limit).all()
    
    def get_by_nationality(
        self, 
        nationality: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[StudentProfile]:
        """
        Get students by nationality.
        
        Args:
            nationality: Nationality string
            skip: Pagination offset
            limit: Max results
            
        Returns:
            List of students
        """
        return self.db.query(StudentProfile).filter(
            StudentProfile.nationality == nationality
        ).offset(skip).limit(limit).all()
