# GeoEvent Test Suite

This directory contains comprehensive tests for the GeoEvent application.

## Running Tests

### Prerequisites
- Python 3.8+
- pytest installed (`pip install pytest`)

### Execute Tests
```bash
# Run all tests
python -m pytest test_geoevent.py -v

# Run specific test class
python -m pytest test_geoevent.py::TestLaneModel -v

# Run specific test method
python -m pytest test_geoevent.py::TestLaneModel::test_assign_lane_basic -v

# Generate coverage report
python -m pytest test_geoevent.py --cov=app --cov-report=html
```

## Test Coverage

The test suite covers the following components:

### Lane Management (`TestLaneModel`)
- LaneFix dataclass creation and serialization
- Basic lane assignment
- Lane period extension
- Lane changing
- Special lane types (SK, TK, TM)
- Ignore functionality
- Overlap detection
- Lane querying at timestamps

### Data Export (`TestExportManager`)
- CSV export with FileID column
- CSV export without FileID column
- Empty data handling
- Invalid path handling

### Settings Management (`TestSettingsManager`)
- Theme persistence
- Window geometry settings

### Core Managers (`TestMemoryManager`, `TestAutoSaveManager`)
- Component initialization
- Basic functionality

### Integration Tests (`TestIntegration`)
- Complete lane assignment and export workflow
- Theme persistence across application instances

## Test Data

Tests use mock data and temporary directories. Real test data is located in the `testdata/` directory.

## Adding New Tests

When adding new tests:

1. Follow the existing naming convention: `Test<ComponentName>`
2. Use descriptive test method names: `test_<action>_<expected_result>`
3. Include docstrings explaining what each test validates
4. Use `setup_method` and `teardown_method` for test isolation
5. Mock external dependencies where appropriate

## Continuous Integration

These tests can be integrated into CI/CD pipelines to ensure code quality and prevent regressions.