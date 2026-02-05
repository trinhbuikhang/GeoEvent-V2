"""
Comprehensive Test Suite for Phase 3 Implementation
Tests: M4 Logging, M5 GPS Optimization, M3 Validation, M1 Refactoring

PHASE 3 TASKS TESTED:
- M4: Centralized logging system with rotation
- M5: GPS interpolation O(log n) optimization
- M3: Complete input validation (timestamps, plates,lanes)
- M1: Code duplication elimination
"""

import sys
import os
import time
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add parent directory to import app modules
sys.path.insert(0, str(Path(__file__).parent))

from app.logging_config import setup_logging
from app.models.gps_model import GPSData, GPSPoint
from app.models.event_model import Event
from app.models.lane_model import LaneManager
from app.security.validator import InputValidator
from app.utils.data_loader import DataLoader

def test_m4_logging_system():
    """Test M4: Centralized logging with rotation"""
    print("\n" + "="*70)
    print("TEST M4: CENTRALIZED LOGGING SYSTEM")
    print("="*70)
    
    test_results = []
    
    # Test 1: Setup logging
    try:
        logger = setup_logging(log_dir="logs")
        test_results.append(("Setup logging", True))
    except Exception as e:
        test_results.append(("Setup logging", False, str(e)))
    
    # Test 2: Log levels
    try:
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        test_results.append(("All log levels", True))
    except Exception as e:
        test_results.append(("All log levels", False, str(e)))
    
    # Test 3: Log files exist
    try:
        log_dir = Path("logs")
        main_log = log_dir / "geoevent.log"
        error_log = log_dir / "geoevent_errors.log"
        
        assert main_log.exists(), "Main log file not created"
        assert error_log.exists(), "Error log file not created"
        test_results.append(("Log files created", True))
    except Exception as e:
        test_results.append(("Log files created", False, str(e)))
    
    # Print results
    passed = sum(1 for r in test_results if r[1])
    print(f"\nTests Passed: {passed}/{len(test_results)}")
    for result in test_results:
        status = "✓" if result[1] else "✗"
        msg = result[2] if len(result) > 2 else ""
        print(f"  {status} {result[0]} {msg}")
    
    return passed == len(test_results)

def test_m5_gps_optimization():
    """Test M5: GPS interpolation O(log n) performance"""
    print("\n" + "="*70)
    print("TEST M5: GPS INTERPOLATION OPTIMIZATION")
    print("="*70)
    
    test_results = []
    
    # Test 1: Binary search implementation exists
    try:
        gps = GPSData()
        assert hasattr(gps,  '_find_surrounding_points'), "Binary search method missing"
        test_results.append(("Binary search method exists", True))
    except Exception as e:
        test_results.append(("Binary search method exists", False, str(e)))
    
    # Test 2: Performance test
    try:
        gps = GPSData()
        base_time = datetime(2026, 2, 5, 10, 0, 0, tzinfo=timezone.utc)
        
        # Create 10,000 GPS points
        for i in range(10000):
            point = GPSPoint(
                timestamp=base_time + timedelta(seconds=i),
                latitude=-43.0 + (i * 0.0001),
                longitude=172.0 + (i * 0.0001),
                chainage=i * 10.0
            )
            gps.add_point(point)
        
        # Benchmark 1000 queries
        start = time.perf_counter()
        for i in range(1000):
            offset = (i * 123) % len(gps.points)
            query_time = base_time + timedelta(seconds=offset)
            pos = gps.interpolate_position(query_time)
        elapsed = time.perf_counter() - start
        
        # Should be fast (< 10ms for 1000 queries)
        assert elapsed < 0.01, f"Too slow: {elapsed*1000:.2f}ms"
        test_results.append((f"Performance (1000 queries in {elapsed*1000:.1f}ms)", True))
    except Exception as e:
        test_results.append(("Performance test", False, str(e)))
    
    # Test 3: Correctness test
    try:
        gps = GPSData()
        t0 = datetime(2026, 2, 5, 12, 0, 0, tzinfo=timezone.utc)
        
        gps.add_point(GPSPoint(t0, -43.0, 172.0, 0.0))
        gps.add_point(GPSPoint(t0 + timedelta(seconds=10), -43.1, 172.1, 100.0))
        
        # Interpolate at midpoint
        mid_pos = gps.interpolate_position(t0 + timedelta(seconds=5))
        assert mid_pos is not None
        assert abs(mid_pos[0] - (-43.05)) < 0.001, f"Latitude interpolation wrong: {mid_pos[0]}"
        assert abs(mid_pos[1] - 172.05) < 0.001, f"Longitude interpolation wrong: {mid_pos[1]}"
        
        test_results.append(("Interpolation correctness", True))
    except Exception as e:
        test_results.append(("Interpolation correctness", False, str(e)))
    
    # Print results
    passed = sum(1 for r in test_results if r[1])
    print(f"\nTests Passed: {passed}/{len(test_results)}")
    for result in test_results:
        status = "✓" if result[1] else "✗"
        msg = result[2] if len(result) > 2 else ""
        print(f"  {status} {result[0]} {msg}")
    
    return passed == len(test_results)

