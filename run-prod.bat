@echo off
setlocal

cd /d "%~dp0"

if "%FACE_ENV%"=="" set FACE_ENV=production
if "%FACE_LOG_PATH%"=="" set FACE_LOG_PATH=logs\face_api.log
if "%FACE_PORT%"=="" set FACE_PORT=8000
if "%FACE_PYTHON%"=="" set FACE_PYTHON=D:\anaconda3\envs\face_api\python.exe

powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=$env:FACE_PORT; if ($p -notmatch '^[0-9]+$') { exit 1 }; $n=[int]$p; if ($n -lt 1 -or $n -gt 65535) { exit 1 }; exit 0"
if errorlevel 1 (
  echo [face_api] ERROR: FACE_PORT must be an integer from 1 to 65535.
  exit /b 1
)

echo [face_api] production startup
echo [face_api] FACE_ENV=%FACE_ENV%
echo [face_api] FACE_USE_GPU=%FACE_USE_GPU%
echo [face_api] FACE_FORCE_CPU=%FACE_FORCE_CPU%
echo [face_api] FACE_DB_PATH=%FACE_DB_PATH%
echo [face_api] FACE_LOG_PATH=%FACE_LOG_PATH%
echo [face_api] FACE_PORT=%FACE_PORT%
echo [face_api] FACE_PYTHON=%FACE_PYTHON%

if "%FACE_API_KEY%"=="" (
  echo [face_api] ERROR: production mode requires FACE_API_KEY
  exit /b 1
)

echo [face_api] FACE_API_KEY is set.

for /f "tokens=5" %%p in ('netstat -ano ^| findstr /R /C:":%FACE_PORT% .*LISTENING"') do (
  echo [face_api] ERROR: port %FACE_PORT% is already in use by PID %%p
  echo [face_api] Run: powershell -ExecutionPolicy Bypass -File scripts\stop-service.ps1 -Port %FACE_PORT%
  exit /b 1
)

"%FACE_PYTHON%" -m uvicorn main:app --host 0.0.0.0 --port %FACE_PORT%
