"""
Comprehensive test script for lane persistence across FileID switches
Tests all user scenarios: adding lanes, changing lanes, switching folders, and verifying output
"""

import sys
import os
import tempfile
from datetime import datetime, timezone, timedelta
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main_window import MainWindow
from app.utils.fileid_manager import FileIDManager
from app.models.lane_model import LaneManager, LaneFix

def setup_test_environment():
    """Setup test environment - use original folder directly"""
    # Use the provided test folder directly (no copy to avoid large data duplication)
    testdata_path = r"C:\Users\du\Desktop\testdata\20251002"

    if not os.path.exists(testdata_path):
        print(f"Test data path not found: {testdata_path}")
        return None

    print(f"Using test environment at: {testdata_path}")
    print("WARNING: Testing directly on original data. Lane files may be modified.")
    return testdata_path

def test_lane_operations(main_window, fileid_manager, app):
    """Test various lane operations"""
    results = []

    if not fileid_manager.fileid_list:
        return results

    # Initialize timestamps
    timestamp = None
    timestamp2 = None
    timestamp3 = None

    # Test 1: Add lane to first FileID
    print("\n=== Test 1: Adding lane to first FileID ===")
    first_fileid = fileid_manager.fileid_list[0]
    main_window.load_fileid(first_fileid)
    app.processEvents()

    if not hasattr(main_window.photo_tab, 'lane_manager') or not main_window.photo_tab.lane_manager:
        results.append(("Test 1", False, "No lane manager"))
        return results

    lane_manager = main_window.photo_tab.lane_manager

    # Get valid timestamps within the FileID's time range
    if lane_manager.first_image_timestamp and lane_manager.last_image_timestamp:
        time_range = lane_manager.last_image_timestamp - lane_manager.first_image_timestamp
        total_seconds = time_range.total_seconds()
        print(f"Time range: {total_seconds:.1f} seconds from {lane_manager.first_image_timestamp} to {lane_manager.last_image_timestamp}")
        
        if total_seconds > 10:  # At least 10 seconds of data
            timestamp = lane_manager.first_image_timestamp + timedelta(seconds=2)  # 2 seconds in
            
            if total_seconds > 30:  # More than 30 seconds
                timestamp2 = timestamp + timedelta(seconds=10)  # 10 seconds later
                timestamp3 = timestamp2 + timedelta(seconds=10)  # Another 10 seconds later
            else:
                # Medium time range, use two timestamps
                timestamp2 = timestamp + timedelta(seconds=total_seconds/4)
                timestamp3 = None
        else:
            # Very short time range, use single timestamp near the middle
            timestamp = lane_manager.first_image_timestamp + time_range / 2
            timestamp2 = None
            timestamp3 = None
    else:
        results.append(("Test 1", False, "No valid time range"))
        return results

    # Now assign lanes at valid timestamps
    success = lane_manager.assign_lane('1', timestamp)
    print(f"Assigned lane '1' at {timestamp}: {success}")
    print(f"Current lane fixes count: {len(lane_manager.lane_fixes)}")
    if lane_manager.lane_fixes:
        fix = lane_manager.lane_fixes[-1]
        print(f"Last fix: {fix.from_time} to {fix.to_time}, lane={fix.lane}")

    if timestamp2:
        success2 = lane_manager.assign_lane('2', timestamp2)
        print(f"Assigned lane '2' at {timestamp2}: {success2}")
        print(f"Current lane fixes count after 2: {len(lane_manager.lane_fixes)}")
    else:
        success2 = True  # No second timestamp to assign

    # Check current state
    lane_at_1 = lane_manager.get_lane_at_timestamp(timestamp)
    lane_at_2 = lane_manager.get_lane_at_timestamp(timestamp2) if timestamp2 else None
    print(f"Lane at time 1: {lane_at_1}, Lane at time 2: {lane_at_2}")

    expected_success = success and (success2 if timestamp2 else True)
    expected_lanes = lane_at_1 == '1' and (lane_at_2 == '2' if timestamp2 else True)
    results.append(("Test 1 - Add lanes", expected_success and expected_lanes, f"Lanes: {lane_at_1}, {lane_at_2}"))

    # Test 2: Change lane
    print("\n=== Test 2: Changing lane ===")
    if timestamp3:
        # Change from lane 2 to lane 3
        success3 = lane_manager.change_lane_smart('3', timestamp3)
        print(f"Changed to lane '3' at {timestamp3}: {success3}")

        lane_at_3 = lane_manager.get_lane_at_timestamp(timestamp3)
        print(f"Lane at time 3: {lane_at_3}")
        results.append(("Test 2 - Change lane", lane_at_3 == '3', f"Lane: {lane_at_3}"))
    else:
        results.append(("Test 2", True, "No third timestamp available"))

    # Test 3: Switch to second FileID and back
    print("\n=== Test 3: Switching FileIDs ===")
    if len(fileid_manager.fileid_list) > 1:
        second_fileid = fileid_manager.fileid_list[1]
        print(f"Switching to {second_fileid.fileid}")
        main_window.load_fileid(second_fileid)
        app.processEvents()

        # Do some operations on second FileID
        if hasattr(main_window.photo_tab, 'lane_manager') and main_window.photo_tab.lane_manager:
            second_lane_manager = main_window.photo_tab.lane_manager
            if main_window.photo_tab.image_paths:
                second_metadata = main_window.photo_tab.current_metadata
                if second_metadata and 'timestamp' in second_metadata:
                    second_timestamp = second_metadata['timestamp']
                    success_second = second_lane_manager.assign_lane('4', second_timestamp)
                    print(f"Assigned lane '4' to second FileID at {second_timestamp}: {success_second}")

        # Switch back to first FileID
        print(f"Switching back to {first_fileid.fileid}")
        main_window.load_fileid(first_fileid)
        app.processEvents()

        # Check if lanes persisted
        if hasattr(main_window.photo_tab, 'lane_manager'):
            back_lane_manager = main_window.photo_tab.lane_manager
            if timestamp is not None:
                lane_after_switch_1 = back_lane_manager.get_lane_at_timestamp(timestamp)
                lane_after_switch_2 = back_lane_manager.get_lane_at_timestamp(timestamp2) if timestamp2 else None
                lane_after_switch_3 = back_lane_manager.get_lane_at_timestamp(timestamp3) if timestamp3 else None
                print(f"After switch - Lane at time 1: {lane_after_switch_1}")
                print(f"After switch - Lane at time 2: {lane_after_switch_2}")
                print(f"After switch - Lane at time 3: {lane_after_switch_3}")

                persisted = (lane_after_switch_1 == '1' and
                           (lane_after_switch_2 == '2' if timestamp2 else True) and
                           (lane_after_switch_3 == '3' if timestamp3 else True))
                results.append(("Test 3 - Persistence after switch", persisted,
                              f"Lanes: {lane_after_switch_1}, {lane_after_switch_2}, {lane_after_switch_3}"))
            else:
                results.append(("Test 3", False, "No timestamp to check"))
        else:
            results.append(("Test 3", False, "No lane manager after switch back"))
    else:
        results.append(("Test 3", False, "Only one FileID"))

    # Test 4: Test with third FileID if available
    print("\n=== Test 4: Multiple FileID operations ===")
    if len(fileid_manager.fileid_list) > 2:
        third_fileid = fileid_manager.fileid_list[2]
        print(f"Switching to {third_fileid.fileid}")
        main_window.load_fileid(third_fileid)
        app.processEvents()

        # Switch back to first
        main_window.load_fileid(first_fileid)
        app.processEvents()

        # Check persistence again
        if hasattr(main_window.photo_tab, 'lane_manager'):
            final_lane_manager = main_window.photo_tab.lane_manager
            if timestamp is not None:
                final_lane_1 = final_lane_manager.get_lane_at_timestamp(timestamp)
                final_lane_2 = final_lane_manager.get_lane_at_timestamp(timestamp2) if timestamp2 else None
                final_lane_3 = final_lane_manager.get_lane_at_timestamp(timestamp3) if timestamp3 else None
                print(f"Final check - Lane at time 1: {final_lane_1}")
                print(f"Final check - Lane at time 2: {final_lane_2}")
                print(f"Final check - Lane at time 3: {final_lane_3}")

                final_persisted = (final_lane_1 == '1' and
                                 (final_lane_2 == '2' if timestamp2 else True) and
                                 (final_lane_3 == '3' if timestamp3 else True))
                results.append(("Test 4 - Final persistence", final_persisted,
                              f"Lanes: {final_lane_1}, {final_lane_2}, {final_lane_3}"))
            else:
                results.append(("Test 4", False, "No timestamp"))
        else:
            results.append(("Test 4", False, "No lane manager"))
    else:
        results.append(("Test 4", True, "Only two FileIDs available"))

    return results

