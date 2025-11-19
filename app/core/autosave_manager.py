"""
AutoSave Manager for GeoEvent application
Handles automatic saving of application state
"""

import os
import json
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal, QTimer

class AutoSaveManager(QThread):
    """
    Manages automatic saving of application data
    """

    autosave_triggered = pyqtSignal(datetime)  # timestamp of save

    def __init__(self, interval_seconds: int = 300):  # 5 minutes default
        super().__init__()
        self.interval_seconds = interval_seconds
        self.running = True
        self.data_to_save = {}
        self.save_path = None

    def set_save_path(self, path: str):
        """Set the path for autosave file"""
        self.save_path = path

    def update_data(self, key: str, data):
        """Update data to be autosaved"""
        self.data_to_save[key] = data

    def schedule_save(self):
        """Schedule an immediate save"""
        if self.save_path:
            self._perform_save()

    def _perform_save(self):
        """Perform the actual save operation"""
        if not self.save_path or not self.data_to_save:
            return

        try:
            # Atomic write
            temp_path = self.save_path + ".tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self.data_to_save, f, indent=2, default=str)

            os.replace(temp_path, self.save_path)

            timestamp = datetime.now()
            self.autosave_triggered.emit(timestamp)

        except Exception as e:
            print(f"Autosave error: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def run(self):
        """Run autosave timer in background"""
        timer = QTimer()
        timer.timeout.connect(self._perform_save)
        timer.start(self.interval_seconds * 1000)  # Convert to milliseconds

        # Keep thread alive
        while self.running:
            self.sleep(1)

    def stop(self):
        """Stop autosave"""
        self.running = False
        self.wait()