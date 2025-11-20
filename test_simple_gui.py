#!/usr/bin/env python3
"""
Simple GUI to test image loading and navigation
"""

import sys
import os
import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame
)
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt

class SimpleImageViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.image_paths = []
        self.current_index = -1

        self.setup_ui()
        self.load_images()
        self.show()

    def setup_ui(self):
        """Setup the UI"""
        self.setWindowTitle("Simple Image Viewer Test")
        self.setGeometry(100, 100, 1200, 800)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        layout = QVBoxLayout(central_widget)

        # Image display area
        self.image_label = QLabel("No image loaded")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(800, 600)
        self.image_label.setStyleSheet("border: 1px solid black; background-color: #f0f0f0;")
        layout.addWidget(self.image_label)

        # Navigation controls
        nav_layout = QHBoxLayout()

        self.prev_btn = QPushButton("◀ Prev")
        self.prev_btn.clicked.connect(self.prev_image)
        self.prev_btn.setEnabled(False)
        nav_layout.addWidget(self.prev_btn)

        self.position_label = QLabel("0 / 0")
        self.position_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.position_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        nav_layout.addWidget(self.position_label)

        self.next_btn = QPushButton("Next ▶")
        self.next_btn.clicked.connect(self.next_image)
        self.next_btn.setEnabled(False)
        nav_layout.addWidget(self.next_btn)

        layout.addLayout(nav_layout)

        # Status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

    def load_images(self):
        """Load images from the Cam1 folder"""
        # Path to the test folder
        test_folder = Path("testdata/err/0D2510020844387700/Cam1")
        if not test_folder.exists():
            self.status_label.setText(f"Test folder not found: {test_folder}")
            return

        # Find all .jpg files
        image_files = list(test_folder.glob("*.jpg"))
        image_files.sort()  # Sort by filename

        self.image_paths = [str(f) for f in image_files]

        self.status_label.setText(f"Loaded {len(self.image_paths)} images")

        if self.image_paths:
            self.navigate_to_image(0)

    def navigate_to_image(self, index):
        """Navigate to specific image"""
        if 0 <= index < len(self.image_paths):
            self.current_index = index
            self.load_current_image()
            self.update_navigation()

    def load_current_image(self):
        """Load and display current image"""
        if self.current_index < 0 or self.current_index >= len(self.image_paths):
            return

        image_path = self.image_paths[self.current_index]

        # Load image
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.image_label.setText(f"Failed to load: {os.path.basename(image_path)}")
            self.status_label.setText(f"Failed to load image: {image_path}")
            return

        # Scale image to fit
        scaled_pixmap = pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        self.image_label.setPixmap(scaled_pixmap)
        self.status_label.setText(f"Loaded: {os.path.basename(image_path)}")

    def update_navigation(self):
        """Update navigation buttons and position label"""
        total = len(self.image_paths)
        current = self.current_index + 1

        self.position_label.setText(f"{current} / {total}")
        self.prev_btn.setEnabled(self.current_index > 0)
        self.next_btn.setEnabled(self.current_index < total - 1)

    def prev_image(self):
        """Navigate to previous image"""
        if self.current_index > 0:
            self.navigate_to_image(self.current_index - 1)

    def next_image(self):
        """Navigate to next image"""
        if self.current_index < len(self.image_paths) - 1:
            self.navigate_to_image(self.current_index + 1)

    def resizeEvent(self, event):
        """Handle window resize to rescale image"""
        super().resizeEvent(event)
        if self.image_paths and self.current_index >= 0:
            self.load_current_image()

def main():
    """Main function"""
    app = QApplication(sys.argv)
    app.setApplicationName("Simple Image Viewer")

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    viewer = SimpleImageViewer()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())