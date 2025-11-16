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
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFont, QAction

from ..models.event_model import Event

import logging

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

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(200)

        # Data
        self.events: List[Event] = []
        self.current_position: Optional[datetime] = None

        # View parameters
        self.view_start_time: Optional[datetime] = None
        self.view_end_time: Optional[datetime] = None
        self.zoom_level = 50.0  # pixels per second - adjusted for smaller time ranges
        self.pan_offset = 0

        # Interaction state
        self.dragging = False
        self.drag_start_pos = QPoint()
        self.selected_event: Optional[Event] = None
        self.drag_handle = None  # 'start', 'end', or 'move'

        # Event creation state
        self.creating_event = False
        self.new_event_start: Optional[datetime] = None
        self.new_event_end: Optional[datetime] = None
        self.new_event_name: str = ""

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

    def setup_ui(self):
        """Setup timeline controls"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Control bar
        control_layout = QHBoxLayout()

        # Zoom controls
        self.zoom_out_btn = QPushButton("−")
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        control_layout.addWidget(self.zoom_out_btn)

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(1)
        self.zoom_slider.setMaximum(10000)  # Increased max for very large time ranges
        self.zoom_slider.setValue(100000)  # Increased default zoom for large time ranges
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

        # Add event button
        self.add_event_btn = QPushButton("Add Event")
        self.add_event_btn.clicked.connect(self.add_event_dialog)
        control_layout.addWidget(self.add_event_btn)

        control_layout.addStretch()
        layout.addLayout(control_layout)

        # Timeline area will be painted in paintEvent

    def set_events(self, events: List[Event], update_view_range: bool = True):
        """Set events to display"""
        # logging.info(f"TimelineWidget: set_events called with {len(events)} events, update_view_range={update_view_range}")
        for i, event in enumerate(events):
            logging.info(f"  Event {i}: {event.event_name} - {event.start_time} to {event.end_time}")

        self.events = events
        if update_view_range:
            self.update_view_range()
        self.update()

    def set_current_position(self, timestamp: datetime):
        """Set current position marker"""
        # logging.info(f"TimelineWidget: set_current_position called with timestamp={timestamp}")
        # logging.info(f"TimelineWidget: Current state - events: {len(self.events)}, view_start: {self.view_start_time}, view_end: {self.view_end_time}")

        old_view_start = self.view_start_time
        old_view_end = self.view_end_time

        self.current_position = timestamp

        # Only set view range if no events are loaded yet
        # When events exist, ensure current position is visible while keeping events in view
        if not self.events:
            padding = timedelta(minutes=30)  # Show 30 minutes around current position
            self.view_start_time = timestamp - padding
            self.view_end_time = timestamp + padding
            # logging.info(f"TimelineWidget: No events loaded, setting initial view range: {self.view_start_time} to {self.view_end_time}")
        else:
            # When events are loaded, ensure current position is visible
            # First, check if current position is within current view range
            if not (self.view_start_time <= timestamp <= self.view_end_time):
                # Current position is outside view range, need to pan
                # Calculate how much to shift the view to make current position visible
                current_span = self.view_end_time - self.view_start_time

                if timestamp < self.view_start_time:
                    # Current position is before view start, shift view left
                    shift_amount = self.view_start_time - timestamp + (current_span * 0.1)  # Keep some margin
                    self.view_start_time = timestamp - (current_span * 0.1)
                    self.view_end_time = self.view_start_time + current_span
                elif timestamp > self.view_end_time:
                    # Current position is after view end, shift view right
                    shift_amount = timestamp - self.view_end_time + (current_span * 0.1)  # Keep some margin
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

                # logging.info(f"TimelineWidget: Panned view range to show current position while keeping events visible: {self.view_start_time} to {self.view_end_time}")
            else:
                # Current position already within view range - no action needed
                pass

        # Log view range change
        # if old_view_start != self.view_start_time or old_view_end != self.view_end_time:
        #     logging.info(f"TimelineWidget: View range changed from {old_view_start}-{old_view_end} to {self.view_start_time}-{self.view_end_time}")

        self.update()

    def set_image_time_range(self, start_time: datetime, end_time: datetime):
        """Set timeline view range based on image folder time range (always UTC)"""
        logging.info(f"TimelineWidget: Setting image time range from {start_time} to {end_time}")

        # Ensure times are UTC
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        # If we have events, expand the view range to include them
        if self.events:
            event_times = []
            for event in self.events:
                if event.start_time.tzinfo is None:
                    event.start_time = event.start_time.replace(tzinfo=timezone.utc)
                if event.end_time.tzinfo is None:
                    event.end_time = event.end_time.replace(tzinfo=timezone.utc)
                event_times.extend([event.start_time, event.end_time])

            if event_times:
                min_event_time = min(event_times)
                max_event_time = max(event_times)

                # Expand image range to include events
                start_time = min(start_time, min_event_time)
                end_time = max(end_time, max_event_time)

                logging.info(f"TimelineWidget: Expanded time range to include events: {start_time} to {end_time}")

        # Add padding to show full range
        padding = timedelta(minutes=5)  # 5 minutes padding
        self.view_start_time = start_time - padding
        self.view_end_time = end_time + padding

        logging.info(f"TimelineWidget: Image time range set to {self.view_start_time} to {self.view_end_time} (with {padding} padding)")

        # Auto-adjust zoom level to fit the time range in the widget width
        time_range_seconds = (self.view_end_time - self.view_start_time).total_seconds()
        if time_range_seconds > 0:
            # pixels_per_second = (width * zoom_level) / time_range_seconds
            # To fit time_range in width, pixels_per_second = width / time_range_seconds
            # So zoom_level = 1.0
            self.zoom_level = 1.0

        self.update()

    def update_view_range(self):
        """Update visible time range based on events"""
        # logging.info(f"TimelineWidget: update_view_range called with {len(self.events)} events")
        if not self.events:
            # logging.info("TimelineWidget: No events to update view range")
            return

        old_view_start = self.view_start_time
        old_view_end = self.view_end_time

        # Find min/max times
        start_times = [e.start_time for e in self.events]
        end_times = [e.end_time for e in self.events]

        min_start = min(start_times)
        max_end = max(end_times)

        # logging.info(f"TimelineWidget: Event time range - min_start: {min_start}, max_end: {max_end}")

        self.view_start_time = min_start
        self.view_end_time = max_end

        # Add some padding
        padding = timedelta(seconds=30)
        self.view_start_time -= padding
        self.view_end_time += padding

        # logging.info(f"TimelineWidget: View range updated from {old_view_start}-{old_view_end} to {self.view_start_time}-{self.view_end_time} (with {padding} padding)")
        # logging.info(f"TimelineWidget: Events in current view range:")
        for i, event in enumerate(self.events):
            in_view = (event.start_time >= self.view_start_time and event.start_time <= self.view_end_time) or \
                     (event.end_time >= self.view_start_time and event.end_time <= self.view_end_time)
            logging.info(f"  Event {i}: {event.event_name} - {event.start_time} to {event.end_time} (in_view: {in_view})")

    def zoom_changed(self, value):
        """Handle zoom slider change"""
        self.zoom_level = value / 10.0  # 0.1 to 10.0
        self.update()

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
        self.update()

    def add_event_dialog(self):
        """Show dialog to add new event"""
        logging.info(f"TimelineWidget: add_event_dialog called, current_position = {self.current_position}")
        if not self.current_position:
            QMessageBox.warning(self, "No Position", "Please navigate to an image first to set the event start time.")
            return

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
            self.update()  # Repaint to show the marker

            logging.info(
                f"Event '{event_name}' started at current position.\n"
                "Drag the marker on the timeline to set the end time, then double-click to finish."
            )
        else:
            logging.info("TimelineWidget: Event creation cancelled")

    def paintEvent(self, event):
        """Paint the timeline"""
        # logging.info(f"TimelineWidget: paintEvent called - view_range: {self.view_start_time} to {self.view_end_time}")
        # logging.info(f"TimelineWidget: Current state - {len(self.events)} events, current_position: {self.current_position}")

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        timeline_height = rect.height() - 60  # Leave space for controls

        # Draw background
        painter.fillRect(rect, QColor('#1E2A38'))

        # Draw timeline area
        timeline_rect = QRect(0, 40, rect.width(), timeline_height)
        painter.fillRect(timeline_rect, QColor('#2C3E50'))

        if self.view_start_time and self.view_end_time:
            self.paint_timeline(painter, timeline_rect)

    def paint_timeline(self, painter: QPainter, rect: QRect):
        """Paint timeline content"""
        # Calculate time range
        time_range = (self.view_end_time - self.view_start_time).total_seconds()
        if time_range <= 0:
            return

        pixels_per_second = (rect.width() * self.zoom_level) / time_range

        # Draw time grid
        self.paint_time_grid(painter, rect, pixels_per_second)

        # Draw events
        self.paint_events(painter, rect, pixels_per_second)

        # Draw current position
        if self.current_position:
            self.paint_current_position(painter, rect, pixels_per_second)

    def paint_time_grid(self, painter: QPainter, rect: QRect, pixels_per_second: float):
        """Paint time grid lines and labels"""
        painter.setPen(QPen(QColor('#34495E'), 1))

        # Calculate grid interval (try for ~100px spacing)
        target_spacing = 100
        seconds_per_grid = target_spacing / pixels_per_second

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

    def paint_events(self, painter: QPainter, rect: QRect, pixels_per_second: float):
        """Paint events on timeline"""
        # logging.info(f"TimelineWidget: paint_events called with {len(self.events)} total events")
        # logging.info(f"TimelineWidget: View range for painting: {self.view_start_time} to {self.view_end_time}")

        layer_height = 25
        max_layers = rect.height() // layer_height

        # Group events by layer to prevent overlap
        layers = [[] for _ in range(max_layers)]

        visible_events = 0
        for event in self.events:
            # Check if event is visible in current view
            event_visible = (event.start_time <= self.view_end_time and event.end_time >= self.view_start_time)
            if event_visible:
                visible_events += 1
                # logging.info(f"TimelineWidget: Event visible - {event.event_name}: {event.start_time} to {event.end_time}")

            # Find available layer
            layer = 0
            while layer < max_layers:
                if not self.event_overlaps_layer(event, layers[layer]):
                    layers[layer].append(event)
                    break
                layer += 1
            else:
                # All layers full, use first layer
                layers[0].append(event)
                layer = 0

        # logging.info(f"TimelineWidget: Total visible events: {visible_events} out of {len(self.events)} total")

        # Paint events by layer
        for layer_idx, layer_events in enumerate(layers):
            for event in layer_events:
                self.paint_event(painter, rect, event, layer_idx, layer_height, pixels_per_second)

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

    def paint_current_position(self, painter: QPainter, rect: QRect, pixels_per_second: float):
        """Paint current position marker"""
        if not self.current_position:
            return

        x = self.time_to_pixel(self.current_position, pixels_per_second, rect.left())

        if rect.left() <= x <= rect.right():
            painter.setPen(QPen(QColor('#FFFF00'), 4))  # Bright yellow, thicker
            painter.drawLine(int(x), rect.top(), int(x), rect.bottom())

            # Position indicator circle
            painter.setBrush(QBrush(QColor('#FFFF00')))  # Bright yellow
            painter.drawEllipse(int(x) - 6, rect.top() - 6, 12, 12)  # Larger circle

            # Large arrow pointing down above timeline area
            painter.setPen(QPen(QColor('#FFFF00'), 3))  # Bright yellow, thicker
            painter.setBrush(QBrush(QColor('#FFFF00')))  # Bright yellow
            arrow_size = 24  # Even larger arrow
            arrow_y = 15  # Higher above timeline area
            # Draw arrow triangle pointing down
            arrow_points = [
                QPoint(int(x), arrow_y),  # Top point
                QPoint(int(x) - arrow_size//2, arrow_y + arrow_size),  # Bottom left
                QPoint(int(x) + arrow_size//2, arrow_y + arrow_size)   # Bottom right
            ]
            painter.drawPolygon(arrow_points)

            # Draw vertical line from arrow to timeline
            painter.setPen(QPen(QColor('#FFFF00'), 3))  # Bright yellow, thicker
            painter.drawLine(int(x), arrow_y + arrow_size, int(x), rect.top())
        else:
            logging.info(f"TimelineWidget: Marker is outside visible area at x={x:.1f} (visible range: {rect.left()} to {rect.right()})")

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

    def utc_to_local(self, dt: datetime) -> datetime:
        """Convert UTC datetime to local timezone"""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        local_tz = datetime.now().astimezone().tzinfo
        return dt.astimezone(local_tz)

    def time_to_pixel(self, time: datetime, pixels_per_second: float, offset: int = 0) -> float:
        """Convert timestamp to pixel position"""
        if not self.view_start_time:
            return 0

        seconds = (time - self.view_start_time).total_seconds()
        return offset + seconds * pixels_per_second

    def pixel_to_time(self, x: float, pixels_per_second: float, offset: int = 0) -> datetime:
        """Convert pixel position to timestamp"""
        if not self.view_start_time:
            return datetime.now()

        seconds = (x - offset) / pixels_per_second
        return self.view_start_time + timedelta(seconds=seconds)

    def mousePressEvent(self, event):
        """Handle mouse press"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.handle_left_click(event)
        elif event.button() == Qt.MouseButton.RightButton:
            self.handle_right_click(event)

        super().mousePressEvent(event)

    def handle_left_click(self, event):
        """Handle left mouse click"""
        rect = self.rect()
        timeline_rect = QRect(0, 40, rect.width(), rect.height() - 60)

        if not timeline_rect.contains(event.position().toPoint()):
            return

        # Convert to time
        pixels_per_second = self.calculate_pixels_per_second(timeline_rect)
        click_time = self.pixel_to_time(event.position().x(), pixels_per_second, timeline_rect.left())

        # Handle event creation
        if self.creating_event:
            # Update end time during drag, but don't complete yet
            self.new_event_end = click_time
            self.update()  # Repaint to show updated marker
            return

        # Check for event at position
        clicked_event = self.get_event_at_position(event.position().toPoint(), timeline_rect, pixels_per_second)

        if clicked_event:
            # Start dragging
            self.selected_event = clicked_event
            self.dragging = True
            self.drag_start_pos = event.position().toPoint()

            # Determine drag handle
            start_x = self.time_to_pixel(clicked_event.start_time, pixels_per_second, timeline_rect.left())
            end_x = self.time_to_pixel(clicked_event.end_time, pixels_per_second, timeline_rect.left())

            mouse_x = event.position().x()
            if abs(mouse_x - start_x) < 10:
                self.drag_handle = 'start'
            elif abs(mouse_x - end_x) < 10:
                self.drag_handle = 'end'
            else:
                self.drag_handle = 'move'
        else:
            # Position click
            gps_coords = (None, None)  # TODO: Get GPS coords
            self.position_clicked.emit(click_time, gps_coords)

    def handle_right_click(self, event):
        """Handle right mouse click"""
        rect = self.rect()
        timeline_rect = QRect(0, 40, rect.width(), rect.height() - 60)

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
        elif self.creating_event:
            # Update end time during event creation
            rect = self.rect()
            timeline_rect = QRect(0, 40, rect.width(), rect.height() - 60)
            if timeline_rect.contains(event.position().toPoint()):
                pixels_per_second = self.calculate_pixels_per_second(timeline_rect)
                mouse_time = self.pixel_to_time(event.position().x(), pixels_per_second, timeline_rect.left())
                self.new_event_end = mouse_time
                self.update()  # Repaint to show updated marker
                
                # Sync to nearest image
                self.position_clicked.emit(mouse_time, (None, None))
        else:
            self.update_cursor(event)

        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Handle double click to edit event or complete event creation"""
        if event.button() == Qt.MouseButton.LeftButton:
            rect = self.rect()
            timeline_rect = QRect(0, 40, rect.width(), rect.height() - 60)

            if timeline_rect.contains(event.position().toPoint()):
                pixels_per_second = self.calculate_pixels_per_second(timeline_rect)
                click_time = self.pixel_to_time(event.position().x(), pixels_per_second, timeline_rect.left())

                # Handle event creation completion
                if self.creating_event:
                    self.new_event_end = click_time
                    self.complete_event_creation()
                    return

                # Find event at click position
                clicked_event = self.get_event_at_position(click_time, timeline_rect, pixels_per_second)
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
            self.update()

    def handle_drag(self, event):
        """Handle event dragging"""
        rect = self.rect()
        timeline_rect = QRect(0, 40, rect.width(), rect.height() - 60)
        pixels_per_second = self.calculate_pixels_per_second(timeline_rect)

        new_time = self.pixel_to_time(event.position().x(), pixels_per_second, timeline_rect.left())

        # Apply snapping
        new_time = self.snap_time_to_grid(new_time)

        # Update event
        changes = {}
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

        self.event_modified.emit(self.selected_event.event_id, changes)
        self.update()

        # Sync to nearest image
        self.position_clicked.emit(new_time, (None, None))

    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if self.dragging:
            self.dragging = False
            self.selected_event = None
            self.drag_handle = None

        super().mouseReleaseEvent(event)

    def update_cursor(self, event):
        """Update cursor based on position"""
        rect = self.rect()
        timeline_rect = QRect(0, 40, rect.width(), rect.height() - 60)

        if not timeline_rect.contains(event.position().toPoint()):
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        pixels_per_second = self.calculate_pixels_per_second(timeline_rect)
        event_at_pos = self.get_event_at_position(event.position().toPoint(), timeline_rect, pixels_per_second)

        if event_at_pos:
            start_x = self.time_to_pixel(event_at_pos.start_time, pixels_per_second, timeline_rect.left())
            end_x = self.time_to_pixel(event_at_pos.end_time, pixels_per_second, timeline_rect.left())

            mouse_x = event.position().x()
            if abs(mouse_x - start_x) < 10 or abs(mouse_x - end_x) < 10:
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            else:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)

    def calculate_pixels_per_second(self, timeline_rect: QRect) -> float:
        """Calculate pixels per second for current view"""
        if not self.view_start_time or not self.view_end_time:
            return 1.0

        time_range = (self.view_end_time - self.view_start_time).total_seconds()
        return (timeline_rect.width() * self.zoom_level) / time_range

    def get_event_at_position(self, pos: QPoint, timeline_rect: QRect, pixels_per_second: float) -> Optional[Event]:
        """Get event at mouse position"""
        layer_height = 25

        for event in self.events:
            start_x = self.time_to_pixel(event.start_time, pixels_per_second, timeline_rect.left())
            end_x = self.time_to_pixel(event.end_time, pixels_per_second, timeline_rect.left())

            # Clip to prevent overflow
            start_x = max(-2147483648, min(2147483647, start_x))
            end_x = max(-2147483648, min(2147483647, end_x))

            # Check each layer
            for layer in range(10):  # Max layers
                y = timeline_rect.top() + layer * layer_height
                event_rect = QRect(int(start_x), y, int(end_x - start_x), layer_height)

                if event_rect.contains(pos):
                    return event

        return None

    def snap_time_to_grid(self, timestamp: datetime) -> datetime:
        """Snap timestamp to grid"""
        grid_seconds = 1  # 1 second grid
        epoch = timestamp.timestamp()
        snapped = round(epoch / grid_seconds) * grid_seconds
        return datetime.fromtimestamp(snapped)

    def edit_event(self, event: Event):
        """Show event edit dialog"""
        # TODO: Implement event editor dialog
        pass

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
        else:
            logging.info(f"TimelineWidget: User cancelled deletion of event '{event.event_name}' (ID: {event.event_id})")

    def add_event_at_time(self, timestamp: datetime):
        """Add event at timestamp"""
        # TODO: Implement event creation
        pass

    def complete_event_creation(self):
        """Complete the creation of a new event"""
        if not self.creating_event or not self.new_event_start or not self.new_event_end or not self.new_event_name:
            return

        # Ensure start time is before end time
        if self.new_event_start >= self.new_event_end:
            self.new_event_end = self.new_event_start + timedelta(seconds=30)  # Default 30 seconds

        # Create new event
        from ..models.event_model import Event
        import uuid
        event_id = f"{self.new_event_name.replace(' ', '_')}_{self.new_event_start.strftime('%Y-%m-%dT%H:%M:%S')}"

        # Calculate chainage (TODO: implement GPS-based calculation)
        start_chainage = 0.0
        end_chainage = 0.0

        new_event = Event(
            event_id=event_id,
            event_name=self.new_event_name,
            start_time=self.new_event_start,
            end_time=self.new_event_end,
            start_chainage=start_chainage,
            end_chainage=end_chainage
        )

        logging.info(f"TimelineWidget: Created new event '{self.new_event_name}' (ID: {event_id}) from {self.new_event_start} to {self.new_event_end}")

        # Reset creation state
        self.creating_event = False
        self.new_event_start = None
        self.new_event_end = None
        self.new_event_name = ""

        # Emit signal to add the event
        self.event_created.emit(new_event)