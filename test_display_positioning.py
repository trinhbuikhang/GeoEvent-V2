#!/usr/bin/env python3
"""
Test script to verify event display positioning on timeline widget
"""

import sys
import os
from datetime import datetime, timezone, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.event_model import Event
from app.models.gps_model import GPSData
from app.utils.data_loader import DataLoader
from app.utils.fileid_manager import FileIDFolder

def test_event_display_positioning():
    """Test how events are positioned for display on timeline"""

    print("=" * 80)
    print("EVENT DISPLAY POSITIONING TEST")
    print("=" * 80)

    # Initialize data loader
    data_loader = DataLoader()

    # Load test data
    test_path = "testdata/0D2510020820137700"
    if not os.path.exists(test_path):
        print(f"Test data path not found: {test_path}")
        return

    try:
        # Create FileID folder object
        fileid_folder = FileIDFolder(
            fileid="0D2510020820137700",
            path=test_path,
            has_driveevt=True,
            has_driveiri=True,
            image_count=0,
            last_modified=datetime.now()
        )

        # Load all data using DataLoader
        print("\n1. LOADING DATA...")
        data = data_loader.load_fileid_data(fileid_folder)

        if not data['events'] or not data['gps_data']:
            print("✗ Missing events or GPS data")
            return

        # Find the test event
        test_event = None
        for event in data['events']:
            if event.event_name == "Test Event":
                test_event = event
                break

        if not test_event:
            print("✗ Test event not found")
            return

        print(f"✓ Found test event: {test_event.event_name}")

        # Simulate timeline widget positioning
        print(f"\n2. SIMULATING TIMELINE WIDGET:")

        # Timeline parameters (similar to TimelineWidget defaults)
        zoom_level = 50.0
        timeline_width = 800  # pixels

        # Get view range from metadata
        if not data['metadata'].get('first_image_timestamp') or not data['metadata'].get('last_image_timestamp'):
            print("✗ Missing timeline metadata")
            return

        view_start_time = data['metadata']['first_image_timestamp']
        view_end_time = data['metadata']['last_image_timestamp']
        time_range_seconds = (view_end_time - view_start_time).total_seconds()

        print(f"  View time range: {view_start_time} to {view_end_time}")
        print(f"  Time range: {time_range_seconds:.1f} seconds")
        print(f"  Zoom level: {zoom_level}")
        print(f"  Timeline width: {timeline_width}px")

        # Calculate pixels per second
        pixels_per_second = (timeline_width * zoom_level) / time_range_seconds
        print(f"  Pixels per second: {pixels_per_second:.2f}")

        # Calculate event pixel positions
        event_start_offset = (test_event.start_time - view_start_time).total_seconds()
        event_end_offset = (test_event.end_time - view_start_time).total_seconds()

        event_start_pixel = event_start_offset * pixels_per_second
        event_end_pixel = event_end_offset * pixels_per_second

        print(f"\n3. EVENT PIXEL POSITIONING:")
        print(f"  Event start time: {test_event.start_time}")
        print(f"  Event end time: {test_event.end_time}")
        print(f"  Start offset: {event_start_offset:.1f}s")
        print(f"  End offset: {event_end_offset:.1f}s")
        print(f"  Start pixel: {event_start_pixel:.1f}")
        print(f"  End pixel: {event_end_pixel:.1f}")
        print(f"  Width: {event_end_pixel - event_start_pixel:.1f}px")

        # Check if event is visible
        if event_start_pixel < 0:
            print("  ⚠️  Event starts before visible timeline")
        elif event_start_pixel > timeline_width:
            print("  ⚠️  Event starts after visible timeline")
        else:
            print("  ✓ Event start is within visible timeline")

        if event_end_pixel < 0:
            print("  ⚠️  Event ends before visible timeline")
        elif event_end_pixel > timeline_width:
            print("  ⚠️  Event ends after visible timeline")
        else:
            print("  ✓ Event end is within visible timeline")

        # Test chainage positioning for display
        print(f"\n4. CHAINAGE SCALE POSITIONING:")

        # Use GPS data range for consistent chainage scale (same as timeline widget)
        gps_points = data['gps_data'].points
        if not gps_points:
            print("  ✗ No GPS points")
            return

        min_chainage = min(p.chainage for p in gps_points)
        max_chainage = max(p.chainage for p in gps_points)
        chainage_range = max_chainage - min_chainage

        print(f"  GPS chainage range: {min_chainage:.1f}m to {max_chainage:.1f}m")
        print(f"  Chainage range: {chainage_range:.1f}m")

        # Calculate chainage pixel positions (same as timeline widget)
        # Find time corresponding to event chainage
        event_start_time_from_chainage = None
        event_end_time_from_chainage = None

        for i, point in enumerate(gps_points):
            if point.chainage >= test_event.start_chainage:
                if point.chainage == test_event.start_chainage:
                    event_start_time_from_chainage = point.timestamp
                elif i > 0:
                    prev_point = gps_points[i-1]
                    chainage_diff = point.chainage - prev_point.chainage
                    if chainage_diff > 0:
                        time_diff = (point.timestamp - prev_point.timestamp).total_seconds()
                        ratio = (test_event.start_chainage - prev_point.chainage) / chainage_diff
                        event_start_time_from_chainage = prev_point.timestamp + timedelta(seconds=time_diff * ratio)
                break

        # Same for end chainage
        for i, point in enumerate(gps_points):
            if point.chainage >= test_event.end_chainage:
                if point.chainage == test_event.end_chainage:
                    event_end_time_from_chainage = point.timestamp
                elif i > 0:
                    prev_point = gps_points[i-1]
                    chainage_diff = point.chainage - prev_point.chainage
                    if chainage_diff > 0:
                        time_diff = (point.timestamp - prev_point.timestamp).total_seconds()
                        ratio = (test_event.end_chainage - prev_point.chainage) / chainage_diff
                        event_end_time_from_chainage = prev_point.timestamp + timedelta(seconds=time_diff * ratio)
                break

        if event_start_time_from_chainage and event_end_time_from_chainage:
            chainage_start_offset = (event_start_time_from_chainage - view_start_time).total_seconds()
            chainage_end_offset = (event_end_time_from_chainage - view_start_time).total_seconds()

            chainage_start_pixel = chainage_start_offset * pixels_per_second
            chainage_end_pixel = chainage_end_offset * pixels_per_second

            print(f"  Chainage start time: {event_start_time_from_chainage}")
            print(f"  Chainage end time: {event_end_time_from_chainage}")
            print(f"  Chainage start pixel: {chainage_start_pixel:.1f}")
            print(f"  Chainage end pixel: {chainage_end_pixel:.1f}")
        else:
            print("  ✗ Could not find corresponding times for chainage")
            return

        # Compare time and chainage positioning
        time_chainage_diff_start = abs(event_start_pixel - chainage_start_pixel)
        time_chainage_diff_end = abs(event_end_pixel - chainage_end_pixel)

        print(f"\n5. TIME VS CHAINAGE ALIGNMENT:")
        print(f"  Pixel diff at start: {time_chainage_diff_start:.1f}px")
        print(f"  Pixel diff at end: {time_chainage_diff_end:.1f}px")

        if time_chainage_diff_start < 5 and time_chainage_diff_end < 5:
            print("  ✅ EXCELLENT ALIGNMENT: Event should display perfectly!")
        elif time_chainage_diff_start < 20 and time_chainage_diff_end < 20:
            print("  ✓ GOOD ALIGNMENT: Event should display well")
        else:
            print("  ⚠️  POOR ALIGNMENT: Event positioning may be incorrect")

        print(f"\nTest completed!")

    except Exception as e:
        print(f"✗ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_event_display_positioning()