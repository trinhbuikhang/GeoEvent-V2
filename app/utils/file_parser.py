"""
File parsers for GeoEvent application
Handles parsing of .driveevt and .driveiri files
"""

import csv
from datetime import datetime, timezone, timedelta
from typing import List
import os
import pytz

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
    Uses Unix timestamp column for higher precision timing
    """
    gps_data = GPSData()

    if not os.path.exists(file_path):
        return gps_data

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    # Parse timestamp: Use Unix timestamp for higher precision
                    unix_timestamp_str = row.get('Unix', '')
                    if not unix_timestamp_str:
                        # Fallback to GPSDateTime if Unix is not available
                        datetime_str = row.get('GPSDateTime', '')
                        if not datetime_str:
                            continue
                        # Handle AM/PM format (UTC)
                        timestamp = datetime.strptime(datetime_str, '%m/%d/%Y %I:%M:%S %p').replace(tzinfo=timezone.utc)
                    else:
                        # Use Unix timestamp (seconds since epoch, with milliseconds)
                        unix_timestamp = float(unix_timestamp_str)
                        timestamp = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)

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
    Enrich events with GPS coordinates and chainage by matching timestamps
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

        # Get chainage for start time (only if not already set from file)
        if event.start_chainage == 0.0:  # Only set if not loaded from file
            start_chainage = gps_data.interpolate_chainage(event.start_time)
            if start_chainage is not None:
                event.start_chainage = start_chainage

        # Get chainage for end time (only if not already set from file)
        if event.end_chainage == 0.0:  # Only set if not loaded from file
            end_chainage = gps_data.interpolate_chainage(event.end_time)
            if end_chainage is not None:
                event.end_chainage = end_chainage


def save_driveevt(events: List[Event], file_path: str, fileid: str = "") -> bool:
    """
    Save events to .driveevt file format
    Each event creates two rows: start event and end event
    Creates backup of original file as .driveevt.backup before saving
    Uses FileID for SessionToken and New Zealand local time for Time column
    """
    try:
        # Create backup of original file if it exists
        if os.path.exists(file_path):
            backup_path = file_path + '.backup'
            try:
                import shutil
                shutil.copy2(file_path, backup_path)
                print(f"Created backup: {backup_path}")
            except Exception as backup_error:
                print(f"Warning: Could not create backup: {backup_error}")

        # New Zealand timezone (UTC+12, with DST UTC+13)
        nz_tz = pytz.timezone('Pacific/Auckland')

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow([
                'SessionToken', 'Distance', 'Chainage', 'Time', 'TimeUtc',
                'Event', 'IsSpanEvent', 'SpanEvent', 'IsSpanStartEvent', 'IsSpanEndEvent'
            ])

            # Ensure all events have file_id set to the provided fileid if missing
            for event in events:
                if not getattr(event, 'file_id', ''):
                    event.file_id = fileid

            # Create list of all event rows (start and end events)
            event_rows = []

            for event in events:
                # Convert timestamps to required formats
                # TimeUtc remains in UTC format
                start_time_utc = event.start_time.strftime('%m/%d/%Y %H:%M:%S')
                end_time_utc = event.end_time.strftime('%m/%d/%Y %H:%M:%S')

                # Time column uses New Zealand local time
                start_time_nz = event.start_time.astimezone(nz_tz).strftime('%m/%d/%Y %H:%M:%S')
                end_time_nz = event.end_time.astimezone(nz_tz).strftime('%m/%d/%Y %H:%M:%S')

                # SessionToken: use event's file_id, remove first 2 and last 2 characters
                event_fileid = getattr(event, 'file_id', fileid)
                session_token = event_fileid[2:-2] if len(event_fileid) > 4 else event_fileid

                # Add start event row
                event_rows.append({
                    'time_utc': event.start_time,  # For sorting
                    'row': [
                        session_token,  # SessionToken (FileID with first/last 2 chars removed)
                        f"{event.start_chainage:.10f}",  # Distance (using start chainage as distance, 10 decimal places)
                        f"{event.start_chainage:.10f}",  # Chainage (10 decimal places)
                        start_time_nz,  # Time (New Zealand local time)
                        start_time_utc,  # TimeUtc
                        f"{event.event_name} Start",  # Event (add "Start" suffix)
                        'True',  # IsSpanEvent
                        event.event_name,  # SpanEvent
                        'True',  # IsSpanStartEvent
                        'False'  # IsSpanEndEvent
                    ]
                })

                # Add end event row
                event_rows.append({
                    'time_utc': event.end_time,  # For sorting
                    'row': [
                        session_token,  # SessionToken (FileID with first/last 2 chars removed)
                        f"{event.end_chainage:.10f}",  # Distance (using end chainage as distance, 10 decimal places)
                        f"{event.end_chainage:.10f}",  # Chainage (10 decimal places)
                        end_time_nz,  # Time (New Zealand local time)
                        end_time_utc,  # TimeUtc
                        f"{event.event_name} End",  # Event (add "End" suffix)
                        'True',  # IsSpanEvent
                        event.event_name,  # SpanEvent
                        'False',  # IsSpanStartEvent
                        'True'  # IsSpanEndEvent
                    ]
                })

            # Sort all event rows by TimeUtc
            event_rows.sort(key=lambda x: x['time_utc'])

            # Write sorted rows
            for event_row in event_rows:
                writer.writerow(event_row['row'])

        return True

    except Exception as e:
        print(f"Error saving events to {file_path}: {e}")
        return False