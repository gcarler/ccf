import os
import sys

# Add parent directory to sys.path to allow importing from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.config import get_settings

settings = get_settings()
print(f"DATABASE_URL: {settings.database_url}")
