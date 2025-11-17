"""
Lane assignment data model for GeoEvent application
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

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

    def assign_lane(self, lane_code: str, timestamp: datetime, plate: str, file_id: str) -> bool:
        """
        Assign lane at given timestamp
        Returns True if successful, False if overlap detected
        """
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
                plate=plate,
                from_time=timestamp,
                to_time=timestamp,  # Will be extended later
                lane=lane_code,
                file_id=file_id
            )
            self.lane_fixes.append(lane_fix)
            self.current_lane = lane_code

        return True

    def start_turn(self, turn_type: str, timestamp: datetime, plate: str, file_id: str, selected_lane: str = None):
        """
        Start a turn period (TK = Turn Left, TM = Turn Right)
        If already in turn, end current turn first
        """
        import logging
        logging.info(f"LaneManager: start_turn called with turn_type='{turn_type}', selected_lane='{selected_lane}'")
        
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
            plate=plate,
            from_time=timestamp,
            to_time=timestamp,  # Will be extended
            lane=combined_lane,
            file_id=file_id
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