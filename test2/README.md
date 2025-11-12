# Test Suite Documentation

## Overview
Comprehensive test suite for the Social Media Management System (SMMS).

## Test Files

### 1. `test_coverage.py`
**Purpose**: Check if code coverage is above 75%
- Runs pytest with coverage analysis
- Generates HTML coverage report
- Fails if coverage < 75%

**Run**: `python test2/test_coverage.py`

### 2. `test_lint_score.py`
**Purpose**: Check if pylint score is above 7.5/10
- Analyzes code quality with pylint
- Checks for code style issues
- Fails if score < 7.5

**Run**: `python test2/test_lint_score.py`

### 3. `test_unit_basic.py`
**Purpose**: Basic unit tests for core functionality
- Tests User, Platform, Post models
- Tests helper functions
- Tests individual components in isolation

**Run**: `python test2/test_unit_basic.py`

### 4. `test_integration_basic.py`
**Purpose**: Integration tests for API endpoints
- Tests authentication routes
- Tests POST API endpoints
- Tests database operations
- Tests component interactions

**Run**: `python test2/test_integration_basic.py`

### 5. `run_all_tests.py`
**Purpose**: Master test runner
- Runs all tests in sequence
- Checks coverage and lint scores
- Provides comprehensive summary

**Run**: `python test2/run_all_tests.py`

## Quick Start

### Run All Tests
```bash
python test2/run_all_tests.py
```

### Run Individual Tests
```bash
# Unit tests only
python test2/test_unit_basic.py

# Integration tests only
python test2/test_integration_basic.py

# Coverage check only
python test2/test_coverage.py

# Lint check only
python test2/test_lint_score.py
```

## Requirements
```bash
pip install pytest pytest-cov pylint
```

## Test Targets
- ✅ Code Coverage: > 75%
- ✅ Lint Score: > 7.5/10
- ✅ Unit Tests: All pass
- ✅ Integration Tests: All pass

## Interpreting Results

### Success Output
```
✅ PASSED - Unit Tests
✅ PASSED - Integration Tests  
✅ PASSED - Coverage Check
✅ PASSED - Lint Score
```

### Failure Output
```
❌ FAILED - Coverage Check
```
Action: Write more tests to increase coverage

```
❌ FAILED - Lint Score
```
Action: Fix pylint warnings in the code
