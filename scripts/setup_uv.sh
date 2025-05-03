#!/bin/bash
# Setup script for uv package manager

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Installing..."
    pip install uv
else
    echo "uv is already installed."
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
else
    echo "Virtual environment already exists."
fi

# Install dependencies
echo "Installing dependencies..."
uv pip install -r requirements.txt

# Install development dependencies
echo "Installing development dependencies..."
uv pip install -r requirements-dev.txt

# Install the package in development mode
echo "Installing package in development mode..."
uv pip install -e .

echo "Setup complete! Activate the virtual environment with:"
echo "source .venv/bin/activate" 