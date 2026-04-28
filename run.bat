@echo off
chcp 65001 >nul

REM ============================================================
REM 人脸识别 API - 启动脚本（conda 版）
REM 适用环境：conda env name = face_api
REM ============================================================

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

REM 激活 conda 环境
call conda activate face_api
if errorlevel 1 (
    echo [ERROR] Failed to activate conda env "face_api"
    echo Please run setup.bat first to create the environment.
    pause
    exit /b 1
)

REM 可选：启用 API Key 鉴权（取消下一行注释并设置密钥）
REM set FACE_API_KEY=your-secret-key-here

REM 启动服务（开发模式，带热重载）
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

REM 生产模式：4 worker（你的 i9-7940X + 128GB 内存可承载）
REM uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

pause
