"""
Test script để kiểm tra validation integration trong app
"""

import os
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.utils.data_loader import DataLoader
from app.models.lane_model import LaneManager

def test_validation_integration():
    """Test that validation is integrated into DataLoader and LaneManager"""

    # Test data directory
    testdata_path = Path("testdata/20251002")
    if not testdata_path.exists():
        print(f"Test data not found: {testdata_path}")
        return

    # Find all FileID folders
    fileid_folders = []
    for item in testdata_path.iterdir():
        if item.is_dir() and (item.name.startswith('0D25') or len(item.name) == 16):
            # Create a simple fileid object
            class FileID:
                def __init__(self, fileid, path):
                    self.fileid = fileid
                    self.path = path

            fileid_folders.append(FileID(item.name, str(item)))

    if not fileid_folders:
        print("No FileID folders found")
        return

    # Test all FileIDs
    for fileid_obj in fileid_folders:
        print(f"\n--- Testing FileID: {fileid_obj.fileid} ---")

        # Create DataLoader and load data
        data_loader = DataLoader()
        result = data_loader.load_fileid_data(fileid_obj)

        # Check that lane manager has metadata set
        lane_manager = result['lane_manager']
        print(f"Lane manager has {len(lane_manager.lane_fixes)} fixes")

        # Test validation
        validation_errors = lane_manager.validate_lane_fixes_time_bounds()
        if validation_errors:
            print(f"❌ Validation failed with {len(validation_errors)} errors:")
            for error in validation_errors[:2]:  # Show first 2
                print(f"  {error}")
        else:
            print("✅ Validation passed - all lane fixes within time bounds")

    print("\nTest completed!")

if __name__ == "__main__":
    test_validation_integration()