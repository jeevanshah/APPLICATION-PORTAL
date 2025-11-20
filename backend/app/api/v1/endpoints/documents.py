"""
Document upload and management endpoints.
Handles file uploads, OCR processing, and document retrieval.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models import UserAccount, UserRole
from app.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentStatsResponse,
    DocumentUploadResponse,
    DocumentVerifyRequest,
    OCRAutoFillResponse,
    OCRResultResponse,
)
from app.services.document import (
    DocumentNotFoundError,
    DocumentPermissionError,
    DocumentService,
    DocumentValidationError,
    FileUploadError,
)

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse,
             status_code=status.HTTP_201_CREATED)
async def upload_document(
    application_id: UUID = Form(...),
    document_type_id: UUID = Form(...),
    file: UploadFile = File(...),
    process_ocr: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user)
):
    """
    Upload a document for an application.

    - **application_id**: UUID of the application
    - **document_type_id**: UUID of the document type
    - **file**: Document file (PDF, JPG, PNG, etc.)
    - **process_ocr**: Whether to process OCR (default: true)

    **Permissions:**
    - Agent: Can upload to their own applications
    - Staff: Can upload to assigned applications
    - Admin: Can upload to any application

    **File Requirements:**
    - Allowed types: PDF, JPG, JPEG, PNG, TIFF, BMP, GIF
    - Maximum size: 20MB

    **OCR Processing:**
    - If enabled, extracts text and structured data
    - Results available via GET /documents/{id}/ocr
    - Auto-fill suggestions via GET /applications/{id}/documents/autofill
    """
    # Only agents, staff, and admins can upload documents
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students cannot upload documents. Please contact your agent."
        )

    service = DocumentService(db)

    try:
        # Read file content
        file_content = await file.read()

        # Create BytesIO object for service
        from io import BytesIO
        file_obj = BytesIO(file_content)

        document = await service.upload_document(
            application_id=application_id,
            document_type_id=document_type_id,
            file=file_obj,
            filename=file.filename or "unnamed",
            user_id=current_user.id,
            user_role=current_user.role,
            process_ocr=process_ocr
        )

        # Build response
        return {
            "document": document,
            "message": "Document uploaded successfully",
            "ocr_queued": process_ocr and document.ocr_status.value == "PENDING"}

    except DocumentPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except DocumentValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except FileUploadError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )


@router.get("/types", response_model=List[dict])
async def get_document_types(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all available document types.
    
    Returns list of document types with their properties:
    - id, code, name, stage
    - is_mandatory: Whether document is required
    - accepts_ocr: Whether OCR processing is available
    """
    from app.models import DocumentType
    
    doc_types = db.query(DocumentType).order_by(DocumentType.display_order).all()
    
    return [
        {
            "id": str(dt.id),
            "code": dt.code,
            "name": dt.name,
            "stage": dt.stage.value if hasattr(dt.stage, 'value') else dt.stage,
            "is_mandatory": dt.is_mandatory,
            "accepts_ocr": dt.ocr_model_ref is not None,
            "display_order": dt.display_order
        }
        for dt in doc_types
    ]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    include_versions: bool = False,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user)
):
    """
    Get document by ID.

    - **document_id**: Document UUID
    - **include_versions**: Include all document versions (default: false)

    **Permissions:**
    - User must have access to the application
    """
    service = DocumentService(db)

    try:
        document = service.get_document(
            document_id=document_id,
            user_id=current_user.id,
            user_role=current_user.role,
            include_versions=include_versions
        )

        return document

    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    except DocumentPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.get("/{document_id}/ocr", response_model=OCRResultResponse)
async def get_ocr_results(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user)
):
    """
    Get OCR extraction results for a document.

    Returns extracted text, structured data, and confidence scores.
    """
    service = DocumentService(db)

    try:
        document = service.get_document(
            document_id=document_id,
            user_id=current_user.id,
            user_role=current_user.role,
            include_versions=True
        )

        if document.ocr_status.value != "COMPLETED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OCR not completed. Status: {
                    document.ocr_status.value}")

        # Get latest version with OCR data
        latest_version = service.doc_repo.get_latest_version(document_id)

        if not latest_version or not latest_version.ocr_json:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OCR results not found"
            )

        ocr_data = latest_version.ocr_json

        return {
            "document_id": document_id,
            "ocr_status": document.ocr_status,
            "extracted_data": ocr_data.get("extracted_data"),
            "confidence_scores": ocr_data.get("confidence_scores"),
            "suggested_mappings": None,  # TODO: Implement field mappings
            "raw_text": ocr_data.get("raw_text"),
            "processing_time_ms": ocr_data.get("processing_time_ms")
        }

    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    except DocumentPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a document (soft delete).

    Only the uploader or admin can delete documents.
    """
    service = DocumentService(db)

    try:
        service.delete_document(
            document_id=document_id,
            user_id=current_user.id,
            user_role=current_user.role
        )

        return None

    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    except DocumentPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.post("/{document_id}/verify", response_model=DocumentResponse)
async def verify_document(
    document_id: UUID,
    data: DocumentVerifyRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Verify or reject a document (staff/admin only).

    Updates document status to APPROVED or REJECTED.
    """
    service = DocumentService(db)

    try:
        document = service.verify_document(
            document_id=document_id,
            status=data.status,
            user_id=current_user.id,
            user_role=current_user.role,
            notes=data.notes
        )

        return document

    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    except DocumentPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


