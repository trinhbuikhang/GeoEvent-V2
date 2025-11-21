"""
Test script để kiểm tra UI notification khi có lane fixes validation errors
"""

import os
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
import logging

def test_ui_validation_notification():
    """Test UI notification for lane fixes validation errors"""

    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Create QApplication
    app = QApplication(sys.argv)

    # Import after QApplication is created
    from app.ui.photo_preview_tab import PhotoPreviewTab
    from app.ui.timeline_widget import TimelineWidget

    # Test data directory
    testdata_path = Path("testdata/20251002")
    if not testdata_path.exists():
        print(f"Test data not found: {testdata_path}")
        return

    # Find FileID with known validation errors (0D2510020754197700)
    target_fileid = "0D2510020754197700"
    fileid_obj = None

    for item in testdata_path.iterdir():
        if item.is_dir() and item.name == target_fileid:
            # Create a simple fileid object
            class FileID:
                def __init__(self, fileid, path):
                    self.fileid = fileid
                    self.path = path

            fileid_obj = FileID(item.name, str(item))
            break

    if not fileid_obj:
        print(f"Target FileID {target_fileid} not found")
        return

    print(f"Testing UI notification for FileID: {fileid_obj.fileid}")

    try:
        # Create a mock main window
        class MockMainWindow:
            def __init__(self):
                self.photo_tab = None

        main_window = MockMainWindow()

        # Create timeline widget
        timeline = TimelineWidget()

        # Create photo preview tab
        photo_tab = PhotoPreviewTab(main_window)
        photo_tab.timeline = timeline
        main_window.photo_tab = photo_tab

        print("Loading FileID (this should show validation warning dialog)...")

        # Load FileID (this should trigger validation notification)
        photo_tab.load_fileid(fileid_obj)

        print("FileID loaded. If validation dialog appeared, test passed!")

        # Keep app running briefly to show dialog
        import time
        time.sleep(2)  # Give time for dialog to appear

        print("Test completed - check if warning dialog was shown")

    except Exception as e:
        print(f"Error testing UI validation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ui_validation_notification()