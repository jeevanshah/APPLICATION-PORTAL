"""
OCR Service for document text extraction using Microsoft Azure AI Document Intelligence.
Handles passport, transcript, and certificate recognition with field extraction.
Uses prebuilt-idDocument model for passports and Computer Vision Read API for other documents.
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
        """Initialize OCR service with Azure Document Intelligence credentials."""
        # Use Document Intelligence for all OCR (has both specialized models + general Read)
        self.form_recognizer_endpoint = getattr(settings, 'AZURE_FORM_RECOGNIZER_ENDPOINT', None)
        self.form_recognizer_key = getattr(settings, 'AZURE_FORM_RECOGNIZER_KEY', None)
        
        # Fallback to vision credentials if form recognizer not configured (backwards compatibility)
        self.endpoint = self.form_recognizer_endpoint or getattr(settings, 'AZURE_VISION_ENDPOINT', None)
        self.key = self.form_recognizer_key or getattr(settings, 'AZURE_VISION_KEY', None)
        
        self.available = self.endpoint is not None and self.key is not None

        if not self.available:
            print("Warning: Azure Document Intelligence credentials not configured. OCR features will be mocked.")
        else:
            print(f"OCR Service initialized with endpoint: {self.endpoint}")

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

            # Use specialized prebuilt models for passports/IDs
            if document_type_code in ['PASSPORT', 'ID_CARD', 'DRIVERS_LICENSE']:
                return await self._extract_with_document_intelligence_id(image_data, document_type_code)
            
            # Use Document Intelligence Read model for all other documents
            return await self._extract_with_document_intelligence_read(image_data, document_type_code)

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

    async def _extract_with_document_intelligence_id(
        self, 
        image_bytes: bytes, 
        document_type_code: str
    ) -> Dict[str, Any]:
        """
        Extract structured data using Azure AI Document Intelligence prebuilt-idDocument model.
        
        Args:
            image_bytes: Image file bytes
            document_type_code: Type of document (PASSPORT, ID_CARD, etc.)
            
        Returns:
            Dictionary with extracted data, confidence scores, and raw text
        """
        try:
            # Submit document for analysis
            url = f"{self.endpoint.rstrip('/')}/formrecognizer/documentModels/prebuilt-idDocument:analyze?api-version=2023-07-31"
            headers = {
                "Ocp-Apim-Subscription-Key": self.key,
                "Content-Type": "application/octet-stream",
            }
            
            response = requests.post(url, headers=headers, data=image_bytes, timeout=30)
            response.raise_for_status()
            
            # Get operation location for polling
            operation_url = response.headers.get("Operation-Location")
            if not operation_url:
                raise OCRProcessingError("No Operation-Location returned from Document Intelligence")
            
            # Poll for results
            result = self._poll_document_intelligence(operation_url)
            
            # Extract structured fields from Document Intelligence response
            extracted_data = self._parse_document_intelligence_result(result, document_type_code)
            
            # Build raw text from all content
            raw_text = ""
            if "analyzeResult" in result and "content" in result["analyzeResult"]:
                raw_text = result["analyzeResult"]["content"]
            
            # Extract confidence scores
            confidence_scores = self._extract_confidence_from_di(result)
            
            return {
                "raw_text": raw_text,
                "extracted_data": extracted_data,
                "confidence_scores": confidence_scores,
                "processing_time_ms": 0,
                "engine": "azure_document_intelligence",
                "raw_result": result
            }
            
        except Exception as e:
            print(f"Document Intelligence ID model extraction failed: {str(e)}")
            print(f"Falling back to Document Intelligence Read model")
            # Fallback to Read model instead of Computer Vision
            return await self._extract_with_document_intelligence_read(image_bytes, document_type_code)

    async def _extract_with_document_intelligence_read(
        self, 
        image_bytes: bytes, 
        document_type_code: str
    ) -> Dict[str, Any]:
        """
        Extract text using Azure AI Document Intelligence Read model (general OCR).
        
        Args:
            image_bytes: Image file bytes
            document_type_code: Type of document (for structured extraction)
            
        Returns:
            Dictionary with extracted data, confidence scores, and raw text
        """
        try:
            # Submit document for analysis with Read model
            url = f"{self.endpoint.rstrip('/')}/formrecognizer/documentModels/prebuilt-read:analyze?api-version=2023-07-31"
            headers = {
                "Ocp-Apim-Subscription-Key": self.key,
                "Content-Type": "application/octet-stream",
            }
            
            response = requests.post(url, headers=headers, data=image_bytes, timeout=30)
            response.raise_for_status()
            
            # Get operation location for polling
            operation_url = response.headers.get("Operation-Location")
            if not operation_url:
                raise OCRProcessingError("No Operation-Location returned from Document Intelligence Read API")
            
            # Poll for results
            result = self._poll_document_intelligence(operation_url)
            
            # Extract text from result
            raw_text = ""
            if "analyzeResult" in result and "content" in result["analyzeResult"]:
                raw_text = result["analyzeResult"]["content"]
            
            # Extract structured data based on document type
            extracted_data = self._extract_structured_data(raw_text, document_type_code)
            
            # Calculate confidence scores
            confidence_scores = self._calculate_confidence(extracted_data)
            
            return {
                "raw_text": raw_text,
                "extracted_data": extracted_data,
                "confidence_scores": confidence_scores,
                "processing_time_ms": 0,
                "engine": "azure_document_intelligence_read",
                "raw_result": result
            }
            
        except Exception as e:
            print(f"Document Intelligence Read model extraction failed: {str(e)}")
            # Final fallback to mock
            print(f"Falling back to mock OCR data")
            # Create a simple mock result instead of calling missing method
            return {
                "raw_text": "",
                "extracted_data": {},
                "confidence_scores": {},
                "processing_time_ms": 0,
                "engine": "mock_fallback",
                "raw_result": {}
            }

    def _poll_document_intelligence(self, operation_url: str, max_retries: int = 60) -> Dict[str, Any]:
        """Poll Document Intelligence API for operation result."""
        headers = {
            "Ocp-Apim-Subscription-Key": self.key,
        }
        
        for attempt in range(max_retries):
            response = requests.get(operation_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            status = result.get("status", "").lower()
            
            if status == "succeeded":
                return result
            elif status == "failed":
                error = result.get("error", {})
                raise OCRProcessingError(f"Document Intelligence failed: {error.get('message', 'Unknown error')}")
            
            # Wait before retrying
            if attempt < max_retries - 1:
                time.sleep(1)
        
        raise OCRProcessingError(f"Document Intelligence operation did not complete after {max_retries} retries")

    def _parse_document_intelligence_result(
        self, 
        result: Dict[str, Any], 
        document_type_code: str
    ) -> Dict[str, Any]:
        """
        Parse Document Intelligence result to extract structured fields.
        
        Args:
            result: Full API response from Document Intelligence
            document_type_code: Type of document
            
        Returns:
            Dictionary of extracted fields
        """
        extracted_data = {}
        
        try:
            analyze_result = result.get("analyzeResult", {})
            documents = analyze_result.get("documents", [])
            
            if not documents:
                return extracted_data
            
            # Get the first document (usually only one for ID documents)
            doc = documents[0]
            fields = doc.get("fields", {})
            
            # Map Document Intelligence field names to our schema
            field_mapping = {
                "FirstName": "given_name",
                "LastName": "family_name",
                "DocumentNumber": "passport_number",
                "DateOfBirth": "date_of_birth",
                "DateOfExpiration": "expiry_date",
                "Sex": "gender",
                "CountryRegion": "country",
                "Nationality": "nationality",
                "PlaceOfBirth": "country_of_birth",
                "DateOfIssue": "date_of_issue",
            }
            
            for di_field, our_field in field_mapping.items():
                if di_field in fields:
                    field_data = fields[di_field]
                    
                    # Extract value (could be string, date, or other type)
                    value = None
                    if "valueString" in field_data:
                        value = field_data["valueString"]
                    elif "valueDate" in field_data:
                        value = field_data["valueDate"]
                    elif "content" in field_data:
                        value = field_data["content"]
                    
                    if value:
                        # Clean up the value
                        if our_field in ["given_name", "family_name"]:
                            value = self._clean_name_field(value)
                        extracted_data[our_field] = value
            
            # Create full_name by combining given_name and family_name
            if "given_name" in extracted_data or "family_name" in extracted_data:
                given = extracted_data.get("given_name", "")
                family = extracted_data.get("family_name", "")
                extracted_data["full_name"] = f"{given} {family}".strip()
            
            # Normalize nationality codes
            if "nationality" in extracted_data:
                extracted_data["nationality"] = self._normalize_nationality(extracted_data["nationality"])
            
            return extracted_data
            
        except Exception as e:
            print(f"Error parsing Document Intelligence result: {str(e)}")
            return extracted_data

    def _extract_confidence_from_di(self, result: Dict[str, Any]) -> Dict[str, float]:
        """Extract confidence scores from Document Intelligence result."""
        confidence_scores = {"overall": 0.0}
        
        try:
            analyze_result = result.get("analyzeResult", {})
            documents = analyze_result.get("documents", [])
            
            if documents:
                doc = documents[0]
                fields = doc.get("fields", {})
                
                # Get confidence for each field
                confidences = []
                for field_name, field_data in fields.items():
                    if "confidence" in field_data:
                        conf = field_data["confidence"]
                        confidence_scores[field_name.lower()] = conf
                        confidences.append(conf)
                
                # Calculate overall confidence
                if confidences:
                    confidence_scores["overall"] = sum(confidences) / len(confidences)
                else:
                    confidence_scores["overall"] = 0.9  # Default high confidence for DI
            
        except Exception as e:
            print(f"Error extracting confidence scores: {str(e)}")
            confidence_scores["overall"] = 0.85
        
        return confidence_scores
    
    def _clean_name_field(self, name: str) -> str:
        """
        Clean name fields by removing common test/specimen markers and normalizing format.
        
        Args:
            name: Raw name string from OCR
            
        Returns:
            Cleaned name string
        """
        if not name:
            return ""
        
        # Remove common specimen/test markers (case-insensitive)
        specimen_markers = [
            "SPECIMEN", "SAMPLE", "TEST", "DEMO", "EXAMPLE",
            "MODELO", "MUESTRA", "ECHANTILLON"
        ]
        
        cleaned = name.strip()
        
        # Remove specimen markers
        for marker in specimen_markers:
            # Remove as standalone word
            cleaned = re.sub(rf'\b{marker}\b', '', cleaned, flags=re.IGNORECASE)
        
        # Clean up multiple spaces and trim
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Capitalize properly (handle all-caps names)
        if cleaned.isupper():
            cleaned = cleaned.title()
        
        return cleaned
    
    def _normalize_nationality(self, nationality: str) -> str:
        """
        Normalize nationality strings to consistent format.
        
        Args:
            nationality: Raw nationality string (could be code or full name)
            
        Returns:
            Normalized nationality name
        """
        if not nationality:
            return ""
        
        nationality = nationality.strip().upper()
        
        # Map common nationality codes to full names
        nationality_map = {
            "NPL": "Nepalese",
            "NEPALI": "Nepalese",
            "IND": "Indian",
            "INDIAN": "Indian",
            "AUS": "Australian",
            "AUSTRALIAN": "Australian",
            "GBR": "British",
            "BRITISH": "British",
            "USA": "American",
            "AMERICAN": "American",
            "CAN": "Canadian",
            "CANADIAN": "Canadian",
            "CHN": "Chinese",
            "CHINESE": "Chinese",
            "JPN": "Japanese",
            "JAPANESE": "Japanese",
            "KOR": "Korean",
            "KOREAN": "Korean",
        }
        
        return nationality_map.get(nationality, nationality.capitalize())

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
            'TRANSCRIPT_10': self._extract_transcript_data,  # Grade 10
            'TRANSCRIPT_12': self._extract_transcript_data,  # Grade 12
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
        """Extract fields from academic transcript (Grade 10/12)."""
        # Detect transcript type
        is_grade_12 = bool(re.search(r'School\s+Leaving\s+Certificate|Grade\s+XII|\+2|HSEB', raw_text, re.IGNORECASE))
        
        if is_grade_12:
            return self._extract_grade12_data(raw_text)
        else:
            return self._extract_grade10_data(raw_text)

    def _extract_grade10_data(self, raw_text: str) -> Dict[str, Any]:
        """Extract fields from Grade 10 (SEE) transcript."""
        data = {}

        # Extract student name: "GRADE-SHEET [NAME] THE GRADE"
        name_match = re.search(
            r'GRADE-SHEET\s+([A-Z][A-Z\s]+?)(?:THE GRADE|DATE OF BIRTH)',
            raw_text,
            re.IGNORECASE
        )
        if name_match:
            student_name = name_match.group(1).strip()
            student_name = ' '.join(student_name.split())
            data['student_name'] = student_name

        # Extract institution: "OF [SCHOOL NAME] IN THE"
        institution_match = re.search(
            r'OF\s+([A-Z][A-Z\s,\.\-]+?)\s+IN\s+THE',
            raw_text,
            re.IGNORECASE
        )
        if institution_match:
            data['institution_name'] = institution_match.group(1).strip()

        # Extract Board
        if 'NATIONAL EXAMINATIONS BOARD' in raw_text or 'NEB' in raw_text:
            data['board'] = 'NEB'

        # Extract year: "(2020 AD)" or "2020 AD"
        year_match = re.search(r'\((\d{4})\s*AD\)', raw_text)
        if year_match:
            data['year_completed'] = year_match.group(1)

        # Extract roll/symbol number
        roll_match = re.search(
            r'(?:ROLL|SYMBOL)\s+NO\s+OF\s+(\d+)',
            raw_text,
            re.IGNORECASE
        )
        if roll_match:
            data['roll_number'] = roll_match.group(1)

        # Extract GPA: "GRADE POINT AVERAGE (GPA): [VALUE]"
        gpa_match = re.search(
            r'GRADE\s+POINT\s+AVERAGE\s*\(GPA\)[:\s]+([0-9.]+)',
            raw_text,
            re.IGNORECASE
        )
        if gpa_match:
            data['gpa'] = gpa_match.group(1)
            data['result'] = f"{gpa_match.group(1)} GPA"

        data['country'] = 'Nepal'
        data['subjects'] = self._extract_subject_grades(raw_text)

        return data

    def _extract_grade12_data(self, raw_text: str) -> Dict[str, Any]:
        """Extract fields from Grade 12 (+2/HSEB) transcript."""
        data = {}

        # Extract student name: "Name of Student : [NAME]"
        name_match = re.search(
            r'Name\s+of\s+Student\s*[:\-]\s*([A-Z][A-Z\s]+?)(?:\n|Date\s+of\s+Birth)',
            raw_text,
            re.IGNORECASE
        )
        if name_match:
            student_name = name_match.group(1).strip()
            student_name = ' '.join(student_name.split())
            data['student_name'] = student_name

        # Extract institution: "School: [SCHOOL NAME]"
        institution_match = re.search(
            r'School\s*:\s*([A-Z][A-Z\s,\.\-\']+?)(?:\n|Subject)',
            raw_text,
            re.IGNORECASE
        )
        if institution_match:
            institution = institution_match.group(1).strip()
            # Remove trailing location info if present
            institution = re.sub(r',\s*[A-Z\s]+\d+,\s*[A-Z]+\s*$', '', institution)
            data['institution_name'] = institution

        # Extract Board
        if 'NATIONAL EXAMINATIONS BOARD' in raw_text or 'NEB' in raw_text:
            data['board'] = 'NEB'
        elif 'HSEB' in raw_text or 'HIGHER SECONDARY EDUCATION BOARD' in raw_text:
            data['board'] = 'HSEB'

        # Extract year: "Year of Completion : 2079 (2022)"
        year_match = re.search(
            r'Year\s+of\s+Completion\s*[:\-]\s*\d+\s*\((\d{4})\)',
            raw_text,
            re.IGNORECASE
        )
        if year_match:
            data['year_completed'] = year_match.group(1)

        # Extract symbol number
        symbol_match = re.search(
            r'Symbol\s+Number\s*[:\-]?\s*(\d+)',
            raw_text,
            re.IGNORECASE
        )
        if symbol_match:
            data['roll_number'] = symbol_match.group(1)

        # Extract GPA: "Grade Point Average (GPA): [TOTAL] [ACTUAL_GPA]"
        gpa_match = re.search(
            r'GRADE\s+POINT\s+AVERAGE\s*\(GPA\)[:\s]+[\d.]+\s+([0-9.]+)',
            raw_text,
            re.IGNORECASE
        )
        if gpa_match:
            data['gpa'] = gpa_match.group(1)
            data['result'] = f"{gpa_match.group(1)} GPA"

        data['country'] = 'Nepal'
        data['subjects'] = self._extract_subject_grades(raw_text)

        return data

    def _extract_subject_grades(self, text: str) -> list:
        """Extract subject names and grades from transcript."""
        subjects = []
        
        # Look for patterns like "COMP ENGLISH A+" or "COMP. MATHMATICS 4 A"
        # This is a simplified pattern - real transcripts vary widely
        lines = text.split('\n')
        for line in lines:
            # Match lines with subject codes and grades
            match = re.search(
                r'(COMP\.?\s+[A-Z\s&,]+?)\s+([A-Z+\-\d.]+)\s*$',
                line,
                re.IGNORECASE
            )
            if match:
                subject = match.group(1).strip()
                grade = match.group(2).strip()
                # Basic validation
                if len(subject) > 5 and len(grade) <= 4:
                    subjects.append({
                        "subject": subject,
                        "grade": grade
                    })
        
        return subjects[:15]  # Limit to 15 subjects max

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

        # Extract candidate name with better pattern matching
        candidate_name = self._extract_candidate_name(raw_text)
        if candidate_name:
            data['candidate_name'] = candidate_name

        # Extract test date
        test_date_match = re.search(
            r'(?:Test\s+Date|Date|Date of Test|Date\s+of\s+Examination)\s*[:\-]?\s*(\d{1,2}[\s\-./]\w{3,9}[\s\-./]\d{2,4})',
            raw_text,
            re.IGNORECASE
        )
        if test_date_match:
            data['test_date'] = test_date_match.group(1).strip()

        # Extract overall score with multiple patterns
        overall_score = self._extract_overall_score(raw_text, data.get('test_type', 'Unknown'))
        if overall_score:
            data['overall_score'] = overall_score

        return data

    def _extract_overall_score(self, text: str, test_type: str) -> Optional[str]:
        """
        Extract overall score from English test documents.
        Handles IELTS (Band Score), TOEFL (Total Score), PTE (Overall Score).
        """
        # Strategy 1: IELTS format - "Overall Band Score" with score on same or next line
        if test_type == 'IELTS':
            # Pattern: "Overall Band Score" followed by number (possibly on next line)
            ielts_match = re.search(
                r'Overall\s+Band\s+Score\s*\n?\s*([0-9.]+)',
                text,
                re.IGNORECASE
            )
            if ielts_match:
                return ielts_match.group(1).strip()

        # Strategy 2: Generic patterns for all test types
        patterns = [
            r'Overall\s+Score\s*[:\-]?\s*([0-9.]+)',  # PTE/TOEFL
            r'Overall\s+Band\s*[:\-]?\s*([0-9.]+)',   # IELTS alternate
            r'Total\s+Score\s*[:\-]?\s*([0-9.]+)',    # TOEFL
            r'Overall\s*[:\-]\s*([0-9.]+)',           # Generic with colon
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None

    def _extract_candidate_name(self, raw_text: str) -> Optional[str]:
        """
        Extract candidate name from English test documents.
        Handles various formats: IELTS (First/Family Name), PTE (Name before ID), TOEFL, etc.
        """
        # Strategy 1: PTE format - Name appears before "Test Taker ID"
        # Pattern: "Example Test Taker Test Taker ID: PTE110000014"
        pte_name_match = re.search(
            r'([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){1,3})\s+Test\s+Taker\s+ID',
            raw_text,
            re.IGNORECASE
        )
        if pte_name_match:
            name = pte_name_match.group(1).strip()
            # Avoid capturing "Score Report" or other headers
            if name.upper() not in ['SCORE REPORT', 'TEST CENTRE', 'CANDIDATE INFORMATION']:
                return self._clean_name_field(name)

        # Strategy 2: Look for "First Name" and "Family Name" fields (IELTS format)
        first_name_match = re.search(
            r'First\s+Name\s*[:\-]?\s*\n?\s*([A-Z][A-Za-z]+)',
            raw_text,
            re.IGNORECASE
        )
        family_name_match = re.search(
            r'(?:Family\s+Name|Surname|Last\s+Name)\s*[:\-]?\s*\n?\s*([A-Z][A-Za-z]+)',
            raw_text,
            re.IGNORECASE
        )
        
        if first_name_match and family_name_match:
            first = first_name_match.group(1).strip()
            family = family_name_match.group(1).strip()
            # Clean specimen markers
            first = self._clean_name_field(first)
            family = self._clean_name_field(family)
            return f"{first} {family}"

        # Strategy 3: Look for "Candidate Name:" or "Test Taker:" with colon (TOEFL format)
        candidate_match = re.search(
            r'(?:Candidate\s+Name|Name)\s*:\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){1,3})',
            raw_text,
            re.IGNORECASE
        )
        if candidate_match:
            name = candidate_match.group(1).strip()
            return self._clean_name_field(name)

        # Strategy 4: Look for "Candidate:" followed by name on same or next line
        candidate_line_match = re.search(
            r'Candidate\s*[:\-]?\s*\n?\s*([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})',
            raw_text,
            re.IGNORECASE
        )
        if candidate_line_match:
            name = candidate_line_match.group(1).strip()
            return self._clean_name_field(name)

        return None

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
                        'NPL': 'Nepalese',
                        'AUSTRALIAN': 'Australian',
                        'AUS': 'Australian',
                        'INDIAN': 'Indian',
                        'IND': 'Indian',
                        'CHINESE': 'Chinese',
                        'CHN': 'Chinese',
                    }
                    mapped = nationality_map.get(nationality.upper(), nationality.title())
                    mappings['personal_details.nationality'] = mapped
            
            # Handle date_of_birth - normalize to ISO format YYYY-MM-DD
            if 'date_of_birth' in extracted_data:
                dob = extracted_data['date_of_birth'].strip()
                # Document Intelligence returns ISO format, others might not
                if re.match(r'^\d{4}-\d{2}-\d{2}', dob):
                    mappings['personal_details.date_of_birth'] = dob
                else:
                    # Try to parse "31 DEC 2000" format
                    mappings['personal_details.date_of_birth'] = self._normalize_date(dob)
            
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
                    'US': 'United States', 'USA': 'United States',
                    'GBR': 'United Kingdom', 'GB': 'United Kingdom', 'UK': 'United Kingdom',
                    'CAN': 'Canada', 'CA': 'Canada'
                }
                country_name = country_code_map.get(country.upper(), country)
                if country_name:
                    mappings['personal_details.country'] = country_name.title()
            
            # Handle country_of_birth / place_of_birth
            if 'country_of_birth' in extracted_data:
                cob = extracted_data['country_of_birth'].strip()
                cob = cob.split('\n')[0].split('|')[0].strip()
                if len(cob) > 2:
                    # Map country codes to names
                    country_code_map = {
                        'NPL': 'Nepal', 'AUS': 'Australia', 'IND': 'India', 'CHN': 'China',
                    }
                    cob = country_code_map.get(cob.upper(), cob)
                    mappings['personal_details.country_of_birth'] = cob.title()
            
            # Handle expiry_date / passport_expiry - normalize to ISO format
            if 'expiry_date' in extracted_data:
                exp = extracted_data['expiry_date'].strip()
                if re.match(r'^\d{4}-\d{2}-\d{2}', exp):
                    mappings['personal_details.passport_expiry'] = exp
                else:
                    mappings['personal_details.passport_expiry'] = self._normalize_date(exp)
            elif 'passport_expiry' in extracted_data:
                exp = extracted_data['passport_expiry'].strip()
                if re.match(r'^\d{4}-\d{2}-\d{2}', exp):
                    mappings['personal_details.passport_expiry'] = exp
                else:
                    mappings['personal_details.passport_expiry'] = self._normalize_date(exp)
            
            # Handle date_of_issue
            if 'date_of_issue' in extracted_data:
                doi = extracted_data['date_of_issue'].strip()
                # Only map if it looks like a date, not a single letter (OCR error)
                if len(doi) > 3 and any(char.isdigit() for char in doi):
                    if re.match(r'^\d{4}-\d{2}-\d{2}', doi):
                        mappings['personal_details.passport_issue_date'] = doi
                    else:
                        mappings['personal_details.passport_issue_date'] = self._normalize_date(doi)

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

    def _normalize_date(self, date_str: str) -> str:
        """
        Normalize various date formats to ISO format YYYY-MM-DD.
        
        Args:
            date_str: Date string in various formats (e.g., "31 DEC 2000", "2000-12-31")
            
        Returns:
            ISO formatted date string or original if parsing fails
        """
        if not date_str:
            return date_str
        
        # Already in ISO format
        if re.match(r'^\d{4}-\d{2}-\d{2}', date_str):
            return date_str
        
        # Try to parse "31 DEC 2000" or "31-DEC-2000" format
        month_map = {
            'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04',
            'MAY': '05', 'JUN': '06', 'JUL': '07', 'AUG': '08',
            'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'
        }
        
        # Try "DD MMM YYYY" format
        match = re.match(r'(\d{1,2})[\s\-]([A-Z]{3})[\s\-](\d{4})', date_str.upper())
        if match:
            day, month, year = match.groups()
            if month in month_map:
                return f"{year}-{month_map[month]}-{day.zfill(2)}"
        
        # Return original if can't parse
        return date_str


# Singleton instance
ocr_service = OCRService()
