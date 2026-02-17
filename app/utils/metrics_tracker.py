"""
Application Metrics Tracker - Track user interactions and performance
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path
import json


@dataclass
class MetricsSession:
    """Container for single session metrics"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # Navigation metrics
    images_viewed: int = 0
    next_clicks: int = 0
    prev_clicks: int = 0
    slider_changes: int = 0
    timeline_clicks: int = 0
    
    # Lane assignment metrics
    lane_assignments: int = 0
    lane_changes: int = 0
    
    # Event metrics
    events_edited: int = 0
    events_created: int = 0
    
    # FileID operations
    fileid_loads: int = 0
    fileid_saves: int = 0
    
    # Auto-play metrics
    autoplay_sessions: int = 0
    autoplay_duration: timedelta = field(default_factory=lambda: timedelta(0))
    
    # Performance metrics
    avg_image_load_time: float = 0.0
    avg_fileid_load_time: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "images_viewed": self.images_viewed,
            "next_clicks": self.next_clicks,
            "prev_clicks": self.prev_clicks,
            "slider_changes": self.slider_changes,
            "timeline_clicks": self.timeline_clicks,
            "lane_assignments": self.lane_assignments,
            "lane_changes": self.lane_changes,
            "events_edited": self.events_edited,
            "events_created": self.events_created,
            "fileid_loads": self.fileid_loads,
            "fileid_saves": self.fileid_saves,
            "autoplay_sessions": self.autoplay_sessions,
            "autoplay_duration": str(self.autoplay_duration),
            "avg_image_load_time": self.avg_image_load_time,
            "avg_fileid_load_time": self.avg_fileid_load_time
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'MetricsSession':
        """Create from dictionary"""
        session = MetricsSession(
            session_id=data["session_id"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None
        )
        
        session.images_viewed = data.get("images_viewed", 0)
        session.next_clicks = data.get("next_clicks", 0)
        session.prev_clicks = data.get("prev_clicks", 0)
        session.slider_changes = data.get("slider_changes", 0)
        session.timeline_clicks = data.get("timeline_clicks", 0)
        session.lane_assignments = data.get("lane_assignments", 0)
        session.lane_changes = data.get("lane_changes", 0)
        session.events_edited = data.get("events_edited", 0)
        session.events_created = data.get("events_created", 0)
        session.fileid_loads = data.get("fileid_loads", 0)
        session.fileid_saves = data.get("fileid_saves", 0)
        session.autoplay_sessions = data.get("autoplay_sessions", 0)
        
        # Parse duration string back to timedelta (supports decimals in seconds, e.g. "0:0:31.023448")
        duration_str = data.get("autoplay_duration", "0:00:00")
        try:
            parts = [float(x) for x in reversed(duration_str.split(":"))]
            session.autoplay_duration = timedelta(seconds=sum(
                parts[i] * 60 ** i for i in range(len(parts))
            ))
        except (ValueError, TypeError):
            session.autoplay_duration = timedelta(0)
        
        session.avg_image_load_time = data.get("avg_image_load_time", 0.0)
        session.avg_fileid_load_time = data.get("avg_fileid_load_time", 0.0)
        
        return session


class MetricsTracker:
    """
    Track application metrics for usage analysis and performance monitoring
    
    RESPONSIBILITIES:
    - Track user interactions (navigation, edits, etc.)
    - Monitor performance metrics (load times)
    - Persist metrics to disk
    - Generate usage reports
    """
    
    def __init__(self, metrics_file: Optional[Path] = None):
        """
        Initialize metrics tracker
        
        Args:
            metrics_file: Path to metrics JSON file (default: logs/metrics.json)
        """
        self.metrics_file = metrics_file or Path("logs/metrics.json")
        self.current_session: Optional[MetricsSession] = None
        self.sessions: List[MetricsSession] = []
        
        # Performance tracking
        self._image_load_times: List[float] = []
        self._fileid_load_times: List[float] = []
        self._autoplay_start: Optional[datetime] = None
        
        self._load_metrics()
        logging.info(f"MetricsTracker: Initialized with {len(self.sessions)} previous sessions")
    
    def start_session(self):
        """Start new tracking session"""
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.current_session = MetricsSession(
            session_id=session_id,
            start_time=datetime.now()
        )
        logging.info(f"MetricsTracker: Started session {session_id}")
    
    def end_session(self):
        """End current session and save"""
        if self.current_session:
            self.current_session.end_time = datetime.now()
            
            # Calculate averages
            if self._image_load_times:
                self.current_session.avg_image_load_time = sum(self._image_load_times) / len(self._image_load_times)
            
            if self._fileid_load_times:
                self.current_session.avg_fileid_load_time = sum(self._fileid_load_times) / len(self._fileid_load_times)
            
            # Add to sessions list
            self.sessions.append(self.current_session)
            
            # Save to disk
            self._save_metrics()
            
            logging.info(f"MetricsTracker: Ended session {self.current_session.session_id}")
            self.current_session = None
    
    # Navigation tracking
    
    def track_image_viewed(self):
        """Track image view"""
        if self.current_session:
            self.current_session.images_viewed += 1
    
    def track_next_click(self):
        """Track next button click"""
        if self.current_session:
            self.current_session.next_clicks += 1
    
    def track_prev_click(self):
        """Track previous button click"""
        if self.current_session:
            self.current_session.prev_clicks += 1
    
    def track_slider_change(self):
        """Track slider change"""
        if self.current_session:
            self.current_session.slider_changes += 1
    
    def track_timeline_click(self):
        """Track timeline click"""
        if self.current_session:
            self.current_session.timeline_clicks += 1
    
    # Lane tracking
    
    def track_lane_assignment(self):
        """Track lane button assignment"""
        if self.current_session:
            self.current_session.lane_assignments += 1
    
    def track_lane_change(self):
        """Track lane change (assignment on already-assigned image)"""
        if self.current_session:
            self.current_session.lane_changes += 1
    
    # Event tracking
    
    def track_event_edit(self):
        """Track event edit"""
        if self.current_session:
            self.current_session.events_edited += 1
    
    def track_event_create(self):
        """Track new event creation"""
        if self.current_session:
            self.current_session.events_created += 1
    
    # FileID tracking
    
    def track_fileid_load(self, load_time: float):
        """
        Track FileID load operation
        
        Args:
            load_time: Load time in seconds
        """
        if self.current_session:
            self.current_session.fileid_loads += 1
            self._fileid_load_times.append(load_time)
    
    def track_fileid_save(self):
        """Track FileID save operation"""
        if self.current_session:
            self.current_session.fileid_saves += 1
    
    # Auto-play tracking
    
    def start_autoplay(self):
        """Start tracking auto-play session"""
        self._autoplay_start = datetime.now()
        if self.current_session:
            self.current_session.autoplay_sessions += 1
    
    def stop_autoplay(self):
        """Stop tracking auto-play session"""
        if self._autoplay_start and self.current_session:
            duration = datetime.now() - self._autoplay_start
            self.current_session.autoplay_duration += duration
            self._autoplay_start = None
    
    # Performance tracking
    
    def track_image_load_time(self, load_time: float):
        """
        Track image load time
        
        Args:
            load_time: Load time in seconds
        """
        self._image_load_times.append(load_time)
    
    # Persistence
    
    def _load_metrics(self):
        """Load metrics from disk"""
        try:
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.sessions = [MetricsSession.from_dict(s) for s in data.get("sessions", [])]
                logging.info(f"MetricsTracker: Loaded {len(self.sessions)} sessions from {self.metrics_file}")
        except Exception as e:
            logging.error(f"MetricsTracker: Failed to load metrics: {e}", exc_info=True)
    
    def _save_metrics(self):
        """Save metrics to disk"""
        try:
            # Ensure directory exists
            self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert sessions to dict
            data = {
                "sessions": [s.to_dict() for s in self.sessions]
            }
            
            # Write to file
            with open(self.metrics_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logging.info(f"MetricsTracker: Saved {len(self.sessions)} sessions to {self.metrics_file}")
        except Exception as e:
            logging.error(f"MetricsTracker: Failed to save metrics: {e}", exc_info=True)
    
    # Reporting
    
    def get_session_summary(self) -> Dict:
        """Get summary of current session"""
        if not self.current_session:
            return {}
        
        return {
            "Session Duration": str(datetime.now() - self.current_session.start_time),
            "Images Viewed": self.current_session.images_viewed,
            "Navigation Actions": (
                self.current_session.next_clicks + 
                self.current_session.prev_clicks +
                self.current_session.slider_changes +
                self.current_session.timeline_clicks
            ),
            "Lane Operations": (
                self.current_session.lane_assignments +
                self.current_session.lane_changes
            ),
            "Event Operations": (
                self.current_session.events_edited +
                self.current_session.events_created
            ),
            "FileID Operations": (
                self.current_session.fileid_loads +
                self.current_session.fileid_saves
            ),
            "Auto-play Sessions": self.current_session.autoplay_sessions,
            "Total Auto-play Time": str(self.current_session.autoplay_duration)
        }
    
    def get_all_sessions_summary(self) -> Dict:
        """Get summary across all sessions"""
        total_images = sum(s.images_viewed for s in self.sessions)
        total_nav = sum(
            s.next_clicks + s.prev_clicks + s.slider_changes + s.timeline_clicks 
            for s in self.sessions
        )
        total_lanes = sum(s.lane_assignments + s.lane_changes for s in self.sessions)
        total_events = sum(s.events_edited + s.events_created for s in self.sessions)
        
        return {
            "Total Sessions": len(self.sessions),
            "Total Images Viewed": total_images,
            "Total Navigation Actions": total_nav,
            "Total Lane Operations": total_lanes,
            "Total Event Operations": total_events
        }
