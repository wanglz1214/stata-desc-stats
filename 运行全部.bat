@echo off
chcp 65001 >nul
cd /d "%~dp0"
setlocal enabledelayedexpansion

REM ===========================================================
REM  Double-click this file to run all 4 analysis scripts.
REM  It does NOT contain any Chinese text on purpose:
REM  ASCII-only .bat files never break due to encoding issues.
REM ===========================================================

set "PY=C:\Users\14568\.workbuddy\binaries\python\versions\3.13.12\python.exe"
if exist "%PY%" goto :havepy
where py >nul 2>nul
if not errorlevel 1 (
    set "PY=py -3"
    goto :havepy
)
set "PY=python"

:havepy
echo.
echo Using Python: %PY%
%PY% -c "import pandas" >nul 2>nul
if errorlevel 1 (
    echo.
    echo [ERROR] pandas is not installed for this Python.
    echo Please install it first:
    echo     %PY% -m pip install -i https://pypi.org/simple pandas numpy pyreadstat matplotlib openpyxl scipy
    echo.
    pause
    exit /b 1
)

for %%p in (01 02 03 04) do (
    for %%f in (%%p_*.py) do (
        echo.
        echo ==========================================================
        echo  RUNNING: %%~nxf
        echo ==========================================================
        %PY% "%%~ff"
        if errorlevel 1 (
            echo.
            echo [ERROR] %%~nxf failed. Read the message above.
            pause
            exit /b 1
        )
        echo.
        echo ------ OK: %%~nxf
    )
)

echo.
echo ==========================================================
echo  ALL DONE. Results are in the folder: %~dp0
echo  Look for the sub-folder that holds the tables and figures.
echo ==========================================================
echo.
pause
