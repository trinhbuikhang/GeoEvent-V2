#!/usr/bin/env python3
"""
Test script to verify event positioning on timeline
"""

import sys
import os
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.event_model import Event
from app.models.gps_model import GPSData
from app.utils.data_loader import DataLoader
from app.utils.fileid_manager import FileIDFolder

def test_timeline_positioning():
    """Test event positioning calculations on timeline"""

    print("=" * 80)
    print("TIMELINE POSITIONING TEST")
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

        # Find the test event we created
        test_event = None
        for event in data['events']:
            if event.event_name == "Test Event":
                test_event = event
                break

        if not test_event:
            print("✗ Test event not found")
            return

        print(f"✓ Found test event: {test_event.event_name}")
        print(f"  Start time: {test_event.start_time}")
        print(f"  End time: {test_event.end_time}")
        print(f"  Start chainage: {test_event.start_chainage:.1f}m")
        print(f"  End chainage: {test_event.end_chainage:.1f}m")

        # Get timeline ranges from metadata
        if not data['metadata'].get('first_image_timestamp') or not data['metadata'].get('last_image_timestamp'):
            print("✗ Missing timeline metadata")
            return

        time_start = data['metadata']['first_image_timestamp']
        time_end = data['metadata']['last_image_timestamp']
        time_range = (time_end - time_start).total_seconds()

        print(f"\n2. TIMELINE TIME RANGE:")
        print(f"  Start: {time_start}")
        print(f"  End: {time_end}")
        print(f"  Duration: {time_range:.1f} seconds")

        # Calculate event time position
        event_time_start_offset = (test_event.start_time - time_start).total_seconds()
        event_time_end_offset = (test_event.end_time - time_start).total_seconds()

        event_time_start_ratio = event_time_start_offset / time_range
        event_time_end_ratio = event_time_end_offset / time_range

        print(f"\n3. EVENT TIME POSITION:")
        print(f"  Start offset: {event_time_start_offset:.1f}s ({event_time_start_ratio:.3f})")
        print(f"  End offset: {event_time_end_offset:.1f}s ({event_time_end_ratio:.3f})")

        # Get chainage range from GPS data
        gps_points = data['gps_data'].points
        if not gps_points:
            print("✗ No GPS points")
            return

        chainage_min = min(p.chainage for p in gps_points)
        chainage_max = max(p.chainage for p in gps_points)
        chainage_range = chainage_max - chainage_min

        print(f"\n4. GPS CHAINAGE RANGE:")
        print(f"  Min: {chainage_min:.1f}m")
        print(f"  Max: {chainage_max:.1f}m")
        print(f"  Range: {chainage_range:.1f}m")

        # Calculate event chainage position
        event_chainage_start_offset = test_event.start_chainage - chainage_min
        event_chainage_end_offset = test_event.end_chainage - chainage_min

        event_chainage_start_ratio = event_chainage_start_offset / chainage_range
        event_chainage_end_ratio = event_chainage_end_offset / chainage_range

        print(f"\n5. EVENT CHAINAGE POSITION:")
        print(f"  Start offset: {event_chainage_start_offset:.1f}m ({event_chainage_start_ratio:.3f})")
        print(f"  End offset: {event_chainage_end_offset:.1f}m ({event_chainage_end_ratio:.3f})")

        # Compare ratios
        time_chainage_diff_start = abs(event_time_start_ratio - event_chainage_start_ratio)
        time_chainage_diff_end = abs(event_time_end_ratio - event_chainage_end_ratio)

        print(f"\n6. ALIGNMENT ANALYSIS:")
        print(f"  Time vs Chainage ratio diff (start): {time_chainage_diff_start:.3f}")
        print(f"  Time vs Chainage ratio diff (end): {time_chainage_diff_end:.3f}")

        if time_chainage_diff_start < 0.01 and time_chainage_diff_end < 0.01:
            print("  ✅ PERFECT ALIGNMENT: Event should display correctly!")
        elif time_chainage_diff_start < 0.05 and time_chainage_diff_end < 0.05:
            print("  ✓ GOOD ALIGNMENT: Event should display well")
        else:
            print("  ⚠️  MISALIGNMENT: Event positioning may be incorrect")

        # Test timeline widget positioning calculations
        print(f"\n7. TIMELINE WIDGET CALCULATIONS:")

        # Simulate timeline widget calculations
        zoom_level = 50.0  # Default zoom
        timeline_width = 800  # Assume 800px width

        pixels_per_second = (timeline_width * zoom_level) / time_range
        print(f"  Pixels per second: {pixels_per_second:.2f}")

        # Calculate pixel positions
        start_pixel = event_time_start_offset * pixels_per_second
        end_pixel = event_time_end_offset * pixels_per_second

        print(f"  Event start pixel: {start_pixel:.1f}")
        print(f"  Event end pixel: {end_pixel:.1f}")
        print(f"  Event width: {end_pixel - start_pixel:.1f}px")

        print(f"\nTest completed!")

    except Exception as e:
        print(f"✗ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_timeline_positioning()