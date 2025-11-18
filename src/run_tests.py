#!/usr/bin/env python3
"""
Local Test Runner for SMMS Notification System
Run this script to execute all tests locally
"""
import subprocess
import sys
import os


def run_command(cmd, description):
    """Run a command and print results"""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def main():
    print("="*60)
    print("  SMMS Notification System - Local Test Runner")
    print("="*60)
    
    # Check Python version
    print(f"Python version: {sys.version}")
    
    # Check if pytest is installed
    try:
        import pytest
        print(f"Pytest version: {pytest.__version__}")
    except ImportError:
        print("❌ Pytest not installed. Install with: pip install pytest")
        sys.exit(1)
    
    # Check if required files exist
    required_files = ['notification_helper.py', 'test_notifications.py']
    for f in required_files:
        if os.path.exists(f):
            print(f"✅ {f} found")
        else:
            print(f"❌ {f} not found")
            sys.exit(1)
    
    results = {}
    
    # 1. Run unit tests
    success = run_command(
        ['python', '-m', 'pytest', 'test_notifications.py', '-v', '--tb=short', '-x'],
        "Running All Tests"
    )
    results['All Tests'] = success
    
    # 2. Run with coverage (if pytest-cov is installed)
    try:
        import pytest_cov
        success = run_command(
            ['python', '-m', 'pytest', 'test_notifications.py', 
             '--cov=notification_helper', '--cov-report=term-missing'],
            "Running Tests with Coverage"
        )
        results['Coverage'] = success
    except ImportError:
        print("\n⚠️ pytest-cov not installed. Skipping coverage report.")
        print("   Install with: pip install pytest-cov")
    
    # Summary
    print("\n" + "="*60)
    print("  TEST SUMMARY")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Check output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
