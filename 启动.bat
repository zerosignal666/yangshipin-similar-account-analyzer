@echo off
cd /d "%~dp0"

REM Find Python - try known paths first, skip Microsoft Store redirect
set "PY="
if exist "C:\Users\%USERNAME%\AppData\Local\Python\pythoncore-3.14-64\python.exe" set "PY=C:\Users\%USERNAME%\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if "%PY%"=="" if exist "C:\Users\%USERNAME%\AppData\Local\Python\pythoncore-3.13-64\python.exe" set "PY=C:\Users\%USERNAME%\AppData\Local\Python\pythoncore-3.13-64\python.exe"
if "%PY%"=="" if exist "C:\Users\%USERNAME%\AppData\Local\Python\pythoncore-3.12-64\python.exe" set "PY=C:\Users\%USERNAME%\AppData\Local\Python\pythoncore-3.12-64\python.exe"
if "%PY%"=="" (
    for /f "tokens=*" %%p in ('where python 2^>nul ^| findstr /v /i "WindowsApps"') do (
        if exist "%%p" set "PY=%%p"
    )
)
if "%PY%"=="" (
    for /f "tokens=*" %%p in ('where python3 2^>nul ^| findstr /v /i "WindowsApps"') do (
        if exist "%%p" set "PY=%%p"
    )
)
if "%PY%"=="" (
    echo [ERROR] Python not found.
    echo Install Python 3.11+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python: "%PY%"
echo.

REM Check deps
"%PY%" -c "import tkinter,httpx,bs4,pandas,matplotlib,seaborn" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    "%PY%" -m pip install httpx beautifulsoup4 lxml pandas numpy matplotlib seaborn openpyxl -q --disable-pip-version-check
    if errorlevel 1 (
        echo [ERROR] Install failed. Run: pip install httpx beautifulsoup4 lxml pandas numpy matplotlib seaborn openpyxl
        pause
        exit /b 1
    )
    echo Done.
    echo.
)

echo Starting YSP Analyzer...
"%PY%" main.py
pause
