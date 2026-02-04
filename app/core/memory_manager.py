"""
Memory Manager for GeoEvent application
Monitors memory usage and triggers cleanup when needed
"""

import psutil
import os
import logging
import threading
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, QMutex, QMutexLocker

from app.config import get_config

class MemoryManager(QThread):
    """
    Monitors system memory usage and emits warnings
    Thread-safe implementation with proper cleanup
    """

    memory_warning = pyqtSignal(int)  # percentage

    def __init__(self, check_interval: int = None):
        super().__init__()
        # Load configuration
        config = get_config()
        self.check_interval = check_interval if check_interval is not None else (config.memory.CHECK_INTERVAL_MS)
        self.warning_threshold = config.memory.WARNING_THRESHOLD_PERCENT
        self.critical_threshold = config.memory.CRITICAL_THRESHOLD_PERCENT
        self.log_memory_usage = True  # Always log for debugging
        
        self._running_lock = QMutex()
        self._running = True
        self._stop_event = threading.Event()
        
        logging.info(f"MemoryManager initialized with warning={self.warning_threshold}%, critical={self.critical_threshold}%")

    @property
    def running(self):
        """Thread-safe getter for running flag"""
        with QMutexLocker(self._running_lock):
            return self._running

    @running.setter
    def running(self, value):
        """Thread-safe setter for running flag"""
        with QMutexLocker(self._running_lock):
            self._running = value

    def run(self):
        """Monitor memory in background thread"""
        logging.info("MemoryManager thread started")
        
        while self.running:
            try:
                # Check stop event periodically
                if self._stop_event.wait(timeout=self.check_interval / 1000):
                    break

                memory = psutil.virtual_memory()
                usage_percent = memory.percent
                
                # Log memory usage if enabled
                if self.log_memory_usage:
                    logging.debug(f"Memory usage: {usage_percent:.1f}% ({memory.used / (1024**3):.2f}GB / {memory.total / (1024**3):.2f}GB)")

                # Emit warning if threshold exceeded
                if usage_percent > self.warning_threshold:
                    self.memory_warning.emit(int(usage_percent))

            except Exception as e:
                logging.error(f"Memory monitoring error: {e}", exc_info=True)
                # Don't crash on error, just log and continue

        logging.info("MemoryManager thread stopped cleanly")

    def stop(self):
        """Stop monitoring with proper cleanup"""
        logging.info("Stopping MemoryManager thread...")
        self.running = False
        self._stop_event.set()
        
        # Wait for thread to finish with timeout
        if not self.wait(5000):  # 5 second timeout
            logging.warning("MemoryManager thread did not stop gracefully, forcing termination")
            self.terminate()
            self.wait()  # Wait for termination to complete