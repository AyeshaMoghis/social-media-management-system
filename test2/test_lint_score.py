#!/usr/bin/env python3
"""
Lint Score Checker
Checks if pylint score is above 7.5
"""
import sys
import os
import subprocess
import re

def run_pylint_check():
    """Run pylint and check if score is above 7.5"""
    print("\n" + "="*70)
    print("🔍 RUNNING PYLINT CODE QUALITY CHECK")
    print("="*70 + "\n")
    
    src_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'src'
    )
    
    try:
        # Run pylint on src directory
        print(f"Analyzing code quality in: {src_path}\n")
        result = subprocess.run(
            ['pylint', src_path, '--output-format=text', '--score=yes'],
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        
        # Extract score using regex
        score_pattern = r"Your code has been rated at ([\d\.]+)/10"
        match = re.search(score_pattern, result.stdout)
        
        if match:
            score = float(match.group(1))
            print("\n" + "="*70)
            print(f"📊 PYLINT SCORE: {score}/10")
            print("="*70)
            
            if score >= 7.5:
                print(f"\n✅ SUCCESS: Code quality score ({score}) is above 7.5!")
                return True
            else:
                print(f"\n❌ FAILED: Code quality score ({score}) is below 7.5")
                print("💡 Tip: Fix the warnings above to improve your score")
                return False
        else:
            print("\n⚠️  Could not extract pylint score from output")
            return False
            
    except FileNotFoundError:
        print("❌ pylint not installed")
        print("Install with: pip install pylint")
        return False
    except Exception as e:
        print(f"❌ Error running pylint: {e}")
        return False

if __name__ == '__main__':
    success = run_pylint_check()
    sys.exit(0 if success else 1)
