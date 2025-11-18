#!/usr/bin/env python3
"""
Test Timeline Zoom Functionality
"""

import sys
import os
from datetime import datetime, timezone, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_timeline_zoom():
    """Test timeline zoom functionality"""
    from PyQt6.QtWidgets import QApplication
    from app.ui.timeline_widget import TimelineWidget
    from app.models.event_model import Event

    app = QApplication(sys.argv)

    try:
        # Create timeline widget
        timeline = TimelineWidget()
        print("TimelineWidget created successfully")

        # Create test events
        base_time = datetime(2025, 10, 2, 8, 22, 0, tzinfo=timezone.utc)
        events = [
            Event(
                event_id="test_1",
                event_name="Bridge",
                start_time=base_time,
                end_time=base_time + timedelta(seconds=30),
                start_chainage=1000.0,
                end_chainage=1050.0
            ),
            Event(
                event_id="test_2",
                event_name="Intersection",
                start_time=base_time + timedelta(seconds=60),
                end_time=base_time + timedelta(seconds=90),
                start_chainage=1100.0,
                end_chainage=1150.0
            )
        ]
        timeline.set_events(events)
        print("Events set successfully")

        # Check initial view range
        print(f"Initial view range: {timeline.view_start_time} - {timeline.view_end_time}")
        print(f"Base view range: {timeline.base_view_start_time} - {timeline.base_view_end_time}")

        # Test zoom in
        print("\nTesting zoom in...")
        initial_range = (timeline.view_end_time - timeline.view_start_time).total_seconds()
        timeline.zoom_changed(200)  # zoom_level = 2.0
        zoomed_range = (timeline.view_end_time - timeline.view_start_time).total_seconds()
        print(f"After zoom in: range {zoomed_range}s (was {initial_range}s)")
        assert zoomed_range < initial_range, "Zoom in should reduce time range"

        # Test zoom out
        print("\nTesting zoom out...")
        timeline.zoom_changed(50)  # zoom_level = 0.5
        zoomed_out_range = (timeline.view_end_time - timeline.view_start_time).total_seconds()
        print(f"After zoom out: range {zoomed_out_range}s (was {zoomed_range}s)")
        assert zoomed_out_range > zoomed_range, "Zoom out should increase time range"

        # Test zoom back to normal
        print("\nTesting zoom to normal...")
        timeline.zoom_changed(100)  # zoom_level = 1.0
        normal_range = (timeline.view_end_time - timeline.view_start_time).total_seconds()
        print(f"After zoom normal: range {normal_range}s")
        assert abs(normal_range - initial_range) < 1, "Zoom to 1.0 should restore original range"

        print("\n✓ Timeline zoom test passed!")
        return True

    except Exception as e:
        print(f"✗ Timeline zoom test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        app.quit()

if __name__ == "__main__":
    success = test_timeline_zoom()
    sys.exit(0 if success else 1)