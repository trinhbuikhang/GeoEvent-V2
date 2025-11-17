#!/usr/bin/env python3
"""
Test script for TimelineWidget click detection
"""

import sys
import os
import logging
from datetime import datetime, timezone, timedelta
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPointF, QRect
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtCore import Qt

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.ui.timeline_widget import TimelineWidget
from app.models.event_model import Event
from app.models.gps_model import GPSData, GPSPoint
from app.utils.data_loader import DataLoader
from app.utils.fileid_manager import FileIDFolder

def setup_logging():
    """Setup logging"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

def create_test_data():
    """Create test data similar to the loaded FileID"""
    # Create GPS data
    gps_data = GPSData()
    base_time = datetime(2025, 10, 1, 19, 20, 19, tzinfo=timezone.utc)

    # Create GPS points (simplified)
    for i in range(100):
        point = GPSPoint(
            timestamp=base_time + timedelta(seconds=i),
            latitude=-43.5 + i * 0.001,
            longitude=172.65 + i * 0.001,
            chainage=i * 10.0
        )
        gps_data.points.append(point)

    # Create events
    events = []
    event_types = ['Bridge', 'Speed Hump', 'Intersection']
    for i, event_type in enumerate(event_types):
        event = Event(
            event_id=f"test_event_{i}",
            event_name=f"Test {event_type}",
            start_time=datetime(2025, 10, 1, 19, 22 + i*2, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 10, 1, 19, 23 + i*2, 0, tzinfo=timezone.utc),
            start_chainage=i * 100.0,
            end_chainage=(i + 1) * 100.0,
            file_id="test"
        )
        events.append(event)

    return gps_data, events

def test_timeline_clicks():
    """Test timeline click detection"""
    app = QApplication(sys.argv)

    # Create timeline widget
    timeline = TimelineWidget()
    timeline.resize(800, 200)  # Set size for rect calculations

    # Set test data
    gps_data, events = create_test_data()
    timeline.set_gps_data(gps_data)
    timeline.set_events(events)

    # Set current position
    current_pos = datetime(2025, 10, 1, 19, 25, 0, tzinfo=timezone.utc)
    timeline.set_current_position(current_pos)

    # Set view range
    timeline.view_start_time = datetime(2025, 10, 1, 19, 20, 0, tzinfo=timezone.utc)
    timeline.view_end_time = datetime(2025, 10, 1, 19, 40, 0, tzinfo=timezone.utc)
    timeline.zoom_level = 2.0  # Adjust zoom to fit marker in view

    # Force update
    timeline.update()

    print("Timeline setup complete")
    print(f"Current position: {timeline.current_position}")
    print(f"View range: {timeline.view_start_time} to {timeline.view_end_time}")
    print(f"GPS data points: {len(gps_data.points)}")
    print(f"Events: {len(events)}")

    # Get timeline rect
    rect = timeline.timeline_area.rect()
    print(f"Timeline rect: {rect}")

    # Calculate marker position
    timeline_rect = QRect(0, 40, rect.width(), rect.height() - 30)  # TIMELINE_TOP_MARGIN=40, CHAINAGE_SCALE_HEIGHT=30
    pixels_per_second = timeline.calculate_pixels_per_second(timeline_rect)
    marker_x = timeline.time_to_pixel(current_pos, pixels_per_second, timeline_rect.left())
    print(f"Marker x position: {marker_x}")

    # Test clicks at different positions
    test_positions = [
        (320, 25),  # On arrow (inside triangle)
        (320, 50),  # On line (below arrow)
        (308, 39),  # On arrow edge
        (100, 50),  # Random position
    ]

    for i, (x, y) in enumerate(test_positions):
        print(f"\n--- Test click {i+1}: pos ({x}, {y}) ---")

        # Create mouse event
        pos = QPointF(x, y)
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            pos,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )

        # Simulate click
        timeline.handle_left_click(event)

    print("\nTest completed")

if __name__ == "__main__":
    setup_logging()
    test_timeline_clicks()