"""
Staff workflow endpoints for application review and document verification.
Requires STAFF or ADMIN role.
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.database import get_db
from app.models import UserAccount, UserRole, ApplicationStage, DocumentStatus, StaffProfile, RtoProfile
from app.api.dependencies import get_current_user
from app.services.staff import StaffService
from app.services.offer_letter import OfferLetterService
from app.repositories.staff import StaffRepository
from app.schemas.staff import (
    StaffMetrics, PendingApplicationsResponse, ApplicationDetailForReview,
    DocumentSummaryForStaff, AssignApplicationRequest, TransitionStageRequest,
    VerifyDocumentRequest, AddStaffCommentRequest, RequestAdditionalDocumentsRequest,
    ApproveApplicationRequest, RejectApplicationRequest, GSAssessmentRequest,
    DocumentVerificationResponse, ApplicationActionResponse, StaffCommentResponse,
    OfferLetterRequest, OfferLetterResponse
)

router = APIRouter()


# ============================================================================
# DEPENDENCY: Require Staff Role
# ============================================================================

def require_staff_role(current_user: UserAccount = Depends(get_current_user)) -> UserAccount:
    """Verify current user is STAFF or ADMIN."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff or Admin role required"
        )
    return current_user


def get_staff_profile(
    current_user: UserAccount = Depends(require_staff_role),
    db: Session = Depends(get_db)
) -> StaffProfile:
    """Get StaffProfile for current user."""
    staff_repo = StaffRepository(db)
    staff_profile = staff_repo.get_by_user_id(current_user.id)
    if not staff_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff profile not found for current user"
        )
    return staff_profile


# ============================================================================
# DASHBOARD & METRICS
# ============================================================================

@router.get("/metrics", response_model=StaffMetrics, summary="Get staff dashboard metrics")
def get_staff_metrics(
    staff_profile: StaffProfile = Depends(get_staff_profile),
    db: Session = Depends(get_db)
):
    """
    Get dashboard metrics for staff workload.
    
    Returns counts of applications in various stages and documents pending verification.
    """
    service = StaffService(db)
    return service.get_dashboard_metrics(staff_id=staff_profile.id)


@router.get("/metrics/all", response_model=StaffMetrics, summary="Get organization-wide metrics")
def get_all_staff_metrics(
    current_user: UserAccount = Depends(require_staff_role),
    db: Session = Depends(get_db)
):
    """
    Get dashboard metrics for entire organization (all staff).
    
    Only accessible to STAFF and ADMIN roles.
    """
    service = StaffService(db)
    return service.get_dashboard_metrics(staff_id=None)


# ============================================================================
# PENDING APPLICATIONS QUEUE
# ============================================================================

@router.get("/applications/pending", response_model=PendingApplicationsResponse, 
            summary="Get applications pending staff review")
