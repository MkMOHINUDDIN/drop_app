#!/usr/bin/env python3
"""
Simple test script for the Send ↔ Receive Drop Service
"""

import requests
import time
import os
import tempfile

def test_application():
    """Test the basic functionality of the application."""
    base_url = "http://localhost:5000"
    
    print("🧪 Testing Send ↔ Receive Drop Service")
    print("=" * 50)
    
    try:
        # Test 1: Home page loads
        print("1. Testing home page...")
        response = requests.get(base_url)
        assert response.status_code == 200
        assert "Send ↔ Receive" in response.text
        print("   ✅ Home page loads successfully")
        
        # Test 2: Create a text-only drop
        print("2. Testing text-only drop creation...")
        data = {
            'text_content': 'Hello, this is a test message!'
        }
        response = requests.post(f"{base_url}/send", data=data)
        assert response.status_code == 200
        assert "Drop Created Successfully" in response.text
        print("   ✅ Text-only drop created successfully")
        
        # Test 3: Create a drop with a file
        print("3. Testing file upload...")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a test file content.")
            temp_file = f.name
        
        try:
            with open(temp_file, 'rb') as f:
                files = {'files': ('test.txt', f, 'text/plain')}
                data = {'text_content': 'File upload test'}
                response = requests.post(f"{base_url}/send", data=data, files=files)
                assert response.status_code == 200
                assert "Drop Created Successfully" in response.text
                print("   ✅ File upload successful")
        finally:
            os.unlink(temp_file)
        
        # Test 4: Test invalid code access
        print("4. Testing invalid code access...")
        response = requests.get(f"{base_url}/d/9999")
        assert response.status_code == 200
        assert "Drop Not Found" in response.text
        print("   ✅ Invalid code handling works")
        
        print("\n🎉 All tests passed! The application is working correctly.")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the application.")
        print("   Make sure the Flask app is running on http://localhost:5000")
        return False
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_application()
    exit(0 if success else 1)
