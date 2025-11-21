"""
Test script để kiểm tra validation trong app context
"""

import os
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.utils.data_loader import DataLoader
from app.ui.photo_preview_tab import PhotoPreviewTab
from PyQt6.QtWidgets import QApplication

def test_app_validation():
    """Test validation in app context"""

    # Test data directory
    testdata_path = Path("testdata/20251002")
    if not testdata_path.exists():
        print(f"Test data not found: {testdata_path}")
        return

    # Find first FileID folder
    for item in testdata_path.iterdir():
        if item.is_dir() and item.name.startswith('0D25'):
            # Create a simple fileid object
            class FileID:
                def __init__(self, fileid, path):
                    self.fileid = fileid
                    self.path = path

            fileid_obj = FileID(item.name, str(item))
            break
    else:
        print("No FileID folders found")
        return

    print(f"Testing FileID: {fileid_obj.fileid} in DataLoader context")

    # Test DataLoader validation (this is what gets called in app)
    try:
        data_loader = DataLoader()
        result = data_loader.load_fileid_data(fileid_obj)

        print("DataLoader loaded successfully with validation checks")

        # Check lane manager validation
        lane_manager = result['lane_manager']
        if lane_manager:
            validation_errors = lane_manager.validate_lane_fixes_time_bounds()
            if validation_errors:
                print(f"❌ Lane manager validation failed with {len(validation_errors)} errors")
                for error in validation_errors[:3]:
                    print(f"  {error}")
            else:
                print("✅ Lane manager validation passed")

        print("DataLoader validation checks completed")

    except Exception as e:
        print(f"Error testing DataLoader validation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_app_validation()