import csv
import os
import shutil
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple
import pytz

from ..models.event_model import Event
from ..models.gps_model import GPSData, GPSPoint


def _validate_file_path(file_path: str, check_write: bool = False) -> bool:
    try:
        if check_write:
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                logging.error(f"Directory does not exist: {directory}")
                return False
            if directory and not os.access(directory, os.W_OK):
                logging.error(f"No write permission for directory: {directory}")
                return False
        else:
            if not os.path.exists(file_path):
                logging.warning(f"File does not exist: {file_path}")
                return False
        return True
    except Exception as e:
        logging.error(f"Error validating path {file_path}: {e}")
        return False


def _parse_timestamp_utc(time_str: str, format_str: str) -> Optional[datetime]:
    try:
        return datetime.strptime(time_str.strip(), format_str).replace(tzinfo=timezone.utc)
    except ValueError as e:
        logging.warning(f"Error parsing timestamp '{time_str}' with format '{format_str}': {e}")
        return None


def _validate_gps_coordinates(lat: float, lon: float) -> bool:
    if not (-90 <= lat <= 90):
        logging.warning(f"Invalid latitude: {lat} (must be between -90 and 90)")
        return False
    if not (-180 <= lon <= 180):
        logging.warning(f"Invalid longitude: {lon} (must be between -180 and 180)")
        return False
    return True


def parse_driveevt(file_path: str) -> List[Event]:
    events = []

    if not _validate_file_path(file_path, check_write=False):
        return events

    skipped_count = 0

    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            start_events = []
            end_events = []

            for row_idx, row in enumerate(reader):
                try:
                    if row.get('IsSpanEvent', '').lower() != 'true':
                        continue

                    span_name = row.get('SpanEvent', '')
                    is_start = row.get('IsSpanStartEvent', '').lower() == 'true'
                    is_end = row.get('IsSpanEndEvent', '').lower() == 'true'

                    if not span_name:
                        skipped_count += 1
                        logging.debug(f"Row {row_idx}: Skipping event with no name")
                        continue

                    time_str = row.get('TimeUtc', '')
                    if not time_str or not time_str.strip():
                        skipped_count += 1
                        logging.warning(f"Row {row_idx}: Missing TimeUtc for event {span_name}")
                        continue

                    timestamp = _parse_timestamp_utc(time_str, '%m/%d/%Y %H:%M:%S')
                    if not timestamp:
                        skipped_count += 1
                        continue

                    try:
                        chainage = float(row.get('Chainage', '0'))
                    except ValueError:
                        logging.warning(f"Row {row_idx}: Invalid chainage for event {span_name}, using 0.0")
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
                except Exception as e:
                    skipped_count += 1
                    logging.warning(f"Row {row_idx}: Error parsing row: {e}")
                    continue

            if skipped_count > 0:
                logging.info(f"Skipped {skipped_count} invalid rows in {file_path}")

            start_events.sort(key=lambda x: x['time'])
            end_events.sort(key=lambda x: x['time'])

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
                    if end['time'] >= start['time']:
                        if best_end is None or end['time'] < best_end['time']:
                            best_end = end
                            best_end_idx = j

                if best_end:
                    used_starts.add(i)
                    used_ends.add(best_end_idx)
                    if best_end['chainage'] < start['chainage']:
                        logging.warning(f"Event {start['name']}: end_chainage < start_chainage")
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
                else:
                    logging.warning(f"No matching end event found for '{start['name']}' at {start['time']}")

            logging.info(f"Successfully parsed {len(events)} events from {file_path}")

    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
    except PermissionError:
        logging.error(f"Permission denied reading file: {file_path}")
    except csv.Error as e:
        logging.error(f"CSV parsing error in {file_path}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error parsing {file_path}: {e}")

    return events


