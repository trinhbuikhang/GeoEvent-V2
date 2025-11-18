"""
Test file for lane assignment functionality
Tests various failure cases when user clicks lane buttons
"""

import sys
import os
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication, QPushButton
from PyQt6.QtCore import Qt

from app.ui.photo_preview_tab import PhotoPreviewTab
from app.models.lane_model import LaneManager


def test_assign_lane_no_metadata():
    """Test assign_lane when no current metadata exists"""
    # Setup mock main window
    mock_main_window = Mock()
    mock_main_window.fileid_manager = Mock()
    mock_main_window.fileid_manager.get_current_fileid.return_value = None

    # Create PhotoPreviewTab
    tab = PhotoPreviewTab(mock_main_window)

    # Setup: No metadata
    tab.current_metadata = {}

    # Action: Try to assign lane
    tab.assign_lane('1')

    # Assert: Should return early, no changes
    assert tab.current_metadata == {}

    print("✓ test_assign_lane_no_metadata passed")


def test_assign_lane_no_timestamp():
    """Test assign_lane when metadata exists but no timestamp"""
    # Setup mock main window
    mock_main_window = Mock()
    mock_main_window.fileid_manager = Mock()
    mock_main_window.fileid_manager.get_current_fileid.return_value = None

    # Create PhotoPreviewTab
    tab = PhotoPreviewTab(mock_main_window)

    # Setup: Metadata without timestamp
    tab.current_metadata = {'latitude': -43.5, 'longitude': 172.6}

    # Action: Try to assign lane
    tab.assign_lane('1')

    # Assert: Should return early
    assert 'timestamp' not in tab.current_metadata

    print("✓ test_assign_lane_no_timestamp passed")


def test_assign_lane_no_lane_manager():
    """Test assign_lane when no lane_manager is set"""
    # Setup mock main window
    mock_main_window = Mock()
    mock_main_window.fileid_manager = Mock()
    mock_main_window.fileid_manager.get_current_fileid.return_value = None

    # Create PhotoPreviewTab
    tab = PhotoPreviewTab(mock_main_window)

    # Setup: Valid metadata but no lane manager
    tab.current_metadata = {
        'timestamp': datetime(2025, 11, 18, 9, 0, 0, tzinfo=timezone.utc)
    }
    tab.lane_manager = None

    # Action: Try to assign lane
    tab.assign_lane('1')

    # Assert: Should return early
    assert tab.lane_manager is None

    print("✓ test_assign_lane_no_lane_manager passed")


def test_assign_lane_overlap_detected():
    """Test assign_lane when overlap is detected"""
    # Setup mock main window
    mock_main_window = Mock()
    mock_main_window.fileid_manager = Mock()
    mock_main_window.fileid_manager.get_current_fileid.return_value = None

    # Create PhotoPreviewTab
    tab = PhotoPreviewTab(mock_main_window)

    # Setup: Valid setup with existing lane assignment
    timestamp1 = datetime(2025, 11, 18, 9, 0, 0, tzinfo=timezone.utc)
    timestamp2 = datetime(2025, 11, 18, 9, 5, 0, tzinfo=timezone.utc)  # Overlapping

    lane_manager = LaneManager()
    lane_manager.set_fileid_folder('test', 'TEST_PLATE')
    end_time = datetime(2025, 11, 18, 10, 0, 0, tzinfo=timezone.utc)
    lane_manager.set_end_time(end_time)

    tab.current_metadata = {'timestamp': timestamp2}
    tab.lane_manager = lane_manager

    # First assignment succeeds
    success1 = lane_manager.assign_lane('1', timestamp1)
    assert success1 == True

    # Mock the update_lane_display to track calls
    tab.update_lane_display = Mock()

    # Action: Try to assign lane change (should succeed with smart change)
    tab.assign_lane('2')

    # Assert: Should succeed with smart change
    # Check that update_lane_display was called (since assignment succeeded)
    tab.update_lane_display.assert_called_once()

    print("✓ test_assign_lane_overlap_detected passed")


def test_ui_state_consistency():
    """Test that UI button states remain consistent with lane manager state"""
    # Setup mock main window
    mock_main_window = Mock()
    mock_main_window.fileid_manager = Mock()
    mock_main_window.fileid_manager.get_current_fileid.return_value = None

    # Create PhotoPreviewTab
    tab = PhotoPreviewTab(mock_main_window)

    # Setup lane manager
    lane_manager = LaneManager()
    lane_manager.set_fileid_folder('test', 'TEST_PLATE')
    end_time = datetime(2025, 11, 18, 10, 0, 0, tzinfo=timezone.utc)
    lane_manager.set_end_time(end_time)
    tab.lane_manager = lane_manager

    # Setup metadata
    timestamp = datetime(2025, 11, 18, 9, 0, 0, tzinfo=timezone.utc)
    tab.current_metadata = {'timestamp': timestamp, 'plate': 'TEST_PLATE'}

    # Initially no buttons should be checked
    assert not any(button.isChecked() for button in tab.lane_buttons.buttons())
    assert not tab.turn_right_btn.isChecked()
    assert not tab.turn_left_btn.isChecked()

    # Assign lane 1
    tab.assign_lane('1')

    # Check that Lane 1 button is checked
    lane1_button = None
    for button in tab.lane_buttons.buttons():
        if button.text() == 'Lane 1':
            lane1_button = button
            break
    assert lane1_button is not None
    assert lane1_button.isChecked()

    # Start a turn
    tab.start_turn('TM')

    # Check that turn right button is checked and lane button is still checked
    assert tab.turn_right_btn.isChecked()
    assert not tab.turn_left_btn.isChecked()
    assert lane1_button.isChecked()  # Should still be checked for TM1

    print("✓ test_ui_state_consistency passed")


if __name__ == "__main__":
    # Create QApplication
    app = QApplication([])

    try:
        test_assign_lane_no_metadata()
        test_assign_lane_no_timestamp()
        test_assign_lane_no_lane_manager()
        test_assign_lane_overlap_detected()
        test_ui_state_consistency()

        print("\n✅ All tests passed!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

    app.quit()