"""
Main Window for GeoEvent Application
"""

from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QHBoxLayout,
    QSplitter, QStatusBar, QMenuBar, QToolBar,
    QFileDialog, QMessageBox, QLabel
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QActionGroup

from .ui.photo_preview_tab import PhotoPreviewTab
from .utils.settings_manager import SettingsManager
from .utils.fileid_manager import FileIDManager
from .core.memory_manager import MemoryManager
from .core.autosave_manager import AutoSaveManager

import os

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
            self.update_fileid_navigation()
            self.status_label.setText("Ready")
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Failed to load FileID {fileid_folder.fileid}: {str(e)}"
            )

    def prev_fileid(self):
        """Navigate to previous FileID"""
        prev_fileid = self.fileid_manager.prev_fileid()
        if prev_fileid:
            self.load_fileid(prev_fileid)
            self.update_fileid_navigation()

    def next_fileid(self):
        """Navigate to next FileID"""
        next_fileid = self.fileid_manager.next_fileid()
        if next_fileid:
            self.load_fileid(next_fileid)
            self.update_fileid_navigation()

    def update_fileid_navigation(self):
        """Update FileID navigation buttons"""
        current = self.fileid_manager.get_current_fileid()
        if current:
            index = self.fileid_manager.fileid_list.index(current)
            total = len(self.fileid_manager.fileid_list)

            self.fileid_label.setText(f"FileID: {current.fileid} ({index + 1}/{total})")

            self.photo_tab.prev_fileid_btn.setEnabled(index > 0)
            self.photo_tab.next_fileid_btn.setEnabled(index < total - 1)

    def set_theme(self, theme_name):
        """Switch application theme"""
        # Load theme stylesheet
        theme_path = os.path.join(
            os.path.dirname(__file__), 'ui', 'styles', f'{theme_name}.qss'
        )

        try:
            with open(theme_path, 'r') as f:
                stylesheet = f.read()
            self.setStyleSheet(stylesheet)
            self.settings_manager.save_setting('theme', theme_name)
        except FileNotFoundError:
            print(f"Theme file not found: {theme_path}, using default theme")
            # Use default theme or no stylesheet
            self.setStyleSheet("")

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

    def prev_fileid(self):
        """Navigate to previous FileID"""
        if self.photo_tab and hasattr(self.photo_tab, 'current_fileid'):
            prev_fileid = self.fileid_manager.prev_fileid()
            if prev_fileid:
                self.photo_tab.load_fileid(prev_fileid)
                self.update_fileid_label()

    def next_fileid(self):
        """Navigate to next FileID"""
        if self.photo_tab and hasattr(self.photo_tab, 'current_fileid'):
            next_fileid = self.fileid_manager.next_fileid()
            if next_fileid:
                self.photo_tab.load_fileid(next_fileid)
                self.update_fileid_label()

    def update_fileid_label(self):
        """Update FileID label in status bar"""
        current = self.fileid_manager.get_current_fileid()
        if current and hasattr(self, 'fileid_label'):
            self.fileid_label.setText(f"FileID: {current.fileid}")
        elif hasattr(self, 'fileid_label'):
            self.fileid_label.setText("No FileID loaded")

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
        # Save window state
        settings = self.settings_manager.load_settings()
        geometry = self.saveGeometry()
        settings['geometry'] = geometry.toBase64().data().decode('latin1')  # Convert QByteArray to base64 string
        self.settings_manager.save_settings(settings)

        # Stop managers
        self.memory_manager.stop()
        self.autosave_manager.stop()

        event.accept()