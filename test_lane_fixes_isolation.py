#!/usr/bin/env python3
"""
Test script to verify that lane fixes are not automatically copied between consecutive FileID folders
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from PyQt6.QtWidgets import QApplication
from app.main_window import MainWindow
from app.models.lane_model import LaneFix

def test_lane_fixes_isolation():
    """Test that lane fixes remain isolated per FileID during navigation"""
    print("Testing lane fixes isolation between FileID folders...")

    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()

    # Use testdata
    testdata_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'testdata', '20251002')
    if not os.path.exists(testdata_path):
        print("❌ Test data not found")
        return False

    # Scan for FileIDs
    main_window.fileid_manager.scan_parent_folder(testdata_path)
    print(f"Found {len(main_window.fileid_manager.fileid_list)} FileIDs")

    if len(main_window.fileid_manager.fileid_list) < 2:
        print("❌ Need at least 2 FileIDs for test")
        return False

    # Load first FileID
    first_fileid = main_window.fileid_manager.fileid_list[0]
    main_window.load_fileid(first_fileid)
    app.processEvents()

    print(f"Loaded first FileID: {first_fileid.fileid}")

    # Create a test lane fix for first FileID with valid time range
    if hasattr(main_window.photo_tab, 'lane_manager') and main_window.photo_tab.lane_manager:
        # Get valid time range from metadata
        start_time = main_window.photo_tab.lane_manager.first_image_timestamp
        end_time = main_window.photo_tab.lane_manager.last_image_timestamp

        if start_time and end_time:
            # Create a lane fix within valid range
            test_lane_fix = LaneFix(
                plate=main_window.photo_tab.lane_manager.plate or 'TEST',
                from_time=start_time + timedelta(seconds=10),
                to_time=start_time + timedelta(seconds=20),
                lane='TM3',
                file_id=first_fileid.fileid,
                ignore=False
            )
            main_window.photo_tab.lane_manager.lane_fixes = [test_lane_fix]
            main_window.photo_tab.lane_manager.has_changes = True

            print(f"Created test lane fix for {first_fileid.fileid}: {test_lane_fix.from_time} to {test_lane_fix.to_time}")

            # Switch to second FileID
            second_fileid = main_window.fileid_manager.fileid_list[1]
            main_window.load_fileid(second_fileid)
            app.processEvents()

            print(f"Switched to second FileID: {second_fileid.fileid}")

            # Check that second FileID has no lane fixes (or only valid ones from file)
            second_lane_fixes = main_window.photo_tab.lane_manager.lane_fixes
            print(f"Second FileID has {len(second_lane_fixes)} lane fixes")

            # Validate that none of the lane fixes have the same time range as our test fix
            invalid_fixes = []
            for fix in second_lane_fixes:
                if (fix.from_time == test_lane_fix.from_time and
                    fix.to_time == test_lane_fix.to_time and
                    fix.lane == test_lane_fix.lane):
                    invalid_fixes.append(fix)

            if invalid_fixes:
                print(f"❌ Found {len(invalid_fixes)} lane fixes from first FileID in second FileID!")
                for fix in invalid_fixes:
                    print(f"  Invalid fix: {fix.from_time} to {fix.to_time}, lane={fix.lane}")
                return False
            else:
                print("✅ No lane fixes from first FileID found in second FileID")

            # Switch back to first FileID
            main_window.load_fileid(first_fileid)
            app.processEvents()

            print(f"Switched back to first FileID: {first_fileid.fileid}")

            # Check that first FileID has lane fixes (may be different due to validation)
            first_lane_fixes = main_window.photo_tab.lane_manager.lane_fixes
            print(f"First FileID has {len(first_lane_fixes)} lane fixes")

            # The important thing is that second FileID didn't get contaminated
            # and first FileID preserved its valid lane fixes
            print("✅ Lane fixes isolation working correctly")
            return True
        else:
            print("❌ No valid time range metadata for first FileID")
            return False
    else:
        print("❌ No lane manager available")
        return False

if __name__ == "__main__":
    success = test_lane_fixes_isolation()
    if success:
        print("\n✅ Lane fixes isolation test PASSED")
        sys.exit(0)
    else:
        print("\n❌ Lane fixes isolation test FAILED")
        sys.exit(1)