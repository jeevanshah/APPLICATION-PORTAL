"""
Student profile management and application tracking endpoints.

Agents can create student profiles with login credentials.
Students can log in and track their application progress.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import get_current_user, get_db
from app.models import (
    AgentProfile,
    Application,
    ApplicationStage,
    ApplicationStageHistory,
    Document,
    DocumentType,
    StaffProfile,
    StudentProfile,
    TimelineEntry,
    UserAccount,
    UserRole,
)
from app.schemas.student import (
    ApplicationSummaryForStudent,
    ApplicationTrackingDetailResponse,
    RecentTimelineActivity,
    RequiredDocumentItem,
    StageProgressItem,
    StudentDashboardResponse,
    StudentListResponse,
    StudentProfileCreateRequest,
    StudentProfileResponse,
    StudentProfileUpdateRequest,
)
from app.services.auth import AuthService

router = APIRouter()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _calculate_stage_progress(
        application: Application,
        db: Session) -> List[StageProgressItem]:
    """Calculate progress through application stages with durations."""
    all_stages = [
        ApplicationStage.DRAFT,
        ApplicationStage.SUBMITTED,
        ApplicationStage.STAFF_REVIEW,
        ApplicationStage.AWAITING_DOCUMENTS,
        ApplicationStage.GS_ASSESSMENT,
        ApplicationStage.OFFER_GENERATED,
        ApplicationStage.OFFER_ACCEPTED,
        ApplicationStage.ENROLLED
    ]

    # Get stage history
    stage_history = db.query(ApplicationStageHistory).filter(
        ApplicationStageHistory.application_id == application.id
    ).order_by(ApplicationStageHistory.changed_at).all()

    progress = []
    current_stage = application.current_stage

    # Build stage progress list
    for i, stage in enumerate(all_stages):
        # Find when this stage was entered
        history_entry = next(
            (h for h in stage_history if h.to_stage == stage),
            None
        )

        if history_entry:
            # Calculate duration in this stage
            if i + 1 < len(stage_history):
                next_entry = stage_history[i + 1]
                duration = (
                    next_entry.changed_at -
                    history_entry.changed_at).days
            elif stage == current_stage:
                duration = (datetime.utcnow() - history_entry.changed_at).days
            else:
                duration = None

            progress.append(StageProgressItem(
                stage=stage.value,
                status="current" if stage == current_stage else "completed",
                completed_at=history_entry.changed_at,
                duration_days=duration
            ))
        else:
            # Stage not yet reached
            progress.append(StageProgressItem(
                stage=stage.value,
                status="pending",
                completed_at=None,
                duration_days=None
            ))

    return progress


def _get_required_documents(
        application: Application,
        db: Session) -> List[RequiredDocumentItem]:
    """Get list of required documents with upload status."""
    # Get all document types required for current and previous stages
    stage_order = [
        ApplicationStage.DRAFT,
        ApplicationStage.SUBMITTED,
        ApplicationStage.STAFF_REVIEW,
        ApplicationStage.AWAITING_DOCUMENTS,
        ApplicationStage.GS_ASSESSMENT,
        ApplicationStage.OFFER_GENERATED,
        ApplicationStage.OFFER_ACCEPTED,
        ApplicationStage.ENROLLED
    ]

    current_stage_index = stage_order.index(application.current_stage)
    # Include current + 1 future stage
    relevant_stages = stage_order[:current_stage_index + 2]

    # Get required document types
    document_types = db.query(DocumentType).filter(
        DocumentType.stage.in_(relevant_stages)
    ).order_by(DocumentType.display_order).all()

    # Get uploaded documents
    uploaded_docs = db.query(Document).filter(
        Document.application_id == application.id
    ).all()

    required_docs = []
    for doc_type in document_types:
        # Find if this document type has been uploaded
        uploaded_doc = next(
            (d for d in uploaded_docs if d.document_type_id == doc_type.id),
            None
        )

        required_docs.append(RequiredDocumentItem(
            document_type_code=doc_type.code,
            document_type_name=doc_type.name,
            is_mandatory=doc_type.is_mandatory,
            status=uploaded_doc.status.value if uploaded_doc else None,
            uploaded_at=uploaded_doc.uploaded_at if uploaded_doc else None,
            ocr_status=uploaded_doc.ocr_status.value if uploaded_doc else None
        ))

    return required_docs


def _generate_next_steps(
        application: Application,
        required_docs: List[RequiredDocumentItem]) -> List[str]:
    """Generate actionable next steps for the student."""
    next_steps = []

    if application.current_stage == ApplicationStage.DRAFT:
        next_steps.append("Complete your application form and submit it")
        # Check for missing required sections
        if not application.emergency_contacts:
            next_steps.append("Add emergency contact information")
        if not application.health_cover_policy:
            next_steps.append("Provide health cover policy details")
        if not application.language_cultural_data:
            next_steps.append("Complete language and cultural information")

    elif application.current_stage == ApplicationStage.SUBMITTED:
        next_steps.append("Your application is under review by our staff")
        next_steps.append("Please check back regularly for updates")

    elif application.current_stage == ApplicationStage.AWAITING_DOCUMENTS:
        # List missing mandatory documents
        missing_docs = [
            doc for doc in required_docs
            if doc.is_mandatory and doc.status is None
        ]
        if missing_docs:
            next_steps.append(
                f"Upload {
                    len(missing_docs)} required document(s):")
            for doc in missing_docs[:3]:  # Show max 3
                next_steps.append(f"  • {doc.document_type_name}")

    elif application.current_stage == ApplicationStage.GS_ASSESSMENT:
        next_steps.append("Genuine Student assessment is in progress")
        next_steps.append("You may be contacted for an interview")

    elif application.current_stage == ApplicationStage.OFFER_GENERATED:
        next_steps.append("Congratulations! An offer has been generated")
        next_steps.append("Review and accept your offer to proceed")

    elif application.current_stage == ApplicationStage.OFFER_ACCEPTED:
        next_steps.append("Complete enrollment formalities")
        next_steps.append("Pay tuition fees if not already paid")

    elif application.current_stage == ApplicationStage.ENROLLED:
        next_steps.append("Welcome! You are now enrolled")
        next_steps.append("Check your email for orientation details")

    if not next_steps:
        next_steps.append("No action required at this time")

    return next_steps


# ============================================================================
# STUDENT PROFILE ENDPOINTS (Agent creates students)
# ============================================================================

@router.post("", status_code=status.HTTP_201_CREATED,
             response_model=StudentProfileResponse)
async def create_student_profile(
    data: StudentProfileCreateRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new student profile with login credentials.

    **Permissions**: Agents and Staff can create student profiles.

    **Workflow**:
    1. Agent enters student details and initial password
    2. System creates user account + student profile
    3. Student can log in with provided credentials
    4. First login may prompt password reset
    """
    # Permission check: only agents and staff can create students
    if current_user.role not in [
            UserRole.AGENT,
            UserRole.STAFF,
            UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only agents and staff can create student profiles"
        )

    auth_service = AuthService(db)

    try:
        # Prepare student profile data
        profile_data = {
            "given_name": data.given_name,
            "family_name": data.family_name,
            "date_of_birth": data.date_of_birth,
            "passport_number": data.passport_number,
            "nationality": data.nationality,
            "visa_type": data.visa_type,
            "phone": data.phone,
            "address": data.address,
        }

        # Register student using AuthService
        user_account = auth_service.register_user(
            email=data.email,
            password=data.password,
            role=UserRole.STUDENT,
            rto_profile_id=current_user.rto_profile_id,
            profile_data=profile_data
        )

        # Get created student profile
        student_profile = db.query(StudentProfile).filter(
            StudentProfile.user_account_id == user_account.id
        ).first()

        # Build response
        return StudentProfileResponse(
            id=student_profile.id,
            user_account_id=user_account.id,
            email=user_account.email,
            given_name=student_profile.given_name,
            family_name=student_profile.family_name,
            date_of_birth=student_profile.date_of_birth,
            passport_number=student_profile.passport_number,
            nationality=student_profile.nationality,
            visa_type=student_profile.visa_type,
            phone=student_profile.phone,
            address=student_profile.address,
            status=user_account.status.value,
            created_at=student_profile.created_at
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create student profile: {str(e)}"
        )


