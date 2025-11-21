#!/usr/bin/env python3
"""
Test script to reproduce lane fixes contamination issue between FileIDs
"""

import sys
import os
import time
import logging
from pathlib import Path

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from app.main_window import MainWindow
from app.models.lane_model import LaneFix

def test_lane_contamination():
    """Test if lane fixes from one FileID contaminate another"""

    print("Testing lane fixes contamination between FileIDs...")
    print("=" * 60)

    # Create QApplication
    app = QApplication(sys.argv)

    # Create main window
    main_window = MainWindow()
    main_window.showMaximized()

    # Give GUI time to initialize
    app.processEvents()
    time.sleep(1)

    # Load network folder
    network_path = r"\\pav001\e$\250410.01-CCC\testdata\20251002"
    print(f"Loading folder: {network_path}")

    try:
        # Scan for FileIDs
        fileid_folders = main_window.fileid_manager.scan_parent_folder(network_path)
        print(f"Found {len(fileid_folders)} FileID folders")

        if len(fileid_folders) < 2:
            print("Need at least 2 FileIDs for test")
            return

        # Find FileID with most images (long timeline)
        max_images = 0
        long_fileid = None
        short_fileid = None

        for fileid_folder in fileid_folders:
            cam1_path = os.path.join(fileid_folder.path, "Cam1")
            if os.path.exists(cam1_path):
                try:
                    image_count = len([f for f in os.listdir(cam1_path) if f.lower().endswith('.jpg')])
                    if image_count > max_images:
                        max_images = image_count
                        long_fileid = fileid_folder
                except:
                    pass

        # Find a shorter FileID
        min_images = float('inf')
        for fileid_folder in fileid_folders:
            if fileid_folder == long_fileid:
                continue
            cam1_path = os.path.join(fileid_folder.path, "Cam1")
            if os.path.exists(cam1_path):
                try:
                    image_count = len([f for f in os.listdir(cam1_path) if f.lower().endswith('.jpg')])
                    if image_count < min_images:
                        min_images = image_count
                        short_fileid = fileid_folder
                except:
                    pass

        if not long_fileid or not short_fileid:
            print("Could not find suitable FileIDs for test")
            return

        print(f"Long FileID: {long_fileid.fileid} ({max_images} images)")
        print(f"Short FileID: {short_fileid.fileid} ({min_images} images)")

        # Step 1: Load long FileID
        print(f"\nStep 1: Loading long FileID {long_fileid.fileid}")
        main_window.load_fileid(long_fileid)
        app.processEvents()
        time.sleep(2)  # Wait for loading

        # Check initial lane fixes
        initial_lane_count = len(main_window.photo_tab.lane_manager.lane_fixes)
        print(f"Initial lane fixes in long FileID: {initial_lane_count}")
        print(f"Lane manager ID: {id(main_window.photo_tab.lane_manager)}")

        # Step 2: Create some lane fixes in long FileID
        print(f"Step 2: Creating test lane fixes in {long_fileid.fileid}")

        # Create a test lane fix
        from datetime import datetime, timezone
        start_time = datetime(2025, 10, 1, 19, 12, 31, tzinfo=timezone.utc)  # Within the time range
        end_time = datetime(2025, 10, 1, 19, 12, 32, tzinfo=timezone.utc)

        test_lane_fix = LaneFix(
            plate=main_window.photo_tab.lane_manager.plate,
            from_time=start_time,
            to_time=end_time,
            lane="LEFT_TO_RIGHT",
            file_id=long_fileid.fileid
        )

        main_window.photo_tab.lane_manager.lane_fixes.append(test_lane_fix)
        main_window.photo_tab.lane_manager.has_changes = True

        print(f"Added 1 test lane fix. Total: {len(main_window.photo_tab.lane_manager.lane_fixes)}")

        # Step 3: Switch to short FileID
        print(f"\nStep 3: Switching to short FileID {short_fileid.fileid}")
        
        # Remove any existing lane_fixes.csv to ensure clean test
        lane_fixes_path = os.path.join(short_fileid.path, f"{short_fileid.fileid}_lane_fixes.csv")
        if os.path.exists(lane_fixes_path):
            os.remove(lane_fixes_path)
            print(f"Removed existing lane_fixes.csv for clean test")
        
        main_window.load_fileid(short_fileid)
        app.processEvents()
        time.sleep(2)  # Wait for loading

        # Check lane fixes in short FileID
        short_lane_count = len(main_window.photo_tab.lane_manager.lane_fixes)
        print(f"Lane fixes in short FileID: {short_lane_count}")
        print(f"Lane manager ID: {id(main_window.photo_tab.lane_manager)}")

        if short_lane_count > 0:
            print("❌ PROBLEM: Short FileID has lane fixes when it shouldn't!")
            print("Lane fixes details:")
            for i, fix in enumerate(main_window.photo_tab.lane_manager.lane_fixes):
                print(f"  {i+1}: {fix.from_time} - {fix.to_time} ({fix.lane})")

            # Check if timestamps are valid for short FileID
            first_ts = main_window.photo_tab.lane_manager.first_image_timestamp
            last_ts = main_window.photo_tab.lane_manager.last_image_timestamp
            print(f"Short FileID time range: {first_ts} - {last_ts}")

            invalid_fixes = []
            for fix in main_window.photo_tab.lane_manager.lane_fixes:
                if fix.from_time < first_ts or fix.to_time > last_ts:
                    invalid_fixes.append(fix)

            if invalid_fixes:
                print(f"❌ CRITICAL: {len(invalid_fixes)} lane fixes have invalid timestamps for this FileID!")
        else:
            print("✅ OK: Short FileID has no lane fixes")

        # Step 4: Switch back to long FileID
        print(f"\nStep 4: Switching back to long FileID {long_fileid.fileid}")
        main_window.load_fileid(long_fileid)
        app.processEvents()
        time.sleep(2)

        final_lane_count = len(main_window.photo_tab.lane_manager.lane_fixes)
        print(f"Lane fixes in long FileID after switch back: {final_lane_count}")

        if final_lane_count == initial_lane_count + 1:
            print("✅ OK: Long FileID retained the test lane fix")
        elif final_lane_count == initial_lane_count:
            print("⚠️ WARNING: Test lane fix was lost")
        else:
            print(f"❌ PROBLEM: Unexpected lane fix count: {final_lane_count}")

    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        app.quit()

if __name__ == "__main__":
    test_lane_contamination()