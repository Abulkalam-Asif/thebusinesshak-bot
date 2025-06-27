@echo off
title Web Automation Bot
color 0A

:menu
cls
echo.
echo  ================================================
echo  🤖 Web Automation Bot Control Panel
echo  ================================================
echo.
echo  1. Run Bot
echo  2. Show Status
echo  3. Update Configuration
echo  4. Add Target URL
echo  5. Add Search Keyword
echo  6. Test Proxies
echo  7. View Reports Folder
echo  8. View Logs
echo  9. Exit
echo.
set /p choice="Enter your choice (1-9): "

if "%choice%"=="1" goto run_bot
if "%choice%"=="2" goto show_status
if "%choice%"=="3" goto update_config
if "%choice%"=="4" goto add_url
if "%choice%"=="5" goto add_keyword
if "%choice%"=="6" goto test_proxies
if "%choice%"=="7" goto view_reports
if "%choice%"=="8" goto view_logs
if "%choice%"=="9" goto exit

echo Invalid choice. Please try again.
pause
goto menu

:run_bot
cls
echo Starting Web Automation Bot...
python bot.py
pause
goto menu

:show_status
cls
python manage.py status
pause
goto menu

:update_config
cls
python manage.py config
pause
goto menu

:add_url
cls
python manage.py add-url
pause
goto menu

:add_keyword
cls
python manage.py add-keyword
pause
goto menu

:test_proxies
cls
python manage.py test-proxies
pause
goto menu

:view_reports
cls
echo Opening reports folder...
start "" "%USERPROFILE%\Desktop\Bot_Reports"
goto menu

:view_logs
cls
echo Current log file contents:
echo ================================
type bot.log 2>nul || echo No log file found
echo ================================
pause
goto menu

:exit
echo.
echo Goodbye! 👋
timeout /t 2 >nul
exit