@router.get("", response_model=StudentListResponse)
async def list_students(
    page: int = Query(
        1,
        ge=1),
    page_size: int = Query(
        20,
        ge=1,
        le=100),
    search: Optional[str] = Query(
        None,
        description="Search by name, email, or passport"),
    nationality: Optional[str] = Query(None),
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)):
    """
    List students with pagination and filters.

    **Permissions**:
    - Agents see students they created applications for
    - Staff/Admin see all students
    """
    # Permission check
    if current_user.role not in [
            UserRole.AGENT,
            UserRole.STAFF,
            UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only agents and staff can list students"
        )

    # Base query
    query = db.query(StudentProfile).join(UserAccount)

    # Apply filters
    if current_user.role == UserRole.AGENT:
        # Agents see only students for whom they created applications
        query = query.join(Application).filter(
            Application.agent_profile_id == current_user.agent_profile.id
        ).distinct()

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (StudentProfile.given_name.ilike(search_filter)) |
            (StudentProfile.family_name.ilike(search_filter)) |
            (StudentProfile.passport_number.ilike(search_filter)) |
            (UserAccount.email.ilike(search_filter))
        )

    if nationality:
        query = query.filter(StudentProfile.nationality == nationality)

    # Get total count
    total = query.count()

    # Paginate
    students = query.offset((page - 1) * page_size).limit(page_size).all()

    # Build response
    student_responses = []
    for student in students:
        student_responses.append(StudentProfileResponse(
            id=student.id,
            user_account_id=student.user_account_id,
            email=student.user_account.email,
            given_name=student.given_name,
            family_name=student.family_name,
            date_of_birth=student.date_of_birth,
            passport_number=student.passport_number,
            nationality=student.nationality,
            visa_type=student.visa_type,
            phone=student.phone,
            address=student.address,
            status=student.user_account.status.value,
            created_at=student.created_at
        ))

    return StudentListResponse(
        students=student_responses,
        total=total,
        page=page,
        page_size=page_size
    )


