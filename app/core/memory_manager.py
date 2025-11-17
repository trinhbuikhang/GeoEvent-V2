"""
Memory Manager for GeoEvent application
Monitors memory usage and triggers cleanup when needed
"""

import psutil
import os
from PyQt6.QtCore import QThread, pyqtSignal, QTimer

class MemoryManager(QThread):
    """
    Monitors system memory usage and emits warnings
    """

    memory_warning = pyqtSignal(int)  # percentage

    def __init__(self, check_interval: int = 5000):  # 5 seconds
        super().__init__()
        self.check_interval = check_interval
        self.running = True

    def run(self):
        """Monitor memory in background thread"""
        while self.running:
            try:
                memory = psutil.virtual_memory()
                usage_percent = memory.percent

                if usage_percent > 70:  # Warning threshold
                    self.memory_warning.emit(int(usage_percent))

                self.sleep(self.check_interval // 1000)  # Convert to seconds

            except Exception as e:
                print(f"Memory monitoring error: {e}")
                self.sleep(10)  # Retry after 10 seconds

    def stop(self):
        """Stop monitoring"""
        self.running = False
        self.wait()