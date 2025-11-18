# Test upload functionality

# Get access token first
$loginBody = @{
    username = "student@test.com"
    password = "password123"
} | ConvertTo-Json

$loginResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/auth/login" `
    -Method POST `
    -ContentType "application/json" `
    -Body $loginBody -UseBasicParsing

$token = ($loginResponse.Content | ConvertFrom-Json).access_token
Write-Host "Token: $token"

# Get applications
$appResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/applications" `
    -Method GET `
    -Headers @{"Authorization" = "Bearer $token"} `
    -UseBasicParsing

$appId = ($appResponse.Content | ConvertFrom-Json)[0].id
Write-Host "App ID: $appId"

# Create test image (1x1 pixel PNG)
$pngBytes = @(0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D, 
              0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, 
              0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4, 0x89, 0x00, 0x00, 0x00, 
              0x0D, 0x49, 0x44, 0x41, 0x54, 0x08, 0xD7, 0x63, 0xF8, 0x0F, 0x00, 0x00, 
              0x01, 0x01, 0x00, 0x00, 0x18, 0xDD, 0x8D, 0xB4, 0x00, 0x00, 0x00, 0x00, 
              0x49, 0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82) -as [byte[]]

$tempFile = [System.IO.Path]::GetTempFileName() + ".png"
[System.IO.File]::WriteAllBytes($tempFile, $pngBytes)
Write-Host "Created test image: $tempFile"

# Upload document
$documentTypeId = "10000000-0000-0000-0000-000000000001"

try {
    $form = @{
        application_id = $appId
        document_type_id = $documentTypeId
        file = Get-Item -Path $tempFile
    }

    $uploadResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/documents/upload" `
        -Method POST `
        -Headers @{"Authorization" = "Bearer $token"} `
        -Form $form `
        -UseBasicParsing

    Write-Host "Upload Response: $($uploadResponse.StatusCode)"
    Write-Host "Response Body: $($uploadResponse.Content)" | ConvertFrom-Json | ConvertTo-Json
} catch {
    Write-Host "Upload Error: $($_.Exception.Message)"
    Write-Host "Response: $($_.Exception.Response.Content | ConvertFrom-Json | ConvertTo-Json)"
}

# Cleanup
Remove-Item $tempFile