# ============================================================================
# STUDENT DASHBOARD (Student views their own data)
# ============================================================================

@router.get("/me/dashboard", response_model=StudentDashboardResponse)
async def get_student_dashboard(
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get student dashboard with applications and recent activity.

    **Permissions**: Students can only view their own dashboard.

    **Returns**:
    - Student profile information
    - List of all applications (with completion %)
    - Recent timeline activities across all applications
    - Statistics (draft/submitted/in-review/offers/enrolled counts)
    """
    # Permission check
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can access student dashboard"
        )

    # Get student profile
    student_profile = db.query(StudentProfile).filter(
        StudentProfile.user_account_id == current_user.id
    ).first()

    if not student_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found"
        )

    # Get all applications for this student
    applications = db.query(Application).filter(
        Application.student_profile_id == student_profile.id).options(
        joinedload(
            Application.course),
        joinedload(
            Application.assigned_staff).joinedload(
            StaffProfile.user_account)).order_by(
        desc(
            Application.updated_at)).all()

    # Build application summaries
    app_summaries = []
    stats = {
        "total_applications": len(applications),
        "draft_count": 0,
        "submitted_count": 0,
        "in_review_count": 0,
        "offers_count": 0,
        "enrolled_count": 0
    }

    for app in applications:
        # Calculate completion percentage
        from app.api.v1.endpoints.applications import _calculate_completion_percentage
        completion = _calculate_completion_percentage(app)

        # Update stats
        if app.current_stage == ApplicationStage.DRAFT:
            stats["draft_count"] += 1
        elif app.current_stage == ApplicationStage.SUBMITTED:
            stats["submitted_count"] += 1
        elif app.current_stage in [ApplicationStage.STAFF_REVIEW, ApplicationStage.AWAITING_DOCUMENTS, ApplicationStage.GS_ASSESSMENT]:
            stats["in_review_count"] += 1
        elif app.current_stage in [ApplicationStage.OFFER_GENERATED, ApplicationStage.OFFER_ACCEPTED]:
            stats["offers_count"] += 1
        elif app.current_stage == ApplicationStage.ENROLLED:
            stats["enrolled_count"] += 1

        # Get assigned staff name
        assigned_staff_name = None
        if app.assigned_staff:
            assigned_staff_name = f"{app.assigned_staff.job_title or 'Staff'}"

        app_summaries.append(ApplicationSummaryForStudent(
            id=app.id,
            course_code=app.course.course_code,
            course_name=app.course.course_name,
            intake=app.course.intake,
            current_stage=app.current_stage.value,
            completion_percentage=completion,
            submitted_at=app.submitted_at,
            last_updated=app.updated_at,
            assigned_staff_name=assigned_staff_name
        ))

    # Get recent timeline activities (last 10 across all applications)
    recent_timeline = db.query(TimelineEntry).filter(
        TimelineEntry.application_id.in_([app.id for app in applications])
    ).options(
        joinedload(TimelineEntry.actor)
    ).order_by(desc(TimelineEntry.created_at)).limit(10).all()

    recent_activity = []
    for entry in recent_timeline:
        actor_name = None
        if entry.actor:
            # Try to get name from profile
            if entry.actor.role == UserRole.STUDENT and entry.actor.student_profile:
                actor_name = f"{
                    entry.actor.student_profile.given_name} {
                    entry.actor.student_profile.family_name}"
            elif entry.actor.role == UserRole.AGENT and entry.actor.agent_profile:
                actor_name = entry.actor.agent_profile.agency_name
            elif entry.actor.role in [UserRole.STAFF, UserRole.ADMIN] and entry.actor.staff_profile:
                actor_name = entry.actor.staff_profile.job_title or "Staff"

        recent_activity.append(RecentTimelineActivity(
            id=entry.id,
            application_id=entry.application_id,
            entry_type=entry.entry_type.value,
            message=entry.message,
            created_at=entry.created_at,
            actor_name=actor_name
        ))

    # Build student profile response
    student_response = StudentProfileResponse(
        id=student_profile.id,
        user_account_id=current_user.id,
        email=current_user.email,
        given_name=student_profile.given_name,
        family_name=student_profile.family_name,
        date_of_birth=student_profile.date_of_birth,
        passport_number=student_profile.passport_number,
        nationality=student_profile.nationality,
        visa_type=student_profile.visa_type,
        phone=student_profile.phone,
        address=student_profile.address,
        status=current_user.status.value,
        created_at=student_profile.created_at
    )

    return StudentDashboardResponse(
        student=student_response,
        applications=app_summaries,
        recent_activity=recent_activity,
        statistics=stats
    )


# ============================================================================
# APPLICATION TRACKING (Student tracks specific application)
# ============================================================================

@router.get("/me/applications/{application_id}/track",
            response_model=ApplicationTrackingDetailResponse)
async def track_application(
    application_id: UUID,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed tracking information for a specific application.

    **Permissions**: Students can only track their own applications.

    **Returns**:
    - Application details (course, stage, completion %)
    - Stage-by-stage progress with durations
    - Required documents with upload status
    - Timeline history
    - Agent and staff contact information
    - Next steps / action items
    """
    # Permission check
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can track applications"
        )

    # Get student profile
    student_profile = db.query(StudentProfile).filter(
        StudentProfile.user_account_id == current_user.id
    ).first()

    if not student_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found"
        )

    # Get application with relationships
    application = db.query(Application).filter(
        and_(
            Application.id == application_id,
            Application.student_profile_id == student_profile.id)).options(
        joinedload(
            Application.course),
        joinedload(
            Application.agent).joinedload(
            AgentProfile.user_account),
        joinedload(
            Application.assigned_staff).joinedload(
            StaffProfile.user_account)).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or you don't have permission to view it")

    # Calculate completion percentage
    from app.api.v1.endpoints.applications import _calculate_completion_percentage
    completion = _calculate_completion_percentage(application)

    # Get stage progress
    stage_progress = _calculate_stage_progress(application, db)

    # Get required documents
    required_docs = _get_required_documents(application, db)

    # Get timeline history
    timeline_entries = db.query(TimelineEntry).filter(
        TimelineEntry.application_id == application_id
    ).options(
        joinedload(TimelineEntry.actor)
    ).order_by(desc(TimelineEntry.created_at)).all()

    timeline_items = []
    for entry in timeline_entries:
        actor_name = None
        if entry.actor:
            if entry.actor.role == UserRole.STUDENT and entry.actor.student_profile:
                actor_name = f"{
                    entry.actor.student_profile.given_name} {
                    entry.actor.student_profile.family_name}"
            elif entry.actor.role == UserRole.AGENT and entry.actor.agent_profile:
                actor_name = entry.actor.agent_profile.agency_name
            elif entry.actor.role in [UserRole.STAFF, UserRole.ADMIN] and entry.actor.staff_profile:
                actor_name = entry.actor.staff_profile.job_title or "Staff"

        timeline_items.append(RecentTimelineActivity(
            id=entry.id,
            application_id=entry.application_id,
            entry_type=entry.entry_type.value,
            message=entry.message,
            created_at=entry.created_at,
            actor_name=actor_name
        ))

    # Get agent information
    agent_name = None
    agent_agency = None
    agent_phone = None
    if application.agent:
        agent_name = application.agent.user_account.email
        agent_agency = application.agent.agency_name
        agent_phone = application.agent.phone

    # Get assigned staff information
    assigned_staff_name = None
    assigned_staff_email = None
    if application.assigned_staff:
        assigned_staff_name = application.assigned_staff.job_title or "Staff"
        assigned_staff_email = application.assigned_staff.user_account.email

    # Generate next steps
    next_steps = _generate_next_steps(application, required_docs)

    return ApplicationTrackingDetailResponse(
        id=application.id,
        course_code=application.course.course_code,
        course_name=application.course.course_name,
        intake=application.course.intake,
        campus=application.course.campus,
        tuition_fee=float(application.course.tuition_fee),
        current_stage=application.current_stage.value,
        completion_percentage=completion,
        submitted_at=application.submitted_at,
        decision_at=application.decision_at,
        stage_progress=stage_progress,
        required_documents=required_docs,
        timeline=timeline_items,
        agent_name=agent_name,
        agent_agency=agent_agency,
        agent_phone=agent_phone,
        assigned_staff_name=assigned_staff_name,
        assigned_staff_email=assigned_staff_email,
        next_steps=next_steps
    )


# ============================================================================
# STUDENT PROFILE UPDATE
# ============================================================================

@router.patch("/me", response_model=StudentProfileResponse)
async def update_my_profile(
    data: StudentProfileUpdateRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update student's own profile.

    **Permissions**: Students can update their own profile.
    """
    # Permission check
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can update their profile"
        )

    # Get student profile
    student_profile = db.query(StudentProfile).filter(
        StudentProfile.user_account_id == current_user.id
    ).first()

    if not student_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found"
        )

    # Update fields
    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(student_profile, field, value)

    db.commit()
    db.refresh(student_profile)

    return StudentProfileResponse(
        id=student_profile.id,
        user_account_id=current_user.id,
        email=current_user.email,
        given_name=student_profile.given_name,
        family_name=student_profile.family_name,
        date_of_birth=student_profile.date_of_birth,
        passport_number=student_profile.passport_number,
        nationality=student_profile.nationality,
        visa_type=student_profile.visa_type,
        phone=student_profile.phone,
        address=student_profile.address,
        status=current_user.status.value,
        created_at=student_profile.created_at
    )
