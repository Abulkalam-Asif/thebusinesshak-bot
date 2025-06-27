@echo off
title Web Automation Bot
color 0A

:menu
cls
echo.
echo  ================================================
echo  🤖 Web Automation Bot
echo  ================================================
echo.
echo  1. Run Bot (Visible Mode)
echo  2. Run Bot (Headless Mode)
echo  3. Exit
echo.
set /p choice="Enter your choice (1-3): "

if "%choice%"=="1" goto run_bot_visible
if "%choice%"=="2" goto run_bot_headless
if "%choice%"=="3" goto exit

echo Invalid choice. Please try again.
pause
goto menu

:run_bot_visible
cls
echo Starting Web Automation Bot in VISIBLE MODE...
echo Browser windows will be visible for monitoring
python bot.py
if %errorlevel% neq 0 (
    echo.
    echo ❌ Bot stopped with error. Check the logs for details.
    pause
)
goto menu

:run_bot_headless
cls
echo Starting Web Automation Bot in HEADLESS MODE...
echo Browser will run in background (not visible)
python bot.py --headless
if %errorlevel% neq 0 (
    echo.
    echo ❌ Bot stopped with error. Check the logs for details.
    pause
)
goto menu

:exit
echo.
echo Goodbye! 👋
timeout /t 2 >nul
exit
