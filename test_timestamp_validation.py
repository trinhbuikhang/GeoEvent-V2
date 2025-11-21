#!/usr/bin/env python3
"""
Test script to verify timestamp validation in lane assignment
"""

import sys
import os
from datetime import datetime, timezone, timedelta

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.models.lane_model import LaneManager

def test_timestamp_validation():
    """Test that lane assignment validates timestamps"""
    print("Testing timestamp validation in lane assignment...")

    manager = LaneManager()
    
    # Set valid time bounds
    base_time = datetime(2025, 10, 2, 2, 30, 0, tzinfo=timezone.utc)
    manager.first_image_timestamp = base_time
    manager.last_image_timestamp = base_time + timedelta(minutes=10)
    manager.gps_min_timestamp = base_time + timedelta(minutes=2)  # GPS starts later
    manager.gps_max_timestamp = base_time + timedelta(minutes=8)  # GPS ends earlier
    
    # Should use image range (longer)
    valid_min = manager.first_image_timestamp
    valid_max = manager.last_image_timestamp
    
    print(f"Valid range: {valid_min} to {valid_max}")
    
    # Test valid timestamp
    valid_timestamp = base_time + timedelta(minutes=5)
    assert manager._is_timestamp_valid(valid_timestamp), "Valid timestamp should pass"
    print("✅ Valid timestamp accepted")
    
    # Test invalid timestamp (too early)
    invalid_timestamp_early = base_time - timedelta(minutes=1)
    assert not manager._is_timestamp_valid(invalid_timestamp_early), "Early timestamp should fail"
    print("✅ Early timestamp rejected")
    
    # Test invalid timestamp (too late)
    invalid_timestamp_late = base_time + timedelta(minutes=15)
    assert not manager._is_timestamp_valid(invalid_timestamp_late), "Late timestamp should fail"
    print("✅ Late timestamp rejected")
    
    # Test boundary (with tolerance)
    boundary_timestamp = valid_min - timedelta(seconds=0.5)  # Within 1 second tolerance
    assert manager._is_timestamp_valid(boundary_timestamp), "Boundary timestamp should pass"
    print("✅ Boundary timestamp accepted")
    
    print("✅ Timestamp validation test PASSED")

if __name__ == "__main__":
    test_timestamp_validation()