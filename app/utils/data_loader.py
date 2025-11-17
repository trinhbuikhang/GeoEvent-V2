"""
Data Loader for GeoEvent application
Handles loading and parsing of all data types for a FileID
"""

import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from ..models.event_model import Event
from ..models.gps_model import GPSData
from ..models.lane_model import LaneManager
from ..utils.file_parser import parse_driveevt, parse_driveiri, enrich_events_with_gps, save_driveevt
from ..utils.image_utils import extract_image_metadata, validate_filename

class DataLoader:
    """
    Loads and parses all data for a FileID folder
    RESPONSIBILITIES:
    - Parse event data (.driveevt files)
    - Parse GPS data (.driveiri files)
    - Load and sort image paths
    - Enrich events with GPS data
    - Create empty files when missing
    """
    
    def __init__(self):
        self.lane_manager = LaneManager()
    
    def load_fileid_data(self, fileid_folder) -> Dict[str, Any]:
        """
        Load all data for a FileID folder
        Returns dict with events, gps_data, image_paths, and metadata
        """
        logging.info(f"Loading data for FileID: {fileid_folder.fileid} from path: {fileid_folder.path}")
        
        result = {
            'events': [],
            'gps_data': None,
            'image_paths': [],
            'lane_manager': self.lane_manager,
            'metadata': {}
        }
        
        try:
            # Parse event data
            logging.debug("Loading event data...")
            result['events'] = self._load_event_data(fileid_folder)
            logging.info(f"Loaded {len(result['events'])} events")
            
            # Parse GPS data
            logging.debug("Loading GPS data...")
            result['gps_data'] = self._load_gps_data(fileid_folder)
            logging.info(f"Loaded GPS data: {result['gps_data'] is not None}")
            
            # Enrich events with GPS data
            if result['gps_data']:
                logging.debug("Enriching events with GPS data...")
                enrich_events_with_gps(result['events'], result['gps_data'])
                logging.info("Events enriched with GPS data")
            
            # Load images
            logging.debug("Loading image paths...")
            result['image_paths'] = self._load_image_paths(fileid_folder)
            logging.info(f"Loaded {len(result['image_paths'])} image paths")
            
            # Extract metadata
            logging.debug("Extracting FileID metadata...")
            result['metadata'] = self._extract_fileid_metadata(fileid_folder, result['image_paths'])
            logging.info("FileID metadata extracted")
            
            # Setup lane manager
            logging.debug("Setting up lane manager...")
            plate = None
            if result['image_paths']:
                try:
                    first_metadata = extract_image_metadata(result['image_paths'][0])
                    plate = first_metadata.get('plate')
                except Exception as e:
                    logging.warning(f"Could not extract plate from first image: {e}")
            
            self.lane_manager.set_fileid_folder(fileid_folder.path, plate)
            logging.info("Lane manager setup complete")
            
            logging.info(f"Successfully loaded all data for FileID: {fileid_folder.fileid}")
            
        except Exception as e:
            logging.error(f"Failed to load FileID data for {fileid_folder.fileid}: {str(e)}", exc_info=True)
            raise Exception(f"Failed to load FileID data: {str(e)}")
        
        return result
    
    def _load_event_data(self, fileid_folder) -> List[Event]:
        """Load event data from .driveevt file"""
        driveevt_path = os.path.join(fileid_folder.path, f"{fileid_folder.fileid}.driveevt")
        logging.debug(f"Checking for driveevt file: {driveevt_path}")
        
        if os.path.exists(driveevt_path):
            logging.debug(f"Found driveevt file, parsing...")
            try:
                events = parse_driveevt(driveevt_path)
                logging.debug(f"Successfully parsed {len(events)} events")
                return events
            except Exception as e:
                logging.error(f"Error parsing driveevt file {driveevt_path}: {str(e)}", exc_info=True)
                raise
        else:
            # Create empty driveevt file
            logging.info(f"Driveevt file not found, creating empty file: {driveevt_path}")
            self._create_empty_driveevt(driveevt_path)
            return []
    
    def _load_gps_data(self, fileid_folder) -> Optional[GPSData]:
        """Load GPS data from .driveiri file"""
        driveiri_path = os.path.join(fileid_folder.path, f"{fileid_folder.fileid}.driveiri")
        logging.debug(f"Checking for driveiri file: {driveiri_path}")
        
        if os.path.exists(driveiri_path):
            logging.debug(f"Found driveiri file, parsing...")
            try:
                gps_data = parse_driveiri(driveiri_path)
                logging.debug("Successfully parsed GPS data")
                return gps_data
            except Exception as e:
                logging.error(f"Error parsing driveiri file {driveiri_path}: {str(e)}", exc_info=True)
                raise
        else:
            logging.info(f"Driveiri file not found, using empty GPSData: {driveiri_path}")
            return GPSData()
    
    def _load_image_paths(self, fileid_folder) -> List[str]:
        """Load and sort image paths from Cam1 folder, filtering only valid survey images"""
        cam_folder = os.path.join(fileid_folder.path, "Cam1")
        logging.debug(f"Checking for Cam1 folder: {cam_folder}")
        
        if os.path.exists(cam_folder):
            try:
                # Get all .jpg files
                all_jpg_files = [
                    f for f in os.listdir(cam_folder)
                    if f.lower().endswith('.jpg')
                ]
                
                # Filter only valid survey image filenames
                valid_image_files = [
                    filename for filename in all_jpg_files
                    if validate_filename(filename)
                ]
                
                # Create full paths
                image_paths = [
                    os.path.join(cam_folder, f)
                    for f in valid_image_files
                ]
                
                # Sort by timestamp instead of filename to handle millisecond padding correctly
                def get_image_timestamp(path):
                    try:
                        metadata = extract_image_metadata(path)
                        return metadata.get('timestamp') or datetime.min.replace(tzinfo=timezone.utc)
                    except Exception:
                        return datetime.min.replace(tzinfo=timezone.utc)
                
                image_paths.sort(key=get_image_timestamp)
                
                logging.info(f"Loaded {len(image_paths)} valid images from {cam_folder}")
                
                if image_paths:
                    logging.debug(f"First image: {os.path.basename(image_paths[0])}")
                    logging.debug(f"Last image: {os.path.basename(image_paths[-1])}")
                return image_paths
            except Exception as e:
                logging.error(f"Error loading images from {cam_folder}: {str(e)}", exc_info=True)
                raise
        else:
            logging.warning(f"Cam1 folder not found: {cam_folder}")
            return []
    
    def _extract_fileid_metadata(self, fileid_folder, image_paths: List[str]) -> Dict[str, Any]:
        """Extract metadata for the FileID"""
        metadata = {
            'fileid': fileid_folder.fileid,
            'path': fileid_folder.path,
            'image_count': len(image_paths),
            'first_image_timestamp': None,
            'last_image_timestamp': None,
            'first_image_coords': None,
            'last_image_coords': None
        }
        
        if image_paths:
            # Extract timestamp from first and last images
            try:
                first_metadata = extract_image_metadata(image_paths[0])
                last_metadata = extract_image_metadata(image_paths[-1])
                
                metadata['first_image_timestamp'] = first_metadata.get('timestamp')
                metadata['last_image_timestamp'] = last_metadata.get('timestamp')
                
                # Also store coordinates
                if first_metadata.get('latitude') is not None and first_metadata.get('longitude') is not None:
                    metadata['first_image_coords'] = (first_metadata['latitude'], first_metadata['longitude'])
                
                if last_metadata.get('latitude') is not None and last_metadata.get('longitude') is not None:
                    metadata['last_image_coords'] = (last_metadata['latitude'], last_metadata['longitude'])
                    
            except Exception as e:
                print(f"Warning: Could not extract image metadata: {e}")
        
        return metadata
    
    def _create_empty_driveevt(self, path: str):
        """Create empty .driveevt file with header"""
        header = "SessionToken,Distance,Chainage,Time,TimeUtc,Event,IsSpanEvent,SpanEvent,IsSpanStartEvent,IsSpanEndEvent"
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(header + '\n')
            print(f"Created empty driveevt file: {path}")
        except Exception as e:
            print(f"Warning: Could not create empty driveevt file: {e}")
    
    def preload_images_metadata(self, image_paths: List[str], limit: int = 50) -> Dict[str, Dict]:
        """
        Preload metadata for first N images to improve performance
        Returns dict mapping image_path to metadata
        """
        metadata_cache = {}
        
        for i, path in enumerate(image_paths[:limit]):
            try:
                metadata = extract_image_metadata(path)
                metadata_cache[path] = metadata
            except Exception as e:
                print(f"Warning: Could not extract metadata for {path}: {e}")
                metadata_cache[path] = {}
        
        return metadata_cache
    
    def save_events(self, events: List[Event], fileid_folder) -> bool:
        """
        Save events to the .driveevt file for the given FileID
        """
        driveevt_path = os.path.join(fileid_folder.path, f"{fileid_folder.fileid}.driveevt")
        
        try:
            success = save_driveevt(events, driveevt_path, fileid_folder.fileid)
            if success:
                logging.info(f"Successfully saved {len(events)} events to {driveevt_path}")
            else:
                logging.error(f"Failed to save events to {driveevt_path}")
            return success
        except Exception as e:
            logging.error(f"Error saving events: {str(e)}")
            return False