def test_m3_input_validation():
    """Test M3: Complete input validation"""
    print("\n" + "="*70)
    print("TEST M3: INPUT VALIDATION")
    print("="*70)
    
    test_results = []
    
    # Test 1: Timestamp validation
    try:
        valid_ts = datetime(2026, 2, 5, 12, 0, 0, tzinfo=timezone.utc)
        result = InputValidator.validate_timestamp(valid_ts)
        assert result.is_valid, "Valid timestamp rejected"
        
        invalid_ts = datetime(1990, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        result = InputValidator.validate_timestamp(invalid_ts)
        assert not result.is_valid, "Invalid timestamp (year 1990) accepted"
        
        test_results.append(("Timestamp validation", True))
    except Exception as e:
        test_results.append(("Timestamp validation", False, str(e)))
    
    # Test 2: Plate validation
    try:
        result = InputValidator.validate_plate("ABC123")
        assert result.is_valid, "Valid plate rejected"
        
        result = InputValidator.validate_plate("")
        assert not result.is_valid, "Empty plate accepted"
        
        test_results.append(("Plate validation", True))
    except Exception as e:
        test_results.append(("Plate validation", False, str(e)))
    
    # Test 3: Lane code validation
    try:
        for code in ['1', '2', 'TK1', 'TM2', 'SK', 'SK3']:
            result = InputValidator.validate_lane_code(code)
            assert result.is_valid, f"Valid lane code {code} rejected"
        
        result = InputValidator.validate_lane_code("INVALID")
        assert not result.is_valid, "Invalid lane code accepted"
        
        test_results.append(("Lane code validation", True))
    except Exception as e:
        test_results.append(("Lane code validation", False, str(e)))
    
    # Test 4: Event model validation
    try:
        # Valid event
        event = Event.from_dict({
            'event_id': '1',
            'event_name': 'Test Event',
            'start_time': datetime(2026, 2, 5, 12, 0, 0, tzinfo=timezone.utc).isoformat(),
            'end_time': datetime(2026, 2, 5, 12, 1, 0, tzinfo=timezone.utc).isoformat(),
            'start_chainage': 100.0,
            'end_chainage': 200.0,
            'start_lat': -43.0,
            'start_lon': 172.0
        })
        assert event is not None
        test_results.append(("Event model validation", True))
    except Exception as e:
        test_results.append(("Event model validation", False, str(e)))
    
    # Print results
    passed = sum(1 for r in test_results if r[1])
    print(f"\nTests Passed: {passed}/{len(test_results)}")
    for result in test_results:
        status = "✓" if result[1] else "✗"
        msg = result[2] if len(result) > 2 else ""
        print(f"  {status} {result[0]} {msg}")
    
    return passed == len(test_results)

def test_m1_code_refactoring():
    """Test M1: Code duplication elimination"""
    print("\n" + "="*70)
    print("TEST M1: CODE DUPLICATION REFACTORING")
    print("="*70)
    
    test_results = []
    
    # Test 1: DataLoader has _load_csv_file helper
    try:
        loader = DataLoader()
        assert hasattr(loader, '_load_csv_file'), "_load_csv_file method missing"
        test_results.append(("Helper method exists", True))
    except Exception as e:
        test_results.append(("Helper method exists", False, str(e)))
    
    # Test 2: _load_csv_file is generic and reusable
    try:
        loader = DataLoader()
        method = loader._load_csv_file
        
        # Check signature has required parameters
        import inspect
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        required = ['file_path', 'parser_func', 'empty_value']
        
        for param in required:
            assert param in params, f"Missing parameter: {param}"
        
        test_results.append(("Generic helper signature", True))
    except Exception as e:
        test_results.append(("Generic helper signature", False, str(e)))
    
    # Test 3: Methods use helper (code inspection)
    try:
        import inspect
        loader = DataLoader()
        
        # Check _load_event_data uses helper
        event_source = inspect.getsource(loader._load_event_data)
        assert '_load_csv_file' in event_source, "_load_event_data doesn't use helper"
        
        # Check _load_gps_data uses helper
        gps_source = inspect.getsource(loader._load_gps_data)
        assert '_load_csv_file' in gps_source, "_load_gps_data doesn't use helper"
        
        test_results.append(("Methods use helper", True))
    except Exception as e:
        test_results.append(("Methods use helper", False, str(e)))
    
    # Print results
    passed = sum(1 for r in test_results if r[1])
    print(f"\nTests Passed: {passed}/{len(test_results)}")
    for result in test_results:
        status = "✓" if result[1] else "✗"
        msg = result[2] if len(result) > 2 else ""
        print(f"  {status} {result[0]} {msg}")
    
    return passed == len(test_results)

def main():
    """Run all Phase 3 tests"""
    print("\n" + "="*70)
    print("PHASE 3 COMPREHENSIVE TEST SUITE")
    print("="*70)
    print("Testing: M4 Logging, M5 GPS Optimization, M3 Validation, M1 Refactoring")
    print("="*70)
    
    results = {}
    
    # Run tests
    results['M4'] = test_m4_logging_system()
    results['M5'] = test_m5_gps_optimization()
    results['M3'] = test_m3_input_validation()
    results['M1'] = test_m1_code_refactoring()
    
    # Summary
    print("\n" + "="*70)
    print("PHASE 3 TEST SUMMARY")
    print("="*70)
    
    for task, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status} - {task}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*70)
    if all_passed:
        print("ALL PHASE 3 TESTS PASSED ✓")
        print("Ready for v2.0.22 release!")
    else:
        print("SOME TESTS FAILED ✗")
        print("Please review failures before release")
    print("="*70)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
