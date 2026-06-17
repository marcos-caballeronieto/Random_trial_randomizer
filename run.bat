@echo off
setlocal enabledelayedexpansion
title Clinical Trial Randomizer Engine

:: Navigate to directory of the batch file
cd /d "%~dp0"

echo ====================================================================
echo 🧬  CLINICAL TRIAL RANDOMIZER ENGINE
echo ====================================================================
echo.

:: Check for virtual environment folder
if exist "venv" goto ACTIVATE_VENV

echo [WARNING] Virtual environment 'venv' not found in this folder.
set /p CREATE_VENV="Would you like to automatically create 'venv' and install requirements? (Y/N): "
if /i "%CREATE_VENV%"=="Y" goto CREATE_VENV
if /i "%CREATE_VENV%"=="yes" goto CREATE_VENV
echo [INFO] Proceeding without virtual environment. Using system Python.
echo.
goto MENU

:CREATE_VENV
echo.
echo [INFO] Checking if Python is installed...
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found in your system PATH.
    echo Please install Python (3.9+) and try again.
    pause
    exit /b 1
)
echo [INFO] Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)
echo [INFO] Virtual environment created successfully.
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat
echo [INFO] Installing required dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [SUCCESS] Dependencies installed successfully.
echo.
pause
goto MENU

:ACTIVATE_VENV
echo [INFO] Found virtual environment 'venv'. Activating...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [WARNING] Failed to activate virtual environment.
)
echo.
goto MENU

:MENU
cls
echo ====================================================================
echo 🧬  CLINICAL TRIAL RANDOMIZER ENGINE - MAIN MENU
echo ====================================================================
echo.
echo   [1] Launch Interactive Web Dashboard (Streamlit UI)
echo   [2] Execute Command Line Engine (CLI)
echo   [3] Install/Update Python Dependencies
echo   [4] Exit
echo.
echo ====================================================================
set CHOICE=
set /p CHOICE="Enter choice (1-4): "

if "%CHOICE%"=="1" goto STREAMLIT
if "%CHOICE%"=="2" goto CLI
if "%CHOICE%"=="3" goto DEPS
if "%CHOICE%"=="4" goto EXIT
goto MENU

:STREAMLIT
cls
echo ====================================================================
echo 🧬  LAUNCHING INTERACTIVE WEB DASHBOARD (STREAMLIT UI)
echo ====================================================================
echo.
echo Running 'streamlit run app.py'...
echo Press Ctrl+C in this window to stop the dashboard server.
echo.
streamlit run app.py
echo.
echo Dashboard stopped.
pause
goto MENU

:CLI
cls
echo ====================================================================
echo 🧬  EXECUTE COMMAND LINE ENGINE (CLI)
echo ====================================================================
echo.
echo Press ENTER to accept the default values in brackets.
echo.

set INPUT_FILE=patients_raw.csv
set /p INPUT_FILE="Input CSV file [%INPUT_FILE%]: "

set OUTPUT_FILE=randomized_cohort.csv
set /p OUTPUT_FILE="Output CSV file [%OUTPUT_FILE%]: "

set STRATA_COLS=Sex,Age_Group
set /p STRATA_COLS="Stratification Covariates [%STRATA_COLS%]: "

set BLOCK_SIZE=4
set /p BLOCK_SIZE="Permuted Block Size [%BLOCK_SIZE%]: "

set RANDOM_SEED=42
set /p RANDOM_SEED="Random Seed [%RANDOM_SEED%]: "

echo.
echo Running Engine CLI...
echo python main.py --input "%INPUT_FILE%" --output "%OUTPUT_FILE%" --strata "%STRATA_COLS%" --block-size %BLOCK_SIZE% --seed %RANDOM_SEED%
echo.

python main.py --input "%INPUT_FILE%" --output "%OUTPUT_FILE%" --strata "%STRATA_COLS%" --block-size %BLOCK_SIZE% --seed %RANDOM_SEED%

echo.
pause
goto MENU

:DEPS
cls
echo ====================================================================
echo 🧬  UPDATING PYTHON DEPENDENCIES
echo ====================================================================
echo.
echo Upgrading pip and running 'pip install -r requirements.txt'...
echo.
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo Dependencies update complete.
pause
goto MENU

:EXIT
echo.
echo Goodbye!
endlocal
exit /b 0
