@echo off
echo Installing Web Automation Bot...
echo.

echo Checking Python installation...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo.
echo Installing Python packages...
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo ERROR: Failed to install Python packages
    pause
    exit /b 1
)

echo.
echo Installing Playwright browsers...
python -m playwright install

if %errorlevel% neq 0 (
    echo ERROR: Failed to install Playwright browsers
    pause
    exit /b 1
)

echo.
echo ✓ Installation completed successfully!
echo.
echo To run the bot, use: python bot.py
echo.
pause
