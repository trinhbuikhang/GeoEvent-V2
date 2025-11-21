"""
Test case để kiểm tra lane fixes time bounds
Đảm bảo rằng các lane fixes được tạo cho mỗi FileID có from_time/to_time
nằm trong khoảng thời gian của folder (ảnh hoặc GPS data, tùy cái nào dài hơn)
"""

import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.utils.data_loader import DataLoader
from app.models.lane_model import LaneFix
from app.models.gps_model import GPSData
from app.utils.file_parser import parse_driveiri
from app.utils.image_utils import extract_image_metadata

def load_lane_fixes_from_csv(csv_path: str) -> list[LaneFix]:
    """Load lane fixes from CSV file"""
    lane_fixes = []
    if not os.path.exists(csv_path):
        return lane_fixes

    try:
        import csv
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Parse datetime in format '01/10/25 19:12:30.314'
                    # Try DD/MM/YY format first (01/10/25 = October 1, 2025)
                    from_time_str = row.get('From', row.get('from_time', ''))
                    to_time_str = row.get('To', row.get('to_time', ''))

                    try:
                        # Try DD/MM/YY format
                        from_time = datetime.strptime(from_time_str, '%d/%m/%y %H:%M:%S.%f')
                        to_time = datetime.strptime(to_time_str, '%d/%m/%y %H:%M:%S.%f')
                    except ValueError:
                        # Try MM/DD/YY format
                        from_time = datetime.strptime(from_time_str, '%m/%d/%y %H:%M:%S.%f')
                        to_time = datetime.strptime(to_time_str, '%m/%d/%y %H:%M:%S.%f')

                    # Make timezone aware (assume UTC)
                    from_time = from_time.replace(tzinfo=timezone.utc)
                    to_time = to_time.replace(tzinfo=timezone.utc)

                    lane_fix = LaneFix(
                        plate=row.get('Plate', row.get('plate', '')),
                        from_time=from_time,
                        to_time=to_time,
                        lane=row.get('Lane', row.get('lane', '')),
                        file_id=row.get('file_id', ''),  # May not be in CSV
                        ignore=row.get('Ignore', row.get('ignore', 'False')).lower() == 'true'
                    )
                    lane_fixes.append(lane_fix)
                except Exception as e:
                    print(f"Warning: Could not parse lane fix row: {e} - Row: {row}")
                    continue
    except Exception as e:
        print(f"Error loading lane fixes from {csv_path}: {e}")

    return lane_fixes

def get_gps_time_range(gps_data: GPSData) -> tuple[datetime, datetime]:
    """Get min/max timestamps from GPS data"""
    if not gps_data.points:
        return None, None

    gps_data.sort_by_time()
    min_time = gps_data.points[0].timestamp
    max_time = gps_data.points[-1].timestamp
    return min_time, max_time

def get_image_time_range(image_paths: list[str]) -> tuple[datetime, datetime]:
    """Get min/max timestamps from image metadata"""
    if not image_paths:
        return None, None

    try:
        first_metadata = extract_image_metadata(image_paths[0])
        last_metadata = extract_image_metadata(image_paths[-1])

        first_time = first_metadata.get('timestamp')
        last_time = last_metadata.get('timestamp')

        return first_time, last_time
    except Exception as e:
        print(f"Error extracting image time range: {e}")
        return None, None

