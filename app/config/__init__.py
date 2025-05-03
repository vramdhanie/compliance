import os
from typing import Dict, Any
from app.config.env import load_environment

# Load environment variables from .env file
load_environment()

# Database configuration
DATABASE_CONFIG = {
    "uri": os.environ.get("MONGO_URI", "mongodb://localhost:27017"),
    "database": os.environ.get("MONGO_DB", "compliance_db"),
}

# Application configuration
APP_CONFIG = {
    "debug": os.environ.get("DEBUG", "False").lower() == "true",
    "environment": os.environ.get("ENVIRONMENT", "development"),
}


def get_config() -> Dict[str, Any]:
    """
    Get the full application configuration
    
    Returns:
        Dict[str, Any]: The application configuration
    """
    return {
        "database": DATABASE_CONFIG,
        "app": APP_CONFIG,
    } 