def test_output_generation(main_window, fileid_manager, testdata_path, app):
    """Test output file generation"""
    results = []

    print("\n=== Testing Output Generation ===")

    # Force save all data
    main_window.auto_save_all_data_on_close()
    app.processEvents()  # Ensure save operations complete
    app.processEvents()  # Ensure save operations complete

    # Check per-FileID files
    print("Checking per-FileID lane files...")
    for fileid_folder in fileid_manager.fileid_list:
        lane_file = os.path.join(fileid_folder.path, f"{fileid_folder.fileid}_lane_fixes.csv")
        if os.path.exists(lane_file):
            with open(lane_file, 'r') as f:
                content = f.read().strip()
                lines = content.split('\n')
                print(f"FileID {fileid_folder.fileid}: {len(lines)-1} lane fixes")  # -1 for header
                results.append((f"Per-FileID {fileid_folder.fileid}", len(lines) > 1, f"{len(lines)-1} fixes"))
        else:
            print(f"FileID {fileid_folder.fileid}: No lane file")
            results.append((f"Per-FileID {fileid_folder.fileid}", False, "No file"))

    # Check merged file
    merged_file = os.path.join(testdata_path, f"laneFixes-{datetime.now().strftime('%d-%m-%Y')}.csv")
    if os.path.exists(merged_file):
        with open(merged_file, 'r') as f:
            content = f.read().strip()
            lines = content.split('\n')
            print(f"Merged file: {len(lines)-1} total lane fixes")
            results.append(("Merged file", len(lines) > 1, f"{len(lines)-1} fixes"))
            print("Merged file content preview:")
            print(content[:500] + "..." if len(content) > 500 else content)
    else:
        print("No merged file found")
        results.append(("Merged file", False, "No file"))

    return results

