"""
FileID Manager for GeoEvent application
Manages scanning and navigation between multiple FileID folders
"""

import os
import re
import json
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class FileIDFolder:
    """Represents a FileID folder with metadata"""
    fileid: str
    path: str
    has_driveevt: bool
    has_driveiri: bool
    image_count: int
    last_modified: datetime

class FileIDManager:
    """
    Manages FileID folders and navigation
    RESPONSIBILITIES:
    - Scan and validate FileID folders
    - Create missing .driveevt files
    - Navigate between FileIDs (next/prev)
    - Track processing state
    """

    def __init__(self):
        self.fileid_list: List[FileIDFolder] = []
        self.current_index = -1
        self.state_file = self._get_state_file_path()

    def _get_state_file_path(self) -> str:
        """Get path to state file"""
        app_dir = os.path.expanduser("~/.geoevent")
        os.makedirs(app_dir, exist_ok=True)
        return os.path.join(app_dir, "fileid_state.json")

    def scan_parent_folder(self, parent_path: str) -> List[FileIDFolder]:
        """
        Scan parent folder for FileID folders
        Returns sorted list of valid FileID folders
        """
        self.fileid_list = []

        if not os.path.exists(parent_path):
            return self.fileid_list

        try:
            # Find potential FileID folders
            for item in os.listdir(parent_path):
                item_path = os.path.join(parent_path, item)

                if not os.path.isdir(item_path):
                    continue

                # Check if it's a valid FileID
                if not self._is_valid_fileid(item):
                    continue

                # Check for required files
                fileid_folder = self._analyze_fileid_folder(item, item_path)
                if fileid_folder:
                    self.fileid_list.append(fileid_folder)

            # Sort by FileID
            self.fileid_list.sort(key=lambda x: x.fileid)

            # Load state and update current index
            self._load_state()

            # If no valid current index after loading state, default to first FileID
            if self.current_index == -1 and self.fileid_list:
                self.current_index = 0
                self._save_state()

        except PermissionError:
            print(f"Permission denied accessing {parent_path}")

        return self.fileid_list

    def _is_valid_fileid(self, filename: str) -> bool:
        """
        Check if filename is a valid FileID pattern
        Pattern: alphanumeric, 16-18 characters, may start with 0D
        """
        # Remove 0D prefix if present
        if filename.startswith('0D'):
            filename = filename[2:]

        # Check length and characters
        if not (14 <= len(filename) <= 16):  # 16-18 with 0D prefix
            return False

        # Check alphanumeric
        return bool(re.match(r'^[A-Za-z0-9]+$', filename))

    def _analyze_fileid_folder(self, fileid: str, path: str) -> Optional[FileIDFolder]:
        """Analyze a FileID folder and return metadata"""
        try:
            driveevt_path = os.path.join(path, f"{fileid}.driveevt")
            driveiri_path = os.path.join(path, f"{fileid}.driveiri")

            has_driveevt = os.path.exists(driveevt_path)
            has_driveiri = os.path.exists(driveiri_path)

            # If no driveevt, try to create it
            if not has_driveevt:
                if self._create_empty_driveevt(driveevt_path):
                    has_driveevt = True

            # Count images
            image_count = 0
            cam_folder = os.path.join(path, "Cam1")
            if os.path.exists(cam_folder):
                try:
                    image_count = len([
                        f for f in os.listdir(cam_folder)
                        if f.lower().endswith('.jpg')
                    ])
                except PermissionError:
                    pass

            # Get last modified time
            last_modified = datetime.now()
            if os.path.exists(path):
                last_modified = datetime.fromtimestamp(os.path.getmtime(path))

            return FileIDFolder(
                fileid=fileid,
                path=path,
                has_driveevt=has_driveevt,
                has_driveiri=has_driveiri,
                image_count=image_count,
                last_modified=last_modified
            )

        except Exception as e:
            print(f"Error analyzing {path}: {e}")
            return None

    def _create_empty_driveevt(self, path: str) -> bool:
        """Create empty .driveevt file with header"""
        try:
            header = "SessionToken,Distance,Chainage,Time,TimeUtc,Event,IsSpanEvent,SpanEvent,IsSpanStartEvent,IsSpanEndEvent"

            # Atomic write
            temp_path = path + ".tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(header + '\n')

            os.replace(temp_path, path)
            return True

        except Exception as e:
            print(f"Failed to create empty driveevt {path}: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False

    def get_current_fileid(self) -> Optional[FileIDFolder]:
        """Get current FileID folder"""
        if 0 <= self.current_index < len(self.fileid_list):
            return self.fileid_list[self.current_index]
        return None

    def next_fileid(self) -> Optional[FileIDFolder]:
        """Navigate to next FileID"""
        if self.current_index < len(self.fileid_list) - 1:
            self.current_index += 1
            self._save_state()
            return self.fileid_list[self.current_index]
        return None

    def prev_fileid(self) -> Optional[FileIDFolder]:
        """Navigate to previous FileID"""
        if self.current_index > 0:
            self.current_index -= 1
            self._save_state()
            return self.fileid_list[self.current_index]
        return None

    def set_current_fileid(self, fileid: str):
        """Set current FileID by name"""
        for i, folder in enumerate(self.fileid_list):
            if folder.fileid == fileid:
                self.current_index = i
                self._save_state()
                break

    def _load_state(self):
        """Load processing state from file"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)

                current_fileid = state.get('current_fileid')
                if current_fileid:
                    self.set_current_fileid(current_fileid)

        except Exception as e:
            print(f"Error loading state: {e}")

    def _save_state(self):
        """Save processing state to file"""
        try:
            current = self.get_current_fileid()
            state = {
                'current_fileid': current.fileid if current else None,
                'processed_fileids': [f.fileid for f in self.fileid_list],
                'last_modified': datetime.now().isoformat()
            }

            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            print(f"Error saving state: {e}")