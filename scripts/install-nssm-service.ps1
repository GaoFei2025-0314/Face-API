<#
.SYNOPSIS
Install face_api as a Windows Service through NSSM.

.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts\install-nssm-service.ps1 -NssmPath C:\tools\nssm\nssm.exe -ApiKey "your-secret"

.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts\install-nssm-service.ps1 -NssmPath C:\missing\nssm.exe -WhatIf
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidateNotNullOrEmpty()]
    [string]$ServiceName = "face_api",

    [string]$ProjectPath = "",

    [ValidateRange(1, 65535)]
    [int]$Port = $(if ($env:FACE_PORT) { [int]$env:FACE_PORT } else { 8000 }),

    [ValidateNotNullOrEmpty()]
    [string]$NssmPath = $(if ($env:NSSM_PATH) { $env:NSSM_PATH } else { "nssm.exe" }),

    [string]$PythonPath = $(if ($env:FACE_PYTHON) { $env:FACE_PYTHON } else { "D:\anaconda3\envs\face_api\python.exe" }),

    [string]$ApiKey = $env:FACE_API_KEY,

    [ValidateNotNullOrEmpty()]
    [string]$FaceEnv = "production"
)

$ErrorActionPreference = "Stop"
trap {
    Write-Host "[face_api] ERROR: $($_.Exception.Message)"
    exit 1
}

if (-not $ProjectPath) {
    $ProjectPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Resolve-Nssm {
    param([string]$Path)
    if ([System.IO.Path]::IsPathRooted($Path)) {
        if (Test-Path -LiteralPath $Path -PathType Leaf) {
            return (Resolve-Path -LiteralPath $Path).Path
        }
        throw "NSSM not found at '$Path'. Install NSSM first or pass -NssmPath. The script will not download NSSM."
    }
    $cmd = Get-Command $Path -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    throw "NSSM executable '$Path' was not found in PATH. Install NSSM first or pass -NssmPath. The script will not download NSSM."
}

if (-not (Test-Path -LiteralPath $ProjectPath -PathType Container)) {
    throw "ProjectPath does not exist: $ProjectPath"
}
$runProd = Join-Path $ProjectPath "run-prod.bat"
if (-not (Test-Path -LiteralPath $runProd -PathType Leaf)) {
    throw "run-prod.bat not found under ProjectPath: $ProjectPath"
}

$nssm = Resolve-Nssm -Path $NssmPath
$logDir = Join-Path $ProjectPath "logs"
$stdoutLog = Join-Path $logDir "nssm-service.out.log"
$stderrLog = Join-Path $logDir "nssm-service.err.log"

$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "[face_api] Service '$ServiceName' already exists. It will be reconfigured."
} else {
    Write-Host "[face_api] Service '$ServiceName' does not exist. It will be installed."
}

if ($PSCmdlet.ShouldProcess("NSSM service '$ServiceName'", "install or reconfigure")) {
    if (-not (Test-Path -LiteralPath $logDir)) {
        New-Item -ItemType Directory -Path $logDir | Out-Null
    }
    if (-not $existing) {
        & $nssm install $ServiceName $runProd
    }
    & $nssm set $ServiceName AppDirectory $ProjectPath
    & $nssm set $ServiceName AppStdout $stdoutLog
    & $nssm set $ServiceName AppStderr $stderrLog
    & $nssm set $ServiceName AppRotateFiles 1
    & $nssm set $ServiceName AppRotateOnline 1
    & $nssm set $ServiceName AppRotateBytes 10485760
    & $nssm set $ServiceName AppEnvironmentExtra "FACE_PORT=$Port" "FACE_ENV=$FaceEnv" "FACE_PYTHON=$PythonPath"
    if ($ApiKey) {
        & $nssm set $ServiceName AppEnvironmentExtra "FACE_PORT=$Port" "FACE_ENV=$FaceEnv" "FACE_PYTHON=$PythonPath" "FACE_API_KEY=$ApiKey"
        Write-Host "[face_api] WARNING: FACE_API_KEY is stored in the NSSM service environment. Prefer machine environment variables for stricter secret handling."
    } else {
        Write-Host "[face_api] FACE_API_KEY was not provided. The service will rely on machine environment."
    }
    Write-Host "[face_api] Installed/reconfigured NSSM service: $ServiceName"
    Write-Host "[face_api] Start service: Start-Service -Name `"$ServiceName`""
}

$baseUrl = "http://localhost:$Port"
Write-Host "[face_api] Verify after start:"
Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\health-check.ps1 -BaseUrl $baseUrl -Port $Port"
Write-Host "[face_api] Service logs:"
Write-Host "  $stdoutLog"
Write-Host "  $stderrLog"
