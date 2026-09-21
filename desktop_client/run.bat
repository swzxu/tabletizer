@echo off
title tabletizer!
cd /d "%~dp0"

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3 is not found in PATH!
    echo Please install Python 3 from https://www.python.org/downloads/
    pause
    exit /b
)

:: Run the application
python main.py
if %errorlevel% neq 0 (
    pause
)
