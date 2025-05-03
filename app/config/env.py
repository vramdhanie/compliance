import os
from pathlib import Path
from dotenv import load_dotenv


def load_environment():
    """
    Load environment variables from .env file
    """
    # Get the root directory of the project
    root_dir = Path(__file__).parent.parent.parent
    
    # Path to .env file
    env_path = root_dir / ".env"
    
    # Load environment variables from .env file if it exists
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print(f"Loaded environment from {env_path}")
    else:
        print("No .env file found, using default environment variables") 