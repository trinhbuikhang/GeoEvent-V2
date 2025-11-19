"""
Test script to verify lane assignments persist across FileID switches
"""

import sys
import os
from datetime import datetime
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geoevent.app.main_window import MainWindow
from geoevent.app.utils.fileid_manager import FileIDManager

def test_lane_persistence():
    """Test that lane assignments persist when switching FileIDs"""
    app = QApplication(sys.argv)

    # Create main window
    main_window = MainWindow()
    main_window.show()

    # Wait for initialization
    app.processEvents()

    # Manually scan testdata directory
    testdata_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'geoevent', 'testdata', '20251002')
    if os.path.exists(testdata_path):
        main_window.fileid_manager.scan_parent_folder(testdata_path)
        print(f"Scanned {len(main_window.fileid_manager.fileid_list)} FileIDs")
    else:
        print(f"Test data path not found: {testdata_path}")
        return

    # Get fileid manager
    fileid_manager = main_window.fileid_manager

    if not fileid_manager.fileid_list:
        print("No FileIDs found, cannot test")
        return

    # Load first FileID
    first_fileid = fileid_manager.fileid_list[0]
    main_window.load_fileid(first_fileid)

    # Wait for loading
    app.processEvents()

    # Check if photo_tab has lane_manager
    if not hasattr(main_window.photo_tab, 'lane_manager') or not main_window.photo_tab.lane_manager:
        print("No lane manager for first FileID")
        return

    # Get current timestamp from first image
    if main_window.photo_tab.image_paths:
        current_metadata = main_window.photo_tab.current_metadata
        if current_metadata and 'timestamp' in current_metadata:
            timestamp = current_metadata['timestamp']

            # Assign lane '2' at current position
            print(f"Assigning lane '2' at {timestamp}")
            main_window.photo_tab.assign_lane('2')

            # Check if lane was assigned
            assigned_lane = main_window.photo_tab.lane_manager.get_lane_at_timestamp(timestamp)
            print(f"Lane assigned: {assigned_lane}")
            print(f"Lane manager id: {id(main_window.photo_tab.lane_manager)}")
            print(f"Lane fixes count: {len(main_window.photo_tab.lane_manager.lane_fixes)}")
            print(f"Lane fixes id: {id(main_window.photo_tab.lane_manager.lane_fixes)}")
            if main_window.photo_tab.lane_manager.lane_fixes:
                fix = main_window.photo_tab.lane_manager.lane_fixes[0]
                print(f"First fix: lane={fix.lane}, from={fix.from_time}, to={fix.to_time}")

            # Check if cached
            cache_key = first_fileid.fileid
            if cache_key in main_window.photo_tab.lane_managers_per_fileid:
                cached_manager = main_window.photo_tab.lane_managers_per_fileid[cache_key]
                cached_lane = cached_manager.get_lane_at_timestamp(timestamp)
                print(f"Cached lane: {cached_lane}")
                print(f"Cached manager id: {id(cached_manager)}")
                print(f"Cached lane fixes count: {len(cached_manager.lane_fixes)}")
                print(f"Cached lane fixes id: {id(cached_manager.lane_fixes)}")
                if cached_manager.lane_fixes:
                    fix = cached_manager.lane_fixes[0]
                    print(f"Cached first fix: lane={fix.lane}, from={fix.from_time}, to={fix.to_time}")
            else:
                print("No cache found")

            # Switch to second FileID if available
            if len(fileid_manager.fileid_list) > 1:
                second_fileid = fileid_manager.fileid_list[1]
                print(f"Switching to {second_fileid.fileid}")
                main_window.load_fileid(second_fileid)
                app.processEvents()

                # Switch back to first FileID
                print(f"Switching back to {first_fileid.fileid}")
                main_window.load_fileid(first_fileid)
                app.processEvents()

                # Check if lane assignment persisted
                current_lane_after_switch = main_window.photo_tab.lane_manager.get_lane_at_timestamp(timestamp)
                print(f"Lane after switch back: {current_lane_after_switch}")
                print(f"Lane manager id after switch: {id(main_window.photo_tab.lane_manager)}")
                print(f"Lane fixes count after switch: {len(main_window.photo_tab.lane_manager.lane_fixes)}")
                print(f"Lane fixes id after switch: {id(main_window.photo_tab.lane_manager.lane_fixes)}")
                if main_window.photo_tab.lane_manager.lane_fixes:
                    fix = main_window.photo_tab.lane_manager.lane_fixes[0]
                    print(f"After switch first fix: lane={fix.lane}, from={fix.from_time}, to={fix.to_time}")

                if current_lane_after_switch == '2':
                    print("SUCCESS: Lane assignment persisted across FileID switches")
                else:
                    print("FAILURE: Lane assignment did not persist")
            else:
                print("Only one FileID, cannot test switching")
        else:
            print("No timestamp in current metadata")
    else:
        print("No images in first FileID")

    # Test merged file creation
    print("Testing merged file creation...")
    main_window.auto_save_all_data_on_close()

    # Check if merged lane fixes file was created
    import os
    from datetime import datetime
    root_folder = testdata_path
    merged_lane_path = os.path.join(root_folder, f"laneFixes-{datetime.now().strftime('%d-%m-%Y')}.csv")
    
    if os.path.exists(merged_lane_path):
        print(f"SUCCESS: Merged lane fixes file created at {merged_lane_path}")
        with open(merged_lane_path, 'r') as f:
            content = f.read()
            print(f"Merged file content:\n{content}")
    else:
        print(f"FAILURE: Merged lane fixes file not found at {merged_lane_path}")
        # Check what lane fixes were collected
        all_lane_fixes = []
        for fileid_folder in fileid_manager.fileid_list:
            fixes = main_window._load_lane_fixes_for_fileid(fileid_folder)
            all_lane_fixes.extend(fixes)
            print(f"FileID {fileid_folder.fileid}: {len(fixes)} lane fixes")
        print(f"Total lane fixes collected: {len(all_lane_fixes)}")

    # Close app
    main_window.close()

if __name__ == "__main__":
    test_lane_persistence()