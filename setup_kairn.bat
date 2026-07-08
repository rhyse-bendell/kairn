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
call :log "Script=setup_kairn.bat"

echo ========================================
echo Kairn Windows setup/update
echo Repository: %APP_ROOT%
echo ========================================
echo.

if not exist "pyproject.toml" (
    echo [Kairn] pyproject.toml was not found in %APP_ROOT%.
    call :log "Missing pyproject.toml"
    goto fail
)

if not exist "src\kairn" (
    echo [Kairn] src\kairn was not found in %APP_ROOT%.
    call :log "Missing src\kairn"
    goto fail
)

set "SYSTEM_PYTHON="
where py >nul 2>&1
if not errorlevel 1 set "SYSTEM_PYTHON=py"
if not defined SYSTEM_PYTHON (
    where python >nul 2>&1
    if not errorlevel 1 set "SYSTEM_PYTHON=python"
)
if not defined SYSTEM_PYTHON (
    echo [Kairn] Python was not found. Install Python 3, then run setup_kairn.bat again.
    call :log "System Python missing"
    goto fail
)
call :log "SYSTEM_PYTHON=%SYSTEM_PYTHON%"

if not exist "%APP_ROOT%\.venv\Scripts\python.exe" (
    echo [Kairn] Creating virtual environment in .venv ...
    call :log "Creating .venv"
    %SYSTEM_PYTHON% -m venv .venv
    if errorlevel 1 (
        echo [Kairn] Failed to create .venv.
        call :log "venv creation failed"
        goto fail
    )
) else (
    echo [Kairn] Using existing .venv.
    call :log "Using existing .venv"
)

set "PYTHON_CMD=%APP_ROOT%\.venv\Scripts\python.exe"
call :log "PYTHON_CMD=%PYTHON_CMD%"

if not exist "%PYTHON_CMD%" (
    echo [Kairn] .venv Python was not found after setup.
    call :log ".venv Python missing after setup"
    goto fail
)

echo [Kairn] Upgrading pip ...
call :log "Upgrading pip"
"%PYTHON_CMD%" -m pip install --upgrade pip
if errorlevel 1 (
    echo [Kairn] Failed to upgrade pip.
    call :log "pip upgrade failed"
    goto fail
)

echo [Kairn] Installing Kairn with GUI extras ...
call :log "Installing Kairn with GUI extras"
"%PYTHON_CMD%" -m pip install -e ".[gui]"
if errorlevel 1 (
    echo [Kairn] Failed to install Kairn with GUI extras.
    call :log "package install failed"
    goto fail
)

echo [Kairn] Running import check ...
call :log "Running import check"
"%PYTHON_CMD%" -c "import kairn; import kairn.apps.desktop.main; print('[Kairn] Import check passed.')"
if errorlevel 1 (
    echo [Kairn] Import check failed.
    call :log "Import check failed"
    goto fail
)

echo [Kairn] Checking CLI help ...
call :log "Checking CLI help"
"%PYTHON_CMD%" -m kairn.cli.main --help >nul 2>&1
if errorlevel 1 (
    echo [Kairn] CLI help check was skipped or unavailable; continuing.
    call :log "CLI help check unavailable"
) else (
    echo [Kairn] CLI help check passed.
    call :log "CLI help check passed"
)

if /I "%~1"=="--test" (
    echo [Kairn] Running tests ...
    call :log "Running pytest"
    "%PYTHON_CMD%" -m pytest -q
    if errorlevel 1 (
        echo [Kairn] Tests failed.
        call :log "pytest failed"
        goto fail
    )
)

echo.
echo [Kairn] Setup complete. You can now run launch_kairn_gui.bat.
call :log "Setup complete"
call :log "Exit code=0"
endlocal & exit /b 0

:fail
echo.
echo [Kairn] Setup failed. Please review the error above.
call :log "Exit code=1"
pause
endlocal & exit /b 1

:log
>> "%LOG_FILE%" echo [%DATE% %TIME%][Kairn][setup] %~1
exit /b 0
