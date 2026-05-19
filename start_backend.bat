@echo off
echo ========================================
echo   AI Platform - Backend Server
echo ========================================
echo.

cd /d "%~dp0backend"

py --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)
py --version

echo.
echo [1/3] Installing dependencies...
py -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ERROR] pip install failed
    pause
    exit /b 1
)
echo        Done

echo.
echo [2/3] Checking database...
py database_setup.py --check
if errorlevel 1 (
    echo.
    echo [ERROR] Database connection failed
    echo         Make sure MySQL is running
    echo         Run: py database_setup.py   to init database
    echo.
    pause
    exit /b 1
)

echo.
echo [3/3] Starting server...
echo.
echo   API Docs: http://127.0.0.1:8050/docs
echo   Health:   http://127.0.0.1:8050/health
echo.
echo   Press Ctrl+C to stop
echo ========================================
echo.

py main.py

echo.
echo Server stopped.
pause
