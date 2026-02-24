#!/usr/bin/env python3
"""
GeoEvent Application - Main Entry Point
PyQt6-based road survey event coding application
"""

import sys
import os
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor, QIcon
from app.main_window import MainWindow
from app.logging_config import setup_logging as setup_centralized_logging
from app.utils.resource_path import get_resource_path, get_app_base_dir


def _setup_dpi_awareness():
    """Set DPI awareness before any GUI for Windows 11 / high-DPI compatibility."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        # PROCESS_PER_MONITOR_DPI_AWARE = 2
        shcore = ctypes.windll.shcore
        shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def setup_logging():
    """Setup centralized logging configuration with rotation"""
    log_dir = str(get_app_base_dir() / "logs")
    logger = setup_centralized_logging(
        log_dir=log_dir,
        level=logging.DEBUG,  # Root level for file
        console_level=logging.INFO,  # Console shows INFO and above
        file_level=logging.DEBUG,  # File logs everything
        error_level=logging.ERROR  # Error file logs errors only
    )
    
    # Set specific module loggers if needed
    # Most verbose modules can be adjusted
    logging.getLogger('app.utils.image_utils').setLevel(logging.WARNING)  # Reduce noise from coordinate parsing
    logging.getLogger('PIL').setLevel(logging.WARNING)  # Suppress PIL debug messages
    
    return logger

def main():
    """Main application entry point"""
    _setup_dpi_awareness()
    setup_logging()

    app = QApplication(sys.argv)
    app.setApplicationName("GeoEvent")
    app.setApplicationVersion("2.0.24")
    app.setOrganizationName("Pavement Team")
    # Consistent scaling on Windows 11 high-DPI
    if hasattr(Qt, 'HighDpiScaleFactorRoundingPolicy'):
        app.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app.setStyle("Fusion")  # App-wide Fusion style
    icon_path = get_resource_path(os.path.join("app", "ui", "icon", "Event.ico"))
    app_icon = None
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)
    else:
        logging.warning("App icon not found at %s", icon_path)
    
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
    if app_icon:
        window.setWindowIcon(app_icon)
    window.showMaximized()

    # Start event loop
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
