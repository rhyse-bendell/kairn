@echo off
setlocal

for %%I in ("%~dp0.") do set "APP_ROOT=%%~fI"
cd /d "%APP_ROOT%" >nul 2>&1
if errorlevel 1 (
    echo [Kairn] Could not switch to the Kairn repository directory.
    pause
    exit /b 1
)

if not exist "logs" mkdir "logs" >nul 2>&1
set "LOG_FILE=%APP_ROOT%\logs\launcher.log"
call :log "APP_ROOT=%APP_ROOT%"
call :log "Script=launch_kairn_gui.bat"

echo ========================================
echo Kairn Windows GUI launcher
echo Repository: %APP_ROOT%
echo ========================================
echo.

if not exist "pyproject.toml" (
    echo [Kairn] pyproject.toml was not found in %APP_ROOT%.
    call :log "Missing pyproject.toml"
    pause
    exit /b 1
)

if not exist "src\kairn\apps\desktop\main.py" (
    echo [Kairn] src\kairn\apps\desktop\main.py was not found in %APP_ROOT%.
    call :log "Missing src\kairn\apps\desktop\main.py"
    pause
    exit /b 1
)

set "PYTHON_CMD=%APP_ROOT%\.venv\Scripts\python.exe"
call :log "PYTHON_CMD=%PYTHON_CMD%"

if not exist "%PYTHON_CMD%" (
    echo [Kairn] .venv was not found. Run setup_kairn.bat first.
    call :log ".venv Python missing"
    pause
    exit /b 1
)

echo [Kairn] Running lightweight import check...
call :log "Running import check"
"%PYTHON_CMD%" -c "import kairn; import kairn.apps.desktop.main; print('[Kairn] Import check passed.')"
if errorlevel 1 (
    echo [Kairn] Dependencies are missing or stale. Run setup_kairn.bat, then launch again.
    call :log "Import check failed"
    pause
    exit /b 1
)

echo [Kairn] Starting GUI...
call :log "Starting GUI"
"%PYTHON_CMD%" -m kairn.apps.desktop.main
set "KAIRN_GUI_EXIT=%ERRORLEVEL%"
call :log "Exit code=%KAIRN_GUI_EXIT%"

if not "%KAIRN_GUI_EXIT%"=="0" (
    echo.
    echo [Kairn] Launch failed with exit code %KAIRN_GUI_EXIT%.
    echo Try running setup_kairn.bat, then launch again.
    pause
)

endlocal & exit /b %KAIRN_GUI_EXIT%

:log
>> "%LOG_FILE%" echo [%DATE% %TIME%][Kairn][launch] %~1
exit /b 0
