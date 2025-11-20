"""
Test for lane change cancel functionality
"""

import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from models.lane_model import LaneManager, LaneFix

def test_lane_change_cancel():
    """Test the cancel functionality in lane change mode"""

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
    for fix in sorted(manager.lane_fixes, key=lambda x: x.from_time):
        color = manager.get_lane_color(fix.lane)
        print(f"  {fix.from_time.strftime('%H:%M')} - {fix.to_time.strftime('%H:%M')}: Lane {fix.lane} (color: {color})")

    # Simulate enabling lane change mode (auto-apply)
    start_time = base_time.replace(hour=10, minute=30)  # 10:30
    new_lane = "3"

    # Store original lane
    original_lane = manager.get_lane_at_timestamp(start_time)
    print(f"\nOriginal lane at {start_time.strftime('%H:%M')}: {original_lane}")

    # Calculate auto end time (next change: 11:00)
    next_change_time = manager.get_next_lane_change_time(start_time)
    print(f"Next change time: {next_change_time.strftime('%H:%M') if next_change_time else 'None'}")

    # Auto-apply change from 10:30 to 11:00 with Lane 3
    print(f"\nAuto-applying lane change: {start_time.strftime('%H:%M')} - {next_change_time.strftime('%H:%M')} -> Lane {new_lane}")

    success = manager.apply_lane_change_range(new_lane, start_time, next_change_time)
    print(f"Auto-apply success: {success}")

    print("\nLane data after auto-apply:")
    for fix in sorted(manager.lane_fixes, key=lambda x: x.from_time):
        color = manager.get_lane_color(fix.lane)
        print(f"  {fix.from_time.strftime('%H:%M')} - {fix.to_time.strftime('%H:%M')}: Lane {fix.lane} (color: {color})")

    # Now simulate cancel (revert to original lane)
    print(f"\nCancelling lane change - reverting to original lane {original_lane}")
    success = manager.apply_lane_change_range(original_lane, start_time, next_change_time)
    print(f"Revert success: {success}")

    print("\nLane data after cancel/revert:")
    for fix in sorted(manager.lane_fixes, key=lambda x: x.from_time):
        color = manager.get_lane_color(fix.lane)
        print(f"  {fix.from_time.strftime('%H:%M')} - {fix.to_time.strftime('%H:%M')}: Lane {fix.lane} (color: {color})")

    # Expected final result: back to original, merged
    expected = [
        ("10:00", "11:00", "1"),  # Merged back to single period
        ("11:00", "12:00", "2")   # Original period unchanged
    ]

    print("\nExpected after cancel:")
    for start, end, lane in expected:
        color = manager.get_lane_color(lane)
        print(f"  {start} - {end}: Lane {lane} (color: {color})")

    # Check if result matches expected
    sorted_fixes = sorted(manager.lane_fixes, key=lambda x: x.from_time)

    if len(sorted_fixes) != len(expected):
        print(f"\n❌ FAIL: Expected {len(expected)} periods, got {len(sorted_fixes)}")
        return False

    for i, fix in enumerate(sorted_fixes):
        exp_start, exp_end, exp_lane = expected[i]
        act_start = fix.from_time.strftime('%H:%M')
        act_end = fix.to_time.strftime('%H:%M')
        act_lane = fix.lane

        print(f"Period {i+1}: Expected {exp_start}-{exp_end} Lane {exp_lane}, Actual {act_start}-{act_end} Lane {act_lane}")

        if act_start != exp_start or act_end != exp_end or act_lane != exp_lane:
            print(f"\n❌ FAIL: Period {i+1}")
            print(f"    Expected: {exp_start}-{exp_end} Lane {exp_lane}")
            print(f"    Actual:   {act_start}-{act_end} Lane {act_lane}")
            return False

    print("\n✅ PASS: Cancel functionality works correctly!")
    return True

if __name__ == "__main__":
    test_lane_change_cancel()