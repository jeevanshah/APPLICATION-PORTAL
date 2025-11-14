"""
Application endpoints: CRUD operations with draft/resume support.
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from uuid import UUID

from app.db.database import get_db
from app.models import (
    Application, ApplicationStage, UserAccount, StudentProfile,
    CourseOffering, AgentProfile, StaffProfile, TimelineEntry,
    TimelineEntryType, UserRole, ApplicationStageHistory
)
from app.api.dependencies import get_current_user
from app.schemas.application import (
    ApplicationCreateRequest, ApplicationUpdateRequest, ApplicationSubmitRequest,
    ApplicationAssignRequest, ApplicationStageChangeRequest,
    ApplicationSummary, ApplicationDetail, ApplicationResponse
)

router = APIRouter()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _calculate_completion_percentage(app: Application) -> int:
    """Calculate form completion based on filled JSONB fields."""
    total_sections = 9
    completed = 0
    
    if app.emergency_contacts:
        completed += 1
    if app.health_cover_policy:
        completed += 1
    if app.disability_support:
        completed += 1
    if app.language_cultural_data:
        completed += 1
    if app.survey_responses:
        completed += 1
    if app.additional_services is not None:  # Can be empty list
        completed += 1
    if app.signature_data:
        completed += 1
    if app.usi:
        completed += 1
    if app.enrollment_data:
        completed += 1
    
    return int((completed / total_sections) * 100)


def _create_timeline_entry(
    db: Session,
    application_id: UUID,
    entry_type: TimelineEntryType,
    message: str,
    actor: UserAccount,
    stage: Optional[ApplicationStage] = None
):
    """Helper to create timeline entries."""
    entry = TimelineEntry(
        application_id=application_id,
        entry_type=entry_type,
        actor_id=actor.id,
        actor_role=actor.role,
        message=message,
        stage=stage
    )
    db.add(entry)
    return entry


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApplicationResponse)
async def create_application_draft(
    request: ApplicationCreateRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create new application in DRAFT stage.
    
    Students can start filling the form and save progress.
    """
    # Validate course offering exists
    course = db.query(CourseOffering).filter(CourseOffering.id == request.course_offering_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course offering not found"
        )
    
    # Determine student_profile_id
    if current_user.role == UserRole.STUDENT:
        # Student creating their own application
        student_profile = db.query(StudentProfile).filter(
            StudentProfile.user_account_id == current_user.id
        ).first()
        if not student_profile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student profile not found. Please complete your profile first."
            )
        student_profile_id = student_profile.id
    elif request.student_profile_id:
        # Agent/staff creating on behalf of student
        student_profile_id = request.student_profile_id
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="student_profile_id required when creating application as agent/staff"
        )
    
    # Create draft application
    new_app = Application(
        student_profile_id=student_profile_id,
        agent_profile_id=request.agent_profile_id,
        course_offering_id=request.course_offering_id,
        current_stage=ApplicationStage.DRAFT,
        form_metadata={
            "version": "1.0",
            "completed_sections": [],
            "auto_save_count": 0,
            "last_saved_at": datetime.utcnow().isoformat()
        }
    )
    
    db.add(new_app)
    db.commit()
    db.refresh(new_app)
    
    # Create timeline entry
    _create_timeline_entry(
        db=db,
        application_id=new_app.id,
        entry_type=TimelineEntryType.APPLICATION_CREATED,
        message=f"Application created for {course.course_name}",
        actor=current_user,
        stage=ApplicationStage.DRAFT
    )
    db.commit()
    
    return ApplicationResponse(
        application=ApplicationDetail.model_validate(new_app),
        message="Application draft created successfully. You can now fill in the details."
    )


