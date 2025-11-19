"""
Test script for Lane Change Confirmation Dialog
"""

import sys
from datetime import datetime, timezone
from PyQt6.QtWidgets import QApplication

# Add the app directory to Python path
sys.path.insert(0, 'app')

from ui.lane_change_dialog import LaneChangeConfirmationDialog, LaneChangeResult

def test_dialog():
    """Test the lane change confirmation dialog"""
    app = QApplication(sys.argv)

    # Test data
    current_lane = "1"
    new_lane = "2"
    start_time = datetime(2025, 11, 20, 10, 0, 0, tzinfo=timezone.utc)
    end_time = datetime(2025, 11, 20, 10, 5, 0, tzinfo=timezone.utc)

    print("Testing Lane Change Confirmation Dialog...")
    print(f"Current lane: {current_lane}")
    print(f"New lane: {new_lane}")
    print(f"Start time: {start_time}")
    print(f"End time: {end_time}")

    # Show dialog
    result = LaneChangeConfirmationDialog.show_dialog(
        parent=None,
        current_lane=current_lane,
        new_lane=new_lane,
        start_time=start_time,
        end_time=end_time
    )

    print(f"Dialog result: {result}")
    print(f"Result name: {result.name}")

    if result == LaneChangeResult.CONFIRMED:
        print("✅ User confirmed the lane change")
    elif result == LaneChangeResult.CONTINUE:
        print("🔄 User wants to continue adjusting")
    elif result == LaneChangeResult.CANCELLED:
        print("❌ User cancelled the lane change")

    return result

if __name__ == "__main__":
    result = test_dialog()
    print(f"\nTest completed with result: {result}")