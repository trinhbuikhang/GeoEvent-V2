#!/usr/bin/env python3
"""
Simple test to verify timeline marker visibility - LARGE WINDOW
"""

import sys
from datetime import datetime, timedelta
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

# Add project path
sys.path.insert(0, '.')

from app.ui.timeline_widget import TimelineWidget

class MarkerTest(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Timeline Marker Test - LARGE WINDOW")
        self.setGeometry(100, 100, 1200, 600)  # Much larger window

        layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel("LOOK FOR BRIGHT YELLOW MARKER:\n"
                            "• Thick yellow vertical line through timeline\n"
                            "• Large yellow circle above timeline\n"
                            "• Large yellow arrow at top pointing down\n"
                            "• Yellow connecting line from arrow to timeline\n"
                            "If you still don't see it, the marker may be positioned outside the visible area.")
        instructions.setStyleSheet("font-size: 14px; padding: 15px; background-color: #FFFF99; border: 2px solid #FF0000;")
        layout.addWidget(instructions)

        # Timeline widget
        self.timeline = TimelineWidget()
        layout.addWidget(self.timeline)

        # Set view range to show a wide time span
        start_time = datetime(2024, 1, 1, 11, 55, 0)
        end_time = datetime(2024, 1, 1, 12, 5, 0)
        self.timeline.view_start_time = start_time
        self.timeline.view_end_time = end_time

        # Set current position in the middle
        current_pos = datetime(2024, 1, 1, 12, 0, 0)
        self.timeline.set_current_position(current_pos)

        # Status
        self.status = QLabel(f"Current position: {current_pos}\n"
                           f"View range: {start_time} to {end_time}\n"
                           f"Window size: 1200x600")
        self.status.setStyleSheet("font-size: 12px; padding: 10px;")
        layout.addWidget(self.status)

        # Force repaint
        self.timeline.repaint()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    test = MarkerTest()
    test.show()
    print("LARGE test window opened. Look for BRIGHT YELLOW marker components.")
    print("If still not visible, marker may be outside visible time range.")
    sys.exit(app.exec())