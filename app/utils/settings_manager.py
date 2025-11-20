"""
Settings Manager for GeoEvent application
Handles application settings persistence
"""

import os
import json
from typing import Dict, Any

class SettingsManager:
    """
    Manages application settings with JSON persistence
    """

    def __init__(self):
        self.settings_file = self._get_settings_file_path()
        self._settings = self._load_settings()

    def _get_settings_file_path(self) -> str:
        """Get path to settings file"""
        app_dir = os.path.expanduser("~/.geoevent")
        os.makedirs(app_dir, exist_ok=True)
        return os.path.join(app_dir, "settings.json")

    def _load_settings(self) -> Dict[str, Any]:
        """Load settings from file"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Merge with defaults for new keys
                    defaults = self._get_default_settings()
                    merged = defaults.copy()
                    merged.update(loaded)
                    return merged
            except (json.JSONDecodeError, IOError, ValueError) as e:
                print(f"Error loading settings: {e}. Using defaults.")
                # Backup corrupted file
                backup_path = self.settings_file + ".backup"
                try:
                    os.rename(self.settings_file, backup_path)
                    print(f"Corrupted settings backed up to {backup_path}")
                except:
                    pass
                return self._get_default_settings()
        else:
            return self._get_default_settings()

    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default settings"""
        return {
            'theme': 'dark',
            'window_geometry': None,
            'last_folder': None,
            'autosave_interval': 300,  # 5 minutes
            'image_cache_size': 500,   # MB
            'timeline_zoom_default': 10,
            'lane_assignment_mode': 'strict',  # 'strict' or 'permissive'
            'auto_save_on_navigation': True,  # Auto-save when switching FileID folders
            'event_names': [
                'Bridge',
                'Pavers',
                'Speed Hump',
                'Detour',
                'Road Works',
                'Surface Contamination',
                'Wet Surface',
                'Unsealed Road',
                'Cattle Grid',
                'Railway Crossing'
            ]
        }

    def save_settings(self, settings: Dict[str, Any] = None):
        """Save settings to file"""
        if settings is not None:
            self._settings.update(settings)

        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2)
        except IOError as e:
            print(f"Error saving settings: {e}")

    def load_settings(self) -> Dict[str, Any]:
        """Get current settings"""
        return self._settings.copy()

    def save_setting(self, key: str, value: Any):
        """Save a single setting"""
        self._settings[key] = value
        self.save_settings()

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a single setting"""
        return self._settings.get(key, default)

    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        self._settings = self._get_default_settings()
        self.save_settings()