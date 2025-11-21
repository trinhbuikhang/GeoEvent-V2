"""
Simple test to check if lane information persists across FileID switches
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from app.main_window import MainWindow

def test_lane_switch():
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()

    # Scan testdata
    testdata_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'testdata', '20251002')
    if os.path.exists(testdata_path):
        main_window.fileid_manager.scan_parent_folder(testdata_path)
        print(f"Scanned {len(main_window.fileid_manager.fileid_list)} FileIDs")

        if len(main_window.fileid_manager.fileid_list) >= 2:
            # Load first FileID
            first_fileid = main_window.fileid_manager.fileid_list[0]
            main_window.load_fileid(first_fileid)
            app.processEvents()

            # Check lane manager
            if hasattr(main_window.photo_tab, 'lane_manager') and main_window.photo_tab.lane_manager:
                print(f"First FileID: {first_fileid.fileid}")
                print(f"Lane manager: {id(main_window.photo_tab.lane_manager)}")
                print(f"Lane fixes count: {len(main_window.photo_tab.lane_manager.lane_fixes)}")

                # Switch to second FileID
                second_fileid = main_window.fileid_manager.fileid_list[1]
                main_window.load_fileid(second_fileid)
                app.processEvents()

                print(f"Switched to: {second_fileid.fileid}")
                print(f"Lane manager: {id(main_window.photo_tab.lane_manager)}")
                print(f"Lane fixes count: {len(main_window.photo_tab.lane_manager.lane_fixes)}")

                # Switch back
                main_window.load_fileid(first_fileid)
                app.processEvents()

                print(f"Switched back to: {first_fileid.fileid}")
                print(f"Lane manager: {id(main_window.photo_tab.lane_manager)}")
                print(f"Lane fixes count: {len(main_window.photo_tab.lane_manager.lane_fixes)}")

                # Check if lane manager is the same object
                if id(main_window.photo_tab.lane_manager) == id(main_window.photo_tab.lane_managers_per_fileid.get(first_fileid.fileid)):
                    print("Lane manager is cached correctly")
                else:
                    print("Lane manager is NOT cached correctly")
            else:
                print("No lane manager for first FileID")
        else:
            print("Need at least 2 FileIDs")
    else:
        print(f"Test data not found: {testdata_path}")

    main_window.close()

if __name__ == "__main__":
    test_lane_switch()