def run_comprehensive_test():
    """Run comprehensive lane persistence test"""
    print("=== Comprehensive Lane Persistence Test ===")

    # Setup test environment
    testdata_path = setup_test_environment()
    if not testdata_path:
        return

    # Create application
    app = QApplication(sys.argv)

    # Create main window
    main_window = MainWindow()
    main_window.show()

    # Wait for initialization
    app.processEvents()

    # Scan test data
    fileid_manager = main_window.fileid_manager
    fileid_manager.scan_parent_folder(testdata_path)
    print(f"Found {len(fileid_manager.fileid_list)} FileIDs")

    # Run lane operations tests
    operation_results = test_lane_operations(main_window, fileid_manager, app)

    # Run output tests
    output_results = test_output_generation(main_window, fileid_manager, testdata_path, app)

    # Summary
    print("\n=== Test Results Summary ===")
    all_results = operation_results + output_results

    passed = 0
    total = len(all_results)

    for test_name, success, details in all_results:
        status = "PASS" if success else "FAIL"
        print(f"{status}: {test_name} - {details}")
        if success:
            passed += 1

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed. Check output above.")

    # Cleanup
    main_window.close()
    app.quit()

    # No cleanup needed for original folder
    print("Test completed. Original data folder was used directly.")

if __name__ == "__main__":
    run_comprehensive_test()