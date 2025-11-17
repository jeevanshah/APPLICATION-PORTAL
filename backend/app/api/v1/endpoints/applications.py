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
from app.services.application import (
    ApplicationService, ApplicationError, ApplicationNotFoundError,
    ApplicationPermissionError, ApplicationValidationError
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
    
    **Permissions:** Agent/Staff/Admin only. Students cannot create applications.
    Agents create applications on behalf of students and fill all details.
    """
    app_service = ApplicationService(db)
    
    try:
        # Validate student_profile_id is provided
        if not request.student_profile_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="student_profile_id required when creating application"
            )
        
        # Create draft application using service
        new_app = app_service.create_draft(
            course_offering_id=request.course_offering_id,
            student_profile_id=request.student_profile_id,
            agent_profile_id=request.agent_profile_id,
            user_id=current_user.id,
            user_role=current_user.role
        )
        
        # Create timeline entry
        _create_timeline_entry(
            db=db,
            application_id=new_app.id,
            entry_type=TimelineEntryType.APPLICATION_CREATED,
            message=f"Application created for course",
            actor=current_user,
            stage=ApplicationStage.DRAFT
        )
        db.commit()
        
        return ApplicationResponse(
            application=ApplicationDetail.model_validate(new_app),
            message="Application draft created successfully. You can now fill in the details."
        )
    
    except ApplicationPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ApplicationValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create application: {str(e)}"
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
    app_service = ApplicationService(db)
    
    try:
        # Get applications using service (handles role-based filtering)
        applications = app_service.list_applications(
            user_id=current_user.id,
            user_role=current_user.role,
            skip=offset,
            limit=limit,
            stage=stage
        )
        
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
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list applications: {str(e)}"
        )


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
    app_service = ApplicationService(db)
    
    try:
        app = app_service.get_application(
            application_id=application_id,
            user_id=current_user.id,
            user_role=current_user.role
        )
        
        return ApplicationDetail.model_validate(app)
    
    except ApplicationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ApplicationPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.patch("/{application_id}", response_model=ApplicationResponse)
async def update_application(
    application_id: UUID,
    request: ApplicationUpdateRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update application (auto-save or manual save).
    
    **Permissions:** Agent/Staff/Admin only. Students cannot edit applications.
    Agents fill the entire application form on behalf of students.
    Supports partial updates - only provided fields are updated.
    """
    app_service = ApplicationService(db)
    
    try:
        # Prepare update data
        update_data = request.model_dump(exclude_unset=True)
        
        # Convert Pydantic models to dict for JSONB storage
        for field, value in list(update_data.items()):
            if value is not None and hasattr(value, 'model_dump'):
                update_data[field] = value.model_dump()
            elif isinstance(value, list) and value and hasattr(value[0], 'model_dump'):
                update_data[field] = [item.model_dump() for item in value]
        
        # Update using service
        app = app_service.update_application(
            application_id=application_id,
            update_data=update_data,
            user_id=current_user.id,
            user_role=current_user.role
        )
        
        return ApplicationResponse(
            application=ApplicationDetail.model_validate(app),
            message="Application updated successfully"
        )
    
    except ApplicationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ApplicationPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ApplicationValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update application: {str(e)}"
        )
    
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
    
    **Permissions:** Agent/Staff/Admin only. Students cannot submit applications.
    Transitions from DRAFT → SUBMITTED stage.
    Validates all required fields are completed.
    """
    app_service = ApplicationService(db)
    
    try:
        # Submit using service
        app = app_service.submit_application(
            application_id=application_id,
            user_id=current_user.id,
            user_role=current_user.role
        )
        
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
        
        return ApplicationResponse(
            application=ApplicationDetail.model_validate(app),
            message="Application submitted successfully! Our team will review it shortly."
        )
    
    except ApplicationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ApplicationPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ApplicationValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit application: {str(e)}"
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
