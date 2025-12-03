"""
Image utilities for GeoEvent application
Extract metadata from survey image filenames
"""

import re
import os
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

def extract_image_metadata(image_path: str) -> Dict:
    """
    Extract metadata from survey image filename
    Format: ProjectID-YYYY-MM-DD-HH-MM-SS-mmm-Lat-Lon-Bearing-Speed-Plate-FileID-Chainage-Distance-LE-.jpg

    Example: PRJ-2025-10-02-08-22-53-123-4351.7594S-17266.0813E-045-50-QJS289-0D2510020814007700-1171.65-100-LE-.jpg
    """
    filename = image_path.split('/')[-1].split('\\')[-1]  # Handle both separators

    metadata = {
        'filename': filename,
        'timestamp': None,
        'latitude': None,
        'longitude': None,
        'bearing': None,
        'speed': None,
        'plate': None,
        'fileid': None,
        'chainage': None,
        'distance': None
    }

    try:
        # Extract timestamp: YYYY-MM-DD-HH-MM-SS-mmm (milliseconds may be 1, 2 or 3 digits)
        timestamp_match = re.search(r'-(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{1,3})-', filename)
        if timestamp_match:
            timestamp_str = timestamp_match.group(1)
            # Convert YYYY-MM-DD-HH-MM-SS-mmm to datetime (handle 1, 2 or 3 digit milliseconds)
            parts = timestamp_str.split('-')
            ms_str = parts[-1]
            # Convert milliseconds to microseconds (pad to 6 digits)
            ms_value = int(ms_str)
            microseconds = ms_value * 1000  # Convert ms to μs
            parts[-1] = f'{microseconds:06d}'  # Format as 6-digit microseconds
            timestamp_str = '-'.join(parts)
            dt = datetime.strptime(timestamp_str, '%Y-%m-%d-%H-%M-%S-%f').replace(tzinfo=timezone.utc)
            metadata['timestamp'] = dt

        # Extract GPS coordinates
        coords = extract_coordinates(filename)
        if coords:
            metadata['latitude'] = coords[0]
            metadata['longitude'] = coords[1]

        # Extract bearing (number before --- after coordinates)
        bearing_match = re.search(r'-([0-9]+(?:\.[0-9]+)?)---', filename)
        if bearing_match:
            try:
                bearing = float(bearing_match.group(1))
                if 0 <= bearing <= 360:  # Valid bearing range
                    metadata['bearing'] = int(bearing)  # Store as integer
            except ValueError:
                pass

        # Extract speed
        speed_match = re.search(r'-(\d{1,3})-', filename)
        if speed_match and not metadata['bearing']:  # Avoid confusion with bearing
            try:
                speed = int(speed_match.group(1))
                if 0 <= speed <= 200:  # Reasonable speed range
                    metadata['speed'] = speed
            except ValueError:
                pass

        # Extract plate (6-character alphanumeric)
        plate_match = re.search(r'-([A-Z0-9]{6})-', filename)
        if plate_match:
            metadata['plate'] = plate_match.group(1)

        # Extract FileID
        fileid_match = re.search(r'-0D(\d{16,18})-', filename)
        if fileid_match:
            metadata['fileid'] = f"0D{fileid_match.group(1)}"

        # Extract chainage
        chainage_match = re.search(r'-(\d+\.\d{1,2})-', filename)
        if chainage_match:
            try:
                chainage = float(chainage_match.group(1))
                # Check if it's a reasonable chainage value
                if 0 <= chainage <= 100000:  # 0 to 100km
                    metadata['chainage'] = chainage
            except ValueError:
                pass

        # Extract distance (last number before -LE-)
        distance_match = re.search(r'-(\d+)-LE-', filename)
        if distance_match:
            try:
                metadata['distance'] = int(distance_match.group(1))
            except ValueError:
                pass

    except Exception as e:
        print(f"Error extracting metadata from {filename}: {e}")
        return metadata  # Return partial metadata

    return metadata

