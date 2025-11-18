"""
Staff service layer for business logic.
Orchestrates staff workflow operations including application review,
document verification, and offer generation.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import ApplicationStage, DocumentStatus
from app.repositories.application import ApplicationRepository
from app.repositories.document import DocumentRepository
from app.repositories.staff import StaffRepository
from app.schemas.staff import (
    AgentSummary,
    ApplicationActionResponse,
    ApplicationDetailForReview,
    ApplicationListItem,
    CourseSummary,
    DocumentSummaryForStaff,
    DocumentVerificationResponse,
    EmploymentHistoryDetail,
    PendingApplicationsResponse,
    QualificationHistoryDetail,
    SchoolingHistoryDetail,
    StaffCommentResponse,
    StaffMetrics,
    StudentSummary,
    TimelineEntryDetail,
)


class StaffService:
    """Service for staff workflow operations."""

    def __init__(self, db: Session):
        self.db = db
        self.staff_repo = StaffRepository(db)
        self.application_repo = ApplicationRepository(db)
        self.document_repo = DocumentRepository(db)

    # ========================================================================
    # DASHBOARD & METRICS
    # ========================================================================

    def get_dashboard_metrics(
            self,
            staff_id: Optional[UUID] = None) -> StaffMetrics:
        """
        Get dashboard metrics for staff.

        Args:
            staff_id: If provided, filter metrics to specific staff member

        Returns:
            StaffMetrics with counts
        """
        metrics_data = self.staff_repo.get_staff_metrics(staff_id)
        return StaffMetrics(**metrics_data)

    def get_pending_applications(
        self,
        staff_id: Optional[UUID] = None,
        stage: Optional[ApplicationStage] = None,
        skip: int = 0,
        limit: int = 50
    ) -> PendingApplicationsResponse:
        """
        Get applications pending staff review.

        Returns:
            PendingApplicationsResponse with list of applications
        """
        applications = self.staff_repo.get_pending_applications(
            staff_id=staff_id,
            stage=stage,
            skip=skip,
            limit=limit
        )
        total = self.staff_repo.get_pending_count(
            staff_id=staff_id, stage=stage)

        # Map to response DTOs
        items = []
        for app in applications:
            # Calculate days pending
            days_pending = None
            if app.submitted_at:
                days_pending = (datetime.utcnow() - app.submitted_at).days

            # Count document statuses
            total_docs = len(app.documents)
            docs_verified = sum(
                1 for d in app.documents if d.status == DocumentStatus.VERIFIED)
            docs_pending = sum(
                1 for d in app.documents if d.status == DocumentStatus.PENDING)

            # Build student summary
            student = StudentSummary(
                id=app.student.id,
                given_name=app.student.given_name,
                family_name=app.student.family_name,
                email=app.student.user_account.email,
                nationality=app.student.nationality
            )

            # Build course summary
            course = CourseSummary(
                id=app.course.id,
                course_code=app.course.course_code,
                course_name=app.course.course_name,
                intake=app.course.intake,
                campus=app.course.campus
            )

            # Build agent summary
            agent = None
            if app.agent:
                agent = AgentSummary(
                    id=app.agent.id,
                    agency_name=app.agent.agency_name,
                    email=app.agent.user_account.email
                )

            # Get assigned staff email
            assigned_staff_email = None
            if app.assigned_staff:
                assigned_staff_email = app.assigned_staff.user_account.email

            item = ApplicationListItem(
                id=app.id,
                student=student,
                course=course,
                agent=agent,
                current_stage=app.current_stage,
                submitted_at=app.submitted_at,
                days_pending=days_pending,
                document_count=total_docs,
                documents_verified=docs_verified,
                documents_pending=docs_pending,
                assigned_staff_email=assigned_staff_email
            )
            items.append(item)

        return PendingApplicationsResponse(
            total=total,
            applications=items,
            skip=skip,
            limit=limit
        )

    def get_application_detail(
            self,
            application_id: UUID) -> ApplicationDetailForReview:
        """
        Get complete application details for staff review.

        Args:
            application_id: Application to retrieve

        Returns:
            ApplicationDetailForReview with all data
        """
        app = self.staff_repo.get_application_with_details(application_id)
        if not app:
            raise ValueError(f"Application {application_id} not found")

        # Build student summary
        student = StudentSummary(
            id=app.student.id,
            given_name=app.student.given_name,
            family_name=app.student.family_name,
            email=app.student.user_account.email,
            nationality=app.student.nationality
        )

        # Build course summary
        course = CourseSummary(
            id=app.course.id,
            course_code=app.course.course_code,
            course_name=app.course.course_name,
            intake=app.course.intake,
            campus=app.course.campus
        )

        # Build agent summary
        agent = None
        if app.agent:
            agent = AgentSummary(
                id=app.agent.id,
                agency_name=app.agent.agency_name,
                email=app.agent.user_account.email
            )

        # Build document summaries
        documents = []
        for doc in app.documents:
            documents.append(DocumentSummaryForStaff(
                id=doc.id,
                document_type_code=doc.document_type.code,
                document_type_name=doc.document_type.name,
                status=doc.status,
                ocr_status=doc.ocr_status.value,
                uploaded_at=doc.uploaded_at,
                version_count=len(doc.versions)
            ))

        # Build timeline entries
        timeline = []
        for entry in app.timeline_entries:
            actor_email = entry.actor.email if entry.actor else None
            timeline.append(TimelineEntryDetail(
                id=entry.id,
                entry_type=entry.entry_type.value,
                message=entry.message,
                actor_email=actor_email,
                actor_role=entry.actor_role,
                created_at=entry.created_at,
                event_payload=entry.event_payload
            ))

        # Build history
        schooling = [SchoolingHistoryDetail.model_validate(
            s) for s in app.schooling_history]
        qualifications = [QualificationHistoryDetail.model_validate(
            q) for q in app.qualification_history]
        employment = [EmploymentHistoryDetail.model_validate(
            e) for e in app.employment_history]

        # Get assigned staff email
        assigned_staff_email = None
        if app.assigned_staff:
            assigned_staff_email = app.assigned_staff.user_account.email

        return ApplicationDetailForReview(
            id=app.id,
            student=student,
            course=course,
            agent=agent,
            current_stage=app.current_stage,
            submitted_at=app.submitted_at,
            decision_at=app.decision_at,
            usi=app.usi,
            usi_verified=app.usi_verified,
            enrollment_data=app.enrollment_data,
            emergency_contacts=app.emergency_contacts,
            health_cover_policy=app.health_cover_policy,
            disability_support=app.disability_support,
            language_cultural_data=app.language_cultural_data,
            survey_responses=app.survey_responses,
            additional_services=app.additional_services,
            gs_assessment=app.gs_assessment,
            form_metadata=app.form_metadata,
            schooling_history=schooling,
            qualification_history=qualifications,
            employment_history=employment,
            documents=documents,
            timeline=timeline,
            assigned_staff_email=assigned_staff_email
        )

    # ========================================================================
    # DOCUMENT VERIFICATION
    # ========================================================================

    def verify_document(
        self,
        document_id: UUID,
        staff_id: UUID,
        status: DocumentStatus,
        notes: Optional[str] = None
    ) -> DocumentVerificationResponse:
        """
        Verify or reject a document.

        Args:
            document_id: Document to verify
            staff_id: Staff performing verification
            status: VERIFIED or REJECTED
            notes: Optional verification notes

        Returns:
            DocumentVerificationResponse
        """
        if status not in [DocumentStatus.VERIFIED, DocumentStatus.REJECTED]:
            raise ValueError("Status must be VERIFIED or REJECTED")

        document = self.staff_repo.verify_document(
            document_id=document_id,
            staff_id=staff_id,
            status=status,
            notes=notes
        )

        action = "verified" if status == DocumentStatus.VERIFIED else "rejected"
        message = f"Document {
            document.document_type.name} successfully {action}"

        return DocumentVerificationResponse(
            document_id=document_id,
            status=status,
            verified_at=datetime.utcnow(),
            message=message
        )

    def get_documents_pending_verification(
        self,
        application_id: Optional[UUID] = None,
        document_type_code: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[DocumentSummaryForStaff]:
        """Get documents awaiting verification."""
        documents = self.staff_repo.get_documents_pending_verification(
            application_id=application_id,
            document_type_code=document_type_code,
            skip=skip,
            limit=limit
        )

        return [
            DocumentSummaryForStaff(
                id=doc.id,
                document_type_code=doc.document_type.code,
                document_type_name=doc.document_type.name,
                status=doc.status,
                ocr_status=doc.ocr_status.value,
                uploaded_at=doc.uploaded_at,
                version_count=len(doc.versions)
            )
            for doc in documents
        ]

    # ========================================================================
    # APPLICATION REVIEW & STAGE TRANSITIONS
    # ========================================================================

    def assign_application(
        self,
        application_id: UUID,
        staff_id: UUID,
        assigned_by: UUID
    ) -> ApplicationActionResponse:
        """Assign application to staff member."""
        application = self.staff_repo.assign_application(
            application_id=application_id,
            staff_id=staff_id,
            assigned_by=assigned_by
        )

        return ApplicationActionResponse(
            application_id=application_id,
            current_stage=application.current_stage,
            message="Application assigned to staff member",
            updated_at=application.updated_at
        )

    def transition_stage(
        self,
        application_id: UUID,
        to_stage: ApplicationStage,
        staff_id: UUID,
        notes: Optional[str] = None
    ) -> ApplicationActionResponse:
        """
        Transition application to new stage with validation.

        Args:
            application_id: Application to transition
            to_stage: Target stage
            staff_id: Staff performing transition
            notes: Optional transition notes

        Returns:
            ApplicationActionResponse
        """
        # Get current application
        app = self.staff_repo.get_application_with_details(application_id)
        if not app:
            raise ValueError(f"Application {application_id} not found")

        # Validate stage transition
        self._validate_stage_transition(app.current_stage, to_stage)

        # Perform transition
        application = self.staff_repo.transition_application_stage(
            application_id=application_id,
            to_stage=to_stage,
            staff_id=staff_id,
            notes=notes
        )

        return ApplicationActionResponse(
            application_id=application_id,
            current_stage=to_stage,
            message=f"Application moved to {
                to_stage.value.replace(
                    '_',
                    ' ').title()}",
            updated_at=application.updated_at)

    def add_comment(
        self,
        application_id: UUID,
        staff_id: UUID,
        comment: str,
        is_internal: bool = False
    ) -> StaffCommentResponse:
        """Add staff comment to application."""
        timeline_entry = self.staff_repo.add_staff_comment(
            application_id=application_id,
            staff_id=staff_id,
            comment=comment,
            is_internal=is_internal
        )

        return StaffCommentResponse(
            timeline_entry_id=timeline_entry.id,
            application_id=application_id,
            comment=comment,
            created_at=timeline_entry.created_at
        )

    def approve_application(
        self,
        application_id: UUID,
        staff_id: UUID,
        offer_details: Dict[str, Any],
        notes: Optional[str] = None
    ) -> ApplicationActionResponse:
        """
        Approve application and move to OFFER_GENERATED stage.

        Args:
            application_id: Application to approve
            staff_id: Staff approving
            offer_details: Offer letter details (fees, start date, conditions)
            notes: Optional approval notes

        Returns:
            ApplicationActionResponse
        """
        # Get application
        app = self.staff_repo.get_application_with_details(application_id)
        if not app:
            raise ValueError(f"Application {application_id} not found")

        # Verify all mandatory documents are verified
        pending_docs = [
            d for d in app.documents if d.status != DocumentStatus.VERIFIED]
        if pending_docs:
            pending_names = ", ".join(
                [d.document_type.name for d in pending_docs[:3]])
            raise ValueError(
                f"Cannot approve: {
                    len(pending_docs)} document(s) not verified ({pending_names})")

        # Update enrollment_data with offer details
        enrollment_data = app.enrollment_data or {}
        enrollment_data.update({
            "status": "offer_sent",
            "offer_generated_at": datetime.utcnow().isoformat(),
            "offer_details": offer_details
        })

        # Update application
        app.enrollment_data = enrollment_data
        self.db.commit()

        # Transition to OFFER_GENERATED stage
        return self.transition_stage(
            application_id=application_id,
            to_stage=ApplicationStage.OFFER_GENERATED,
            staff_id=staff_id,
            notes=notes or "Application approved. Offer letter generated."
        )

    def reject_application(
        self,
        application_id: UUID,
        staff_id: UUID,
        rejection_reason: str,
        is_appealable: bool = False
    ) -> ApplicationActionResponse:
        """
        Reject application.

        Args:
            application_id: Application to reject
            staff_id: Staff rejecting
            rejection_reason: Reason for rejection
            is_appealable: Whether student can appeal

        Returns:
            ApplicationActionResponse
        """
        # Get application
        app = self.staff_repo.get_application_with_details(application_id)
        if not app:
            raise ValueError(f"Application {application_id} not found")

        # Update enrollment_data with rejection details
        enrollment_data = app.enrollment_data or {}
        enrollment_data.update({
            "status": "rejected",
            "rejected_at": datetime.utcnow().isoformat(),
            "rejection_reason": rejection_reason,
            "is_appealable": is_appealable
        })

        # Update application
        app.enrollment_data = enrollment_data
        self.db.commit()

        # Transition to REJECTED stage
        return self.transition_stage(
            application_id=application_id,
            to_stage=ApplicationStage.REJECTED,
            staff_id=staff_id,
            notes=f"Application rejected: {rejection_reason}"
        )

    def request_additional_documents(
        self,
        application_id: UUID,
        staff_id: UUID,
        document_type_codes: List[str],
        message: str,
        due_date: Optional[datetime] = None
    ) -> ApplicationActionResponse:
        """
        Request additional documents from student/agent.

        Args:
            application_id: Application requesting documents for
            staff_id: Staff making request
            document_type_codes: List of document type codes to request
            message: Message to student/agent
            due_date: Optional due date

        Returns:
            ApplicationActionResponse
        """
        # Get application
        app = self.staff_repo.get_application_with_details(application_id)
        if not app:
            raise ValueError(f"Application {application_id} not found")

        # Create document request records
        for doc in app.documents:
            if doc.document_type.code in document_type_codes:
                gs_requests = doc.gs_document_requests or []
                gs_requests.append({
                    "requested_by": str(staff_id),
                    "requested_at": datetime.utcnow().isoformat(),
                    "message": message,
                    "due_at": due_date.isoformat() if due_date else None,
                    "status": "pending"
                })
                doc.gs_document_requests = gs_requests

        self.db.commit()

        # Transition to AWAITING_DOCUMENTS stage
        return self.transition_stage(
            application_id=application_id,
            to_stage=ApplicationStage.AWAITING_DOCUMENTS,
            staff_id=staff_id,
            notes=f"Additional documents requested: {message}"
        )

    def record_gs_assessment(
        self,
        application_id: UUID,
        staff_id: UUID,
        interview_date: datetime,
        decision: str,
        scorecard: Dict[str, Any],
        notes: Optional[str] = None
    ) -> ApplicationActionResponse:
        """
        Record Genuine Student (GS) assessment.

        Args:
            application_id: Application being assessed
            staff_id: Staff conducting assessment
            interview_date: Interview date
            decision: "pass", "fail", or "pending"
            scorecard: Assessment scorecard
            notes: Optional assessment notes

        Returns:
            ApplicationActionResponse
        """
        # Get application
        app = self.staff_repo.get_application_with_details(application_id)
        if not app:
            raise ValueError(f"Application {application_id} not found")

        # Update GS assessment data
        gs_assessment = {
            "interview_date": interview_date.isoformat(),
            "staff_id": str(staff_id),
            "scorecard": scorecard,
            "decision": decision,
            "notes": notes,
            "assessed_at": datetime.utcnow().isoformat()
        }
        app.gs_assessment = gs_assessment
        self.db.commit()

        # Determine next stage based on decision
        if decision == "pass":
            # Move back to staff review for final approval
            next_stage = ApplicationStage.STAFF_REVIEW
            message = "GS Assessment passed. Ready for final review."
        elif decision == "fail":
            next_stage = ApplicationStage.REJECTED
            message = f"GS Assessment failed: {notes or 'Did not meet GS criteria'}"
        else:
            # Keep in GS_ASSESSMENT stage
            return ApplicationActionResponse(
                application_id=application_id,
                current_stage=app.current_stage,
                message="GS Assessment recorded (pending decision)",
                updated_at=app.updated_at
            )

        return self.transition_stage(
            application_id=application_id,
            to_stage=next_stage,
            staff_id=staff_id,
            notes=message
        )

    # ========================================================================
    # VALIDATION HELPERS
    # ========================================================================

    def _validate_stage_transition(
        self,
        from_stage: ApplicationStage,
        to_stage: ApplicationStage
    ) -> None:
        """
        Validate that stage transition is allowed.

        Raises:
            ValueError if transition is invalid
        """
        # Define allowed transitions
        allowed_transitions = {
            ApplicationStage.DRAFT: [ApplicationStage.SUBMITTED],
            ApplicationStage.SUBMITTED: [
                ApplicationStage.STAFF_REVIEW,
                ApplicationStage.AWAITING_DOCUMENTS,
                ApplicationStage.REJECTED
            ],
            ApplicationStage.STAFF_REVIEW: [
                ApplicationStage.AWAITING_DOCUMENTS,
                ApplicationStage.GS_ASSESSMENT,
                ApplicationStage.OFFER_GENERATED,
                ApplicationStage.REJECTED
            ],
            ApplicationStage.AWAITING_DOCUMENTS: [
                ApplicationStage.STAFF_REVIEW,
                ApplicationStage.REJECTED
            ],
            ApplicationStage.GS_ASSESSMENT: [
                ApplicationStage.STAFF_REVIEW,
                ApplicationStage.REJECTED
            ],
            ApplicationStage.OFFER_GENERATED: [
                ApplicationStage.OFFER_ACCEPTED,
                ApplicationStage.WITHDRAWN
            ],
            ApplicationStage.OFFER_ACCEPTED: [
                ApplicationStage.ENROLLED
            ],
            # Terminal stages - no transitions allowed
            ApplicationStage.ENROLLED: [],
            ApplicationStage.REJECTED: [],
            ApplicationStage.WITHDRAWN: []
        }

        valid_next_stages = allowed_transitions.get(from_stage, [])

        if to_stage not in valid_next_stages:
            raise ValueError(
                f"Invalid transition from {from_stage.value} to {to_stage.value}. "
                f"Allowed: {[s.value for s in valid_next_stages]}"
            )