def parse_driveiri(file_path: str) -> GPSData:
    gps_data = GPSData()

    if not _validate_file_path(file_path, check_write=False):
        return gps_data

    skipped_count = 0
    valid_count = 0

    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            for row_idx, row in enumerate(reader):
                try:
                    unix_timestamp_str = row.get('Unix', '')
                    if not unix_timestamp_str:
                        datetime_str = row.get('GPSDateTime', '')
                        if not datetime_str or not datetime_str.strip():
                            skipped_count += 1
                            logging.debug(f"Row {row_idx}: Missing timestamp")
                            continue
                        timestamp = _parse_timestamp_utc(datetime_str, '%m/%d/%Y %I:%M:%S %p')
                        if not timestamp:
                            skipped_count += 1
                            continue
                    else:
                        try:
                            unix_timestamp = float(unix_timestamp_str)
                            if unix_timestamp < 0 or unix_timestamp > 32503680000:  # year 3000
                                raise ValueError("Unix timestamp out of range")
                            timestamp = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
                        except (ValueError, OSError) as e:
                            skipped_count += 1
                            logging.warning(f"Row {row_idx}: Invalid Unix timestamp '{unix_timestamp_str}': {e}")
                            continue

                    try:
                        lat = float(row.get('Position (begin) (LAT)', '0'))
                        lon = float(row.get('Position (begin) (LON)', '0'))
                    except ValueError as e:
                        skipped_count += 1
                        logging.warning(f"Row {row_idx}: Invalid GPS coordinates: {e}")
                        continue

                    if not _validate_gps_coordinates(lat, lon):
                        skipped_count += 1
                        continue

                    try:
                        start_chainage_km = float(row.get('StartChainage [km]', '0'))
                        start_chainage = start_chainage_km * 1000
                    except ValueError:
                        logging.debug(f"Row {row_idx}: Invalid chainage, using 0.0")
                        start_chainage = 0.0

                    speed = None
                    try:
                        speed_str = row.get('AverageSpeed [km/h]', '')
                        if speed_str:
                            speed = float(speed_str)
                    except (ValueError, TypeError):
                        pass

                    elevation = None
                    try:
                        elevation_str = row.get('Elevation [m]', '')
                        if elevation_str:
                            elevation = float(elevation_str)
                    except (ValueError, TypeError):
                        pass

                    point = GPSPoint(
                        timestamp=timestamp,
                        latitude=lat,
                        longitude=lon,
                        chainage=start_chainage,
                        speed=speed,
                        elevation=elevation
                    )

                    gps_data.add_point(point)
                    valid_count += 1

                except KeyError as e:
                    skipped_count += 1
                    logging.warning(f"Row {row_idx}: Missing required field: {e}")
                    continue
                except ValueError as e:
                    skipped_count += 1
                    logging.warning(f"Row {row_idx}: Value error: {e}")
                    continue
                except Exception as e:
                    skipped_count += 1
                    logging.warning(f"Row {row_idx}: Unexpected error: {e}")
                    continue

            if skipped_count > 0:
                logging.info(f"Skipped {skipped_count} invalid rows in {file_path}")

            logging.info(f"Successfully parsed {valid_count} GPS points from {file_path}")

    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
    except PermissionError:
        logging.error(f"Permission denied reading file: {file_path}")
    except csv.Error as e:
        logging.error(f"CSV parsing error in {file_path}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error parsing {file_path}: {e}")

    return gps_data


def enrich_events_with_gps(events: List[Event], gps_data: GPSData) -> None:
    if not events:
        logging.debug("No events to enrich")
        return

    if not gps_data or not gps_data.points:
        logging.warning("No GPS data available for enrichment")
        return

    gps_data.sort_by_time()
    enriched_count = 0

    for event in events:
        enriched = False

        start_pos = gps_data.interpolate_position(event.start_time)
        if start_pos:
            event.start_lat, event.start_lon = start_pos
            enriched = True

        end_pos = gps_data.interpolate_position(event.end_time)
        if end_pos:
            event.end_lat, event.end_lon = end_pos
            enriched = True

        # Sử dụng None để đánh dấu chainage chưa set, tránh ghi đè giá trị 0 hợp lệ
        # Always update chainage when GPS data is available (for edited events)
        start_chainage = gps_data.interpolate_chainage(event.start_time)
        if start_chainage is not None:
            event.start_chainage = start_chainage
            enriched = True

        end_chainage = gps_data.interpolate_chainage(event.end_time)
        if end_chainage is not None:
            event.end_chainage = end_chainage
            enriched = True

        if enriched:
            enriched_count += 1

    logging.info(f"Enriched {enriched_count}/{len(events)} events with GPS data")


