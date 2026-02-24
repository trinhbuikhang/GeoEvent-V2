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
    QFileDialog, QMessageBox, QLabel, QApplication
)
from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer, QMutexLocker
from .ui.photo_preview_tab import PhotoPreviewTab
from .utils.settings_manager import SettingsManager
from .utils.fileid_manager import FileIDManager
from .utils.user_guide import show_user_guide
from .core.memory_manager import MemoryManager
from .core.autosave_manager import AutoSaveManager
from .ui.settings_dialog import SettingsDialog
from .ui.shortcuts_dialog import ShortcutsDialog
from .utils.metrics_tracker import MetricsTracker
from .utils.resource_path import get_resource_path

class BackgroundSaveWorker(QThread):
    """
    Worker thread for background save operations
    """
    save_completed = pyqtSignal(str, bool)  # (operation_name, success)

    def __init__(self, save_func, *args, **kwargs):
        super().__init__()
        self.save_func = save_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        """Execute save operation in background thread"""
        try:
            result = self.save_func(*self.args, **self.kwargs)
            self.save_completed.emit("save_operation", result)
        except Exception as e:
            logging.error(f"Background save failed: {e}")
            self.save_completed.emit("save_operation", False)


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
        self.metrics_tracker = MetricsTracker()
        self.root_folder_path = None  # Parent folder containing FileID folders
        self._merge_after_save_pending = False

        # Ensure settings file is initialized without clearing user preferences
        self._ensure_settings_migration()

        self.photo_tab = None
        
        # Start metrics session
        self.metrics_tracker.start_session()

        self.setup_ui()
        self.load_settings()
        self.connect_signals()

    def setup_ui(self):
        """Create menu, toolbar, status bar"""
        self._update_window_title()
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

    def _get_root_folder_name(self):
        """Return the active root folder name (parent of FileID folders)"""
        if self.root_folder_path:
            return os.path.basename(os.path.normpath(self.root_folder_path))

        current = self.fileid_manager.get_current_fileid()
        if current:
            return os.path.basename(os.path.dirname(current.path))

        if self.fileid_manager.fileid_list:
            return os.path.basename(os.path.dirname(self.fileid_manager.fileid_list[0].path))

        return None

    def _update_window_title(self):
        """Update window title with app name, version, and root folder"""
        app_instance = QApplication.instance()
        version = app_instance.applicationVersion() if app_instance else ""
        if version and not version.lower().startswith("v"):
            version_text = f"v{version}"
        else:
            version_text = version or None

        root_name = self._get_root_folder_name()

        parts = ["GeoEvent"]
        if version_text:
            parts.append(version_text)
        if root_name:
            parts.append(root_name)

        self.setWindowTitle(" - ".join(parts))

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
        
        # Merge data action
        merge_action = QAction("Merge All Data", self)
        merge_action.triggered.connect(self._handle_manual_merge)
        merge_action.setStatusTip("Merge data from all FileID folders into root folder files (auto-saves current data first)")
        file_menu.addAction(merge_action)
        
        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu

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
        settings_action = QAction("Settings...", self)
        settings_action.triggered.connect(self.show_settings_dialog)
        tools_menu.addAction(settings_action)

        reset_settings_action = QAction("Reset Settings to Defaults", self)
        reset_settings_action.triggered.connect(self._confirm_reset_settings)
        tools_menu.addAction(reset_settings_action)

        # Help menu
        help_menu = menubar.addMenu("Help")
        
        shortcuts_action = QAction("Keyboard Shortcuts...", self)
        shortcuts_action.setShortcut("F1")
        shortcuts_action.triggered.connect(self.show_shortcuts_dialog)
        help_menu.addAction(shortcuts_action)
        
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
        last_folder = self.settings_manager.get_setting('last_folder')
        start_dir = last_folder if last_folder and os.path.isdir(last_folder) else None
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Survey Data Folder", directory=start_dir or ""
        )

        if folder_path:
            self.root_folder_path = os.path.normpath(folder_path)
            try:
                # Auto-save current data before switching folders (silent save)
                self.auto_save_current_data_silent()

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

                # Remember folder for next time
                self.settings_manager.save_setting('last_folder', self.root_folder_path)

                # Update navigation
                self.update_fileid_navigation()
                self._update_window_title()

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
            self._update_window_title()
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Failed to load FileID {fileid_folder.fileid}: {str(e)}"
            )

    def prev_fileid(self):
        """Navigate to previous FileID"""
        # Auto-save current data before switching (silent save)
        self.auto_save_current_data_silent()

        prev_fileid = self.fileid_manager.prev_fileid()
        if prev_fileid:
            self.load_fileid(prev_fileid)
            self.update_fileid_navigation()

    def next_fileid(self):
        """Navigate to next FileID"""
        # Auto-save current data before switching (silent save)
        self.auto_save_current_data_silent()

        next_fileid = self.fileid_manager.next_fileid()
        if next_fileid:
            self.load_fileid(next_fileid)
            self.update_fileid_navigation()

    def auto_save_current_data_silent(self):
        """Auto-save current data silently in background thread"""
        if hasattr(self.photo_tab, 'current_fileid') and self.photo_tab.current_fileid:
            # Start background save operations
            self._start_background_save()

    def _start_background_save(self):
        """Start background save operations for current FileID"""
        def save_operations():
            """Perform all save operations and return overall success"""
            overall_success = True

            # Thread-safe access to shared data
            with QMutexLocker(self.photo_tab._data_mutex):
                # Save events if modified
                if self.photo_tab.events_modified:
                    # Backup existing .driveevt file before overwriting
                    driveevt_path = os.path.join(self.photo_tab.current_fileid.path, f"{self.photo_tab.current_fileid.fileid}.driveevt")
                    if os.path.exists(driveevt_path):
                        import datetime
                        backup_path = os.path.join(self.photo_tab.current_fileid.path, f"{self.photo_tab.current_fileid.fileid}_driveevt_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.driveevt")
                        try:
                            import shutil
                            shutil.copy2(driveevt_path, backup_path)
                            # logging.info(f"Backed up existing .driveevt file to {backup_path}")
                        except Exception as e:
                            logging.error(f"Failed to backup .driveevt file: {str(e)}")
                    success = self.photo_tab.save_all_events_internal()
                    if success:
                        # logging.info(f"Auto-saved {len(self.photo_tab.events)} modified events for {self.photo_tab.current_fileid.fileid}")
                        pass
                    else:
                        logging.error("Failed to auto-save modified events")
                        overall_success = False

                # Save lane fixes (always save when switching FileID to ensure data integrity)
                if hasattr(self.photo_tab, 'lane_manager') and self.photo_tab.lane_manager:
                    output_path = os.path.join(self.photo_tab.current_fileid.path, f"{self.photo_tab.current_fileid.fileid}_lane_fixes.csv")
                    # Backup existing file before overwriting
                    if os.path.exists(output_path):
                        import datetime
                        backup_path = os.path.join(self.photo_tab.current_fileid.path, f"{self.photo_tab.current_fileid.fileid}_lane_fixes_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
                        try:
                            import shutil
                            shutil.copy2(output_path, backup_path)
                            # logging.info(f"Backed up existing lane fixes file to {backup_path}")
                        except Exception as e:
                            logging.error(f"Failed to backup lane fixes file: {str(e)}")
                    success = self.photo_tab.export_manager.export_lane_fixes(self.photo_tab.lane_manager.lane_fixes, output_path, include_file_id=False)
                    if success:
                        # logging.info(f"Auto-saved {len(self.photo_tab.lane_manager.lane_fixes)} lane fixes to {output_path}")
                        self.photo_tab.lane_manager.has_changes = False  # Reset after successful save
                    else:
                        logging.error("Failed to auto-save lane fixes")
                        overall_success = False
                #     self._merge_and_save_multi_fileid_data()
                #     # logging.info("Updated merged files after auto-save")
                # except Exception as e:
                #     logging.error(f"Failed to update merged files: {e}")
                #     overall_success = False

            return overall_success

        # Create and start background worker
        self.save_worker = BackgroundSaveWorker(save_operations)
        self.save_worker.save_completed.connect(self._on_save_completed)
        self.save_worker.start()

    def _on_save_completed(self, operation_name, success):
        """Handle save completion signal"""
        if operation_name == "save_operation":
            if success:
                logging.debug("Background save completed successfully")
            else:
                logging.warning("Background save completed with errors")

        # Clean up worker
        if hasattr(self, 'save_worker') and self.save_worker is not None:
            self.save_worker.quit()
            self.save_worker.wait()
            self.save_worker = None

        # Deferred merge after save (avoids main-thread sleep)
        if getattr(self, '_merge_after_save_pending', False):
            self._merge_after_save_pending = False
            QTimer.singleShot(0, self._do_merge_and_show_message)

    def _ensure_settings_migration(self):
        """Mark settings migration once without deleting user preferences"""
        migration_flag = "settings_migrated_v2"
        if not self.settings_manager.get_setting(migration_flag, False):
            self.settings_manager.save_setting(migration_flag, True)

    def _confirm_reset_settings(self):
        """Prompt user before resetting settings to defaults"""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Reset all GeoEvent settings to defaults? This will clear saved preferences like theme and last folder.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.settings_manager.reset_to_defaults()
            self.load_settings()
            QMessageBox.information(
                self,
                "Settings Reset",
                "Settings were reset to defaults."
            )

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
                            # Backup existing file before overwriting
                            if os.path.exists(output_path):
                                import datetime
                                backup_path = os.path.join(fileid_folder.path, f"{fileid_folder.fileid}_lane_fixes_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
                                try:
                                    import shutil
                                    shutil.copy2(output_path, backup_path)
                                    logging.info(f"Backed up existing lane fixes file to {backup_path}")
                                except Exception as e:
                                    logging.error(f"Failed to backup lane fixes file: {str(e)}")
                            success = self.photo_tab.export_manager.export_lane_fixes(lane_fixes, output_path, include_file_id=False)
                            if success:
                                logging.info(f"Auto-saved {len(lane_fixes)} modified lane fixes for FileID {fileid_folder.fileid}")
                            else:
                                logging.error(f"Failed to auto-save lane fixes for FileID {fileid_folder.fileid}")
                    except Exception as e:
                        logging.error(f"Error checking/saving lane fixes for {fileid_folder.fileid}: {str(e)}")

            # Also save current FileID data if not already saved via cache
            if self.photo_tab.current_fileid and self.photo_tab.current_fileid not in [f.fileid for f in self.fileid_manager.fileid_list if f.fileid in self.photo_tab.events_per_fileid]:
                # Current FileID data not in cache, save it directly
                try:
                    # Save events
                    if self.photo_tab.events:
                        success = self.photo_tab.data_loader.save_events(self.photo_tab.events, self.photo_tab.current_fileid)
                        if success:
                            logging.info(f"Auto-saved {len(self.photo_tab.events)} current events for FileID {self.photo_tab.current_fileid.fileid}")
                        else:
                            logging.error(f"Failed to auto-save current events for FileID {self.photo_tab.current_fileid.fileid}")
                    
                    # Save lane fixes if modified
                    if self.photo_tab.lane_manager and self.photo_tab.lane_manager.has_changes:
                        lane_fixes = self.photo_tab.lane_manager.get_lane_fixes()
                        output_path = os.path.join(self.photo_tab.current_fileid.path, f"{self.photo_tab.current_fileid.fileid}_lane_fixes.csv")
                        success = self.photo_tab.export_manager.export_lane_fixes(lane_fixes, output_path, include_file_id=False)
                        if success:
                            logging.info(f"Auto-saved {len(lane_fixes)} current lane fixes for FileID {self.photo_tab.current_fileid.fileid}")
                        else:
                            logging.error(f"Failed to auto-save current lane fixes for FileID {self.photo_tab.current_fileid.fileid}")
                except Exception as e:
                    logging.error(f"Error saving current FileID data: {str(e)}")

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

        # Always save events to ensure .driverevt files are up-to-date
        success = self.photo_tab.save_all_events_internal()
        if success:
            logging.info(f"Auto-saved {len(self.photo_tab.events)} events")
        else:
            logging.error("Failed to auto-save events")

        # Save lane fixes if modified
        if hasattr(self.photo_tab, 'lane_manager') and self.photo_tab.lane_manager.has_changes:
            output_path = os.path.join(self.photo_tab.current_fileid.path, f"{self.photo_tab.current_fileid.fileid}_lane_fixes.csv")
            success = self.photo_tab.export_manager.export_lane_fixes(self.photo_tab.lane_manager.lane_fixes, output_path, include_file_id=False)
            if success:
                logging.info(f"Auto-saved {len(self.photo_tab.lane_manager.lane_fixes)} modified lane fixes to {output_path}")
                self.photo_tab.lane_manager.has_changes = False  # Reset after successful save
            else:
                logging.error("Failed to auto-save modified lane fixes")

    def _handle_manual_merge(self):
        """Handle manual merge request - auto-save current data first, then merge (no main-thread sleep)."""
        try:
            if hasattr(self.photo_tab, 'current_fileid') and self.photo_tab.current_fileid:
                self._merge_after_save_pending = True
                self._start_background_save()
            else:
                self._do_merge_and_show_message()
        except Exception as e:
            QMessageBox.warning(self, "Merge Error", f"Failed to merge data: {str(e)}")

    def _do_merge_and_show_message(self):
        """Run merge and show completion message (called after save or when no save needed)."""
        try:
            self._merge_and_save_multi_fileid_data()
            QMessageBox.information(
                self, "Merge Complete",
                "All FileID data has been merged into root folder files."
            )
        except Exception as e:
            QMessageBox.warning(self, "Merge Error", f"Failed to merge data: {str(e)}")

    def _merge_and_save_multi_fileid_data(self):
        """Merge data from all FileID folders and save to root folder"""
        if not self.fileid_manager.fileid_list:
            return

        root_folder = os.path.dirname(self.fileid_manager.fileid_list[0].path)

        # Always collect all data from cache and merge - don't check for changes
        # since we want to ensure merged files are always up-to-date
        all_events = []
        all_lane_fixes = []

        for fileid_folder in self.fileid_manager.fileid_list:
            # Load events from cache if available, otherwise from file
            if fileid_folder.fileid in self.photo_tab.events_per_fileid:
                fileid_events = self.photo_tab.events_per_fileid[fileid_folder.fileid]
                logging.info(f"Using cached events for {fileid_folder.fileid}: {len(fileid_events)} events")
            else:
                fileid_events = self._load_events_for_fileid(fileid_folder)
                logging.info(f"Loaded events from file for {fileid_folder.fileid}: {len(fileid_events)} events")
            all_events.extend(fileid_events)

            # Load lane fixes from cache if available, otherwise from file
            if fileid_folder.fileid in self.photo_tab.lane_fixes_per_fileid:
                fileid_lane_fixes = self.photo_tab.lane_fixes_per_fileid[fileid_folder.fileid]
                logging.info(f"Using cached lane fixes for {fileid_folder.fileid}: {len(fileid_lane_fixes)} fixes")
            else:
                fileid_lane_fixes = self._load_lane_fixes_for_fileid(fileid_folder)
                logging.info(f"Loaded lane fixes from file for {fileid_folder.fileid}: {len(fileid_lane_fixes)} fixes")
            all_lane_fixes.extend(fileid_lane_fixes)

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
                display_text = f"▶ {fileid_folder.fileid}" if fileid_folder.fileid == current.fileid else fileid_folder.fileid
                self.photo_tab.fileid_combo.addItem(display_text, fileid_folder.fileid)
            # Set current item by data, not display text
            for i in range(self.photo_tab.fileid_combo.count()):
                if self.photo_tab.fileid_combo.itemData(i) == current.fileid:
                    self.photo_tab.fileid_combo.setCurrentIndex(i)
                    break
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

        # Load theme stylesheet (frozen-EXE safe via get_resource_path)
        theme_path = get_resource_path(os.path.join('app', 'ui', 'styles', f'{theme_name}.qss'))

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
            logging.warning(f"Theme file not found: {theme_path}, using default theme")
            # Use default theme or no stylesheet
            self.setStyleSheet("")
            # Reset to default palette
            QApplication.setPalette(QApplication.style().standardPalette())

        # Propagate theme to child tabs/widgets that support it
        if hasattr(self, "photo_tab") and self.photo_tab:
            apply_theme = getattr(self.photo_tab, "apply_theme", None)
            if callable(apply_theme):
                apply_theme(theme_name)

    def handle_memory_warning(self, usage_percent):
        """Handle memory warning from MemoryManager"""
        self.memory_label.setText(f"{usage_percent}%")

        if usage_percent > 90:
            self.photo_tab.clear_caches()
            # QMessageBox.warning(
            #     self, "Memory Warning",
            #     f"High memory usage ({usage_percent}%). Cleared caches."
            # )

    def handle_autosave(self, timestamp):
        """Handle autosave completion"""
        self.autosave_label.setText(timestamp.strftime("%H:%M:%S"))

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self, "About GeoEvent",
            "GeoEvent v2.0.20\n\n"
            "PyQt6-based road survey event coding application\n"
            "with GPS-synchronized timeline.\n\n"
            "© 2025 Pavement Team"
        )

    def closeEvent(self, event):
        """Handle application close"""
        # End metrics session
        self.metrics_tracker.end_session()
        
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
            # Backup existing file before overwriting
            if os.path.exists(output_path):
                import datetime
                backup_path = output_path + f".backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                try:
                    import shutil
                    shutil.copy2(output_path, backup_path)
                    logging.info(f"Backed up existing merged lane fixes file to {backup_path}")
                except Exception as e:
                    logging.error(f"Failed to backup merged lane fixes file: {str(e)}")

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
    
    def show_shortcuts_dialog(self):
        """Show keyboard shortcuts dialog"""
        dialog = ShortcutsDialog(self)
        dialog.exec()

    def show_settings_dialog(self):
        """Show settings dialog"""
        # Store old cache size
        old_cache_size = self.settings_manager.get_setting('image_cache_size', 500)

        dialog = SettingsDialog(self, self.settings_manager)
        result = dialog.exec()

        if result:  # Dialog was accepted
            new_cache_size = self.settings_manager.get_setting('image_cache_size', 500)
            if new_cache_size != old_cache_size:
                # Update cache size in photo tab
                self.photo_tab.update_cache_settings(new_cache_size)

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self, "About GeoEvent",
            "GeoEvent v2.0.20\n\n"
            "Road Survey Event Coding Application\n\n"
            "Built with PyQt6 and Python\n\n"
            "© 2025 Pavement Team"
        )
