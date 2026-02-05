"""
Event data model for GeoEvent application
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
import logging

from .event_config import is_event_length_exceeded
from app.security.sanitizer import InputSanitizer
from app.security.validator import InputValidator

@dataclass
class Event:
    """
    Road survey event data structure
    """
    event_id: str
    event_name: str
    start_time: datetime
    end_time: datetime
    start_chainage: float
    end_chainage: float
    start_lat: Optional[float] = None
    start_lon: Optional[float] = None
    end_lat: Optional[float] = None
    end_lon: Optional[float] = None
    file_id: str = ""
    color: str = "#95A5A6"  # Default gray
    layer: int = 0

    @property
    def duration_seconds(self) -> float:
        """Calculate event duration in seconds"""
        return (self.end_time - self.start_time).total_seconds()

    @property
    def length_meters(self) -> float:
        """Calculate event length in meters"""
        return self.end_chainage - self.start_chainage

    @property
    def is_length_exceeded(self) -> bool:
        """Check if event length exceeds maximum allowed"""
        return is_event_length_exceeded(self.event_name, self.length_meters)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'event_id': self.event_id,
            'event_name': self.event_name,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'start_chainage': self.start_chainage,
            'end_chainage': self.end_chainage,
            'start_lat': self.start_lat,
            'start_lon': self.start_lon,
            'end_lat': self.end_lat,
            'end_lon': self.end_lon,
            'file_id': self.file_id,
            'color': self.color,
            'layer': self.layer
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Event':
        """Create Event from dictionary with validation"""
        # Validate and sanitize event name
        event_name = data['event_name']
        name_validation = InputValidator.validate_event_name(event_name)
        if not name_validation.is_valid:
            logging.warning(f"Invalid event name: {name_validation.error_message}")
            event_name = InputSanitizer.sanitize_string(event_name, max_length=100)
        else:
            event_name = name_validation.sanitized_value
        
        # Validate coordinates if provided
        start_lat = data.get('start_lat')
        start_lon = data.get('start_lon')
        if start_lat is not None and start_lon is not None:
            coord_validation = InputValidator.validate_coordinates(start_lat, start_lon)
            if not coord_validation.is_valid:
                logging.warning(f"Invalid start coordinates: {coord_validation.error_message}")
                start_lat, start_lon = None, None
        
        end_lat = data.get('end_lat')
        end_lon = data.get('end_lon')
        if end_lat is not None and end_lon is not None:
            coord_validation = InputValidator.validate_coordinates(end_lat, end_lon)
            if not coord_validation.is_valid:
                logging.warning(f"Invalid end coordinates: {coord_validation.error_message}")
                end_lat, end_lon = None, None
        
        # Validate chainage
        start_chainage = data['start_chainage']
        end_chainage = data['end_chainage']
        chainage_validation = InputValidator.validate_chainage(start_chainage)
        if not chainage_validation.is_valid:
            logging.warning(f"Invalid start chainage: {chainage_validation.error_message}")
        chainage_validation = InputValidator.validate_chainage(end_chainage)
        if not chainage_validation.is_valid:
            logging.warning(f"Invalid end chainage: {chainage_validation.error_message}")
        
        # Parse and validate timestamps
        start_dt = datetime.fromisoformat(data['start_time'])
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        
        # Validate start timestamp
        timestamp_validation = InputValidator.validate_timestamp(start_dt)
        if not timestamp_validation.is_valid:
            logging.warning(f"Invalid start timestamp: {timestamp_validation.error_message}")
        
        end_dt = datetime.fromisoformat(data['end_time'])
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)
        
        # Validate end timestamp
        timestamp_validation = InputValidator.validate_timestamp(end_dt)
        if not timestamp_validation.is_valid:
            logging.warning(f"Invalid end timestamp: {timestamp_validation.error_message}")
        
        # Validate time range (end must be after start)
        if end_dt < start_dt:
            logging.warning(f"End time {end_dt} is before start time {start_dt}")
            # Swap if needed
            start_dt, end_dt = end_dt, start_dt
        
        return cls(
            event_id=data['event_id'],
            event_name=event_name,
            start_time=start_dt,
            end_time=end_dt,
            start_chainage=start_chainage,
            end_chainage=end_chainage,
            start_lat=start_lat,
            start_lon=start_lon,
            end_lat=end_lat,
            end_lon=end_lon,
            file_id=data.get('file_id', ''),
            color=data.get('color', '#95A5A6'),
            layer=data.get('layer', 0)
        )