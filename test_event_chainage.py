#!/usr/bin/env python3
"""
Test script to analyze event chainage calculation and timeline rendering
"""

import sys
import os
from datetime import datetime, timezone
from typing import List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.event_model import Event
from app.models.gps_model import GPSData
from app.utils.data_loader import DataLoader
from app.utils.fileid_manager import FileIDFolder
from app.utils.image_utils import extract_image_metadata

def test_event_chainage_analysis():
    """Test and analyze event chainage calculations"""

    print("=" * 80)
    print("EVENT CHAINAGE ANALYSIS TEST")
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
        print("\n1. LOADING ALL DATA...")
        data = data_loader.load_fileid_data(fileid_folder)

        gps_data = data['gps_data']
        events = data['events']
        image_paths = data['image_paths']

        print(f"✓ Loaded GPS data: {gps_data is not None}")
        if gps_data and gps_data.points:
            print(f"  GPS points: {len(gps_data.points)}")
            print(f"  First GPS point: {gps_data.points[0]}")
            print(f"  Last GPS point: {gps_data.points[-1]}")

        print(f"✓ Loaded {len(events)} events")
        print(f"✓ Loaded {len(image_paths)} images")

        # Extract image metadata
        first_image_meta = None
        last_image_meta = None
        if image_paths:
            first_image_meta = extract_image_metadata(image_paths[0])
            last_image_meta = extract_image_metadata(image_paths[-1])
            print(f"✓ First image: {os.path.basename(image_paths[0])}")
            print(f"  Timestamp: {first_image_meta.get('timestamp')}")
            print(f"  Coordinates: ({first_image_meta.get('latitude')}, {first_image_meta.get('longitude')})")
            print(f"✓ Last image: {os.path.basename(image_paths[-1])}")
            print(f"  Timestamp: {last_image_meta.get('timestamp')}")
            print(f"  Coordinates: ({last_image_meta.get('latitude')}, {last_image_meta.get('longitude')})")

        # Analyze each event
        print("\n2. ANALYZING EVENTS...")
        print("-" * 80)

        for i, event in enumerate(events, 1):
            print(f"\nEVENT {i}: {event.event_name}")
            print("-" * 40)

            # Event time information
            print("TIME INFORMATION:")
            print(f"  Start time: {event.start_time}")
            print(f"  End time: {event.end_time}")
            duration = (event.end_time - event.start_time).total_seconds()
            print(f"  Duration: {duration:.1f} seconds")

            # Chainage information
            print("\nCHAINAGE INFORMATION:")
            print(f"  Start chainage: {event.start_chainage:.1f}m")
            print(f"  End chainage: {event.end_chainage:.1f}m")
            chainage_length = event.end_chainage - event.start_chainage
            print(f"  Chainage length: {chainage_length:.1f}m")

            # GPS-based chainage verification
            if gps_data:
                gps_start_chainage = gps_data.interpolate_chainage(event.start_time)
                gps_end_chainage = gps_data.interpolate_chainage(event.end_time)

                print("\nGPS VERIFICATION:")
                print(f"  GPS start chainage: {gps_start_chainage:.1f}m")
                print(f"  GPS end chainage: {gps_end_chainage:.1f}m")

                if gps_start_chainage is not None and gps_end_chainage is not None:
                    gps_length = gps_end_chainage - gps_start_chainage
                    print(f"  GPS chainage length: {gps_length:.1f}m")

                    # Compare with stored chainage
                    start_diff = abs(event.start_chainage - gps_start_chainage)
                    end_diff = abs(event.end_chainage - gps_end_chainage)
                    print(f"  Start chainage difference: {start_diff:.1f}m")
                    print(f"  End chainage difference: {end_diff:.1f}m")

                    if start_diff > 10 or end_diff > 10:
                        print("  ⚠️  LARGE CHAINAGE DIFFERENCE DETECTED!")
                else:
                    print("  ⚠️  Could not interpolate chainage from GPS data")

            # Timeline rendering analysis
            print("\nTIMELINE RENDERING ANALYSIS:")
            if first_image_meta and last_image_meta:
                first_time = first_image_meta.get('timestamp')
                last_time = last_image_meta.get('timestamp')

                if first_time and last_time:
                    total_time_range = (last_time - first_time).total_seconds()

                    start_offset = (event.start_time - first_time).total_seconds()
                    end_offset = (event.end_time - first_time).total_seconds()

                    start_ratio = start_offset / total_time_range if total_time_range > 0 else 0
                    end_ratio = end_offset / total_time_range if total_time_range > 0 else 0

                    print(f"  Time range: {first_time} to {last_time}")
                    print(f"  Event start ratio: {start_ratio:.3f} ({start_offset:.1f}s from start)")
                    print(f"  Event end ratio: {end_ratio:.3f} ({end_offset:.1f}s from start)")

                    # Chainage ratio
                    if gps_data:
                        first_coords = (first_image_meta.get('latitude'), first_image_meta.get('longitude'))
                        last_coords = (last_image_meta.get('latitude'), last_image_meta.get('longitude'))

                        if first_coords[0] and first_coords[1] and last_coords[0] and last_coords[1]:
                            first_chainage = gps_data.interpolate_chainage_by_position(first_coords[0], first_coords[1])
                            last_chainage = gps_data.interpolate_chainage_by_position(last_coords[0], last_coords[1])

                            if first_chainage is not None and last_chainage is not None:
                                total_chainage_range = last_chainage - first_chainage

                                event_start_chainage_ratio = (event.start_chainage - first_chainage) / total_chainage_range if total_chainage_range > 0 else 0
                                event_end_chainage_ratio = (event.end_chainage - first_chainage) / total_chainage_range if total_chainage_range > 0 else 0

                                print(f"  Chainage range: {first_chainage:.1f}m to {last_chainage:.1f}m")
                                print(f"  Event start chainage ratio: {event_start_chainage_ratio:.3f}")
                                print(f"  Event end chainage ratio: {event_end_chainage_ratio:.3f}")

                                # Compare time vs chainage ratios
                                time_chainage_diff_start = abs(start_ratio - event_start_chainage_ratio)
                                time_chainage_diff_end = abs(end_ratio - event_end_chainage_ratio)

                                print(f"  Time vs Chainage ratio diff (start): {time_chainage_diff_start:.3f}")
                                print(f"  Time vs Chainage ratio diff (end): {time_chainage_diff_end:.3f}")

                                if time_chainage_diff_start > 0.1 or time_chainage_diff_end > 0.1:
                                    print("  ⚠️  SIGNIFICANT TIME-CHAINAGE MISMATCH!")

        # Test coordinate-based event creation
        print("\n3. TESTING COORDINATE-BASED EVENT CREATION...")
        if data['gps_data'] and data['image_paths']:
            # Get coordinates from first image
            first_image_metadata = extract_image_metadata(data['image_paths'][0])
            test_lat = first_image_metadata.get('latitude')
            test_lon = first_image_metadata.get('longitude')
            test_timestamp = first_image_metadata.get('timestamp')
            
            if test_lat is not None and test_lon is not None and test_timestamp is not None:
                print(f"  Using coordinates from first image: ({test_lat:.6f}, {test_lon:.6f})")
                print(f"  Image timestamp: {test_timestamp}")
                
                # Calculate chainage using coordinates
                coord_chainage = data['gps_data'].interpolate_chainage_by_position(test_lat, test_lon)
                time_chainage = data['gps_data'].interpolate_chainage(test_timestamp)
                
                print(f"  Chainage by coordinates: {coord_chainage:.1f}m")
                print(f"  Chainage by timestamp: {time_chainage:.1f}m")
                
                if coord_chainage is not None and time_chainage is not None:
                    difference = abs(coord_chainage - time_chainage)
                    print(f"  Difference: {difference:.1f}m")
                    
                    if difference < 1.0:
                        print("  ✓ COORDINATE-BASED CHAINAGE CALCULATION WORKS PERFECTLY!")
                    elif difference < 10.0:
                        print("  ✓ COORDINATE-BASED CHAINAGE CALCULATION WORKS WELL!")
                    else:
                        print("  ⚠️  COORDINATE-BASED CHAINAGE STILL HAS ISSUES")
                else:
                    print("  ✗ Could not calculate chainage")
            else:
                print("  ✗ Could not extract coordinates/timestamp from first image")

        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)

        if events:
            print(f"Total events analyzed: {len(events)}")

            # Check for consistency issues
            issues = []
            for event in events:
                if event.start_chainage >= event.end_chainage:
                    issues.append(f"Event '{event.event_name}' has invalid chainage range")

            if issues:
                print(f"⚠️  Found {len(issues)} issues:")
                for issue in issues:
                    print(f"  - {issue}")
            else:
                print("✓ No obvious chainage consistency issues found")

        print("\nTest completed successfully!")

    except Exception as e:
        print(f"✗ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_event_chainage_analysis()