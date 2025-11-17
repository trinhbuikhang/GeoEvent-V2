"""
Export Manager for GeoEvent application
Handles CSV export of lane assignments and events
"""

import os
import csv
from datetime import datetime
from typing import List
import pandas as pd

from ..models.lane_model import LaneFix
from ..models.event_model import Event

class ExportManager:
    """
    Manages data export to CSV format
    """

    def export_lane_fixes(self, lane_fixes: List[LaneFix], output_path: str) -> bool:
        """
        Export lane assignments to CSV with full datetime format
        """
        try:
            # Create backup if file exists
            if os.path.exists(output_path):
                backup_path = output_path + '.backup'
                import shutil
                shutil.copy2(output_path, backup_path)
                print(f"Created backup: {backup_path}")

            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Write header matching the example format
                writer.writerow([
                    'Plate', 'From', 'To', 'Lane', 'Ignore', 'RegionID', 'RoadID', 'Travel'
                ])

                # Write data
                for fix in lane_fixes:
                    # Convert times to DD/MM/YY HH:MM:SS.mmm format (day/month/year hour:minute:second.millisecond)
                    from_time_str = fix.from_time.strftime('%d/%m/%y %H:%M:%S.%f')[:-3]  # Remove microseconds to milliseconds
                    to_time_str = fix.to_time.strftime('%d/%m/%y %H:%M:%S.%f')[:-3]
                    
                    writer.writerow([
                        fix.plate,
                        from_time_str,
                        to_time_str,
                        fix.lane,
                        '',  # Ignore column (empty)
                        '',  # RegionID (empty)
                        '',  # RoadID (empty)
                        'N'  # Travel (always 'N' based on example)
                    ])

            return True

        except Exception as e:
            print(f"Error exporting lane fixes: {e}")
            return False

    def export_events(self, events: List[Event], output_path: str) -> bool:
        """
        Export events to CSV
        """
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Write header
                writer.writerow([
                    'Event_ID', 'Event_Name', 'Start_Time', 'End_Time',
                    'Start_Chainage', 'End_Chainage', 'Start_Lat', 'Start_Lon',
                    'End_Lat', 'End_Lon', 'File_ID', 'Color', 'Layer'
                ])

                # Write data
                for event in events:
                    writer.writerow([
                        event.event_id,
                        event.event_name,
                        event.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                        event.end_time.strftime('%Y-%m-%d %H:%M:%S'),
                        event.start_chainage,
                        event.end_chainage,
                        event.start_lat,
                        event.start_lon,
                        event.end_lat,
                        event.end_lon,
                        event.file_id,
                        event.color,
                        event.layer
                    ])

            return True

        except Exception as e:
            print(f"Error exporting events: {e}")
            return False

    def merge_lane_fixes(self, existing_path: str, new_fixes: List[LaneFix], output_path: str) -> bool:
        """
        Merge new lane fixes with existing CSV file
        """
        try:
            existing_fixes = []

            # Load existing data
            if os.path.exists(existing_path):
                df = pd.read_csv(existing_path)
                for _, row in df.iterrows():
                    try:
                        fix = LaneFix(
                            plate=str(row['Plate']),
                            from_time=datetime.strptime(str(row['From_Time']), '%Y-%m-%d %H:%M:%S'),
                            to_time=datetime.strptime(str(row['To_Time']), '%Y-%m-%d %H:%M:%S'),
                            lane=str(row['Lane']),
                            file_id=str(row['FileID'])
                        )
                        existing_fixes.append(fix)
                    except (KeyError, ValueError):
                        continue

            # Merge with new fixes (simple append for now)
            all_fixes = existing_fixes + new_fixes

            # Remove duplicates based on plate, time, and lane
            unique_fixes = self._remove_duplicates(all_fixes)

            # Export merged data
            return self.export_lane_fixes(unique_fixes, output_path)

        except Exception as e:
            print(f"Error merging lane fixes: {e}")
            return False

    def _remove_duplicates(self, fixes: List[LaneFix]) -> List[LaneFix]:
        """Remove duplicate lane fixes"""
        seen = set()
        unique = []

        for fix in fixes:
            key = (fix.plate, fix.from_time, fix.to_time, fix.lane, fix.file_id)
            if key not in seen:
                seen.add(key)
                unique.append(fix)

        return unique