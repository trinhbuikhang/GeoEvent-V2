"""
Main Window for GeoEvent Application
"""

import logging
import os
import csv
from datetime import datetime
from typing import List

from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QHBoxLayout,
    QSplitter, QStatusBar, QMenuBar, QToolBar,
    QFileDialog, QMessageBox, QLabel
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtWidgets import QApplication

from .ui.photo_preview_tab import PhotoPreviewTab
from .utils.settings_manager import SettingsManager
from .utils.fileid_manager import FileIDManager
from .utils.user_guide import show_user_guide
from .core.memory_manager import MemoryManager
from .core.autosave_manager import AutoSaveManager

class MainWindow(QMainWindow):
    """
    Main application window
    RESPONSIBILITIES:
    - Initialize application components
    - Manage menu bar (File, Edit, View, Help)
    - Handle theme switching
    - Coordinate between managers
    """

    def __init__(self):
        super().__init__()
        self.settings_manager = SettingsManager()
        self.fileid_manager = FileIDManager()
        self.memory_manager = MemoryManager()
        self.autosave_manager = AutoSaveManager()

        self.photo_tab = None

        self.setup_ui()
        self.load_settings()
        self.connect_signals()

    def setup_ui(self):
        """Create menu, toolbar, status bar"""
        self.setWindowTitle("GeoEvent - Road Survey Event Coding")
        self.setGeometry(100, 100, 1400, 900)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create main layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create toolbar
        self.create_toolbar()

        # Create status bar
        self.create_status_bar()

        # Create menu bar
        self.create_menu_bar()

        # Initialize photo preview tab (will be loaded when folder is selected)
        self.photo_tab = PhotoPreviewTab(self)
        layout.addWidget(self.photo_tab)

    def create_toolbar(self):
        """Create main toolbar"""
        toolbar = self.addToolBar("Main")
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        # FileID navigation moved to lane controls

    def create_status_bar(self):
        """Create status bar with memory and autosave info"""
        self.status_bar = self.statusBar()

        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)

        self.fileid_label = QLabel("No FileID loaded")
        self.status_bar.addPermanentWidget(self.fileid_label)

        self.status_bar.addPermanentWidget(QLabel("Memory: --%"))
        self.memory_label = QLabel("--%")
        self.status_bar.addPermanentWidget(self.memory_label)

        self.status_bar.addPermanentWidget(QLabel("Autosave: --"))
        self.autosave_label = QLabel("--")
        self.status_bar.addPermanentWidget(self.autosave_label)

    def create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")
        open_action = QAction("Open Folder...", self)
        open_action.triggered.connect(self.handle_folder_selection)
        file_menu.addAction(open_action)

        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        # Will add undo/redo actions later

        # View menu
        view_menu = menubar.addMenu("View")

        # Theme submenu
        theme_menu = view_menu.addMenu("Theme")
        theme_group = QActionGroup(self)

        light_theme = QAction("Light", self)
        light_theme.setCheckable(True)
        light_theme.triggered.connect(lambda: self.set_theme("light"))
        theme_group.addAction(light_theme)
        theme_menu.addAction(light_theme)

        dark_theme = QAction("Dark", self)
        dark_theme.setCheckable(True)
        dark_theme.setChecked(True)  # Default
        dark_theme.triggered.connect(lambda: self.set_theme("dark"))
        theme_group.addAction(dark_theme)
        theme_menu.addAction(dark_theme)

        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        # Will add export and other tools

        # Help menu
        help_menu = menubar.addMenu("Help")
        user_guide_action = QAction("User Guide", self)
        user_guide_action.triggered.connect(self.show_user_guide)
        help_menu.addAction(user_guide_action)

        help_menu.addSeparator()
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def connect_signals(self):
        """Connect signal handlers"""
        self.memory_manager.memory_warning.connect(self.handle_memory_warning)
        self.autosave_manager.autosave_triggered.connect(self.handle_autosave)

    def load_settings(self):
        """Restore window state"""
        settings = self.settings_manager.load_settings()

        # Restore window geometry
        if 'geometry' in settings:
            from PyQt6.QtCore import QByteArray
            geometry_data = settings['geometry']
            geometry = QByteArray.fromBase64(geometry_data.encode('latin1'))
            self.restoreGeometry(geometry)
        else:
            self.showMaximized()

        # Restore theme
        theme = settings.get('theme', 'dark')
        self.set_theme(theme)

    def handle_folder_selection(self):
        """Handle folder selection for single/multi-FileID mode"""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Survey Data Folder"
        )

        if folder_path:
            try:
                # Scan for FileIDs
                fileid_folders = self.fileid_manager.scan_parent_folder(folder_path)

                if not fileid_folders:
                    QMessageBox.warning(
                        self, "No Data Found",
                        "No valid FileID folders found in the selected directory."
                    )
                    return

                # Load first FileID
                self.load_fileid(fileid_folders[0])

                # Update navigation
                self.update_fileid_navigation()

            except Exception as e:
                QMessageBox.critical(
                    self, "Error",
                    f"Failed to load folder: {str(e)}"
                )

    def load_fileid(self, fileid_folder):
        """Load a specific FileID"""
        try:
            self.photo_tab.load_fileid(fileid_folder)
            # Update the FileIDManager's current index to match the loaded FileID
            self.fileid_manager.set_current_fileid(fileid_folder.fileid)
            self.update_fileid_navigation()
            self.status_label.setText("Ready")
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Failed to load FileID {fileid_folder.fileid}: {str(e)}"
            )

    def prev_fileid(self):
        """Navigate to previous FileID"""
        # Auto-save current data before switching - DISABLED to avoid overwriting unchanged events
        # self.auto_save_current_data()
        
        prev_fileid = self.fileid_manager.prev_fileid()
        if prev_fileid:
            self.load_fileid(prev_fileid)
            self.update_fileid_navigation()

    def next_fileid(self):
        """Navigate to next FileID"""
        # Auto-save current data before switching - DISABLED to avoid overwriting unchanged events
        # self.auto_save_current_data()
        
        next_fileid = self.fileid_manager.next_fileid()
        if next_fileid:
            self.load_fileid(next_fileid)
            self.update_fileid_navigation()

    def auto_save_current_data(self):
        """Auto-save events and lane fixes for current FileID"""
        if hasattr(self.photo_tab, 'current_fileid') and self.photo_tab.current_fileid:
            # Save events if modified
            if self.photo_tab.events_modified:
                success = self.photo_tab.save_all_events_internal()
                if success:
                    logging.info(f"Auto-saved {len(self.photo_tab.events)} modified events")
                else:
                    logging.error("Failed to auto-save modified events")

            # Save lane fixes if modified
            if hasattr(self.photo_tab, 'lane_manager') and self.photo_tab.lane_manager.has_changes:
                output_path = os.path.join(self.photo_tab.current_fileid.path, f"{self.photo_tab.current_fileid.fileid}_lane_fixes.csv")
                success = self.photo_tab.export_manager.export_lane_fixes(self.photo_tab.lane_manager.lane_fixes, output_path, include_file_id=False)
                if success:
                    logging.info(f"Auto-saved {len(self.photo_tab.lane_manager.lane_fixes)} modified lane fixes to {output_path}")
                    self.photo_tab.lane_manager.has_changes = False  # Reset after successful save
                else:
                    logging.error("Failed to auto-save modified lane fixes")

    def auto_save_all_data_on_close(self):
        """Auto-save all data when closing app"""
        try:
            # Check if we have FileID folders loaded
            if not self.fileid_manager.fileid_list:
                return

            # Save events for each FileID that has cached modifications
            for fileid_folder in self.fileid_manager.fileid_list:
                if fileid_folder.fileid in self.photo_tab.events_per_fileid:
                    events = self.photo_tab.events_per_fileid[fileid_folder.fileid]
                    try:
                        success = self.photo_tab.data_loader.save_events(events, fileid_folder)
                        if success:
                            logging.info(f"Auto-saved {len(events)} events for FileID {fileid_folder.fileid}")
                        else:
                            logging.error(f"Failed to auto-save events for FileID {fileid_folder.fileid}")
                    except Exception as e:
                        logging.error(f"Error saving events for {fileid_folder.fileid}: {str(e)}")

            # Save lane fixes for each FileID that has cached lane fixes
            for fileid_folder in self.fileid_manager.fileid_list:
                if fileid_folder.fileid in self.photo_tab.lane_fixes_per_fileid:
                    lane_fixes = self.photo_tab.lane_fixes_per_fileid[fileid_folder.fileid]
                    # Check if there are changes by comparing with loaded data
                    try:
                        from .models.lane_model import LaneManager
                        temp_manager = LaneManager()
                        temp_manager.set_fileid_folder(fileid_folder.path)
                        original_fixes = temp_manager.get_lane_fixes()
                        if len(lane_fixes) != len(original_fixes) or any(f1 != f2 for f1, f2 in zip(lane_fixes, original_fixes)):
                            output_path = os.path.join(fileid_folder.path, f"{fileid_folder.fileid}_lane_fixes.csv")
                            success = self.photo_tab.export_manager.export_lane_fixes(lane_fixes, output_path, include_file_id=False)
                            if success:
                                logging.info(f"Auto-saved {len(lane_fixes)} modified lane fixes for FileID {fileid_folder.fileid}")
                            else:
                                logging.error(f"Failed to auto-save lane fixes for FileID {fileid_folder.fileid}")
                    except Exception as e:
                        logging.error(f"Error checking/saving lane fixes for {fileid_folder.fileid}: {str(e)}")

            # Also merge and save all data to root folder
            self._merge_and_save_multi_fileid_data()

        except Exception as e:
            logging.error(f"Error during auto-save on close: {str(e)}")
            QMessageBox.warning(
                self, "Save Error",
                f"Failed to save data automatically: {str(e)}"
            )

    def _save_single_fileid_data(self):
        """Save data for single FileID folder"""
        if not hasattr(self.photo_tab, 'current_fileid') or not self.photo_tab.current_fileid:
            return

        # Save events if modified
        if self.photo_tab.events_modified:
            success = self.photo_tab.save_all_events_internal()
            if success:
                logging.info(f"Auto-saved {len(self.photo_tab.events)} modified events")
            else:
                logging.error("Failed to auto-save modified events")

        # Save lane fixes if modified
        if hasattr(self.photo_tab, 'lane_manager') and self.photo_tab.lane_manager.has_changes:
            output_path = os.path.join(self.photo_tab.current_fileid.path, f"{self.photo_tab.current_fileid.fileid}_lane_fixes.csv")
            success = self.photo_tab.export_manager.export_lane_fixes(self.photo_tab.lane_manager.lane_fixes, output_path, include_file_id=False)
            if success:
                logging.info(f"Auto-saved {len(self.photo_tab.lane_manager.lane_fixes)} modified lane fixes to {output_path}")
                self.photo_tab.lane_manager.has_changes = False  # Reset after successful save
            else:
                logging.error("Failed to auto-save modified lane fixes")

    def _merge_and_save_multi_fileid_data(self):
        """Merge data from all FileID folders and save to root folder"""
        if not self.fileid_manager.fileid_list:
            return

        root_folder = os.path.dirname(self.fileid_manager.fileid_list[0].path)

        # Check if any data has changes
        has_event_changes = False
        has_lane_changes = False

        for fileid_folder in self.fileid_manager.fileid_list:
            # Check events for this FileID
            if hasattr(self.photo_tab, 'current_fileid') and self.photo_tab.current_fileid == fileid_folder:
                if self.photo_tab.events_modified:
                    has_event_changes = True
            # Check lane fixes for this FileID
            try:
                from .models.lane_model import LaneManager
                temp_lane_manager = LaneManager()
                temp_lane_manager.set_fileid_folder(fileid_folder.path)
                if temp_lane_manager.has_changes:
                    has_lane_changes = True
            except:
                pass

        # Collect all data from FileID folders
        all_events = []
        all_lane_fixes = []

        for fileid_folder in self.fileid_manager.fileid_list:
            # Load events for this FileID
            fileid_events = self._load_events_for_fileid(fileid_folder)
            all_events.extend(fileid_events)

            # Load lane fixes for this FileID
            fileid_lane_fixes = self._load_lane_fixes_for_fileid(fileid_folder)
            all_lane_fixes.extend(fileid_lane_fixes)

        # Save merged events to root folder if there are any events
        all_events = []
        for fileid_folder in self.fileid_manager.fileid_list:
            fileid_events = self._load_events_for_fileid(fileid_folder)
            all_events.extend(fileid_events)

        if all_events:
            merged_driveevt_path = os.path.join(root_folder, "merged.driveevt")
            success = self._save_merged_events(all_events, merged_driveevt_path)
            if success:
                logging.info(f"Saved {len(all_events)} merged events to {merged_driveevt_path}")
            else:
                logging.error("Failed to save merged events")

        # Save merged lane fixes to root folder if there are any lane fixes
        if all_lane_fixes:
            merged_lane_path = os.path.join(root_folder, f"laneFixes-{datetime.now().strftime('%d-%m-%Y')}.csv")
            success = self._save_merged_lane_fixes(all_lane_fixes, merged_lane_path)
            if success:
                logging.info(f"Saved {len(all_lane_fixes)} merged lane fixes to {merged_lane_path}")
            else:
                logging.error("Failed to save merged lane fixes")

    def update_fileid_navigation(self):
        """Update FileID navigation buttons"""
        current = self.fileid_manager.get_current_fileid()
        if current:
            index = self.fileid_manager.fileid_list.index(current)
            total = len(self.fileid_manager.fileid_list)

            self.fileid_label.setText(f"FileID: {current.fileid} ({index + 1}/{total})")

            prev_enabled = index > 0
            next_enabled = index < total - 1

            self.photo_tab.prev_fileid_btn.setEnabled(prev_enabled)
            self.photo_tab.next_fileid_btn.setEnabled(next_enabled)

            # Update FileID combo box
            self.photo_tab.fileid_combo.blockSignals(True)
            self.photo_tab.fileid_combo.clear()
            for fileid_folder in self.fileid_manager.fileid_list:
                self.photo_tab.fileid_combo.addItem(fileid_folder.fileid)
            self.photo_tab.fileid_combo.setCurrentText(current.fileid)
            self.photo_tab.fileid_combo.blockSignals(False)

            logging.info(f"Navigation updated: index={index}, total={total}, prev_enabled={prev_enabled}, next_enabled={next_enabled}")
        else:
            logging.warning("No current FileID for navigation update")

    def set_theme(self, theme_name):
        """Switch application theme"""
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QPalette, QColor

        # Force Fusion style to prevent system theme override
        QApplication.setStyle("Fusion")

        # Load theme stylesheet
        theme_path = os.path.join(
            os.path.dirname(__file__), 'ui', 'styles', f'{theme_name}.qss'
        )

        try:
            with open(theme_path, 'r') as f:
                stylesheet = f.read()
            self.setStyleSheet(stylesheet)
            self.settings_manager.save_setting('theme', theme_name)

            # Set custom palette based on theme to ensure consistency
            palette = QPalette()
            if theme_name == 'dark':
                # Dark theme palette
                palette.setColor(QPalette.ColorRole.Window, QColor(45, 45, 45))
                palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
                palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
                palette.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 45, 45))
                palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
                palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
                palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
                palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
                palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
                palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
                palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
                palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
                palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
            else:
                # Light theme palette
                palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
                palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
                palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
                palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
                palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
                palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
                palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
                palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
                palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
                palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
                palette.setColor(QPalette.ColorRole.Link, QColor(0, 0, 255))
                palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 215))
                palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

            QApplication.setPalette(palette)

        except FileNotFoundError:
            print(f"Theme file not found: {theme_path}, using default theme")
            # Use default theme or no stylesheet
            self.setStyleSheet("")
            # Reset to default palette
            QApplication.setPalette(QApplication.style().standardPalette())

    def handle_memory_warning(self, usage_percent):
        """Handle memory warning from MemoryManager"""
        self.memory_label.setText(f"{usage_percent}%")

        if usage_percent > 90:
            self.photo_tab.clear_caches()
            QMessageBox.warning(
                self, "Memory Warning",
                f"High memory usage ({usage_percent}%). Cleared caches."
            )

    def handle_autosave(self, timestamp):
        """Handle autosave completion"""
        self.autosave_label.setText(timestamp.strftime("%H:%M:%S"))

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self, "About GeoEvent",
            "GeoEvent v2.0.0\n\n"
            "PyQt6-based road survey event coding application\n"
            "with GPS-synchronized timeline.\n\n"
            "© 2025 GeoEvent Team"
        )

    def closeEvent(self, event):
        """Handle application close"""
        # Show saving dialog
        save_dialog = QMessageBox(self)
        save_dialog.setWindowTitle("Saving Data")
        save_dialog.setText("Saving .driverevt and lane fix files...\nPlease wait.")
        save_dialog.setStandardButtons(QMessageBox.StandardButton.NoButton)  # No buttons, just informative
        save_dialog.setModal(True)
        save_dialog.show()

        # Force UI update to show the dialog
        QApplication.processEvents()

        try:
            # Auto-save all data before closing
            self.auto_save_all_data_on_close()
        finally:
            # Close the dialog after a short delay to show completion
            QTimer.singleShot(2000, save_dialog.close)  # 2 second delay

        # Save window state
        settings = self.settings_manager.load_settings()
        geometry = self.saveGeometry()
        settings['geometry'] = geometry.toBase64().data().decode('latin1')  # Convert QByteArray to base64 string
        self.settings_manager.save_settings(settings)

        # Accept the close event after dialog closes
        QTimer.singleShot(2000, lambda: event.accept())

        # Stop managers
        self.memory_manager.stop()
        self.autosave_manager.stop()

        event.accept()

    def _load_events_for_fileid(self, fileid_folder) -> List:
        """Load events for a specific FileID folder"""
        # First check if we have cached modified events
        if hasattr(self.photo_tab, 'events_per_fileid') and fileid_folder.fileid in self.photo_tab.events_per_fileid:
            return self.photo_tab.events_per_fileid[fileid_folder.fileid]
        
        # Otherwise load from file
        from .utils.data_loader import DataLoader
        try:
            data_loader = DataLoader()
            data = data_loader.load_fileid_data(fileid_folder)
            return data.get('events', [])
        except Exception as e:
            logging.error(f"Failed to load events for {fileid_folder.fileid}: {str(e)}")
            return []

    def _load_lane_fixes_for_fileid(self, fileid_folder) -> List:
        """Load lane fixes for a specific FileID folder"""
        # First check if we have cached lane fixes
        if hasattr(self.photo_tab, 'lane_fixes_per_fileid') and fileid_folder.fileid in self.photo_tab.lane_fixes_per_fileid:
            return self.photo_tab.lane_fixes_per_fileid[fileid_folder.fileid]
        
        # Otherwise load from file
        from .models.lane_model import LaneManager
        try:
            lane_manager = LaneManager()
            lane_manager.set_fileid_folder(fileid_folder.path)
            return lane_manager.get_lane_fixes()
        except Exception as e:
            logging.error(f"Failed to load lane fixes for {fileid_folder.fileid}: {str(e)}")
            return []

    def _save_merged_events(self, events: List, output_path: str) -> bool:
        """Save merged events to file"""
        from .utils.file_parser import save_driveevt
        import os

        try:
            # Sort events by timestamp
            sorted_events = sorted(events, key=lambda e: e.timestamp_utc if hasattr(e, 'timestamp_utc') else datetime.min)

            # Extract fileid from output_path (filename without extension)
            fileid = os.path.splitext(os.path.basename(output_path))[0]

            # Save all events - each will use its own file_id for session token, fallback to fileid from path
            success = save_driveevt(sorted_events, output_path, fileid)
            return success
        except Exception as e:
            logging.error(f"Failed to save merged events: {str(e)}")
            return False

    def _save_merged_lane_fixes(self, lane_fixes: List, output_path: str) -> bool:
        """Save merged lane fixes to file"""
        try:
            # Sort lane fixes by timestamp
            sorted_fixes = sorted(lane_fixes, key=lambda f: f.from_time)

            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow(['Plate', 'From', 'To', 'Lane', 'Ignore', 'RegionID', 'RoadID', 'Travel'])

                # Write data - format times as DD/MM/YY HH:MM:SS.mmm (same as individual files)
                for fix in sorted_fixes:
                    # Convert times to DD/MM/YY HH:MM:SS.mmm format (day/month/year hour:minute:second.millisecond)
                    from_milliseconds = fix.from_time.microsecond // 1000
                    from_time_str = fix.from_time.strftime('%d/%m/%y %H:%M:%S') + f'.{from_milliseconds:03d}'
                    
                    to_milliseconds = fix.to_time.microsecond // 1000
                    to_time_str = fix.to_time.strftime('%d/%m/%y %H:%M:%S') + f'.{to_milliseconds:03d}'
                    
                    writer.writerow([
                        fix.plate,
                        from_time_str,
                        to_time_str,
                        fix.lane,
                        '1' if fix.ignore else '',  # Ignore
                        '',  # RegionID
                        '',  # RoadID
                        'N'  # Travel direction
                    ])

            logging.info(f"Saved {len(sorted_fixes)} merged lane fixes to {output_path}")
            return True

        except Exception as e:
            logging.error(f"Failed to save merged lane fixes: {str(e)}")
            return False

    def show_user_guide(self):
        """Show user guide dialog"""
        show_user_guide(self)

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self, "About GeoEvent",
            "GeoEvent v2.0.0\n\n"
            "Road Survey Event Coding Application\n\n"
            "Built with PyQt6 and Python"
        )