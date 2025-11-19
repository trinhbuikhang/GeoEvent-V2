"""
Test for lane change range logic
"""

import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from models.lane_model import LaneManager, LaneFix

def test_lane_change_range():
    """Test the apply_lane_change_range logic with the user's example"""

    # Create a LaneManager
    manager = LaneManager()
    manager.plate = "TEST_PLATE"
    manager.fileid_folder = Path("test_folder")

    # Set up initial lane data:
    # 10:00-11:00 Lane 1, 11:00-12:00 Lane 2
    base_time = datetime(2025, 11, 20, 10, 0, 0, tzinfo=timezone.utc)

    fix1 = LaneFix(
        plate="TEST_PLATE",
        from_time=base_time,  # 10:00
        to_time=base_time.replace(hour=11),  # 11:00
        lane="1",
        file_id="test_folder"
    )

    fix2 = LaneFix(
        plate="TEST_PLATE",
        from_time=base_time.replace(hour=11),  # 11:00
        to_time=base_time.replace(hour=12),  # 12:00
        lane="2",
        file_id="test_folder"
    )

    manager.lane_fixes = [fix1, fix2]

    print("Initial lane data:")
    for fix in manager.lane_fixes:
        print(f"  {fix.from_time.strftime('%H:%M')} - {fix.to_time.strftime('%H:%M')}: Lane {fix.lane}")

    # Apply lane change: from 10:15 to 10:30, change to Lane 2
    start_time = base_time.replace(minute=15)  # 10:15
    end_time = base_time.replace(minute=30)    # 10:30

    print(f"\nApplying lane change: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')} -> Lane 2")

    success = manager.apply_lane_change_range("2", start_time, end_time)

    print(f"Success: {success}")

    print("\nResulting lane data:")
    for fix in manager.lane_fixes:
        print(f"  {fix.from_time.strftime('%H:%M')} - {fix.to_time.strftime('%H:%M')}: Lane {fix.lane}")

    # Sort by from_time for comparison
    sorted_fixes = sorted(manager.lane_fixes, key=lambda x: x.from_time)
    # 10:00-10:15: Lane 1
    # 10:15-10:30: Lane 2
    # 10:30-11:00: Lane 1
    # 11:00-12:00: Lane 2

    expected = [
        ("10:00", "10:15", "1"),
        ("10:15", "10:30", "2"),
        ("10:30", "11:00", "1"),
        ("11:00", "12:00", "2")
    ]

    print("\nExpected:")
    for start, end, lane in expected:
        print(f"  {start} - {end}: Lane {lane}")

    # Check if result matches expected
    if len(sorted_fixes) != len(expected):
        print(f"\n❌ FAIL: Expected {len(expected)} periods, got {len(sorted_fixes)}")
        return False

    for i, fix in enumerate(sorted_fixes):
        exp_start, exp_end, exp_lane = expected[i]
        act_start = fix.from_time.strftime('%H:%M')
        act_end = fix.to_time.strftime('%H:%M')
        act_lane = fix.lane

        if act_start != exp_start or act_end != exp_end or act_lane != exp_lane:
            print(f"\n❌ FAIL: Period {i+1}")
            print(f"    Expected: {exp_start}-{exp_end} Lane {exp_lane}")
            print(f"    Actual:   {act_start}-{act_end} Lane {act_lane}")
            return False

    print("\n✅ PASS: All periods match expected result!")
    return True

if __name__ == "__main__":
    test_lane_change_range()