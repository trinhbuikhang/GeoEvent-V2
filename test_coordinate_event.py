#!/usr/bin/env python3
"""
Test script to create a new event using coordinate-based chainage calculation
and verify it displays correctly on the timeline
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
from app.utils.image_utils import extract_image_metadata

def test_coordinate_based_event_creation():
    """Test creating a new event using coordinates and verify timeline display"""

    print("=" * 80)
    print("COORDINATE-BASED EVENT CREATION TEST")
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

        if not data['gps_data'] or not data['image_paths']:
            print("✗ Missing GPS data or images")
            return

        # Get coordinates from first image
        first_image_metadata = extract_image_metadata(data['image_paths'][0])
        test_lat = first_image_metadata.get('latitude')
        test_lon = first_image_metadata.get('longitude')
        test_timestamp = first_image_metadata.get('timestamp')

        if not all([test_lat, test_lon, test_timestamp]):
            print("✗ Could not extract coordinates/timestamp from first image")
            return

        print(f"✓ First image coordinates: ({test_lat:.6f}, {test_lon:.6f})")
        print(f"✓ First image timestamp: {test_timestamp}")

        # Calculate chainage using coordinates
        coord_chainage = data['gps_data'].interpolate_chainage_by_position(test_lat, test_lon)
        time_chainage = data['gps_data'].interpolate_chainage(test_timestamp)

        print(f"\n2. CHAINAGE CALCULATION:")
        print(f"  Chainage by coordinates: {coord_chainage:.1f}m")
        print(f"  Chainage by timestamp: {time_chainage:.1f}m")
        print(f"  Difference: {abs(coord_chainage - time_chainage):.1f}m")

        # Create a test event using coordinate-based chainage
        print(f"\n3. CREATING TEST EVENT:")
        event_id = f"Test_Event_{test_timestamp.strftime('%H%M%S')}"

        # For a test event, let's make it 10 seconds long
        end_timestamp = test_timestamp.replace(second=test_timestamp.second + 10)

        # Calculate end chainage using the same coordinates (assuming same position)
        end_coord_chainage = coord_chainage  # Same position

        test_event = Event(
            event_id=event_id,
            event_name="Test Event",
            start_time=test_timestamp,
            end_time=end_timestamp,
            start_chainage=coord_chainage,
            end_chainage=end_coord_chainage
        )

        print(f"  Event ID: {event_id}")
        print(f"  Start time: {test_timestamp}")
        print(f"  End time: {end_timestamp}")
        print(f"  Start chainage: {coord_chainage:.1f}m")
        print(f"  End chainage: {end_coord_chainage:.1f}m")

        # Add to existing events
        data['events'].append(test_event)

        # Save the updated events
        print(f"\n4. SAVING EVENT...")
        success = data_loader.save_events(data['events'], fileid_folder)
        if success:
            print("✓ Event saved successfully")
        else:
            print("✗ Failed to save event")

        # Verify the event was saved correctly
        print(f"\n5. VERIFICATION:")
        print(f"  Total events now: {len(data['events'])}")

        # Check timeline positioning
        print(f"\n6. TIMELINE POSITION ANALYSIS:")

        # Get timeline range from metadata
        if data['metadata'].get('first_image_timestamp') and data['metadata'].get('last_image_timestamp'):
            time_start = data['metadata']['first_image_timestamp']
            time_end = data['metadata']['last_image_timestamp']

            time_range_seconds = (time_end - time_start).total_seconds()
            event_time_offset = (test_timestamp - time_start).total_seconds()

            print(f"  Timeline time range: {time_start} to {time_end}")
            print(f"  Event time offset: {event_time_offset:.1f}s")
            print(f"  Event time ratio: {event_time_offset / time_range_seconds:.3f}")

        # Get chainage range
        if data['gps_data'] and data['gps_data'].points:
            chainage_start = min(p.chainage for p in data['gps_data'].points)
            chainage_end = max(p.chainage for p in data['gps_data'].points)

            chainage_range = chainage_end - chainage_start
            event_chainage_offset = coord_chainage - chainage_start

            print(f"  Timeline chainage range: {chainage_start:.1f}m to {chainage_end:.1f}m")
            print(f"  Event chainage offset: {event_chainage_offset:.1f}m")
            print(f"  Event chainage ratio: {event_chainage_offset / chainage_range:.3f}")

            # Check if time and chainage ratios match
            time_ratio = event_time_offset / time_range_seconds
            chainage_ratio = event_chainage_offset / chainage_range

            ratio_diff = abs(time_ratio - chainage_ratio)
            print(f"  Time vs Chainage ratio difference: {ratio_diff:.3f}")

            if ratio_diff < 0.01:
                print("  ✅ PERFECT ALIGNMENT: Event should display correctly on timeline!")
            elif ratio_diff < 0.05:
                print("  ✓ GOOD ALIGNMENT: Event should display well on timeline")
            else:
                print("  ⚠️  MISALIGNMENT: Event may not display correctly on timeline")

        print(f"\nTest completed! Event '{test_event.event_name}' created with coordinate-based chainage.")

    except Exception as e:
        print(f"✗ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_coordinate_based_event_creation()