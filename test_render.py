#!/usr/bin/env python3
"""
Test script to verify Render deployment configuration
"""

import os
import sys

def test_render_config():
    """Test Render-specific configuration."""
    print("🧪 Testing Render Configuration")
    print("=" * 40)
    
    # Test environment detection
    render_env = os.environ.get('RENDER', 'false')
    print(f"RENDER environment: {render_env}")
    
    # Test database path
    if render_env == 'true':
        db_path = '/opt/render/project/src/drops.db'
        storage_path = '/opt/render/project/src/storage'
    else:
        db_path = 'drops.db'
        storage_path = 'storage'
    
    print(f"Database path: {db_path}")
    print(f"Storage path: {storage_path}")
    
    # Test directory creation
    try:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        os.makedirs(storage_path, exist_ok=True)
        print("✅ Directories created successfully")
    except Exception as e:
        print(f"❌ Directory creation failed: {e}")
        return False
    
    # Test database file creation
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS test (id INTEGER)')
        conn.commit()
        conn.close()
        print("✅ Database file created successfully")
    except Exception as e:
        print(f"❌ Database creation failed: {e}")
        return False
    
    print("\n🎉 Render configuration test passed!")
    return True

if __name__ == "__main__":
    success = test_render_config()
    sys.exit(0 if success else 1)
