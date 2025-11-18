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
        self.turn_active = False
        self.turn_start_lane: Optional[str] = None
        self.fileid_folder: Optional[Path] = None
        self.plate: Optional[str] = None
        self.end_time: Optional[datetime] = None  # End time of the folder
        self.has_changes = False  # Track if there are unsaved changes

    def assign_lane(self, lane_code: str, timestamp: datetime) -> bool:
        """
        Assign lane at given timestamp
        Returns True if successful, False if overlap detected
        """
        if not self.plate or not self.fileid_folder:
            logging.warning("No plate or fileid_folder set for lane assignment")
            return False

        # Check for overlaps (exclude ignore and special periods)
        if self.check_overlap(timestamp, exclude_ignore=True, exclude_special=True):
            return False

        # End any active turn when assigning a new lane
        if self.turn_active:
            self.end_turn(timestamp)

        # If same lane as current, extend period
        if self.current_lane == lane_code and self.lane_fixes:
            # Extend the last lane fix
            self.lane_fixes[-1].to_time = timestamp
        else:
            # End current period if exists
            if self.current_lane and self.lane_fixes:
                self.lane_fixes[-1].to_time = timestamp

            # Start new period
            lane_fix = LaneFix(
                plate=self.plate,
                from_time=timestamp,
                to_time=timestamp,  # Will be extended later
                lane=lane_code,
                file_id=self.fileid_folder.name
            )
            self.lane_fixes.append(lane_fix)
            self.current_lane = lane_code

            # If this is the last lane assignment and we have end_time, extend to end
            if self.end_time and not self._has_lane_after(timestamp):
                lane_fix.to_time = self.end_time
                logging.info(f"Extended lane {lane_code} to folder end time: {self.end_time}")

        self.has_changes = True
        return True

    def start_turn(self, turn_type: str, timestamp: datetime, selected_lane: str = None):
        """
        Start a turn period (TK = Turn Left, TM = Turn Right)
        If already in turn, end current turn first
        """
        import logging
        logging.info(f"LaneManager: start_turn called with turn_type='{turn_type}', selected_lane='{selected_lane}'")
        
        if not self.plate or not self.fileid_folder:
            logging.warning("No plate or fileid_folder set for turn")
            return

        # If already in turn, end it first
        if self.turn_active:
            logging.info("LaneManager: ending current turn before starting new turn")
            self.end_turn(timestamp)
        
        self.turn_start_lane = self.current_lane
        self.turn_active = True

        # End current lane period
        if self.current_lane and self.lane_fixes:
            self.lane_fixes[-1].to_time = timestamp

        # Start turn period with combined code (TK1, TM2, etc.)
        combined_lane = f"{turn_type}{selected_lane}" if selected_lane else turn_type
        lane_fix = LaneFix(
            plate=self.plate,
            from_time=timestamp,
            to_time=timestamp,  # Will be extended
            lane=combined_lane,
            file_id=self.fileid_folder.name
        )
        self.lane_fixes.append(lane_fix)
        self.current_lane = combined_lane

        self.has_changes = True

    def end_turn(self, timestamp: datetime):
        """
        End turn period and resume previous lane
        """
        if not self.turn_active:
            return

        # End turn period
        if self.lane_fixes:
            self.lane_fixes[-1].to_time = timestamp

        # Resume previous lane if exists
        if self.turn_start_lane:
            lane_fix = LaneFix(
                plate=self.lane_fixes[-1].plate,
                from_time=timestamp,
                to_time=timestamp,  # Will be extended
                lane=self.turn_start_lane,
                file_id=self.lane_fixes[-1].file_id
            )
            self.lane_fixes.append(lane_fix)
            self.current_lane = self.turn_start_lane

        # Reset turn state
        self.turn_active = False
        self.turn_start_lane = None

        self.has_changes = True

    def assign_sk(self, timestamp: datetime) -> bool:
        """
        Assign shoulder lane (SK) at given timestamp
        Uses the previous lane number (SK1, SK2, etc.)
        Returns True if successful, False if overlap detected
        """
        if not self.plate or not self.fileid_folder:
            logging.warning("No plate or fileid_folder set for SK assignment")
            return False

        # End any active turn when assigning SK
        if self.turn_active:
            self.end_turn(timestamp)
        # End current period if exists (before checking overlap)
        if self.current_lane and self.lane_fixes:
            # End 1 microsecond before timestamp to avoid overlap
            end_time = timestamp - timedelta(microseconds=1)
            self.lane_fixes[-1].to_time = end_time

        # Check for overlaps after ending current period (exclude ignore periods only)
        if self.check_overlap(timestamp, exclude_ignore=True):
            return False

        # Get previous lane number
        sk_lane = "SK"
        if self.current_lane and self.current_lane in ['1', '2', '3', '4']:
            sk_lane = f"SK{self.current_lane}"

        # Start new SK period
        lane_fix = LaneFix(
            plate=self.plate,
            from_time=timestamp,
            to_time=timestamp,  # Will be extended later
            lane=sk_lane,
            file_id=self.fileid_folder.name,
            ignore=False
        )
        self.lane_fixes.append(lane_fix)
        self.current_lane = sk_lane

        # If this is the last lane assignment and we have end_time, extend to end
        if self.end_time and not self._has_lane_after(timestamp):
            lane_fix.to_time = self.end_time
            logging.info(f"Extended SK lane {sk_lane} to folder end time: {self.end_time}")

        self.has_changes = True
        return True

    def assign_ignore(self, timestamp: datetime) -> bool:
        """
        Assign ignore period at given timestamp
        Returns True if successful, False if overlap detected
        """
        if not self.plate or not self.fileid_folder:
            logging.warning("No plate or fileid_folder set for ignore assignment")
            return False

        # End any active turn when assigning ignore
        if self.turn_active:
            self.end_turn(timestamp)

        # End current period if exists (before checking overlap)
        if self.current_lane and self.lane_fixes:
            # End 1 microsecond before timestamp to avoid overlap
            end_time = timestamp - timedelta(microseconds=1)
            self.lane_fixes[-1].to_time = end_time

        # Check for overlaps after ending current period (exclude ignore periods only)
        if self.check_overlap(timestamp, exclude_ignore=True):
            return False

        # Start new ignore period
        lane_fix = LaneFix(
            plate=self.plate,
            from_time=timestamp,
            to_time=timestamp,  # Will be extended later
            lane="",  # Empty lane for ignore entries
            file_id=self.fileid_folder.name,
            ignore=True
        )
        self.lane_fixes.append(lane_fix)
        # Don't change current_lane for ignore - keep previous lane
        # self.current_lane = "IGNORE"

        # If this is the last lane assignment and we have end_time, extend to end
        if self.end_time and not self._has_lane_after(timestamp):
            lane_fix.to_time = self.end_time
            logging.info(f"Extended ignore period to folder end time: {self.end_time}")

        self.has_changes = True
        return True

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
        """Get all lane fixes"""
        return self.lane_fixes.copy()

    def get_lane_at_timestamp(self, timestamp: datetime) -> str:
        """Get the lane code active at the given timestamp"""
        for fix in self.lane_fixes:
            if fix.from_time is not None and fix.to_time is not None:
                # Skip ignore entries
                if fix.ignore:
                    continue
                if fix.from_time <= timestamp <= fix.to_time:
                    return fix.lane
        return None

    def clear(self):
        """Clear all lane assignments"""
        self.lane_fixes.clear()
        self.current_lane = None
        self.turn_active = False
        self.turn_start_lane = None

    def set_fileid_folder(self, fileid_folder_path: str, plate: str = None):
        """Set the current FileID folder and load lane fixes"""
        from pathlib import Path
        self.fileid_folder = Path(fileid_folder_path)
        self.plate = plate
        self._load_lane_fixes()

    def set_end_time(self, end_time: datetime):
        """Set the end time of the folder for extending lanes"""
        self.end_time = end_time

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
                        plate=row.get('Plate', ''),
                        from_time=from_time,
                        to_time=to_time,
                        lane=row.get('Lane', ''),
                        file_id=self.fileid_folder.name,
                        ignore=row.get('Ignore', '').strip() == '1'
                    )
                    self.lane_fixes.append(lane_fix)

            logging.info(f"Loaded {len(self.lane_fixes)} lane fixes from {lane_fix_path}")

        except Exception as e:
            logging.error(f"Error loading lane fixes from {lane_fix_path}: {e}")
            self.lane_fixes = []

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

                # Write data - format times as HH:MM:SS.sss
                for fix in self.lane_fixes:
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

            logging.info(f"Saved {len(self.lane_fixes)} lane fixes to {lane_fix_path}")
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
            'current_lane': self.current_lane,
            'turn_active': self.turn_active,
            'turn_start_lane': self.turn_start_lane
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'LaneManager':
        """Create LaneManager from dictionary"""
        manager = cls()
        manager.lane_fixes = [LaneFix.from_dict(fix) for fix in data.get('lane_fixes', [])]
        manager.current_lane = data.get('current_lane')
        manager.turn_active = data.get('turn_active', False)
        manager.turn_start_lane = data.get('turn_start_lane')
        return manager