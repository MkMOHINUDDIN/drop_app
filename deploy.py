#!/usr/bin/env python3
"""
Deployment helper script for Send ↔ Receive Drop Service
"""

import os
import sys
import subprocess
import secrets

def generate_secret_key():
    """Generate a secure secret key."""
    return secrets.token_hex(32)

def setup_environment():
    """Set up environment variables for production."""
    env_file = ".env"
    
    if not os.path.exists(env_file):
        print("🔧 Creating .env file with production settings...")
        
        with open(env_file, 'w') as f:
            f.write(f"SECRET_KEY={generate_secret_key()}\n")
            f.write("MAX_CONTENT_LENGTH_MB=400\n")
            f.write("DROP_EXPIRY_HOURS=24\n")
            f.write("DATABASE_PATH=drops.db\n")
            f.write("STORAGE_PATH=storage\n")
        
        print(f"   ✅ Created {env_file}")
    else:
        print(f"   ℹ️  {env_file} already exists")

def install_dependencies():
    """Install Python dependencies."""
    print("📦 Installing dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True)
        print("   ✅ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Failed to install dependencies: {e}")
        return False
    return True

def create_directories():
    """Create necessary directories."""
    print("📁 Creating directories...")
    directories = ["storage", "templates"]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"   ✅ Created {directory}/")
        else:
            print(f"   ℹ️  {directory}/ already exists")

def run_tests():
    """Run basic tests."""
    print("🧪 Running tests...")
    try:
        result = subprocess.run([sys.executable, "test_app.py"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("   ✅ All tests passed")
            return True
        else:
            print(f"   ❌ Tests failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ Could not run tests: {e}")
        return False

def main():
    """Main deployment setup."""
    print("🚀 Setting up Send ↔ Receive Drop Service")
    print("=" * 50)
    
    # Setup steps
    setup_environment()
    create_directories()
    
    if not install_dependencies():
        print("❌ Setup failed at dependency installation")
        return False
    
    print("\n✅ Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Run the application: python app.py")
    print("2. Open your browser to: http://localhost:5000")
    print("3. For production deployment, see README.md")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
