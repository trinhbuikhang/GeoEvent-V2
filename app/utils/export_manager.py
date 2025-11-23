"""
Export Manager for GeoEvent application
Handles CSV export of lane assignments and events
"""

import os
import csv
import shutil
import logging
from datetime import datetime
from typing import List
import pandas as pd

from ..models.lane_model import LaneFix
from ..models.event_model import Event


class ExportManager:
    """
    Manages data export to CSV format
    """

    def _validate_output_path(self, output_path: str) -> bool:
        """
        Validate output path is safe and writable
        
        Args:
            output_path: Path to validate
            
        Returns:
            bool: True if path is valid and writable, False otherwise
        """
        try:
            # Check if path is absolute
            if not os.path.isabs(output_path):
                logging.warning(f"Output path is not absolute: {output_path}")
            
            # Check if directory exists
            directory = os.path.dirname(output_path)
            if directory and not os.path.exists(directory):
                logging.error(f"Directory does not exist: {directory}")
                return False
            
            # Check if we can write to the directory
            if directory:
                if not os.access(directory, os.W_OK):
                    logging.error(f"No write permission for directory: {directory}")
                    return False
            
            return True
            
        except Exception as e:
            logging.error(f"Error validating path: {e}")
            return False

    def export_lane_fixes(self, lane_fixes: List[LaneFix], output_path: str, include_file_id: bool = True) -> bool:
        """
        Export lane assignments to CSV with full datetime format
        
        Args:
            lane_fixes: List of LaneFix objects to export
            output_path: Path to output CSV file
            include_file_id: Whether to include FileID column (for merged files)
            
        Returns:
            bool: True if export successful, False otherwise
        """
        # Validate input
        if not lane_fixes:
            logging.warning("ExportManager: No lane fixes to export")
            return False
        
        # Validate output path
        if not self._validate_output_path(output_path):
            return False
        
        backup_path = None
        
        try:
            # Log what we're exporting
            # logging.info(f"ExportManager: Exporting {len(sorted_fixes)} lane fixes to {output_path} (include_file_id={include_file_id})")
            
            # Create backup if file exists
            if os.path.exists(output_path):
                backup_path = output_path + '.backup'
                shutil.copy2(output_path, backup_path)
                logging.info(f"Created backup: {backup_path}")

            with open(output_path, 'w', newline='', encoding='utf-8', errors='replace') as f:
                writer = csv.writer(f)

                # Write header based on include_file_id flag
                if include_file_id:
                    writer.writerow([
                        'Plate', 'From', 'To', 'Lane', 'Ignore', 'FileID', 'RegionID', 'RoadID', 'Travel'
                    ])
                else:
                    writer.writerow([
                        'Plate', 'From', 'To', 'Lane', 'Ignore'
                    ])

                # Sort lane fixes by from_time before exporting
                sorted_fixes = sorted(lane_fixes, key=lambda x: x.from_time)

                # Write data
                skipped = 0
                for fix in sorted_fixes:
                    # Validate data before writing
                    if not fix.plate or not fix.lane:
                        logging.warning(f"Skipping invalid fix: plate='{fix.plate}', lane='{fix.lane}'")
                        skipped += 1
                        continue
                    
                    if not fix.from_time or not fix.to_time:
                        logging.warning(f"Skipping fix with invalid time: {fix.plate}")
                        skipped += 1
                        continue
                    
                    try:
                        # Convert times to DD/MM/YY HH:MM:SS.mmm format
                        from_milliseconds = fix.from_time.microsecond // 1000
                        from_time_str = fix.from_time.strftime('%d/%m/%y %H:%M:%S') + f'.{from_milliseconds:03d}'
                        
                        to_milliseconds = fix.to_time.microsecond // 1000
                        to_time_str = fix.to_time.strftime('%d/%m/%y %H:%M:%S') + f'.{to_milliseconds:03d}'
                        
                        if include_file_id:
                            writer.writerow([
                                fix.plate,
                                from_time_str,
                                to_time_str,
                                fix.lane,
                                '1' if fix.ignore else '',
                                fix.file_id or '',  # Handle None
                                '',
                                '',
                                'N'
                            ])
                        else:
                            writer.writerow([
                                fix.plate,
                                from_time_str,
                                to_time_str,
                                fix.lane,
                                '1' if fix.ignore else ''
                            ])
                    
                    except AttributeError as e:
                        logging.error(f"Error formatting fix {fix.plate}: {e}")
                        skipped += 1
                        continue
                
                if skipped > 0:
                    logging.warning(f"Skipped {skipped} invalid lane fixes during export")

            # Delete backup on success
            if backup_path and os.path.exists(backup_path):
                os.remove(backup_path)
                logging.debug(f"Deleted backup: {backup_path}")
            
            # logging.info(f"Successfully exported {len(sorted_fixes) - skipped} lane fixes")
            return True

        except PermissionError as e:
            logging.error(f"Permission denied writing to {output_path}: {e}")
            if backup_path and os.path.exists(backup_path):
                shutil.copy2(backup_path, output_path)
                logging.info("Restored from backup")
            return False
            
        except IOError as e:
            logging.error(f"IO error exporting lane fixes: {e}")
            if backup_path and os.path.exists(backup_path):
                shutil.copy2(backup_path, output_path)
                logging.info("Restored from backup")
            return False
            
        except Exception as e:
            logging.error(f"Unexpected error exporting lane fixes: {e}")
            if backup_path and os.path.exists(backup_path):
                shutil.copy2(backup_path, output_path)
                logging.info("Restored from backup")
            return False

    def export_events(self, events: List[Event], output_path: str) -> bool:
        """
        Export events to CSV
        
        Args:
            events: List of Event objects to export
            output_path: Path to output CSV file
            
        Returns:
            bool: True if export successful, False otherwise
        """
        # Validate input
        if not events:
            logging.warning("ExportManager: No events to export")
            return False
        
        # Validate output path
        if not self._validate_output_path(output_path):
            return False
        
        try:
            logging.info(f"ExportManager: Exporting {len(events)} events to {output_path}")
            
            with open(output_path, 'w', newline='', encoding='utf-8', errors='replace') as f:
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

            logging.info(f"Successfully exported {len(events)} events")
            return True

        except PermissionError as e:
            logging.error(f"Permission denied writing to {output_path}: {e}")
            return False
            
        except IOError as e:
            logging.error(f"IO error exporting events: {e}")
            return False
            
        except Exception as e:
            logging.error(f"Unexpected error exporting events: {e}")
            return False

    def merge_lane_fixes(self, existing_path: str, new_fixes: List[LaneFix], output_path: str) -> bool:
        """
        Merge new lane fixes with existing CSV file
        
        Args:
            existing_path: Path to existing CSV file
            new_fixes: List of new LaneFix objects to merge
            output_path: Path to output merged CSV file
            
        Returns:
            bool: True if merge successful, False otherwise
        """
        try:
            # Use the existing helper method instead of duplicating code
            existing_fixes = self._load_existing_fixes(existing_path)
            
            logging.info(f"Loaded {len(existing_fixes)} existing fixes")
            logging.info(f"Merging with {len(new_fixes)} new fixes")

            # Merge with new fixes
            all_fixes = existing_fixes + new_fixes

            # Remove duplicates
            unique_fixes = self._remove_duplicates(all_fixes)
            
            logging.info(f"After deduplication: {len(unique_fixes)} unique fixes")

            # Export merged data with file_id column
            return self.export_lane_fixes(unique_fixes, output_path, include_file_id=True)

        except Exception as e:
            logging.error(f"Error merging lane fixes: {e}")
            return False

    def _load_existing_fixes(self, existing_path: str) -> List[LaneFix]:
        """
        Load existing fixes from CSV
        
        Args:
            existing_path: Path to existing CSV file
            
        Returns:
            List[LaneFix]: List of loaded LaneFix objects
        """
        existing_fixes = []
        skipped_count = 0
        
        if not os.path.exists(existing_path):
            logging.info(f"No existing file found at {existing_path}")
            return existing_fixes
        
        try:
            df = pd.read_csv(existing_path)
            logging.info(f"Reading {len(df)} rows from {existing_path}")
            
            for idx, row in df.iterrows():
                try:
                    fix = LaneFix(
                        plate=str(row['Plate']),
                        from_time=datetime.strptime(str(row['From']), '%d/%m/%y %H:%M:%S.%f'),
                        to_time=datetime.strptime(str(row['To']), '%d/%m/%y %H:%M:%S.%f'),
                        lane=str(row['Lane']),
                        file_id=str(row.get('FileID', '')),
                        ignore=str(row.get('Ignore', '')).strip() in ['1', '1.0']
                    )
                    existing_fixes.append(fix)
                    
                except KeyError as e:
                    skipped_count += 1
                    logging.warning(f"Row {idx}: Missing required field {e}")
                    
                except ValueError as e:
                    skipped_count += 1
                    logging.warning(f"Row {idx}: Invalid value - {e}")
            
            if skipped_count > 0:
                logging.warning(f"Skipped {skipped_count} invalid rows from {existing_path}")
            
            logging.info(f"Successfully loaded {len(existing_fixes)} fixes from {existing_path}")
                
        except FileNotFoundError:
            logging.warning(f"File not found: {existing_path}")
        except pd.errors.EmptyDataError:
            logging.warning(f"Empty CSV file: {existing_path}")
        except Exception as e:
            logging.error(f"Error reading CSV file {existing_path}: {e}")
            
        return existing_fixes

    def _remove_duplicates(self, fixes: List[LaneFix]) -> List[LaneFix]:
        """
        Remove duplicate lane fixes
        
        Args:
            fixes: List of LaneFix objects (may contain duplicates)
            
        Returns:
            List[LaneFix]: List with duplicates removed
        """
        seen = set()
        unique = []

        for fix in fixes:
            key = (fix.plate, fix.from_time, fix.to_time, fix.lane, fix.file_id)
            if key not in seen:
                seen.add(key)
                unique.append(fix)
            else:
                logging.debug(f"Duplicate found and skipped: {fix.plate} at {fix.from_time}")

        duplicates_removed = len(fixes) - len(unique)
        if duplicates_removed > 0:
            logging.info(f"Removed {duplicates_removed} duplicate lane fixes")
            
        return unique
