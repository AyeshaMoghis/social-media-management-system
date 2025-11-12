#!/usr/bin/env python3
"""
Setup Verification Script for SMMS Tests
Run this to verify your test environment is correctly configured
"""
import os
import sys

def print_header(text):
    """Print formatted header"""
    print(f"\n{'='*50}")
    print(f"  {text}")
    print(f"{'='*50}\n")

def check_mark(condition):
    """Return check mark or X based on condition"""
    return "✓" if condition else "✗"

def main():
    print_header("SMMS Test Environment Verification")
    
    errors = []
    warnings = []
    
    # Check 1: Python version
    print("1. Checking Python version...")
    py_version = sys.version_info
    if py_version.major == 3 and py_version.minor >= 8:
        print(f"   {check_mark(True)} Python {py_version.major}.{py_version.minor}.{py_version.micro}")
    else:
        print(f"   {check_mark(False)} Python {py_version.major}.{py_version.minor}.{py_version.micro}")
        errors.append("Python 3.8+ required")
    
    # Check 2: Project structure
    print("\n2. Checking project structure...")
    
    required_files = {
        'src/app.py': 'Main Flask application',
        'src/auth.py': 'Authentication module',
        'src/__init__.py': 'Package initialization',
        'test_intg2/test_app.py': 'Unit tests',
        'test_intg2/test_integration.py': 'Integration tests',
        'test_intg2/pytest.ini': 'Pytest configuration'
    }
    
    for file_path, description in required_files.items():
        exists = os.path.exists(file_path)
        print(f"   {check_mark(exists)} {file_path:<35} - {description}")
        if not exists:
            errors.append(f"Missing: {file_path}")
    
    # Check 3: Environment variables
    print("\n3. Checking environment variables...")
    
    testing_env = os.getenv('TESTING')
    python_path = os.getenv('PYTHONPATH')
    
    print(f"   {check_mark(testing_env == 'true')} TESTING = {testing_env}")
    if testing_env != 'true':
        warnings.append("Set TESTING=true before running tests")
    
    print(f"   {check_mark(python_path is not None)} PYTHONPATH = {python_path or 'Not set'}")
    if not python_path:
        warnings.append("Set PYTHONPATH=$(pwd) before running tests")
    
    # Check 4: Dependencies
    print("\n4. Checking Python packages...")
    
    required_packages = [
        'pytest',
        'pytest_cov',
        'pytest_mock',
        'flask',
        'flask_sqlalchemy',
        'requests',
        'dotenv'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"   {check_mark(True)} {package}")
        except ImportError:
            print(f"   {check_mark(False)} {package}")
            errors.append(f"Missing package: {package}")
    
    # Check 5: Can import src.app?
    print("\n5. Checking if src.app can be imported...")
    try:
        sys.path.insert(0, os.getcwd())
        os.environ['TESTING'] = 'true'  # Set for import
        from src.app import app, dbs, User
        print(f"   {check_mark(True)} Successfully imported src.app")
        print(f"   {check_mark(True)} Flask app found")
        print(f"   {check_mark(True)} Database models found")
    except Exception as e:
        print(f"   {check_mark(False)} Import failed: {e}")
        errors.append(f"Cannot import src.app: {e}")
    
    # Check 6: Test discovery
    print("\n6. Checking test discovery...")
    test_files = [
        'test_intg2/test_app.py',
        'test_intg2/test_integration.py'
    ]
    
    test_count = 0
    for test_file in test_files:
        if os.path.exists(test_file):
            with open(test_file, 'r') as f:
                content = f.read()
                # Count test functions
                count = content.count('def test_')
                test_count += count
                print(f"   {check_mark(count > 0)} {test_file}: {count} tests")
    
    print(f"\n   Total tests found: {test_count}")
    
    # Summary
    print_header("Verification Summary")
    
    if errors:
        print("❌ ERRORS (must fix):")
        for error in errors:
            print(f"   - {error}")
        print()
    
    if warnings:
        print("⚠️  WARNINGS (recommended fixes):")
        for warning in warnings:
            print(f"   - {warning}")
        print()
    
    if not errors and not warnings:
        print("✅ All checks passed! You're ready to run tests.")
        print("\nRun tests with:")
        print("   export TESTING=true")
        print("   pytest test_intg2/ -v --cov=src --cov-report=html")
        return 0
    elif not errors:
        print("✅ No critical errors, but some warnings.")
        print("\nFix warnings and run tests with:")
        print("   export TESTING=true")
        print("   export PYTHONPATH=$(pwd)")
        print("   pytest test_intg2/ -v --cov=src --cov-report=html")
        return 0
    else:
        print("❌ Critical errors found. Fix them before running tests.")
        print("\nQuick fixes:")
        print("   pip install pytest pytest-cov pytest-mock flask flask-sqlalchemy requests python-dotenv")
        print("   export TESTING=true")
        print("   export PYTHONPATH=$(pwd)")
        return 1

if __name__ == '__main__':
    sys.exit(main())