#!/usr/bin/env python3
"""
Simple GUI to test timeline zoom functionality
"""

import sys
import os
from datetime import datetime, timezone, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt

from app.ui.timeline_widget import TimelineWidget
from app.models.event_model import Event

class ZoomTestWindow(QMainWindow):
    """Simple window to test timeline zoom"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Timeline Zoom Test")
        self.setGeometry(100, 100, 1200, 600)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Info label
        self.info_label = QLabel("Timeline Zoom Test - Adjust zoom to see time range changes")
        layout.addWidget(self.info_label)

        # Create timeline widget
        self.timeline = TimelineWidget()
        layout.addWidget(self.timeline)

        # Status label
        self.status_label = QLabel("Status: Ready")
        layout.addWidget(self.status_label)

        # Connect to timeline signals to update status
        self.timeline.zoom_slider.valueChanged.connect(self.update_status)

        # Setup test data
        self.setup_test_data()

    def setup_test_data(self):
        """Setup test events and time range"""
        # Create test events - some very short
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
                event_name="Short Event",  # Very short event - only 3 seconds
                start_time=base_time + timedelta(seconds=15),
                end_time=base_time + timedelta(seconds=18),
                start_chainage=1100.0,
                end_chainage=1110.0
            ),
            Event(
                event_id="test_3",
                event_name="Intersection",
                start_time=base_time + timedelta(seconds=60),
                end_time=base_time + timedelta(seconds=90),
                start_chainage=1200.0,
                end_chainage=1250.0
            )
        ]

        self.timeline.set_events(events)

        # Set image time range (simulating folder images)
        start_time = base_time - timedelta(seconds=30)
        end_time = base_time + timedelta(seconds=120)
        self.timeline.set_image_time_range(start_time, end_time)

        # Set current position
        self.timeline.set_current_position(base_time + timedelta(seconds=22))

        self.update_status()

    def update_status(self, value=None):
        """Update status label with current zoom and time range"""
        zoom_level = self.timeline.zoom_level
        if self.timeline.view_start_time and self.timeline.view_end_time:
            duration = (self.timeline.view_end_time - self.timeline.view_start_time).total_seconds()
            time_range = f"{self.timeline.view_start_time.strftime('%H:%M:%S')} - {self.timeline.view_end_time.strftime('%H:%M:%S')}"
            status = f"Zoom: {zoom_level:.2f} | Duration: {duration:.1f}s | Range: {time_range}"
        else:
            status = f"Zoom: {zoom_level:.2f} | No time range set"

        self.status_label.setText(f"Status: {status}")

def main():
    """Main function"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = ZoomTestWindow()
    window.show()

    return app.exec()

if __name__ == "__main__":
    sys.exit(main())