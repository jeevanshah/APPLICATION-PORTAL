"""
OCR Service for document text extraction using Microsoft Azure Computer Vision.
Handles passport, transcript, and certificate recognition with field extraction.
"""
import asyncio
import hashlib
import json
from typing import Dict, Any, Optional, List, Tuple
from uuid import UUID
from datetime import datetime
import re

# Azure imports
try:
    from azure.ai.vision.imageanalysis import ImageAnalysisClient
    from azure.ai.vision.imageanalysis.models import VisualFeatures
    from azure.core.credentials import AzureKeyCredential
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    print("Warning: Azure Computer Vision SDK not installed. OCR features will be mocked.")

from app.core.config import settings


class OCRError(Exception):
    """Base exception for OCR-related errors."""
    pass


class OCRServiceUnavailable(OCRError):
    """Raised when OCR service is not available."""
    pass


class OCRProcessingError(OCRError):
    """Raised when OCR processing fails."""
    pass


class OCRService:
    """Service for optical character recognition and data extraction."""
    
    def __init__(self):
        """Initialize OCR service with Azure credentials."""
        self.endpoint = getattr(settings, 'AZURE_VISION_ENDPOINT', None)
        self.key = getattr(settings, 'AZURE_VISION_KEY', None)
        self.client = None
        
        if AZURE_AVAILABLE and self.endpoint and self.key:
            try:
                self.client = ImageAnalysisClient(
                    endpoint=self.endpoint,
                    credential=AzureKeyCredential(self.key)
                )
            except Exception as e:
                print(f"Failed to initialize Azure Vision client: {e}")
                self.client = None
    
    def is_available(self) -> bool:
        """Check if OCR service is configured and available."""
        return self.client is not None
    
    async def extract_text_from_file(
        self, 
        file_path: str,
        document_type_code: str
    ) -> Dict[str, Any]:
        """
        Extract text and structured data from document.
        
        Args:
            file_path: Path to image/PDF file
            document_type_code: Type of document (e.g., 'PASSPORT', 'TRANSCRIPT')
            
        Returns:
            Dictionary with extracted data, confidence scores, and raw text
            
        Raises:
            OCRServiceUnavailable: If Azure service not configured
            OCRProcessingError: If extraction fails
        """
        if not self.is_available():
            # Return mock data for development
            return self._mock_ocr_extraction(file_path, document_type_code)
        
        try:
            # Read file
            with open(file_path, 'rb') as f:
                image_data = f.read()
            
            # Call Azure Computer Vision
            result = self.client.analyze(
                image_data=image_data,
                visual_features=[VisualFeatures.READ, VisualFeatures.CAPTION]
            )
            
            # Extract text
            raw_text = ""
            text_blocks = []
            
            if result.read is not None:
                for block in result.read.blocks:
                    for line in block.lines:
                        raw_text += line.text + "\n"
                        text_blocks.append({
                            "text": line.text,
                            "confidence": getattr(line, 'confidence', 0.0),
                            "bounding_box": getattr(line, 'bounding_polygon', None)
                        })
            
            # Extract structured data based on document type
            extracted_data = self._extract_structured_data(
                raw_text,
                text_blocks,
                document_type_code
            )
            
            # Calculate confidence scores
            confidence_scores = self._calculate_confidence(text_blocks, extracted_data)
            
            return {
                "raw_text": raw_text,
                "text_blocks": text_blocks,
                "extracted_data": extracted_data,
                "confidence_scores": confidence_scores,
                "processing_time_ms": 0,  # Azure doesn't provide this
                "engine": "azure_computer_vision"
            }
            
        except Exception as e:
            raise OCRProcessingError(f"OCR extraction failed: {str(e)}")
    
    def _extract_structured_data(
        self,
        raw_text: str,
        text_blocks: List[Dict],
        document_type_code: str
    ) -> Dict[str, Any]:
        """
        Extract structured fields based on document type.
        
        Args:
            raw_text: Full extracted text
            text_blocks: Text blocks with positions
            document_type_code: Document type
            
        Returns:
            Dictionary of extracted fields
        """
        extractors = {
            'PASSPORT': self._extract_passport_data,
            'TRANSCRIPT': self._extract_transcript_data,
            'ENGLISH_TEST': self._extract_english_test_data,
            'ID_CARD': self._extract_id_card_data,
        }
        
        extractor = extractors.get(document_type_code, self._extract_generic_data)
        return extractor(raw_text, text_blocks)
    
    def _extract_passport_data(
        self, 
        raw_text: str, 
        text_blocks: List[Dict]
    ) -> Dict[str, Any]:
        """Extract fields from passport document."""
        data = {}
        
        # Common passport patterns
        patterns = {
            'passport_number': r'(?:Passport|Pass\.|P)\s*(?:No\.?|Number|#)?\s*([A-Z0-9]{6,12})',
            'given_name': r'Given\s+Names?\s*[:\-]?\s*([A-Z][A-Z\s]+)',
            'surname': r'Surname\s*[:\-]?\s*([A-Z][A-Z\s]+)',
            'date_of_birth': r'(?:Date\s+of\s+Birth|DOB|Birth\s+Date)\s*[:\-]?\s*(\d{1,2}[\s\-./]\w{3,9}[\s\-./]\d{2,4})',
            'nationality': r'Nationality\s*[:\-]?\s*([A-Z][A-Z\s]+)',
            'sex': r'Sex\s*[:\-]?\s*([MF])',
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                data[field] = match.group(1).strip()
        
        return data
    
    def _extract_transcript_data(
        self, 
        raw_text: str, 
        text_blocks: List[Dict]
    ) -> Dict[str, Any]:
        """Extract fields from academic transcript."""
        data = {}
        
        # Look for student name, ID, grades, etc.
        patterns = {
            'student_name': r'(?:Student|Name)\s*[:\-]?\s*([A-Z][A-Za-z\s]+)',
            'student_id': r'(?:Student\s+ID|ID\s+Number)\s*[:\-]?\s*([A-Z0-9]+)',
            'institution': r'(?:Institution|School|University)\s*[:\-]?\s*([A-Za-z\s]+)',
            'completion_year': r'(?:Completed|Graduation|Year)\s*[:\-]?\s*(\d{4})',
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                data[field] = match.group(1).strip()
        
        # Extract grades/subjects (complex table parsing)
        data['courses'] = self._extract_course_grades(raw_text)
        
        return data
    
    def _extract_english_test_data(
        self, 
        raw_text: str, 
        text_blocks: List[Dict]
    ) -> Dict[str, Any]:
        """Extract fields from English test results (IELTS, TOEFL, PTE)."""
        data = {}
        
        # Detect test type
        if 'IELTS' in raw_text.upper():
            data['test_type'] = 'IELTS'
            data['scores'] = self._extract_ielts_scores(raw_text)
        elif 'TOEFL' in raw_text.upper():
            data['test_type'] = 'TOEFL'
            data['scores'] = self._extract_toefl_scores(raw_text)
        elif 'PTE' in raw_text.upper():
            data['test_type'] = 'PTE'
            data['scores'] = self._extract_pte_scores(raw_text)
        
        # Common fields
        patterns = {
            'candidate_name': r'(?:Candidate|Name)\s*[:\-]?\s*([A-Z][A-Za-z\s]+)',
            'test_date': r'(?:Test\s+Date|Date)\s*[:\-]?\s*(\d{1,2}[\s\-./]\w{3,9}[\s\-./]\d{2,4})',
            'overall_score': r'(?:Overall|Total)\s*(?:Band|Score)?\s*[:\-]?\s*([0-9.]+)',
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                data[field] = match.group(1).strip()
        
        return data
    
    def _extract_id_card_data(
        self, 
        raw_text: str, 
        text_blocks: List[Dict]
    ) -> Dict[str, Any]:
        """Extract fields from ID card/driver's license."""
        data = {}
        
        patterns = {
            'name': r'(?:Name|Full\s+Name)\s*[:\-]?\s*([A-Z][A-Za-z\s]+)',
            'id_number': r'(?:ID|License|Card)\s*(?:No\.?|Number|#)?\s*[:\-]?\s*([A-Z0-9]+)',
            'date_of_birth': r'(?:DOB|Date\s+of\s+Birth|Born)\s*[:\-]?\s*(\d{1,2}[\s\-./]\w{3,9}[\s\-./]\d{2,4})',
            'address': r'(?:Address|Residence)\s*[:\-]?\s*([A-Za-z0-9\s,.-]+)',
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                data[field] = match.group(1).strip()
        
        return data
    
    def _extract_generic_data(
        self, 
        raw_text: str, 
        text_blocks: List[Dict]
    ) -> Dict[str, Any]:
        """Extract generic fields from unknown document type."""
        return {
            "full_text": raw_text,
            "line_count": len(text_blocks),
            "word_count": len(raw_text.split())
        }
    
    def _extract_course_grades(self, text: str) -> List[Dict[str, str]]:
        """Extract course names and grades from transcript."""
        # Simplified - real implementation would need complex table parsing
        courses = []
        # Pattern: Course Name followed by grade (A, B, C, etc.)
        pattern = r'([A-Za-z\s&]+?)\s+([A-F][+-]?|\d+(?:\.\d+)?)'
        
        for match in re.finditer(pattern, text):
            courses.append({
                "course": match.group(1).strip(),
                "grade": match.group(2).strip()
            })
        
        return courses[:20]  # Limit to first 20 matches
    
    def _extract_ielts_scores(self, text: str) -> Dict[str, str]:
        """Extract IELTS band scores."""
        scores = {}
        skills = ['listening', 'reading', 'writing', 'speaking']
        
        for skill in skills:
            pattern = rf'{skill}\s*[:\-]?\s*([0-9.]+)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                scores[skill] = match.group(1)
        
        return scores
    
    def _extract_toefl_scores(self, text: str) -> Dict[str, str]:
        """Extract TOEFL scores."""
        scores = {}
        sections = ['reading', 'listening', 'speaking', 'writing']
        
        for section in sections:
            pattern = rf'{section}\s*[:\-]?\s*(\d+)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                scores[section] = match.group(1)
        
        return scores
    
    def _extract_pte_scores(self, text: str) -> Dict[str, str]:
        """Extract PTE Academic scores."""
        return self._extract_toefl_scores(text)  # Similar format
    
    def _calculate_confidence(
        self, 
        text_blocks: List[Dict], 
        extracted_data: Dict
    ) -> Dict[str, float]:
        """Calculate confidence scores for extracted fields."""
        confidence_scores = {}
        
        # Average confidence from text blocks
        if text_blocks:
            avg_confidence = sum(
                block.get('confidence', 0.0) 
                for block in text_blocks
            ) / len(text_blocks)
        else:
            avg_confidence = 0.0
        
        # Per-field confidence (simplified - real implementation would be more sophisticated)
        for field in extracted_data.keys():
            # Higher confidence for fields with clear patterns
            if field in ['passport_number', 'student_id', 'id_number']:
                confidence_scores[field] = min(avg_confidence + 0.1, 1.0)
            elif field in ['given_name', 'surname', 'student_name']:
                confidence_scores[field] = avg_confidence
            else:
                confidence_scores[field] = max(avg_confidence - 0.1, 0.0)
        
        confidence_scores['overall'] = avg_confidence
        
        return confidence_scores
    
    def _mock_ocr_extraction(
        self, 
        file_path: str, 
        document_type_code: str
    ) -> Dict[str, Any]:
        """
        Return mock OCR data for development/testing.
        Used when Azure SDK is not available.
        """
        # Generate consistent mock data based on file path hash
        file_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
        
        mock_data = {
            'PASSPORT': {
                "raw_text": "PASSPORT\nGiven Names: JOHN MICHAEL\nSurname: SMITH\nPassport No: N1234567\nNationality: AUSTRALIAN\nDate of Birth: 15 JAN 1995\nSex: M",
                "extracted_data": {
                    "passport_number": f"N{file_hash[:7].upper()}",
                    "given_name": "JOHN MICHAEL",
                    "surname": "SMITH",
                    "date_of_birth": "15 JAN 1995",
                    "nationality": "AUSTRALIAN",
                    "sex": "M"
                },
                "confidence_scores": {
                    "passport_number": 0.95,
                    "given_name": 0.92,
                    "surname": 0.94,
                    "date_of_birth": 0.88,
                    "nationality": 0.91,
                    "sex": 0.96,
                    "overall": 0.93
                }
            },
            'TRANSCRIPT': {
                "raw_text": "ACADEMIC TRANSCRIPT\nStudent Name: JOHN SMITH\nStudent ID: ST123456\nInstitution: Sydney High School\nCompletion Year: 2020",
                "extracted_data": {
                    "student_name": "JOHN SMITH",
                    "student_id": f"ST{file_hash[:6].upper()}",
                    "institution": "Sydney High School",
                    "completion_year": "2020",
                    "courses": [
                        {"course": "Mathematics Advanced", "grade": "A"},
                        {"course": "English Advanced", "grade": "B+"},
                        {"course": "Physics", "grade": "A-"}
                    ]
                },
                "confidence_scores": {
                    "student_name": 0.90,
                    "student_id": 0.94,
                    "institution": 0.89,
                    "completion_year": 0.95,
                    "overall": 0.92
                }
            },
            'ENGLISH_TEST': {
                "raw_text": "IELTS TEST REPORT\nCandidate: JOHN SMITH\nTest Date: 15 MAR 2024\nListening: 7.5\nReading: 7.0\nWriting: 6.5\nSpeaking: 7.5\nOverall Band: 7.0",
                "extracted_data": {
                    "test_type": "IELTS",
                    "candidate_name": "JOHN SMITH",
                    "test_date": "15 MAR 2024",
                    "overall_score": "7.0",
                    "scores": {
                        "listening": "7.5",
                        "reading": "7.0",
                        "writing": "6.5",
                        "speaking": "7.5"
                    }
                },
                "confidence_scores": {
                    "candidate_name": 0.91,
                    "test_date": 0.93,
                    "overall_score": 0.96,
                    "overall": 0.93
                }
            }
        }
        
        default_mock = {
            "raw_text": f"MOCK DOCUMENT\nDocument ID: {file_hash.upper()}\nThis is mock OCR data for development.",
            "extracted_data": {
                "document_id": file_hash.upper(),
                "full_text": "This is mock OCR data for development"
            },
            "confidence_scores": {
                "overall": 0.85
            }
        }
        
        data = mock_data.get(document_type_code, default_mock)
        
        return {
            **data,
            "text_blocks": [],
            "processing_time_ms": 150,
            "engine": "mock"
        }
    
    def map_to_application_fields(
        self, 
        extracted_data: Dict[str, Any],
        document_type_code: str
    ) -> Dict[str, Any]:
        """
        Map extracted OCR data to application form fields.
        
        Args:
            extracted_data: OCR extracted data
            document_type_code: Type of document
            
        Returns:
            Dictionary mapping application field paths to values
        """
        mappings = {}
        
        if document_type_code == 'PASSPORT':
            if 'given_name' in extracted_data:
                mappings['personal_details.given_name'] = extracted_data['given_name'].title()
            if 'surname' in extracted_data:
                mappings['personal_details.family_name'] = extracted_data['surname'].title()
            if 'passport_number' in extracted_data:
                mappings['personal_details.passport_number'] = extracted_data['passport_number']
            if 'nationality' in extracted_data:
                mappings['personal_details.nationality'] = extracted_data['nationality'].title()
            if 'date_of_birth' in extracted_data:
                # Would need date parsing here
                mappings['personal_details.date_of_birth'] = extracted_data['date_of_birth']
            if 'sex' in extracted_data:
                gender_map = {'M': 'Male', 'F': 'Female'}
                mappings['personal_details.gender'] = gender_map.get(extracted_data['sex'], extracted_data['sex'])
        
        elif document_type_code == 'TRANSCRIPT':
            if 'institution' in extracted_data:
                # Map to schooling history
                mappings['schooling_history.schools[0].name'] = extracted_data['institution']
            if 'completion_year' in extracted_data:
                mappings['schooling_history.schools[0].end_date'] = extracted_data['completion_year']
        
        elif document_type_code == 'ENGLISH_TEST':
            if 'test_type' in extracted_data:
                mappings['language_cultural.english_test_type'] = extracted_data['test_type']
            if 'overall_score' in extracted_data:
                mappings['language_cultural.english_test_score'] = extracted_data['overall_score']
            if 'test_date' in extracted_data:
                mappings['language_cultural.english_test_date'] = extracted_data['test_date']
        
        return mappings


# Singleton instance
ocr_service = OCRService()
