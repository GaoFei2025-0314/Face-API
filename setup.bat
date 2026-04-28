@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ================================================
echo    Face API - Setup
echo ================================================
echo.

REM ============================================================
REM Python path (modify if needed)
REM ============================================================
set PYTHON_EXE=D:\dev\python3.1\python.exe

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python not found: %PYTHON_EXE%
    echo Please edit setup.bat and modify PYTHON_EXE
    echo.
    pause
    exit /b 1
)

echo [1/5] Python: %PYTHON_EXE%
"%PYTHON_EXE%" --version
echo.

REM ============================================================
REM Create venv
REM ============================================================
if exist "venv\Scripts\activate.bat" (
    echo [2/5] venv already exists, skipping
) else (
    echo [2/5] Creating venv...
    "%PYTHON_EXE%" -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv
        pause
        exit /b 1
    )
)
echo.

REM ============================================================
REM Activate venv
REM ============================================================
echo [3/5] Activating venv...
call "venv\Scripts\activate.bat"
echo.

REM ============================================================
REM Upgrade pip
REM ============================================================
echo [4/5] Upgrading pip...
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
echo.

REM ============================================================
REM Install dependencies
REM ============================================================
echo [5/5] Installing dependencies (1-2GB, takes 5-15 min)...
echo.
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo.

echo ================================================
echo  Setup completed
echo ================================================
echo.

REM ============================================================
REM Verify GPU
REM ============================================================
echo Verifying GPU support...
python -c "import onnxruntime as ort; ps = ort.get_available_providers(); print('Providers:', ps); print('[OK] GPU available' if 'CUDAExecutionProvider' in ps else '[WARN] CPU only')"
echo.
echo ================================================
echo  Next: double-click run.bat to start the service
echo ================================================
echo.

pause
