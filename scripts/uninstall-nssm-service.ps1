<#
.SYNOPSIS
Uninstall the face_api Windows Service installed through NSSM.

.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts\uninstall-nssm-service.ps1 -NssmPath C:\tools\nssm\nssm.exe

.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts\uninstall-nssm-service.ps1 -ServiceName face_api -WhatIf
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidateNotNullOrEmpty()]
    [string]$ServiceName = "face_api",

    [ValidateNotNullOrEmpty()]
    [string]$NssmPath = $(if ($env:NSSM_PATH) { $env:NSSM_PATH } else { "nssm.exe" })
)

$ErrorActionPreference = "Stop"
trap {
    Write-Host "[face_api] ERROR: $($_.Exception.Message)"
    exit 1
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

$service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $service) {
    Write-Host "[face_api] Service '$ServiceName' does not exist. Nothing to uninstall."
    exit 0
}

$nssm = Resolve-Nssm -Path $NssmPath

if ($PSCmdlet.ShouldProcess("NSSM service '$ServiceName'", "stop and remove")) {
    if ($service.Status -ne "Stopped") {
        & $nssm stop $ServiceName
    }
    & $nssm remove $ServiceName confirm
    Write-Host "[face_api] Uninstalled NSSM service: $ServiceName"
}
