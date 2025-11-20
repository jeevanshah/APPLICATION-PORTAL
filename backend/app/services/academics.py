"""
Academic Records Service

Extracts and transforms academic data from OCR-processed documents
into structured application step data (schooling history, qualifications).
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.repositories.application import ApplicationRepository
from app.repositories.document import DocumentRepository


class AcademicService:
    """Service for extracting academic data from documents and auto-filling application steps."""

    def __init__(self, db: Session):
        self.db = db
        self.app_repo = ApplicationRepository(db)
        self.doc_repo = DocumentRepository(db)

    def extract_schooling_from_transcript(
        self,
        document_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Extract schooling history entry from a Grade 10/12 transcript document.
        
        Converts OCR extracted data into Step 6 (schooling history) format.
        
        Args:
            document_id: UUID of the transcript document
            
        Returns:
            Schooling history entry dict or None if no valid data
            {
                "institution": "Kathmandu Secondary School",
                "country": "Nepal",
                "qualification_level": "Grade 10 (SEE)",
                "start_year": 2017,
                "end_year": 2019,
                "currently_attending": false,
                "result": "3.8 GPA",
                "field_of_study": "General Secondary"
            }
        """
        document = self.doc_repo.get_by_id(document_id)
        if not document or document.ocr_status != "COMPLETED":
            return None

        # Get latest version with OCR data
        latest_version = document.latest_version
        if not latest_version or not latest_version.ocr_json:
            return None

        ocr_data = latest_version.ocr_json.get("extracted_data", {})
        if not ocr_data:
            return None

        # Determine qualification level from document type
        doc_type_code = document.document_type.code
        qualification_level = None
        if doc_type_code == "TRANSCRIPT_10":
            qualification_level = "Grade 10"
        elif doc_type_code == "TRANSCRIPT_12":
            qualification_level = "Grade 12"
        else:
            # Not a transcript document
            return None

        # Extract institution name
        institution = ocr_data.get("institution_name") or ocr_data.get("institution")
        if not institution:
            return None

        # Extract completion year
        end_year = None
        year_completed = ocr_data.get("year_completed")
        if year_completed:
            try:
                end_year = int(year_completed)
            except (ValueError, TypeError):
                pass

        # Calculate start year (typically 1-2 years before end for Grade 10/12)
        start_year = None
        if end_year and doc_type_code == "TRANSCRIPT_12":
            # Only calculate start year for Grade 12 (typically 2-year program)
            start_year = end_year - 2
        # For Grade 10, leave start_year as None unless explicitly provided in OCR data
        elif end_year and doc_type_code == "TRANSCRIPT_10":
            # Check if OCR extracted a start year
            ocr_start = ocr_data.get("start_year")
            if ocr_start:
                try:
                    start_year = int(ocr_start)
                except (ValueError, TypeError):
                    pass

        # Extract grades/result - check multiple possible field names
        result = None
        result_value = (
            ocr_data.get("result") or 
            ocr_data.get("gpa") or 
            ocr_data.get("grade_gpa") or 
            ocr_data.get("grades")
        )
        if result_value:
            result = str(result_value)
            # Format GPA if it's just a number
            if result_value and not any(word in result.upper() for word in ["GPA", "GRADE", "%"]):
                try:
                    float(result_value)
                    result = f"{result_value} GPA"
                except (ValueError, TypeError):
                    pass

        # Extract country (OCR should detect Nepal for NEB transcripts)
        country = ocr_data.get("country", "Nepal")

        entry = {
            "institution": institution,
            "country": country,
            "qualification_level": qualification_level,
            "start_year": start_year,
            "end_year": end_year,
            "currently_attending": False,  # Always false for completed transcripts
            "result": result,
            "field_of_study": "General Secondary Education",  # Default for Grade 10/12
        }

        return entry

    def auto_populate_step6(
        self,
        application_id: UUID
    ) -> Dict[str, Any]:
        """
        Auto-populate Step 6 (schooling history) from uploaded transcript documents.
        
        Finds all Grade 10/12 transcript documents for the application,
        extracts academic data, and returns formatted entries.
        
        Args:
            application_id: UUID of the application
            
        Returns:
            {
                "entries": [
                    {schooling_history_entry},
                    {schooling_history_entry}
                ],
                "source": "ocr_auto_fill",
                "documents_processed": [document_ids]
            }
        """
        application = self.app_repo.get_by_id(application_id)
        if not application:
            raise ValueError(f"Application {application_id} not found")

        entries = []
        documents_processed = []

        # Find all transcript documents
        for document in application.documents:
            doc_type_code = document.document_type.code
            
            # Only process Grade 10 and Grade 12 transcripts
            if doc_type_code not in ["TRANSCRIPT_10", "TRANSCRIPT_12"]:
                continue

            # Extract schooling entry from this document
            entry = self.extract_schooling_from_transcript(document.id)
            if entry:
                entries.append(entry)
                documents_processed.append(str(document.id))

        return {
            "entries": entries,
            "source": "ocr_auto_fill",
            "documents_processed": documents_processed,
            "count": len(entries),
        }

    def extract_qualifications(
        self,
        application_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        Extract qualifications for Step 7 from transcript documents.
        
        Similar to step 6 but focuses on completed qualifications
        (degrees, diplomas, certificates).
        
        Args:
            application_id: UUID of the application
            
        Returns:
            List of qualification entries
        """
        application = self.app_repo.get_by_id(application_id)
        if not application:
            raise ValueError(f"Application {application_id} not found")

        qualifications = []

        for document in application.documents:
            if document.ocr_status != "COMPLETED" or not document.latest_version:
                continue

            ocr_data = document.latest_version.ocr_json.get("extracted_data", {})
            doc_type_code = document.document_type.code

            # Map document types to qualification entries
            if doc_type_code == "TRANSCRIPT_10":
                qualifications.append({
                    "qualification_name": "Secondary Education Examination (SEE) / SLC",
                    "institution": ocr_data.get("institution_name"),
                    "completion_date": ocr_data.get("year_completed"),
                    "certificate_number": None,
                    "grade": ocr_data.get("grades"),
                })
            elif doc_type_code == "TRANSCRIPT_12":
                qualifications.append({
                    "qualification_name": "Higher Secondary Certificate (+2)",
                    "institution": ocr_data.get("institution_name"),
                    "completion_date": ocr_data.get("year_completed"),
                    "certificate_number": None,
                    "grade": ocr_data.get("grades"),
                })

        return qualifications
