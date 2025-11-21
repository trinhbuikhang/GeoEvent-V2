"""
Test case to reproduce TM3/TM4 lane assignment display issues
Tests for lane display position and chainage issues
"""

import sys
import os
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QPointF
from app.main_window import MainWindow

def test_tm3_tm4_display_issues():
    """Test TM3/TM4 lane assignment display issues"""
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()

    # Scan testdata
    testdata_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'testdata', '20251002')
    if os.path.exists(testdata_path):
        main_window.fileid_manager.scan_parent_folder(testdata_path)
        print(f"Scanned {len(main_window.fileid_manager.fileid_list)} FileIDs")
        
        # Print available FileIDs
        for i, fileid in enumerate(main_window.fileid_manager.fileid_list):
            print(f"  {i}: {fileid.fileid}")

        if len(main_window.fileid_manager.fileid_list) >= 2:
            # Test with FileIDs that have longer chainage: 0D2510020812247700 and 0D2510020814007700
            target_fileids = ['0D2510020812247700', '0D2510020814007700']
            found_fileids = []
            
            for target in target_fileids:
                for fileid in main_window.fileid_manager.fileid_list:
                    if fileid.fileid == target:
                        found_fileids.append(fileid)
                        break
            
            if len(found_fileids) >= 2:
                fileid1 = found_fileids[0]
                fileid2 = found_fileids[1]
                print(f"Found target FileIDs: {fileid1.fileid} and {fileid2.fileid}")
            else:
                # Fallback to first two
                fileid1 = main_window.fileid_manager.fileid_list[0]
                fileid2 = main_window.fileid_manager.fileid_list[1]
                print(f"Using fallback FileIDs: {fileid1.fileid} and {fileid2.fileid}")
            
            print(f"Testing with FileID 1: {fileid1.fileid}")
            print(f"Testing with FileID 2: {fileid2.fileid}")
            
            # Load first FileID
            main_window.load_fileid(fileid1)
            app.processEvents()
            
            if hasattr(main_window.photo_tab, 'lane_manager') and main_window.photo_tab.lane_manager:
                # Test TM3 on first FileID
                if main_window.photo_tab.image_paths:
                    current_metadata = main_window.photo_tab.current_metadata
                    if current_metadata and 'timestamp' in current_metadata:
                        print(f"\n--- Testing TM3 on {fileid1.fileid} ---")
                        success = main_window.photo_tab.assign_lane('TM3')
                        print(f"TM3 assignment on {fileid1.fileid}: {success}")
                        
                        # Check chainage
                        if hasattr(main_window.photo_tab, 'gps_data') and main_window.photo_tab.gps_data:
                            chainage = main_window.photo_tab.gps_data.interpolate_chainage(current_metadata['timestamp'])
                            print(f"Chainage at TM3 position: {chainage}")
                        
                        # Force save to cache
                        main_window.photo_tab.lane_fixes_per_fileid[fileid1.fileid] = main_window.photo_tab.lane_manager.lane_fixes.copy()
                
                # Switch to second FileID
                print(f"\n--- Switching to {fileid2.fileid} ---")
                main_window.load_fileid(fileid2)
                app.processEvents()
                
                # Test TM4 on second FileID
                if main_window.photo_tab.image_paths:
                    current_metadata2 = main_window.photo_tab.current_metadata
                    if current_metadata2 and 'timestamp' in current_metadata2:
                        print(f"\n--- Testing TM4 on {fileid2.fileid} ---")
                        success2 = main_window.photo_tab.assign_lane('TM4')
                        print(f"TM4 assignment on {fileid2.fileid}: {success2}")
                        
                        # Check chainage
                        if hasattr(main_window.photo_tab, 'gps_data') and main_window.photo_tab.gps_data:
                            chainage2 = main_window.photo_tab.gps_data.interpolate_chainage(current_metadata2['timestamp'])
                            print(f"Chainage at TM4 position: {chainage2}")
                        
                        # Force save to cache
                        main_window.photo_tab.lane_fixes_per_fileid[fileid2.fileid] = main_window.photo_tab.lane_manager.lane_fixes.copy()
                
                # NOW create merged lane manager after both FileIDs are loaded
                print(f"\n--- Creating merged lane manager ---")
                all_lane_fixes = []
                
                # Get cached lane fixes from both FileIDs
                for fid in [fileid1, fileid2]:
                    cached_fixes = main_window.photo_tab.lane_fixes_per_fileid.get(fid.fileid, [])
                    all_lane_fixes.extend(cached_fixes)
                
                tm_fixes = [f for f in all_lane_fixes if f.lane in ['TM3', 'TM4']]
                print(f"Total TM fixes for merging: {len(tm_fixes)}")
                
                # Print details of TM fixes
                for fix in tm_fixes:
                    print(f"  {fix.lane} in {fix.file_id}: {fix.from_time.strftime('%H:%M:%S')} - {fix.to_time.strftime('%H:%M:%S')}")
                
                # Create merged lane manager for timeline display
                if hasattr(main_window.photo_tab, 'lane_manager') and main_window.photo_tab.lane_manager:
                    # Create a new lane manager and add fixes from both FileIDs
                    from app.models.lane_model import LaneManager
                    merged_lane_manager = LaneManager()
                    merged_lane_manager.lane_fixes = all_lane_fixes
                    merged_lane_manager.plate = main_window.photo_tab.lane_manager.plate
                    merged_lane_manager.fileid_folder = main_window.photo_tab.lane_manager.fileid_folder
                    
                    # Just set it immediately for now - the issue is that _setup_timeline_data overrides it
                    main_window.photo_tab.timeline.set_lane_manager(merged_lane_manager)
                    
                    # Force a repaint cycle
                    main_window.photo_tab.timeline.invalidate_cache()
                    main_window.photo_tab.timeline.repaint()
                    main_window.photo_tab.timeline.timeline_area.repaint()
                    app.processEvents()
                    
                    print("Set merged lane manager to timeline")
                
                # Test timeline display for both
                timeline = main_window.photo_tab.timeline
                if hasattr(timeline, 'lane_manager') and timeline.lane_manager:
                    lane_fixes = timeline.lane_manager.lane_fixes
                    tm_lanes = [fix for fix in lane_fixes if fix.lane in ['TM3', 'TM4']]
                    
                    print(f"\nTimeline has lane_manager: {timeline.lane_manager is not None}")
                    print(f"Lane manager has {len(lane_fixes)} total fixes")
                    print(f"Merged lane manager has {len(merged_lane_manager.lane_fixes)} fixes")
                    print(f"Timeline shows {len(tm_lanes)} TM lanes:")
                    
                    # Debug: print all lane fixes
                    for i, fix in enumerate(lane_fixes):
                        print(f"  Fix {i}: {fix.lane} in {fix.file_id}: {fix.from_time.strftime('%H:%M:%S')} - {fix.to_time.strftime('%H:%M:%S')}")
                    
                    # Force repaint and check
                    timeline.repaint()
                    timeline.timeline_area.repaint()
                    app.processEvents()
                    
                    for fix in tm_lanes:
                        print(f"  {fix.lane}: {fix.from_time.strftime('%H:%M:%S')} - {fix.to_time.strftime('%H:%M:%S')} ({(fix.to_time - fix.from_time).total_seconds():.1f}s)")
                        
                        # Check visibility
                        rect = timeline.rect()
                        
                        # Get pixels_per_second from timeline
                        pixels_per_second = 10  # fallback
                        if hasattr(timeline, 'get_pixels_per_second'):
                            try:
                                pixels_per_second = timeline.get_pixels_per_second()
                                print(f"  Using timeline pixels_per_second: {pixels_per_second}")
                            except Exception as e:
                                print(f"  Error getting pixels_per_second: {e}")
                                print(f"  Using fallback pixels_per_second: {pixels_per_second}")
                        else:
                            print(f"  Timeline has no get_pixels_per_second method, using fallback: {pixels_per_second}")
                        
                        # Calculate time range in seconds
                        time_range_seconds = (timeline.view_end_time - timeline.view_start_time).total_seconds()
                        print(f"  Time range: {time_range_seconds:.1f} seconds")
                        print(f"  Timeline width: {rect.width()}")
                        
                        # Manual pixels_per_second calculation
                        manual_pixels_per_second = rect.width() / time_range_seconds if time_range_seconds > 0 else 10
                        print(f"  Manual pixels_per_second: {manual_pixels_per_second}")
                        
                        start_x = timeline.time_to_pixel(fix.from_time, pixels_per_second, rect.left())
                        end_x = timeline.time_to_pixel(fix.to_time, pixels_per_second, rect.left())
                        
                        print(f"  Lane time range: {fix.from_time} to {fix.to_time}")
                        print(f"  Pixel range: {start_x:.1f} to {end_x:.1f} (width: {end_x - start_x:.1f})")
                        
                        if end_x <= rect.left() or start_x >= rect.right():
                            print(f"    NOT VISIBLE on timeline")
                        else:
                            print(f"    VISIBLE: pixels {start_x:.1f} to {end_x:.1f}")
                else:
                    print("Timeline has no lane_manager after setting merged data")
        else:
            print("Need at least 2 FileIDs")
    else:
        print(f"Test data not found: {testdata_path}")

    main_window.close()

if __name__ == "__main__":
    test_tm3_tm4_display_issues()