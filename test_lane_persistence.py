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

from app.main_window import MainWindow
from app.utils.fileid_manager import FileIDManager

def test_lane_persistence():
    """Test that lane assignments persist when switching FileIDs"""
    import os
    app = QApplication(sys.argv)

    # Create main window
    main_window = MainWindow()
    main_window.show()

    # Wait for initialization
    app.processEvents()

    # Manually scan testdata directory
    testdata_path = r"C:\Users\du\Desktop\testdata\20251002"
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

def test_load_existing_lane_fixes():
    """Test that app loads existing lane fixes from CSV file when cache is empty"""
    import os
    import csv
    from datetime import datetime, timezone
    
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    app.processEvents()

    # Manually scan testdata directory
    testdata_path = r"C:\Users\du\Desktop\testdata\20251002"
    if os.path.exists(testdata_path):
        main_window.fileid_manager.scan_parent_folder(testdata_path)
        print(f"Scanned {len(main_window.fileid_manager.fileid_list)} FileIDs")
    else:
        print(f"Test data path not found: {testdata_path}")
        return

    if not main_window.fileid_manager.fileid_list:
        print("No FileIDs found")
        return

    # Get first FileID
    first_fileid = main_window.fileid_manager.fileid_list[0]
    
    # Create a test lane fixes CSV file
    csv_path = os.path.join(first_fileid.path, f"{first_fileid.fileid}_lane_fixes.csv")
    test_lane_fixes = [
        ['Plate', 'From', 'To', 'Lane', 'Ignore'],
        ['TEST123', '01/11/25 10:00:00.000', '01/11/25 10:05:00.000', '1', '']
    ]
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(test_lane_fixes)
    print(f"Created test lane fixes file: {csv_path}")

    # Clear any existing cache for this FileID
    if first_fileid.fileid in main_window.photo_tab.lane_fixes_per_fileid:
        del main_window.photo_tab.lane_fixes_per_fileid[first_fileid.fileid]
    print("Cleared cache for FileID")

    # Load the FileID
    main_window.load_fileid(first_fileid)
    app.processEvents()

    # Check if lane fixes were loaded from file
    if main_window.photo_tab.lane_manager and main_window.photo_tab.lane_manager.lane_fixes:
        loaded_fixes = main_window.photo_tab.lane_manager.lane_fixes
        print(f"SUCCESS: Loaded {len(loaded_fixes)} lane fixes from file")
        if len(loaded_fixes) == 1:
            fix = loaded_fixes[0]
            print(f"Loaded fix: plate={fix.plate}, lane={fix.lane}, from={fix.from_time}, to={fix.to_time}")
            if fix.plate == 'TEST123' and fix.lane == '1':
                print("SUCCESS: Lane fix data matches expected")
            else:
                print("FAILURE: Lane fix data does not match")
        else:
            print("FAILURE: Expected 1 lane fix")
    else:
        print("FAILURE: No lane fixes loaded from file")

    # Now assign a new lane
    if main_window.photo_tab.image_paths and main_window.photo_tab.current_metadata:
        timestamp = main_window.photo_tab.current_metadata['timestamp']
        print(f"Assigning new lane '2' at {timestamp}")
        main_window.photo_tab.assign_lane('2')
        
        # Switch to another FileID to trigger save
        if len(main_window.fileid_manager.fileid_list) > 1:
            second_fileid = main_window.fileid_manager.fileid_list[1]
            print(f"Switching to {second_fileid.fileid} to trigger save")
            main_window.load_fileid(second_fileid)
            app.processEvents()
            
            # Check if backup was created
            backup_files = [f for f in os.listdir(first_fileid.path) if f.startswith(f"{first_fileid.fileid}_lane_fixes_backup_")]
            if backup_files:
                print(f"SUCCESS: Backup file created: {backup_files[0]}")
            else:
                print("FAILURE: No backup file created")
            
            # Check if original file was updated
            if os.path.exists(csv_path):
                with open(csv_path, 'r') as f:
                    lines = f.readlines()
                    if len(lines) > 1:  # Header + data
                        print("SUCCESS: Original file has data after save")
                        print(f"File content:\n{''.join(lines)}")
                    else:
                        print("FAILURE: Original file empty after save")
            else:
                print("FAILURE: Original file not found")
            
            # Check merged file
            root_folder = testdata_path
            merged_path = os.path.join(root_folder, f"laneFixes-{datetime.now().strftime('%d-%m-%Y')}.csv")
            if os.path.exists(merged_path):
                print(f"SUCCESS: Merged file exists: {merged_path}")
                with open(merged_path, 'r') as f:
                    content = f.read()
                    print(f"Merged file content:\n{content}")
            else:
                print("FAILURE: Merged file not found")
        else:
            print("Only one FileID, cannot test save/backup")
    else:
        print("No images or metadata for assigning new lane")

    # Close app
    main_window.close()

def test_specific_folder():
    """Test loading lane fixes for specific folder 0D2510021153057700"""
    import os
    import csv
    from datetime import datetime, timezone
    
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    app.processEvents()

    # Manually scan testdata directory
    testdata_path = r"C:\Users\du\Desktop\testdata\20251002"
    if os.path.exists(testdata_path):
        main_window.fileid_manager.scan_parent_folder(testdata_path)
        print(f"Scanned {len(main_window.fileid_manager.fileid_list)} FileIDs")
    else:
        print(f"Test data path not found: {testdata_path}")
        return

    # Find the specific FileID
    target_fileid = None
    for fid in main_window.fileid_manager.fileid_list:
        if fid.fileid == '0D2510021153057700':
            target_fileid = fid
            break
    
    if not target_fileid:
        print("Target FileID not found")
        return
    
    print(f"Found target FileID: {target_fileid.fileid} at {target_fileid.path}")
    
    # Check existing file
    csv_path = os.path.join(target_fileid.path, f"{target_fileid.fileid}_lane_fixes.csv")
    if os.path.exists(csv_path):
        with open(csv_path, 'r') as f:
            content = f.read()
            print(f"Existing file content:\n{content}")
    else:
        print("No existing lane fixes file")

    # Clear any existing cache for this FileID
    if target_fileid.fileid in main_window.photo_tab.lane_fixes_per_fileid:
        del main_window.photo_tab.lane_fixes_per_fileid[target_fileid.fileid]
    print("Cleared cache for FileID")

    # Load the FileID
    main_window.load_fileid(target_fileid)
    app.processEvents()

    # Check if lane fixes were loaded from file
    if main_window.photo_tab.lane_manager and main_window.photo_tab.lane_manager.lane_fixes:
        loaded_fixes = main_window.photo_tab.lane_manager.lane_fixes
        print(f"SUCCESS: Loaded {len(loaded_fixes)} lane fixes from file")
        for i, fix in enumerate(loaded_fixes):
            print(f"Fix {i}: plate={fix.plate}, lane={fix.lane}, from={fix.from_time}, to={fix.to_time}")
    else:
        print("FAILURE: No lane fixes loaded from file")

    # Close app
    main_window.close()

if __name__ == "__main__":
    # test_lane_persistence()
    # test_load_existing_lane_fixes()
    test_specific_folder()