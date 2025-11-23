"""
Lane assignment data model for GeoEvent application
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from pathlib import Path
import csv
import os
import logging

@dataclass
class LaneFix:
    """
    Lane assignment record
    """
    plate: str
    from_time: datetime
    to_time: datetime
    lane: str  # '1'|'2'|'3'|'4'|'-1'|'TK1'|'TM2'|'SK1'|'SK2'|...
    file_id: str
    ignore: bool = False  # Whether this period should be ignored

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'plate': self.plate,
            'from_time': self.from_time.isoformat(),
            'to_time': self.to_time.isoformat(),
            'lane': self.lane,
            'file_id': self.file_id,
            'ignore': self.ignore
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'LaneFix':
        """Create LaneFix from dictionary"""
        return cls(
            plate=data['plate'],
            from_time=datetime.fromisoformat(data['from_time']),
            to_time=datetime.fromisoformat(data['to_time']),
            lane=data['lane'],
            file_id=data['file_id'],
            ignore=data.get('ignore', False)
        )

class LaneManager:
    """
    Manages lane assignments and turn periods
    """

    def __init__(self):
        self.lane_fixes: List[LaneFix] = []
        self.current_lane: Optional[str] = None
        self.fileid_folder: Optional[Path] = None
        self.plate: Optional[str] = None
        self.end_time: Optional[datetime] = None  # End time of the folder
        self.has_changes = False  # Track if there are unsaved changes
        
        # Metadata for validation
        self.first_image_timestamp: Optional[datetime] = None
        self.last_image_timestamp: Optional[datetime] = None
        self.gps_min_timestamp: Optional[datetime] = None
        self.gps_max_timestamp: Optional[datetime] = None

    def assign_lane(self, lane_code: str, timestamp: datetime) -> bool:
        """
        Assign lane at given timestamp
        All lane types create lane_fix entries for consistency
        Returns True if successful, False if overlap detected or timestamp invalid
        """
        if not self.plate or not self.fileid_folder:
            logging.warning("No plate or fileid_folder set for lane assignment")
            return False

        # Validate timestamp is within valid time bounds
        if not self._is_timestamp_valid(timestamp):
            logging.warning(f"Cannot assign lane at invalid timestamp {timestamp}")
            return False

        # Check if we have existing lane data at this timestamp
        current_lane_at_time = self.get_lane_at_timestamp(timestamp)
        logging.debug(f"Current lane at {timestamp}: {current_lane_at_time}")
        
        # If changing from one lane to another, use smart change logic
        if current_lane_at_time and current_lane_at_time != lane_code:
            logging.debug(f"Changing lane from {current_lane_at_time} to {lane_code}")
            return self.change_lane_smart(lane_code, timestamp)
        
        # If same lane as current at this timestamp, no need to do anything
        if current_lane_at_time == lane_code:
            logging.debug(f"Same lane {lane_code} already at {timestamp}")
            return True
        
        # Standard assignment logic for new assignments
        # Check for overlaps with different lanes (exclude ignore periods)
        if self.check_overlap(timestamp, exclude_ignore=True):
            logging.warning(f"Overlap detected at {timestamp} for lane {lane_code}")
            return False

        # If same lane as current, extend period
        if self.current_lane == lane_code and self.lane_fixes:
            # Extend the last lane fix
            self.lane_fixes[-1].to_time = timestamp
        else:
            # End current period if exists
            if self.current_lane and self.lane_fixes:
                self.lane_fixes[-1].to_time = timestamp

            # Start new period
            # Handle special lane codes
            actual_lane_code = self._resolve_lane_code(lane_code, self.current_lane)
            
            lane_fix = LaneFix(
                plate=self.plate,
                from_time=timestamp,
                to_time=timestamp,  # Will be extended later
                lane=actual_lane_code,
                ignore=(lane_code == ''),  # Mark as ignore if lane_code is empty
                file_id=self.fileid_folder.name
            )
            self.lane_fixes.append(lane_fix)
            self.current_lane = actual_lane_code

            # If this is the last lane assignment and we have end_time, extend to end
            if self.end_time and not self._has_lane_after(timestamp):
                lane_fix.to_time = self.end_time
                logging.info(f"Extended lane {lane_code} to folder end time: {self.end_time}")

        self.has_changes = True
        return True

    def _is_timestamp_valid(self, timestamp: datetime) -> bool:
        """
        Check if timestamp is within valid time bounds for lane assignment
        """
        # Determine valid time range (union of image and GPS ranges)
        valid_min_time = None
        valid_max_time = None
        
        if self.first_image_timestamp and self.last_image_timestamp:
            if valid_min_time is None or self.first_image_timestamp < valid_min_time:
                valid_min_time = self.first_image_timestamp
            if valid_max_time is None or self.last_image_timestamp > valid_max_time:
                valid_max_time = self.last_image_timestamp
        
        if self.gps_min_timestamp and self.gps_max_timestamp:
            if valid_min_time is None or self.gps_min_timestamp < valid_min_time:
                valid_min_time = self.gps_min_timestamp
            if valid_max_time is None or self.gps_max_timestamp > valid_max_time:
                valid_max_time = self.gps_max_timestamp
        
        if valid_min_time is None or valid_max_time is None:
            # No time range available, allow assignment
            return True
        
        # Check bounds with tolerance
        tolerance_seconds = 1.0
        return (timestamp >= valid_min_time - timedelta(seconds=tolerance_seconds) and 
                timestamp <= valid_max_time + timedelta(seconds=tolerance_seconds))

    def _resolve_lane_code(self, lane_code: str, reference_lane: str = None) -> str:
        """Resolve special lane codes like SK based on reference lane"""
        if lane_code == 'SK':
            # SK uses reference lane number (SK1, SK2, SK3, etc.)
            # Extract lane number from reference lane (could be '1', 'TK1', 'TM2', etc.)
            lane_number = None
            if reference_lane:
                if reference_lane in ['1', '2', '3', '4']:
                    lane_number = reference_lane
                elif len(reference_lane) >= 3 and reference_lane[:2] in ['TK', 'TM'] and reference_lane[2] in ['1', '2', '3', '4']:
                    lane_number = reference_lane[2]
                elif len(reference_lane) >= 3 and reference_lane[:2] == 'SK' and reference_lane[2] in ['1', '2', '3', '4']:
                    lane_number = reference_lane[2]

            if lane_number:
                return f"{lane_code}{lane_number}"
            else:
                return lane_code
        # TK and TM are now direct codes (TK1, TK2, TM1, TM2, etc.)
        return lane_code

    def change_lane_smart(self, new_lane_code: str, timestamp: datetime, user_choice_callback=None, custom_end_time: datetime = None) -> bool:
        """
        Smart lane change for all lane types using period splitting
        Returns True if successful, False otherwise
        """
        if not self.plate or not self.fileid_folder:
            logging.warning("No plate or fileid_folder set for smart lane change")
            return False

        # Validate timestamp is within valid time bounds
        if not self._is_timestamp_valid(timestamp):
            logging.warning(f"Cannot change lane at invalid timestamp {timestamp}")
            return False

        # Find the current lane period at this timestamp
        current_lane_at_time = self.get_lane_at_timestamp(timestamp)
        if not current_lane_at_time:
            logging.warning(f"No lane found at timestamp {timestamp}")
            return False

        # Find the lane fix record for this period
        target_fix = None
        for fix in self.lane_fixes:
            if fix.from_time <= timestamp <= fix.to_time and fix.lane == current_lane_at_time:
                target_fix = fix
                break

        if not target_fix:
            logging.error(f"Could not find lane fix record for timestamp {timestamp}")
            return False

        if current_lane_at_time == new_lane_code:
            if custom_end_time and custom_end_time != target_fix.to_time:
                # For same lane with custom end time, split the period
                original_end = target_fix.to_time
                # Update current period end to custom_end_time
                target_fix.to_time = custom_end_time
                # Create new period from custom_end_time to original_end with same lane
                new_period = LaneFix(
                    plate=self.plate,
                    from_time=custom_end_time,
                    to_time=original_end,
                    lane=target_fix.lane,
                    ignore=target_fix.ignore,
                    file_id=self.fileid_folder.name
                )
                self.lane_fixes.append(new_period)
                # Do not merge for same lane splits to preserve the split
                return True
            else:
                logging.info("Same lane, no change needed")
                return True

        # Resolve special lane codes based on current lane
        resolved_new_lane = self._resolve_lane_code(new_lane_code, target_fix.lane)

        # Determine change scope based on user choice
        if user_choice_callback:
            try:
                change_scope = user_choice_callback(
                    current_lane=current_lane_at_time,
                    new_lane=resolved_new_lane,
                    timestamp=timestamp,
                    period_start=target_fix.from_time,
                    period_end=target_fix.to_time
                )
            except Exception as e:
                logging.error(f"Error getting user choice: {e}")
                return False
        else:
            # Default: change from timestamp to end of period
            change_scope = 'forward'

        # Apply the change based on scope
        if change_scope == 'forward':
            # Change from timestamp to end of current period
            self._apply_lane_change_forward(target_fix, resolved_new_lane, timestamp)
        elif change_scope == 'backward':
            # Change from start of current period to timestamp
            self._apply_lane_change_backward(target_fix, resolved_new_lane, timestamp)
        elif change_scope == 'current':
            # Change entire current period
            self._apply_lane_change_entire(target_fix, resolved_new_lane)
        elif change_scope == 'custom' and custom_end_time:
            # Change from timestamp to custom_end_time using range logic
            self.apply_lane_change_range(resolved_new_lane, timestamp, custom_end_time)
        else:
            logging.error(f"Invalid change scope: {change_scope}")
            return False

        self.has_changes = True
        return True

    def _apply_lane_change_forward(self, target_fix, new_lane_code: str, timestamp: datetime):
        """Change lane from timestamp to end of period"""
        # Split the current period at timestamp
        # Keep original period until timestamp
        # Create new period from timestamp to original end
        
        original_end = target_fix.to_time
        
        # End current period at timestamp
        target_fix.to_time = timestamp
        
        # Create new period with new lane
        new_fix = LaneFix(
            plate=self.plate,
            from_time=timestamp,
            to_time=original_end,
            lane=new_lane_code,
            ignore=(new_lane_code == ''),
            file_id=self.fileid_folder.name
        )
        self.lane_fixes.append(new_fix)
        
        # Merge adjacent periods with the same lane
        self._merge_adjacent_same_lane_periods()
        
        # Update current_lane if this affects the current state
        if timestamp <= datetime.now(timezone.utc) <= original_end:
            self.current_lane = new_lane_code

    def _apply_lane_change_backward(self, target_fix, new_lane_code: str, timestamp: datetime):
        """Change lane from start of period to timestamp"""
        # Change the lane of the current period from start to timestamp
        # Create new period from timestamp to original end with original lane
        
        original_lane = target_fix.lane
        original_end = target_fix.to_time
        
        # Change current period lane
        target_fix.lane = new_lane_code
        target_fix.ignore = (new_lane_code == '')
        target_fix.to_time = timestamp
        
        # Create continuation period with original lane
        new_fix = LaneFix(
            plate=self.plate,
            from_time=timestamp,
            to_time=original_end,
            lane=original_lane,
            file_id=self.fileid_folder.name
        )
        self.lane_fixes.append(new_fix)
        
        # Merge adjacent periods with the same lane
        self._merge_adjacent_same_lane_periods()

    def _apply_lane_change_entire(self, target_fix, new_lane_code: str):
        """Change entire period to new lane"""
        target_fix.lane = new_lane_code
        target_fix.ignore = (new_lane_code == '')
        
        # Update current_lane if this period is current
        now = datetime.now(timezone.utc)
        if target_fix.from_time <= now <= target_fix.to_time:
            self.current_lane = new_lane_code

    def _apply_lane_change_custom(self, target_fix, new_lane_code: str, timestamp: datetime, custom_end_time: datetime):
        """Change lane from timestamp to custom_end_time"""
        # Similar to forward change but with custom end time
        # Split the current period at timestamp and custom_end_time
        
        original_end = target_fix.to_time
        
        # End current period at timestamp
        target_fix.to_time = timestamp
        
        # Create new period with new lane from timestamp to custom_end_time
        new_fix = LaneFix(
            plate=self.plate,
            from_time=timestamp,
            to_time=custom_end_time,
            lane=new_lane_code,
            ignore=(new_lane_code == ''),
            file_id=self.fileid_folder.name
        )
        self.lane_fixes.append(new_fix)
        
        # If there's remaining time after custom_end_time, create continuation with original lane
        if custom_end_time < original_end:
            continuation_fix = LaneFix(
                plate=self.plate,
                from_time=custom_end_time,
                to_time=original_end,
                lane=target_fix.lane,  # Original lane
                ignore=target_fix.ignore,  # Preserve original ignore flag
                file_id=self.fileid_folder.name
            )
    def assign_sk(self, timestamp: datetime) -> bool:
        """Assign shoulder lane (SK) at given timestamp"""
        return self.assign_lane('SK', timestamp)

    def assign_ignore(self, timestamp: datetime) -> bool:
        """Assign ignore period at given timestamp"""
        return self.assign_lane('', timestamp)

    def _has_lane_after(self, timestamp: datetime) -> bool:
        """Check if there are any lane assignments after the given timestamp"""
        for fix in self.lane_fixes:
            if fix.from_time > timestamp:
                return True
        return False

    def check_overlap(self, timestamp: datetime, exclude_ignore: bool = False, exclude_special: bool = False) -> bool:
        """
        Check if timestamp overlaps with existing lane periods
        exclude_ignore: if True, ignore periods are not considered as overlaps
        exclude_special: if True, special lanes (SK*, IGNORE) are not considered as overlaps
        """
        for fix in self.lane_fixes:
            if fix.from_time is not None and fix.to_time is not None:
                # Skip ignore periods if exclude_ignore is True
                if exclude_ignore and fix.ignore:
                    continue
                # Skip special lanes (SK*, or ignore entries) if exclude_special is True
                if exclude_special and (fix.lane.startswith('SK') or fix.ignore):
                    continue
                if fix.from_time <= timestamp <= fix.to_time:
                    return True
        return False

    def get_lane_fixes(self) -> List[LaneFix]:
        """Get all lane fixes sorted by time"""
        return sorted(self.lane_fixes, key=lambda x: x.from_time)

    def get_lane_at_timestamp(self, timestamp: datetime) -> str:
        """Get the lane code active at the given timestamp"""
        # Sort by from_time descending to check latest periods first
        for fix in sorted(self.lane_fixes, key=lambda x: x.from_time, reverse=True):
            if fix.from_time is not None and fix.to_time is not None:
                if fix.from_time <= timestamp <= fix.to_time:
                    return fix.lane
        return None

    def clear(self):
        """Clear all lane assignments"""
        self.lane_fixes.clear()
        self.current_lane = None

    def set_fileid_folder(self, fileid_folder_path: str, plate: str = None):
        """Set the current FileID folder and load lane fixes"""
        from pathlib import Path
        self.fileid_folder = Path(fileid_folder_path)
        self.plate = plate
        self._load_lane_fixes()

    def set_end_time(self, end_time: datetime):
        """Set the end time of the folder for extending lanes"""
        self.end_time = end_time

    def set_metadata(self, first_image_timestamp: Optional[datetime] = None, 
                    last_image_timestamp: Optional[datetime] = None,
                    gps_min_timestamp: Optional[datetime] = None,
                    gps_max_timestamp: Optional[datetime] = None):
        """Set metadata for time bounds validation"""
        self.first_image_timestamp = first_image_timestamp
        self.last_image_timestamp = last_image_timestamp
        self.gps_min_timestamp = gps_min_timestamp
        self.gps_max_timestamp = gps_max_timestamp

    def validate_lane_fixes_time_bounds(self) -> List[str]:
        """
        Validate that all lane fixes are within valid time bounds
        Returns list of validation errors, empty list if all valid
        """
        errors = []
        
        if not self.lane_fixes:
            return errors  # No fixes to validate
        
        # Determine valid time range (union of image and GPS ranges)
        valid_min_time = None
        valid_max_time = None
        
        if self.first_image_timestamp and self.last_image_timestamp:
            if valid_min_time is None or self.first_image_timestamp < valid_min_time:
                valid_min_time = self.first_image_timestamp
            if valid_max_time is None or self.last_image_timestamp > valid_max_time:
                valid_max_time = self.last_image_timestamp
        
        if self.gps_min_timestamp and self.gps_max_timestamp:
            if valid_min_time is None or self.gps_min_timestamp < valid_min_time:
                valid_min_time = self.gps_min_timestamp
            if valid_max_time is None or self.gps_max_timestamp > valid_max_time:
                valid_max_time = self.gps_max_timestamp
        
        if valid_min_time is None or valid_max_time is None:
            # No time range available for validation
            return errors
        
        # Validate each lane fix
        tolerance_seconds = 1.0  # Allow 1 second tolerance for floating point precision
        
        for i, fix in enumerate(self.lane_fixes):
            # Check from_time bounds
            if fix.from_time < valid_min_time - timedelta(seconds=tolerance_seconds):
                errors.append(f"Fix {i} ({fix.lane}): from_time {fix.from_time} < valid_min {valid_min_time}")
            
            # Check to_time bounds
            if fix.to_time > valid_max_time + timedelta(seconds=tolerance_seconds):
                errors.append(f"Fix {i} ({fix.lane}): to_time {fix.to_time} > valid_max {valid_max_time}")
            
            # Check from_time < to_time
            if fix.from_time >= fix.to_time:
                errors.append(f"Fix {i} ({fix.lane}): from_time {fix.from_time} >= to_time {fix.to_time}")
        
        return errors

    def _get_lane_fix_path(self) -> Path:
        """Get the path to the lane fix CSV file"""
        if not self.fileid_folder:
            return None
        return self.fileid_folder / f"{self.fileid_folder.name}_lane_fixes.csv"

    def _load_lane_fixes(self):
        """Load lane fixes from CSV file, create empty file if not exists"""
        if not self.fileid_folder:
            return

        lane_fix_path = self._get_lane_fix_path()

        # Always ensure the file exists
        if not lane_fix_path.exists():
            self._create_empty_lane_fix_file()
            self.lane_fixes = []
            logging.info(f"Created empty lane fix file: {lane_fix_path}")
            return

        try:
            self.lane_fixes = []
            with open(lane_fix_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Parse timestamps - handle different formats
                    try:
                        from_time_str = row['From']
                        to_time_str = row['To']
                        
                        # Try different time formats
                        # Format 1: DD/MM/YY HH:MM:SS.sss (saved by export_manager)
                        if '/' in from_time_str and len(from_time_str.split()) == 2:
                            try:
                                from_time = datetime.strptime(from_time_str, '%d/%m/%y %H:%M:%S.%f').replace(tzinfo=timezone.utc)
                                to_time = datetime.strptime(to_time_str, '%d/%m/%y %H:%M:%S.%f').replace(tzinfo=timezone.utc)
                            except ValueError:
                                # Try without microseconds
                                from_time = datetime.strptime(from_time_str, '%d/%m/%y %H:%M:%S').replace(tzinfo=timezone.utc)
                                to_time = datetime.strptime(to_time_str, '%d/%m/%y %H:%M:%S').replace(tzinfo=timezone.utc)
                        # Format 2: MM:SS.s (total minutes:seconds.tenth from start of day)
                        elif ':' in from_time_str and from_time_str.count(':') == 1:
                            try:
                                from_parts = from_time_str.split(':')
                                to_parts = to_time_str.split(':')
                                
                                from_total_minutes = int(from_parts[0])
                                from_seconds = float(from_parts[1])
                                to_total_minutes = int(to_parts[0])
                                to_seconds = float(to_parts[1])
                                
                                # Convert to hours/minutes/seconds
                                from_hour = from_total_minutes // 60
                                from_minute = from_total_minutes % 60
                                to_hour = to_total_minutes // 60
                                to_minute = to_total_minutes % 60
                                
                                # Create datetime
                                today = datetime.now(timezone.utc).date()
                                from_time = datetime(today.year, today.month, today.day, 
                                                   from_hour, from_minute, int(from_seconds), 
                                                   int((from_seconds % 1) * 1000000), timezone.utc)
                                to_time = datetime(today.year, today.month, today.day,
                                                 to_hour, to_minute, int(to_seconds),
                                                 int((to_seconds % 1) * 1000000), timezone.utc)
                            except (ValueError, IndexError):
                                # Fall back to assuming HH:MM:SS.s format
                                from_time_str = f"00:{from_time_str}"
                                to_time_str = f"00:{to_time_str}"
                                today = datetime.now(timezone.utc).date()
                                from_time_full = f"{today} {from_time_str}"
                                to_time_full = f"{today} {to_time_str}"
                                from_time = datetime.strptime(from_time_full, '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=timezone.utc)
                                to_time = datetime.strptime(to_time_full, '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=timezone.utc)
                        else:
                            # Assume HH:MM:SS.s format
                            today = datetime.now(timezone.utc).date()
                            from_time_full = f"{today} {from_time_str}"
                            to_time_full = f"{today} {to_time_str}"
                            from_time = datetime.strptime(from_time_full, '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=timezone.utc)
                            to_time = datetime.strptime(to_time_full, '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=timezone.utc)
                    except ValueError:
                        try:
                            # Try without microseconds
                            from_time = datetime.strptime(from_time_full, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
                            to_time = datetime.strptime(to_time_full, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
                        except ValueError:
                            logging.error(f"Could not parse time format: {from_time_str} or {to_time_str}")
                            continue

                    lane_fix = LaneFix(
                        plate=row.get('Plate', '') or self.plate or '',
                        from_time=from_time,
                        to_time=to_time,
                        lane=row.get('Lane', ''),
                        file_id=self.fileid_folder.name,
                        ignore=row.get('Ignore', '').strip() == '1'
                    )
                    
                    # Validate the loaded lane fix before adding
                    temp_manager = LaneManager()
                    temp_manager.lane_fixes = [lane_fix]
                    temp_manager.first_image_timestamp = self.first_image_timestamp
                    temp_manager.last_image_timestamp = self.last_image_timestamp
                    temp_manager.gps_min_timestamp = self.gps_min_timestamp
                    temp_manager.gps_max_timestamp = self.gps_max_timestamp
                    
                    if not temp_manager.validate_lane_fixes_time_bounds():
                        self.lane_fixes.append(lane_fix)
                    else:
                        logging.warning(f"Skipped invalid lane fix from file: {lane_fix.from_time} to {lane_fix.to_time}, lane={lane_fix.lane}")

            logging.info(f"Loaded {len(self.lane_fixes)} lane fixes from {lane_fix_path}")

        except Exception as e:
            logging.error(f"Error loading lane fixes from {lane_fix_path}: {e}")
            self.lane_fixes = []

        # Validate lane fixes time bounds (should be clean now)
        validation_errors = self.validate_lane_fixes_time_bounds()
        if validation_errors:
            logging.warning(f"Lane fixes validation errors after loading {self.fileid_folder.name}:")
            for error in validation_errors:
                logging.warning(f"  {error}")
        else:
            logging.info(f"Lane fixes validation passed for {self.fileid_folder.name}")

        self.has_changes = False  # Reset change flag after loading

    def _create_empty_lane_fix_file(self):
        """Create an empty lane fix CSV file with headers"""
        if not self.fileid_folder:
            return

        lane_fix_path = self._get_lane_fix_path()

        try:
            with open(lane_fix_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Write header matching the example format
                writer.writerow(['Plate', 'From', 'To', 'Lane', 'Ignore', 'RegionID', 'RoadID', 'Travel'])
            logging.info(f"Created empty lane fix file: {lane_fix_path}")
        except Exception as e:
            logging.error(f"Error creating empty lane fix file {lane_fix_path}: {e}")

    def save_lane_fixes(self):
        """Save current lane fixes to CSV file"""
        if not self.fileid_folder:
            return False

        lane_fix_path = self._get_lane_fix_path()

        try:
            with open(lane_fix_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow(['Plate', 'From', 'To', 'Lane', 'Ignore', 'RegionID', 'RoadID', 'Travel'])

                # Sort lane fixes by from_time before saving
                sorted_fixes = sorted(self.lane_fixes, key=lambda x: x.from_time)

                # Write data - format times as HH:MM:SS.sss
                for fix in sorted_fixes:
                    writer.writerow([
                        fix.plate,
                        fix.from_time.strftime('%H:%M:%S.%f')[:-3],  # Remove last 3 digits of microseconds
                        fix.to_time.strftime('%H:%M:%S.%f')[:-3],
                        fix.lane,
                        '1' if fix.ignore else '',  # Ignore
                        '',  # RegionID
                        '',  # RoadID
                        'N'  # Travel direction
                    ])

            logging.info(f"Saved {len(sorted_fixes)} lane fixes to {lane_fix_path}")
            self.has_changes = False  # Reset change flag after successful save
            return True

        except Exception as e:
            logging.error(f"Error saving lane fixes to {lane_fix_path}: {e}")
            return False

    def get_lane_color(self, lane_code: str) -> str:
        """Get the color for a lane code"""
        colors = {
            '1': '#2ECC71',  # Green
            '2': '#3498DB',  # Blue
            '3': '#F39C12',  # Orange
            '4': '#E74C3C',  # Red
            'IGNORE': '#7F8C8D', # Ignore - Dark Gray
            'SK1': '#FF6B35', # Shoulder lane 1 - Red-orange
            'SK2': '#FF6B35', # Shoulder lane 2 - Red-orange
            'TK': '#9B59B6', # Turn Left - Purple
            'TM': '#9B59B6', # Turn Right - Purple
        }
        return colors.get(lane_code, '#95A5A6')  # Default gray

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'lane_fixes': [fix.to_dict() for fix in self.lane_fixes],
            'current_lane': self.current_lane
        }

    def get_lane_fixes(self):
        """Get all lane fixes for timeline display, sorted by time"""
        return sorted(self.lane_fixes, key=lambda x: x.from_time)

    def get_lane_color(self, lane_code: str) -> str:
        """Get color for lane display"""
        color_map = {
            '1': '#4CAF50',  # Green
            '2': '#2196F3',  # Blue
            '3': '#FF9800',  # Orange
            '4': '#9C27B0',  # Purple
            'SK': '#FF5722', # Deep Orange
            'TK': '#795548', # Brown
            'TM': '#607D8B', # Blue Grey
        }
        return color_map.get(lane_code, '#9E9E9E')  # Default gray

    def apply_lane_change_range(self, new_lane_code: str, start_time: datetime, end_time: datetime):
        """Apply lane change for a time range, splitting periods as needed"""
        # Find all periods that overlap with [start_time, end_time]
        overlapping_fixes = []
        for fix in self.lane_fixes:
            if fix.from_time < end_time and fix.to_time > start_time:
                overlapping_fixes.append(fix)
        
        # Sort by from_time
        overlapping_fixes.sort(key=lambda x: x.from_time)
        
        # Clamp end_time to not exceed the last overlapping period's end time
        if overlapping_fixes:
            max_end_time = max(fix.to_time for fix in overlapping_fixes)
            if end_time > max_end_time:
                logging.info(f"Clamping end_time from {end_time} to {max_end_time}")
                end_time = max_end_time
        
        # Create new periods
        new_fixes = []
        
        # Handle the start part - keep original lane until start_time
        if overlapping_fixes and overlapping_fixes[0].from_time < start_time:
            first_fix = overlapping_fixes[0]
            start_part = LaneFix(
                plate=self.plate,
                from_time=first_fix.from_time,
                to_time=start_time,
                lane=first_fix.lane,
                ignore=first_fix.ignore,  # Preserve original ignore flag
                file_id=self.fileid_folder.name
            )
            new_fixes.append(start_part)
        
        # Add the new lane period
        new_lane_fix = LaneFix(
            plate=self.plate,
            from_time=start_time,
            to_time=end_time,
            lane=new_lane_code,
            ignore=(new_lane_code == ''),
            file_id=self.fileid_folder.name
        )
        new_fixes.append(new_lane_fix)
        
        # Handle the end part - keep original lane from end_time
        if overlapping_fixes:
            # Find the period that contains end_time to get the correct lane
            end_period = None
            for fix in overlapping_fixes:
                if fix.from_time <= end_time <= fix.to_time:
                    end_period = fix
                    break
            
            # If end_time is within a period, create end part from end_time to that period's end
            if end_period and end_period.to_time > end_time:
                end_part = LaneFix(
                    plate=self.plate,
                    from_time=end_time,
                    to_time=end_period.to_time,
                    lane=end_period.lane,
                    ignore=end_period.ignore,
                    file_id=self.fileid_folder.name
                )
                new_fixes.append(end_part)
            
            # Handle any remaining periods after the end_period
            remaining_fixes = []
            if end_period:
                # Find fixes that start after end_period
                remaining_fixes = [fix for fix in overlapping_fixes if fix.from_time >= end_period.to_time]
            else:
                # If end_time is not in any period, find fixes that start after end_time
                remaining_fixes = [fix for fix in overlapping_fixes if fix.from_time >= end_time]
            
            # Add remaining periods as-is
            for fix in remaining_fixes:
                remaining_part = LaneFix(
                    plate=self.plate,
                    from_time=fix.from_time,
                    to_time=fix.to_time,
                    lane=fix.lane,
                    ignore=fix.ignore,
                    file_id=self.fileid_folder.name
                )
                new_fixes.append(remaining_part)
        
        # Replace overlapping fixes with new fixes
        self.lane_fixes = [fix for fix in self.lane_fixes if fix not in overlapping_fixes] + new_fixes
        
        self.has_changes = True
        return True

    def _merge_adjacent_same_lane_periods(self):
        """Merge adjacent periods with the same lane"""
        if not self.lane_fixes:
            return
        
        # Sort by from_time
        self.lane_fixes.sort(key=lambda x: x.from_time)
        
        merged = []
        current = self.lane_fixes[0]
        
        for next_fix in self.lane_fixes[1:]:
            if (current.lane == next_fix.lane and 
                current.to_time == next_fix.from_time and
                current.ignore == next_fix.ignore):
                # Merge
                current.to_time = next_fix.to_time
            else:
                merged.append(current)
                current = next_fix
        
        merged.append(current)
        self.lane_fixes = merged

    def get_next_lane_change_time(self, timestamp: datetime) -> Optional[datetime]:
        """
        Get the timestamp of the next lane change after the given timestamp
        Returns None if no lane change found
        """
        future_fixes = [fix for fix in self.lane_fixes if fix.from_time > timestamp]
        if not future_fixes:
            return None
        # Return the earliest future lane change time
        return min(fix.from_time for fix in future_fixes)

    @classmethod
    def from_dict(cls, data: dict) -> 'LaneManager':
        """Create LaneManager from dictionary"""
        manager = cls()
        manager.lane_fixes = [LaneFix.from_dict(fix) for fix in data.get('lane_fixes', [])]
        manager.current_lane = data.get('current_lane')
        return manager