# Application-scoped document endpoints

@router.get("/application/{application_id}/list",
            response_model=List[DocumentListResponse])
async def list_application_documents(
    application_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List all documents for an application.

    Returns lightweight list of documents with basic info.
    """
    service = DocumentService(db)

    try:
        documents = service.get_application_documents(
            application_id=application_id,
            user_id=current_user.id,
            user_role=current_user.role
        )

        # Convert to list response format
        result = []
        for doc in documents:
            latest_version = service.doc_repo.get_latest_version(doc.id)

            result.append({
                "id": doc.id,
                "application_id": doc.application_id,
                "document_type_id": doc.document_type_id,
                "document_type_name": doc.document_type.name,
                "document_type_code": doc.document_type.code,
                "status": doc.status,
                "ocr_status": doc.ocr_status,
                "uploaded_at": doc.uploaded_at,
                "uploaded_by": doc.uploaded_by,
                "uploader_email": doc.uploader.email if doc.uploader else None,
                "file_size_bytes": latest_version.file_size_bytes if latest_version else None,
                "latest_version_id": latest_version.id if latest_version else None
            })

        return result

    except DocumentPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/application/{application_id}/autofill",
           response_model=OCRAutoFillResponse)
async def get_autofill_suggestions(
    application_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user)
):
    """
    Get OCR auto-fill suggestions for application form.

    Analyzes all uploaded documents with OCR results and suggests
    field values that can be auto-filled into the application form.

    **Confidence Levels:**
    - High (>0.8): Highly confident, safe to auto-fill
    - Medium (0.5-0.8): Moderately confident, suggest to user
    - Low (<0.5): Low confidence, show but don't auto-fill
    """
    service = DocumentService(db)

    try:
        suggestions = service.get_ocr_autofill_suggestions(
            application_id=application_id,
            user_id=current_user.id,
            user_role=current_user.role
        )

        return suggestions

    except DocumentPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/application/{application_id}/stats",
           response_model=DocumentStatsResponse)
async def get_document_stats(
    application_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user)
):
    """
    Get document statistics for an application.

    Returns counts by status, OCR status, and missing mandatory documents.
    """
    service = DocumentService(db)

    try:
        documents = service.get_application_documents(
            application_id=application_id,
            user_id=current_user.id,
            user_role=current_user.role
        )

        # Calculate statistics
        total = len(documents)

        by_status = {}
        for doc in documents:
            status_name = doc.status.value
            by_status[status_name] = by_status.get(status_name, 0) + 1

        by_ocr_status = {}
        for doc in documents:
            ocr_status_name = doc.ocr_status.value
            by_ocr_status[ocr_status_name] = by_ocr_status.get(
                ocr_status_name, 0) + 1

        # Get mandatory document types
        from app.models import DocumentType
        application = service.app_repo.get_by_id(application_id)

        mandatory_types = db.query(DocumentType).filter(
            DocumentType.is_mandatory,
            DocumentType.stage == application.current_stage
        ).all()

        uploaded_type_ids = {doc.document_type_id for doc in documents}
        missing_mandatory = [
            doc_type.name
            for doc_type in mandatory_types
            if doc_type.id not in uploaded_type_ids
        ]

        # Calculate completion percentage
        if mandatory_types:
            completion_percentage = int(
                (len(mandatory_types) -
                 len(missing_mandatory)) /
                len(mandatory_types) *
                100)
        else:
            completion_percentage = 100

        return {
            "total_documents": total,
            "by_status": by_status,
            "by_ocr_status": by_ocr_status,
            "missing_mandatory": missing_mandatory,
            "completion_percentage": completion_percentage
        }

    except DocumentPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{document_id}/reprocess-ocr", response_model=DocumentResponse)
async def reprocess_ocr(
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_user)
):
    """
    Re-process OCR for an existing document.
    
    Useful for testing new OCR models or re-extracting data.
    Only admins and staff can trigger reprocessing.
    """
    # Only staff and admins can reprocess
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff and admins can reprocess OCR"
        )
    
    service = DocumentService(db)
    
    try:
        # Get document with permission check
        document = service.get_document(
            document_id=document_id,
            user_id=current_user.id,
            user_role=current_user.role,
            include_versions=True
        )
        
        # Re-process OCR
        await service.reprocess_ocr(document_id)
        
        # Refresh and return
        db.refresh(document)
        return document
        
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    except DocumentPermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR reprocessing failed: {str(e)}"
        )
