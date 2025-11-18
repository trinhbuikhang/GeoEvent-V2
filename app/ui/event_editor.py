"""
Event Editor Dialog - Dialog for editing road events
"""

from datetime import datetime, timezone
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QDateTimeEdit, QMessageBox
)
from PyQt6.QtCore import Qt

from ..models.event_model import Event
from ..utils.settings_manager import SettingsManager

class EventEditor(QDialog):
    """
    Simple dialog for selecting/editing event name only
    """

    def __init__(self, event: Event = None, parent=None):
        super().__init__(parent)
        self.settings_manager = SettingsManager()
        self.event = event or Event(
            event_id="",
            event_name="",
            start_time=datetime.now(),
            end_time=datetime.now(),
            start_chainage=0.0,
            end_chainage=0.0
        )

        self.setup_ui()
        self.load_event_data()

    def setup_ui(self):
        """Setup simple UI with only event name"""
        self.setWindowTitle("Add Event")
        self.setModal(True)
        self.resize(300, 100)

        layout = QVBoxLayout(self)

        # Event name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Event Name:"))
        self.name_combo = QComboBox()
        self.name_combo.setEditable(True)
        event_names = self.settings_manager.get_setting('event_names', [])
        self.name_combo.addItems(event_names)
        name_layout.addWidget(self.name_combo)
        layout.addLayout(name_layout)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.save_btn = QPushButton("OK")
        self.save_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def load_event_data(self):
        """Load event data into form"""
        self.name_combo.setCurrentText(self.event.event_name)
        
        # If no event name is set, select the first item in the dropdown
        if not self.event.event_name and self.name_combo.count() > 0:
            self.name_combo.setCurrentIndex(0)

    def get_event_data(self) -> Event:
        """Get event data from form"""
        try:
            event_name = self.name_combo.currentText()
            start_time = self.start_time_edit.dateTime().toPyDateTime().replace(tzinfo=timezone.utc)
            end_time = self.end_time_edit.dateTime().toPyDateTime().replace(tzinfo=timezone.utc)
            start_chainage = float(self.start_chainage_edit.text())
            end_chainage = float(self.end_chainage_edit.text())

            # Validation
            if start_time >= end_time:
                raise ValueError("Start time must be before end time")

            if start_chainage >= end_chainage:
                raise ValueError("Start chainage must be less than end chainage")

            # Add new event name to settings if not exists
            event_names = self.settings_manager.get_setting('event_names', [])
            if event_name not in event_names:
                event_names.append(event_name)
                self.settings_manager.save_setting('event_names', event_names)

            # Update event
            self.event.event_name = event_name
            self.event.start_time = start_time
            self.event.end_time = end_time
            self.event.start_chainage = start_chainage
            self.event.end_chainage = end_chainage

            return self.event

        except ValueError as e:
            QMessageBox.warning(self, "Invalid Data", str(e))
            return None

    @staticmethod
    def edit_event(event: Event, parent=None) -> Event:
        """Static method to edit an event"""
        dialog = EventEditor(event, parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_event_data()
        return None