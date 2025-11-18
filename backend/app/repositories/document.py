"""
Document repository.
Handles document upload, retrieval, and status operations.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models import Document, DocumentStatus, DocumentVersion, OCRStatus
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Repository for document operations."""

    def __init__(self, db: Session):
        super().__init__(Document, db)

    def get_with_versions(self, document_id: UUID) -> Optional[Document]:
        """
        Get document with all versions loaded.

        Args:
            document_id: Document UUID

        Returns:
            Document with versions or None
        """
        return self.db.query(Document).filter(
            Document.id == document_id
        ).options(
            joinedload(Document.versions),
            joinedload(Document.document_type)
        ).first()

    def get_by_application(
        self,
        application_id: UUID,
        include_versions: bool = False
    ) -> List[Document]:
        """
        Get all documents for an application.

        Args:
            application_id: Application UUID
            include_versions: Whether to load versions

        Returns:
            List of documents
        """
        query = self.db.query(Document).filter(
            Document.application_id == application_id
        ).options(
            joinedload(Document.document_type)
        )

        if include_versions:
            query = query.options(joinedload(Document.versions))

        return query.order_by(Document.uploaded_at.desc()).all()

    def get_by_type_and_application(
        self,
        application_id: UUID,
        document_type_id: UUID
    ) -> Optional[Document]:
        """
        Get document by type for specific application.

        Args:
            application_id: Application UUID
            document_type_id: Document type UUID

        Returns:
            Document or None if not found
        """
        return self.db.query(Document).filter(
            Document.application_id == application_id,
            Document.document_type_id == document_type_id
        ).options(
            joinedload(Document.versions)
        ).first()

    def get_pending_verification(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Document]:
        """
        Get documents pending verification.

        Args:
            skip: Pagination offset
            limit: Max results

        Returns:
            List of pending documents
        """
        return self.db.query(Document).filter(
            Document.status == DocumentStatus.PENDING
        ).options(
            joinedload(Document.document_type),
            joinedload(Document.application)
        ).order_by(
            Document.uploaded_at.asc()
        ).offset(skip).limit(limit).all()

    def get_pending_ocr(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Document]:
        """
        Get documents with pending OCR processing.

        Args:
            skip: Pagination offset
            limit: Max results

        Returns:
            List of documents awaiting OCR
        """
        return self.db.query(Document).filter(
            Document.ocr_status == OCRStatus.PENDING
        ).order_by(
            Document.uploaded_at.asc()
        ).offset(skip).limit(limit).all()

    def update_status(
        self,
        document_id: UUID,
        status: DocumentStatus
    ) -> Optional[Document]:
        """
        Update document verification status.

        Args:
            document_id: Document UUID
            status: New status

        Returns:
            Updated document or None if not found
        """
        doc = self.get_by_id(document_id)
        if not doc:
            return None

        doc.status = status
        self.db.flush()
        self.db.refresh(doc)
        return doc

    def update_ocr_status(
        self,
        document_id: UUID,
        ocr_status: OCRStatus,
        ocr_completed: bool = False
    ) -> Optional[Document]:
        """
        Update OCR processing status.

        Args:
            document_id: Document UUID
            ocr_status: New OCR status
            ocr_completed: Whether OCR is complete

        Returns:
            Updated document or None if not found
        """
        doc = self.get_by_id(document_id)
        if not doc:
            return None

        doc.ocr_status = ocr_status
        if ocr_completed:
            doc.ocr_completed_at = datetime.utcnow()

        self.db.flush()
        self.db.refresh(doc)
        return doc

    def create_version(
        self,
        document_id: UUID,
        blob_url: str,
        checksum: str,
        file_size_bytes: int,
        ocr_json: Optional[dict] = None,
        preview_url: Optional[str] = None
    ) -> Optional[DocumentVersion]:
        """
        Create new document version.

        Args:
            document_id: Document UUID
            blob_url: Storage URL
            checksum: File checksum
            file_size_bytes: File size
            ocr_json: OCR results
            preview_url: Preview image URL

        Returns:
            Created version or None if document not found
        """
        doc = self.get_by_id(document_id)
        if not doc:
            return None

        # Get next version number
        existing_versions = self.db.query(DocumentVersion).filter(
            DocumentVersion.document_id == document_id
        ).count()

        version = DocumentVersion(
            document_id=document_id,
            blob_url=blob_url,
            checksum=checksum,
            file_size_bytes=file_size_bytes,
            version_number=existing_versions + 1,
            ocr_json=ocr_json,
            preview_url=preview_url,
            created_at=datetime.utcnow()
        )

        self.db.add(version)
        self.db.flush()
        self.db.refresh(version)
        return version

    def get_latest_version(
            self,
            document_id: UUID) -> Optional[DocumentVersion]:
        """
        Get latest version of a document.

        Args:
            document_id: Document UUID

        Returns:
            Latest version or None
        """
        return self.db.query(DocumentVersion).filter(
            DocumentVersion.document_id == document_id
        ).order_by(
            DocumentVersion.version_number.desc()
        ).first()

    def count_by_status(self, status: DocumentStatus) -> int:
        """
        Count documents by verification status.

        Args:
            status: Document status

        Returns:
            Count of documents
        """
        return self.db.query(Document).filter(
            Document.status == status
        ).count()

    def count_by_ocr_status(self, ocr_status: OCRStatus) -> int:
        """
        Count documents by OCR status.

        Args:
            ocr_status: OCR status

        Returns:
            Count of documents
        """
        return self.db.query(Document).filter(
            Document.ocr_status == ocr_status
        ).count()
