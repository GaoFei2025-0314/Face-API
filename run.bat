@echo off
setlocal

cd /d "%~dp0"

echo ================================================
echo    Face Recognition API - Starting
echo ================================================
echo.
echo  URL:  http://localhost:8000
echo  Docs: http://localhost:8000/docs
echo  Test: double click test.html
echo.
echo  Press Ctrl+C to stop
echo ================================================
echo.

call conda activate face_api
if errorlevel 1 (
    echo [ERROR] Failed to activate conda env "face_api"
    echo Please run setup.bat first to create the environment.
    pause
    exit /b 1
)

if "%FACE_ENV%"=="" set FACE_ENV=development

if "%FACE_API_KEY%"=="" (
    echo [WARN] FACE_API_KEY is empty. Admin/auth/liveness APIs will reject requests.
) else (
    echo [OK] FACE_API_KEY is set.
)

uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
