@echo off
title Hand Gesture Control (DO NOT CLOSE)
echo.
echo ========================================================
echo   HAND GESTURE CONTROL APPLICATION
echo ========================================================
echo.
echo   1. Starting backend server...
echo   2. Browser will open automatically...
echo.
echo   [ NOTE ] To STOP the app, simply CLOSE this window.
echo.

:: Open browser in a separate non-blocking process after a short delay
start "" /B cmd /c "timeout /t 4 /nobreak >nul & start http://localhost:5000"

:: Start the server (This keeps the window open)
py -3.11 server.py

:: If it crashes, pause to show error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] The server crashed or failed to start.
    pause
)
