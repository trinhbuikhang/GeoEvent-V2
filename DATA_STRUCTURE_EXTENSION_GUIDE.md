# GeoEvent Data Structure Extension Guide

## Overview

GeoEvent application currently supports **LCMS** data structure. This document outlines the plan to extend support for **LMD** and **MSD** data structures.

## Current Data Structure (LCMS)

### Folder Structure
```
FileID_Folder/
├── FileID.driveiri      # GPS data (binary)
├── FileID.driveevt      # Event data (binary)
├── FileID.drivegps      # GPS metadata (binary)
├── FileID.drivehdr      # Header info (binary)
├── FileID.driveinterval # Time intervals (binary)
├── FileID.driveiri      # IRI data (binary)
├── FileID.drivenotifications # Notifications (binary)
├── Cam1/                # Camera folder
│   ├── FileID_001.jpg   # Survey images
│   ├── FileID_002.jpg
│   └── ...
└── lane_fixes.csv       # Lane correction data (optional)
```

### Data Sources
- **GPS**: `.driveiri` file (binary format)
- **Events**: `.driveevt` file (binary format)
- **Images**: `Cam1/` folder with timestamped JPG files
- **Metadata**: Extracted from filename patterns

## Target Data Structures

### LMD Structure
```
Project_Folder/
├── Photos/              # All images in one folder
│   ├── image001.jpg     # Survey images
│   ├── image002.jpg
│   └── ...
└── lane_fixes.csv       # Lane correction data (output only)
```

**Characteristics:**
- No GPS data files (`.driveiri`, `.driveevt`)
- Images only in `Photos/` folder
- No binary GPS/event files
- Lane fixes as output only

### MSD Structure (TBD)
```
MSD_Project/
├── Images/              # Image folder (name TBD)
│   ├── scan001.jpg      # Survey images
│   ├── scan002.jpg
│   └── ...
└── lane_fixes.csv       # Lane correction data (output only)
```

**Characteristics:**
- Similar to LMD but different folder naming
- No GPS data files
- Images in different folder structure
- Lane fixes as output only

## Architecture Extension Plan

### 1. Data Type Detection

Add automatic detection of data structure type:

```python
class DataType(Enum):
    LCMS = "lcms"
    LMD = "lmd"
    MSD = "msd"

def detect_data_type(fileid_folder: Path) -> DataType:
    """
    Detect data structure type from folder contents
    """
    # Check for LCMS indicators
    if (fileid_folder / f"{fileid_folder.name}.driveiri").exists():
        return DataType.LCMS

    # Check for LMD indicators
    if (fileid_folder / "Photos").exists() and (fileid_folder / "Photos").is_dir():
        return DataType.LMD

    # Check for MSD indicators
    if (fileid_folder / "Images").exists() and (fileid_folder / "Images").is_dir():
        return DataType.MSD

    # Default fallback
    return DataType.LCMS
```

### 2. DataLoader Extension

Extend `DataLoader.load_fileid_data()` to handle multiple data types:

```python
class DataLoader:
    def load_fileid_data(self, fileid_folder: Path) -> Dict[str, Any]:
        """
        Load data based on detected structure type
        """
        data_type = self.detect_data_type(fileid_folder)

        if data_type == DataType.LCMS:
            return self._load_lcms_data(fileid_folder)
        elif data_type == DataType.LMD:
            return self._load_lmd_data(fileid_folder)
        elif data_type == DataType.MSD:
            return self._load_msd_data(fileid_folder)
        else:
            raise ValueError(f"Unsupported data type: {data_type}")

    def _load_lcms_data(self, fileid_folder: Path) -> Dict[str, Any]:
        """Load LCMS data (current implementation)"""
        # Existing LCMS loading logic
        pass

    def _load_lmd_data(self, fileid_folder: Path) -> Dict[str, Any]:
        """Load LMD data structure"""
        # New LMD loading logic
        pass

    def _load_msd_data(self, fileid_folder: Path) -> Dict[str, Any]:
        """Load MSD data structure"""
        # New MSD loading logic
        pass
```

### 3. LMD Data Loading Implementation

```python
def _load_lmd_data(self, fileid_folder: Path) -> Dict[str, Any]:
    """
    Load LMD project data
    """
    result = {
        'events': [],
        'gps_data': None,  # No GPS data for LMD
        'image_paths': [],
        'metadata': {},
        'lane_manager': None
    }

    # Load images from Photos folder
    photos_dir = fileid_folder / "Photos"
    if photos_dir.exists():
        image_paths = sorted(photos_dir.glob("*.jpg"))
        result['image_paths'] = [str(p) for p in image_paths]

        # Extract metadata from first image
        if image_paths:
            first_image = image_paths[0]
            metadata = extract_image_metadata(str(first_image))
            result['metadata'] = metadata

            # Create lane manager for lane fixes
            result['lane_manager'] = LaneManager(
                plate=metadata.get('plate', 'Unknown'),
                fileid_folder=fileid_folder,
                end_time=metadata.get('timestamp')
            )

            # Load existing lane fixes if available
            lane_fixes_file = fileid_folder / "lane_fixes.csv"
            if lane_fixes_file.exists():
                result['lane_manager'].load_lane_fixes(str(lane_fixes_file))

    return result
```

