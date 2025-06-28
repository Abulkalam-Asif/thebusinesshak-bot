@echo off
echo Installing Web Automation Bot...
echo.

REM Remove existing venv if it exists to start fresh
if exist venv (
    echo Removing existing virtual environment...
    rmdir /s /q venv
)

echo Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment
    echo Please ensure Python 3.8+ is installed from https://python.org
    pause
    exit /b 1
)

echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

echo.
echo Checking Python installation in virtual environment...
venv\Scripts\python.exe --version
if %errorlevel% neq 0 (
    echo ERROR: Python is not working in virtual environment
    pause
    exit /b 1
)

echo.
echo Upgrading pip...
venv\Scripts\python.exe -m pip install --upgrade pip

echo.
echo Installing Python packages...
venv\Scripts\python.exe -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo ERROR: Failed to install Python packages
    pause
    exit /b 1
)

echo.
echo Installing Playwright browsers...
venv\Scripts\python.exe -m playwright install

if %errorlevel% neq 0 (
    echo ERROR: Failed to install Playwright browsers
    pause
    exit /b 1
)

echo.
echo ✓ Installation completed successfully!
echo.
echo To run the bot:
echo 1. Run start.bat for guided options
echo 2. Or use: venv\Scripts\python.exe bot.py
echo.
pause
