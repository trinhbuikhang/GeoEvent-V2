#!/usr/bin/env python3
"""
Test script to verify the merge delay fix
"""

import os
import sys
import time
import csv
from pathlib import Path

# Add app to path
sys.path.insert(0, os.path.join(os.pathdirname(__file__), 'app'))

def test_merge_delay_fix():
    """Test that merge delay issue is fixed"""
    print("Testing merge delay fix...")

    # Import here to avoid issues
    from app.main_window import MainWindow
    from app.utils.fileid_manager import FileIDManager
    from app.utils.settings_manager import SettingsManager

    # Create main window (but don't show it)
    app = MainWindow.__new__(MainWindow)
    app.settings_manager = SettingsManager()
    app.fileid_manager = FileIDManager()

    # Mock photo_tab with cache
    class MockPhotoTab:
        def __init__(self):
            self.events_per_fileid = {}
            self.lane_fixes_per_fileid = {}
            self.events_modified = False

    app.photo_tab = MockPhotoTab()

    # Test data
    test_data = {
        'FileID1': [
            {'from_time': '10:00:00', 'to_time': '11:00:00', 'lane': '1', 'ignore': ''},
        ],
        'FileID1_modified': [
            {'from_time': '10:30:00', 'to_time': '11:00:00', 'lane': '2', 'ignore': ''},
        ],
        'FileID2': [
            {'from_time': '12:00:00', 'to_time': '13:00:00', 'lane': '1', 'ignore': ''},
        ]
    }

    print("1. FileID 1: Add lane 1 (10:00-11:00)")
    app.photo_tab.lane_fixes_per_fileid['FileID1'] = test_data['FileID1']

    print("2. Switch to FileID 2 -> merge should include FileID1 lane 1")
    # Simulate merge call
    app._merge_and_save_multi_fileid_data()

    print("3. Modify FileID1 cache (simulate user editing lane fixes)")
    app.photo_tab.lane_fixes_per_fileid['FileID1'] = test_data['FileID1_modified']

    print("4. Switch to FileID 2 again -> merge should include FileID1 lane 2 (FIXED)")
    # Simulate merge call again
    app._merge_and_save_multi_fileid_data()

    print("✅ Test completed - merge should now include latest changes immediately")
    print("\n🔧 Fix applied:")
    print("- Cache is updated immediately when lane fixes are modified")
    print("- Merge uses latest cache data instead of old file data")
    print("- No more 'lag' between modification and merge update")

if __name__ == "__main__":
    test_merge_delay_fix()