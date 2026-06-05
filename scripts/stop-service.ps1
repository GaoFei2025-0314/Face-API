param(
    [int]$Port = 8000,
    [switch]$ForceUnrelated
)

$ErrorActionPreference = "Stop"

Write-Host "[face_api] Stopping service on port $Port..."

$connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if (-not $connections) {
    Write-Host "[face_api] Port $Port is already free."
    exit 0
}

$processIds = @()
foreach ($conn in $connections) {
    if ($conn.OwningProcess -and $processIds -notcontains $conn.OwningProcess) {
        $processIds += $conn.OwningProcess
    }
}

$allProcessIds = New-Object System.Collections.Generic.HashSet[int]
foreach ($processId in $processIds) {
    [void]$allProcessIds.Add([int]$processId)
    $children = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.ParentProcessId -eq $processId }
    foreach ($child in $children) {
        [void]$allProcessIds.Add([int]$child.ProcessId)
    }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$safeProcessIds = New-Object System.Collections.Generic.HashSet[int]
foreach ($processId in @($allProcessIds)) {
    $procInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
    $commandLine = if ($procInfo) { [string]$procInfo.CommandLine } else { "" }
    $isFaceApi = (
        $commandLine -like "*$repoRoot*" -or
        ($commandLine -like "*uvicorn*" -and $commandLine -like "*main:app*")
    )
    if ($isFaceApi -or $ForceUnrelated) {
        [void]$safeProcessIds.Add([int]$processId)
    } else {
        Write-Host "[face_api] Refusing to kill unrelated PID $processId."
        Write-Host "[face_api] CommandLine: $commandLine"
    }
}

if ($safeProcessIds.Count -eq 0) {
    Write-Host "[face_api] No face_api/uvicorn process matched. Use -ForceUnrelated only after manual confirmation."
    exit 1
}

foreach ($processId in @($safeProcessIds)) {
    try {
        $proc = Get-Process -Id $processId -ErrorAction Stop
        Write-Host "[face_api] Killing PID $processId ($($proc.ProcessName))"
        Stop-Process -Id $processId -Force -ErrorAction Stop
    } catch {
        Write-Host "[face_api] PID $processId is not a live process, skipping."
    }
}

Start-Sleep -Seconds 2
$remaining = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($remaining) {
    Write-Host "[face_api] Port $Port still appears busy:"
    $remaining | Select-Object LocalAddress, LocalPort, State, OwningProcess | Format-Table -AutoSize
    exit 1
}

Write-Host "[face_api] Port $Port is free."
