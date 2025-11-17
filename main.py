#!/usr/bin/env python3
"""
GeoEvent Application - Main Entry Point
PyQt6-based road survey event coding application
"""

import sys
import os
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor
from app.main_window import MainWindow

def setup_logging():
    """Setup logging configuration"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)  # Log to console/terminal
        ]
    )
    
    # Set specific loggers to DEBUG level for more detailed output
    logging.getLogger('app.utils.data_loader').setLevel(logging.DEBUG)
    logging.getLogger('app.ui.photo_preview_tab').setLevel(logging.DEBUG)
    logging.getLogger('app.ui.timeline_widget').setLevel(logging.DEBUG)
    
    logging.info("GeoEvent application starting...")

def main():
    """Main application entry point"""
    # Setup logging first
    setup_logging()
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("GeoEvent")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("GeoEvent Team")
    app.setStyle("Fusion")  # ép style
    
    # Set custom palette to override system theme
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))  # Light gray background
    palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))  # Black text
    palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))  # White base
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))  # Light alternate
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))  # Light yellow tooltip
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))  # Black tooltip text
    palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))  # Black text
    palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))  # Light gray buttons
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))  # Black button text
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))  # White bright text
    palette.setColor(QPalette.ColorRole.Link, QColor(0, 0, 255))  # Blue links
    palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 215))  # Blue highlight
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))  # White highlighted text
    app.setPalette(palette)
    # Create and show main window
    window = MainWindow()
    window.showMaximized()

    # Start event loop
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())