"""
File parsers for GeoEvent application
Handles parsing of .driveevt and .driveiri files
"""

import csv
from datetime import datetime, timezone
from typing import List
import os

from ..models.event_model import Event
from ..models.gps_model import GPSData, GPSPoint

def parse_driveevt(file_path: str) -> List[Event]:
    """
    Parse .driveevt file and return list of events
    Matches Start/End event pairs to create complete events
    """
    events = []

    if not os.path.exists(file_path):
        return events

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            # Collect all start and end events
            start_events = []
            end_events = []

            for row in reader:
                if row.get('IsSpanEvent', '').lower() != 'true':
                    continue

                span_name = row.get('SpanEvent', '')
                is_start = row.get('IsSpanStartEvent', '').lower() == 'true'
                is_end = row.get('IsSpanEndEvent', '').lower() == 'true'

                if not span_name:
                    continue

                # Parse timestamp
                time_str = row.get('TimeUtc', '')
                try:
                    # MM/DD/YYYY HH:MM:SS format (UTC)
                    timestamp = datetime.strptime(time_str, '%m/%d/%Y %H:%M:%S').replace(tzinfo=timezone.utc)
                except ValueError:
                    print(f"Error parsing timestamp '{time_str}' for event {span_name}")
                    continue

                # Parse chainage (convert to float)
                try:
                    chainage = float(row.get('Chainage', '0'))
                except ValueError:
                    chainage = 0.0

                if is_start:
                    start_events.append({
                        'name': span_name,
                        'time': timestamp,
                        'chainage': chainage
                    })
                elif is_end:
                    end_events.append({
                        'name': span_name,
                        'time': timestamp,
                        'chainage': chainage
                    })

            # Sort events by time
            start_events.sort(key=lambda x: x['time'])
            end_events.sort(key=lambda x: x['time'])

            # Match start and end events by name and time proximity
            used_starts = set()
            used_ends = set()

            for i, start in enumerate(start_events):
                if i in used_starts:
                    continue

                best_end = None
                best_end_idx = -1

                for j, end in enumerate(end_events):
                    if j in used_ends or start['name'] != end['name']:
                        continue

                    if end['time'] >= start['time']:  # Allow equal time for instant events
                        if best_end is None or end['time'] < best_end['time']:
                            best_end = end
                            best_end_idx = j

                if best_end:
                    used_starts.add(i)
                    used_ends.add(best_end_idx)

                    event = Event(
                        event_id=f"{start['name']}_{start['time'].isoformat()}",
                        event_name=start['name'],
                        start_time=start['time'],
                        end_time=best_end['time'],
                        start_chainage=start['chainage'],
                        end_chainage=best_end['chainage'],
                        file_id=os.path.splitext(os.path.basename(file_path))[0]
                    )
                    events.append(event)

    except Exception as e:
        print(f"Error parsing {file_path}: {e}")

    return events

def parse_driveiri(file_path: str) -> GPSData:
    """
    Parse .driveiri file and return GPSData object
    """
    gps_data = GPSData()

    if not os.path.exists(file_path):
        return gps_data

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    # Parse timestamp: M/D/YYYY H:MM:SS AM/PM format
                    datetime_str = row.get('GPSDateTime', '')
                    if not datetime_str:
                        continue

                    # Handle AM/PM format (UTC)
                    timestamp = datetime.strptime(datetime_str, '%m/%d/%Y %I:%M:%S %p').replace(tzinfo=timezone.utc)

                    # Parse GPS coordinates
                    lat = float(row.get('Position (begin) (LAT)', '0'))
                    lon = float(row.get('Position (begin) (LON)', '0'))

                    # Parse chainage (convert km to meters)
                    start_chainage_km = float(row.get('StartChainage [km]', '0'))
                    start_chainage = start_chainage_km * 1000

                    # Optional fields
                    speed = None
                    try:
                        speed = float(row.get('AverageSpeed [km/h]', '0'))
                    except (ValueError, TypeError):
                        pass

                    elevation = None
                    try:
                        elevation = float(row.get('Elevation [m]', '0'))
                    except (ValueError, TypeError):
                        pass

                    # Create GPS point
                    point = GPSPoint(
                        timestamp=timestamp,
                        latitude=lat,
                        longitude=lon,
                        chainage=start_chainage,
                        speed=speed,
                        elevation=elevation
                    )

                    gps_data.add_point(point)

                except (ValueError, KeyError) as e:
                    # Skip invalid rows
                    continue

    except Exception as e:
        print(f"Error parsing {file_path}: {e}")

    return gps_data

def enrich_events_with_gps(events: List[Event], gps_data: GPSData):
    """
    Enrich events with GPS coordinates by matching timestamps
    """
    gps_data.sort_by_time()

    for event in events:
        # Get GPS position for start time
        start_pos = gps_data.interpolate_position(event.start_time)
        if start_pos:
            event.start_lat, event.start_lon = start_pos

        # Get GPS position for end time
        end_pos = gps_data.interpolate_position(event.end_time)
        if end_pos:
            event.end_lat, event.end_lon = end_pos