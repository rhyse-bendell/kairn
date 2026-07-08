@echo off
setlocal

REM Run from the directory where this batch file lives.
pushd "%~dp0" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Could not switch to the Kairn repository directory.
    pause
    exit /b 1
)

echo ========================================
echo Kairn Windows GUI launcher
echo Repository: %CD%
echo ========================================
echo.

if not exist "pyproject.toml" (
    echo ERROR: pyproject.toml was not found in %CD%.
    echo Please run this launcher from the Kairn repository root.
    goto fail
)

if not exist "src\kairn" (
    echo ERROR: src\kairn was not found in %CD%.
    echo Please run this launcher from the Kairn repository root.
    goto fail
)

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python was not found on PATH.
    echo Install Python 3, then open a new Command Prompt and try again.
    goto fail
)

python --version
if errorlevel 1 (
    echo ERROR: Python is installed but could not be run.
    goto fail
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment in .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create .venv.
        goto fail
    )
) else (
    echo Using existing .venv.
)

echo Activating virtual environment ...
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Failed to activate .venv.
    goto fail
)

echo Upgrading pip ...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo ERROR: Failed to upgrade pip.
    goto fail
)

echo Installing Kairn with GUI extras ...
pip install -e ".[gui]"
if errorlevel 1 (
    echo ERROR: Failed to install Kairn with GUI extras.
    goto fail
)

if not exist "kairn_workspace" (
    echo Creating kairn_workspace ...
    mkdir "kairn_workspace"
    if errorlevel 1 (
        echo ERROR: Failed to create kairn_workspace.
        goto fail
    )
) else (
    echo Using existing kairn_workspace.
)

echo Running lightweight import check ...
python -c "import kairn; import kairn.apps.desktop.main; print('Kairn import check passed.')"
if errorlevel 1 (
    echo ERROR: Kairn import check failed.
    goto fail
)

echo Checking kairn --help ...
kairn --help >nul 2>&1
if errorlevel 1 (
    echo WARNING: kairn --help failed; continuing to GUI launch.
) else (
    echo kairn --help passed.
)

echo.
echo Launching Kairn GUI ...
kairn-gui
set "KAIRN_GUI_EXIT=%ERRORLEVEL%"
echo.
echo Kairn GUI exited with code %KAIRN_GUI_EXIT%.
goto done

:fail
echo.
echo Setup failed. Please review the error above.
set "KAIRN_GUI_EXIT=1"
goto done

:done
echo.
echo Press any key to close this window.
pause >nul
popd >nul 2>&1
endlocal
exit /b %KAIRN_GUI_EXIT%
