param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$ApiKey = $env:FACE_API_KEY,
    [int]$Port = 8000,
    [string]$DbPath = $(if ($env:FACE_DB_PATH) { $env:FACE_DB_PATH } else { "faces.db" }),
    [string]$LogPath = $(if ($env:FACE_LOG_PATH) { $env:FACE_LOG_PATH } else { "logs\face_api.log" })
)

$ErrorActionPreference = "Stop"

Write-Host "[face_api] Checking health..."
$health = Invoke-RestMethod -Method Get -Uri "$BaseUrl/health"
$health | ConvertTo-Json -Depth 5

Write-Host "[face_api] Checking port..."
$listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listeners) {
    $listeners | Select-Object LocalAddress, LocalPort, State, OwningProcess | Format-Table -AutoSize
} else {
    Write-Host "[face_api] Port $Port is not listening."
}

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

Write-Host "[face_api] Checking database files..."
foreach ($file in @($DbPath, "$DbPath-wal", "$DbPath-shm")) {
    if (Test-Path -LiteralPath $file) {
        Get-Item -LiteralPath $file | Select-Object FullName, Length, LastWriteTime | Format-List
    } else {
        Write-Host "[face_api] Missing: $file"
    }
}

Write-Host "[face_api] Checking log file..."
if (Test-Path -LiteralPath $LogPath) {
    Get-Item -LiteralPath $LogPath | Select-Object FullName, Length, LastWriteTime | Format-List
} else {
    Write-Host "[face_api] Log file not found: $LogPath"
}
