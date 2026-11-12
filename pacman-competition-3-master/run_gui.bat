@echo off
cd /d "%~dp0"
echo ========================================================
echo   Starting Pacman Capture the Flag GUI (ApexPredators)
echo ========================================================
echo.
where python >nul 2>nul
if %errorlevel% neq 0 (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
) else (
    set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" capture.py -r ApexPredators -b baselineTeam -z 1.5 --delay-step 0.005
pause
