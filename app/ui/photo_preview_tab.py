"""
Photo Preview Tab - Main UI component for GeoEvent application
"""

import os
import logging
from datetime import datetime
from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QFrame, QScrollArea, QGroupBox, QButtonGroup, QSplitter, QSizePolicy, QMessageBox
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
        self.lane_manager = LaneManager()

        self.image_cache = {}  # Simple cache for loaded images
        self.current_metadata = {}
        self.scroll_area = None  # Reference to scroll area for image display

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
        #self.minimap_view.setMaximumSize(200, 250)
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
        lanecode_group = QGroupBox("Lanecode button control")
        lanecode_group.setStyleSheet("QGroupBox { border: 2px solid black; padding: 10px; }")
        lanecode_layout = QVBoxLayout()
        self.setup_lane_controls(lanecode_layout)
        lanecode_group.setLayout(lanecode_layout)
        lanecode_group.setMinimumHeight(100)  # Reduced from 120 to 80 (2/3)
        lanecode_group.setMaximumHeight(120)  # Reduced from 150 to 100 (2/3)
        right_layout.addWidget(lanecode_group, stretch=1)

        # FileID button control
        fileid_group = QGroupBox("FileID button control")
        fileid_group.setStyleSheet("QGroupBox { border: 2px solid black; padding: 10px; }")
        fileid_layout = QHBoxLayout()
        self.setup_fileid_controls(fileid_layout)
        fileid_group.setLayout(fileid_layout)
        fileid_group.setMinimumHeight(60)
        fileid_group.setMaximumHeight(80)
        right_layout.addWidget(fileid_group)

        # No stretch at bottom - FileID control will align with bottom of photo canvas
        top_splitter.addWidget(right_widget)

        # Set splitter proportions (60% photo, 40% controls)
        top_splitter.setSizes([600, 400])
        main_layout.addWidget(top_splitter, stretch=7)

        # Timeline and event marker display (no label, just timeline)
        timeline_frame = QFrame()
        timeline_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        timeline_frame.setLineWidth(2)
        timeline_layout = QVBoxLayout(timeline_frame)
        timeline_layout.setContentsMargins(5, 5, 5, 5)
        
        self.timeline = TimelineWidget()
        timeline_layout.addWidget(self.timeline)
        
        main_layout.addWidget(timeline_frame, stretch=3)

        # Bottom section: Navigation and buttons in one row
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        # Photo navigation buttons
        nav_group = QGroupBox("Photo navi button")
        nav_group.setStyleSheet("QGroupBox { border: 2px solid black; padding: 5px; }")
        nav_layout = QHBoxLayout()
        self.setup_navigation_buttons(nav_layout)
        nav_group.setLayout(nav_layout)
        bottom_layout.addWidget(nav_group)

        # Save event button
        save_event_group = QGroupBox("Save event button")
        save_event_group.setStyleSheet("QGroupBox { border: 2px solid black; padding: 5px; }")
        save_event_layout = QVBoxLayout()
        self.save_events_btn = QPushButton("Save Events")
        self.save_events_btn.clicked.connect(self.save_all_events)
        self.save_events_btn.setMinimumHeight(40)
        save_event_layout.addWidget(self.save_events_btn)
        save_event_group.setLayout(save_event_layout)
        bottom_layout.addWidget(save_event_group)

        # Save lane code button
        save_lane_group = QGroupBox("Save lane code button")
        save_lane_group.setStyleSheet("QGroupBox { border: 2px solid black; padding: 5px; }")
        save_lane_layout = QVBoxLayout()
        self.save_lane_btn = QPushButton("Save Lane Codes")
        self.save_lane_btn.clicked.connect(self.save_lane_codes)
        self.save_lane_btn.setMinimumHeight(40)
        save_lane_layout.addWidget(self.save_lane_btn)
        save_lane_group.setLayout(save_lane_layout)
        bottom_layout.addWidget(save_lane_group)

        main_layout.addLayout(bottom_layout)

        # Photo slider - no frame, direct slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)
        self.slider.valueChanged.connect(self.slider_changed)
        self.slider.setMinimumHeight(30)
        main_layout.addWidget(self.slider)

    def setup_image_display(self, parent_layout):
        """Setup image display area"""
        # Scroll area for image
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
        # Previous button
        self.prev_btn = QPushButton("◀ Previous")
        self.prev_btn.clicked.connect(self.prev_image)
        self.prev_btn.setMinimumHeight(40)
        parent_layout.addWidget(self.prev_btn)

        # Play/Pause button
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.clicked.connect(self.toggle_playback)
        self.play_btn.setMinimumHeight(40)
        parent_layout.addWidget(self.play_btn)

        # Next button
        self.next_btn = QPushButton("Next ▶")
        self.next_btn.clicked.connect(self.next_image)
        self.next_btn.setMinimumHeight(40)
        parent_layout.addWidget(self.next_btn)

        # Position label
        self.position_label = QLabel("0 / 0")
        self.position_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.position_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        parent_layout.addWidget(self.position_label)

        # Playback timer
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.next_image)
        self.is_playing = False

    def setup_lane_controls(self, parent_layout):
        """Setup lane controls"""
        # Row 1: Lane buttons
        lane_row = QHBoxLayout()
        lane_codes = ['1', '2', '3', '4']
        lane_names = ['Lane 1', 'Lane 2', 'Lane 3', 'Lane 4']

        for code, name in zip(lane_codes, lane_names):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, c=code: self.assign_lane(c))
            btn.setMinimumHeight(30)
            self.lane_buttons.addButton(btn)
            lane_row.addWidget(btn)

        parent_layout.addLayout(lane_row)

        # Row 2: Turn buttons and current lane
        turn_row = QHBoxLayout()
        
        self.turn_right_btn = QPushButton("TM ↱ (Turn Right)")
        self.turn_right_btn.clicked.connect(lambda: self.start_turn('TM'))
        self.turn_right_btn.setMinimumHeight(30)
        turn_row.addWidget(self.turn_right_btn)

        self.turn_left_btn = QPushButton("TK ↰ (Turn Left)")
        self.turn_left_btn.clicked.connect(lambda: self.start_turn('TK'))
        self.turn_left_btn.setMinimumHeight(30)
        turn_row.addWidget(self.turn_left_btn)

        self.current_lane_label = QLabel("Current: None")
        self.current_lane_label.setStyleSheet("font-weight: bold; padding: 5px;")
        self.current_lane_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        turn_row.addWidget(self.current_lane_label)

        parent_layout.addLayout(turn_row)

    def setup_fileid_controls(self, parent_layout):
        """Setup FileID navigation controls"""
        self.prev_fileid_btn = QPushButton("◀ Previous FileID")
        self.prev_fileid_btn.clicked.connect(self.main_window.prev_fileid)
        self.prev_fileid_btn.setMinimumHeight(40)
        parent_layout.addWidget(self.prev_fileid_btn)

        parent_layout.addStretch()

        self.next_fileid_btn = QPushButton("Next FileID ▶")
        self.next_fileid_btn.clicked.connect(self.main_window.next_fileid)
        self.next_fileid_btn.setMinimumHeight(40)
        parent_layout.addWidget(self.next_fileid_btn)

    def update_minimap(self, lat: float, lon: float):
        """Update minimap with GPS position"""
        if lat is None or lon is None:
            self.minimap_label.setText("minimap\n(No GPS data)")
            self.minimap_label.setPixmap(QPixmap())
            return

        # Create a QImage for minimap
        width, height = self.minimap_label.width() - 10, self.minimap_label.height() - 10
        if width <= 0 or height <= 0:
            width, height = 190, 140
            
        image = QImage(width, height, QImage.Format.Format_RGB32)
        image.fill(Qt.GlobalColor.white)

        painter = QPainter(image)
        painter.setPen(QPen(Qt.GlobalColor.black, 1))
        painter.setBrush(QBrush(Qt.GlobalColor.lightGray))

        # Draw a simple map (rectangle)
        map_margin = 10
        painter.drawRect(map_margin, map_margin, width - 2*map_margin, height - 2*map_margin)

        # Draw grid
        painter.setPen(QPen(Qt.GlobalColor.gray, 1))
        grid_cols = 4
        grid_rows = 4
        for i in range(1, grid_cols):
            x = map_margin + i * (width - 2*map_margin) / grid_cols
            painter.drawLine(int(x), map_margin, int(x), height - map_margin)
        for i in range(1, grid_rows):
            y = map_margin + i * (height - 2*map_margin) / grid_rows
            painter.drawLine(map_margin, int(y), width - map_margin, int(y))

        # Scale coordinates to map
        x = int(map_margin + (width - 2*map_margin) * ((lon + 180) / 360))
        y = int(map_margin + (height - 2*map_margin) * ((90 - lat) / 180))

        # Draw position point
        painter.setPen(QPen(Qt.GlobalColor.red, 3))
        painter.setBrush(QBrush(Qt.GlobalColor.red))
        painter.drawEllipse(QPointF(x, y), 5, 5)

        # Draw cross
        painter.drawLine(x - 7, y, x + 7, y)
        painter.drawLine(x, y - 7, x, y + 7)

        painter.end()

        # Convert to QPixmap
        pixmap = QPixmap.fromImage(image)
        self.minimap_label.setPixmap(pixmap)

    def connect_signals(self):
        """Connect signal handlers"""
        self.timeline.position_clicked.connect(self.sync_to_timeline_position)
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
        # Update timeline display
        self.timeline.update()

    def on_event_deleted(self, event_id: str):
        """Handle event deletion"""
        logging.info(f"PhotoPreviewTab: Deleting event {event_id}")
        self.events = [event for event in self.events if event.event_id != event_id]
        logging.info(f"PhotoPreviewTab: {len(self.events)} events remaining after deletion")
        # Update timeline display without changing view range
        self.timeline.set_events(self.events, update_view_range=False)

    def on_event_created(self, event):
        """Handle event creation"""
        logging.info(f"PhotoPreviewTab: Adding new event {event.event_id}")
        self.events.append(event)
        # Update timeline display
        self.timeline.set_events(self.events, update_view_range=False)

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
            self.main_window.update_fileid_label()

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

            # Add timestamp info if available
            if metadata['first_image_timestamp']:
                first_time = metadata['first_image_timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                info_text += f"<b>First:</b> {first_time}<br>"
            if metadata['last_image_timestamp']:
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

        # No extra info label to update anymore

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
            self.playback_timer.start(1000)  # 1 second intervals
            self.play_btn.setText("⏸ Pause")
            self.is_playing = True

    def assign_lane(self, lane_code: str):
        """Assign lane at current position"""
        logging.info(f"PhotoPreviewTab: assign_lane called with lane_code='{lane_code}'")
        if not self.current_metadata or 'timestamp' not in self.current_metadata:
            logging.warning("PhotoPreviewTab: assign_lane failed - no current metadata")
            return

        timestamp = self.current_metadata['timestamp']
        plate = self.current_metadata.get('plate', '')
        file_id = getattr(self, 'current_fileid', '')

        success = self.lane_manager.assign_lane(lane_code, timestamp, plate, file_id)
        logging.info(f"PhotoPreviewTab: lane_manager.assign_lane returned success={success}")

        if success:
            self.update_lane_display()
        else:
            logging.warning("PhotoPreviewTab: assign_lane failed - overlap detected")

    def start_turn(self, turn_type: str):
        """Start turn period or end if already active"""
        logging.info(f"PhotoPreviewTab: start_turn called with turn_type='{turn_type}'")
        if not self.current_metadata or 'timestamp' not in self.current_metadata:
            logging.warning("PhotoPreviewTab: start_turn failed - no current metadata")
            return

        timestamp = self.current_metadata['timestamp']
        plate = self.current_metadata.get('plate', '')
        file_id = getattr(self, 'current_fileid', '')

        # If turn is already active with same type, end it
        current_turn_type = None
        if self.lane_manager.turn_active and self.lane_manager.current_lane:
            # Extract turn type from current lane (TK1 -> TK, TM2 -> TM)
            if len(self.lane_manager.current_lane) >= 2 and self.lane_manager.current_lane[:2] in ['TK', 'TM']:
                current_turn_type = self.lane_manager.current_lane[:2]
        
        if current_turn_type == turn_type:
            logging.info(f"PhotoPreviewTab: Ending active {turn_type} turn")
            self.lane_manager.end_turn(timestamp)
            self.update_lane_display()
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

        logging.info(f"PhotoPreviewTab: Final selected_lane='{selected_lane}', calling lane_manager.start_turn")
        self.lane_manager.start_turn(turn_type, timestamp, plate, file_id, selected_lane)
        self.update_lane_display()

    def update_lane_display(self):
        """Update current lane display"""
        current_lane = self.lane_manager.current_lane or "None"
        self.current_lane_label.setText(f"Current: {current_lane}")
        logging.info(f"PhotoPreviewTab: update_lane_display - current_lane='{current_lane}'")

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
            success = self.data_loader.save_events(self.events, self.current_fileid)
            if success:
                logging.info(f"PhotoPreviewTab: Successfully saved {len(self.events)} events")
            else:
                logging.error("PhotoPreviewTab: Failed to save events")
            return success
        else:
            logging.warning("PhotoPreviewTab: No current FileID to save events to")
            return False

    def save_lane_codes(self):
        """Save lane codes to CSV file"""
        if hasattr(self, 'current_fileid') and self.current_fileid:
            # Create output path for lane fixes CSV
            output_path = os.path.join(self.current_fileid.path, f"{self.current_fileid.fileid}_lane_fixes.csv")
            success = self.export_manager.export_lane_fixes(self.lane_manager.lane_fixes, output_path)
            if success:
                logging.info(f"PhotoPreviewTab: Successfully saved {len(self.lane_manager.lane_fixes)} lane fixes to {output_path}")
                QMessageBox.information(self, "Success", f"Saved {len(self.lane_manager.lane_fixes)} lane fixes to:\n{output_path}")
            else:
                logging.error("PhotoPreviewTab: Failed to save lane fixes")
                QMessageBox.warning(self, "Error", "Failed to save lane fixes")
        else:
            logging.warning("PhotoPreviewTab: No current FileID to save lane fixes to")
            QMessageBox.warning(self, "Warning", "No current FileID to save lane fixes to")

    def update_minimap(self, lat: float, lon: float, bearing: float = 0):
        """Update minimap with GPS position and bearing using Leaflet"""
        if lat is None or lon is None:
            # Show empty map centered on default location
            lat, lon, bearing = -6.2, 106.816666, 0  # Default to Jakarta

        # Ensure bearing is a number
        if bearing is None:
            bearing = 0

        # Normalize bearing to 0-360 range (REMOVED the +180 adjustment)
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