#!/bin/bash
# Setup script for type checking tools

# Source virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Install mypy and plugins
echo "Installing mypy and plugins..."
pip install mypy==1.7.1
pip install mypy-extensions==1.0.0
pip install typing-extensions>=4.8.0

# Create a mypy.ini file if it doesn't exist
if [ ! -f "mypy.ini" ]; then
    echo "Creating mypy.ini file..."
    cat > mypy.ini << EOL
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = False
disallow_incomplete_defs = False
plugins = pydantic.mypy

[mypy.plugins.numpy.*]
follow_imports = skip

[mypy-pymongo.*]
ignore_missing_imports = True

[mypy-bson.*]
ignore_missing_imports = True

[mypy-pytest.*]
ignore_missing_imports = True

[mypy-dotenv.*]
ignore_missing_imports = True

[mypy-pydantic.*]
ignore_missing_imports = True
EOL
fi

echo "Type checking setup complete!"
echo "Run 'mypy app' to type check your code." 