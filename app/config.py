"""
Centralized Configuration for GeoEvent Application
All application constants and settings in one place
"""

from dataclasses import dataclass, field
from typing import Dict, Any
import json
import logging
import os


@dataclass
class TimelineConfig:
    """Timeline widget configuration"""
    LAYER_HEIGHT: int = 25
    TOP_MARGIN: int = 40
    CONTROLS_HEIGHT: int = 60
    CHAINAGE_SCALE_HEIGHT: int = 30
    HANDLE_SNAP_DISTANCE: int = 20
    DEFAULT_EVENT_DURATION: int = 30  # seconds
    GRID_SNAP_SECONDS: int = 1
    INT32_MIN: int = -2147483648
    INT32_MAX: int = 2147483647
    MAX_TIMEDELTA_SECONDS: int = 999999999


@dataclass
class MemoryConfig:
    """Memory management configuration"""
    WARNING_THRESHOLD_PERCENT: int = 70
    CRITICAL_THRESHOLD_PERCENT: int = 85
    CHECK_INTERVAL_MS: int = 5000  # milliseconds
    RETRY_INTERVAL_SEC: int = 10


@dataclass
class CacheConfig:
    """Image cache configuration"""
    DEFAULT_SIZE_MB: int = 500
    MAX_AGE_SECONDS: int = 300
    EMERGENCY_CLEANUP_PERCENT: int = 50
    PRELOAD_BATCH_SIZE: int = 50


@dataclass
class ValidationConfig:
    """Input validation configuration"""
    MAX_STRING_LENGTH: int = 1000
    MAX_FILENAME_LENGTH: int = 255
    PLATE_PATTERN: str = r'^[A-Z0-9]{6}$'
    VALID_LANE_CODES: set = None
    
    def __post_init__(self):
        if self.VALID_LANE_CODES is None:
            self.VALID_LANE_CODES = {
                '1', '2', '3', '4', 
                'TK1', 'TK2', 'TK3', 'TK4',
                'TM1', 'TM2', 'TM3', 'TM4',
                'SK', 'SK1', 'SK2', 'SK3', 'SK4',
                '-1', ''
            }


@dataclass
class FileConfig:
    """File handling configuration"""
    CSV_ENCODING: str = 'utf-8'
    CSV_ERRORS: str = 'replace'
    BACKUP_EXTENSION: str = '.backup'
    MAX_FILE_SIZE_MB: int = 100


@dataclass
class ImageConfig:
    """Image processing configuration"""
    SUPPORTED_FORMATS: tuple = ('.jpg', '.jpeg', '.png')
    THUMBNAIL_SIZE: tuple = (200, 150)
    THUMBNAIL_QUALITY: int = 85
    LAZY_LOAD_BATCH_SIZE: int = 100
    MAX_IMAGE_SIZE_MB: int = 10


@dataclass
class GPSConfig:
    """GPS data configuration"""
    MIN_LATITUDE: float = -90.0
    MAX_LATITUDE: float = 90.0
    MIN_LONGITUDE: float = -180.0
    MAX_LONGITUDE: float = 180.0
    MAX_CHAINAGE_KM: float = 10000.0  # 10,000 km
    MAX_TIME_GAP_SECONDS: int = 3600
    MIN_YEAR: int = 2000
    MAX_YEAR: int = 2100


@dataclass
class AppConfig:
    """Main application configuration"""
    timeline: TimelineConfig = field(default_factory=TimelineConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    file: FileConfig = field(default_factory=FileConfig)
    image: ImageConfig = field(default_factory=ImageConfig)
    gps: GPSConfig = field(default_factory=GPSConfig)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'AppConfig':
        """
        Load configuration from JSON file
        
        Args:
            filepath: Path to JSON config file
            
        Returns:
            AppConfig instance with loaded values
        """
        if not os.path.exists(filepath):
            return cls()  # Return defaults
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            config = cls()
            
            # Update timeline config
            if 'timeline' in data:
                for key, value in data['timeline'].items():
                    if hasattr(config.timeline, key):
                        setattr(config.timeline, key, value)
            
            # Update memory config
            if 'memory' in data:
                for key, value in data['memory'].items():
                    if hasattr(config.memory, key):
                        setattr(config.memory, key, value)
            
            # Update cache config
            if 'cache' in data:
                for key, value in data['cache'].items():
                    if hasattr(config.cache, key):
                        setattr(config.cache, key, value)
            
            # Update validation config
            if 'validation' in data:
                for key, value in data['validation'].items():
                    if hasattr(config.validation, key):
                        if key == 'VALID_LANE_CODES':
                            setattr(config.validation, key, set(value))
                        else:
                            setattr(config.validation, key, value)
            
            return config
            
        except Exception as e:
            logging.error(f"Error loading config from {filepath}: {e}", exc_info=True)
            return cls()  # Return defaults on error
    
    def save_to_file(self, filepath: str) -> bool:
        """
        Save configuration to JSON file
        
        Args:
            filepath: Path to JSON config file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            data = {
                'timeline': {
                    'LAYER_HEIGHT': self.timeline.LAYER_HEIGHT,
                    'TOP_MARGIN': self.timeline.TOP_MARGIN,
                    'CONTROLS_HEIGHT': self.timeline.CONTROLS_HEIGHT,
                    'CHAINAGE_SCALE_HEIGHT': self.timeline.CHAINAGE_SCALE_HEIGHT,
                    'HANDLE_SNAP_DISTANCE': self.timeline.HANDLE_SNAP_DISTANCE,
                    'DEFAULT_EVENT_DURATION': self.timeline.DEFAULT_EVENT_DURATION,
                    'GRID_SNAP_SECONDS': self.timeline.GRID_SNAP_SECONDS,
                },
                'memory': {
                    'WARNING_THRESHOLD_PERCENT': self.memory.WARNING_THRESHOLD_PERCENT,
                    'CRITICAL_THRESHOLD_PERCENT': self.memory.CRITICAL_THRESHOLD_PERCENT,
                    'CHECK_INTERVAL_MS': self.memory.CHECK_INTERVAL_MS,
                },
                'cache': {
                    'DEFAULT_SIZE_MB': self.cache.DEFAULT_SIZE_MB,
                    'MAX_AGE_SECONDS': self.cache.MAX_AGE_SECONDS,
                    'EMERGENCY_CLEANUP_PERCENT': self.cache.EMERGENCY_CLEANUP_PERCENT,
                },
                'validation': {
                    'MAX_STRING_LENGTH': self.validation.MAX_STRING_LENGTH,
                    'MAX_FILENAME_LENGTH': self.validation.MAX_FILENAME_LENGTH,
                    'PLATE_PATTERN': self.validation.PLATE_PATTERN,
                    'VALID_LANE_CODES': list(self.validation.VALID_LANE_CODES),
                }
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            return True
            
        except Exception as e:
            logging.error(f"Error saving config to {filepath}: {e}", exc_info=True)
            return False


# Global configuration instance
_config = None

def get_config() -> AppConfig:
    """Get global configuration instance"""
    global _config
    if _config is None:
        # Try to load from default location
        config_path = os.path.expanduser("~/.geoevent/config.json")
        _config = AppConfig.load_from_file(config_path)
    return _config

def set_config(config: AppConfig):
    """Set global configuration instance"""
    global _config
    _config = config