### 4. GPS Data Handling

For projects without GPS data (LMD, MSD), we need to handle the UI gracefully:

```python
class GPSData:
    """GPS Data container that can handle missing GPS data"""

    def __init__(self, has_gps: bool = True):
        self.has_gps = has_gps
        self.points: List[GPSPoint] = []

    def interpolate_position(self, timestamp: datetime) -> Optional[tuple[float, float]]:
        if not self.has_gps:
            return None  # No GPS data available
        # Existing interpolation logic
```

### 5. UI Adaptations

#### Minimap Handling
```python
def update_minimap(self, lat: float, lon: float, bearing: float = 0):
    """Update minimap, handling cases with no GPS data"""
    if not self.gps_data or not self.gps_data.has_gps:
        # Show message or hide minimap for projects without GPS
        self.minimap_view.setHtml("""
        <html><body style='text-align:center; padding:20px;'>
        <p>No GPS data available for this project type.</p>
        </body></html>
        """)
        return

    # Existing minimap logic for projects with GPS
    # ...
```

#### Timeline GPS Integration
```python
def set_gps_data(self, gps_data: GPSData):
    """Set GPS data, handling missing GPS gracefully"""
    self.gps_data = gps_data

    if gps_data and gps_data.has_gps:
        # Enable GPS-dependent features
        self.gps_available = True
        # Existing GPS integration logic
    else:
        # Disable GPS-dependent features
        self.gps_available = False
        # Show appropriate UI indicators
```

### 6. Lane Manager Adaptations

For LMD/MSD projects, lane manager should focus on lane fixes only:

```python
class LaneManager:
    def __init__(self, plate: str, fileid_folder: Path, end_time: datetime = None, has_gps: bool = True):
        self.plate = plate
        self.fileid_folder = fileid_folder
        self.has_gps = has_gps
        self.end_time = end_time
        self.lane_fixes = []

    def save_lane_fixes(self, filepath: str):
        """Save lane fixes to CSV (main output for LMD/MSD)"""
        # Existing save logic, ensure it works without GPS data
        pass
```

## Implementation Steps

### Phase 1: Core Infrastructure
1. ✅ Add `DataType` enum and detection logic
2. ✅ Extend `DataLoader` with multiple load methods
3. ✅ Update `GPSData` to handle missing GPS data
4. ✅ Modify UI components to handle GPS-less projects

### Phase 2: LMD Support
1. Implement `_load_lmd_data()` method
2. Test with sample LMD data: `J:\Testing\250584 HTAUPO_LMD_25\Photos`
3. Update UI to show appropriate messages for GPS-less projects
4. Ensure lane fixes saving works correctly

### Phase 3: MSD Support
1. Implement `_load_msd_data()` method
2. Identify MSD folder structure patterns
3. Test with MSD sample data
4. Ensure compatibility with existing lane fix workflows

### Phase 4: Testing & Validation
1. Unit tests for each data type detection
2. Integration tests with sample data
3. UI/UX testing for GPS-less projects
4. Performance testing with large image sets

## Migration Strategy

### Backward Compatibility
- Existing LCMS projects continue to work unchanged
- No breaking changes to current API
- Automatic data type detection

### User Experience
- Clear indication when GPS data is not available
- Appropriate UI adaptations for different project types
- Consistent lane fixing workflow across all data types

## File Structure Changes

```
app/utils/
├── data_loader.py          # Extended with multiple data type support
├── image_utils.py          # Enhanced metadata extraction
└── settings_manager.py     # Project type preferences

app/models/
├── gps_model.py            # GPSData handles missing GPS
├── event_model.py          # Event handling for GPS-less projects
└── lane_model.py           # Lane fixes as primary output

app/ui/
├── photo_preview_tab.py    # Minimap adaptations
├── timeline_widget.py      # GPS-less timeline handling
└── event_editor.py         # Event creation for GPS-less projects
```

## Testing Checklist

- [ ] LCMS projects load correctly (regression test)
- [ ] LMD projects load from `Photos/` folder
- [ ] MSD projects load from `Images/` folder (when structure known)
- [ ] Minimap shows appropriate message for GPS-less projects
- [ ] Lane fixes save correctly for all project types
- [ ] Timeline functions without GPS data
- [ ] Event creation works for GPS-less projects
- [ ] Data type detection is accurate
- [ ] Performance is acceptable with large image sets

## Future Considerations

1. **GPS Data Import**: Allow manual GPS data import for LMD/MSD projects
2. **Metadata Enhancement**: Extract more metadata from image EXIF data
3. **Batch Processing**: Support processing multiple projects of different types
4. **Data Validation**: Enhanced validation for different data structures
5. **Export Options**: Additional export formats for different project types</content>
<parameter name="filePath">c:\Users\du\Desktop\PyDeveloper\GeoEvent Ver2\DATA_STRUCTURE_EXTENSION_GUIDE.md