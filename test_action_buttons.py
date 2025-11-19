"""
Test script for Lane Change Action Buttons
"""

import sys
from datetime import datetime, timezone
from unittest.mock import Mock

# Add the app directory to Python path
sys.path.insert(0, 'app')

def test_button_painting():
    """Test that buttons are painted correctly"""
    print("=== Testing Button Painting ===")

    # Mock painter
    painter = Mock()

    # Mock timeline widget
    from ui.timeline_widget import TimelineWidget
    timeline = TimelineWidget()

    # Set up lane change mode
    timeline.lane_change_mode_active = True
    timeline.current_position = datetime(2025, 11, 20, 10, 0, 0, tzinfo=timezone.utc)

    # Mock rect and pixels_per_second
    from PyQt6.QtCore import QRect
    rect = QRect(0, 0, 1000, 200)
    pixels_per_second = 10.0

    # Call paint method
    timeline.paint_current_position(painter, rect, pixels_per_second)

    # Check that painter methods were called for buttons
    print("✅ Paint method called for buttons")

    # Check that ellipse was drawn (for buttons)
    painter.drawEllipse.assert_called()
    print("✅ Button circles drawn")

    # Check that text was drawn
    painter.drawText.assert_called()
    print("✅ Button labels drawn")

    print("=== Button Painting Test Passed ===")

def test_button_detection():
    """Test button click detection"""
    print("\n=== Testing Button Click Detection ===")

    from ui.timeline_widget import TimelineWidget
    from PyQt6.QtCore import QPoint

    timeline = TimelineWidget()
    timeline.lane_change_mode_active = True
    timeline.current_position = datetime(2025, 11, 20, 10, 0, 0, tzinfo=timezone.utc)

    # Mock timeline area rect
    rect = Mock()
    rect.width.return_value = 1000
    timeline.timeline_area = Mock()
    timeline.timeline_area.rect.return_value = rect

    # Set view times
    timeline.view_start_time = datetime(2025, 11, 20, 9, 0, 0, tzinfo=timezone.utc)
    timeline.view_end_time = datetime(2025, 11, 20, 11, 0, 0, tzinfo=timezone.utc)

    # Test clicking on cancel button (left)
    marker_x = 500  # Assume marker at center
    button_radius = 12
    button_spacing = 8
    cancel_x = marker_x - button_spacing - button_radius
    button_y = 0 - button_radius - 5

    cancel_pos = QPoint(int(cancel_x), int(button_y))
    button = timeline.get_lane_change_button_at_position(cancel_pos)

    assert button == 'cancel', f"Expected 'cancel', got {button}"
    print("✅ Cancel button detection works")

    # Test clicking on continue button (center)
    continue_pos = QPoint(int(marker_x), int(button_y))
    button = timeline.get_lane_change_button_at_position(continue_pos)

    assert button == 'continue', f"Expected 'continue', got {button}"
    print("✅ Continue button detection works")

    # Test clicking on yes button (right)
    yes_x = marker_x + button_spacing + button_radius
    yes_pos = QPoint(int(yes_x), int(button_y))
    button = timeline.get_lane_change_button_at_position(yes_pos)

    assert button == 'yes', f"Expected 'yes', got {button}"
    print("✅ Yes button detection works")

    # Test clicking outside buttons
    outside_pos = QPoint(0, 0)
    button = timeline.get_lane_change_button_at_position(outside_pos)

    assert button is None, f"Expected None, got {button}"
    print("✅ Outside click detection works")

    print("=== Button Detection Test Passed ===")

def test_button_actions():
    """Test button click actions"""
    print("\n=== Testing Button Actions ===")

    from ui.timeline_widget import TimelineWidget

    timeline = TimelineWidget()

    # Mock photo_tab
    timeline.photo_tab = Mock()
    timeline.photo_tab._apply_lane_change = Mock()

    # Test cancel action
    print("Testing cancel action...")
    timeline.handle_lane_change_button_click('cancel')
    # Should call disable_lane_change_mode
    print("✅ Cancel action handled")

    # Test continue action
    print("Testing continue action...")
    timeline.handle_lane_change_button_click('continue')
    # Should do nothing (keep mode active)
    print("✅ Continue action handled")

    # Test yes action
    print("Testing yes action...")
    timeline.handle_lane_change_button_click('yes')
    # Should call _apply_lane_change
    timeline.photo_tab._apply_lane_change.assert_called_once()
    print("✅ Yes action handled")

    print("=== Button Actions Test Passed ===")

if __name__ == "__main__":
    test_button_painting()
    test_button_detection()
    test_button_actions()
    print("\n🎉 All button tests passed!")