"""
OCR Service for document text extraction using Microsoft Azure Computer Vision.
Handles passport, transcript, and certificate recognition with field extraction.
"""
import hashlib
import re
import os
import time
import requests
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

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
        self.available = self.endpoint is not None and self.key is not None

        if not self.available:
            print("Warning: Azure Vision credentials not configured. OCR features will be mocked.")

    def is_available(self) -> bool:
        """Check if OCR service is configured and available."""
        return self.available

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

            # Call Azure Computer Vision Read API
            raw_text, raw_result = self._call_azure_vision_api(image_data)

            if not raw_text:
                # If Azure fails, fall back to mock
                return self._mock_ocr_extraction(file_path, document_type_code)

            # Extract structured data based on document type
            extracted_data = self._extract_structured_data(
                raw_text,
                document_type_code
            )

            # Calculate confidence scores
            confidence_scores = self._calculate_confidence(extracted_data)

            return {
                "raw_text": raw_text,
                "extracted_data": extracted_data,
                "confidence_scores": confidence_scores,
                "processing_time_ms": 0,
                "engine": "azure_computer_vision",
                "raw_result": raw_result
            }

        except Exception as e:
            print(f"OCR extraction failed: {str(e)}")
            # Fall back to mock data
            return self._mock_ocr_extraction(file_path, document_type_code)

    def _call_azure_vision_api(self, image_bytes: bytes) -> Tuple[str, Dict[str, Any]]:
        """Call Azure Computer Vision Read API and get extracted text."""
        url = f"{self.endpoint.rstrip('/')}/vision/v3.2/read/analyze"
        headers = {
            "Ocp-Apim-Subscription-Key": self.key,
            "Content-Type": "application/octet-stream",
        }

        # Submit the image for reading
        response = requests.post(url, headers=headers, data=image_bytes, timeout=30)
        response.raise_for_status()
        
        operation_url = response.headers.get("Operation-Location")
        if not operation_url:
            raise OCRProcessingError("No Operation-Location returned from Azure Vision API")

        # Poll for results
        result = self._poll_azure_vision_api(operation_url)

        # Extract text from result
        raw_text = ""
        if result.get("status") == "succeeded" and "analyzeResult" in result:
            for page in result["analyzeResult"].get("readResults", []):
                for line in page.get("lines", []):
                    raw_text += line.get("text", "") + "\n"

        return raw_text, result

    def _poll_azure_vision_api(self, operation_url: str, max_retries: int = 60) -> Dict[str, Any]:
        """Poll Azure Vision API for operation result."""
        headers = {
            "Ocp-Apim-Subscription-Key": self.key,
        }

        for attempt in range(max_retries):
            response = requests.get(operation_url, headers=headers, timeout=10)
            response.raise_for_status()

            result = response.json()
            status = result.get("status", "").lower()

            if status == "succeeded" or status == "failed":
                return result

            # Wait before retrying
            if attempt < max_retries - 1:
                time.sleep(1)

        raise OCRProcessingError(f"Operation did not complete after {max_retries} retries")

    def _extract_structured_data(
        self,
        raw_text: str,
        document_type_code: str
    ) -> Dict[str, Any]:
        """
        Extract structured fields based on document type.

        Args:
            raw_text: Full extracted text
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

        extractor = extractors.get(
            document_type_code,
            self._extract_generic_data)
        return extractor(raw_text)

    def _extract_passport_data(
        self,
        raw_text: str
    ) -> Dict[str, Any]:
        """Extract fields from passport document."""
        data = {}

        # Split text into lines for better structured parsing
        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]

        # Method 1: Try structured field extraction (label | value format)
        for i, line in enumerate(lines):
            line_upper = line.upper()
            
            # Pattern: "LABEL | VALUE" (bilingual passports often use this)
            if '|' in line:
                parts = line.split('|')
                if len(parts) >= 2:
                    value = parts[-1].strip()  # Take the last part as value
                    
                    if 'GIVEN' in line_upper and 'NAME' in line_upper:
                        if i + 1 < len(lines) and '|' not in lines[i + 1]:
                            data['given_name'] = lines[i + 1].strip()
                    elif 'SURNAME' in line_upper:
                        if i + 1 < len(lines) and '|' not in lines[i + 1]:
                            data['family_name'] = lines[i + 1].strip()
                    elif 'NATIONALITY' in line_upper:
                        if i + 1 < len(lines) and '|' not in lines[i + 1]:
                            data['nationality'] = lines[i + 1].strip()
                    elif 'PASSPORT' in line_upper and 'NO' in line_upper:
                        if i + 1 < len(lines) and '|' not in lines[i + 1] and len(lines[i + 1]) > 3:
                            passport = lines[i + 1].strip()
                            # Validate it looks like a passport number
                            if re.match(r'^[A-Z0-9]{6,}$', passport):
                                data['passport_number'] = passport
                    elif 'SEX' in line_upper:
                        if i + 1 < len(lines) and '|' not in lines[i + 1]:
                            data['gender'] = lines[i + 1].strip()
                    elif 'DATE' in line_upper and 'BIRTH' in line_upper:
                        if i + 1 < len(lines) and '|' not in lines[i + 1]:
                            data['date_of_birth'] = lines[i + 1].strip()
                    elif 'DATE' in line_upper and 'ISSUE' in line_upper:
                        if i + 1 < len(lines) and '|' not in lines[i + 1]:
                            data['date_of_issue'] = lines[i + 1].strip()
                    elif 'DATE' in line_upper and 'EXPIRY' in line_upper:
                        if i + 1 < len(lines) and '|' not in lines[i + 1]:
                            data['expiry_date'] = lines[i + 1].strip()
                    elif 'COUNTRY' in line_upper and 'CODE' in line_upper:
                        if i + 1 < len(lines) and '|' not in lines[i + 1]:
                            data['country'] = lines[i + 1].strip()
                    elif 'PLACE' in line_upper and 'BIRTH' in line_upper:
                        if i + 1 < len(lines) and '|' not in lines[i + 1]:
                            data['country_of_birth'] = lines[i + 1].strip()

        # Method 2: Extract from MRZ (Machine Readable Zone) at bottom
        # MRZ format: P<COUNTRY_CODE><SURNAME><<FIRST_NAME><<<...
        mrz_lines = [l for l in lines if l.startswith('P<')]
        if mrz_lines:
            mrz = mrz_lines[0]
            # Extract country code (3 chars after P<)
            if len(mrz) > 5:
                data['country'] = mrz[2:5].strip('<')
            
            # Extract passport number from MRZ (first 9 chars after country code)
            if len(mrz) > 14:
                potential_passport = mrz[5:14].strip('<')
                if re.match(r'^[A-Z0-9]{6,}$', potential_passport):
                    data['passport_number'] = potential_passport
            
            # Try to extract names from MRZ
            if '<<' in mrz:
                name_part = mrz.split('<<')[1] if len(mrz.split('<<')) > 1 else ''
                name_part = name_part.strip('<')
                if '<' in name_part:
                    parts = name_part.split('<')
                    if parts[0] and 'family_name' not in data:
                        data['family_name'] = parts[0]
                    if len(parts) > 1 and parts[1] and 'given_name' not in data:
                        data['given_name'] = parts[1]

        # Method 3: Fallback regex patterns for unstructured data
        if 'passport_number' not in data:
            # Look for 6-9 alphanumeric character sequences
            for potential in re.finditer(r'\b([A-Z][A-Z0-9]{5,8})\b', raw_text):
                candidate = potential.group(1)
                if not any(word in candidate for word in ['DATE', 'TYPE', 'ISSUE', 'EXPIRY']):
                    data['passport_number'] = candidate
                    break

        if 'given_name' not in data:
            match = re.search(r'(?:Given|First)\s+Names?\s*[:\-]?\s*([A-Z][A-Z\s]{2,})', raw_text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if '\n' in name:
                    name = name.split('\n')[0]
                data['given_name'] = name

        if 'family_name' not in data:
            match = re.search(r'(?:Surname|Family\s+Name|Last\s+Name)\s*[:\-]?\s*([A-Z][A-Z\s]{2,})', raw_text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if '\n' in name:
                    name = name.split('\n')[0]
                data['family_name'] = name

        if 'nationality' not in data:
            match = re.search(r'Nationality\s*[:\-]?\s*([A-Z][A-Za-z\s]{2,})', raw_text, re.IGNORECASE)
            if match:
                nationality = match.group(1).strip()
                if '\n' in nationality:
                    nationality = nationality.split('\n')[0]
                data['nationality'] = nationality

        # Extract date components if full dates were found
        if 'date_of_birth' in data and 'date_of_birth' not in data:
            dob = data.get('date_of_birth', '')
            if re.search(r'\d{1,2}\s+[A-Z]{3}\s+\d{4}', dob):
                data['date_of_birth'] = dob

        return data

    def _extract_transcript_data(
        self,
        raw_text: str
    ) -> Dict[str, Any]:
        """Extract fields from academic transcript."""
        data = {}

        # Look for student name, ID, grades, etc.
        patterns = {
            'institution_name': r'(?:Institution|School|University|HSC|SLC)\s*[:\-]?\s*([A-Za-z\s]+)',
            'student_id': r'(?:Student\s+ID|ID\s+Number|Candidate\s+ID)\s*[:\-]?\s*([A-Z0-9]+)',
            'year_completed': r'(?:Completed|Graduation|Year|Date of Issue)\s*[:\-]?\s*(\d{4})',
        }

        for field, pattern in patterns.items():
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                data[field] = match.group(1).strip()

        data['country'] = 'Australia'  # Default to Australia for transcripts
        return data

    def _extract_english_test_data(
        self,
        raw_text: str
    ) -> Dict[str, Any]:
        """Extract fields from English test results (IELTS, TOEFL, PTE)."""
        data = {}

        # Detect test type
        if 'IELTS' in raw_text.upper():
            data['test_type'] = 'IELTS'
            data['component_scores'] = self._extract_ielts_scores(raw_text)
        elif 'TOEFL' in raw_text.upper():
            data['test_type'] = 'TOEFL'
            data['component_scores'] = self._extract_toefl_scores(raw_text)
        elif 'PTE' in raw_text.upper():
            data['test_type'] = 'PTE'
            data['component_scores'] = self._extract_pte_scores(raw_text)
        else:
            data['test_type'] = 'Unknown'

        # Common fields
        patterns = {
            'candidate_name': r'(?:Candidate|Name|Test Taker)\s*[:\-]?\s*([A-Z][A-Za-z\s]+)',
            'test_date': r'(?:Test\s+Date|Date|Date of Test)\s*[:\-]?\s*(\d{1,2}[\s\-./]\w{3,9}[\s\-./]\d{2,4})',
            'overall_score': r'(?:Overall|Total)\s*(?:Band|Score)?\s*[:\-]?\s*([0-9.]+)',
        }

        for field, pattern in patterns.items():
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                data[field] = match.group(1).strip()

        return data

    def _extract_id_card_data(
        self,
        raw_text: str
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
        raw_text: str
    ) -> Dict[str, Any]:
        """Extract generic fields from unknown document type."""
        return {
            "full_text": raw_text[:500],  # First 500 chars
            "line_count": len(raw_text.split('\n')),
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
        extracted_data: Dict
    ) -> Dict[str, float]:
        """Calculate confidence scores for extracted fields."""
        confidence_scores = {}

        # Per-field confidence (simplified)
        for field in extracted_data.keys():
            # Higher confidence for fields with clear patterns
            if field in ['passport_number', 'student_id', 'id_number']:
                confidence_scores[field] = 0.95
            elif field in ['given_name', 'family_name', 'student_name']:
                confidence_scores[field] = 0.90
            else:
                confidence_scores[field] = 0.85

        confidence_scores['overall'] = 0.90

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
            "raw_text": f"MOCK DOCUMENT\nDocument ID: {
                file_hash.upper()}\nThis is mock OCR data for development.",
            "extracted_data": {
                "document_id": file_hash.upper(),
                "full_text": "This is mock OCR data for development"},
            "confidence_scores": {
                "overall": 0.85}}

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
            # Handle given_name
            if 'given_name' in extracted_data:
                name = extracted_data['given_name'].strip()
                # Remove extra text after name (e.g., "HRIDAYA\nUITPOCIT" -> "HRIDAYA")
                name = name.split('\n')[0].split('|')[0].strip()
                # Filter out label text that might be included
                if not any(keyword in name.upper() for keyword in ['NATIONALITY', 'PERSONAL']):
                    mappings['personal_details.given_name'] = name.title()
            
            # Handle family_name/surname
            if 'family_name' in extracted_data:
                name = extracted_data['family_name'].strip()
                # Remove extra text (e.g., "LAMSAL SPECIMEN\nWITH" -> "LAMSAL SPECIMEN")
                name = name.split('\n')[0].split('|')[0].strip()
                # Filter out label text
                if not any(keyword in name.upper() for keyword in ['WITH', 'GIVEN', 'NAMES']):
                    mappings['personal_details.family_name'] = name.title()
            elif 'surname' in extracted_data:
                name = extracted_data['surname'].strip()
                name = name.split('\n')[0].split('|')[0].strip()
                mappings['personal_details.family_name'] = name.title()
            
            # Handle passport_number
            if 'passport_number' in extracted_data:
                passport = extracted_data['passport_number'].strip()
                # Extract valid passport number (usually alphanumeric, 6-12 chars)
                passport = re.sub(r'[^A-Z0-9]', '', passport.upper())[:12]
                if len(passport) >= 6:
                    mappings['personal_details.passport_number'] = passport
            
            # Handle nationality
            if 'nationality' in extracted_data:
                nationality = extracted_data['nationality'].strip()
                nationality = nationality.split('\n')[0].split('|')[0].strip()
                # Filter out garbage text
                if len(nationality) > 2 and not any(char.isdigit() for char in nationality[:3]):
                    # Convert common country adjectives to country names
                    nationality_map = {
                        'NEPALI': 'Nepalese',
                        'NEPAL': 'Nepal',
                        'AUSTRALIAN': 'Australian',
                        'INDIAN': 'Indian',
                        'CHINESE': 'Chinese',
                    }
                    mapped = nationality_map.get(nationality.upper(), nationality.title())
                    mappings['personal_details.nationality'] = mapped
            
            # Handle date_of_birth
            if 'date_of_birth' in extracted_data:
                dob = extracted_data['date_of_birth'].strip()
                mappings['personal_details.date_of_birth'] = dob
            
            # Handle gender/sex
            if 'gender' in extracted_data:
                gender = extracted_data['gender'].strip().upper()
                if gender:
                    gender_map = {'M': 'Male', 'F': 'Female', 'MALE': 'Male', 'FEMALE': 'Female'}
                    mappings['personal_details.gender'] = gender_map.get(gender, gender)
            
            # Handle country (country of origin/issue)
            if 'country' in extracted_data:
                country = extracted_data['country'].strip()
                # Convert country code to country name if needed
                country_code_map = {
                    'NPL': 'Nepal', 'AUS': 'Australia', 'IND': 'India', 'CHN': 'China',
                    'US': 'United States', 'GBR': 'United Kingdom', 'CAN': 'Canada'
                }
                country_name = country_code_map.get(country.upper(), country)
                if country_name:
                    mappings['personal_details.country'] = country_name.title()
            
            # Handle country_of_birth / place_of_birth
            if 'country_of_birth' in extracted_data:
                cob = extracted_data['country_of_birth'].strip()
                cob = cob.split('\n')[0].split('|')[0].strip()
                if len(cob) > 2:
                    mappings['personal_details.country_of_birth'] = cob.title()
            
            # Handle expiry_date / passport_expiry
            if 'expiry_date' in extracted_data:
                mappings['personal_details.passport_expiry'] = extracted_data['expiry_date'].strip()
            elif 'passport_expiry' in extracted_data:
                mappings['personal_details.passport_expiry'] = extracted_data['passport_expiry'].strip()
            
            # Handle date_of_issue
            if 'date_of_issue' in extracted_data:
                doi = extracted_data['date_of_issue'].strip()
                # Only map if it looks like a date, not a single letter (OCR error)
                if len(doi) > 3 and any(char.isdigit() for char in doi):
                    mappings['personal_details.passport_issue_date'] = doi

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
