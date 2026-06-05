param(
    [string]$DbPath = $(if ($env:FACE_DB_PATH) { $env:FACE_DB_PATH } else { "faces.db" }),
    [string]$BackupDir = "backups"
)

$ErrorActionPreference = "Stop"

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$targetDir = Join-Path $BackupDir $timestamp
New-Item -ItemType Directory -Force -Path $targetDir | Out-Null

$files = @($DbPath, "$DbPath-wal", "$DbPath-shm")
foreach ($file in $files) {
    if (Test-Path -LiteralPath $file) {
        Copy-Item -LiteralPath $file -Destination $targetDir -Force
        Write-Host "[face_api] Backed up $file to $targetDir"
    }
}

Write-Host "[face_api] Backup complete: $targetDir"

