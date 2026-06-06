<#
.SYNOPSIS
Install a Windows Task Scheduler task for face_api.

.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts\install-task-scheduler.ps1

.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts\install-task-scheduler.ps1 -TaskName "face_api_8001" -Port 8001 -WhatIf
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidateNotNullOrEmpty()]
    [string]$TaskName = "face_api",

    [string]$ProjectPath = "",

    [ValidateRange(1, 65535)]
    [int]$Port = $(if ($env:FACE_PORT) { [int]$env:FACE_PORT } else { 8000 }),

    [string]$PythonPath = $(if ($env:FACE_PYTHON) { $env:FACE_PYTHON } else { "D:\anaconda3\envs\face_api\python.exe" }),

    [ValidateNotNullOrEmpty()]
    [string]$FaceEnv = "production",

    [ValidateSet("Logon", "Startup")]
    [string]$Trigger = "Logon",

    [switch]$RunAsSystem
)

$ErrorActionPreference = "Stop"
trap {
    Write-Host "[face_api] ERROR: $($_.Exception.Message)"
    exit 1
}

if (-not $ProjectPath) {
    $ProjectPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Assert-ProjectPath {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        throw "ProjectPath does not exist: $Path"
    }
    $runProd = Join-Path $Path "run-prod.bat"
    if (-not (Test-Path -LiteralPath $runProd -PathType Leaf)) {
        throw "run-prod.bat not found under ProjectPath: $Path"
    }
}

Assert-ProjectPath -Path $ProjectPath

if ($Trigger -eq "Startup" -and -not $RunAsSystem) {
    throw "Trigger=Startup requires -RunAsSystem. For mapped drives such as H:, verify SYSTEM can access the project path before installing."
}

$logDir = Join-Path $ProjectPath "logs"
$logFile = Join-Path $logDir "task-scheduler.out.log"
$commands = @(
    "cd /d `"$ProjectPath`"",
    "set FACE_PORT=$Port",
    "set FACE_ENV=$FaceEnv",
    "set FACE_PYTHON=$PythonPath"
)
Write-Host "[face_api] FACE_API_KEY is not written to the scheduled task. Configure it as a user or machine environment variable for the task account."
$commands += "if not exist `"$logDir`" mkdir `"$logDir`""
$commands += "call run-prod.bat >> `"$logFile`" 2>>&1"
$actionArgs = "/c " + ($commands -join " && ")

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $actionArgs -WorkingDirectory $ProjectPath
$taskTrigger = if ($Trigger -eq "Startup") {
    New-ScheduledTaskTrigger -AtStartup
} else {
    New-ScheduledTaskTrigger -AtLogOn
}
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$description = "face_api long-running task on port $Port. ProjectPath=$ProjectPath"
$principal = if ($RunAsSystem) {
    New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
} else {
    $currentUser = if ($env:USERDOMAIN) { "$env:USERDOMAIN\$env:USERNAME" } else { $env:USERNAME }
    New-ScheduledTaskPrincipal -UserId $currentUser -LogonType Interactive -RunLevel Limited
}

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    if ($PSCmdlet.ShouldProcess("Scheduled task '$TaskName'", "replace existing task")) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
} else {
    Write-Host "[face_api] Scheduled task '$TaskName' does not exist. It will be created."
}

if ($PSCmdlet.ShouldProcess("Scheduled task '$TaskName'", "register face_api task")) {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $taskTrigger -Settings $settings -Principal $principal -Description $description | Out-Null
    Write-Host "[face_api] Installed scheduled task: $TaskName"
    Write-Host "[face_api] Start manually: Start-ScheduledTask -TaskName `"$TaskName`""
}

$baseUrl = "http://localhost:$Port"
Write-Host "[face_api] Verify after start:"
Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\health-check.ps1 -BaseUrl $baseUrl -Port $Port"
Write-Host "[face_api] Log file:"
Write-Host "  $logFile"
