#!/usr/bin/env python3
"""
Test script to verify merged lane fixes are saved on app close
"""

import os
import sys
import logging
from pathlib import Path

# Add the geoevent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'geoevent'))

from app.main_window import MainWindow
from utils.fileid_manager import FileIDManager

def test_merged_lane_fixes_save():
    """Test that merged lane fixes are saved when closing app"""
    logging.basicConfig(level=logging.INFO)

    # Initialize main window
    app = MainWindow()

    # Load test data folder
    test_data_path = Path("testdata/20251002")
    if not test_data_path.exists():
        print("Test data folder not found")
        return

    # Load FileID folders
    fileid_manager = FileIDManager()
    fileid_manager.load_folder(str(test_data_path))

    if not fileid_manager.fileid_list:
        print("No FileID folders found")
        return

    print(f"Loaded {len(fileid_manager.fileid_list)} FileID folders")

    # Simulate loading first FileID and assigning a lane
    first_fileid = fileid_manager.fileid_list[0]
    app.photo_tab.load_fileid(first_fileid)

    # Assign a lane
    if app.photo_tab.image_paths:
        app.photo_tab.current_index = 0
        app.photo_tab.load_current_image()
        app.photo_tab.assign_lane('2')
        print("Assigned lane '2' to first image")

    # Simulate closing app (call auto_save_all_data_on_close)
    print("Simulating app close...")
    app.auto_save_all_data_on_close()

    # Check if merged lane fixes file was created
    root_folder = str(test_data_path)
    merged_lane_path = os.path.join(root_folder, f"laneFixes-{app.photo_tab.current_metadata['timestamp'].strftime('%d-%m-%Y')}.csv")

    if os.path.exists(merged_lane_path):
        print(f"SUCCESS: Merged lane fixes file created at {merged_lane_path}")
        with open(merged_lane_path, 'r') as f:
            content = f.read()
            print(f"File content:\n{content}")
    else:
        print(f"FAILURE: Merged lane fixes file not found at {merged_lane_path}")

    # Check individual FileID lane fixes
    for fileid_folder in fileid_manager.fileid_list:
        lane_fixes_path = os.path.join(fileid_folder.path, f"{fileid_folder.fileid}_lane_fixes.csv")
        if os.path.exists(lane_fixes_path):
            print(f"Individual lane fixes saved for {fileid_folder.fileid}")
        else:
            print(f"No individual lane fixes for {fileid_folder.fileid}")

if __name__ == "__main__":
    test_merged_lane_fixes_save()