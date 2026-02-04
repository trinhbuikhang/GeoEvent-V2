"""
Input Validation for GeoEvent Application
Validates data integrity and format
"""

import re
from datetime import datetime
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of validation with error message if invalid"""
    is_valid: bool
    error_message: Optional[str] = None
    sanitized_value: any = None
    
    def __bool__(self):
        return self.is_valid


class InputValidator:
    """
    Validates input data for GeoEvent application
    """
    
    # Regex patterns
    PLATE_PATTERN = re.compile(r'^[A-Z0-9\-\s]{2,20}$')  # Support Vietnamese plates with dashes/spaces
    LANE_CODE_PATTERN = re.compile(r'^([1-4]|TK[1-4]|TM[1-4]|SK[1-4]?|-1|)$')
    FILEID_PATTERN = re.compile(r'^0D[A-Za-z0-9]{14,16}$')
    
    @staticmethod
    def validate_plate(plate: str) -> ValidationResult:
        """
        Validate vehicle plate format
        
        Args:
            plate: Plate number to validate
            
        Returns:
            ValidationResult with status, error message, and sanitized value
        """
        if not plate or not isinstance(plate, str):
            return ValidationResult(False, "Plate must be non-empty string")
        
        # Sanitize and normalize
        from app.security.sanitizer import InputSanitizer
        sanitized = InputSanitizer.sanitize_plate(plate)
        
        if not sanitized:
            return ValidationResult(False, "Plate empty after sanitization")
        
        if not InputValidator.PLATE_PATTERN.match(sanitized):
            return ValidationResult(
                False, 
                f"Invalid plate format: {sanitized} (expected 2-20 alphanumeric characters with dashes/spaces)"
            )
        
        return ValidationResult(True, sanitized_value=sanitized)
    
    @staticmethod
    def validate_lane_code(lane_code: str) -> ValidationResult:
        """
        Validate lane code format
        
        Args:
            lane_code: Lane code to validate
            
        Returns:
            ValidationResult with status, error message, and sanitized value
        """
        if not isinstance(lane_code, str):
            return ValidationResult(False, "Lane code must be a string")
        
        # Sanitize
        from app.security.sanitizer import InputSanitizer
        sanitized = InputSanitizer.sanitize_lane_code(lane_code)
        
        if not InputValidator.LANE_CODE_PATTERN.match(sanitized):
            return ValidationResult(
                False,
                f"Invalid lane code: {sanitized}"
            )
        
        return ValidationResult(True, sanitized_value=sanitized)
    
    @staticmethod
    def validate_timestamp(timestamp: datetime) -> ValidationResult:
        """
        Validate timestamp is reasonable
        
        Args:
            timestamp: Datetime to validate
            
        Returns:
            ValidationResult with status and error message
        """
        if not isinstance(timestamp, datetime):
            return ValidationResult(False, f"Timestamp must be datetime, got {type(timestamp)}")
        
        # Check year range (2000-2100)
        if not (2000 <= timestamp.year <= 2100):
            return ValidationResult(
                False,
                f"Timestamp year out of range: {timestamp.year} (expected 2000-2100)"
            )
        
        # Check if timestamp is in the future (with 1 day tolerance)
        now = datetime.now(timestamp.tzinfo)
        if timestamp > now:
            days_future = (timestamp - now).days
            if days_future > 1:
                return ValidationResult(
                    False,
                    f"Timestamp is {days_future} days in the future"
                )
        
        return ValidationResult(True)
    
    @staticmethod
    def validate_coordinates(latitude: float, longitude: float) -> ValidationResult:
        """
        Validate GPS coordinates
        
        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            
        Returns:
            ValidationResult with status and error message
        """
        try:
            lat = float(latitude)
            lon = float(longitude)
        except (TypeError, ValueError) as e:
            return ValidationResult(False, f"Coordinates must be numeric: {e}")
        
        if not (-90 <= lat <= 90):
            return ValidationResult(
                False,
                f"Latitude out of range: {lat} (expected -90 to 90)"
            )
        
        if not (-180 <= lon <= 180):
            return ValidationResult(
                False,
                f"Longitude out of range: {lon} (expected -180 to 180)"
            )
        
        return ValidationResult(True)
    
    @staticmethod
    def validate_chainage(chainage: float, max_km: float = 10000.0) -> ValidationResult:
        """
        Validate chainage value
        
        Args:
            chainage: Chainage in meters
            max_km: Maximum allowed chainage in kilometers
            
        Returns:
            ValidationResult with status and error message
        """
        try:
            ch = float(chainage)
        except (TypeError, ValueError) as e:
            return ValidationResult(False, f"Chainage must be numeric: {e}")
        
        max_meters = max_km * 1000
        
        if ch < 0:
            return ValidationResult(False, f"Chainage cannot be negative: {ch}")
        
        if ch > max_meters:
            return ValidationResult(
                False,
                f"Chainage exceeds maximum: {ch}m (max: {max_meters}m = {max_km}km)"
            )
        
        return ValidationResult(True)
    
    @staticmethod
    def validate_fileid(fileid: str) -> ValidationResult:
        """
        Validate FileID format
        
        Args:
            fileid: FileID string to validate
            
        Returns:
            ValidationResult with status and error message
        """
        if not fileid or not isinstance(fileid, str):
            return ValidationResult(False, "FileID must be non-empty string")
        
        if not InputValidator.FILEID_PATTERN.match(fileid):
            return ValidationResult(
                False,
                f"Invalid FileID format: {fileid} (expected: 0D + 14-16 alphanumeric)"
            )
        
        return ValidationResult(True)
    
    @staticmethod
    def validate_event_name(name: str, max_length: int = 100) -> ValidationResult:
        """
        Validate event name
        
        Args:
            name: Event name to validate
            max_length: Maximum allowed length
            
        Returns:
            ValidationResult with status, error message, and sanitized value
        """
        if not name or not isinstance(name, str):
            return ValidationResult(False, "Event name must be non-empty string")
        
        # Sanitize first
        from app.security.sanitizer import InputSanitizer
        sanitized = InputSanitizer.sanitize_string(name, max_length=max_length)
        
        if len(sanitized) > max_length:
            return ValidationResult(
                False,
                f"Event name too long: {len(sanitized)} (max: {max_length})"
            )
        
        # Check for dangerous characters (after sanitization should be clean)
        if not sanitized:
            return ValidationResult(False, "Event name empty after sanitization")
        
        return ValidationResult(True, sanitized_value=sanitized)
    
    @staticmethod
    def validate_filepath(filepath: str) -> ValidationResult:
        """
        Validate file path for security
        
        Args:
            filepath: File path to validate
            
        Returns:
            ValidationResult with status and error message
        """
        if not filepath or not isinstance(filepath, str):
            return ValidationResult(False, "Filepath must be non-empty string")
        
        # Check for path traversal
        if '..' in filepath:
            return ValidationResult(False, "Path traversal detected in filepath")
        
        # Check for null bytes
        if '\x00' in filepath:
            return ValidationResult(False, "Null byte detected in filepath")
        
        # Check length
        if len(filepath) > 4096:
            return ValidationResult(False, f"Filepath too long: {len(filepath)} (max: 4096)")
        
        return ValidationResult(True)
