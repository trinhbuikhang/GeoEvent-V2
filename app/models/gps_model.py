"""
GPS data model for GeoEvent application
Optimized with binary search for O(log n) interpolation
"""

import bisect
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple

@dataclass
class GPSPoint:
    """
    Individual GPS data point
    """
    timestamp: datetime
    latitude: float
    longitude: float
    chainage: float  # in meters
    speed: Optional[float] = None
    elevation: Optional[float] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'latitude': self.latitude,
            'longitude': self.longitude,
            'chainage': self.chainage,
            'speed': self.speed,
            'elevation': self.elevation
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'GPSPoint':
        """Create GPSPoint from dictionary"""
        dt = datetime.fromisoformat(data['timestamp'])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return cls(
            timestamp=dt,
            latitude=data['latitude'],
            longitude=data['longitude'],
            chainage=data['chainage'],
            speed=data.get('speed'),
            elevation=data.get('elevation')
        )

class GPSData:
    """
    Collection of GPS data points with caching and querying
    Optimized with binary search for O(log n) interpolation performance
    """

    def __init__(self):
        self.points: List[GPSPoint] = []
        self._sorted = False
        self._timestamp_index: List[datetime] = []  # Cached timestamp index for binary search

    def add_point(self, point: GPSPoint):
        """Add a GPS point to the collection"""
        self.points.append(point)
        self._sorted = False
        self._timestamp_index = []  # Invalidate cache

    def sort_by_time(self):
        """Sort points by timestamp and build index for binary search"""
        if not self._sorted:
            self.points.sort(key=lambda p: p.timestamp)
            self._sorted = True
            # Build timestamp index for O(log n) binary search
            self._timestamp_index = [p.timestamp for p in self.points]
            logging.debug(f"GPS data sorted: {len(self.points)} points indexed")

    def get_points_in_range(self, start_time: datetime, end_time: datetime) -> List[GPSPoint]:
        """Get GPS points within time range"""
        self.sort_by_time()
        return [p for p in self.points if start_time <= p.timestamp <= end_time]

    def _find_surrounding_points(self, timestamp: datetime) -> Tuple[Optional[GPSPoint], Optional[GPSPoint]]:
        """
        Find GPS points surrounding a timestamp using binary search - O(log n)
        
        Args:
            timestamp: Target timestamp to find surrounding points for
            
        Returns:
            Tuple of (before_point, after_point) where:
            - before_point: Latest point at or before timestamp (or None)
            - after_point: Earliest point after timestamp (or None)
            
        Performance: O(log n) using binary search instead of O(n) linear search
        """
        self.sort_by_time()
        
        if not self.points:
            return None, None
        
        # Binary search for insertion point - O(log n)
        idx = bisect.bisect_left(self._timestamp_index, timestamp)
        
        # Determine before and after points
        before = None
        after = None
        
        if idx > 0:
            # There's a point at or before timestamp
            # Check if exact match or need previous point
            if idx < len(self.points) and self._timestamp_index[idx] == timestamp:
                before = self.points[idx]
                after = self.points[idx + 1] if idx + 1 < len(self.points) else None
            else:
                before = self.points[idx - 1]
                after = self.points[idx] if idx < len(self.points) else None
        else:
            # timestamp is before all points
            after = self.points[0] if self.points else None
        
        return before, after

    def interpolate_position(self, timestamp: datetime) -> Optional[tuple[float, float]]:
        """
        Interpolate latitude/longitude for a given timestamp using binary search
        Returns (lat, lon) or None if cannot interpolate
        
        Performance: O(log n) with binary search (was O(n) with linear search)
        """
        # Use binary search to find surrounding points - O(log n)
        before, after = self._find_surrounding_points(timestamp)

        if before and after and before.timestamp != after.timestamp:
            # Interpolate between two points
            time_diff = (after.timestamp - before.timestamp).total_seconds()
            target_diff = (timestamp - before.timestamp).total_seconds()

            if time_diff > 0:
                ratio = target_diff / time_diff
                lat = before.latitude + (after.latitude - before.latitude) * ratio
                lon = before.longitude + (after.longitude - before.longitude) * ratio
                return (lat, lon)

        elif before:
            # Use the closest point before
            return (before.latitude, before.longitude)

        elif after:
            # Use the closest point after
            return (after.latitude, after.longitude)

        return None

    def interpolate_chainage(self, timestamp: datetime) -> Optional[float]:
        """
        Interpolate chainage for a given timestamp using binary search
        Returns chainage or None if cannot interpolate
        
        Performance: O(log n) with binary search (was O(n) with linear search)
        """
        # Use binary search to find surrounding points - O(log n)
        before, after = self._find_surrounding_points(timestamp)

        if before and after and before.timestamp != after.timestamp:
            # Interpolate between two points
            time_diff = (after.timestamp - before.timestamp).total_seconds()
            target_diff = (timestamp - before.timestamp).total_seconds()

            if time_diff > 0:
                ratio = target_diff / time_diff
                chainage = before.chainage + (after.chainage - before.chainage) * ratio
                return chainage

        elif before:
            # Use the closest point before
            return before.chainage

        elif after:
            # Use the closest point after
            return after.chainage

        return None

    def interpolate_chainage_by_position(self, latitude: float, longitude: float) -> Optional[float]:
        """
        Find chainage for a given latitude/longitude by finding the closest GPS point
        Returns chainage of the closest point or None if no points available
        """
        if not self.points:
            return None

        # Find the closest point by Euclidean distance (simple approximation)
        closest_point = None
        min_distance = float('inf')

        for point in self.points:
            # Simple Euclidean distance (not great circle, but sufficient for close points)
            distance = ((point.latitude - latitude) ** 2 + (point.longitude - longitude) ** 2) ** 0.5
            if distance < min_distance:
                min_distance = distance
                closest_point = point

        if closest_point:
            return closest_point.chainage

        return None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'points': [p.to_dict() for p in self.points]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'GPSData':
        """Create GPSData from dictionary"""
        gps_data = cls()
        for point_data in data.get('points', []):
            gps_data.add_point(GPSPoint.from_dict(point_data))
        return gps_data