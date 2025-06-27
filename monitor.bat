@echo off
title Bot Progress Monitor
color 0B

echo Starting Bot Progress Monitor...
echo.

python monitor.py

if %errorlevel% neq 0 (
    echo.
    echo Error running monitor. Make sure Python is installed.
    pause
)
