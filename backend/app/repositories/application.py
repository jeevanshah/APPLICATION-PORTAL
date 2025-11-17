"""
Application repository.
Handles application CRUD and workflow operations.
"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_

from app.models import Application, ApplicationStage, UserRole
from app.repositories.base import BaseRepository


class ApplicationRepository(BaseRepository[Application]):
    """Repository for application operations."""
    
    def __init__(self, db: Session):
        super().__init__(Application, db)
    
    def get_with_relations(self, application_id: UUID) -> Optional[Application]:
        """
        Get application with all related entities loaded.
        
        Args:
            application_id: Application UUID
            
        Returns:
            Application with relations or None
        """
        return self.db.query(Application).filter(
            Application.id == application_id
        ).options(
            joinedload(Application.student),
            joinedload(Application.agent),
            joinedload(Application.course),
            joinedload(Application.assigned_staff),
            joinedload(Application.documents),
            joinedload(Application.schooling_history),
            joinedload(Application.qualification_history),
            joinedload(Application.employment_history)
        ).first()
    
    def get_by_student(
        self, 
        student_id: UUID, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Application]:
        """
        Get all applications for a student.
        
        Args:
            student_id: Student profile UUID
            skip: Pagination offset
            limit: Max results
            
        Returns:
            List of applications
        """
        return self.db.query(Application).filter(
            Application.student_profile_id == student_id
        ).options(
            joinedload(Application.course),
            joinedload(Application.agent)
        ).order_by(
            Application.created_at.desc()
        ).offset(skip).limit(limit).all()
    
    def get_by_agent(
        self, 
        agent_id: UUID, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Application]:
        """
        Get all applications created by an agent.
        
        Args:
            agent_id: Agent profile UUID
            skip: Pagination offset
            limit: Max results
            
        Returns:
            List of applications
        """
        return self.db.query(Application).filter(
            Application.agent_profile_id == agent_id
        ).options(
            joinedload(Application.student),
            joinedload(Application.course)
        ).order_by(
            Application.created_at.desc()
        ).offset(skip).limit(limit).all()
    
    def get_by_staff(
        self, 
        staff_id: UUID, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Application]:
        """
        Get all applications assigned to a staff member.
        
        Args:
            staff_id: Staff profile UUID
            skip: Pagination offset
            limit: Max results
            
        Returns:
            List of applications
        """
        return self.db.query(Application).filter(
            Application.assigned_staff_id == staff_id
        ).options(
            joinedload(Application.student),
            joinedload(Application.course),
            joinedload(Application.agent)
        ).order_by(
            Application.created_at.desc()
        ).offset(skip).limit(limit).all()
    
    def get_by_stage(
        self, 
        stage: ApplicationStage, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Application]:
        """
        Get all applications in a specific stage.
        
        Args:
            stage: Application stage enum
            skip: Pagination offset
            limit: Max results
            
        Returns:
            List of applications
        """
        return self.db.query(Application).filter(
            Application.current_stage == stage
        ).options(
            joinedload(Application.student),
            joinedload(Application.course)
        ).order_by(
            Application.submitted_at.desc()
        ).offset(skip).limit(limit).all()
    
    def get_submitted_applications(
        self, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Application]:
        """
        Get all submitted applications (not draft).
        
        Args:
            skip: Pagination offset
            limit: Max results
            
        Returns:
            List of submitted applications
        """
        return self.db.query(Application).filter(
            Application.current_stage != ApplicationStage.DRAFT,
            Application.submitted_at.isnot(None)
        ).options(
            joinedload(Application.student),
            joinedload(Application.course),
            joinedload(Application.agent)
        ).order_by(
            Application.submitted_at.desc()
        ).offset(skip).limit(limit).all()
    
    def get_draft_applications(
        self, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Application]:
        """
        Get all draft applications.
        
        Args:
            skip: Pagination offset
            limit: Max results
            
        Returns:
            List of draft applications
        """
        return self.db.query(Application).filter(
            Application.current_stage == ApplicationStage.DRAFT
        ).options(
            joinedload(Application.student),
            joinedload(Application.course)
        ).order_by(
            Application.updated_at.desc()
        ).offset(skip).limit(limit).all()
    
    def count_by_student(self, student_id: UUID) -> int:
        """
        Count applications for a student.
        
        Args:
            student_id: Student profile UUID
            
        Returns:
            Count of applications
        """
        return self.db.query(Application).filter(
            Application.student_profile_id == student_id
        ).count()
    
    def count_by_agent(self, agent_id: UUID) -> int:
        """
        Count applications created by an agent.
        
        Args:
            agent_id: Agent profile UUID
            
        Returns:
            Count of applications
        """
        return self.db.query(Application).filter(
            Application.agent_profile_id == agent_id
        ).count()
    
    def count_by_stage(self, stage: ApplicationStage) -> int:
        """
        Count applications in a specific stage.
        
        Args:
            stage: Application stage enum
            
        Returns:
            Count of applications
        """
        return self.db.query(Application).filter(
            Application.current_stage == stage
        ).count()
    
    def update_stage(
        self, 
        application_id: UUID, 
        new_stage: ApplicationStage,
        notes: Optional[str] = None
    ) -> Optional[Application]:
        """
        Update application stage and create history entry.
        
        Args:
            application_id: Application UUID
            new_stage: New stage enum
            notes: Optional transition notes
            
        Returns:
            Updated application or None if not found
        """
        from app.models import ApplicationStageHistory
        
        app = self.get_by_id(application_id)
        if not app:
            return None
        
        old_stage = app.current_stage
        app.current_stage = new_stage
        
        # Create stage history entry
        history = ApplicationStageHistory(
            application_id=application_id,
            from_stage=old_stage,
            to_stage=new_stage,
            changed_at=datetime.utcnow(),
            notes=notes
        )
        self.db.add(history)
        
        # Update submission timestamp if transitioning from DRAFT
        if old_stage == ApplicationStage.DRAFT and new_stage == ApplicationStage.SUBMITTED:
            app.submitted_at = datetime.utcnow()
        
        self.db.flush()
        self.db.refresh(app)
        return app
    
    def assign_to_staff(
        self, 
        application_id: UUID, 
        staff_id: UUID
    ) -> Optional[Application]:
        """
        Assign application to staff member.
        
        Args:
            application_id: Application UUID
            staff_id: Staff profile UUID
            
        Returns:
            Updated application or None if not found
        """
        app = self.get_by_id(application_id)
        if not app:
            return None
        
        app.assigned_staff_id = staff_id
        self.db.flush()
        self.db.refresh(app)
        return app
    
    def can_user_edit(
        self, 
        application_id: UUID, 
        user_id: UUID, 
        user_role: UserRole
    ) -> bool:
        """
        Check if user can edit this application.
        
        Args:
            application_id: Application UUID
            user_id: User account UUID
            user_role: User role enum
            
        Returns:
            True if user can edit, False otherwise
        """
        app = self.get_by_id(application_id)
        if not app:
            return False
        
        # Students cannot edit applications
        if user_role == UserRole.STUDENT:
            return False
        
        # Staff and admin can edit any application
        if user_role in [UserRole.STAFF, UserRole.ADMIN]:
            return True
        
        # Agents can only edit applications they created
        if user_role == UserRole.AGENT:
            # Get agent profile for this user
            from app.repositories.agent import AgentRepository
            agent_repo = AgentRepository(self.db)
            agent = agent_repo.get_by_user_id(user_id)
            
            if agent and app.agent_profile_id == agent.id:
                # Cannot edit submitted applications
                return app.current_stage == ApplicationStage.DRAFT
        
        return False
    
    def search_applications(
        self,
        search_term: Optional[str] = None,
        stage: Optional[ApplicationStage] = None,
        agent_id: Optional[UUID] = None,
        staff_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Application]:
        """
        Search applications with multiple filters.
        
        Args:
            search_term: Search in student name, course name
            stage: Filter by stage
            agent_id: Filter by agent
            staff_id: Filter by assigned staff
            skip: Pagination offset
            limit: Max results
            
        Returns:
            List of matching applications
        """
        from app.models import StudentProfile, CourseOffering
        
        query = self.db.query(Application)
        
        # Join for search
        if search_term:
            query = query.join(Application.student).join(Application.course)
            search_pattern = f"%{search_term}%"
            query = query.filter(
                or_(
                    StudentProfile.given_name.ilike(search_pattern),
                    StudentProfile.family_name.ilike(search_pattern),
                    CourseOffering.course_name.ilike(search_pattern),
                    CourseOffering.course_code.ilike(search_pattern)
                )
            )
        
        # Filter by stage
        if stage:
            query = query.filter(Application.current_stage == stage)
        
        # Filter by agent
        if agent_id:
            query = query.filter(Application.agent_profile_id == agent_id)
        
        # Filter by staff
        if staff_id:
            query = query.filter(Application.assigned_staff_id == staff_id)
        
        # Load relations
        query = query.options(
            joinedload(Application.student),
            joinedload(Application.course),
            joinedload(Application.agent)
        )
        
        return query.order_by(
            Application.created_at.desc()
        ).offset(skip).limit(limit).all()
