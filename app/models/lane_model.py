"""
Lane assignment data model for GeoEvent application
"""

from dataclasses import dataclass
from datetime import datetime, timezone
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
    lane: str  # '1'|'2'|'3'|'4'|'-1'|'TK1'|'TM2'...
    file_id: str

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'plate': self.plate,
            'from_time': self.from_time.isoformat(),
            'to_time': self.to_time.isoformat(),
            'lane': self.lane,
            'file_id': self.file_id
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'LaneFix':
        """Create LaneFix from dictionary"""
        return cls(
            plate=data['plate'],
            from_time=datetime.fromisoformat(data['from_time']),
            to_time=datetime.fromisoformat(data['to_time']),
            lane=data['lane'],
            file_id=data['file_id']
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

    def assign_lane(self, lane_code: str, timestamp: datetime) -> bool:
        """
        Assign lane at given timestamp
        Returns True if successful, False if overlap detected
        """
        if not self.plate or not self.fileid_folder:
            logging.warning("No plate or fileid_folder set for lane assignment")
            return False

        # Check for overlaps
        if self.check_overlap(timestamp):
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
            lane_fix = LaneFix(
                plate=self.plate,
                from_time=timestamp,
                to_time=timestamp,  # Will be extended later
                lane=lane_code,
                file_id=self.fileid_folder.name
            )
            self.lane_fixes.append(lane_fix)
            self.current_lane = lane_code

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

    def check_overlap(self, timestamp: datetime) -> bool:
        """
        Check if timestamp overlaps with existing lane periods
        """
        for fix in self.lane_fixes:
            if fix.from_time is not None and fix.to_time is not None:
                if fix.from_time <= timestamp <= fix.to_time:
                    return True
        return False

    def get_lane_fixes(self) -> List[LaneFix]:
        """Get all lane fixes"""
        return self.lane_fixes.copy()

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
                    # Parse timestamps - format is HH:MM:SS.sss (no date)
                    try:
                        # Assume current date for time-only format
                        today = datetime.now(timezone.utc).date()
                        from_time_str = f"{today} {row['From']}"
                        to_time_str = f"{today} {row['To']}"
                        
                        from_time = datetime.strptime(from_time_str, '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=timezone.utc)
                        to_time = datetime.strptime(to_time_str, '%Y-%m-%d %H:%M:%S.%f').replace(tzinfo=timezone.utc)
                    except ValueError:
                        # Try without microseconds
                        from_time_str = f"{today} {row['From']}"
                        to_time_str = f"{today} {row['To']}"
                        from_time = datetime.strptime(from_time_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
                        to_time = datetime.strptime(to_time_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)

                    lane_fix = LaneFix(
                        plate=row.get('Plate', ''),
                        from_time=from_time,
                        to_time=to_time,
                        lane=row.get('Lane', ''),
                        file_id=self.fileid_folder.name
                    )
                    self.lane_fixes.append(lane_fix)

            logging.info(f"Loaded {len(self.lane_fixes)} lane fixes from {lane_fix_path}")

        except Exception as e:
            logging.error(f"Error loading lane fixes from {lane_fix_path}: {e}")
            self.lane_fixes = []

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
                        '',  # Ignore
                        '',  # RegionID
                        '',  # RoadID
                        'N'  # Travel direction
                    ])

            logging.info(f"Saved {len(self.lane_fixes)} lane fixes to {lane_fix_path}")
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
            '-1': '#7F8C8D', # Ignore - Dark Gray
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