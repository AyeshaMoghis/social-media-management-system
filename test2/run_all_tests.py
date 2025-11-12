#!/usr/bin/env python3
"""
Master Test Runner
Runs all tests and checks quality metrics
"""
import sys
import os
import subprocess

def print_header(title):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def run_command(description, command):
    """Run a command and return success status"""
    print_header(description)
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all tests and checks"""
    print("\n" + "🚀"*35)
    print_header("COMPREHENSIVE TEST SUITE")
    print("🚀"*35)
    
    results = {}
    
    # 1. Run unit tests
    print_header("1️⃣  RUNNING UNIT TESTS")
    results['unit_tests'] = run_command(
        "Unit Tests",
        "python test2/test_unit_basic.py"
    )
    
    # 2. Run integration tests
    print_header("2️⃣  RUNNING INTEGRATION TESTS")
    results['integration_tests'] = run_command(
        "Integration Tests",
        "python test2/test_integration_basic.py"
    )
    
    # 3. Run existing test suite
    print_header("3️⃣  RUNNING EXISTING TEST SUITE")
    results['existing_tests'] = run_command(
        "Existing Tests",
        "pytest tests/ -v"
    )
    
    # 4. Check code coverage
    print_header("4️⃣  CHECKING CODE COVERAGE (Target: >75%)")
    results['coverage'] = run_command(
        "Coverage Check",
        "python test2/test_coverage.py"
    )
    
    # 5. Check lint score
    print_header("5️⃣  CHECKING CODE QUALITY (Target: >7.5/10)")
    results['lint'] = run_command(
        "Lint Score",
        "python test2/test_lint_score.py"
    )
    
    # Print summary
    print_header("📊 TEST RESULTS SUMMARY")
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status:12} - {test_name.replace('_', ' ').title()}")
    
    print("\n" + "-"*70)
    print(f"Total: {passed_tests}/{total_tests} checks passed")
    print("-"*70)
    
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! Your code is ready for deployment!")
        return 0
    else:
        print(f"\n⚠️  {total_tests - passed_tests} check(s) failed. Please review the errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
