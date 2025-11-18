"""
Photo Preview Tab - Main UI component for GeoEvent application
"""

import os
import logging
from datetime import datetime
from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QFrame, QScrollArea, QGroupBox, QButtonGroup, QSplitter, QSizePolicy, QMessageBox, QComboBox, QDialog, QRadioButton, QDialogButtonBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QBrush
from PyQt6.QtCore import QPointF
from PyQt6.QtWebEngineWidgets import QWebEngineView

from ..models.event_model import Event
from ..models.gps_model import GPSData
from ..models.lane_model import LaneManager
from ..utils.data_loader import DataLoader
from ..utils.image_utils import extract_image_metadata
from ..utils.export_manager import ExportManager
from .timeline_widget import TimelineWidget

class LaneChangeDialog(QDialog):
    """Dialog for choosing lane change scope"""
    
    def __init__(self, current_lane, new_lane, timestamp, period_start, period_end, parent=None):
        super().__init__(parent)
        self.current_lane = current_lane
        self.new_lane = new_lane
        self.timestamp = timestamp
        self.period_start = period_start
        self.period_end = period_end
        self.selected_scope = None
        
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Lane Change Mode")
        self.setModal(True)
        self.resize(500, 200)
        
        layout = QVBoxLayout(self)
        
        # Description
        desc_label = QLabel(
            f"Change from Lane {self.current_lane} to Lane {self.new_lane} at {self.timestamp.strftime('%H:%M:%S')}\n\n"
            f"• Drag the yellow marker on the timeline to select the end time\n"
            f"• The change will apply from {self.timestamp.strftime('%H:%M:%S')} to the marker position\n"
            f"• Release the marker to confirm the change\n"
            f"• Click 'Cancel' to exit lane change mode"
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-size: 11px; line-height: 1.4;")
        layout.addWidget(desc_label)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_selected_scope(self):
        """Return the selected scope: always 'marker'"""
        return 'marker'

class PhotoPreviewTab(QWidget):
    """
    Main tab widget for photo preview and navigation
    RESPONSIBILITIES:
    - Display current survey image
    - Navigate images (prev/next, slider)
    - Show image metadata (timestamp, GPS, plate)
    - Sync with timeline position
    - Manage lane assignment buttons
    """

    # Signals
    image_changed = pyqtSignal(int, dict)  # index, metadata
    position_changed = pyqtSignal(datetime, tuple)  # timestamp, (lat, lon)

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.image_paths: List[str] = []
        self.current_index = -1
        self.events: List[Event] = []
        self.gps_data: Optional[GPSData] = None
        self.lane_manager = None  # Will be set from data loader

        self.image_cache = {}  # Simple cache for loaded images
        self.events_modified = False  # Track if events have been modified
        self.marker_mode_active = False
        self.marker_new_lane = None
        self.marker_timestamp = None
        self.marker_period_start = None
        self.marker_period_end = None

        # Lane change mode using current position marker
        self.lane_change_mode_active = False
        self.lane_change_new_lane = None
        self.lane_change_start_timestamp = None

        # Global lane button group (exclusive)
        self.lane_buttons = QButtonGroup(self)
        self.lane_buttons.setExclusive(True)  # Only one lane button can be checked at a time

        self.data_loader = DataLoader()  # Data loading manager
        self.export_manager = ExportManager()  # Export manager

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """Create the UI components"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Top section: Photo display (left) + Controls (right)
        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: Photo display canvas
        photo_widget = QWidget()
        photo_layout = QVBoxLayout(photo_widget)
        photo_layout.setContentsMargins(0, 0, 0, 0)
        self.setup_image_display(photo_layout)
        top_splitter.addWidget(photo_widget)

        # Right: Control panels
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)

        # Top row: Minimap and Folder info side by side (HORIZONTAL)
        top_row_layout = QHBoxLayout()
        top_row_layout.setSpacing(5)
        
        # Minimap (left side of top row)
        self.minimap_view = QWebEngineView()
        self.minimap_view.setMinimumSize(150, 200)
        top_row_layout.addWidget(self.minimap_view, stretch=1)

        # Folder information (right side of top row)
        self.folder_info_label = QLabel("Folder")
        self.folder_info_label.setStyleSheet("border: 2px solid black; background-color: black; color: white; padding: 10px;")
        self.folder_info_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.folder_info_label.setWordWrap(True)
        self.folder_info_label.setMinimumSize(150, 200)
        top_row_layout.addWidget(self.folder_info_label, stretch=1)
        
        right_layout.addLayout(top_row_layout)

        # Lanecode button control
        lanecode_group = QGroupBox("LaneCode")
        lanecode_group.setStyleSheet("QGroupBox { border: 2px solid black; padding: 10px; }")
        lanecode_layout = QVBoxLayout()
        self.setup_lane_controls(lanecode_layout)
        lanecode_group.setLayout(lanecode_layout)
        lanecode_group.setMinimumHeight(180)
        lanecode_group.setMaximumHeight(220)
        right_layout.addWidget(lanecode_group, stretch=1)

        # FileID button control
        fileid_group = QGroupBox("FileID")
        fileid_group.setStyleSheet("QGroupBox { border: 2px solid black; padding: 10px; }")
        fileid_layout = QHBoxLayout()
        self.setup_fileid_controls(fileid_layout)
        fileid_group.setLayout(fileid_layout)
        fileid_group.setMinimumHeight(60)
        fileid_group.setMaximumHeight(80)
        right_layout.addWidget(fileid_group)

        top_splitter.addWidget(right_widget)

        # Set splitter proportions (60% photo, 40% controls)
        top_splitter.setSizes([600, 400])
        main_layout.addWidget(top_splitter, stretch=7)

        # Timeline and event marker display
        timeline_frame = QFrame()
        timeline_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        timeline_frame.setLineWidth(2)
        timeline_layout = QVBoxLayout(timeline_frame)
        timeline_layout.setContentsMargins(5, 5, 5, 5)
        
        self.timeline = TimelineWidget(photo_tab=self)
        timeline_layout.addWidget(self.timeline)
        
        main_layout.addWidget(timeline_frame, stretch=3)

        # Bottom section: Navigation and buttons in one row
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        # Photo navigation buttons
        nav_group = QGroupBox("Photo Navigation")
        nav_group.setStyleSheet("QGroupBox { border: 2px solid black; padding: 5px; }")
        nav_layout = QHBoxLayout()
        self.setup_navigation_buttons(nav_layout)
        nav_group.setLayout(nav_layout)
        bottom_layout.addWidget(nav_group)

        # Marker control buttons (hidden by default)
        self.marker_group = QGroupBox("Lane Change Marker")
        self.marker_group.setStyleSheet("QGroupBox { border: 2px solid black; padding: 5px; }")
        marker_layout = QHBoxLayout()
        self.setup_marker_buttons(marker_layout)
        self.marker_group.setLayout(marker_layout)
        self.marker_group.setVisible(False)  # Hidden by default
        bottom_layout.addWidget(self.marker_group)

        main_layout.addLayout(bottom_layout)

        # Photo slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)
        self.slider.valueChanged.connect(self.slider_changed)
        self.slider.setMinimumHeight(30)
        main_layout.addWidget(self.slider)

    def setup_image_display(self, parent_layout):
        """Setup image display area"""
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: 2px solid black;")
        self.scroll_area.setMinimumHeight(400)

        self.image_label = QLabel("Photo display canvas")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: #f0f0f0; font-size: 18px; font-weight: bold;")
        self.scroll_area.setWidget(self.image_label)

        parent_layout.addWidget(self.scroll_area)

    def setup_navigation_buttons(self, parent_layout):
        """Setup navigation buttons"""
        self.prev_btn = QPushButton("◀ Previous")
        self.prev_btn.clicked.connect(self.prev_image)
        self.prev_btn.setMinimumHeight(40)
        parent_layout.addWidget(self.prev_btn)

        self.play_btn = QPushButton("▶ Play")
        self.play_btn.clicked.connect(self.toggle_playback)
        self.play_btn.setMinimumHeight(40)
        parent_layout.addWidget(self.play_btn)

        self.next_btn = QPushButton("Next ▶")
        self.next_btn.clicked.connect(self.next_image)
        self.next_btn.setMinimumHeight(40)
        parent_layout.addWidget(self.next_btn)

        self.position_label = QLabel("0 / 0")
        self.position_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.position_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        parent_layout.addWidget(self.position_label)

        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.next_image)
        self.is_playing = False

    def setup_marker_buttons(self, parent_layout):
        """Setup marker control buttons"""
        self.apply_marker_btn = QPushButton("Apply Change")
        self.apply_marker_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: 1px solid #388E3C;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.apply_marker_btn.clicked.connect(self._apply_marker_change_from_button)
        self.apply_marker_btn.setMinimumHeight(40)
        parent_layout.addWidget(self.apply_marker_btn)

        self.cancel_marker_btn = QPushButton("Cancel")
        self.cancel_marker_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border: 1px solid #B71C1C;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E53935;
            }
        """)
        self.cancel_marker_btn.clicked.connect(self._exit_marker_mode)
        self.cancel_marker_btn.setMinimumHeight(40)
        parent_layout.addWidget(self.cancel_marker_btn)

    def setup_lane_controls(self, parent_layout):
        """Setup lane controls with improved layout"""
        # Row 1: Lane 1-4 buttons
        lane_row = QHBoxLayout()
        lane_row.setSpacing(5)
        lane_codes = ['1', '2', '3', '4']
        lane_names = ['Lane 1', 'Lane 2', 'Lane 3', 'Lane 4']

        for code, name in zip(lane_codes, lane_names):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1976D2;
                    color: white;
                    border: 1px solid #0D47A1;
                    padding: 8px;
                    font-weight: bold;
                }
                QPushButton:checked {
                    background-color: #4CAF50;
                    color: white;
                    border: 2px solid #388E3C;
                }
                QPushButton:hover {
                    background-color: #1565C0;
                }
                QPushButton:checked:hover {
                    background-color: #45a049;
                }
            """)
            btn.clicked.connect(lambda checked, c=code: self.assign_lane(c))
            btn.setMinimumHeight(35)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.lane_buttons.addButton(btn)
            lane_row.addWidget(btn)

        parent_layout.addLayout(lane_row)

        # Row 2: TK, TM, SK, Ignore buttons
        control_row = QHBoxLayout()
        control_row.setSpacing(5)
        
        # Turn Left button (TK)
        self.turn_left_btn = QPushButton("TK\n↰")
        self.turn_left_btn.setCheckable(True)
        self.turn_left_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                border: 1px solid #0D47A1;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #FFF9C4;
                color: black;
                border: 2px solid #FBC02D;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:checked:hover {
                background-color: #FFF59D;
            }
        """)
        self.turn_left_btn.clicked.connect(lambda: self.start_turn('TK'))
        self.turn_left_btn.setMinimumHeight(35)
        self.turn_left_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        control_row.addWidget(self.turn_left_btn)

        # Turn Right button (TM)
        self.turn_right_btn = QPushButton("TM\n↱")
        self.turn_right_btn.setCheckable(True)
        self.turn_right_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                border: 1px solid #0D47A1;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #FFF9C4;
                color: black;
                border: 2px solid #FBC02D;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:checked:hover {
                background-color: #FFF59D;
            }
        """)
        self.turn_right_btn.clicked.connect(lambda: self.start_turn('TM'))
        self.turn_right_btn.setMinimumHeight(35)
        self.turn_right_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        control_row.addWidget(self.turn_right_btn)

        # SK button (Shoulder)
        self.sk_btn = QPushButton("SK")
        self.sk_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: 1px solid #E65100;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FB8C00;
            }
            QPushButton:pressed {
                background-color: #E65100;
            }
        """)
        self.sk_btn.clicked.connect(self.assign_sk)
        self.sk_btn.setMinimumHeight(35)
        self.sk_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        control_row.addWidget(self.sk_btn)

        # Ignore button
        self.ignore_btn = QPushButton("Ignore")
        self.ignore_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border: 1px solid #B71C1C;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E53935;
            }
            QPushButton:pressed {
                background-color: #B71C1C;
            }
        """)
        self.ignore_btn.clicked.connect(self.assign_ignore)
        self.ignore_btn.setMinimumHeight(35)
        self.ignore_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        control_row.addWidget(self.ignore_btn)

        parent_layout.addLayout(control_row)

        # Row 3: Current lane label
        self.current_lane_label = QLabel("Current: None")
        self.current_lane_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 12px;
                padding: 4px;
                background-color: #34495E;
                color: white;
                border: 1px solid #2C3E50;
                border-radius: 3px;
            }
        """)
        self.current_lane_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_lane_label.setMaximumHeight(50)
        parent_layout.addWidget(self.current_lane_label)

    def setup_fileid_controls(self, parent_layout):
        """Setup FileID navigation controls"""
        self.prev_fileid_btn = QPushButton("◀ Previous FileID")
        self.prev_fileid_btn.clicked.connect(self.main_window.prev_fileid)
        self.prev_fileid_btn.setMinimumHeight(40)
        parent_layout.addWidget(self.prev_fileid_btn)

        # FileID selector dropdown
        self.fileid_combo = QComboBox()
        self.fileid_combo.setMinimumHeight(40)
        self.fileid_combo.setMinimumWidth(200)
        self.fileid_combo.currentTextChanged.connect(self.on_fileid_selected)
        parent_layout.addWidget(self.fileid_combo)

        parent_layout.addStretch()

        self.next_fileid_btn = QPushButton("Next FileID ▶")
        self.next_fileid_btn.clicked.connect(self.main_window.next_fileid)
        self.next_fileid_btn.setMinimumHeight(40)
        parent_layout.addWidget(self.next_fileid_btn)

    def connect_signals(self):
        """Connect signal handlers"""
        self.timeline.position_clicked.connect(self.sync_to_timeline_position)
        self.timeline.lane_change_position_changed.connect(self.on_lane_change_position_changed)
        self.timeline.event_modified.connect(self.on_event_modified)
        self.timeline.event_deleted.connect(self.on_event_deleted)
        self.timeline.event_created.connect(self.on_event_created)

    def on_event_modified(self, event_id: str, changes: dict):
        """Handle event modification"""
        logging.info(f"PhotoPreviewTab: Applying changes to event {event_id}: {changes}")
        for event in self.events:
            if event.event_id == event_id:
                for key, value in changes.items():
                    setattr(event, key, value)
                break
        self.events_modified = True
        # Use timeline_area.update() instead of timeline.update()
        if hasattr(self.timeline, 'timeline_area'):
            self.timeline.timeline_area.update()

    def on_event_deleted(self, event_id: str):
        """Handle event deletion"""
        logging.info(f"PhotoPreviewTab: Deleting event {event_id}")
        self.events = [event for event in self.events if event.event_id != event_id]
        self.events_modified = True
        logging.info(f"PhotoPreviewTab: {len(self.events)} events remaining after deletion")
        # Update timeline display without changing view range
        self.timeline.set_events(self.events, update_view_range=False)
        # Force update timeline area
        if hasattr(self.timeline, 'timeline_area'):
            self.timeline.timeline_area.update()

    def on_event_created(self, event):
        """Handle event creation"""
        logging.info(f"PhotoPreviewTab: Adding new event {event.event_id}")
        self.events.append(event)
        self.events_modified = True
        # Update timeline display
        self.timeline.set_events(self.events, update_view_range=False)
        # Force update timeline area
        if hasattr(self.timeline, 'timeline_area'):
            self.timeline.timeline_area.update()

    def on_lane_change_position_changed(self, timestamp: datetime):
        """Handle lane change position changed during drag"""
        logging.debug(f"PhotoPreviewTab: Lane change position changed to {timestamp}")
        # Update the lane change end timestamp
        if hasattr(self, 'lane_change_start_timestamp') and self.lane_change_start_timestamp:
            # Store the dragged timestamp for later use in lane change application
            self.lane_change_end_timestamp = timestamp
            logging.debug(f"PhotoPreviewTab: Lane change range: {self.lane_change_start_timestamp} to {timestamp}")

        # Sync image preview to the marker position
        self.sync_to_timeline_position(timestamp, (None, None))

    def load_fileid(self, fileid_folder):
        """Load data for a specific FileID"""
        logging.info(f"PhotoPreviewTab: Loading FileID {fileid_folder.fileid} from {fileid_folder.path}")
        
        try:
            # Store current FileID for saving
            self.current_fileid = fileid_folder
            
            # Use DataLoader to load all data
            data = self.data_loader.load_fileid_data(fileid_folder)

            # Store loaded data
            self.events = data['events']
            self.gps_data = data['gps_data']
            self.image_paths = data['image_paths']
            self.fileid_metadata = data['metadata']
            self.lane_manager = data['lane_manager']
            
            logging.info(f"PhotoPreviewTab: Stored {len(self.events)} events, {len(self.image_paths)} images")

            # Load first image if available BEFORE setting timeline events
            if self.image_paths:
                logging.info(f"Loading first image: {os.path.basename(self.image_paths[0])}")
                self.navigate_to_image(0)

                # Update UI components
                self.slider.setMaximum(len(self.image_paths) - 1)
                self.update_navigation_state()

                # Load timeline with events first
                self.timeline.set_events(self.events, update_view_range=False)

                # Set GPS data for chainage calculation
                if self.gps_data:
                    self.timeline.set_gps_data(self.gps_data)

                # Set lane manager for lane period display
                self.timeline.set_lane_manager(self.lane_manager)

                # Set timeline view range based on image folder time range (UTC)
                if self.fileid_metadata.get('first_image_timestamp') and self.fileid_metadata.get('last_image_timestamp'):
                    self.timeline.set_image_time_range(
                        self.fileid_metadata['first_image_timestamp'],
                        self.fileid_metadata['last_image_timestamp'],
                        self.fileid_metadata.get('first_image_coords'),
                        self.fileid_metadata.get('last_image_coords')
                    )

                # Update folder info display
                self.update_folder_info_display()
            else:
                logging.warning("PhotoPreviewTab: No images found in FileID")
            
            logging.info(f"PhotoPreviewTab: Successfully loaded FileID {fileid_folder.fileid}")
            if hasattr(self.main_window, 'update_fileid_navigation'):
                self.main_window.update_fileid_navigation()

            # Reset lane button states when switching FileID
            for button in self.lane_buttons.buttons():
                button.setChecked(False)
            self.turn_right_btn.setChecked(False)
            self.turn_left_btn.setChecked(False)
            self.update_lane_display()

        except Exception as e:
            logging.error(f"PhotoPreviewTab: Failed to load FileID {fileid_folder.fileid}: {str(e)}", exc_info=True)
            raise Exception(f"Failed to load FileID data: {str(e)}")

    def update_folder_info_display(self):
        """Update folder info display with current FileID metadata"""
        if hasattr(self, 'fileid_metadata'):
            metadata = self.fileid_metadata
            info_text = f"<b>FileID:</b> {metadata['fileid']}<br>"
            info_text += f"<b>Path:</b> {metadata['path']}<br>"
            info_text += f"<b>Images:</b> {metadata['image_count']}<br>"

            if metadata.get('first_image_timestamp'):
                first_time = metadata['first_image_timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                info_text += f"<b>First:</b> {first_time}<br>"
            if metadata.get('last_image_timestamp'):
                last_time = metadata['last_image_timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                info_text += f"<b>Last:</b> {last_time}"

            self.folder_info_label.setText(info_text)

    def navigate_to_image(self, index: int):
        """Navigate to specific image index"""
        if 0 <= index < len(self.image_paths):
            self.current_index = index
            self.load_current_image()
            self.update_navigation_state()
            self.slider.setValue(index)

            # Emit signal
            self.image_changed.emit(index, self.current_metadata)

            # Sync timeline
            timestamp = self.current_metadata.get('timestamp')
            if timestamp is not None:
                gps_coords = self.current_metadata.get('gps_coords', (None, None))
                self.timeline.set_current_position(timestamp)
                self.position_changed.emit(timestamp, gps_coords)

            # Update lane display based on current timestamp
            if self.lane_manager and timestamp:
                self.update_lane_display()

    def load_current_image(self):
        """Load and display current image"""
        if self.current_index < 0 or self.current_index >= len(self.image_paths):
            logging.warning(f"load_current_image: Invalid index {self.current_index}, total images: {len(self.image_paths)}")
            return

        image_path = self.image_paths[self.current_index]

        # Load image (with simple caching)
        if image_path not in self.image_cache:
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                self.image_label.setText(f"Failed to load image: {os.path.basename(image_path)}")
                logging.error(f"Failed to load pixmap for {image_path}")
                return

            # Scale down large images for display
            if pixmap.width() > 1920:
                pixmap = pixmap.scaledToWidth(1920, Qt.TransformationMode.SmoothTransformation)

            self.image_cache[image_path] = pixmap

        pixmap = self.image_cache[image_path]
        
        # Scale image to fit available space
        self.scale_image_to_fit()
        
        # Schedule a rescale after widget is fully displayed
        QTimer.singleShot(100, self.rescale_current_image)

        # Extract metadata
        self.current_metadata = extract_image_metadata(image_path)
        self.update_metadata_display()

    def rescale_current_image(self):
        """Rescale current image after widget is fully displayed"""
        if hasattr(self, 'image_paths') and self.image_paths and self.current_index >= 0:
            self.scale_image_to_fit()

    def scale_image_to_fit(self):
        """Scale current image to fit available space"""
        if self.current_index < 0 or not hasattr(self, 'image_cache') or not hasattr(self, 'image_paths'):
            return
            
        if self.current_index >= len(self.image_paths):
            return
            
        image_path = self.image_paths[self.current_index]
        if image_path not in self.image_cache:
            return
            
        pixmap = self.image_cache[image_path]
        
        # Get available size from scroll area
        if self.scroll_area and hasattr(self.scroll_area, 'viewport'):
            available_size = self.scroll_area.viewport().size()
            
            if available_size.width() <= 0 or available_size.height() <= 0:
                available_size = self.scroll_area.size()
            
            if available_size.width() <= 0 or available_size.height() <= 0:
                available_size = QSize(800, 600)
            
            available_width = max(100, available_size.width() - 20)
            available_height = max(100, available_size.height() - 20)
            
            scaled_pixmap = pixmap.scaled(
                available_width, available_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        """Handle resize events to rescale images"""
        super().resizeEvent(event)
        if hasattr(self, 'image_paths') and self.image_paths and self.current_index >= 0:
            self.scale_image_to_fit()

    def update_metadata_display(self):
        """Update metadata labels"""
        metadata = self.current_metadata

        # Testtime
        timestamp = metadata.get('timestamp', '--')
        if isinstance(timestamp, datetime):
            testtime_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        else:
            testtime_str = str(timestamp)

        # GPS coords
        lat = metadata.get('latitude', '--')
        lon = metadata.get('longitude', '--')
        
        if lat is not None:
            lat_str = f"{lat:.6f}"
        else:
            lat_str = '--'

        if lon is not None:
            lon_str = f"{lon:.6f}"
        else:
            lon_str = '--'

        # Bearing
        bearing = metadata.get('bearing', '--')
        if bearing is not None:
            bearing_str = f"{bearing}°"
        else:
            bearing_str = '--'

        # Truck (Plate)
        truck = metadata.get('plate', '--')

        # Update minimap
        self.update_minimap(lat, lon, bearing)

    def update_navigation_state(self):
        """Update navigation buttons and labels"""
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
        else:
            # Stop playback if at end
            if self.is_playing:
                self.toggle_playback()

    def slider_changed(self, value):
        """Handle slider value change"""
        if value != self.current_index:
            self.navigate_to_image(value)

    def toggle_playback(self):
        """Toggle slideshow playback"""
        if self.is_playing:
            self.playback_timer.stop()
            self.play_btn.setText("▶ Play")
            self.is_playing = False
        else:
            self.playback_timer.start(1000)
            self.play_btn.setText("⏸ Pause")
            self.is_playing = True

    def assign_lane(self, lane_code: str):
        """Assign lane at current position with smart change logic"""
        logging.info(f"PhotoPreviewTab: assign_lane called with lane_code='{lane_code}'")
        if not self.current_metadata or 'timestamp' not in self.current_metadata:
            logging.warning("PhotoPreviewTab: assign_lane failed - no current metadata")
            return

        if not self.lane_manager:
            logging.warning("PhotoPreviewTab: assign_lane failed - no lane_manager")
            return

        timestamp = self.current_metadata['timestamp']

        # Check if this is a smart change (changing from one lane to another)
        current_lane_at_time = self.lane_manager.get_lane_at_timestamp(timestamp)
        is_smart_change = (
            current_lane_at_time and 
            current_lane_at_time in ['1', '2', '3', '4'] and 
            lane_code in ['1', '2', '3', '4'] and
            current_lane_at_time != lane_code
        )

        if is_smart_change:
            # Use smart change logic
            success = self._perform_smart_lane_change(lane_code, timestamp)
        else:
            # Use standard assignment
            success = self.lane_manager.assign_lane(lane_code, timestamp)
            logging.info(f"PhotoPreviewTab: standard lane_manager.assign_lane returned success={success}")

        if success:
            self.update_lane_display()
            # Update timeline to show lane changes
            if hasattr(self.timeline, 'timeline_area'):
                self.timeline.timeline_area.update()
            # Reset turn buttons if turn was ended by lane assignment
            if not self.lane_manager.turn_active:
                self.turn_right_btn.setChecked(False)
                self.turn_left_btn.setChecked(False)
        else:
            logging.warning("PhotoPreviewTab: assign_lane failed")
            QMessageBox.warning(
                self, "Lane Assignment Failed",
                f"Cannot assign Lane {lane_code} at this time.\n\n"
                f"Reason: Lane assignment failed.\n\n"
                f"Time: {timestamp.strftime('%H:%M:%S')}\n"
                f"Plate: {self.current_metadata.get('plate', 'Unknown')}"
            )

    def _perform_smart_lane_change(self, new_lane_code: str, timestamp: datetime) -> bool:
        """Perform smart lane change with user choice dialog"""
        # Find current lane period
        current_lane = self.lane_manager.get_lane_at_timestamp(timestamp)
        
        # Find the lane fix record
        target_fix = None
        for fix in self.lane_manager.lane_fixes:
            if fix.from_time <= timestamp <= fix.to_time and fix.lane == current_lane:
                target_fix = fix
                break
        
        if not target_fix:
            logging.error("Could not find target lane fix for smart change")
            return False
        
        # Show choice dialog
        dialog = LaneChangeDialog(
            current_lane=current_lane,
            new_lane=new_lane_code,
            timestamp=timestamp,
            period_start=target_fix.from_time,
            period_end=target_fix.to_time,
            parent=self
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Always enable lane change mode using current position marker
            self._enable_lane_change_mode(new_lane_code, timestamp)
            return True  # Don't apply change yet, wait for marker confirmation
        else:
            logging.info("PhotoPreviewTab: Smart lane change cancelled by user")
            return False

    def _enable_lane_change_mode(self, new_lane_code: str, timestamp: datetime):
        """Enable lane change mode using current position marker"""
        self.lane_change_mode_active = True
        self.lane_change_new_lane = new_lane_code
        self.lane_change_start_timestamp = timestamp
        self.lane_change_end_timestamp = timestamp  # Initial end time same as start
        
        # Enable lane change mode on timeline
        self.timeline.enable_lane_change_mode(new_lane_code, timestamp)
        
        # Show marker buttons
        self._update_marker_buttons_visibility()

    def _exit_marker_mode(self):
        """Exit marker mode without applying changes"""
        self.marker_mode_active = False
        self.marker_new_lane = None
        self.marker_timestamp = None
        self.marker_period_start = None
        self.marker_period_end = None
        
        # Disable marker on timeline
        self.timeline.disable_marker_mode()
        
        # Hide marker buttons
        self._update_marker_buttons_visibility()

    def _exit_lane_change_mode(self):
        """Exit lane change mode without applying changes"""
        self.lane_change_mode_active = False
        self.lane_change_new_lane = None
        self.lane_change_start_timestamp = None
        
        # Disable lane change mode on timeline
        self.timeline.disable_lane_change_mode()
        
        # Hide marker buttons
        self._update_marker_buttons_visibility()

    def _apply_marker_change_from_button(self):
        """Apply marker change from button click"""
        if self.marker_mode_active and self.marker_timestamp:
            self._apply_marker_change(self.marker_timestamp)

    def _apply_lane_change(self):
        """Apply lane change using dragged marker range"""
        if not self.lane_change_mode_active:
            logging.warning("PhotoPreviewTab: _apply_lane_change called but lane change mode not active")
            return

        if not hasattr(self, 'lane_change_start_timestamp') or not hasattr(self, 'lane_change_end_timestamp'):
            logging.warning("PhotoPreviewTab: _apply_lane_change called but timestamps not set")
            return

        start_time = self.lane_change_start_timestamp
        end_time = self.lane_change_end_timestamp

        if start_time >= end_time:
            logging.warning("PhotoPreviewTab: Invalid time range for lane change")
            QMessageBox.warning(self, "Invalid Range", "End time must be after start time.")
            return

        # Apply the lane change
        success = self.lane_manager.change_lane_smart(
            self.lane_change_new_lane,
            start_time,
            lambda **kwargs: 'custom',  # Custom range selected by dragging
            custom_end_time=end_time
        )

        if success:
            logging.info(f"PhotoPreviewTab: Lane change applied - {self.lane_change_new_lane} from {start_time} to {end_time}")
            self.update_lane_display()
            # Update timeline to show lane changes
            if hasattr(self.timeline, 'timeline_area'):
                self.timeline.timeline_area.update()
            QMessageBox.information(self, "Success", f"Lane changed to {self.lane_change_new_lane} for the selected time range.")
        else:
            logging.error("PhotoPreviewTab: Lane change failed")
            QMessageBox.warning(self, "Error", "Failed to apply lane change.")

        # Exit lane change mode
        self._exit_lane_change_mode()

    def _update_marker_buttons_visibility(self):
        """Update marker buttons visibility based on marker mode"""
        self.marker_group.setVisible(self.marker_mode_active or self.lane_change_mode_active)

    def assign_sk(self):
        """Assign shoulder lane (SK) at current position"""
        logging.info("PhotoPreviewTab: assign_sk called")
        if not self.current_metadata or 'timestamp' not in self.current_metadata:
            logging.warning("PhotoPreviewTab: assign_sk failed - no current metadata")
            return

        if not self.lane_manager:
            logging.warning("PhotoPreviewTab: assign_sk failed - no lane_manager")
            return

        timestamp = self.current_metadata['timestamp']

        success = self.lane_manager.assign_sk(timestamp)
        logging.info(f"PhotoPreviewTab: lane_manager.assign_sk returned success={success}")

        if success:
            self.update_lane_display()
            # Update timeline to show lane changes
            if hasattr(self.timeline, 'timeline_area'):
                self.timeline.timeline_area.update()
            # Reset turn buttons if turn was ended by SK assignment
            if not self.lane_manager.turn_active:
                self.turn_right_btn.setChecked(False)
                self.turn_left_btn.setChecked(False)
        else:
            logging.warning("PhotoPreviewTab: assign_sk failed - overlap detected")
            QMessageBox.warning(
                self, "Shoulder Lane Assignment Failed",
                f"Cannot assign Shoulder Lane at this time.\n\n"
                f"Reason: Overlapping with existing lane assignment.\n\n"
                f"Time: {timestamp.strftime('%H:%M:%S')}\n"
                f"Plate: {self.current_metadata.get('plate', 'Unknown')}"
            )

    def assign_ignore(self):
        """Assign ignore period at current position"""
        logging.info("PhotoPreviewTab: assign_ignore called")
        if not self.current_metadata or 'timestamp' not in self.current_metadata:
            logging.warning("PhotoPreviewTab: assign_ignore failed - no current metadata")
            return

        if not self.lane_manager:
            logging.warning("PhotoPreviewTab: assign_ignore failed - no lane_manager")
            return

        timestamp = self.current_metadata['timestamp']

        success = self.lane_manager.assign_ignore(timestamp)
        logging.info(f"PhotoPreviewTab: lane_manager.assign_ignore returned success={success}")

        if success:
            self.update_lane_display()
            # Update timeline to show lane changes
            if hasattr(self.timeline, 'timeline_area'):
                self.timeline.timeline_area.update()
            # Reset turn buttons if turn was ended by ignore assignment
            if not self.lane_manager.turn_active:
                self.turn_right_btn.setChecked(False)
                self.turn_left_btn.setChecked(False)
        else:
            logging.warning("PhotoPreviewTab: assign_ignore failed - overlap detected")
            QMessageBox.warning(
                self, "Ignore Assignment Failed",
                f"Cannot assign Ignore period at this time.\n\n"
                f"Reason: Overlapping with existing lane assignment.\n\n"
                f"Time: {timestamp.strftime('%H:%M:%S')}\n"
                f"Plate: {self.current_metadata.get('plate', 'Unknown')}"
            )

    def start_turn(self, turn_type: str):
        """Start turn period or end if already active"""
        logging.info(f"PhotoPreviewTab: start_turn called with turn_type='{turn_type}'")
        if not self.current_metadata or 'timestamp' not in self.current_metadata:
            logging.warning("PhotoPreviewTab: start_turn failed - no current metadata")
            QMessageBox.warning(
                self, "Turn Start Failed",
                f"Cannot start turn period.\n\n"
                f"Reason: No current image metadata available.\n\n"
                f"Please ensure an image is selected."
            )
            return

        if not self.lane_manager:
            logging.warning("PhotoPreviewTab: start_turn failed - no lane_manager")
            QMessageBox.warning(
                self, "Turn Start Failed",
                f"Cannot start turn period.\n\n"
                f"Reason: Lane manager not initialized.\n\n"
                f"Please load a FileID first."
            )
            return

        timestamp = self.current_metadata['timestamp']

        # If turn is already active with same type, end it
        current_turn_type = None
        if self.lane_manager.turn_active and self.lane_manager.current_lane:
            if len(self.lane_manager.current_lane) >= 2 and self.lane_manager.current_lane[:2] in ['TK', 'TM']:
                current_turn_type = self.lane_manager.current_lane[:2]
        
        if current_turn_type == turn_type:
            logging.info(f"PhotoPreviewTab: Ending active {turn_type} turn")
            self.lane_manager.end_turn(timestamp)
            self.update_lane_display()
            # Update timeline to show lane changes
            if hasattr(self.timeline, 'timeline_area'):
                self.timeline.timeline_area.update()
            # Reset turn button
            if turn_type == 'TM':
                self.turn_right_btn.setChecked(False)
            elif turn_type == 'TK':
                self.turn_left_btn.setChecked(False)
            return

        # Get selected lane from button group
        selected_lane = None
        checked_button = self.lane_buttons.checkedButton()
        if checked_button:
            button_text = checked_button.text()
            if button_text == 'Lane 1':
                selected_lane = '1'
            elif button_text == 'Lane 2':
                selected_lane = '2'
            elif button_text == 'Lane 3':
                selected_lane = '3'
            elif button_text == 'Lane 4':
                selected_lane = '4'
        
        logging.info(f"PhotoPreviewTab: checked_button='{checked_button.text() if checked_button else None}', selected_lane='{selected_lane}'")

        # If no button selected, use current lane if it's a lane number
        if not selected_lane and self.lane_manager.current_lane:
            current = self.lane_manager.current_lane
            if current in ['1', '2', '3', '4']:
                selected_lane = current
                logging.info(f"PhotoPreviewTab: No button selected, using current_lane='{selected_lane}'")

        # Validate that we have a lane selected for turn
        if not selected_lane:
            logging.warning("PhotoPreviewTab: start_turn failed - no lane selected for turn")
            QMessageBox.warning(
                self, "Turn Start Failed",
                f"Cannot start {turn_type} turn period.\n\n"
                f"Reason: No lane selected.\n\n"
                f"Please select a lane (1-4) before starting a turn.\n\n"
                f"Time: {timestamp.strftime('%H:%M:%S')}\n"
                f"Plate: {self.current_metadata.get('plate', 'Unknown')}"
            )
            return

        logging.info(f"PhotoPreviewTab: Final selected_lane='{selected_lane}', calling lane_manager.start_turn")
        self.lane_manager.start_turn(turn_type, timestamp, selected_lane)
        self.update_lane_display()
        # Update timeline to show lane changes
        if hasattr(self.timeline, 'timeline_area'):
            self.timeline.timeline_area.update()
        # Set turn button checked
        if turn_type == 'TM':
            self.turn_right_btn.setChecked(True)
            self.turn_left_btn.setChecked(False)
        elif turn_type == 'TK':
            self.turn_left_btn.setChecked(True)
            self.turn_right_btn.setChecked(False)

    def update_lane_display(self):
        """Update current lane display based on current timestamp"""
        if not self.lane_manager:
            self.current_lane_label.setText("Current: None")
            # Reset all lane buttons
            for button in self.lane_buttons.buttons():
                button.setChecked(False)
            self.turn_right_btn.setChecked(False)
            self.turn_left_btn.setChecked(False)
            return

        current_lane = self.lane_manager.current_lane or "None"
        
        # If we have a current timestamp, get the lane at that timestamp
        if self.current_metadata and 'timestamp' in self.current_metadata:
            timestamp = self.current_metadata['timestamp']
            lane_at_time = self.lane_manager.get_lane_at_timestamp(timestamp)
            if lane_at_time:
                current_lane = lane_at_time
        
        self.current_lane_label.setText(f"Current: {current_lane}")
        logging.info(f"PhotoPreviewTab: update_lane_display - current_lane='{current_lane}'")

        # Update button states to match lane_manager state
        self._update_button_states(current_lane)

    def _update_button_states(self, current_lane: str):
        """Update UI button states to match the current lane state"""
        # Reset all lane buttons first
        for button in self.lane_buttons.buttons():
            button.setChecked(False)
        
        # Reset turn buttons
        self.turn_right_btn.setChecked(False)
        self.turn_left_btn.setChecked(False)

        # Set appropriate button based on current_lane
        if current_lane and current_lane != "None":
            # Check for regular lanes (1-4)
            if current_lane in ['1', '2', '3', '4']:
                for button in self.lane_buttons.buttons():
                    button_text = button.text()
                    if button_text == f'Lane {current_lane}':
                        button.setChecked(True)
                        break
            # Check for turn lanes (TK1, TM2, etc.)
            elif len(current_lane) >= 2 and current_lane[:2] in ['TK', 'TM']:
                turn_type = current_lane[:2]
                if turn_type == 'TM':
                    self.turn_right_btn.setChecked(True)
                elif turn_type == 'TK':
                    self.turn_left_btn.setChecked(True)
                # Also check the lane button if there's a lane number
                if len(current_lane) >= 3 and current_lane[2] in ['1', '2', '3', '4']:
                    lane_num = current_lane[2]
                    for button in self.lane_buttons.buttons():
                        if button.text() == f'Lane {lane_num}':
                            button.setChecked(True)
                            break

    def sync_to_timeline_position(self, timestamp: datetime, gps_coords: tuple):
        """Sync to timeline position - find closest image"""
        if not self.image_paths:
            return

        # Find image closest to timestamp
        closest_index = 0
        min_diff = float('inf')

        # Convert timestamp to naive for comparison
        timestamp_naive = timestamp.replace(tzinfo=None) if timestamp.tzinfo else timestamp

        for i, path in enumerate(self.image_paths):
            metadata = extract_image_metadata(path)
            img_timestamp = metadata.get('timestamp')
            if img_timestamp:
                # Convert to naive datetime for comparison
                img_timestamp_naive = img_timestamp.replace(tzinfo=None)
                diff = abs((img_timestamp_naive - timestamp_naive).total_seconds())
                if diff < min_diff:
                    min_diff = diff
                    closest_index = i

        if closest_index != self.current_index:
            self.navigate_to_image(closest_index)

    def clear_caches(self):
        """Clear image and GPS caches"""
        self.image_cache.clear()
        if self.gps_data:
            pass

    def save_all_events(self):
        """Save all current events to the .driveevt file with backup"""
        success = self.save_all_events_internal()
        if success:
            QMessageBox.information(self, "Success", f"Successfully saved {len(self.events)} events")
        else:
            QMessageBox.warning(self, "Error", "Failed to save events")

    def save_all_events_internal(self):
        """Save all current events to the .driveevt file with backup, return success"""
        if hasattr(self, 'current_fileid') and self.current_fileid:
            try:
                success = self.data_loader.save_events(self.events, self.current_fileid)
                if success:
                    logging.info(f"PhotoPreviewTab: Successfully saved {len(self.events)} events")
                    self.events_modified = False  # Reset change flag after successful save
                else:
                    logging.error("PhotoPreviewTab: Failed to save events")
                return success
            except PermissionError as e:
                logging.error(f"PhotoPreviewTab: Permission denied saving events: {e}")
                QMessageBox.critical(self, "Permission Error", f"Cannot save events due to permission error:\n\n{str(e)}\n\nPlease check file permissions and try again.")
                return False
            except OSError as e:
                logging.error(f"PhotoPreviewTab: File system error saving events: {e}")
                QMessageBox.critical(self, "File System Error", f"File system error while saving events:\n\n{str(e)}\n\nPlease check disk space and file system integrity.")
                return False
            except Exception as e:
                logging.error(f"PhotoPreviewTab: Unexpected error saving events: {e}")
                QMessageBox.critical(self, "Unexpected Error", f"An unexpected error occurred while saving events:\n\n{str(e)}")
                return False
        else:
            logging.warning("PhotoPreviewTab: No current FileID to save events to")
            return False

    def save_lane_codes(self):
        """Save lane codes to CSV file"""
        if hasattr(self, 'current_fileid') and self.current_fileid and self.lane_manager:
            try:
                # Create output path for lane fixes CSV
                output_path = os.path.join(self.current_fileid.path, f"{self.current_fileid.fileid}_lane_fixes.csv")
                success = self.export_manager.export_lane_fixes(self.lane_manager.lane_fixes, output_path)
                if success:
                    logging.info(f"PhotoPreviewTab: Successfully saved {len(self.lane_manager.lane_fixes)} lane fixes to {output_path}")
                    QMessageBox.information(self, "Success", f"Saved {len(self.lane_manager.lane_fixes)} lane fixes to:\n{output_path}")
                else:
                    logging.error("PhotoPreviewTab: Failed to save lane fixes")
                    QMessageBox.warning(self, "Error", "Failed to save lane fixes")
            except PermissionError as e:
                logging.error(f"PhotoPreviewTab: Permission denied saving lane fixes: {e}")
                QMessageBox.critical(self, "Permission Error", f"Cannot save lane fixes due to permission error:\n\n{str(e)}\n\nPlease check file permissions and try again.")
            except OSError as e:
                logging.error(f"PhotoPreviewTab: File system error saving lane fixes: {e}")
                QMessageBox.critical(self, "File System Error", f"File system error while saving lane fixes:\n\n{str(e)}\n\nPlease check disk space and file system integrity.")
            except Exception as e:
                logging.error(f"PhotoPreviewTab: Unexpected error saving lane fixes: {e}")
                QMessageBox.critical(self, "Unexpected Error", f"An unexpected error occurred while saving lane fixes:\n\n{str(e)}")
        else:
            logging.warning("PhotoPreviewTab: No current FileID or lane_manager to save lane fixes")
            QMessageBox.warning(self, "Warning", "No current FileID to save lane fixes to")

    def on_fileid_selected(self, fileid: str):
        """Handle FileID selection from dropdown"""
        logging.info(f"PhotoPreviewTab: on_fileid_selected called with fileid='{fileid}'")
        if not fileid or not hasattr(self.main_window, 'fileid_manager'):
            logging.warning("PhotoPreviewTab: on_fileid_selected - no fileid or fileid_manager")
            return
        
        # Check if this is already the current FileID
        current = self.main_window.fileid_manager.get_current_fileid()
        if current and current.fileid == fileid:
            logging.info(f"PhotoPreviewTab: on_fileid_selected - already current fileid {fileid}")
            return
        
        logging.info(f"PhotoPreviewTab: on_fileid_selected - switching to {fileid}")
        # Find the FileID folder
        for fileid_folder in self.main_window.fileid_manager.fileid_list:
            if fileid_folder.fileid == fileid:
                # Auto-save current data before switching
                self.main_window.auto_save_current_data()
                
                # Load the selected FileID
                self.main_window.load_fileid(fileid_folder)
                break

    def update_minimap(self, lat: float, lon: float, bearing: float = 0):
        """Update minimap with GPS position and bearing using Leaflet"""
        if lat is None or lon is None or lat == '--' or lon == '--':
            # Show empty map centered on default location
            lat, lon, bearing = -6.2, 106.816666, 0  # Default to Jakarta

        # Ensure bearing is a number
        if bearing is None or bearing == '--':
            bearing = 0
        
        try:
            bearing = float(bearing)
        except (ValueError, TypeError):
            bearing = 0

        # Normalize bearing to 0-360 range
        bearing = bearing % 360

        # Create HTML content for Leaflet map
        html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Minimap</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            html, body {{
                height: 100%;
                margin: 0;
                padding: 0;
            }}
            #map {{
                height: 100%;
                width: 100%;
            }}
            .coord-control {{
                background: white !important;
                padding: 5px !important;
                border: 1px solid #ccc !important;
                border-radius: 3px !important;
                font-family: monospace;
                font-size: 11px;
            }}
            /* Fix for bearing marker to ensure proper rotation */
            .bearing-marker {{
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }}
        </style>
    </head>
    <body>
        <div id="map"></div>
        <script>
            // Initialize map
            var map = L.map('map').setView([{lat}, {lon}], 18);

            // Add OpenStreetMap tiles
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '© OpenStreetMap contributors',
                maxZoom: 19
            }}).addTo(map);

            // Create custom marker with bearing arrow
            // Triangle points up (▲) at 0°, rotates clockwise
            var bearingIcon = L.divIcon({{
                html: '<div style="transform: rotate({bearing}deg); font-size: 32px; color: #ff0000; text-shadow: 2px 2px 3px rgba(255,255,255,0.9), -1px -1px 1px rgba(0,0,0,0.6); font-weight: bold; line-height: 1;">▲</div>',
                className: 'bearing-marker',
                iconSize: [32, 32],
                iconAnchor: [16, 16]  // Center the icon
            }});

            // Add marker with bearing
            var marker = L.marker([{lat}, {lon}], {{icon: bearingIcon}}).addTo(map);

            // Add coordinate display
            var coordControl = L.control({{position: 'bottomleft'}});
            coordControl.onAdd = function(map) {{
                var div = L.DomUtil.create('div', 'coord-control');
                div.innerHTML = '<div>Lat: {lat:.6f}<br>Lon: {lon:.6f}<br>Bearing: {bearing:.1f}°</div>';
                return div;
            }};
            coordControl.addTo(map);
        </script>
    </body>
    </html>
    """

        # Load HTML content into WebView
        self.minimap_view.setHtml(html_content)