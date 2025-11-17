"""
12-step application form endpoints.
Each step can be saved independently, allowing for progressive form filling.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import UserAccount
from app.api.dependencies import get_current_user
from app.schemas.application_steps import (
    PersonalDetailsRequest, EmergencyContactRequest, HealthCoverRequest,
    LanguageCulturalRequest, DisabilitySupportRequest, SchoolingHistoryRequest,
    PreviousQualificationsRequest, EmploymentHistoryRequest, USIRequest,
    AdditionalServicesRequest, SurveyRequest, DocumentStepResponse,
    StepUpdateResponse
)
from app.services.application import (
    ApplicationService, ApplicationError, ApplicationNotFoundError,
    ApplicationPermissionError, ApplicationValidationError
)

router = APIRouter()


def _calculate_completion_percentage(app) -> int:
    """Calculate form completion percentage based on completed_sections metadata."""
    if not app.form_metadata or 'completed_sections' not in app.form_metadata:
        return 0
    
    completed_sections = app.form_metadata.get('completed_sections', [])
    total_steps = 12
    
    return int((len(completed_sections) / total_steps) * 100)


def _build_step_response(
    app,
    step_number: int,
    step_name: str,
    message: str = "Step saved successfully"
) -> StepUpdateResponse:
    """Build standard step response."""
    completion = _calculate_completion_percentage(app)
    
    # Determine next step
    next_steps = [
        "personal_details", "emergency_contact", "health_cover",
        "language_cultural", "disability", "schooling",
        "previous_qualifications", "employment", "usi",
        "additional_services", "survey", "document"
    ]
    
    completed_sections = app.form_metadata.get("completed_sections", []) if app.form_metadata else []
    next_step = None
    
    for step in next_steps:
        if step not in completed_sections:
            next_step = step
            break
    
    # Can submit if all steps completed
    can_submit = completion >= 100
    
    return StepUpdateResponse(
        success=True,
        message=message,
        step_number=step_number,
        step_name=step_name,
        completion_percentage=completion,
        next_step=next_step,
        can_submit=can_submit
    )


# ============================================================================
# STEP 1: PERSONAL DETAILS
# ============================================================================

@router.patch("/{application_id}/steps/1/personal-details", response_model=StepUpdateResponse)
async def update_personal_details(
    application_id: UUID,
    data: PersonalDetailsRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    **Step 1/12: Personal Details**
    
    Update student's personal information including contact details and identity documents.
    """
    app_service = ApplicationService(db)
    
    try:
        app = app_service.update_personal_details(
            application_id=application_id,
            data=data.model_dump(mode='json'),  # Use mode='json' to serialize dates/datetimes
            user_id=current_user.id,
            user_role=current_user.role
        )
        
        return _build_step_response(app, 1, "personal_details", "Personal details saved successfully")
    
    except (ApplicationNotFoundError, ApplicationPermissionError, ApplicationValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN if isinstance(e, ApplicationPermissionError) else status.HTTP_404_NOT_FOUND if isinstance(e, ApplicationNotFoundError) else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# STEP 2: EMERGENCY CONTACT
# ============================================================================

@router.patch("/{application_id}/steps/2/emergency-contact", response_model=StepUpdateResponse)
async def update_emergency_contact(
    application_id: UUID,
    data: EmergencyContactRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    **Step 2/12: Emergency Contact**
    
    Add emergency contact information (at least one required).
    """
    app_service = ApplicationService(db)
    
    try:
        contacts = [c.model_dump() for c in data.contacts]
        
        app = app_service.update_emergency_contact(
            application_id=application_id,
            contacts=contacts,
            user_id=current_user.id,
            user_role=current_user.role
        )
        
        return _build_step_response(app, 2, "emergency_contact", f"{len(contacts)} emergency contact(s) saved")
    
    except (ApplicationNotFoundError, ApplicationPermissionError, ApplicationValidationError) as e:
        if isinstance(e, ApplicationPermissionError):
            status_code = status.HTTP_403_FORBIDDEN
        elif isinstance(e, ApplicationNotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        else:  # ApplicationValidationError
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        
        raise HTTPException(status_code=status_code, detail=str(e))


# ============================================================================
# STEP 3: HEALTH COVER
# ============================================================================

@router.patch("/{application_id}/steps/3/health-cover", response_model=StepUpdateResponse)
async def update_health_cover(
    application_id: UUID,
    data: HealthCoverRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    **Step 3/12: Health Cover (OSHC)**
    
    Provide Overseas Student Health Cover details.
    """
    app_service = ApplicationService(db)
    
    try:
        # Convert dates to ISO format strings for JSON storage
        health_data = data.model_dump()
        health_data['start_date'] = health_data['start_date'].isoformat()
        health_data['end_date'] = health_data['end_date'].isoformat()
        
        app = app_service.update_health_cover(
            application_id=application_id,
            health_data=health_data,
            user_id=current_user.id,
            user_role=current_user.role
        )
        
        return _build_step_response(app, 3, "health_cover", "Health cover details saved")
    
    except (ApplicationNotFoundError, ApplicationPermissionError, ApplicationValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN if isinstance(e, ApplicationPermissionError) else status.HTTP_404_NOT_FOUND if isinstance(e, ApplicationNotFoundError) else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# STEP 4: LANGUAGE & CULTURAL
# ============================================================================

@router.patch("/{application_id}/steps/4/language-cultural", response_model=StepUpdateResponse)
async def update_language_cultural(
    application_id: UUID,
    data: LanguageCulturalRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    **Step 4/12: Language & Cultural Background**
    
    Provide language proficiency and cultural background information.
    """
    app_service = ApplicationService(db)
    
    try:
        language_data = data.model_dump()
        
        # Convert optional dates
        if language_data.get('visa_expiry'):
            language_data['visa_expiry'] = language_data['visa_expiry'].isoformat()
        if language_data.get('english_test_date'):
            language_data['english_test_date'] = language_data['english_test_date'].isoformat()
        
        app = app_service.update_language_cultural(
            application_id=application_id,
            language_data=language_data,
            user_id=current_user.id,
            user_role=current_user.role
        )
        
        return _build_step_response(app, 4, "language_cultural", "Language and cultural details saved")
    
    except (ApplicationNotFoundError, ApplicationPermissionError, ApplicationValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN if isinstance(e, ApplicationPermissionError) else status.HTTP_404_NOT_FOUND if isinstance(e, ApplicationNotFoundError) else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# STEP 5: DISABILITY SUPPORT
# ============================================================================

@router.patch("/{application_id}/steps/5/disability-support", response_model=StepUpdateResponse)
async def update_disability_support(
    application_id: UUID,
    data: DisabilitySupportRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    **Step 5/12: Disability Support**
    
    Provide information about any disability and required support.
    """
    app_service = ApplicationService(db)
    
    try:
        app = app_service.update_disability_support(
            application_id=application_id,
            disability_data=data.model_dump(),
            user_id=current_user.id,
            user_role=current_user.role
        )
        
        return _build_step_response(app, 5, "disability", "Disability support details saved")
    
    except (ApplicationNotFoundError, ApplicationPermissionError, ApplicationValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN if isinstance(e, ApplicationPermissionError) else status.HTTP_404_NOT_FOUND if isinstance(e, ApplicationNotFoundError) else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# STEP 6: SCHOOLING HISTORY
# ============================================================================

@router.patch("/{application_id}/steps/6/schooling-history", response_model=StepUpdateResponse)
async def update_schooling_history(
    application_id: UUID,
    data: SchoolingHistoryRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    **Step 6/12: Schooling History**
    
    Add educational background (at least one entry required).
    """
    app_service = ApplicationService(db)
    
    try:
        entries = [e.model_dump() for e in data.entries]
        
        app = app_service.update_schooling_history(
            application_id=application_id,
            schooling_entries=entries,
            user_id=current_user.id,
            user_role=current_user.role
        )
        
        return _build_step_response(app, 6, "schooling", f"{len(entries)} education entries saved")
    
    except (ApplicationNotFoundError, ApplicationPermissionError, ApplicationValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN if isinstance(e, ApplicationPermissionError) else status.HTTP_404_NOT_FOUND if isinstance(e, ApplicationNotFoundError) else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# STEP 7: PREVIOUS QUALIFICATIONS
# ============================================================================

@router.patch("/{application_id}/steps/7/qualifications", response_model=StepUpdateResponse)
async def update_qualifications(
    application_id: UUID,
    data: PreviousQualificationsRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    **Step 7/12: Previous Qualifications**
    
    Add professional qualifications and certifications (optional).
    """
    app_service = ApplicationService(db)
    
    try:
        entries = [q.model_dump() for q in data.qualifications]
        
        # Convert dates to strings
        for entry in entries:
            if entry.get('completion_date'):
                entry['completion_date'] = entry['completion_date'].isoformat()
        
        app = app_service.update_qualifications(
            application_id=application_id,
            qualification_entries=entries,
            user_id=current_user.id,
            user_role=current_user.role
        )
        
        return _build_step_response(app, 7, "previous_qualifications", f"{len(entries)} qualification(s) saved")
    
    except (ApplicationNotFoundError, ApplicationPermissionError, ApplicationValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN if isinstance(e, ApplicationPermissionError) else status.HTTP_404_NOT_FOUND if isinstance(e, ApplicationNotFoundError) else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# STEP 8: EMPLOYMENT HISTORY
# ============================================================================

@router.patch("/{application_id}/steps/8/employment-history", response_model=StepUpdateResponse)
async def update_employment_history(
    application_id: UUID,
    data: EmploymentHistoryRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    **Step 8/12: Employment History**
    
    Add work experience (optional).
    """
    app_service = ApplicationService(db)
    
    try:
        entries = [e.model_dump() for e in data.entries]
        
        # Convert dates to strings
        for entry in entries:
            if entry.get('start_date'):
                entry['start_date'] = entry['start_date'].isoformat()
            if entry.get('end_date'):
                entry['end_date'] = entry['end_date'].isoformat()
        
        app = app_service.update_employment_history(
            application_id=application_id,
            employment_entries=entries,
            user_id=current_user.id,
            user_role=current_user.role
        )
        
        return _build_step_response(app, 8, "employment", f"{len(entries)} employment entries saved")
    
    except (ApplicationNotFoundError, ApplicationPermissionError, ApplicationValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN if isinstance(e, ApplicationPermissionError) else status.HTTP_404_NOT_FOUND if isinstance(e, ApplicationNotFoundError) else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# STEP 9: USI
# ============================================================================

@router.patch("/{application_id}/steps/9/usi", response_model=StepUpdateResponse)
async def update_usi(
    application_id: UUID,
    data: USIRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    **Step 9/12: USI (Unique Student Identifier)**
    
    Provide USI details (required for enrollment).
    """
    app_service = ApplicationService(db)
    
    try:
        app = app_service.update_usi(
            application_id=application_id,
            usi=data.usi,
            consent=data.consent_to_verify,
            user_id=current_user.id,
            user_role=current_user.role
        )
        
        return _build_step_response(app, 9, "usi", "USI saved successfully")
    
    except (ApplicationNotFoundError, ApplicationPermissionError, ApplicationValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN if isinstance(e, ApplicationPermissionError) else status.HTTP_404_NOT_FOUND if isinstance(e, ApplicationNotFoundError) else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# STEP 10: ADDITIONAL SERVICES
# ============================================================================

@router.patch("/{application_id}/steps/10/additional-services", response_model=StepUpdateResponse)
async def update_additional_services(
    application_id: UUID,
    data: AdditionalServicesRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    **Step 10/12: Additional Services**
    
    Select optional services (accommodation, airport pickup, etc.).
    """
    app_service = ApplicationService(db)
    
    try:
        services = [s.model_dump() for s in data.services]
        
        app = app_service.update_additional_services(
            application_id=application_id,
            services=services,
            user_id=current_user.id,
            user_role=current_user.role
        )
        
        selected_count = sum(1 for s in services if s.get('selected', False))
        
        return _build_step_response(app, 10, "additional_services", f"{selected_count} service(s) selected")
    
    except (ApplicationNotFoundError, ApplicationPermissionError, ApplicationValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN if isinstance(e, ApplicationPermissionError) else status.HTTP_404_NOT_FOUND if isinstance(e, ApplicationNotFoundError) else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# STEP 11: SURVEY
# ============================================================================

@router.patch("/{application_id}/steps/11/survey", response_model=StepUpdateResponse)
async def update_survey(
    application_id: UUID,
    data: SurveyRequest,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    **Step 11/12: Survey**
    
    Complete pre-enrollment survey.
    """
    app_service = ApplicationService(db)
    
    try:
        survey_data = data.model_dump()
        
        app = app_service.update_survey(
            application_id=application_id,
            survey_data=survey_data,
            user_id=current_user.id,
            user_role=current_user.role
        )
        
        return _build_step_response(app, 11, "survey", "Survey responses saved")
    
    except (ApplicationNotFoundError, ApplicationPermissionError, ApplicationValidationError) as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN if isinstance(e, ApplicationPermissionError) else status.HTTP_404_NOT_FOUND if isinstance(e, ApplicationNotFoundError) else status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# STEP 12: DOCUMENT STATUS
# ============================================================================

@router.get("/{application_id}/steps/12/documents", response_model=DocumentStepResponse)
async def get_document_status(
    application_id: UUID,
    current_user: UserAccount = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    **Step 12/12: Document Upload Status**
    
    View status of required documents (actual upload handled separately).
    """
    from app.models import DocumentType, Document, ApplicationStage
    
    app_service = ApplicationService(db)
    
    try:
        # Get application
        app = app_service.get_application(
            application_id=application_id,
            user_id=current_user.id,
            user_role=current_user.role
        )
        
        # Get required document types for current stage
        stage_order = [
            ApplicationStage.DRAFT,
            ApplicationStage.SUBMITTED,
            ApplicationStage.STAFF_REVIEW,
            ApplicationStage.AWAITING_DOCUMENTS
        ]
        
        current_stage_index = stage_order.index(app.current_stage) if app.current_stage in stage_order else 0
        relevant_stages = stage_order[:current_stage_index + 1]
        
        document_types = db.query(DocumentType).filter(
            DocumentType.stage.in_(relevant_stages)
        ).order_by(DocumentType.display_order).all()
        
        # Get uploaded documents
        uploaded_docs = db.query(Document).filter(
            Document.application_id == application_id
        ).all()
        
        from app.schemas.application_steps import DocumentUploadInfo
        
        required_documents = []
        total_required = 0
        total_uploaded = 0
        
        for doc_type in document_types:
            uploaded_doc = next(
                (d for d in uploaded_docs if d.document_type_id == doc_type.id),
                None
            )
            
            is_uploaded = uploaded_doc is not None
            if is_uploaded:
                total_uploaded += 1
            
            if doc_type.is_mandatory:
                total_required += 1
            
            required_documents.append(DocumentUploadInfo(
                document_type_code=doc_type.code,
                document_type_name=doc_type.name,
                is_mandatory=doc_type.is_mandatory,
                uploaded=is_uploaded,
                uploaded_at=uploaded_doc.uploaded_at if uploaded_doc else None,
                status=uploaded_doc.status.value if uploaded_doc else None,
                ocr_status=uploaded_doc.ocr_status.value if uploaded_doc else None
            ))
        
        all_mandatory_uploaded = all(
            not doc.is_mandatory or doc.uploaded
            for doc in required_documents
        )
        
        return DocumentStepResponse(
            required_documents=required_documents,
            total_required=total_required,
            total_uploaded=total_uploaded,
            all_mandatory_uploaded=all_mandatory_uploaded
        )
    
    except (ApplicationNotFoundError, ApplicationPermissionError) as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN if isinstance(e, ApplicationPermissionError) else status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
