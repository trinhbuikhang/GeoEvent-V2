#!/usr/bin/env python3
"""
Performance test script for GeoEvent data loading
"""

import sys
import os
import time
import logging
from pathlib import Path

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))
sys.path.insert(0, os.path.dirname(__file__))

from app.utils.data_loader import DataLoader
from app.utils.fileid_manager import FileIDManager

def test_data_loading_performance(network_path):
    """Test performance of loading data from network path"""

    print(f"Testing data loading performance for: {network_path}")
    print("=" * 60)

    # Initialize components
    fileid_manager = FileIDManager()
    data_loader = DataLoader()

    # Scan for FileIDs
    print("Scanning for FileID folders...")
    start_time = time.time()
    fileid_folders = fileid_manager.scan_parent_folder(network_path)
    scan_time = time.time() - start_time
    print(f"Found {len(fileid_folders)} FileID folders in {scan_time:.2f} seconds")

    if not fileid_folders:
        print("No FileID folders found!")
        return

    # Test loading the largest FileID (by image count)
    print("\nFinding FileID with most images...")
    max_images = 0
    largest_fileid = None

    for fileid_folder in fileid_folders:
        cam1_path = os.path.join(fileid_folder.path, "Cam1")
        if os.path.exists(cam1_path):
            try:
                image_count = len([f for f in os.listdir(cam1_path) if f.lower().endswith('.jpg')])
                if image_count > max_images:
                    max_images = image_count
                    largest_fileid = fileid_folder
            except:
                pass

    if largest_fileid:
        print(f"Largest FileID: {largest_fileid.fileid} with {max_images} images")

        # Test loading this FileID
        print(f"\nLoading data for FileID: {largest_fileid.fileid}")
        start_time = time.time()
        try:
            data = data_loader.load_fileid_data(largest_fileid)
            load_time = time.time() - start_time

            print(f"  Load time: {load_time:.2f} seconds")
            print(f"  - Events: {len(data['events'])}")
            print(f"  - GPS points: {len(data['gps_data'].points) if data['gps_data'] and data['gps_data'].points else 0}")
            print(f"  - Images: {len(data['image_paths'])}")

        except Exception as e:
            print(f"Error loading FileID: {e}")
            load_time = time.time() - start_time
            print(f"  Load time: {load_time:.2f} seconds (with error)")
    # Test loading a few more FileIDs to simulate navigation
    print("\nTesting navigation performance (loading 5 FileIDs)...")
    navigation_times = []

    for i, fileid_folder in enumerate(fileid_folders[:5]):
        print(f"Loading FileID {i+1}/5: {fileid_folder.fileid}")
        start_time = time.time()
        try:
            data = data_loader.load_fileid_data(fileid_folder)
            load_time = time.time() - start_time
            navigation_times.append(load_time)
            print(f"  Load time: {load_time:.2f} seconds")
        except Exception as e:
            load_time = time.time() - start_time
            navigation_times.append(load_time)
            print(f"  Load time: {load_time:.2f} seconds (with error)")

    if navigation_times:
        avg_nav_time = sum(navigation_times) / len(navigation_times)
        print(f"\nAverage navigation load time: {avg_nav_time:.2f} seconds")

if __name__ == "__main__":
    # Test with the provided network path
    network_path = r"\\pav001\e$\250410.01-CCC\testdata\20251002"
    test_data_loading_performance(network_path)