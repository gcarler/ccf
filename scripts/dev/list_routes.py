import sys
from pathlib import Path

# Add backend directory to python path
current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir))

from backend.app import app

print("Listing all registered routes matching 'project' in app:")
for route in app.routes:
    if "project" in route.path.lower():
        methods = getattr(route, "methods", None)
        print(f"Path: {route.path} | Methods: {methods}")
