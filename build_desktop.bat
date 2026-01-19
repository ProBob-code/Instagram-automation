@echo off
echo ================================================
echo   IG Growth Hub - Desktop App Builder
echo ================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if pyinstaller is installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Check if waitress is installed (for production server)
pip show waitress >nul 2>&1
if errorlevel 1 (
    echo Installing waitress (production server)...
    pip install waitress
)

REM Install all requirements
echo Installing dependencies...
pip install -r requirements.txt

REM Install playwright browsers
echo Installing Playwright browsers...
playwright install chromium

REM Build the application
echo.
echo Building IG Growth Hub Desktop App...
echo This may take a few minutes...
echo.

pyinstaller ig_growth_hub.spec --clean

if errorlevel 1 (
    echo.
    echo BUILD FAILED! Check errors above.
    pause
    exit /b 1
)

echo.
echo ================================================
echo   BUILD SUCCESSFUL!
echo ================================================
echo.
echo Your app is in: dist\IG_Growth_Hub\
echo Run: dist\IG_Growth_Hub\IG_Growth_Hub.exe
echo.
pause
