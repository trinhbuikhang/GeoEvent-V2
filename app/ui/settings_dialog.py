"""
Settings Dialog for GeoEvent Application
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QCheckBox,
    QPushButton, QLabel, QGroupBox, QSpinBox, QComboBox
)
from PyQt6.QtCore import Qt

class SettingsDialog(QDialog):
    """
    Dialog for application settings
    """

    def __init__(self, parent=None, settings_manager=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(400, 300)

        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)

        # Auto-save group
        autosave_group = QGroupBox("Auto-Save")
        autosave_layout = QVBoxLayout(autosave_group)

        self.auto_save_navigation_cb = QCheckBox("Auto-save when switching FileID folders")
        self.auto_save_navigation_cb.setToolTip(
            "Automatically save events and lane fixes when switching to another FileID folder.\n"
            "Only saves the current folder's changes, does not affect other folders."
        )
        autosave_layout.addWidget(self.auto_save_navigation_cb)

        layout.addWidget(autosave_group)

        # Lane assignment group
        lane_group = QGroupBox("Lane Assignment")
        lane_layout = QVBoxLayout(lane_group)

        lane_layout.addWidget(QLabel("Lane assignment mode:"))
        self.lane_mode_combo = QComboBox()
        self.lane_mode_combo.addItems(["strict", "permissive"])
        self.lane_mode_combo.setToolTip(
            "Strict: Only assign lanes to images within lane change periods\n"
            "Permissive: Assign lanes to all images, using the most recent lane change"
        )
        lane_layout.addWidget(self.lane_mode_combo)

        layout.addWidget(lane_group)

        # Timeline display group
        timeline_group = QGroupBox("Timeline")
        timeline_layout = QVBoxLayout(timeline_group)

        self.timeline_event_popup_cb = QCheckBox("Highlight event name when marker passes through event")
        self.timeline_event_popup_cb.setToolTip(
            "When the yellow position marker moves through an event on the timeline, show a pop-up label with the event name.\n"
            "Useful for short events where the colored bar is hard to see."
        )
        timeline_layout.addWidget(self.timeline_event_popup_cb)

        layout.addWidget(timeline_group)

        # Performance group
        perf_group = QGroupBox("Performance")
        perf_layout = QVBoxLayout(perf_group)

        perf_layout.addWidget(QLabel("Image cache size (MB):"))
        self.cache_size_spin = QSpinBox()
        self.cache_size_spin.setRange(100, 2000)
        self.cache_size_spin.setSingleStep(100)
        perf_layout.addWidget(self.cache_size_spin)

        perf_layout.addWidget(QLabel("Timeline default zoom level:"))
        self.timeline_zoom_spin = QSpinBox()
        self.timeline_zoom_spin.setRange(1, 50)
        perf_layout.addWidget(self.timeline_zoom_spin)

        layout.addWidget(perf_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(self.reset_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_settings)
        self.save_btn.setDefault(True)
        button_layout.addWidget(self.save_btn)

        layout.addLayout(button_layout)

    def load_settings(self):
        """Load current settings into UI"""
        if not self.settings_manager:
            return

        settings = self.settings_manager.load_settings()

        self.auto_save_navigation_cb.setChecked(
            settings.get('auto_save_on_navigation', False)
        )
        self.lane_mode_combo.setCurrentText(
            settings.get('lane_assignment_mode', 'strict')
        )
        self.cache_size_spin.setValue(
            settings.get('image_cache_size', 500)
        )
        self.timeline_zoom_spin.setValue(
            settings.get('timeline_zoom_default', 10)
        )
        self.timeline_event_popup_cb.setChecked(
            settings.get('timeline_event_popup', True)
        )

    def save_settings(self):
        """Save settings from UI"""
        if not self.settings_manager:
            self.reject()
            return

        new_settings = {
            'auto_save_on_navigation': self.auto_save_navigation_cb.isChecked(),
            'lane_assignment_mode': self.lane_mode_combo.currentText(),
            'timeline_event_popup': self.timeline_event_popup_cb.isChecked(),
            'image_cache_size': self.cache_size_spin.value(),
            'timeline_zoom_default': self.timeline_zoom_spin.value()
        }

        self.settings_manager.save_settings(new_settings)
        self.accept()

    def reset_to_defaults(self):
        """Reset settings to defaults"""
        if not self.settings_manager:
            return

        self.settings_manager.reset_to_defaults()
        self.load_settings()