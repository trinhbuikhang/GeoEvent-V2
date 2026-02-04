"""
Input Sanitization for GeoEvent Application
Prevents injection attacks and malicious input
"""

import html
import re
import os
import logging
from typing import Optional


class InputSanitizer:
    """
    Sanitizes user input to prevent security vulnerabilities
    """
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """
        Sanitize string input
        
        Args:
            value: Input string to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
            
        Raises:
            TypeError: If input is not a string
            ValueError: If input is empty after sanitization
        """
        if not isinstance(value, str):
            raise TypeError(f"Input must be string, got {type(value)}")
        
        # Truncate to max length
        value = value[:max_length]
        
        # Remove control characters except newline and tab
        value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', value)
        
        # HTML escape to prevent XSS
        value = html.escape(value)
        
        # Strip leading/trailing whitespace
        value = value.strip()
        
        if not value:
            raise ValueError("Input is empty after sanitization")
        
        return value
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent path traversal attacks
        
        Args:
            filename: Input filename to sanitize
            
        Returns:
            Sanitized filename
            
        Raises:
            ValueError: If filename is invalid
        """
        if not filename or not isinstance(filename, str):
            raise ValueError("Filename must be non-empty string")
        
        # Remove path separators
        filename = re.sub(r'[/\\]', '', filename)
        
        # Remove dangerous characters
        filename = re.sub(r'[<>:"|?*\x00-\x1f]', '_', filename)
        
        # Allow only safe characters
        filename = re.sub(r'[^a-zA-Z0-9._\-]', '_', filename)
        
        # Prevent hidden files
        if filename.startswith('.'):
            filename = '_' + filename[1:]
        
        # Check length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:250] + ext
        
        if not filename or filename in ['.', '..']:
            raise ValueError(f"Invalid filename: {filename}")
        
        return filename
    
    @staticmethod
    def sanitize_filepath(filepath: str) -> str:
        """
        Sanitize file path to prevent path traversal
        
        Args:
            filepath: Input file path to sanitize
            
        Returns:
            Sanitized and normalized file path, or empty string if invalid
        """
        if not filepath or not isinstance(filepath, str):
            return ""
        
        # Normalize path
        filepath = os.path.normpath(filepath)
        
        # Check for path traversal attempts
        if '..' in filepath.split(os.sep):
            logging.warning(f"Path traversal detected: {filepath}")
            return ""
        
        # Check for absolute paths starting with dangerous locations
        if os.path.isabs(filepath):
            dangerous_roots = ['/', '\\', 'C:\\Windows', 'C:\\Program Files']
            for root in dangerous_roots:
                if filepath.startswith(root) and len(filepath) == len(root):
                    logging.warning(f"Access to system directory denied: {filepath}")
                    return ""
        
        # Remove null bytes
        filepath = filepath.replace('\x00', '')
        
        return filepath
    
    @staticmethod
    def sanitize_csv_value(value: str) -> str:
        """
        Sanitize CSV cell value to prevent CSV injection
        
        Args:
            value: CSV cell value
            
        Returns:
            Sanitized value
        """
        if not isinstance(value, str):
            value = str(value)
        
        # Check for CSV injection patterns
        dangerous_prefixes = ['=', '+', '-', '@', '\t', '\r']
        
        if value and value[0] in dangerous_prefixes:
            # Prepend single quote to neutralize
            value = "'" + value
        
        # Escape special characters
        value = value.replace('"', '""')
        
        return value
    
    @staticmethod
    def sanitize_plate(plate: str) -> str:
        """
        Sanitize vehicle plate number
        
        Args:
            plate: Plate number
            
        Returns:
            Sanitized plate (uppercase, alphanumeric only)
            
        Raises:
            ValueError: If plate format is invalid
        """
        if not plate or not isinstance(plate, str):
            raise ValueError("Plate must be non-empty string")
        
        # Convert to uppercase
        plate = plate.upper()
        
        # Remove non-alphanumeric characters
        plate = re.sub(r'[^A-Z0-9]', '', plate)
        
        # Validate length (typically 6 characters)
        if not (3 <= len(plate) <= 10):
            raise ValueError(f"Invalid plate length: {len(plate)}")
        
        return plate
    
    @staticmethod
    def sanitize_lane_code(lane_code: str) -> str:
        """
        Sanitize lane code
        
        Args:
            lane_code: Lane code (e.g., '1', 'TK1', 'SK2')
            
        Returns:
            Sanitized lane code
            
        Raises:
            ValueError: If lane code format is invalid
        """
        if not isinstance(lane_code, str):
            raise TypeError("Lane code must be string")
        
        # Remove whitespace
        lane_code = lane_code.strip().upper()
        
        # Allow only alphanumeric and hyphen
        if not re.match(r'^[A-Z0-9\-]+$', lane_code):
            raise ValueError(f"Invalid lane code format: {lane_code}")
        
        # Check max length
        if len(lane_code) > 10:
            raise ValueError(f"Lane code too long: {lane_code}")
        
        return lane_code
