#!/usr/bin/env python3
"""Test if all imports work correctly."""

try:
    print("Testing imports...")
    
    # Core imports
    from app.core.config import settings
    print("✓ Config imported")
    
    # Database imports
    from app.db.base import Base, engine, get_db
    print("✓ Database base imported")
    
    # Model imports
    from app.models import *
    print("✓ All models imported")
    
    # API imports
    from app.main import app
    print("✓ FastAPI app imported")
    
    print("\nAll imports successful!")
    
except Exception as e:
    print(f"\n✗ Import failed: {e}")
    import traceback
    traceback.print_exc()