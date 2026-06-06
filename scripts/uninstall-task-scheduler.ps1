<#
.SYNOPSIS
Uninstall the Windows Task Scheduler task for face_api.

.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts\uninstall-task-scheduler.ps1 -TaskName "face_api"

.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts\uninstall-task-scheduler.ps1 -TaskName "face_api" -WhatIf
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidateNotNullOrEmpty()]
    [string]$TaskName = "face_api"
)

$ErrorActionPreference = "Stop"
trap {
    Write-Host "[face_api] ERROR: $($_.Exception.Message)"
    exit 1
}

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $existing) {
    Write-Host "[face_api] Scheduled task '$TaskName' does not exist. Nothing to uninstall."
    exit 0
}

if ($PSCmdlet.ShouldProcess("Scheduled task '$TaskName'", "stop and unregister")) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "[face_api] Uninstalled scheduled task: $TaskName"
}