def save_driveevt(events: List[Event], file_path: str, fileid: str = "") -> bool:
    if not events:
        logging.warning("No events to save")
        return False

    if not _validate_file_path(file_path, check_write=True):
        return False

    backup_path = None

    try:
        if os.path.exists(file_path):
            backup_path = file_path + '.backup'
            shutil.copy2(file_path, backup_path)
            logging.info(f"Created backup: {backup_path}")

        nz_tz = pytz.timezone('Pacific/Auckland')

        with open(file_path, 'w', newline='', encoding='utf-8', errors='replace') as f:
            writer = csv.writer(f)
            writer.writerow([
                'SessionToken', 'Distance', 'Chainage', 'Time', 'TimeUtc',
                'Event', 'IsSpanEvent', 'SpanEvent', 'IsSpanStartEvent', 'IsSpanEndEvent'
            ])

            for event in events:
                event_file_id = getattr(event, 'file_id', None)
                if not event_file_id:
                    event.file_id = fileid

            event_rows = []
            for event in events:
                start_time = event.start_time
                end_time = event.end_time

                # Cần đảm bảo luôn timezone-aware (raise nếu naive)
                if start_time.tzinfo is None or end_time.tzinfo is None:
                    raise ValueError(f"Event {event.event_name} has naive datetime! Please provide timezone-aware times.")

                start_time_utc = start_time.strftime('%m/%d/%Y %H:%M:%S')
                end_time_utc = end_time.strftime('%m/%d/%Y %H:%M:%S')

                start_time_nz = start_time.astimezone(nz_tz).strftime('%m/%d/%Y %H:%M:%S')
                end_time_nz = end_time.astimezone(nz_tz).strftime('%m/%d/%Y %H:%M:%S')

                event_fileid = getattr(event, 'file_id', fileid) or ""
                session_token = event_fileid[2:-2] if len(event_fileid) >= 5 else event_fileid

                event_rows.append({
                    'time_utc': start_time,
                    'row': [
                        session_token,
                        f"{event.start_chainage:.10f}",
                        f"{event.start_chainage:.10f}",
                        start_time_nz,
                        start_time_utc,
                        f"{event.event_name} Start",
                        'True',
                        event.event_name,
                        'True',
                        'False'
                    ]
                })
                event_rows.append({
                    'time_utc': end_time,
                    'row': [
                        session_token,
                        f"{event.end_chainage:.10f}",
                        f"{event.end_chainage:.10f}",
                        end_time_nz,
                        end_time_utc,
                        f"{event.event_name} End",
                        'True',
                        event.event_name,
                        'False',
                        'True'
                    ]
                })

            event_rows.sort(key=lambda x: x['time_utc'])
            for event_row in event_rows:
                writer.writerow(event_row['row'])

        if backup_path and os.path.exists(backup_path):
            os.remove(backup_path)
            logging.debug(f"Deleted backup: {backup_path}")

        logging.info(f"Successfully saved {len(events)} events to {file_path}")
        return True

    except PermissionError as e:
        logging.error(f"Permission denied writing to {file_path}: {e}")
        if backup_path and os.path.exists(backup_path):
            shutil.copy2(backup_path, file_path)
            logging.info("Restored from backup")
        return False

    except IOError as e:
        logging.error(f"IO error saving events to {file_path}: {e}")
        if backup_path and os.path.exists(backup_path):
            shutil.copy2(backup_path, file_path)
            logging.info("Restored from backup")
        return False

    except Exception as e:
        logging.error(f"Unexpected error saving events to {file_path}: {e}")
        if backup_path and os.path.exists(backup_path):
            shutil.copy2(backup_path, file_path)
            logging.info("Restored from backup")
        return False
