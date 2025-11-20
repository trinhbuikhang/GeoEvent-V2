#!/usr/bin/env python3
"""
Test script to check minimap overlay performance with 1000 point limit
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.utils.minimap_overlay import MinimapOverlay
from app.models.gps_model import GPSData, GPSPoint
from datetime import datetime

def test_overlay_performance():
    """Test overlay generation with different point counts"""

    # Test with 2000 points (should be sampled down to ~1000)
    print("Testing with 2000 GPS points...")
    gps_data = GPSData()
    for i in range(2000):
        point = GPSPoint(
            timestamp=datetime.now(),
            chainage=float(i),
            latitude=10.0 + i * 0.001,
            longitude=106.0 + i * 0.001
        )
        gps_data.add_point(point)

    overlay_js = MinimapOverlay.generate_path_overlay(gps_data)

    print(f"Original points: {len(gps_data.points)}")
    print(f"JavaScript code length: {len(overlay_js)} characters")
    print(f"Approximate coordinates in overlay: {overlay_js.count('[')}")

    # Test with 500 points (should use all points)
    print("\nTesting with 500 GPS points...")
    gps_data_small = GPSData()
    for i in range(500):
        point = GPSPoint(
            timestamp=datetime.now(),
            chainage=float(i),
            latitude=10.0 + i * 0.001,
            longitude=106.0 + i * 0.001
        )
        gps_data_small.add_point(point)

    overlay_js_small = MinimapOverlay.generate_path_overlay(gps_data_small)

    print(f"Original points: {len(gps_data_small.points)}")
    print(f"JavaScript code length: {len(overlay_js_small)} characters")
    print(f"Approximate coordinates in overlay: {overlay_js_small.count('[')}")

if __name__ == "__main__":
    test_overlay_performance()