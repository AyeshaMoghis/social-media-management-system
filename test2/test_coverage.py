#!/usr/bin/env python3
"""
Test Coverage Runner
Checks if code coverage is above 75%
"""
import sys
import os
import subprocess

def run_coverage_tests():
    """Run pytest with coverage and check if it meets threshold"""
    print("\n" + "="*70)
    print("📊 RUNNING CODE COVERAGE TESTS")
    print("="*70 + "\n")
    
    try:
        # Run pytest with coverage
        print("Running tests with coverage analysis...\n")
        result = subprocess.run(
            [
                'pytest',
                'test2/',
                '--cov=src',
                '--cov-report=term-missing',
                '--cov-report=html',
                '--cov-fail-under=75',
                '-v',
                '--tb=short'
            ],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        # Check coverage percentage
        if "TOTAL" in result.stdout:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'TOTAL' in line:
                    print("\n" + "="*70)
                    print(line)
                    print("="*70)
        
        if result.returncode == 0:
            print("\n✅ SUCCESS: Code coverage is above 75%!")
            print("📄 HTML coverage report generated in htmlcov/index.html")
            return True
        else:
            print("\n❌ FAILED: Code coverage is below 75%")
            print("💡 Tip: Write more tests to increase coverage")
            return False
            
    except FileNotFoundError:
        print("❌ pytest or pytest-cov not installed")
        print("Install with: pip install pytest pytest-cov")
        return False
    except Exception as e:
        print(f"❌ Error running coverage tests: {e}")
        return False

if __name__ == '__main__':
    success = run_coverage_tests()
    sys.exit(0 if success else 1)
