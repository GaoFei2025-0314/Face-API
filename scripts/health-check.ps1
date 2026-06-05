param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$ApiKey = $env:FACE_API_KEY
)

$ErrorActionPreference = "Stop"

Write-Host "[face_api] Checking health..."
$health = Invoke-RestMethod -Method Get -Uri "$BaseUrl/health"
$health | ConvertTo-Json -Depth 5

Write-Host "[face_api] Checking OpenAPI..."
$openapi = Invoke-WebRequest -Method Get -Uri "$BaseUrl/openapi.json"
Write-Host "[face_api] OpenAPI status: $($openapi.StatusCode)"

if ($ApiKey) {
    Write-Host "[face_api] Checking effective config..."
    $headers = @{ "X-API-Key" = $ApiKey }
    $config = Invoke-RestMethod -Method Get -Uri "$BaseUrl/config/effective" -Headers $headers
    $config | ConvertTo-Json -Depth 5
} else {
    Write-Host "[face_api] Skipping protected config check because FACE_API_KEY is empty."
}

