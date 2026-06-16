@echo off
setlocal

cd /d "%~dp0\.."

if "%BUSINESS_DEMO_PORT%"=="" set BUSINESS_DEMO_PORT=8010
if "%FACE_PYTHON%"=="" set FACE_PYTHON=D:\anaconda3\envs\face_api\python.exe

powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=$env:BUSINESS_DEMO_PORT; if ($p -notmatch '^[0-9]+$') { exit 1 }; $n=[int]$p; if ($n -lt 1 -or $n -gt 65535) { exit 1 }; exit 0"
if errorlevel 1 (
  echo [business-demo] ERROR: BUSINESS_DEMO_PORT must be an integer from 1 to 65535.
  exit /b 1
)

if not exist "%FACE_PYTHON%" (
  echo [business-demo] ERROR: FACE_PYTHON does not exist: %FACE_PYTHON%
  echo [business-demo] Fix: set FACE_PYTHON=C:\path\to\python.exe
  echo [business-demo] Example: set FACE_PYTHON=D:\anaconda3\envs\face_api\python.exe
  exit /b 1
)

echo ================================================
echo    face_api business-demo - Starting
echo ================================================
echo.
echo URL: http://localhost:%BUSINESS_DEMO_PORT%
echo FACE_API_BASE_URL=%FACE_API_BASE_URL%
echo FACE_PYTHON=%FACE_PYTHON%
echo.

if "%FACE_API_KEY%"=="" (
  echo [business-demo] WARN: FACE_API_KEY is empty. Calls to protected face_api routes may fail.
) else (
  echo [business-demo] FACE_API_KEY is set.
)

"%FACE_PYTHON%" -m uvicorn business_demo.app:app --host 0.0.0.0 --port %BUSINESS_DEMO_PORT%
