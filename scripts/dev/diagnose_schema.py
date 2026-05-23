import json
import os
import sys
from pathlib import Path

# Add backend directory to python path
current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir))

from backend.app import app


def diagnose():
    try:
        print("Attempting to generate OpenAPI schema...")
        schema = app.openapi()
        print("Schema generated successfully!")
        with open("openapi_debug.json", "w") as f:
            json.dump(schema, f, indent=2)
        print("Schema saved to openapi_debug.json")
    except Exception as e:
        print("Error generating schema:")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    diagnose()
