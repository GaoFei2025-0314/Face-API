param(
    [Parameter(Mandatory = $true)][string]$BackupDir,
    [string]$DbPath = $(if ($env:FACE_DB_PATH) { $env:FACE_DB_PATH } else { "faces.db" })
)

$ErrorActionPreference = "Stop"

Write-Host "[face_api] Restore expects the service to be stopped first."

$baseName = Split-Path -Leaf $DbPath
$restoreFiles = @(
    @{ Source = Join-Path $BackupDir $baseName; Target = $DbPath },
    @{ Source = Join-Path $BackupDir "$baseName-wal"; Target = "$DbPath-wal" },
    @{ Source = Join-Path $BackupDir "$baseName-shm"; Target = "$DbPath-shm" }
)

foreach ($item in $restoreFiles) {
    if (Test-Path -LiteralPath $item.Source) {
        Copy-Item -LiteralPath $item.Source -Destination $item.Target -Force
        Write-Host "[face_api] Restored $($item.Target)"
    }
}

Write-Host "[face_api] Restore complete. Start the service and run scripts/health-check.ps1."

