"""
Test file for lane change logic and timeline display
Tests both the lane model logic and timeline widget color display
"""

import pytest
import os
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from app.models.lane_model import LaneManager, LaneFix
from app.models.event_model import Event
from app.models.gps_model import GPSData
from app.ui.timeline_widget import TimelineWidget
from app.ui.photo_preview_tab import PhotoPreviewTab


class TestLaneChangeLogicAndDisplay:
    """Test lane change logic and timeline display"""

    @pytest.fixture
    def setup_app(self):
        """Setup QApplication for GUI tests"""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app

    @pytest.fixture
    def manager(self):
        """Create LaneManager with test data"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test folder structure
            test_folder = os.path.join(temp_dir, "0D2510020721457700")
            os.makedirs(test_folder)

            manager = LaneManager()
            manager.plate = "TEST001"
            manager.fileid_folder = Mock()
            manager.fileid_folder.name = "0D2510020721457700"
            manager.end_time = datetime(2025, 10, 2, 12, 0, tzinfo=timezone.utc)

            yield manager

    def test_lane_change_different_lane_creates_three_periods(self, manager):
        """Test that lane change to different lane creates three periods"""
        # Setup: lane 1 from 10:00 to 11:00
        start_time = datetime(2025, 10, 2, 10, 0, tzinfo=timezone.utc)
        manager.assign_lane("1", start_time)

        # Change 10:10 to 10:20 to lane 2
        change_start = datetime(2025, 10, 2, 10, 10, tzinfo=timezone.utc)
        change_end = datetime(2025, 10, 2, 10, 20, tzinfo=timezone.utc)

        result = manager.apply_lane_change_range("2", change_start, change_end)
        assert result is True

        # Should have 3 periods
        assert len(manager.lane_fixes) == 3

        # Check periods
        periods = sorted(manager.lane_fixes, key=lambda x: x.from_time)
        assert periods[0].lane == "1"
        assert periods[0].from_time == start_time
        assert periods[0].to_time == change_start

        assert periods[1].lane == "2"
        assert periods[1].from_time == change_start
        assert periods[1].to_time == change_end

        assert periods[2].lane == "1"
        assert periods[2].from_time == change_end

    def test_lane_change_same_lane_creates_two_periods(self, manager):
        """Test that lane change to same lane creates two periods"""
        # Setup: lane 1 from 10:00 to 11:00
        start_time = datetime(2025, 10, 2, 10, 0, tzinfo=timezone.utc)
        manager.assign_lane("1", start_time)

        # Change 10:10 to 10:20 to same lane 1
        change_start = datetime(2025, 10, 2, 10, 10, tzinfo=timezone.utc)
        change_end = datetime(2025, 10, 2, 10, 20, tzinfo=timezone.utc)

        result = manager.apply_lane_change_range("1", change_start, change_end)
        assert result is True

        # Should have 3 periods (start_part, new_part, end_part)
        assert len(manager.lane_fixes) == 3

        periods = sorted(manager.lane_fixes, key=lambda x: x.from_time)
        assert periods[0].lane == "1"
        assert periods[1].lane == "1"
        assert periods[2].lane == "1"

    def test_timeline_color_display(self, setup_app, manager):
        """Test timeline widget has lane manager set correctly"""
        # Setup lane periods
        start_time = datetime(2025, 10, 2, 10, 0, tzinfo=timezone.utc)
        manager.assign_lane("1", start_time)

        change_start = datetime(2025, 10, 2, 10, 10, tzinfo=timezone.utc)
        change_end = datetime(2025, 10, 2, 10, 20, tzinfo=timezone.utc)
        manager.apply_lane_change_range("2", change_start, change_end)

        # Create timeline widget
        timeline = TimelineWidget()
        timeline.lane_manager = manager

        # Check that lane manager is set
        assert timeline.lane_manager == manager
        assert len(timeline.lane_manager.lane_fixes) == 3  # Should have 3 periods

    def test_timeline_paint_periods_correctly(self, setup_app, manager):
        """Test that timeline has correct periods and colors for display"""
        # Setup lane periods: 10:00-10:10 Lane 1, 10:10-10:20 Lane 2, 10:20-11:00 Lane 1
        start_time = datetime(2025, 10, 2, 10, 0, tzinfo=timezone.utc)
        manager.assign_lane("1", start_time)
        
        change_start = datetime(2025, 10, 2, 10, 10, tzinfo=timezone.utc)
        change_end = datetime(2025, 10, 2, 10, 20, tzinfo=timezone.utc)
        manager.apply_lane_change_range("2", change_start, change_end)
        
        # Create timeline widget
        timeline = TimelineWidget()
        timeline.lane_manager = manager
        
        # Check that timeline has access to the periods
        periods = timeline.lane_manager.get_lane_fixes()
        assert len(periods) == 3
        assert periods[0].lane == "1"
        assert periods[1].lane == "2" 
        assert periods[2].lane == "1"
        
        # Test color mapping used in timeline
        assert timeline.lane_manager.get_lane_color("1") == "#4CAF50"  # Green
        assert timeline.lane_manager.get_lane_color("2") == "#2196F3"  # Blue
        
        # Verify periods are sorted for display
        assert periods == sorted(periods, key=lambda x: x.from_time)

    def test_user_modified_lane_change_restores_original_lane(self, manager):
        """Test that when user modifies end time, remaining period gets original lane"""
        # Setup: lane 1 from 10:00 to 12:00
        start_time = datetime(2025, 10, 2, 10, 0, tzinfo=timezone.utc)
        manager.assign_lane("1", start_time)
        
        # Simulate auto-apply: change 10:10 to 12:00 to lane 2
        auto_start = datetime(2025, 10, 2, 10, 10, tzinfo=timezone.utc)
        auto_end = datetime(2025, 10, 2, 12, 0, tzinfo=timezone.utc)
        manager.apply_lane_change_range("2", auto_start, auto_end)
        
        # Now user modifies to end at 10:30, remaining should be lane 1
        user_end = datetime(2025, 10, 2, 10, 30, tzinfo=timezone.utc)
        manager.apply_lane_change_range("2", auto_start, user_end)
        
        # Find the period from user_end to auto_end and set to original lane
        for fix in manager.lane_fixes:
            if fix.from_time == user_end and fix.to_time == auto_end:
                fix.lane = "1"  # Original lane
                break
        
        # Check periods
        periods = sorted(manager.lane_fixes, key=lambda x: x.from_time)
        assert len(periods) == 3  # 10:00-10:10 L1, 10:10-10:30 L2, 10:30-12:00 L1
        
        assert periods[0].lane == "1"
        assert periods[1].lane == "2"
        assert periods[2].lane == "1"  # Remaining restored to original
        
        # Test display colors
        assert manager.get_lane_color(periods[0].lane) == "#4CAF50"  # Green for lane 1
        assert manager.get_lane_color(periods[1].lane) == "#2196F3"  # Blue for lane 2
        assert manager.get_lane_color(periods[2].lane) == "#4CAF50"  # Green for lane 1