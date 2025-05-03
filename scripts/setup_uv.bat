@echo off
REM Setup script for uv package manager on Windows

REM Check if uv is installed
where uv >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo uv is not installed. Installing...
    pip install uv
) else (
    echo uv is already installed.
)

REM Create virtual environment if it doesn't exist
if not exist .venv (
    echo Creating virtual environment...
    uv venv
) else (
    echo Virtual environment already exists.
)

REM Install dependencies
echo Installing dependencies...
uv pip install -r requirements.txt

REM Install development dependencies
echo Installing development dependencies...
uv pip install -r requirements-dev.txt

REM Install the package in development mode
echo Installing package in development mode...
uv pip install -e .

echo Setup complete! Activate the virtual environment with:
echo .venv\Scripts\activate.bat 