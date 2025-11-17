# Document Types Reference

## 📋 Available Document Types

These document types are now seeded in your database. Use these UUIDs when uploading documents via the API.

---

## 🆔 Document Type IDs

### **Mandatory Documents** (Required for Application)

| Name | Code | UUID | OCR Enabled |
|------|------|------|-------------|
| **Passport** | `PASSPORT` | `10000000-0000-0000-0000-000000000001` | ✅ Yes |
| **SLC Transcript** | `TRANSCRIPT_SLC` | `10000000-0000-0000-0000-000000000002` | ✅ Yes |
| **HSC Transcript** | `TRANSCRIPT_HSC` | `10000000-0000-0000-0000-000000000003` | ✅ Yes |
| **English Test Results** | `ENGLISH_TEST` | `10000000-0000-0000-0000-000000000004` | ✅ Yes |

### **Optional Documents**

| Name | Code | UUID | OCR Enabled |
|------|------|------|-------------|
| **National ID / License** | `ID_CARD` | `10000000-0000-0000-0000-000000000005` | ✅ Yes |
| **Birth Certificate** | `BIRTH_CERTIFICATE` | `10000000-0000-0000-0000-000000000006` | ❌ No |
| **Previous Visa** | `PREVIOUS_VISA` | `10000000-0000-0000-0000-000000000007` | ❌ No |
| **Health Cover** | `HEALTH_COVER` | `10000000-0000-0000-0000-000000000008` | ❌ No |
| **Financial Proof** | `FINANCIAL_PROOF` | `10000000-0000-0000-0000-000000000009` | ❌ No |
| **Relation Proof** | `RELATION_PROOF` | `10000000-0000-0000-0000-000000000010` | ❌ No |
| **Tax Income** | `TAX_INCOME` | `10000000-0000-0000-0000-000000000011` | ❌ No |
| **Business Income** | `BUSINESS_INCOME` | `10000000-0000-0000-0000-000000000012` | ❌ No |
| **Other Documents** | `OTHER` | `10000000-0000-0000-0000-000000000013` | ❌ No |

---

## 🧪 Testing Document Upload

### Example: Upload Passport

**Using Swagger UI:**
1. Go to http://localhost:8000/docs
2. Find **POST /api/v1/documents/upload**
3. Click "Try it out"
4. Fill in:
   - `application_id`: Your application UUID
   - `document_type_id`: `10000000-0000-0000-0000-000000000001` (Passport)
   - `file`: Upload a PDF/image
   - `process_ocr`: `true`
5. Click "Execute"

**Using PowerShell:**
```powershell
# Create form data
$form = @{
    application_id = "your-application-uuid"
    document_type_id = "10000000-0000-0000-0000-000000000001"
    file = Get-Item "C:\path\to\passport.pdf"
    process_ocr = "true"
}

# Upload
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/documents/upload" `
    -Method POST `
    -Headers @{"Authorization" = "Bearer your-token"} `
    -Form $form
```

**Using curl:**
```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Authorization: Bearer your-token" \
  -F "application_id=your-application-uuid" \
  -F "document_type_id=10000000-0000-0000-0000-000000000001" \
  -F "file=@passport.pdf" \
  -F "process_ocr=true"
```

---

## 📊 OCR Feature Support

### Documents with OCR Auto-fill

| Document Type | Extracted Fields | Auto-fills To |
|---------------|------------------|---------------|
| **Passport** | Name, Passport #, DOB, Nationality, Gender | Personal Details Step |
| **Transcripts** | School Name, Student ID, Completion Year | Schooling History Step |
| **English Test** | Test Type, Scores, Test Date | Language & Cultural Step |
| **ID Card** | Name, ID Number, Address, DOB | Personal Details Step |

### Documents without OCR

These documents are stored for verification but don't have auto-fill:
- Birth Certificate
- Previous Visa
- Health Cover
- Financial/Tax/Business documents (for GS process)

---

## 🔍 Quick Reference for Testing

### Test Credentials
```json
{
  "agent": {
    "email": "test.agent@agency.com",
    "password": "AgentPass123!",
    "user_id": "ddee69e2-a48f-4b4d-8440-3e8efc38c786"
  },
  "student": {
    "email": "test.student@example.com",
    "password": "StudentPass123!",
    "user_id": "0cfb9aec-5e16-48cb-b1a1-5f4dd8dde802"
  }
}
```

### Common Document Type IDs (for quick copy-paste)
```
Passport:      10000000-0000-0000-0000-000000000001
SLC Transcript: 10000000-0000-0000-0000-000000000002
HSC Transcript: 10000000-0000-0000-0000-000000000003
English Test:   10000000-0000-0000-0000-000000000004
ID Card:        10000000-0000-0000-0000-000000000005
Other:          10000000-0000-0000-0000-000000000013
```

---

## 🎯 Testing Workflow

1. **Login as Agent**
   ```
   POST /api/v1/auth/login
   Body: {"username": "test.agent@agency.com", "password": "AgentPass123!"}
   ```

2. **Create Application** (or get existing one)
   ```
   POST /api/v1/applications
   Body: {"student_profile_id": "...", "course_offering_id": "..."}
   ```

3. **Upload Passport** (with OCR)
   ```
   POST /api/v1/documents/upload
   Form: application_id, document_type_id=10000000..001, file, process_ocr=true
   ```

4. **Check OCR Results**
   ```
   GET /api/v1/documents/{document_id}/ocr
   ```

5. **Get Auto-fill Suggestions**
   ```
   GET /api/v1/documents/application/{application_id}/autofill
   ```

6. **Apply to Form** (mock data will suggest values for personal details)

---

## 📝 Notes

- **Mock Mode Active**: OCR returns realistic mock data without Azure credentials
- **File Limits**: Max 20MB, formats: PDF, JPG, PNG, TIFF, BMP, GIF
- **Permissions**: Agents can upload to own apps, Students to own apps, Staff to assigned
- **Versioning**: Re-uploading same document type creates a new version (keeps history)

---

## 🚀 Next Steps

1. Test document upload in Swagger UI
2. Verify OCR mock responses
3. Check auto-fill suggestions
4. Test with different document types
5. Verify permission checks work

**API Documentation:** http://localhost:8000/docs
