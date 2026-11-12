@echo off
chcp 65001 >nul
title Pacman Capture the Flag - ApexPredators GUI Launcher
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel% neq 0 (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
) else (
    set "PYTHON_EXE=python"
)

:menu
cls
echo ========================================================
echo       PACMAN CAPTURE THE FLAG - APEXPREDATORS GUI
echo ========================================================
echo.
echo Kies een modus om te starten met de grafische GUI:
echo.
echo [1] ApexPredators (Rood) vs BaselineTeam (Blauw)  [Standaard]
echo [2] ApexPredators (Rood) vs HeuristicTeam (Blauw) [Sterkere tegenstander]
echo [3] ApexPredators vs ApexPredators                [Spiegelgevecht]
echo [4] Zelf spelen (Pijltjestoetsen) vs ApexPredators
echo [5] Willekeurige map (Random Layout)
echo [6] Vertraagd tempo (0.06s vertraging, makkelijker volgen)
echo [7] Eigen commando invoeren
echo [8] Afsluiten
echo.
set /p keuze="Maak een keuze [1-8]: "

if "%keuze%"=="1" goto match1
if "%keuze%"=="2" goto match2
if "%keuze%"=="3" goto match3
if "%keuze%"=="4" goto match4
if "%keuze%"=="5" goto match5
if "%keuze%"=="6" goto match6
if "%keuze%"=="7" goto match7
if "%keuze%"=="8" goto end
goto menu

:match1
echo.
echo Starten: ApexPredators vs BaselineTeam (Snel + Zoom 1.5)...
"%PYTHON_EXE%" capture.py -r ApexPredators -b baselineTeam -z 1.5 --delay-step 0.005
goto finish

:match2
echo.
echo Starten: ApexPredators vs HeuristicTeam (Snel + Zoom 1.5)...
"%PYTHON_EXE%" capture.py -r ApexPredators -b heuristicTeam -z 1.5 --delay-step 0.005
goto finish

:match3
echo.
echo Starten: ApexPredators vs ApexPredators (Snel + Zoom 1.5)...
"%PYTHON_EXE%" capture.py -r ApexPredators -b ApexPredators -z 1.5 --delay-step 0.005
goto finish

:match4
echo.
echo Starten: Jij (Rood, Agent 0 met pijltjestoetsen) vs ApexPredators...
"%PYTHON_EXE%" capture.py --keys0 -b ApexPredators -z 1.5 --delay-step 0.01
goto finish

:match5
echo.
echo Starten op een willekeurige map...
"%PYTHON_EXE%" capture.py -r ApexPredators -b baselineTeam -l RANDOM -z 1.5 --delay-step 0.005
goto finish

:match6
echo.
echo Starten op rustig tempo (--delay-step 0.06)...
"%PYTHON_EXE%" capture.py -r ApexPredators -b baselineTeam --delay-step 0.06
goto finish

:match7
echo.
echo Typ extra opties voor capture.py (bijv: -r ApexPredators -b simpleTeam -l officeCapture):
set /p custom_args="python capture.py "
"%PYTHON_EXE%" capture.py %custom_args%
goto finish

:finish
echo.
echo Wedstrijd afgelopen!
pause
goto menu

:end
exit