def test_lane_fix_time_bounds():
    """Test that lane fixes are within valid time bounds for each FileID"""

    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Test data directory
    testdata_path = Path("testdata/20251002")
    if not testdata_path.exists():
        print(f"Test data not found: {testdata_path}")
        return

    # Find all FileID folders
    fileid_folders = []
    for item in testdata_path.iterdir():
        if item.is_dir() and (item.name.startswith('0D25') or len(item.name) == 16):  # FileID format
            # Create a simple fileid object
            class FileID:
                def __init__(self, fileid, path):
                    self.fileid = fileid
                    self.path = path

            fileid_folders.append(FileID(item.name, str(item)))

    if not fileid_folders:
        print("No FileID folders found")
        return

    print(f"Found {len(fileid_folders)} FileID folders")

    # Test each FileID
    all_passed = True

    for fileid_obj in fileid_folders:
        print(f"\n--- Testing FileID: {fileid_obj.fileid} ---")

        # Load lane fixes from CSV
        csv_path = os.path.join(fileid_obj.path, f"{fileid_obj.fileid}_lane_fixes.csv")
        lane_fixes = load_lane_fixes_from_csv(csv_path)

        if not lane_fixes:
            print(f"  No lane fixes found for {fileid_obj.fileid}")
            continue

        print(f"  Loaded {len(lane_fixes)} lane fixes")

        # Get image time range
        image_paths = []
        for ext in ['*.jpg', '*.jpeg', '*.png']:
            image_paths.extend(list(Path(fileid_obj.path).glob(f"**/{ext}")))

        image_min_time, image_max_time = get_image_time_range([str(p) for p in image_paths])

        # Get GPS time range
        iri_path = os.path.join(fileid_obj.path, f"{fileid_obj.fileid}.driveriri")
        gps_min_time, gps_max_time = None, None
        if os.path.exists(iri_path):
            try:
                gps_data = parse_driveiri(iri_path)
                gps_min_time, gps_max_time = get_gps_time_range(gps_data)
            except Exception as e:
                print(f"  Error loading GPS data: {e}")

        # Determine valid time range (whichever is longer)
        valid_min_time = None
        valid_max_time = None

        image_duration = None
        gps_duration = None

        if image_min_time and image_max_time:
            image_duration = (image_max_time - image_min_time).total_seconds()
            print(f"  Image time range: {image_min_time} to {image_max_time} ({image_duration:.1f}s)")

        if gps_min_time and gps_max_time:
            gps_duration = (gps_max_time - gps_min_time).total_seconds()
            print(f"  GPS time range: {gps_min_time} to {gps_max_time} ({gps_duration:.1f}s)")

        # Use the longer time range
        if image_duration is not None and gps_duration is not None:
            if image_duration >= gps_duration:
                valid_min_time, valid_max_time = image_min_time, image_max_time
                print("  Using image time range (longer)")
            else:
                valid_min_time, valid_max_time = gps_min_time, gps_max_time
                print("  Using GPS time range (longer)")
        elif image_duration is not None:
            valid_min_time, valid_max_time = image_min_time, image_max_time
            print("  Using image time range (only available)")
        elif gps_duration is not None:
            valid_min_time, valid_max_time = gps_min_time, gps_max_time
            print("  Using GPS time range (only available)")
        else:
            print("  ERROR: No time range available for validation")
            all_passed = False
            continue

        # Check each lane fix
        file_passed = True
        tolerance_seconds = 1.0  # Allow 1 second tolerance for floating point precision
        
        for i, fix in enumerate(lane_fixes):
            issues = []

            if fix.from_time < valid_min_time - timedelta(seconds=tolerance_seconds):
                issues.append(f"from_time {fix.from_time} < valid_min {valid_min_time} (by more than {tolerance_seconds}s)")

            if fix.to_time > valid_max_time + timedelta(seconds=tolerance_seconds):
                issues.append(f"to_time {fix.to_time} > valid_max {valid_max_time} (by more than {tolerance_seconds}s)")

            if fix.from_time >= fix.to_time:
                issues.append(f"from_time {fix.from_time} >= to_time {fix.to_time}")

            if issues:
                print(f"  ❌ Fix {i}: {fix.lane} {fix.from_time} - {fix.to_time}")
                for issue in issues:
                    print(f"    {issue}")
                file_passed = False
            else:
                print(f"  ✅ Fix {i}: {fix.lane} {fix.from_time} - {fix.to_time}")

        if file_passed:
            print(f"  ✅ All lane fixes for {fileid_obj.fileid} are within valid time bounds")
        else:
            print(f"  ❌ Some lane fixes for {fileid_obj.fileid} are outside valid time bounds")
            all_passed = False

    # Summary
    print(f"\n{'='*50}")
    if all_passed:
        print("✅ ALL TESTS PASSED: All lane fixes are within valid time bounds")
        return True
    else:
        print("❌ SOME TESTS FAILED: Some lane fixes are outside valid time bounds")
        return False

if __name__ == "__main__":
    success = test_lane_fix_time_bounds()
    sys.exit(0 if success else 1)