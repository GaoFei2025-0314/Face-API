param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$ApiKey = $env:FACE_API_KEY,
    [int]$Port = 8000,
    [string]$DbPath = $(if ($env:FACE_DB_PATH) { $env:FACE_DB_PATH } else { "faces.db" }),
    [string]$LogPath = $(if ($env:FACE_LOG_PATH) { $env:FACE_LOG_PATH } else { "logs\face_api.log" })
)

$ErrorActionPreference = "Stop"

function Write-Section($name) {
    Write-Host ""
    Write-Host "== $name =="
}

Write-Section "Port"
$listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listeners) {
    $listeners | Select-Object LocalAddress, LocalPort, State, OwningProcess | Format-Table -AutoSize
    foreach ($listener in $listeners) {
        $processId = $listener.OwningProcess
        try {
            Get-CimInstance Win32_Process -Filter "ProcessId=$processId" |
                Select-Object ProcessId, ParentProcessId, Name, CommandLine |
                Format-List
        } catch {
            Write-Host "[face_api] Listener PID $processId is not visible through Win32_Process."
        }
    }
} else {
    Write-Host "[face_api] Port $Port is not listening."
}

Write-Section "Health"
try {
    Invoke-RestMethod -Method Get -Uri "$BaseUrl/health" -TimeoutSec 5 | ConvertTo-Json -Depth 5
} catch {
    Write-Host "[face_api] Health check failed: $($_.Exception.Message)"
}

Write-Section "OpenAPI"
try {
    $openapi = Invoke-WebRequest -Method Get -Uri "$BaseUrl/openapi.json" -TimeoutSec 5
    Write-Host "[face_api] OpenAPI status: $($openapi.StatusCode)"
} catch {
    Write-Host "[face_api] OpenAPI check failed: $($_.Exception.Message)"
}

Write-Section "Protected Config"
if ($ApiKey) {
    try {
        $headers = @{ "X-API-Key" = $ApiKey }
        Invoke-RestMethod -Method Get -Uri "$BaseUrl/config/effective" -Headers $headers -TimeoutSec 5 |
            ConvertTo-Json -Depth 8
    } catch {
        Write-Host "[face_api] Protected config check failed: $($_.Exception.Message)"
    }
} else {
    Write-Host "[face_api] FACE_API_KEY is empty; protected config check skipped."
}

Write-Section "Database"
foreach ($file in @($DbPath, "$DbPath-wal", "$DbPath-shm")) {
    if (Test-Path -LiteralPath $file) {
        Get-Item -LiteralPath $file | Select-Object FullName, Length, LastWriteTime | Format-List
    } else {
        Write-Host "[face_api] Missing: $file"
    }
}

Write-Section "Log"
if (Test-Path -LiteralPath $LogPath) {
    Get-Item -LiteralPath $LogPath | Select-Object FullName, Length, LastWriteTime | Format-List
    Write-Host "[face_api] Recent log lines:"
    Get-Content -LiteralPath $LogPath -Tail 20
} else {
    Write-Host "[face_api] Log file not found: $LogPath"
}

Write-Section "GPU"
try {
    & nvidia-smi
} catch {
    Write-Host "[face_api] nvidia-smi unavailable or GPU driver not installed."
}
