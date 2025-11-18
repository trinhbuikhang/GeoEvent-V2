"""
Timeline Widget - GPS-synchronized timeline for event visualization and editing
"""

from datetime import datetime, timedelta, timezone
import time
from typing import List, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSlider, QMenu, QInputDialog, QMessageBox, QLineEdit
)
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal, QTimer, QMutex, QMutexLocker
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFont, QAction

from ..models.event_model import Event
from ..models.gps_model import GPSData

import logging

# Constants
LAYER_HEIGHT = 25
TIMELINE_TOP_MARGIN = 40
CONTROLS_HEIGHT = 60
CHAINAGE_SCALE_HEIGHT = 30  # Height for chainage scale at bottom
HANDLE_SNAP_DISTANCE = 20
DEFAULT_EVENT_DURATION = 30  # seconds
GRID_SNAP_SECONDS = 1
INT32_MIN = -2147483648
INT32_MAX = 2147483647
MAX_TIMEDELTA_SECONDS = 999999999  # Safe limit for timedelta

class TimelineArea(QWidget):
    """
    Widget for painting the timeline and chainage
    """

    def __init__(self, parent_widget):
        super().__init__()
        self.parent_widget = parent_widget
        self.setMouseTracking(True)

    def paintEvent(self, event):
        """Paint the timeline"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        timeline_height = rect.height() - CHAINAGE_SCALE_HEIGHT

        # Draw background
        painter.fillRect(rect, QColor('#1E2A38'))

        # Draw timeline area
        timeline_rect = QRect(0, TIMELINE_TOP_MARGIN, rect.width(), timeline_height - TIMELINE_TOP_MARGIN)
        painter.fillRect(timeline_rect, QColor('#2C3E50'))

        # Draw chainage scale area
        chainage_rect = QRect(0, timeline_height, rect.width(), CHAINAGE_SCALE_HEIGHT)
        painter.fillRect(chainage_rect, QColor('#34495E'))

        if self.parent_widget.view_start_time and self.parent_widget.view_end_time:
            self.parent_widget.paint_timeline(painter, timeline_rect)
            self.parent_widget.paint_chainage_scale(painter, chainage_rect)

    def mousePressEvent(self, event):
        self.parent_widget.mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.parent_widget.mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.parent_widget.mouseReleaseEvent(event)

    def wheelEvent(self, event):
        self.parent_widget.wheelEvent(event)

    def contextMenuEvent(self, event):
        self.parent_widget.contextMenuEvent(event)

class TimelineWidget(QWidget):
    """
    Timeline widget for GPS-synchronized event display and editing
    RESPONSIBILITIES:
    - Render timeline with GPS-synchronized events
    - Handle zoom/pan (mouse wheel, drag)
    - Event editing (drag handles, right-click menu)
    - Display event layers (prevent overlap)
    - Show current position marker
    """

    # Signals
    position_clicked = pyqtSignal(datetime, tuple)  # timestamp, (lat, lon)
    event_modified = pyqtSignal(str, dict)  # event_id, changes
    event_deleted = pyqtSignal(str)  # event_id
    event_created = pyqtSignal(object)  # Event object

    def __init__(self, photo_tab=None):
        super().__init__()
        self.photo_tab = photo_tab
        self.setMinimumHeight(200)

        # Data
        self.events: List[Event] = []
        self.gps_data: Optional[GPSData] = None
        self.current_position: Optional[datetime] = None
        self.lane_manager = None

        # View parameters
        self.view_start_time: Optional[datetime] = None
        self.view_end_time: Optional[datetime] = None
        self.base_view_start_time: Optional[datetime] = None  # Base range for zoom calculations
        self.base_view_end_time: Optional[datetime] = None
        self.image_start_time: Optional[datetime] = None  # Actual image time range for chainage mapping
        self.image_end_time: Optional[datetime] = None
        self.zoom_level = 1.0  # Zoom factor: 1.0 = full range, >1.0 = zoom in, <1.0 = zoom out
        self.pan_offset = 0

        # Interaction state
        self.dragging = False
        self.drag_start_pos = QPoint()
        self.selected_event: Optional[Event] = None
        self.drag_handle = None  # 'start', 'end', or 'move'
        self.dragging_marker = False

        # Event creation state
        self.creating_event = False
        self.new_event_start: Optional[datetime] = None
        self.new_event_end: Optional[datetime] = None
        self.new_event_name: str = ""
        self.event_coords: Optional[tuple] = None  # Store coordinates for event creation

        # Layer cache for performance
        self.layer_cache: Optional[List[List[Event]]] = None
        self.layer_cache_dirty = True
        self.cache_mutex = QMutex()  # Thread safety for cache

        # Colors
        self.event_colors = {
            'Bridge': QColor('#3498DB'),
            'Speed Hump': QColor('#E74C3C'),
            'Intersection': QColor('#F39C12'),
            'Road Works': QColor('#9B59B6'),
            'Roundabout': QColor('#1ABC9C'),
        }
        self.default_color = QColor('#95A5A6')

        # UI controls
        self.setup_ui()

        # Enable mouse tracking
        self.setMouseTracking(True)

    def set_gps_data(self, gps_data: GPSData):
        """Set GPS data for chainage calculations."""
        self.gps_data = gps_data

    def set_lane_manager(self, lane_manager):
        """Set lane manager for displaying lane periods."""
        self.lane_manager = lane_manager
        self.timeline_area.update()

    def get_chainage_at_time(self, timestamp: datetime) -> float:
        """Get chainage value at specific timestamp using GPS data."""
        if not self.gps_data:
            return 0.0
        return self.gps_data.interpolate_chainage(timestamp)

    def get_chainage_by_position(self, latitude: float, longitude: float) -> float:
        """Get chainage value at specific coordinates using GPS data."""
        if not self.gps_data:
            return 0.0
        return self.gps_data.interpolate_chainage_by_position(latitude, longitude)

    def setup_ui(self):
        """Setup timeline controls"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Timeline area
        self.timeline_area = TimelineArea(self)
        self.timeline_area.setMinimumHeight(200)
        layout.addWidget(self.timeline_area)

        # Control bar
        control_layout = QHBoxLayout()

        # Zoom controls
        self.zoom_out_btn = QPushButton("−")
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        control_layout.addWidget(self.zoom_out_btn)

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(1)      # 0.01 zoom out
        self.zoom_slider.setMaximum(10000) # 100.0 zoom in
        self.zoom_slider.setValue(100)     # 1.0 default zoom
        self.zoom_slider.valueChanged.connect(self.zoom_changed)
        control_layout.addWidget(self.zoom_slider)

        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        control_layout.addWidget(self.zoom_in_btn)

        # View mode
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItems(["Time", "Space"])
        self.view_mode_combo.currentTextChanged.connect(self.view_mode_changed)
        control_layout.addWidget(self.view_mode_combo)

        # Reset button
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self.reset_timeline)
        control_layout.addWidget(self.reset_btn)

        # Add event button
        self.add_event_btn = QPushButton("Add Event")
        self.add_event_btn.clicked.connect(self.add_event_dialog)
        control_layout.addWidget(self.add_event_btn)

        control_layout.addStretch()
        layout.addLayout(control_layout)

    def ensure_timezone(self, dt: datetime) -> datetime:
        """Ensure datetime has UTC timezone"""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def set_events(self, events: List[Event], update_view_range: bool = True):
        """Set events to display"""
        logging.debug(f"TimelineWidget: set_events called with {len(events)} events, update_view_range={update_view_range}")
        
        # Ensure all events have timezone
        for event in events:
            event.start_time = self.ensure_timezone(event.start_time)
            event.end_time = self.ensure_timezone(event.end_time)
        
        self.events = events
        self.invalidate_cache()  # Thread-safe cache invalidation
        
        if update_view_range:
            self.update_view_range()
        self.timeline_area.update()

    def invalidate_cache(self):
        """Thread-safe cache invalidation"""
        with QMutexLocker(self.cache_mutex):
            self.layer_cache_dirty = True

    def set_current_position(self, timestamp: datetime):
        """Set current position marker"""
        # Ensure timezone
        timestamp = self.ensure_timezone(timestamp)
        
        old_view_start = self.view_start_time
        old_view_end = self.view_end_time

        self.current_position = timestamp

        # Only set view range if no events are loaded yet
        # When events exist, ensure current position is visible while keeping events in view
        if not self.events:
            padding = timedelta(minutes=0.5)  # Show 0.5 minutes around current position
            self.view_start_time = timestamp - padding
            self.view_end_time = timestamp + padding
        else:
            # When events are loaded, ensure current position is visible
            # First, check if current position is within current view range
            if not (self.view_start_time <= timestamp <= self.view_end_time):
                # Current position is outside view range, need to pan
                # Calculate how much to shift the view to make current position visible
                current_span = self.view_end_time - self.view_start_time

                if timestamp < self.view_start_time:
                    # Current position is before view start, shift view left
                    self.view_start_time = timestamp - (current_span * 0.1)
                    self.view_end_time = self.view_start_time + current_span
                elif timestamp > self.view_end_time:
                    # Current position is after view end, shift view right
                    self.view_end_time = timestamp + (current_span * 0.1)
                    self.view_start_time = self.view_end_time - current_span

                # Ensure ALL events are still visible after panning
                if self.events:
                    start_times = [e.start_time for e in self.events]
                    end_times = [e.end_time for e in self.events]
                    min_event_time = min(start_times) - timedelta(seconds=30)
                    max_event_time = max(end_times) + timedelta(seconds=30)

                    # Adjust view if it would hide events
                    if self.view_start_time > min_event_time:
                        self.view_start_time = min_event_time
                        self.view_end_time = self.view_start_time + current_span
                    if self.view_end_time < max_event_time:
                        self.view_end_time = max_event_time
                        self.view_start_time = self.view_end_time - current_span

        self.timeline_area.update()

    def set_image_time_range(self, start_time: datetime, end_time: datetime, start_coords: tuple = None, end_coords: tuple = None):
        """Set timeline view range based on image folder time range (always UTC)"""
        logging.info(f"TimelineWidget: Setting image time range from {start_time} to {end_time}")
        logging.info(f"TimelineWidget: Image coords - start: {start_coords}, end: {end_coords}")

        # Ensure times are UTC
        start_time = self.ensure_timezone(start_time)
        end_time = self.ensure_timezone(end_time)

        # Store actual image time range for chainage mapping
        self.image_start_time = start_time
        self.image_end_time = end_time
        
        # Store coordinates for chainage calculation
        self.image_start_coords = start_coords
        self.image_end_coords = end_coords

        # If we have events, expand the view range to include them
        if self.events:
            event_times = []
            for event in self.events:
                event.start_time = self.ensure_timezone(event.start_time)
                event.end_time = self.ensure_timezone(event.end_time)
                event_times.extend([event.start_time, event.end_time])

            if event_times:
                min_event_time = min(event_times)
                max_event_time = max(event_times)

                # Expand image range to include events
                start_time = min(start_time, min_event_time)
                end_time = max(end_time, max_event_time)

                logging.info(f"TimelineWidget: Expanded time range to include events: {start_time} to {end_time}")

        # If we have lane fixes, expand the view range to include them
        if hasattr(self, 'lane_manager') and self.lane_manager:
            lane_fixes = self.lane_manager.get_lane_fixes()
            if lane_fixes:
                lane_times = []
                for fix in lane_fixes:
                    fix.from_time = self.ensure_timezone(fix.from_time)
                    fix.to_time = self.ensure_timezone(fix.to_time)
                    lane_times.extend([fix.from_time, fix.to_time])

                if lane_times:
                    min_lane_time = min(lane_times)
                    max_lane_time = max(lane_times)

                    # Expand image range to include lane fixes
                    start_time = min(start_time, min_lane_time)
                    end_time = max(end_time, max_lane_time)

                    logging.info(f"TimelineWidget: Expanded time range to include lane fixes: {start_time} to {end_time}")

        # Add padding to show full range
        padding = timedelta(minutes=0.5)  # 0.5 minute padding
        self.view_start_time = start_time - padding
        self.view_end_time = end_time + padding

        # Set base range for zoom calculations
        self.base_view_start_time = self.view_start_time
        self.base_view_end_time = self.view_end_time

        logging.info(f"TimelineWidget: Image time range set to {self.view_start_time} to {self.view_end_time} (with {padding} padding)")
        logging.debug(f"TimelineWidget: Base range set to {self.base_view_start_time} - {self.base_view_end_time}")

        # Auto-adjust zoom level to fit the time range in the widget width
        time_range_seconds = (self.view_end_time - self.view_start_time).total_seconds()
        if time_range_seconds > 0:
            self.zoom_level = 1.0

        self.invalidate_cache()
        self.timeline_area.update()

    def update_view_range(self):
        """Update visible time range based on events"""
        if not self.events:
            return

        # Find min/max times
        start_times = [e.start_time for e in self.events]
        end_times = [e.end_time for e in self.events]

        min_start = min(start_times)
        max_end = max(end_times)

        # Set base range
        self.base_view_start_time = min_start
        self.base_view_end_time = max_end

        # Add some padding to base
        padding = timedelta(seconds=30)
        self.base_view_start_time -= padding
        self.base_view_end_time += padding

        # Initially, view range equals base range
        self.view_start_time = self.base_view_start_time
        self.view_end_time = self.base_view_end_time

        logging.debug(f"TimelineWidget: Base range updated to {self.base_view_start_time} - {self.base_view_end_time}")
        logging.debug(f"TimelineWidget: View range updated to {self.view_start_time} - {self.view_end_time}")

    def zoom_changed(self, value):
        """Handle zoom slider change"""
        if not self.base_view_start_time or not self.base_view_end_time:
            return

        # Zoom level: 0.01 (zoom out) to 100.0 (zoom in), default 1.0
        self.zoom_level = value / 100.0  # slider value 1-10000 -> zoom 0.01-100.0

        # Calculate base range duration
        base_duration = (self.base_view_end_time - self.base_view_start_time).total_seconds()

        # Calculate new view duration (smaller when zoom in)
        new_duration = base_duration / self.zoom_level

        # Calculate center for zoom (use current position if available, otherwise current view center)
        if self.current_position and self.base_view_start_time <= self.current_position <= self.base_view_end_time:
            zoom_center = self.current_position
        elif self.view_start_time and self.view_end_time:
            zoom_center = self.view_start_time + (self.view_end_time - self.view_start_time) / 2
        else:
            zoom_center = self.base_view_start_time + timedelta(seconds=base_duration / 2)

        # Ensure center is within base range
        base_center = self.base_view_start_time + timedelta(seconds=base_duration / 2)
        max_offset = (base_duration - new_duration) / 2
        center_offset = (zoom_center - base_center).total_seconds()
        center_offset = max(-max_offset, min(max_offset, center_offset))

        # Calculate new view range
        new_center = base_center + timedelta(seconds=center_offset)
        self.view_start_time = new_center - timedelta(seconds=new_duration / 2)
        self.view_end_time = new_center + timedelta(seconds=new_duration / 2)

        # Ensure view range stays within base range
        if self.view_start_time < self.base_view_start_time:
            self.view_start_time = self.base_view_start_time
            self.view_end_time = self.view_start_time + timedelta(seconds=new_duration)
        if self.view_end_time > self.base_view_end_time:
            self.view_end_time = self.base_view_end_time
            self.view_start_time = self.view_end_time - timedelta(seconds=new_duration)

        logging.debug(f"Zoom level: {self.zoom_level}, View range: {self.view_start_time} - {self.view_end_time}")
        self.timeline_area.update()

    def zoom_in(self):
        """Zoom in"""
        current = self.zoom_slider.value()
        self.zoom_slider.setValue(min(current + 5, self.zoom_slider.maximum()))

    def zoom_out(self):
        """Zoom out"""
        current = self.zoom_slider.value()
        self.zoom_slider.setValue(max(current - 5, self.zoom_slider.minimum()))

    def view_mode_changed(self, mode):
        """Handle view mode change"""
        # TODO: Implement space-based view
        self.timeline_area.update()

    def reset_timeline(self):
        """Reset timeline to default state"""
        logging.info("TimelineWidget: Resetting timeline to default state")

        # Reset zoom
        self.zoom_level = 1.0
        self.zoom_slider.setValue(100)  # 100 corresponds to zoom_level = 1.0

        # Reset view range to base range
        if self.base_view_start_time and self.base_view_end_time:
            self.view_start_time = self.base_view_start_time
            self.view_end_time = self.base_view_end_time

        # Reset pan
        self.pan_offset = 0

        # Update display
        self.invalidate_cache()
        self.timeline_area.update()

        logging.info(f"TimelineWidget: Reset complete - zoom: {self.zoom_level}, view: {self.view_start_time} to {self.view_end_time}")

    def add_event_dialog(self, coords=None):
        """Show dialog to add new event"""
        logging.info(f"TimelineWidget: add_event_dialog called, current_position = {self.current_position}, coords = {coords}")
        if not self.current_position:
            QMessageBox.warning(self, "No Position", "Please navigate to an image first to set the event start time.")
            return

        # If no coordinates provided, try to get them from photo tab's current image
        if coords is None and self.photo_tab and hasattr(self.photo_tab, 'current_metadata'):
            lat = self.photo_tab.current_metadata.get('latitude')
            lon = self.photo_tab.current_metadata.get('longitude')
            if lat is not None and lon is not None:
                coords = (lat, lon)
                logging.debug(f"TimelineWidget: Retrieved coordinates from current image: {coords}")

        # Store coordinates for chainage calculation
        self.event_coords = coords

        # Show name input dialog
        event_name, ok = QInputDialog.getText(
            self, "New Event", "Enter event name:",
            QLineEdit.EchoMode.Normal, "New Event"
        )

        if ok and event_name.strip():
            logging.info(f"TimelineWidget: Starting event creation for '{event_name}' at {self.current_position}")
            self.creating_event = True
            self.new_event_start = self.current_position
            self.new_event_end = self.current_position  # Will be updated during drag
            self.new_event_name = event_name.strip()
            self.timeline_area.update()  # Repaint to show the marker

            logging.info(
                f"Event '{event_name}' started at current position.\n"
                "Drag the marker on the timeline to set the end time, then double-click to finish."
            )
        else:
            logging.info("TimelineWidget: Event creation cancelled")
            # Reset state on cancel
            self.creating_event = False
            self.new_event_start = None
            self.new_event_end = None
            self.new_event_name = ""
            self.event_coords = None  # Clear coordinates


    def paint_timeline(self, painter: QPainter, rect: QRect):
        """Paint timeline content"""
        # Calculate time range
        time_range = (self.view_end_time - self.view_start_time).total_seconds()
        if time_range <= 0:
            return

        # Check for zero width
        if rect.width() <= 0:
            return

        pixels_per_second = rect.width() / time_range

        # Prevent division by zero
        if pixels_per_second <= 0:
            pixels_per_second = 0.001

        # Draw time grid
        self.paint_time_grid(painter, rect, pixels_per_second)

        # Draw events
        self.paint_events(painter, rect, pixels_per_second)

        # Draw lane periods
        self.paint_lane_periods(painter, rect, pixels_per_second)

        # Draw current position
        if self.current_position:
            self.paint_current_position(painter, rect, pixels_per_second)

    def paint_time_grid(self, painter: QPainter, rect: QRect, pixels_per_second: float):
        """Paint time grid lines and labels"""
        painter.setPen(QPen(QColor('#34495E'), 1))

        # Calculate grid interval (try for ~100px spacing)
        target_spacing = 100
        seconds_per_grid = target_spacing / pixels_per_second if pixels_per_second > 0 else 1

        # Round to nice intervals
        if seconds_per_grid < 1:
            interval = 1
        elif seconds_per_grid < 60:
            interval = max(1, round(seconds_per_grid / 10) * 10)
        elif seconds_per_grid < 3600:
            interval = max(60, round(seconds_per_grid / 60) * 60)
        else:
            interval = max(3600, round(seconds_per_grid / 3600) * 3600)

        current_time = self.view_start_time.replace(second=0, microsecond=0)
        if interval >= 60:
            # Align to minute boundaries
            current_time = current_time.replace(second=0)

        while current_time <= self.view_end_time:
            x = self.time_to_pixel(current_time, pixels_per_second, rect.left())

            if 0 <= x <= rect.right():
                # Draw grid line
                painter.drawLine(int(x), rect.top(), int(x), rect.bottom())

                # Draw time label
                time_str = current_time.strftime("%H:%M:%S")
                painter.setPen(QColor('#ECF0F1'))
                painter.drawText(int(x) + 2, rect.top() + 15, time_str)
                painter.setPen(QColor('#34495E'))

            current_time += timedelta(seconds=interval)

    def paint_chainage_scale(self, painter: QPainter, rect: QRect):
        """Paint chainage scale at bottom of timeline"""
        if not self.gps_data or not self.view_start_time or not self.view_end_time:
            return

        if not self.gps_data.points:
            return

        # Use same time range and pixels_per_second as timeline for alignment
        time_range = (self.view_end_time - self.view_start_time).total_seconds()
        if time_range <= 0:
            return

        # Check for zero width before division
        if rect.width() <= 0:
            return

        pixels_per_second = rect.width() / time_range
        if pixels_per_second <= 0:
            pixels_per_second = 0.001

        # Calculate chainage range for visible time period
        visible_points = [p for p in self.gps_data.points 
                         if self.view_start_time <= p.timestamp <= self.view_end_time]
        if not visible_points:
            # Fallback to full range if no points in view
            min_chainage = min(p.chainage for p in self.gps_data.points)
            max_chainage = max(p.chainage for p in self.gps_data.points)
        else:
            min_chainage = min(p.chainage for p in visible_points)
            max_chainage = max(p.chainage for p in visible_points)
        
        chainage_range = max_chainage - min_chainage

        if chainage_range <= 0:
            return

        # Debug logging
        logging.debug(f"Chainage scale: GPS range {min_chainage:.1f}m to {max_chainage:.1f}m")
        logging.debug(f"Chainage scale: view_start={self.view_start_time}, view_end={self.view_end_time}")

        # Calculate grid interval for chainage (try for ~100px spacing)
        target_spacing = 100
        meters_per_grid = target_spacing * (chainage_range / rect.width()) if rect.width() > 0 else 100

        # Round to nice intervals (10m, 50m, 100m, 500m, 1000m, etc.)
        if meters_per_grid < 10:
            interval = 10
        elif meters_per_grid < 50:
            interval = max(10, round(meters_per_grid / 10) * 10)
        elif meters_per_grid < 100:
            interval = max(50, round(meters_per_grid / 50) * 50)
        elif meters_per_grid < 500:
            interval = max(100, round(meters_per_grid / 100) * 100)
        elif meters_per_grid < 1000:
            interval = max(500, round(meters_per_grid / 500) * 500)
        else:
            interval = max(1000, round(meters_per_grid / 1000) * 1000)

        # Draw chainage grid
        painter.setPen(QPen(QColor('#7F8C8D'), 1))

        current_chainage = round(min_chainage / interval) * interval
        while current_chainage <= max_chainage:
            # Find the timestamp that corresponds to this chainage
            corresponding_time = None
            for i, point in enumerate(self.gps_data.points):
                if point.chainage >= current_chainage:
                    if point.chainage == current_chainage:
                        corresponding_time = point.timestamp
                    elif i > 0:
                        # Interpolate between this point and the previous one
                        prev_point = self.gps_data.points[i-1]
                        chainage_diff = point.chainage - prev_point.chainage
                        if chainage_diff > 0:
                            time_diff = (point.timestamp - prev_point.timestamp).total_seconds()
                            ratio = (current_chainage - prev_point.chainage) / chainage_diff
                            corresponding_time = prev_point.timestamp + timedelta(seconds=time_diff * ratio)
                    break

            if corresponding_time:
                x = self.time_to_pixel(corresponding_time, pixels_per_second, rect.left())
            else:
                continue  # Skip if no corresponding time found

            if rect.left() <= x <= rect.right():
                # Draw grid line
                painter.drawLine(int(x), rect.top(), int(x), rect.bottom())

                # Draw chainage label
                chainage_str = f"{current_chainage:.0f}m"
                painter.setPen(QColor('#BDC3C7'))
                painter.drawText(int(x) + 2, rect.top() + 15, chainage_str)
                painter.setPen(QColor('#7F8C8D'))

            current_chainage += interval

    def rebuild_layer_cache(self, rect: QRect):
        """Rebuild layer cache for events"""
        with QMutexLocker(self.cache_mutex):
            max_layers = max(1, rect.height() // LAYER_HEIGHT)
            self.layer_cache = [[] for _ in range(max_layers)]

            for event in self.events:
                # Check if event is visible in current view
                event_visible = (event.start_time <= self.view_end_time and event.end_time >= self.view_start_time)
                
                if not event_visible:
                    continue

                # Find available layer
                layer = 0
                while layer < max_layers:
                    if not self.event_overlaps_layer(event, self.layer_cache[layer]):
                        self.layer_cache[layer].append(event)
                        break
                    layer += 1
                else:
                    # All layers full, use first layer
                    self.layer_cache[0].append(event)

            self.layer_cache_dirty = False

    def paint_events(self, painter: QPainter, rect: QRect, pixels_per_second: float):
        """Paint events on timeline"""
        # Rebuild cache if dirty
        if self.layer_cache_dirty or self.layer_cache is None:
            self.rebuild_layer_cache(rect)

        # Paint events by layer
        if self.layer_cache:
            for layer_idx, layer_events in enumerate(self.layer_cache):
                for event in layer_events:
                    self.paint_event(painter, rect, event, layer_idx, LAYER_HEIGHT, pixels_per_second)

        # Paint new event being created
        if self.creating_event and self.new_event_start and self.new_event_end:
            self.paint_new_event(painter, rect, pixels_per_second)

    def event_overlaps_layer(self, event: Event, layer_events: List[Event]) -> bool:
        """Check if event overlaps with events in layer"""
        for existing in layer_events:
            if (event.start_time < existing.end_time and
                event.end_time > existing.start_time):
                return True
        return False

    def paint_event(self, painter: QPainter, rect: QRect, event: Event,
                   layer: int, layer_height: int, pixels_per_second: float):
        """Paint individual event"""
        start_x = self.time_to_pixel(event.start_time, pixels_per_second, rect.left())
        end_x = self.time_to_pixel(event.end_time, pixels_per_second, rect.left())

        if end_x <= rect.left() or start_x >= rect.right():
            return  # Not visible

        # Clip to visible area
        visible_start = max(start_x, rect.left())
        visible_end = min(end_x, rect.right())
        width = visible_end - visible_start

        # Ensure minimum width for very short events (at least 8 pixels)
        MIN_EVENT_WIDTH = 8
        if width < MIN_EVENT_WIDTH and visible_start < visible_end:
            # Extend the visible area to meet minimum width
            center = (visible_start + visible_end) / 2
            half_width = MIN_EVENT_WIDTH / 2
            visible_start = max(rect.left(), center - half_width)
            visible_end = min(rect.right(), center + half_width)
            width = visible_end - visible_start

        if width < 1:
            return

        # Event bar
        y = rect.top() + layer * layer_height
        height = layer_height - 2

        color = self.event_colors.get(event.event_name, self.default_color)
        painter.fillRect(int(visible_start), y, int(width), height, color)

        # Event border
        painter.setPen(QPen(QColor('#000000'), 1))
        painter.drawRect(int(visible_start), y, int(width), height)

        # Event label (if space)
        if width > 50:
            painter.setPen(QColor('#FFFFFF'))
            font = painter.font()
            font.setPointSize(8)
            painter.setFont(font)
            label = event.event_name
            painter.drawText(int(visible_start) + 2, y + 12, label)

    def paint_lane_periods(self, painter: QPainter, rect: QRect, pixels_per_second: float):
        """Paint lane periods below the timeline"""
        if not hasattr(self, 'lane_manager') or not self.lane_manager:
            return

        lane_fixes = self.lane_manager.get_lane_fixes()
        if not lane_fixes:
            return

        # Draw lane periods as thin horizontal bars below the marker
        lane_bar_y = rect.bottom() + 5  # Just below the timeline
        lane_bar_height = 3  # Thin bar

        for fix in lane_fixes:
            start_x = self.time_to_pixel(fix.from_time, pixels_per_second, rect.left())
            end_x = self.time_to_pixel(fix.to_time, pixels_per_second, rect.left())

            if end_x <= rect.left() or start_x >= rect.right():
                continue  # Not visible

            # Clip to visible area
            visible_start = max(start_x, rect.left())
            visible_end = min(end_x, rect.right())
            width = visible_end - visible_start

            if width < 1:
                continue

            # Get lane color
            color = QColor(self.lane_manager.get_lane_color(fix.lane))
            painter.fillRect(int(visible_start), lane_bar_y, int(width), lane_bar_height, color)

    def paint_current_position(self, painter: QPainter, rect: QRect, pixels_per_second: float):
        """Paint current position marker"""
        if not self.current_position:
            return

        x = self.time_to_pixel(self.current_position, pixels_per_second, rect.left())

        if rect.left() <= x <= rect.right():
            painter.setPen(QPen(QColor('#FFFF00'), 1))  # Bright yellow, thicker
            painter.drawLine(int(x), rect.top(), int(x), rect.bottom())

            # Large arrow pointing up above timeline area
            painter.setPen(QPen(QColor('#FFFF00'), 1))  # Bright yellow, thicker
            painter.setBrush(QBrush(QColor('#FFFF00')))  # Bright yellow
            arrow_size = 30  # Larger arrow for easier clicking
            arrow_y = 0  # Position above timeline area
            # Draw arrow triangle pointing up
            arrow_points = [
                QPoint(int(x), arrow_y + arrow_size),  # Bottom point
                QPoint(int(x) - arrow_size//2, arrow_y),  # Top left
                QPoint(int(x) + arrow_size//2, arrow_y)   # Top right
            ]
            painter.drawPolygon(arrow_points)

            # Draw vertical line from arrow to timeline
            painter.setPen(QPen(QColor('#FFFF00'), 1))  # Bright yellow, thicker
            painter.drawLine(int(x), arrow_y + arrow_size, int(x), rect.bottom())
        else:
            logging.debug(f"TimelineWidget: Marker is outside visible area at x={x:.1f} (visible range: {rect.left()} to {rect.right()})")

    def paint_new_event(self, painter: QPainter, rect: QRect, pixels_per_second: float):
        """Paint the new event marker being created"""
        if not self.new_event_start or not self.new_event_end:
            return

        # Draw start marker
        start_x = self.time_to_pixel(self.new_event_start, pixels_per_second, rect.left())
        if rect.left() <= start_x <= rect.right():
            painter.setPen(QPen(QColor('#E74C3C'), 2))
            painter.setBrush(QBrush(QColor('#E74C3C')))
            painter.drawEllipse(int(start_x) - 6, rect.top() + 5, 12, 12)

            # Start label
            painter.setPen(QColor('#FFFFFF'))
            font = painter.font()
            font.setPointSize(7)
            painter.setFont(font)
            painter.drawText(int(start_x) - 20, rect.top() + 25, "START")

        # Draw end marker
        end_x = self.time_to_pixel(self.new_event_end, pixels_per_second, rect.left())
        if rect.left() <= end_x <= rect.right():
            painter.setPen(QPen(QColor('#27AE60'), 2))
            painter.setBrush(QBrush(QColor('#27AE60')))
            painter.drawEllipse(int(end_x) - 6, rect.top() + 5, 12, 12)

            # End label
            painter.setPen(QColor('#FFFFFF'))
            painter.drawText(int(end_x) - 15, rect.top() + 25, "END")

        # Draw connecting line
        if start_x < end_x:
            painter.setPen(QPen(QColor('#E74C3C'), 2))
            painter.drawLine(int(start_x), rect.top() + 11, int(end_x), rect.top() + 11)

            # Event name label
            mid_x = (start_x + end_x) / 2
            painter.setPen(QColor('#FFFFFF'))
            painter.drawText(int(mid_x) - 30, rect.top() + 40, self.new_event_name)

    def time_to_pixel(self, time: datetime, pixels_per_second: float, offset: int = 0) -> float:
        """Convert timestamp to pixel position with overflow protection"""
        if not self.view_start_time:
            return 0

        # Ensure timezone
        time = self.ensure_timezone(time)
        
        # Calculate seconds difference
        seconds = (time - self.view_start_time).total_seconds()
        
        # Clamp seconds to safe range before multiplication
        seconds = max(-MAX_TIMEDELTA_SECONDS, min(MAX_TIMEDELTA_SECONDS, seconds))
        
        # Calculate pixel position
        pixel_pos = offset + seconds * pixels_per_second
        
        # Clamp to prevent INT32 overflow
        return max(INT32_MIN, min(INT32_MAX, pixel_pos))

    def pixel_to_time(self, x: float, pixels_per_second: float, offset: int = 0) -> datetime:
        """Convert pixel position to timestamp with validation"""
        if not self.view_start_time or pixels_per_second <= 0:
            return datetime.now(timezone.utc)

        # Validate input x is within reasonable bounds
        x = max(INT32_MIN, min(INT32_MAX, x))
        
        # Calculate seconds
        seconds = (x - offset) / pixels_per_second
        
        # Clamp seconds to safe range for timedelta
        seconds = max(-MAX_TIMEDELTA_SECONDS, min(MAX_TIMEDELTA_SECONDS, seconds))
        
        try:
            return self.view_start_time + timedelta(seconds=seconds)
        except (OverflowError, ValueError) as e:
            logging.error(f"Error converting pixel to time: {e}")
            return self.view_start_time

    def mousePressEvent(self, event):
        """Handle mouse press"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.handle_left_click(event)
        elif event.button() == Qt.MouseButton.RightButton:
            self.handle_right_click(event)

        super().mousePressEvent(event)

    def handle_left_click(self, event):
        """Handle left mouse click"""
        rect = self.timeline_area.rect()
        timeline_rect = QRect(0, TIMELINE_TOP_MARGIN, rect.width(), rect.height() - CHAINAGE_SCALE_HEIGHT)

        logging.debug(f"TimelineWidget: Left click at pos {event.position().toPoint()}, timeline_rect {timeline_rect}")

        # Check if clicking on current position marker (even outside timeline rect)
        marker_clicked = self.is_click_on_current_position_marker(event.position().toPoint())
        if marker_clicked:
            logging.debug("TimelineWidget: Clicked on marker")
            # Start dragging marker
            self.dragging_marker = True
            self.drag_start_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)  # Set cursor immediately when starting drag
            # Position click
            pixels_per_second = self.calculate_pixels_per_second(timeline_rect)
            click_time = self.pixel_to_time(event.position().x(), pixels_per_second, timeline_rect.left())
            gps_coords = (None, None)  # TODO: Get GPS coords from GPS data
            self.position_clicked.emit(click_time, gps_coords)
            return

        if not timeline_rect.contains(event.position().toPoint()):
            logging.debug("TimelineWidget: Click outside timeline rect")
            return

        # Convert to time
        pixels_per_second = self.calculate_pixels_per_second(timeline_rect)
        click_time = self.pixel_to_time(event.position().x(), pixels_per_second, timeline_rect.left())

        logging.debug(f"TimelineWidget: Click time {click_time}")

        # Handle event creation
        if self.creating_event:
            # Update end time during drag, but don't complete yet
            self.new_event_end = click_time
            self.timeline_area.update()  # Repaint to show updated marker
            return

        # Check for event at position
        clicked_event = self.get_event_at_position(event.position().toPoint(), timeline_rect, pixels_per_second)

        if clicked_event:
            logging.debug(f"TimelineWidget: Clicked on event: {clicked_event.event_name}")
            # Start dragging
            self.selected_event = clicked_event
            self.dragging = True
            self.drag_start_pos = event.position().toPoint()

            # Determine drag handle with adaptive snap distance
            start_x = self.time_to_pixel(clicked_event.start_time, pixels_per_second, timeline_rect.left())
            end_x = self.time_to_pixel(clicked_event.end_time, pixels_per_second, timeline_rect.left())

            mouse_x = event.position().x()
            event_width = end_x - start_x
            
            # Use larger snap distance for very short events
            snap_distance = max(HANDLE_SNAP_DISTANCE, min(15, event_width / 4))
            
            if abs(mouse_x - start_x) < snap_distance:
                self.drag_handle = 'start'
            elif abs(mouse_x - end_x) < snap_distance:
                self.drag_handle = 'end'
            else:
                self.drag_handle = 'move'
        else:
            logging.debug("TimelineWidget: Click in empty area")

    def handle_right_click(self, event):
        """Handle right mouse click"""
        rect = self.timeline_area.rect()
        timeline_rect = QRect(0, TIMELINE_TOP_MARGIN, rect.width(), rect.height() - CHAINAGE_SCALE_HEIGHT)

        if not timeline_rect.contains(event.position().toPoint()):
            return

        pixels_per_second = self.calculate_pixels_per_second(timeline_rect)
        clicked_event = self.get_event_at_position(event.position().toPoint(), timeline_rect, pixels_per_second)

        menu = QMenu(self)

        if clicked_event:
            # Event menu
            edit_action = QAction("Edit Event", self)
            edit_action.triggered.connect(lambda: self.edit_event(clicked_event))
            menu.addAction(edit_action)

            delete_action = QAction("Delete Event", self)
            delete_action.triggered.connect(lambda: self.delete_event(clicked_event))
            menu.addAction(delete_action)
        else:
            # Empty area menu
            add_action = QAction("Add Event", self)
            click_time = self.pixel_to_time(event.position().x(), pixels_per_second, timeline_rect.left())
            add_action.triggered.connect(lambda: self.add_event_at_time(click_time))
            menu.addAction(add_action)

        menu.exec(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        """Handle mouse move"""
        if self.dragging and self.selected_event:
            self.handle_drag(event)
        elif self.dragging_marker:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.handle_drag_marker(event)
        elif self.creating_event:
            # Update end time during event creation
            rect = self.timeline_area.rect()
            timeline_rect = QRect(0, TIMELINE_TOP_MARGIN, rect.width(), rect.height() - CHAINAGE_SCALE_HEIGHT)
            if timeline_rect.contains(event.position().toPoint()):
                pixels_per_second = self.calculate_pixels_per_second(timeline_rect)
                mouse_time = self.pixel_to_time(event.position().x(), pixels_per_second, timeline_rect.left())
                self.new_event_end = mouse_time
                self.timeline_area.update()  # Repaint to show updated marker
                
                # Sync to nearest image
                self.position_clicked.emit(mouse_time, (None, None))
        else:
            self.update_cursor(event)
            
            # Update tooltip for event hover
            self.update_event_tooltip(event)

        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Handle double click to edit event or complete event creation"""
        if event.button() == Qt.MouseButton.LeftButton:
            rect = self.timeline_area.rect()
            timeline_rect = QRect(0, TIMELINE_TOP_MARGIN, rect.width(), rect.height() - CHAINAGE_SCALE_HEIGHT)

            if timeline_rect.contains(event.position().toPoint()):
                pixels_per_second = self.calculate_pixels_per_second(timeline_rect)
                click_time = self.pixel_to_time(event.position().x(), pixels_per_second, timeline_rect.left())

                # Handle event creation completion
                if self.creating_event:
                    self.new_event_end = click_time
                    self.complete_event_creation()
                    return

                # Find event at click position
                clicked_event = self.get_event_at_position(event.position().toPoint(), timeline_rect, pixels_per_second)
                if clicked_event:
                    self.edit_event(clicked_event)

        super().mouseDoubleClickEvent(event)

    def edit_event(self, event: Event):
        """Edit an event using dialog"""
        logging.info(f"TimelineWidget: User opened edit dialog for event '{event.event_name}' (ID: {event.event_id})")
        from .event_editor import EventEditor
        edited_event = EventEditor.edit_event(event, self)
        if edited_event:
            logging.info(f"TimelineWidget: User saved changes to event '{edited_event.event_name}' (ID: {edited_event.event_id})")
            # Emit modification signal
            changes = {
                'event_name': edited_event.event_name,
                'start_time': edited_event.start_time,
                'end_time': edited_event.end_time,
                'start_chainage': edited_event.start_chainage,
                'end_chainage': edited_event.end_chainage
            }
            self.event_modified.emit(edited_event.event_id, changes)
            self.invalidate_cache()
            self.timeline_area.update()

    def handle_drag_marker(self, event):
        """Handle dragging current position marker"""
        rect = self.timeline_area.rect()
        timeline_rect = QRect(0, TIMELINE_TOP_MARGIN, rect.width(), rect.height() - CHAINAGE_SCALE_HEIGHT)
        pixels_per_second = self.calculate_pixels_per_second(timeline_rect)

        new_time = self.pixel_to_time(event.position().x(), pixels_per_second, timeline_rect.left())

        # Update current position
        self.current_position = new_time
        self.timeline_area.update()

        # Emit position changed for realtime sync
        self.position_clicked.emit(new_time, (None, None))

    def handle_drag(self, event):
        """Handle dragging events"""
        rect = self.timeline_area.rect()
        timeline_rect = QRect(0, TIMELINE_TOP_MARGIN, rect.width(), rect.height() - CHAINAGE_SCALE_HEIGHT)
        pixels_per_second = self.calculate_pixels_per_second(timeline_rect)

        new_time = self.pixel_to_time(event.position().x(), pixels_per_second, timeline_rect.left())

        # Prepare changes dict
        changes = {}

        # Update event based on drag handle
        if self.drag_handle == 'start':
            self.selected_event.start_time = new_time
            changes['start_time'] = new_time
        elif self.drag_handle == 'end':
            self.selected_event.end_time = new_time
            changes['end_time'] = new_time
        elif self.drag_handle == 'move':
            duration = self.selected_event.end_time - self.selected_event.start_time
            self.selected_event.start_time = new_time
            self.selected_event.end_time = new_time + duration
            changes['start_time'] = new_time
            changes['end_time'] = new_time + duration

        # Emit modification signal
        self.event_modified.emit(self.selected_event.event_id, changes)
        self.invalidate_cache()
        self.timeline_area.update()

        # Sync to nearest image
        self.position_clicked.emit(new_time, (None, None))

    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if self.dragging:
            self.dragging = False
            self.selected_event = None
            self.drag_handle = None
        if self.dragging_marker:
            self.dragging_marker = False
            # Reset cursor after dragging
            self.update_cursor(event)

        super().mouseReleaseEvent(event)

    def update_cursor(self, event):
        """Update cursor based on position"""
        rect = self.timeline_area.rect()
        timeline_rect = QRect(0, TIMELINE_TOP_MARGIN, rect.width(), rect.height() - CHAINAGE_SCALE_HEIGHT)

        if not timeline_rect.contains(event.position().toPoint()):
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        pixels_per_second = self.calculate_pixels_per_second(timeline_rect)
        event_at_pos = self.get_event_at_position(event.position().toPoint(), timeline_rect, pixels_per_second)

        if event_at_pos:
            start_x = self.time_to_pixel(event_at_pos.start_time, pixels_per_second, timeline_rect.left())
            end_x = self.time_to_pixel(event_at_pos.end_time, pixels_per_second, timeline_rect.left())

            mouse_x = event.position().x()
            event_width = end_x - start_x
            
            # Use larger snap distance for very short events
            snap_distance = max(HANDLE_SNAP_DISTANCE, min(15, event_width / 4))
            
            if abs(mouse_x - start_x) < snap_distance or abs(mouse_x - end_x) < snap_distance:
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            else:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            if self.is_click_on_current_position_marker(event.position().toPoint()):
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)

    def update_event_tooltip(self, event):
        """Update tooltip for event under mouse"""
        rect = self.timeline_area.rect()
        timeline_rect = QRect(0, TIMELINE_TOP_MARGIN, rect.width(), rect.height() - CHAINAGE_SCALE_HEIGHT)
        
        if not timeline_rect.contains(event.position().toPoint()):
            self.timeline_area.setToolTip("")
            return

        pixels_per_second = self.calculate_pixels_per_second(timeline_rect)
        hovered_event = self.get_event_at_position(event.position().toPoint(), timeline_rect, pixels_per_second)

        if hovered_event:
            # Create tooltip with event information
            tooltip_lines = []
            tooltip_lines.append(f"<b>{hovered_event.event_name}</b>")
            tooltip_lines.append(f"Start: {hovered_event.start_time.strftime('%H:%M:%S')}")
            tooltip_lines.append(f"End: {hovered_event.end_time.strftime('%H:%M:%S')}")
            tooltip_lines.append(f"Duration: {hovered_event.duration_seconds:.1f}s")
            tooltip_lines.append(f"Chainage: {hovered_event.start_chainage:.1f}m - {hovered_event.end_chainage:.1f}m")
            tooltip_lines.append(f"Length: {hovered_event.length_meters:.1f}m")
            
            tooltip = "<br>".join(tooltip_lines)
            self.timeline_area.setToolTip(tooltip)
        else:
            self.timeline_area.setToolTip("")

    def is_click_on_current_position_marker(self, pos: QPoint) -> bool:
        """Check if click position is on the current position marker arrow"""
        if not self.current_position:
            logging.debug("TimelineWidget: No current position")
            return False

        rect = self.timeline_area.rect()
        timeline_rect = QRect(0, TIMELINE_TOP_MARGIN, rect.width(), rect.height() - CHAINAGE_SCALE_HEIGHT)
        pixels_per_second = self.calculate_pixels_per_second(timeline_rect)

        x = self.time_to_pixel(self.current_position, pixels_per_second, timeline_rect.left())
        logging.debug(f"TimelineWidget: Marker x={x}, pos={pos}, rect={rect.left()}-{rect.right()}")
        if not (rect.left() <= x <= rect.right()):
            logging.debug("TimelineWidget: Marker not in view")
            return False

        # Arrow position
        arrow_y = 0  # Match paint position
        arrow_size = 50  # Match paint size

        # Check if click is within the arrow bounding box only (not the entire line)
        px, py = pos.x(), pos.y()
        arrow_rect = QRect(int(x - arrow_size//2), arrow_y, arrow_size, arrow_size)
        result = arrow_rect.contains(pos)
        logging.debug(f"TimelineWidget: Arrow rect {arrow_rect}, click at ({px}, {py}), inside={result}")
        return result

    def calculate_pixels_per_second(self, timeline_rect: QRect) -> float:
        """Calculate pixels per second for current view"""
        if not self.view_start_time or not self.view_end_time:
            return 1.0

        time_range = (self.view_end_time - self.view_start_time).total_seconds()
        if time_range <= 0:
            return 1.0
            
        pixels_per_second = timeline_rect.width() / time_range
        
        # Prevent division by zero in pixel_to_time
        return max(0.001, pixels_per_second)

    def get_event_at_position(self, pos: QPoint, timeline_rect: QRect, pixels_per_second: float) -> Optional[Event]:
        """Get event at mouse position (returns the topmost event in layers)"""
        # Rebuild cache if needed
        if self.layer_cache_dirty or self.layer_cache is None:
            self.rebuild_layer_cache(timeline_rect)

        # Check layers from top to bottom (higher layers are drawn on top)
        for layer_idx in range(len(self.layer_cache) - 1, -1, -1):
            layer_events = self.layer_cache[layer_idx]
            for event in layer_events:
                # Check if event is visible in current view
                if not (event.start_time <= self.view_end_time and event.end_time >= self.view_start_time):
                    continue

                start_x = self.time_to_pixel(event.start_time, pixels_per_second, timeline_rect.left())
                end_x = self.time_to_pixel(event.end_time, pixels_per_second, timeline_rect.left())

                # Safety check for invalid coordinates
                if not (INT32_MIN <= start_x <= INT32_MAX and INT32_MIN <= end_x <= INT32_MAX):
                    continue

                # Check if event is on screen
                if end_x <= timeline_rect.left() or start_x >= timeline_rect.right():
                    continue

                # Check event rect at this layer with hover tolerance
                y = timeline_rect.top() + layer_idx * LAYER_HEIGHT
                event_rect = QRect(int(start_x), y, int(end_x - start_x), LAYER_HEIGHT)

                # Add hover tolerance for short events (expand rect by 5 pixels on each side)
                HOVER_TOLERANCE = 5
                expanded_rect = event_rect.adjusted(-HOVER_TOLERANCE, -HOVER_TOLERANCE, HOVER_TOLERANCE, HOVER_TOLERANCE)

                if expanded_rect.contains(pos):
                    return event

        return None

    def snap_time_to_grid(self, timestamp: datetime) -> datetime:
        """Snap timestamp to grid"""
        timestamp = self.ensure_timezone(timestamp)
        epoch = timestamp.timestamp()
        snapped = round(epoch / GRID_SNAP_SECONDS) * GRID_SNAP_SECONDS
        snapped_dt = datetime.fromtimestamp(snapped, tz=timezone.utc)
        return snapped_dt

    def delete_event(self, event: Event):
        """Delete event"""
        logging.info(f"TimelineWidget: User requested to delete event '{event.event_name}' (ID: {event.event_id})")
        reply = QMessageBox.question(
            self, "Delete Event",
            f"Delete event '{event.event_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            logging.info(f"TimelineWidget: User confirmed deletion of event '{event.event_name}' (ID: {event.event_id})")
            self.event_deleted.emit(event.event_id)
            self.invalidate_cache()
        else:
            logging.info(f"TimelineWidget: User cancelled deletion of event '{event.event_name}' (ID: {event.event_id})")

    def add_event_at_time(self, timestamp: datetime, coords=None):
        """Add event at timestamp"""
        # Set current position to timestamp and call add_event_dialog
        self.current_position = self.ensure_timezone(timestamp)
        
        # If no coordinates provided, try to get them from photo tab's current image
        if coords is None and self.photo_tab and hasattr(self.photo_tab, 'current_metadata'):
            lat = self.photo_tab.current_metadata.get('latitude')
            lon = self.photo_tab.current_metadata.get('longitude')
            if lat is not None and lon is not None:
                coords = (lat, lon)
                logging.debug(f"TimelineWidget: Retrieved coordinates from current image: {coords}")
        
        self.add_event_dialog(coords)

    def complete_event_creation(self):
        """Complete the creation of a new event"""
        if not self.creating_event or not self.new_event_start or not self.new_event_end or not self.new_event_name:
            return

        # Ensure start time is before end time
        if self.new_event_start >= self.new_event_end:
            self.new_event_end = self.new_event_start + timedelta(seconds=DEFAULT_EVENT_DURATION)

        # Create new event
        from ..models.event_model import Event
        import uuid
        event_id = f"{self.new_event_name.replace(' ', '_')}_{self.new_event_start.strftime('%Y-%m-%dT%H:%M:%S')}"

        # Calculate chainage using GPS data
        # Use coordinates if available for more accurate chainage calculation
        if self.event_coords and len(self.event_coords) == 2:
            # Use coordinates from current image for both start and end chainage
            start_chainage = self.get_chainage_by_position(self.event_coords[0], self.event_coords[1])
            end_chainage = start_chainage  # Same position for now, will be adjusted if needed
            logging.debug(f"TimelineWidget: Using coordinates {self.event_coords} for chainage calculation: {start_chainage}")
        else:
            # Fallback to time-based calculation
            start_chainage = self.get_chainage_at_time(self.new_event_start)
            end_chainage = self.get_chainage_at_time(self.new_event_end)
            logging.debug(f"TimelineWidget: Using time-based chainage calculation")

        new_event = Event(
            event_id=event_id,
            event_name=self.new_event_name,
            start_time=self.new_event_start,
            end_time=self.new_event_end,
            start_chainage=start_chainage,
            end_chainage=end_chainage,
            file_id=getattr(self.photo_tab, 'current_fileid', '') if self.photo_tab else ''
        )

        logging.info(f"TimelineWidget: Created new event '{self.new_event_name}' (ID: {event_id}) from {self.new_event_start} to {self.new_event_end}")

        # Reset creation state and clear coordinates
        self.creating_event = False
        self.new_event_start = None
        self.new_event_end = None
        self.new_event_name = ""
        self.event_coords = None  # Clear coordinates after use

        # Invalidate layer cache
        self.invalidate_cache()

        # Emit signal to add the event
        self.event_created.emit(new_event)

    def save_events(self):
        """Save all events"""
        if self.photo_tab and hasattr(self.photo_tab, 'save_all_events_internal'):
            success = self.photo_tab.save_all_events_internal()
            if success:
                self.save_event_btn.setText("✅ Saved!")
                QTimer.singleShot(2000, lambda: self.save_event_btn.setText("💾 Save Event"))
            else:
                self.save_event_btn.setText("❌ Save Failed!")
                QTimer.singleShot(3000, lambda: self.save_event_btn.setText("💾 Save Event"))
        else:
            logging.warning("TimelineWidget: Cannot save events - photo_tab or save_all_events_internal method not available")

    def save_lane_codes(self):
        """Save lane codes"""
        if self.photo_tab and hasattr(self.photo_tab, 'save_lane_codes'):
            self.photo_tab.save_lane_codes()
        else:
            logging.warning("TimelineWidget: Cannot save lane codes - photo_tab or save_lane_codes method not available")