def get_pending_applications(
    stage: Optional[ApplicationStage] = Query(None, description="Filter by specific stage"),
    assigned_to_me: bool = Query(False, description="Show only applications assigned to me"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
    staff_profile: StaffProfile = Depends(get_staff_profile),
    db: Session = Depends(get_db)
):
    """
    Get applications pending staff review.
    
    **Default behavior**: Returns all applications in review stages (SUBMITTED, STAFF_REVIEW, 
    AWAITING_DOCUMENTS, GS_ASSESSMENT).
    
    **Query parameters**:
    - `stage`: Filter to specific stage only
    - `assigned_to_me`: If true, show only applications assigned to current staff member
    - `skip`, `limit`: Pagination
    
    **Returns**:
    - List of applications with student, course, agent info
    - Document verification status
    - Days pending (for SLA tracking)
    """
    service = StaffService(db)
    staff_id = staff_profile.id if assigned_to_me else None
    return service.get_pending_applications(
        staff_id=staff_id,
        stage=stage,
        skip=skip,
        limit=limit
    )


@router.get("/applications/{application_id}", response_model=ApplicationDetailForReview,
            summary="Get complete application details for review")
def get_application_detail(
    application_id: UUID,
    current_user: UserAccount = Depends(require_staff_role),
    db: Session = Depends(get_db)
):
    """
    Get complete application details for staff review.
    
    **Returns**:
    - Student profile and contact info
    - Course details
    - All 12 form steps (JSONB data)
    - Schooling, qualification, employment history
    - Documents with OCR status
    - Full timeline with comments
    - Assigned staff member
    """
    service = StaffService(db)
    try:
        return service.get_application_detail(application_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============================================================================
# DOCUMENT VERIFICATION
# ============================================================================

@router.get("/documents/pending", response_model=List[DocumentSummaryForStaff],
            summary="Get documents pending verification")
def get_pending_documents(
    application_id: Optional[UUID] = Query(None, description="Filter by application"),
    document_type_code: Optional[str] = Query(None, description="Filter by document type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: UserAccount = Depends(require_staff_role),
    db: Session = Depends(get_db)
):
    """
    Get documents awaiting staff verification.
    
    **Query parameters**:
    - `application_id`: Filter to specific application
    - `document_type_code`: Filter to specific document type (e.g., "PASSPORT")
    
    **Returns**: List of documents with OCR status and version count
    """
    service = StaffService(db)
    return service.get_documents_pending_verification(
        application_id=application_id,
        document_type_code=document_type_code,
        skip=skip,
        limit=limit
    )


@router.patch("/documents/{document_id}/verify", response_model=DocumentVerificationResponse,
              summary="Verify or reject a document")
def verify_document(
    document_id: UUID,
    request: VerifyDocumentRequest,
    staff_profile: StaffProfile = Depends(get_staff_profile),
    db: Session = Depends(get_db)
):
    """
    Verify or reject a document.
    
    **Request body**:
    - `status`: VERIFIED or REJECTED
    - `notes`: Optional verification notes (required if rejecting)
    
    **Actions**:
    - Updates document status
    - Creates timeline entry
    - Notifies student/agent (future: email notification)
    """
    service = StaffService(db)
    try:
        return service.verify_document(
            document_id=document_id,
            staff_id=staff_profile.id,
            status=request.status,
            notes=request.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============================================================================
# APPLICATION ASSIGNMENT
# ============================================================================

@router.patch("/applications/{application_id}/assign", response_model=ApplicationActionResponse,
              summary="Assign application to staff member")
def assign_application(
    application_id: UUID,
    request: AssignApplicationRequest,
    staff_profile: StaffProfile = Depends(get_staff_profile),
    current_user: UserAccount = Depends(require_staff_role),
    db: Session = Depends(get_db)
):
    """
    Assign application to a staff member for review.
    
    **Request body**:
    - `staff_id`: UUID of staff member to assign to
    
    **Actions**:
    - Updates `assigned_staff_id` on application
    - Creates timeline entry for audit trail
    """
    service = StaffService(db)
    try:
        return service.assign_application(
            application_id=application_id,
            staff_id=request.staff_id,
            assigned_by=current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============================================================================
# STAGE TRANSITIONS
# ============================================================================

@router.patch("/applications/{application_id}/transition", response_model=ApplicationActionResponse,
              summary="Transition application to new stage")
def transition_application_stage(
    application_id: UUID,
    request: TransitionStageRequest,
    staff_profile: StaffProfile = Depends(get_staff_profile),
    db: Session = Depends(get_db)
):
    """
    Transition application to a new workflow stage.
    
    **Request body**:
    - `to_stage`: Target ApplicationStage
    - `notes`: Optional transition notes
    
    **Validation**:
    - Ensures transition is valid according to workflow rules
    - Example: STAFF_REVIEW → OFFER_GENERATED (approve)
    - Example: STAFF_REVIEW → REJECTED (reject)
    
    **Actions**:
    - Updates `current_stage`
    - Creates `ApplicationStageHistory` record
    - Creates timeline entry
    """
    service = StaffService(db)
    try:
        return service.transition_stage(
            application_id=application_id,
            to_stage=request.to_stage,
            staff_id=staff_profile.id,
            notes=request.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# COMMENTS
# ============================================================================

@router.post("/applications/{application_id}/comments", response_model=StaffCommentResponse,
             summary="Add staff comment to application")
def add_staff_comment(
    application_id: UUID,
    request: AddStaffCommentRequest,
    staff_profile: StaffProfile = Depends(get_staff_profile),
    db: Session = Depends(get_db)
):
    """
    Add a staff comment to application timeline.
    
    **Request body**:
    - `comment`: Comment text (1-2000 characters)
    - `is_internal`: If true, only visible to staff (not student/agent)
    
    **Actions**:
    - Creates `TimelineEntry` with COMMENT_ADDED type
    - Visible in application timeline
    """
    service = StaffService(db)
    try:
        return service.add_comment(
            application_id=application_id,
            staff_id=staff_profile.id,
            comment=request.comment,
            is_internal=request.is_internal
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============================================================================
# REQUEST ADDITIONAL DOCUMENTS
# ============================================================================

@router.post("/applications/{application_id}/request-documents", 
             response_model=ApplicationActionResponse,
             summary="Request additional documents from student/agent")
def request_additional_documents(
    application_id: UUID,
    request: RequestAdditionalDocumentsRequest,
    staff_profile: StaffProfile = Depends(get_staff_profile),
    db: Session = Depends(get_db)
):
    """
    Request additional or updated documents from student/agent.
    
    **Request body**:
    - `document_type_codes`: List of document type codes to request
    - `message`: Message explaining what's needed
    - `due_date`: Optional deadline
    
    **Actions**:
    - Adds request to `document.gs_document_requests` JSONB field
    - Transitions application to AWAITING_DOCUMENTS stage
    - Creates timeline entry
    - Sends notification to student/agent (future)
    """
    service = StaffService(db)
    try:
        return service.request_additional_documents(
            application_id=application_id,
            staff_id=staff_profile.id,
            document_type_codes=request.document_type_codes,
            message=request.message,
            due_date=request.due_date
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============================================================================
# APPROVE APPLICATION
# ============================================================================

@router.post("/applications/{application_id}/approve", response_model=ApplicationActionResponse,
             summary="Approve application and generate offer")
def approve_application(
    application_id: UUID,
    request: ApproveApplicationRequest,
    staff_profile: StaffProfile = Depends(get_staff_profile),
    db: Session = Depends(get_db)
):
    """
    Approve application and generate offer letter.
    
    **Request body**:
    - `offer_details`: Offer letter details (course_start_date, fees, conditions, etc.)
    - `notes`: Optional approval notes
    
    **Validation**:
    - All mandatory documents must be VERIFIED
    
    **Actions**:
    - Updates `enrollment_data` with offer details
    - Transitions to OFFER_GENERATED stage
    - Sets `decision_at` timestamp
    - Creates timeline entry
    - Triggers offer letter generation (future: PDF)
    """
    service = StaffService(db)
    try:
        return service.approve_application(
            application_id=application_id,
            staff_id=staff_profile.id,
            offer_details=request.offer_details,
            notes=request.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# REJECT APPLICATION
# ============================================================================

@router.post("/applications/{application_id}/reject", response_model=ApplicationActionResponse,
             summary="Reject application")
def reject_application(
    application_id: UUID,
    request: RejectApplicationRequest,
    staff_profile: StaffProfile = Depends(get_staff_profile),
    db: Session = Depends(get_db)
):
    """
    Reject application with reason.
    
    **Request body**:
    - `rejection_reason`: Detailed reason for rejection (10-1000 characters)
    - `is_appealable`: Whether student can appeal decision
    
    **Actions**:
    - Updates `enrollment_data` with rejection details
    - Transitions to REJECTED stage
    - Sets `decision_at` timestamp
    - Creates timeline entry
    - Sends rejection notification (future)
    """
    service = StaffService(db)
    try:
        return service.reject_application(
            application_id=application_id,
            staff_id=staff_profile.id,
            rejection_reason=request.rejection_reason,
            is_appealable=request.is_appealable
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# GS ASSESSMENT
# ============================================================================

@router.post("/applications/{application_id}/gs-assessment", 
             response_model=ApplicationActionResponse,
             summary="Record Genuine Student assessment")
def record_gs_assessment(
    application_id: UUID,
    request: GSAssessmentRequest,
    staff_profile: StaffProfile = Depends(get_staff_profile),
    db: Session = Depends(get_db)
):
    """
    Record Genuine Student (GS) assessment for international student application.
    
    **Request body**:
    - `interview_date`: Date/time of GS interview
    - `decision`: "pass", "fail", or "pending"
    - `scorecard`: Assessment scorecard with criteria scores
    - `notes`: Optional assessment notes
    
    **Workflow**:
    - If "pass": Returns to STAFF_REVIEW for final approval
    - If "fail": Transitions to REJECTED
    - If "pending": Remains in GS_ASSESSMENT stage
    
    **Actions**:
    - Updates `gs_assessment` JSONB field
    - Creates timeline entry
    - Transitions stage based on decision
    """
    service = StaffService(db)
    try:
        return service.record_gs_assessment(
            application_id=application_id,
            staff_id=staff_profile.id,
            interview_date=request.interview_date,
            decision=request.decision,
            scorecard=request.scorecard,
            notes=request.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# OFFER LETTER GENERATION
# ============================================================================

@router.post("/applications/{application_id}/generate-offer-letter",
             response_model=OfferLetterResponse,
             summary="Generate offer letter PDF")
def generate_offer_letter(
    application_id: UUID,
    request: OfferLetterRequest,
    staff_profile: StaffProfile = Depends(get_staff_profile),
    db: Session = Depends(get_db)
):
    """
    Generate offer letter PDF for approved application.
    
    **Request body**:
    - `course_start_date`: Course commencement date
    - `tuition_fee`: Tuition fee amount (overrides course default)
    - `material_fee`: Additional material fees
    - `conditions`: List of offer conditions
    - `template`: Template name (default: "standard")
    
    **Requirements**:
    - Application must be in OFFER_GENERATED stage
    
    **Actions**:
    - Generates professional PDF offer letter
    - Saves to uploads/offer_letters/ directory
    - Returns URL/path to generated PDF
    
    **Returns**: OfferLetterResponse with PDF URL and metadata
    """
    # Get application
    staff_repo = StaffRepository(db)
    app = staff_repo.get_application_with_details(application_id)
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    
    # Verify application is in correct stage
    if app.current_stage != ApplicationStage.OFFER_GENERATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Application must be in OFFER_GENERATED stage. Current stage: {app.current_stage.value}"
        )
    
    # Get RTO profile
    rto_profile = db.query(RtoProfile).filter(RtoProfile.id == app.student.user_account.rto_profile_id).first()
    if not rto_profile:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                          detail="RTO profile not found")
    
    # Build offer details
    offer_details = {
        "course_start_date": request.course_start_date,
        "tuition_fee": request.tuition_fee,
        "material_fee": request.material_fee,
        "conditions": request.conditions
    }
    
    # Generate PDF
    offer_service = OfferLetterService()
    try:
        pdf_path = offer_service.generate_offer_letter(
            application=app,
            offer_details=offer_details,
            rto_profile=rto_profile
        )
        
        # Update enrollment_data with offer letter path
        enrollment_data = app.enrollment_data or {}
        enrollment_data["offer_letter_pdf"] = pdf_path
        enrollment_data["offer_letter_generated_at"] = datetime.now().isoformat()
        app.enrollment_data = enrollment_data
        db.commit()
        
        return OfferLetterResponse(
            application_id=application_id,
            offer_letter_url=pdf_path,
            generated_at=datetime.now(),
            expires_at=None  # Could add expiry logic
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate offer letter: {str(e)}"
        )
