@echo off
chcp 65001 >nul 2>&1
echo ================================================
echo    Appium Server Startup Script (Windows)
echo ================================================
echo.

REM Check if Appium is installed
where appium >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Appium not found. Please install:
    echo    npm install -g appium@next
    echo.
    pause
    exit /b 1
)

REM Check Appium version
for /f "delims=" %%v in ('appium --version 2^>nul') do set "APPIUM_VERSION=%%v"
echo [INFO] Current Appium version: %APPIUM_VERSION%

REM Check version is 3.x
echo %APPIUM_VERSION% | findstr /C:"3." >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Detected Appium %APPIUM_VERSION%, NovaWindows Driver requires Appium 3.x
    echo    Please upgrade: npm install -g appium@next
    echo.
    echo Press any key to continue...
    pause >nul
)

REM Check if NovaWindows Driver is installed
appium driver list --installed | findstr /C:"novawindows" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [INFO] NovaWindows driver found
) else (
    echo [INFO] NovaWindows driver not found
)

echo.

REM Get port from config
set APPIUM_HOST=127.0.0.1
set APPIUM_PORT=4723

for /f "tokens=2 delims== " %%a in ('findstr /r "^appium_port " "config\env.ini" 2^>nul') do set APPIUM_PORT=%%a

echo [INFO] Appium server config:
echo    Host: %APPIUM_HOST%
echo    Port: %APPIUM_PORT%
echo.

REM Check if port is in use
netstat -ano | findstr ":%APPIUM_PORT% " >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [WARNING] Port %APPIUM_PORT% is in use, Appium may already be running
    echo    Verify at http://%APPIUM_HOST%:%APPIUM_PORT%/status
    echo    Press any key to continue...
    pause >nul
)

echo [INFO] Starting Appium server...
echo    Look for "Appium REST http interface listener started" message
echo    Verify at http://%APPIUM_HOST%:%APPIUM_PORT%/status
echo.

REM Start Appium
appium --address %APPIUM_HOST% --port %APPIUM_PORT% --log-level info --local-timezone

echo.
echo [INFO] Appium server stopped
pause