def extract_coordinates(filename: str) -> Optional[Tuple[float, float]]:
    """
    Extract latitude and longitude from filename
    Format: DDMM.MMMMM with direction N/S/E/W

    Example: 4351.7594S → -43.862657°
    """
    try:
        # Remove file extension
        filename_no_ext = os.path.splitext(filename)[0]
        parts = filename_no_ext.split('-')
        if len(parts) < 9:  # Need at least 9 parts for coordinates
            print(f"Filename {filename} has only {len(parts)} parts, expected >=9")
            return None
            
        lat_str, lon_str = parts[8], parts[9]
        if not lat_str or not lon_str or lat_str == '-' or lon_str == '-':
            print(f"Invalid lat/lon strings: {lat_str}, {lon_str} in {filename}")
            return None
            
        # Check if direction is present and valid
        if len(lat_str) < 2 or lat_str[-1].upper() not in 'NS':
            print(f"Invalid lat direction in {lat_str} for {filename}")
            return None
        if len(lon_str) < 2 or lon_str[-1].upper() not in 'EW':
            print(f"Invalid lon direction in {lon_str} for {filename}")
            return None
            
        # Parse DDMM.MMMMM format
        lat_coord = lat_str[:-1]  # Remove direction
        lat_dir = lat_str[-1].upper()
        if len(lat_coord) < 4:  # At least DDMM
            print(f"Lat coord too short: {lat_coord} for {filename}")
            return None
        lat_deg = int(lat_coord[:2])
        lat_min = float(lat_coord[2:])
        lat = lat_deg + (lat_min / 60)
        
        lon_coord = lon_str[:-1]  # Remove direction
        lon_dir = lon_str[-1].upper()
        if len(lon_coord) < 5:  # At least DDDMM
            print(f"Lon coord too short: {lon_coord} for {filename}")
            return None
        lon_deg = int(lon_coord[:3])
        lon_min = float(lon_coord[3:])
        lon = lon_deg + (lon_min / 60)
        
        if lat_dir == 'S':
            lat = -lat
        if lon_dir == 'W':
            lon = -lon
            
        # Validate coordinates are in reasonable ranges
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            print(f"Coordinates out of range: {lat}, {lon} for {filename}")
            return None
            
        return lat, lon
    except (ValueError, IndexError, TypeError) as e:
        print(f"Error parsing coordinates in {filename}: {e}")
        return None

def ddmm_to_decimal(ddmm: float, direction: str) -> float:
    """
    Convert DDMM.MMMM format to decimal degrees
    """
    degrees = int(ddmm / 100)
    minutes = ddmm % 100
    decimal = degrees + (minutes / 60)

    if direction in ['S', 'W']:
        decimal = -decimal

    return decimal

def extract_timestamp(filename: str) -> Optional[datetime]:
    """
    Extract timestamp from filename
    """
    match = re.search(r'(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{3})', filename)
    if match:
        try:
            return datetime.strptime(match.group(1), '%Y-%m-%d-%H-%M-%S-%f')
        except ValueError:
            pass
    return None

def extract_plate(filename: str) -> Optional[str]:
    """
    Extract 6-character alphanumeric plate
    """
    match = re.search(r'-([A-Z0-9]{6})-', filename)
    return match.group(1) if match else None

def extract_fileid(filename: str) -> Optional[str]:
    """
    Extract FileID from filename
    """
    match = re.search(r'-0D(\d{16,18})-', filename)
    return f"0D{match.group(1)}" if match else None

def validate_filename(filename: str) -> bool:
    """
    Validate if filename matches the expected survey image format
    Format: ProjectID-YYYY-MM-DD-HH-MM-SS-mmm-Lat-Lon-Bearing---Plate-FileID-Chainage-Distance-LE-.jpg

    Example: 250410.01-2025-10-01-19-37-03-304-4325.555329S-17238.975553E-22.9---QJS289-0D2510020820137700-5554013603272-16.64-LE-.jpg
    Example: 250041-2025-11-26-20-10-24-862-3730.680559S-17510.095384E-156.4---NWZ263-0D2511270910197800-2580493456456-28.95-LE-.jpg
    """
    try:
        # Remove file extension
        if not filename.lower().endswith('.jpg'):
            return False

        filename_no_ext = filename[:-4]  # Remove .jpg

        # Use regex to match the exact pattern - support both ProjectID formats:
        # - 6 digits + dot + 2 digits (e.g., 250410.01)
        # - 6 digits only (e.g., 250041)
        pattern = r'^(\d{6}(?:\.\d{2})?)-(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{1,3})-(\d+\.\d+[NS])-(\d+\.\d+[EW])-(\d+(?:\.\d+)?)---([A-Z0-9]{6})-([A-Z0-9]+)-(\d+)-(\d+(?:\.\d+)?)-LE-$'
        
        match = re.match(pattern, filename_no_ext)
        if not match:
            return False

        # Extract groups for validation
        groups = match.groups()
        
        # Validate date/time components
        year, month, day, hour, minute, second = map(int, groups[1:7])
        millisecond_str = groups[7]
        millisecond = int(millisecond_str)
        
        if not (2020 <= year <= 2100):
            return False
        if not (1 <= month <= 12):
            return False
        if not (1 <= day <= 31):
            return False
        if not (0 <= hour <= 23):
            return False
        if not (0 <= minute <= 59):
            return False
        if not (0 <= second <= 59):
            return False
        if not (0 <= millisecond <= 999):
            return False

        # Validate bearing (0-360)
        bearing = float(groups[10])
        if not (0 <= bearing <= 360):
            return False

        # Validate chainage (numeric)
        try:
            int(groups[13])
        except ValueError:
            return False

        # Validate distance (numeric)
        try:
            float(groups[14])
        except ValueError:
            return False

        return True

    except Exception as e:
        return False