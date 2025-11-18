"""
Document service for file upload, storage, and OCR processing.
"""
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    Application,
    Document,
    DocumentStatus,
    DocumentType,
    DocumentVersion,
    OCRStatus,
    UserRole,
)
from app.repositories.application import ApplicationRepository
from app.repositories.document import DocumentRepository
from app.services.ocr import OCRError, ocr_service


class DocumentError(Exception):
    """Base exception for document-related errors."""
    pass


class DocumentNotFoundError(DocumentError):
    """Raised when document is not found."""
    pass


class DocumentPermissionError(DocumentError):
    """Raised when user lacks permission for document operation."""
    pass


class DocumentValidationError(DocumentError):
    """Raised when document validation fails."""
    pass


class FileUploadError(DocumentError):
    """Raised when file upload fails."""
    pass


class DocumentService:
    """Service for document upload and management."""

    # Allowed file types
    ALLOWED_EXTENSIONS = {
        '.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif'
    }

    # Max file size (20MB)
    MAX_FILE_SIZE = 20 * 1024 * 1024

    def __init__(self, db: Session):
        """Initialize document service."""
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.app_repo = ApplicationRepository(db)
        self.upload_dir = Path(getattr(settings, 'UPLOAD_DIR', '/app/uploads'))
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def upload_document(
        self,
        application_id: UUID,
        document_type_id: UUID,
        file: BinaryIO,
        filename: str,
        user_id: UUID,
        user_role: UserRole,
        process_ocr: bool = True
    ) -> Document:
        """
        Upload document file and create record.

        Args:
            application_id: Application UUID
            document_type_id: Document type UUID
            file: File object (binary)
            filename: Original filename
            user_id: Uploading user UUID
            user_role: User's role
            process_ocr: Whether to queue OCR processing

        Returns:
            Created document

        Raises:
            DocumentPermissionError: If user lacks permission
            DocumentValidationError: If validation fails
            FileUploadError: If file upload fails
        """
        # Validate user can upload to this application
        application = self.app_repo.get_by_id(application_id)
        if not application:
            raise DocumentValidationError("Application not found")

        if not self._can_upload(application, user_id, user_role):
            raise DocumentPermissionError(
                "You do not have permission to upload documents to this application"
            )

        # Validate file
        self._validate_file(file, filename)

        # Get document type
        doc_type = self.db.query(DocumentType).filter(
            DocumentType.id == document_type_id
        ).first()

        if not doc_type:
            raise DocumentValidationError("Document type not found")

        # Check if document already exists for this type
        existing_doc = self.doc_repo.get_by_type_and_application(
            application_id,
            document_type_id
        )

        # Save file
        file_path, checksum, file_size = await self._save_file(
            file,
            filename,
            application_id
        )

        if existing_doc:
            # Create new version
            version = self.doc_repo.create_version(
                document_id=existing_doc.id,
                blob_url=file_path,
                checksum=checksum,
                file_size_bytes=file_size
            )

            # Update OCR status to pending if requested
            if process_ocr:
                existing_doc.ocr_status = OCRStatus.PENDING
                self.db.flush()

            document = existing_doc
        else:
            # Create new document
            document = Document(
                application_id=application_id,
                document_type_id=document_type_id,
                status=DocumentStatus.PENDING,
                uploaded_by=user_id,
                uploaded_at=datetime.utcnow(),
                ocr_status=OCRStatus.PENDING if process_ocr else OCRStatus.NOT_REQUIRED)
            self.db.add(document)
            self.db.flush()
            self.db.refresh(document)

            # Create first version
            version = self.doc_repo.create_version(
                document_id=document.id,
                blob_url=file_path,
                checksum=checksum,
                file_size_bytes=file_size
            )

        self.db.commit()
        self.db.refresh(document)

        # Queue OCR processing if requested
        if process_ocr and doc_type.ocr_model_ref:
            try:
                await self._process_ocr(document, version, doc_type)
            except OCRError as e:
                # Log error but don't fail upload
                print(f"OCR processing failed: {e}")
                document.ocr_status = OCRStatus.FAILED
                self.db.commit()

        return document

    async def _save_file(
        self,
        file: BinaryIO,
        filename: str,
        application_id: UUID
    ) -> tuple[str, str, int]:
        """
        Save uploaded file to disk.

        Args:
            file: File object
            filename: Original filename
            application_id: Application UUID

        Returns:
            Tuple of (file_path, checksum, file_size)
        """
        # Create application directory
        app_dir = self.upload_dir / str(application_id)
        app_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        safe_filename = self._sanitize_filename(filename)
        unique_filename = f"{timestamp}_{safe_filename}"
        file_path = app_dir / unique_filename

        # Read file content
        file_content = file.read()
        file_size = len(file_content)

        # Calculate checksum
        checksum = hashlib.sha256(file_content).hexdigest()

        # Write file
        try:
            with open(file_path, 'wb') as f:
                f.write(file_content)
        except Exception as e:
            raise FileUploadError(f"Failed to save file: {str(e)}")

        # Return relative path from upload directory
        relative_path = str(file_path.relative_to(self.upload_dir))

        return relative_path, checksum, file_size

    async def _process_ocr(
        self,
        document: Document,
        version: DocumentVersion,
        doc_type: DocumentType
    ):
        """
        Process OCR on uploaded document.

        Args:
            document: Document record
            version: Document version
            doc_type: Document type
        """
        # Update status to processing
        document.ocr_status = OCRStatus.PROCESSING
        self.db.commit()

        try:
            # Get full file path
            full_path = self.upload_dir / version.blob_url

            # Extract text and data
            ocr_result = await ocr_service.extract_text_from_file(
                str(full_path),
                doc_type.code
            )

            # Update version with OCR results
            version.ocr_json = ocr_result

            # Update document
            document.ocr_status = OCRStatus.COMPLETED
            document.ocr_completed_at = datetime.utcnow()

            self.db.commit()

        except OCRError:
            document.ocr_status = OCRStatus.FAILED
            self.db.commit()
            raise

    def get_document(
        self,
        document_id: UUID,
        user_id: UUID,
        user_role: UserRole,
        include_versions: bool = False
    ) -> Document:
        """
        Get document by ID with permission check.

        Args:
            document_id: Document UUID
            user_id: Requesting user UUID
            user_role: User's role
            include_versions: Whether to include versions

        Returns:
            Document

        Raises:
            DocumentNotFoundError: If not found
            DocumentPermissionError: If no permission
        """
        if include_versions:
            document = self.doc_repo.get_with_versions(document_id)
        else:
            document = self.doc_repo.get_by_id(document_id)

        if not document:
            raise DocumentNotFoundError("Document not found")

        # Check permission
        if not self._can_view(document, user_id, user_role):
            raise DocumentPermissionError(
                "You do not have permission to view this document")

        return document

    def get_application_documents(
        self,
        application_id: UUID,
        user_id: UUID,
        user_role: UserRole
    ) -> List[Document]:
        """
        Get all documents for an application.

        Args:
            application_id: Application UUID
            user_id: Requesting user UUID
            user_role: User's role

        Returns:
            List of documents
        """
        application = self.app_repo.get_by_id(application_id)
        if not application:
            raise DocumentValidationError("Application not found")

        if not self._can_view_application(application, user_id, user_role):
            raise DocumentPermissionError(
                "You do not have permission to view documents for this application"
            )

        return self.doc_repo.get_by_application(
            application_id, include_versions=False)

    def get_ocr_autofill_suggestions(
        self,
        application_id: UUID,
        user_id: UUID,
        user_role: UserRole
    ) -> Dict[str, Any]:
        """
        Get OCR auto-fill suggestions for application form.

        Args:
            application_id: Application UUID
            user_id: User UUID
            user_role: User role

        Returns:
            Dictionary with suggestions
        """
        documents = self.get_application_documents(
            application_id, user_id, user_role)

        suggestions = []

        for doc in documents:
            if doc.ocr_status != OCRStatus.COMPLETED:
                continue

            # Get latest version with OCR data
            version = self.doc_repo.get_latest_version(doc.id)
            if not version or not version.ocr_json:
                continue

            # Extract data
            extracted_data = version.ocr_json.get('extracted_data', {})
            confidence_scores = version.ocr_json.get('confidence_scores', {})

            # Map to application fields
            field_mappings = ocr_service.map_to_application_fields(
                extracted_data,
                doc.document_type.code
            )

            # Create suggestions
            for field_path, value in field_mappings.items():
                field_name = field_path.split('.')[-1]
                confidence = confidence_scores.get(
                    field_name, confidence_scores.get('overall', 0.0))

                suggestions.append({
                    "field_name": field_name,
                    "field_path": field_path,
                    "extracted_value": value,
                    "confidence": confidence,
                    "source_document_id": str(doc.id),
                    "source_text": None  # Could extract snippet
                })

        # Categorize by confidence
        high_conf = [s for s in suggestions if s['confidence'] > 0.8]
        medium_conf = [s for s in suggestions if 0.5 < s['confidence'] <= 0.8]
        low_conf = [s for s in suggestions if s['confidence'] <= 0.5]

        return {
            "application_id": str(application_id),
            "suggestions": suggestions,
            "total_suggestions": len(suggestions),
            "high_confidence_count": len(high_conf),
            "medium_confidence_count": len(medium_conf),
            "low_confidence_count": len(low_conf)
        }

    def verify_document(
        self,
        document_id: UUID,
        status: DocumentStatus,
        user_id: UUID,
        user_role: UserRole,
        notes: Optional[str] = None
    ) -> Document:
        """
        Verify/reject document (staff only).

        Args:
            document_id: Document UUID
            status: New status
            user_id: User UUID
            user_role: User role
            notes: Optional notes

        Returns:
            Updated document
        """
        if user_role not in [UserRole.STAFF, UserRole.ADMIN]:
            raise DocumentPermissionError("Only staff can verify documents")

        document = self.doc_repo.get_by_id(document_id)
        if not document:
            raise DocumentNotFoundError("Document not found")

        document = self.doc_repo.update_status(document_id, status)

        # Could add notes to a notes field or timeline entry here

        self.db.commit()
        return document

    def delete_document(
        self,
        document_id: UUID,
        user_id: UUID,
        user_role: UserRole
    ):
        """
        Delete document (soft delete - mark as deleted).

        Args:
            document_id: Document UUID
            user_id: User UUID
            user_role: User role
        """
        document = self.doc_repo.get_by_id(document_id)
        if not document:
            raise DocumentNotFoundError("Document not found")

        if not self._can_delete(document, user_id, user_role):
            raise DocumentPermissionError(
                "You do not have permission to delete this document")

        # Soft delete
        document.status = DocumentStatus.DELETED
        self.db.commit()

    def _can_upload(
        self,
        application: Application,
        user_id: UUID,
        user_role: UserRole
    ) -> bool:
        """Check if user can upload documents to application."""
        if user_role == UserRole.ADMIN:
            return True

        if user_role == UserRole.STAFF:
            # Staff can upload if assigned
            return application.assigned_staff_id == user_id

        if user_role == UserRole.AGENT:
            # Agent can upload if they own the application
            from app.repositories.agent import AgentRepository
            agent_repo = AgentRepository(self.db)
            agent = agent_repo.get_by_user_id(user_id)
            return agent and application.agent_profile_id == agent.id

        if user_role == UserRole.STUDENT:
            # Student can upload to their own application
            from app.repositories.student import StudentRepository
            student_repo = StudentRepository(self.db)
            student = student_repo.get_by_user_id(user_id)
            return student and application.student_profile_id == student.id

        return False

    def _can_view(
        self,
        document: Document,
        user_id: UUID,
        user_role: UserRole
    ) -> bool:
        """Check if user can view document."""
        application = document.application
        return self._can_view_application(application, user_id, user_role)

    def _can_view_application(
        self,
        application: Application,
        user_id: UUID,
        user_role: UserRole
    ) -> bool:
        """Check if user can view application documents."""
        if user_role in [UserRole.ADMIN, UserRole.STAFF]:
            return True

        if user_role == UserRole.AGENT:
            from app.repositories.agent import AgentRepository
            agent_repo = AgentRepository(self.db)
            agent = agent_repo.get_by_user_id(user_id)
            return agent and application.agent_profile_id == agent.id

        if user_role == UserRole.STUDENT:
            from app.repositories.student import StudentRepository
            student_repo = StudentRepository(self.db)
            student = student_repo.get_by_user_id(user_id)
            return student and application.student_profile_id == student.id

        return False

    def _can_delete(
        self,
        document: Document,
        user_id: UUID,
        user_role: UserRole
    ) -> bool:
        """Check if user can delete document."""
        if user_role == UserRole.ADMIN:
            return True

        # Only uploader or admin can delete (within time window)
        if document.uploaded_by == user_id:
            # Could add time restriction here (e.g., within 1 hour)
            return True

        return False

    def _validate_file(self, file: BinaryIO, filename: str):
        """Validate uploaded file."""
        # Check extension
        ext = Path(filename).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise DocumentValidationError(
                f"File type not allowed. Allowed types: {
                    ', '.join(
                        self.ALLOWED_EXTENSIONS)}")

        # Check file size
        file.seek(0, 2)  # Seek to end
        size = file.tell()
        file.seek(0)  # Reset

        if size > self.MAX_FILE_SIZE:
            max_mb = self.MAX_FILE_SIZE / (1024 * 1024)
            raise DocumentValidationError(
                f"File too large. Maximum size: {max_mb}MB"
            )

        if size == 0:
            raise DocumentValidationError("File is empty")

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent directory traversal."""
        # Remove path components
        filename = os.path.basename(filename)

        # Remove dangerous characters
        safe_chars = set(
            'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-')
        filename = ''.join(c if c in safe_chars else '_' for c in filename)

        # Limit length
        name, ext = os.path.splitext(filename)
        if len(name) > 100:
            name = name[:100]

        return name + ext
