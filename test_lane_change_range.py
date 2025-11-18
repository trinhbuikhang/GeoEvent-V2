#!/usr/bin/env python3
"""
Test apply_lane_change_range functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.models.lane_model import LaneManager, LaneFix
from datetime import datetime, timedelta

def test_apply_lane_change_range():
    """Test that apply_lane_change_range properly splits periods"""
    print("Testing apply_lane_change_range...")

    lane_manager = LaneManager()
    from pathlib import Path
    lane_manager.fileid_folder = Path("TEST_FILE")
    lane_manager.plate = "TEST_PLATE"

    # Create initial periods: Lane1 from 0 to 20, Lane2 from 20 to 40
    base_time = datetime.now()
    lane_manager.lane_fixes = [
        LaneFix(plate="TEST_PLATE", from_time=base_time, to_time=base_time + timedelta(seconds=20), lane='1', file_id="TEST_FILE"),
        LaneFix(plate="TEST_PLATE", from_time=base_time + timedelta(seconds=20), to_time=base_time + timedelta(seconds=40), lane='2', file_id="TEST_FILE")
    ]

    print(f"Initial periods: {len(lane_manager.lane_fixes)}")
    for fix in lane_manager.lane_fixes:
        print(f"  {fix.lane}: {fix.from_time} to {fix.to_time}")

    # Apply Ignore from 5 to 35 seconds
    start_time = base_time + timedelta(seconds=5)
    end_time = base_time + timedelta(seconds=35)
    lane_manager.apply_lane_change_range('', start_time, end_time)

    print(f"After apply_lane_change_range Ignore from 5 to 35:")
    print(f"Total periods: {len(lane_manager.lane_fixes)}")
    for i, fix in enumerate(lane_manager.lane_fixes):
        print(f"  {i}: {fix.lane}: {fix.from_time} to {fix.to_time}")

    # Expected result:
    # 0-5: Lane1 (original start)
    # 5-35: Ignore (new range)
    # 35-40: Lane2 (original end)

    expected = [
        ('1', 0, 5),
        ('', 5, 35),
        ('2', 35, 40)
    ]

    if len(lane_manager.lane_fixes) != len(expected):
        print(f"✗ FAILED: Expected {len(expected)} periods, got {len(lane_manager.lane_fixes)}")
        return False

    for i, (exp_lane, exp_start, exp_end) in enumerate(expected):
        fix = lane_manager.lane_fixes[i]
        exp_start_time = base_time + timedelta(seconds=exp_start)
        exp_end_time = base_time + timedelta(seconds=exp_end)

        if fix.lane != exp_lane or fix.from_time != exp_start_time or fix.to_time != exp_end_time:
            print(f"✗ FAILED: Period {i} expected {exp_lane} {exp_start_time} to {exp_end_time}, got {fix.lane} {fix.from_time} to {fix.to_time}")
            return False

    print("✓ SUCCESS: apply_lane_change_range works correctly for Ignore")
    return True

if __name__ == "__main__":
    print("Apply Lane Change Range Test")
    print("=" * 40)

    success = test_apply_lane_change_range()
    if success:
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Tests failed!")
        sys.exit(1)