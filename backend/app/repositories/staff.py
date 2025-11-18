"""
Staff repository for querying and managing staff-related operations.
Handles pending applications, document verification, and application reviews.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    Application, ApplicationStage, ApplicationStageHistory,
    Document, DocumentStatus, DocumentType, OCRStatus,
    StudentProfile, CourseOffering, AgentProfile, StaffProfile,
    TimelineEntry, TimelineEntryType, UserRole, UserAccount
)
from app.repositories.base import BaseRepository


class StaffRepository(BaseRepository[StaffProfile]):
    """Repository for staff-specific operations."""
    
    def __init__(self, db: Session):
        super().__init__(StaffProfile, db)
    
    def get_by_user_id(self, user_id: UUID) -> Optional[StaffProfile]:
        """Get staff profile by user account ID."""
        return self.db.query(StaffProfile).filter(
            StaffProfile.user_account_id == user_id
        ).first()
    
    # ========================================================================
    # PENDING APPLICATIONS QUEUE
    # ========================================================================
    
    def get_pending_applications(
        self,
        staff_id: Optional[UUID] = None,
        stage: Optional[ApplicationStage] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Application]:
        """
        Get applications pending staff review.
        
        Args:
            staff_id: Filter by assigned staff (None = all unassigned or assigned to any staff)
            stage: Filter by specific stage (None = all review stages)
            skip: Pagination offset
            limit: Max results
        
        Returns:
            List of applications with eager-loaded relationships
        """
        query = self.db.query(Application)
        
        # Default to staff review stages if no stage specified
        if stage is None:
            review_stages = [
                ApplicationStage.SUBMITTED,
                ApplicationStage.STAFF_REVIEW,
                ApplicationStage.AWAITING_DOCUMENTS,
                ApplicationStage.GS_ASSESSMENT
            ]
            query = query.filter(Application.current_stage.in_(review_stages))
        else:
            query = query.filter(Application.current_stage == stage)
        
        # Filter by assigned staff
        if staff_id is not None:
            query = query.filter(Application.assigned_staff_id == staff_id)
        
        # Eager load relationships to avoid N+1 queries
        query = query.options(
            joinedload(Application.student).joinedload(StudentProfile.user_account),
            joinedload(Application.course),
            joinedload(Application.agent).joinedload(AgentProfile.user_account),
            joinedload(Application.assigned_staff).joinedload(StaffProfile.user_account),
            selectinload(Application.documents).joinedload(Document.document_type),
            selectinload(Application.documents).joinedload(Document.versions)
        )
        
        # Order by submission date (oldest first for SLA)
        query = query.order_by(Application.submitted_at.asc().nullsfirst())
        
        return query.offset(skip).limit(limit).all()
    
    def get_pending_count(
        self,
        staff_id: Optional[UUID] = None,
        stage: Optional[ApplicationStage] = None
    ) -> int:
        """Get count of pending applications (for dashboard metrics)."""
        query = self.db.query(func.count(Application.id))
        
        if stage is None:
            review_stages = [
                ApplicationStage.SUBMITTED,
                ApplicationStage.STAFF_REVIEW,
                ApplicationStage.AWAITING_DOCUMENTS,
                ApplicationStage.GS_ASSESSMENT
            ]
            query = query.filter(Application.current_stage.in_(review_stages))
        else:
            query = query.filter(Application.current_stage == stage)
        
        if staff_id is not None:
            query = query.filter(Application.assigned_staff_id == staff_id)
        
        return query.scalar() or 0
    
    def get_application_with_details(self, application_id: UUID) -> Optional[Application]:
        """Get single application with all relationships loaded."""
        return self.db.query(Application).options(
            joinedload(Application.student).joinedload(StudentProfile.user_account),
            joinedload(Application.course),
            joinedload(Application.agent).joinedload(AgentProfile.user_account),
            joinedload(Application.assigned_staff).joinedload(StaffProfile.user_account),
            selectinload(Application.documents).joinedload(Document.document_type),
            selectinload(Application.documents).joinedload(Document.versions),
            selectinload(Application.schooling_history),
            selectinload(Application.qualification_history),
            selectinload(Application.employment_history),
            selectinload(Application.stage_history),
            selectinload(Application.timeline_entries).joinedload(TimelineEntry.actor)
        ).filter(Application.id == application_id).first()
    
    # ========================================================================
    # DOCUMENT VERIFICATION
    # ========================================================================
    
    def get_documents_pending_verification(
        self,
        application_id: Optional[UUID] = None,
        document_type_code: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Document]:
        """
        Get documents awaiting staff verification.
        
        Args:
            application_id: Filter by specific application
            document_type_code: Filter by document type
            skip: Pagination offset
            limit: Max results
        """
        query = self.db.query(Document).filter(
            Document.status == DocumentStatus.PENDING
        )
        
        if application_id is not None:
            query = query.filter(Document.application_id == application_id)
        
        if document_type_code is not None:
            query = query.join(DocumentType).filter(
                DocumentType.code == document_type_code
            )
        
        query = query.options(
            joinedload(Document.document_type),
            joinedload(Document.application),
            selectinload(Document.versions)
        )
        
        # Order by upload date (oldest first)
        query = query.order_by(Document.uploaded_at.asc())
        
        return query.offset(skip).limit(limit).all()
    
    def verify_document(
        self,
        document_id: UUID,
        staff_id: UUID,
        status: DocumentStatus,
        notes: Optional[str] = None
    ) -> Document:
        """
        Verify or reject a document.
        
        Args:
            document_id: Document to verify
            staff_id: Staff performing verification
            status: VERIFIED or REJECTED
            notes: Optional verification notes
        
        Returns:
            Updated document
        """
        document = self.db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Update document status
        document.status = status
        
        # Create timeline entry
        staff_profile = self.db.query(StaffProfile).filter(StaffProfile.id == staff_id).first()
        user_id = staff_profile.user_account_id if staff_profile else None
        
        action_verb = "verified" if status == DocumentStatus.VERIFIED else "rejected"
        message = f"Document {document.document_type.name} {action_verb}"
        if notes:
            message += f": {notes}"
        
        timeline = TimelineEntry(
            application_id=document.application_id,
            entry_type=TimelineEntryType.DOCUMENT_VERIFIED,
            actor_id=user_id,
            actor_role=UserRole.STAFF,
            message=message,
            linked_document_id=document_id,
            event_payload={
                "document_id": str(document_id),
                "document_type": document.document_type.code,
                "status": status.value,
                "notes": notes,
                "verified_by": str(staff_id)
            }
        )
        self.db.add(timeline)
        
        self.db.commit()
        self.db.refresh(document)
        return document
    
    # ========================================================================
    # APPLICATION REVIEW & STAGE TRANSITIONS
    # ========================================================================
    
    def assign_application(
        self,
        application_id: UUID,
        staff_id: UUID,
        assigned_by: UUID
    ) -> Application:
        """Assign application to a staff member."""
        application = self.db.query(Application).filter(
            Application.id == application_id
        ).first()
        if not application:
            raise ValueError(f"Application {application_id} not found")
        
        application.assigned_staff_id = staff_id
        
        # Create timeline entry
        staff_profile = self.db.query(StaffProfile).filter(StaffProfile.id == staff_id).first()
        staff_user = self.db.query(UserAccount).filter(
            UserAccount.id == staff_profile.user_account_id
        ).first() if staff_profile else None
        
        timeline = TimelineEntry(
            application_id=application_id,
            entry_type=TimelineEntryType.ASSIGNED,
            actor_id=assigned_by,
            actor_role=UserRole.STAFF,
            message=f"Application assigned to {staff_user.email if staff_user else 'staff'}",
            event_payload={
                "assigned_to_staff_id": str(staff_id),
                "assigned_by": str(assigned_by)
            }
        )
        self.db.add(timeline)
        
        self.db.commit()
        self.db.refresh(application)
        return application
    
    def transition_application_stage(
        self,
        application_id: UUID,
        to_stage: ApplicationStage,
        staff_id: UUID,
        notes: Optional[str] = None
    ) -> Application:
        """
        Transition application to a new stage with audit trail.
        
        Args:
            application_id: Application to transition
            to_stage: Target stage
            staff_id: Staff performing transition
            notes: Optional transition notes
        """
        application = self.db.query(Application).filter(
            Application.id == application_id
        ).first()
        if not application:
            raise ValueError(f"Application {application_id} not found")
        
        from_stage = application.current_stage
        
        # Update application stage
        application.current_stage = to_stage
        
        # Special handling for terminal stages
        if to_stage in [ApplicationStage.OFFER_GENERATED, ApplicationStage.ENROLLED, 
                        ApplicationStage.REJECTED, ApplicationStage.WITHDRAWN]:
            application.decision_at = datetime.utcnow()
        
        # Create stage history record
        stage_history = ApplicationStageHistory(
            application_id=application_id,
            from_stage=from_stage,
            to_stage=to_stage,
            changed_by=staff_id,
            notes=notes
        )
        self.db.add(stage_history)
        
        # Create timeline entry
        staff_profile = self.db.query(StaffProfile).filter(StaffProfile.id == staff_id).first()
        user_id = staff_profile.user_account_id if staff_profile else None
        
        message = f"Application moved to {to_stage.value.replace('_', ' ').title()}"
        if notes:
            message += f": {notes}"
        
        timeline = TimelineEntry(
            application_id=application_id,
            entry_type=TimelineEntryType.STAGE_CHANGED,
            actor_id=user_id,
            actor_role=UserRole.STAFF,
            message=message,
            stage=to_stage,
            event_payload={
                "from_stage": from_stage.value if from_stage else None,
                "to_stage": to_stage.value,
                "notes": notes,
                "changed_by": str(staff_id)
            }
        )
        self.db.add(timeline)
        
        self.db.commit()
        self.db.refresh(application)
        return application
    
    def add_staff_comment(
        self,
        application_id: UUID,
        staff_id: UUID,
        comment: str,
        is_internal: bool = False
    ) -> TimelineEntry:
        """
        Add a staff comment to application timeline.
        
        Args:
            application_id: Application to comment on
            staff_id: Staff adding comment
            comment: Comment text
            is_internal: If True, only visible to staff
        """
        staff_profile = self.db.query(StaffProfile).filter(StaffProfile.id == staff_id).first()
        if not staff_profile:
            raise ValueError(f"Staff {staff_id} not found")
        
        timeline = TimelineEntry(
            application_id=application_id,
            entry_type=TimelineEntryType.COMMENT_ADDED,
            actor_id=staff_profile.user_account_id,
            actor_role=UserRole.STAFF,
            message=comment,
            event_payload={
                "is_internal": is_internal,
                "staff_id": str(staff_id)
            }
        )
        self.db.add(timeline)
        self.db.commit()
        self.db.refresh(timeline)
        return timeline
    
    # ========================================================================
    # DASHBOARD METRICS
    # ========================================================================
    
    def get_staff_metrics(self, staff_id: Optional[UUID] = None) -> Dict[str, Any]:
        """
        Get dashboard metrics for staff.
        
        Args:
            staff_id: If provided, get metrics for specific staff member
        
        Returns:
            Dictionary with counts and metrics
        """
        base_query = self.db.query(Application)
        if staff_id:
            base_query = base_query.filter(Application.assigned_staff_id == staff_id)
        
        return {
            "total_applications": base_query.count(),
            "submitted_pending_review": base_query.filter(
                Application.current_stage == ApplicationStage.SUBMITTED
            ).count(),
            "in_staff_review": base_query.filter(
                Application.current_stage == ApplicationStage.STAFF_REVIEW
            ).count(),
            "awaiting_documents": base_query.filter(
                Application.current_stage == ApplicationStage.AWAITING_DOCUMENTS
            ).count(),
            "in_gs_assessment": base_query.filter(
                Application.current_stage == ApplicationStage.GS_ASSESSMENT
            ).count(),
            "offers_generated": base_query.filter(
                Application.current_stage == ApplicationStage.OFFER_GENERATED
            ).count(),
            "enrolled": base_query.filter(
                Application.current_stage == ApplicationStage.ENROLLED
            ).count(),
            "rejected": base_query.filter(
                Application.current_stage == ApplicationStage.REJECTED
            ).count(),
            "documents_pending_verification": self.db.query(Document).join(Application).filter(
                Document.status == DocumentStatus.PENDING,
                Application.assigned_staff_id == staff_id if staff_id else True
            ).count()
        }
