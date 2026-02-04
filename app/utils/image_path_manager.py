"""
Image Path Manager for GeoEvent Application
Provides efficient lazy loading of image paths for large datasets
"""

import os
import logging
from typing import List, Optional, Callable
from datetime import datetime, timezone
from pathlib import Path


class ImagePathManager:
    """
    Manages image paths with lazy loading and efficient batch processing
    Reduces memory usage and improves performance for large image sets
    """
    
    def __init__(self, cam_folder: str, batch_size: int = 100, validate_func: Optional[Callable] = None):
        """
        Initialize ImagePathManager
        
        Args:
            cam_folder: Path to Cam1 folder containing images
            batch_size: Number of images to load per batch
            validate_func: Optional function to validate filenames
        """
        self.cam_folder = cam_folder
        self.batch_size = batch_size
        self.validate_func = validate_func
        self._cached_paths: List[str] = []
        self._total_count: Optional[int] = None
        self._all_files: Optional[List[str]] = None
        
    def get_total_count(self) -> int:
        """
        Get total number of valid images without loading all paths
        
        Returns:
            Total image count
        """
        if self._total_count is None:
            self._scan_directory()
        return self._total_count or 0
    
    def load_batch(self, start_idx: int, count: int) -> List[str]:
        """
        Load a specific batch of image paths
        
        Args:
            start_idx: Starting index
            count: Number of images to load
            
        Returns:
            List of image paths for requested batch
        """
        # Check if we have cached paths covering this range
        if start_idx < len(self._cached_paths):
            end_idx = min(start_idx + count, len(self._cached_paths))
            return self._cached_paths[start_idx:end_idx]
        
        # Load new batch
        batch = self._load_from_disk(start_idx, count)
        return batch
    
    def load_all(self) -> List[str]:
        """
        Load all image paths (fallback for backward compatibility)
        
        Returns:
            List of all image paths
        """
        if not self._all_files:
            self._scan_directory()
        
        if not self._all_files:
            return []
        
        # Apply full path
        image_paths = [
            os.path.join(self.cam_folder, f)
            for f in self._all_files
        ]
        
        return image_paths
    
    def preload_range(self, start_idx: int, end_idx: int):
        """
        Preload a range of images into cache
        
        Args:
            start_idx: Starting index
            end_idx: Ending index
        """
        count = end_idx - start_idx
        batch = self.load_batch(start_idx, count)
        
        # Extend cache if needed
        if len(self._cached_paths) < end_idx:
            missing_start = len(self._cached_paths)
            missing_count = end_idx - missing_start
            if missing_count > 0:
                additional = self._load_from_disk(missing_start, missing_count)
                self._cached_paths.extend(additional)
    
    def clear_cache(self):
        """Clear cached paths to free memory"""
        self._cached_paths.clear()
        logging.debug(f"ImagePathManager cache cleared for {self.cam_folder}")
    
    def _scan_directory(self):
        """Scan directory and build file list"""
        if not os.path.exists(self.cam_folder):
            logging.warning(f"Cam1 folder not found: {self.cam_folder}")
            self._all_files = []
            self._total_count = 0
            return
        
        try:
            # Get all .jpg files
            all_jpg_files = [
                f for f in os.listdir(self.cam_folder)
                if f.lower().endswith('.jpg')
            ]
            
            # Filter with validation function if provided
            if self.validate_func:
                valid_files = [
                    filename for filename in all_jpg_files
                    if self.validate_func(filename)
                ]
            else:
                valid_files = all_jpg_files
            
            # Sort by filename (timestamp-based sorting done separately)
            valid_files.sort()
            
            self._all_files = valid_files
            self._total_count = len(valid_files)
            
            logging.debug(f"Scanned {len(all_jpg_files)} JPG files, {self._total_count} valid")
            
        except Exception as e:
            logging.error(f"Error scanning directory {self.cam_folder}: {e}", exc_info=True)
            self._all_files = []
            self._total_count = 0
    
    def _load_from_disk(self, start_idx: int, count: int) -> List[str]:
        """
        Load batch of image paths from disk
        
        Args:
            start_idx: Starting index
            count: Number of images to load
            
        Returns:
            List of image paths
        """
        if not self._all_files:
            self._scan_directory()
        
        if not self._all_files:
            return []
        
        # Get batch of filenames
        end_idx = min(start_idx + count, len(self._all_files))
        batch_files = self._all_files[start_idx:end_idx]
        
        # Create full paths
        batch_paths = [
            os.path.join(self.cam_folder, f)
            for f in batch_files
        ]
        
        return batch_paths
    
    def get_image_at_index(self, index: int) -> Optional[str]:
        """
        Get image path at specific index
        
        Args:
            index: Image index
            
        Returns:
            Image path or None if index out of range
        """
        if not self._all_files:
            self._scan_directory()
        
        if not self._all_files or index < 0 or index >= len(self._all_files):
            return None
        
        return os.path.join(self.cam_folder, self._all_files[index])
    
    def get_stats(self) -> dict:
        """
        Get statistics about image loading
        
        Returns:
            Dictionary with statistics
        """
        return {
            'total_count': self.get_total_count(),
            'cached_count': len(self._cached_paths),
            'batch_size': self.batch_size,
            'cache_percentage': (len(self._cached_paths) / self.get_total_count() * 100) if self.get_total_count() > 0 else 0
        }