@router.get("", response_model=List[ApplicationSummary])
async def list_applications(
    stage: Optional[ApplicationStage] = Query(None, description="Filter by stage"),
    student_id: Optional[UUID] = Query(None, description="Filter by student"),
    agent_id: Optional[UUID] = Query(None, description="Filter by agent"),
    assigned_staff_id: Optional[UUID] = Query(None, description="Filter by assigned staff"),
    from_date: Optional[datetime] = Query(None, description="Filter by created date (from)"),
    to_date: Optional[datetime] = Query(None, description="Filter by created date (to)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List applications with filtering.
    
    **Permissions:**
    - Students: see only their own applications
    - Agents: see applications they submitted
    - Staff/Admin: see all applications (with filters)
    """
    query = db.query(Application).options(
        joinedload(Application.student),
        joinedload(Application.course),
        joinedload(Application.agent),
        joinedload(Application.assigned_staff)
    )
    
    # Role-based filtering
    if current_user.role == UserRole.STUDENT:
        student_profile = db.query(StudentProfile).filter(
            StudentProfile.user_account_id == current_user.id
        ).first()
        if student_profile:
            query = query.filter(Application.student_profile_id == student_profile.id)
        else:
            return []  # Student has no profile yet
    
    elif current_user.role == UserRole.AGENT:
        agent_profile = db.query(AgentProfile).filter(
            AgentProfile.user_account_id == current_user.id
        ).first()
        if agent_profile:
            query = query.filter(Application.agent_profile_id == agent_profile.id)
        else:
            return []
    
    # Apply filters
    if stage:
        query = query.filter(Application.current_stage == stage)
    if student_id:
        query = query.filter(Application.student_profile_id == student_id)
    if agent_id:
        query = query.filter(Application.agent_profile_id == agent_id)
    if assigned_staff_id:
        query = query.filter(Application.assigned_staff_id == assigned_staff_id)
    if from_date:
        query = query.filter(Application.created_at >= from_date)
    if to_date:
        query = query.filter(Application.created_at <= to_date)
    
    # Order by most recent first
    query = query.order_by(Application.updated_at.desc())
    
    applications = query.offset(offset).limit(limit).all()
    
    # Build summary response with computed fields
    results = []
    for app in applications:
        summary = ApplicationSummary.model_validate(app)
        summary.student_name = f"{app.student.given_name} {app.student.family_name}" if app.student else None
        summary.course_name = app.course.course_name if app.course else None
        summary.agent_name = app.agent.agency_name if app.agent else None
        summary.assigned_staff_name = app.assigned_staff.job_title if app.assigned_staff else None
        summary.completion_percentage = _calculate_completion_percentage(app)
        results.append(summary)
    
    return results


@router.get("/{application_id}", response_model=ApplicationDetail)
async def get_application(
    application_id: UUID,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get full application details.
    
    Used for resuming draft or viewing submitted application.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    # Permission check
    if current_user.role == UserRole.STUDENT:
        student_profile = db.query(StudentProfile).filter(
            StudentProfile.user_account_id == current_user.id
        ).first()
        if not student_profile or app.student_profile_id != student_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this application"
            )
    
    elif current_user.role == UserRole.AGENT:
        agent_profile = db.query(AgentProfile).filter(
            AgentProfile.user_account_id == current_user.id
        ).first()
        if not agent_profile or app.agent_profile_id != agent_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this application"
            )
    
    return ApplicationDetail.model_validate(app)


@router.patch("/{application_id}", response_model=ApplicationResponse)
async def update_application(
    application_id: UUID,
    request: ApplicationUpdateRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update application (auto-save or manual save).
    
    Supports partial updates - only provided fields are updated.
    Used for draft/resume workflow.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    # Only allow updates on DRAFT applications
    if app.current_stage != ApplicationStage.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update application in {app.current_stage.value} stage. Only DRAFT applications can be edited."
        )
    
    # Permission check (same as get)
    if current_user.role == UserRole.STUDENT:
        student_profile = db.query(StudentProfile).filter(
            StudentProfile.user_account_id == current_user.id
        ).first()
        if not student_profile or app.student_profile_id != student_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    # Update fields (only if provided)
    update_data = request.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if hasattr(app, field):
            # Convert Pydantic models to dict for JSONB storage
            if value is not None and hasattr(value, 'model_dump'):
                setattr(app, field, value.model_dump())
            elif isinstance(value, list) and value and hasattr(value[0], 'model_dump'):
                setattr(app, field, [item.model_dump() for item in value])
            else:
                setattr(app, field, value)
    
    # Update form_metadata
    if app.form_metadata:
        metadata = app.form_metadata.copy() if isinstance(app.form_metadata, dict) else {}
    else:
        metadata = {}
    
    metadata['last_saved_at'] = datetime.utcnow().isoformat()
    metadata['auto_save_count'] = metadata.get('auto_save_count', 0) + 1
    
    if request.form_metadata:
        # Merge incoming metadata
        incoming = request.form_metadata.model_dump(exclude_unset=True)
        metadata.update(incoming)
    
    app.form_metadata = metadata
    app.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(app)
    
    return ApplicationResponse(
        application=ApplicationDetail.model_validate(app),
        message="Application saved successfully"
    )


@router.post("/{application_id}/submit", response_model=ApplicationResponse)
async def submit_application(
    application_id: UUID,
    request: ApplicationSubmitRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit application for review.
    
    Transitions from DRAFT → SUBMITTED stage.
    Validates all required fields are completed.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    
    if app.current_stage != ApplicationStage.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Application already submitted (current stage: {app.current_stage.value})"
        )
    
    # Permission check
    if current_user.role == UserRole.STUDENT:
        student_profile = db.query(StudentProfile).filter(
            StudentProfile.user_account_id == current_user.id
        ).first()
        if not student_profile or app.student_profile_id != student_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    # Validate required fields
    validation_errors = []
    if not app.emergency_contacts:
        validation_errors.append("Emergency contacts required")
    if not app.health_cover_policy:
        validation_errors.append("Health cover policy required")
    if not app.language_cultural_data:
        validation_errors.append("Language and cultural data required")
    
    if validation_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation failed: {', '.join(validation_errors)}"
        )
    
    # Update stage
    previous_stage = app.current_stage
    app.current_stage = ApplicationStage.SUBMITTED
    app.submitted_at = datetime.utcnow()
    
    # Record stage change
    stage_history = ApplicationStageHistory(
        application_id=app.id,
        from_stage=previous_stage,
        to_stage=ApplicationStage.SUBMITTED,
        changed_by=current_user.id,
        notes="Application submitted by student"
    )
    db.add(stage_history)
    
    # Create timeline entry
    _create_timeline_entry(
        db=db,
        application_id=app.id,
        entry_type=TimelineEntryType.STAGE_CHANGED,
        message=f"Application submitted for review",
        actor=current_user,
        stage=ApplicationStage.SUBMITTED
    )
    
    db.commit()
    db.refresh(app)
    
    return ApplicationResponse(
        application=ApplicationDetail.model_validate(app),
        message="Application submitted successfully! Our team will review it shortly."
    )


@router.post("/{application_id}/assign", response_model=ApplicationResponse)
async def assign_application(
    application_id: UUID,
    request: ApplicationAssignRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Assign application to staff member.
    
    **Permissions:** Staff/Admin only
    """
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff/admin can assign applications"
        )
    
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    
    # Validate staff exists
    staff = db.query(StaffProfile).filter(StaffProfile.id == request.staff_id).first()
    if not staff:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found")
    
    app.assigned_staff_id = request.staff_id
    
    # Create timeline entry
    _create_timeline_entry(
        db=db,
        application_id=app.id,
        entry_type=TimelineEntryType.ASSIGNED,
        message=f"Application assigned to {staff.job_title}",
        actor=current_user
    )
    
    db.commit()
    db.refresh(app)
    
    return ApplicationResponse(
        application=ApplicationDetail.model_validate(app),
        message=f"Application assigned to {staff.job_title}"
    )


@router.post("/{application_id}/change-stage", response_model=ApplicationResponse)
async def change_application_stage(
    application_id: UUID,
    request: ApplicationStageChangeRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Transition application to new stage.
    
    **Permissions:** Staff/Admin only
    """
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff/admin can change application stage"
        )
    
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    
    previous_stage = app.current_stage
    app.current_stage = request.to_stage
    
    # Record stage change
    stage_history = ApplicationStageHistory(
        application_id=app.id,
        from_stage=previous_stage,
        to_stage=request.to_stage,
        changed_by=current_user.id,
        notes=request.notes
    )
    db.add(stage_history)
    
    # Create timeline entry
    _create_timeline_entry(
        db=db,
        application_id=app.id,
        entry_type=TimelineEntryType.STAGE_CHANGED,
        message=f"Stage changed: {previous_stage.value} → {request.to_stage.value}",
        actor=current_user,
        stage=request.to_stage
    )
    
    db.commit()
    db.refresh(app)
    
    return ApplicationResponse(
        application=ApplicationDetail.model_validate(app),
        message=f"Application moved to {request.to_stage.value}"
    )
