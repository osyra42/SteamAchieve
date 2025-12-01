@echo off
title Steam Achievement Tracker

:: Change to the directory where this batch file is located
cd /d "%~dp0"

echo ========================================
echo   Steam Achievement Tracker Launcher
echo ========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

:: Create venv if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate the virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

:: Check if pip dependencies are installed
echo [1/2] Checking dependencies...
pip show flask >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
)

:: Check for .env file
if not exist ".env" (
    echo.
    echo ========================================
    echo   WARNING: .env file not found!
    echo ========================================
    echo.
    echo Please create a .env file with:
    echo   FLASK_SECRET_KEY=your-secret-key-here
    echo   STEAM_API_KEY=your-steam-api-key-here
    echo.
    echo Get your Steam API key from:
    echo   https://steamcommunity.com/dev/apikey
    echo.
    pause
    exit /b 1
)

:: Start Flask app
echo [2/2] Starting Flask server...
echo.
echo ========================================
echo   App running at: http://localhost:5000
echo   Press Ctrl+C to stop
echo ========================================
echo.

:: Open browser after short delay
start /B cmd /c "timeout /t 2 >nul && start http://localhost:5000"

:: Run Flask
python app.py

pause
