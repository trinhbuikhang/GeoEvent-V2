"""
Enhanced Image Cache Manager for GeoEvent application
Implements LRU cache with size limits and memory monitoring
"""

import os
import logging
import psutil
from collections import OrderedDict
from typing import Dict, Optional, Tuple
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

class ImageCacheEntry:
    """Cache entry with metadata"""
    def __init__(self, pixmap: QPixmap, access_time: float, file_size: int):
        self.pixmap = pixmap
        self.access_time = access_time
        self.file_size = file_size
        self.memory_size = self._estimate_memory_size()

    def _estimate_memory_size(self) -> int:
        """Estimate memory usage of pixmap in bytes"""
        if self.pixmap.isNull():
            return 0
        # Rough estimate: width * height * 4 bytes per pixel (RGBA)
        return self.pixmap.width() * self.pixmap.height() * 4

    def update_access_time(self, access_time: float):
        """Update last access time"""
        self.access_time = access_time

class SmartImageCache(QObject):
    """
    Smart LRU image cache with size limits and memory monitoring
    """

    cache_cleared = pyqtSignal(int)  # emitted when cache is cleared (bytes freed)
    memory_warning = pyqtSignal(int)  # emitted when memory usage is high

    def __init__(self, max_cache_size_mb: int = 500, memory_threshold_percent: int = 75):
        super().__init__()
        self.max_cache_size_bytes = max_cache_size_mb * 1024 * 1024
        self.memory_threshold_percent = memory_threshold_percent

        # LRU cache: OrderedDict with key=image_path, value=ImageCacheEntry
        self.cache: OrderedDict[str, ImageCacheEntry] = OrderedDict()

        # Cache statistics
        self.total_memory_used = 0
        self.hits = 0
        self.misses = 0

        # Memory monitoring timer
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._check_memory_usage)
        self.monitor_timer.start(30000)  # Check every 30 seconds

        logging.info(f"SmartImageCache initialized with {max_cache_size_mb}MB limit")

    def get(self, image_path: str) -> Optional[QPixmap]:
        """Get image from cache, update access time"""
        if image_path in self.cache:
            entry = self.cache[image_path]
            entry.update_access_time(self._get_current_time())
            self.cache.move_to_end(image_path)  # Move to end (most recently used)
            self.hits += 1
            return entry.pixmap
        else:
            self.misses += 1
            return None

    def put(self, image_path: str, pixmap: QPixmap) -> bool:
        """Add image to cache, evict if necessary"""
        if pixmap.isNull():
            return False

        # Get file size for metadata
        file_size = os.path.getsize(image_path) if os.path.exists(image_path) else 0

        # Create cache entry
        entry = ImageCacheEntry(pixmap, self._get_current_time(), file_size)

        # Check if we need to evict before adding
        if image_path not in self.cache:
            self._ensure_capacity(entry.memory_size)

        # Add/update cache
        old_memory = 0
        if image_path in self.cache:
            old_memory = self.cache[image_path].memory_size

        self.cache[image_path] = entry
        self.cache.move_to_end(image_path)
        self.total_memory_used += (entry.memory_size - old_memory)

        return True

    def clear(self):
        """Clear entire cache"""
        bytes_freed = self.total_memory_used
        self.cache.clear()
        self.total_memory_used = 0
        self.hits = 0
        self.misses = 0
        self.cache_cleared.emit(bytes_freed)
        logging.info(f"Cache cleared, freed {bytes_freed / (1024*1024):.1f}MB")

    def remove_old_entries(self, max_age_seconds: int = 300):
        """Remove entries older than max_age_seconds"""
        current_time = self._get_current_time()
        to_remove = []

        for path, entry in self.cache.items():
            if current_time - entry.access_time > max_age_seconds:
                to_remove.append(path)

        bytes_freed = 0
        for path in to_remove:
            entry = self.cache[path]
            bytes_freed += entry.memory_size
            del self.cache[path]

        if to_remove:
            self.total_memory_used -= bytes_freed
            logging.info(f"Removed {len(to_remove)} old cache entries, freed {bytes_freed / (1024*1024):.1f}MB")

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            'total_entries': len(self.cache),
            'memory_used_mb': self.total_memory_used / (1024 * 1024),
            'max_memory_mb': self.max_cache_size_bytes / (1024 * 1024),
            'hit_rate': self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0,
            'hits': self.hits,
            'misses': self.misses
        }

    def _ensure_capacity(self, required_bytes: int):
        """Ensure there's enough capacity for required_bytes"""
        while self.total_memory_used + required_bytes > self.max_cache_size_bytes and self.cache:
            # Remove least recently used item
            path, entry = self.cache.popitem(last=False)  # FIFO - least recently used
            self.total_memory_used -= entry.memory_size
            logging.debug(f"Evicted {os.path.basename(path)} from cache")

    def _check_memory_usage(self):
        """Check system memory usage and emit warnings"""
        try:
            memory = psutil.virtual_memory()
            usage_percent = memory.percent

            if usage_percent > self.memory_threshold_percent:
                self.memory_warning.emit(int(usage_percent))
                # Aggressive cleanup when memory is high
                self._emergency_cleanup()

        except Exception as e:
            logging.error(f"Memory check failed: {e}")

    def _emergency_cleanup(self):
        """Emergency cleanup when memory is critically low"""
        # Clear 50% of cache by removing oldest entries
        target_entries = len(self.cache) // 2
        bytes_freed = 0

        for _ in range(target_entries):
            if not self.cache:
                break
            path, entry = self.cache.popitem(last=False)
            bytes_freed += entry.memory_size

        self.total_memory_used -= bytes_freed
        logging.warning(f"Emergency cleanup: removed {target_entries} entries, freed {bytes_freed / (1024*1024):.1f}MB")

    def _get_current_time(self) -> float:
        """Get current time for cache timing"""
        import time
        return time.time()

    def preload_images(self, image_paths: list, max_concurrent: int = 3):
        """Preload images in background (not implemented yet)"""
        # Future enhancement: background preloading
        pass