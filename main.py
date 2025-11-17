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

    # Create and show main window
    window = MainWindow()
    window.showMaximized()

    # Start event loop
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())