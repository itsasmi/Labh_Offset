@echo off
title Labh Offset Server
echo ========================================
echo   LABH OFFSET - MANAGEMENT SYSTEM
echo ========================================
echo.
echo Starting server...
echo.
echo [STEP 1] Checking dependencies...
pip install -r requirements.txt >nul 2>&1

echo [STEP 2] Opening browser to http://localhost:8000
start http://localhost:8000

echo [STEP 3] Launching Backend...
echo.
echo ----------------------------------------
echo KEEP THIS WINDOW OPEN while using the app.
echo To STOP the server, simply CLOSE this window.
echo ----------------------------------------
echo.
python main.py

pause
