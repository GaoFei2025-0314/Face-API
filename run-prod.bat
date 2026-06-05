@echo off
setlocal

cd /d "%~dp0"

if "%FACE_ENV%"=="" set FACE_ENV=production
if "%FACE_LOG_PATH%"=="" set FACE_LOG_PATH=logs\face_api.log

echo [face_api] production startup
echo [face_api] FACE_ENV=%FACE_ENV%
echo [face_api] FACE_USE_GPU=%FACE_USE_GPU%
echo [face_api] FACE_FORCE_CPU=%FACE_FORCE_CPU%
echo [face_api] FACE_DB_PATH=%FACE_DB_PATH%
echo [face_api] FACE_LOG_PATH=%FACE_LOG_PATH%

if "%FACE_API_KEY%"=="" (
  echo [face_api] ERROR: production mode requires FACE_API_KEY
  exit /b 1
)

echo [face_api] FACE_API_KEY is set.

for /f "tokens=5" %%p in ('netstat -ano ^| findstr /R /C:":8000 .*LISTENING"') do (
  echo [face_api] ERROR: port 8000 is already in use by PID %%p
  echo [face_api] Run: powershell -ExecutionPolicy Bypass -File scripts\stop-service.ps1
  exit /b 1
)

D:\anaconda3\envs\face_api\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
