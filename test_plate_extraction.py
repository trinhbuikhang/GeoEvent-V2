#!/usr/bin/env python3
"""
Test script to verify plate extraction from image filenames
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geoevent.app.utils.image_utils import extract_image_metadata

def test_plate_extraction():
    """Test plate extraction from sample filenames"""

    # Sample filename from test data
    sample_filename = "250410.01-2025-10-01-18-21-49-637-4309.004262S-17244.099429E-274.4---QJS289-0D2510020721457700-1040382883056-5.78-LE-.jpg"

    print(f"Testing filename: {sample_filename}")

    metadata = extract_image_metadata(sample_filename)

    print("Extracted metadata:")
    for key, value in metadata.items():
        print(f"  {key}: {value}")

    print(f"\nPlate should be: QJS289")
    print(f"Extracted plate: {metadata.get('plate', 'NOT FOUND')}")

    if metadata.get('plate') == 'QJS289':
        print("SUCCESS: Plate extraction working correctly")
    else:
        print("FAILURE: Plate extraction not working")

if __name__ == "__main__":
    test_plate_extraction()