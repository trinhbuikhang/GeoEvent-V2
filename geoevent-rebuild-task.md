# GeoEvent Application - Complete Rebuild Task

## Executive Summary
Rebuild GeoEvent as a PyQt6-based road survey event coding application with GPS-synchronized timeline, focusing on stability, performance, and user experience. The application processes road survey data from GPS logs (.driveevt, .driveiri) and images to enable systematic event coding and lane assignment.

---

## PART 1: CORE REQUIREMENTS & DATA MODEL

### 1.1 Primary Use Cases (Priority Order)
1. **Event Timeline Management** - GPS-synchronized visualization and editing of road events
2. **Image Navigation** - Browse survey photos with GPS coordinate extraction
3. **Lane Assignment** - Code lane changes with conflict detection
4. **Multi-FileID Processing** - Sequential processing of multiple survey folders
5. **Data Export** - Export coded events and lane assignments to CSV

### 1.2 Data Sources & Parsing Logic

#### A. .driveevt File (Event Data)
**Format:** CSV with UTF-8 encoding
```
SessionToken,Distance,Chainage,Time,TimeUtc,Event,IsSpanEvent,SpanEvent,IsSpanStartEvent,IsSpanEndEvent
25100208201377,1171.65,1171.65,10/02/2025 08:22:53,10/01/2025 19:22:53,Speed Hump Start,True,Speed Hump,True,False
25100208201377,1187.75,1187.75,10/02/2025 08:23:39,10/01/2025 19:23:39,Speed Hump End,True,Speed Hump,False,True
```

**Parsing Requirements:**
- All events are span events (pairs of Start/End records)
- Match Start and End by `SpanEvent` name to create complete event objects
- Parse timestamps: `DD/MM/YYYY HH:MM:SS` format
- Convert `SessionToken` to `FileID` (add "0D" prefix if needed)
- Handle missing files: Auto-create empty .driveevt with header if not exists

**Event Object Structure:**
```python
{
    'event_id': str,           # Unique identifier
    'event_name': str,         # From SpanEvent field
    'start_time': datetime,    # From Start record Time
    'end_time': datetime,      # From End record Time
    'start_chainage': float,   # meters
    'end_chainage': float,     # meters
    'start_lat': float,        # From GPS enrichment
    'start_lon': float,        # From GPS enrichment
    'end_lat': float,          # From GPS enrichment
    'end_lon': float,          # From GPS enrichment
    'file_id': str,            # Source FileID
    'color': str,              # Display color
    'layer': int               # Display layer (0-based)
}
```

#### B. .driveiri File (GPS/IRI Data)
**Format:** CSV with UTF-8 encoding
```
Session,System,GPSDateTime,Elevation [m],HDOP,Quality,Unix,Position (begin) (LAT),Position (begin) (LON),AverageSpeed [km/h],StartChainage [km],EndChainage [km],IRI Left [m/km],IRI Right [m/km]
25100208201377,ICC77,10/1/2025 7:20:13 PM,17.389,,RTKFloat,1759346413.35,-43.51759368,172.66081272,0,0.000,0.001,5.08,0.73
```

**Parsing Requirements:**
- Parse timestamp: `M/D/YYYY H:MM:SS AM/PM` format → convert to datetime
- Convert chainage: kilometers → meters (multiply by 1000)
- Extract GPS coordinates: `Position (begin) (LAT)` and `(LON)`
- Calculate timeline bounds: `min/max(StartChainage)` for space range
- Cache parsed data for performance (lazy loading)

**GPS Enrichment Logic:**
```python
def enrich_event_with_gps(event, gps_data):
    """
    Match event with GPS data by timestamp proximity
    - Find GPS record closest to event start_time (±30 seconds tolerance)
    - Interpolate coordinates if between two GPS points
    - Add start_lat, start_lon, end_lat, end_lon to event
    """
```

#### C. Image Files
**Filename Format:** 
```
ProjectID-YYYY-MM-DD-HH-MM-SS-mmm-Lat-Lon-Bearing-Speed-Plate-FileID-Chainage-Distance-LE-.jpg
Example: PRJ-2025-10-02-08-22-53-123-4351.7594S-17266.0813E-045-50-QJS289-0D2510020814007700-1171.65-100-LE-.jpg
```

**Extraction Functions:**
```python
def extract_coordinates(filename):
    """
    Extract lat/lon from format: DDMM.MMMMM with direction N/S/E/W
    Example: 4351.7594S → -43.862657°
    Validation: lat ∈ [-90, 90], lon ∈ [-180, 180]
    """

def extract_timestamp(filename):
    """Parse YYYY-MM-DD-HH-MM-SS-mmm → datetime object"""

def extract_plate(filename):
    """Find 6-character alphanumeric segment (e.g., QJS289)"""
```

### 1.3 Folder Structure Requirements

**Single FileID Mode:**
```
Survey_Data/
└── 0D2510020814007700/              # FileID folder
    ├── 0D2510020814007700.driveevt   # Event data
    ├── 0D2510020814007700.driveiri   # GPS/IRI data
    └── Cam1/                          # Image folder
        ├── image_001.jpg
        └── ...
```

**Multi-FileID Mode:**
```
Survey_Parent/
├── 20251002/                         # Date folder (optional)
│   ├── 0D2510020814007700/          # FileID 1
│   │   ├── 0D2510020814007700.driveevt
│   │   ├── 0D2510020814007700.driveiri
│   │   └── Cam1/
│   └── 0D2510020920158900/          # FileID 2
│       ├── ...
└── 20251003/
    └── ...
```

**FileID Detection Logic:**
```python
def scan_fileid_folders(parent_path):
    """
    - Recursively find folders containing .driveevt files
    - Validate FileID naming pattern (alphanumeric, 16-18 chars)
    - Create empty .driveevt if missing (atomic operation with lock)
    - Return sorted list of FileID paths
    - Handle permission errors gracefully
    """
```

---

## PART 2: ARCHITECTURE & IMPLEMENTATION

### 2.1 Technology Stack
- **UI Framework:** PyQt6
- **Data Processing:** pandas (for CSV), datetime (timestamps)
- **Storage:** JSON (settings), CSV (exports)
- **Python Version:** 3.9+

### 2.2 Module Structure

```
geoevent/
├── main.py                          # Application entry point
├── requirements.txt
├── README.md
├── app/
│   ├── __init__.py
│   ├── main_window.py              # MainWindow class
│   ├── models/                      # Data models
│   │   ├── event_model.py          # Event data class
│   │   ├── gps_model.py            # GPS data class
│   │   └── lane_model.py           # Lane assignment data
│   ├── ui/
│   │   ├── photo_preview_tab.py    # Main tab widget
│   │   ├── timeline_widget.py      # GPS-synced timeline
│   │   ├── event_editor.py         # Event editing dialog
│   │   └── styles/
│   │       └── theme.qss           # Stylesheet
│   ├── utils/
│   │   ├── file_parser.py          # Parse .driveevt/.driveiri
│   │   ├── image_utils.py          # Extract info from filenames
│   │   ├── fileid_manager.py       # Multi-folder management
│   │   ├── lane_manager.py         # Lane coding logic
│   │   ├── export_manager.py       # CSV export
│   │   └── settings_manager.py     # App settings
│   └── core/
│       ├── memory_manager.py       # Memory monitoring
│       └── autosave_manager.py     # Autosave logic
└── testdata/                        # Sample data for testing
```

### 2.3 Critical Classes & Responsibilities

#### A. MainWindow (main_window.py)
```python
class MainWindow(QMainWindow):
    """
    RESPONSIBILITIES:
    - Initialize application components
    - Manage menu bar (File, Edit, View, Help)
    - Handle theme switching
    - Coordinate between managers
    
    KEY METHODS:
    - setup_ui(): Create menu, toolbar, status bar
    - load_settings(): Restore window state
    - handle_folder_selection(): Single/Multi-FileID mode selection
    """
```

#### B. PhotoPreviewTab (photo_preview_tab.py)
```python
class PhotoPreviewTab(QWidget):
    """
    RESPONSIBILITIES:
    - Display current survey image
    - Navigate images (prev/next, slider)
    - Show image metadata (timestamp, GPS, plate)
    - Sync with timeline position
    - Manage lane assignment buttons
    
    SIGNALS:
    - image_changed(index, metadata)
    - position_changed(timestamp, gps_coords)
    
    KEY METHODS:
    - load_image_folder(path)
    - navigate_to_image(index)
    - sync_to_timeline_position(timestamp)
    """
```

#### C. TimelineWidget (timeline_widget.py)
```python
class TimelineWidget(QWidget):
    """
    RESPONSIBILITIES:
    - Render timeline with GPS-synchronized events
    - Handle zoom/pan (mouse wheel, drag)
    - Event editing (drag handles, right-click menu)
    - Display event layers (prevent overlap)
    - Show current position marker
    
    SIGNALS:
    - position_clicked(timestamp, gps_coords)
    - event_modified(event_id, changes)
    - event_deleted(event_id)
    
    KEY METHODS:
    - paint_timeline(): Custom painting
    - handle_mouse_press/move/release()
    - zoom_to_range(start_time, end_time)
    - add_event(event_data)
    """
```

**Timeline Rendering Logic:**
```python
def paint_timeline(self, painter):
    # 1. Draw background and grid
    # 2. Calculate visible time range based on zoom/pan
    # 3. For each event in visible range:
    #    - Calculate x position: map timestamp to pixel
    #    - Calculate y position: layer_index * layer_height
    #    - Draw event bar with color
    #    - Draw event label if space available
    # 4. Draw current position marker
    # 5. Draw hover highlights
```

**Event Editing Logic:**
```python
def handle_event_drag(self, event_id, drag_type, new_position):
    """
    drag_type: 'start' | 'end' | 'move'
    new_position: timestamp
    
    VALIDATION:
    - Check time bounds (within survey range)
    - Check overlaps with other events
    - Enforce minimum event duration (1 second)
    
    APPLY:
    - Update event start/end time
    - Mark as modified
    - Emit event_modified signal
    - Trigger repaint
    """
```

#### D. FileIDManager (fileid_manager.py)
```python
class FileIDManager:
    """
    RESPONSIBILITIES:
    - Scan and validate FileID folders
    - Create missing .driveevt files
    - Navigate between FileIDs (next/prev)
    - Track processing state
    
    STATE PERSISTENCE:
    - Save to ~/.geoevent/fileid_state.json
    - Fields: current_fileid, processed_fileids[], last_modified
    
    KEY METHODS:
    - scan_parent_folder(path) → List[FileIDFolder]
    - get_current_fileid() → FileIDFolder
    - next_fileid() → FileIDFolder | None
    - create_empty_driveevt(path) → bool
    """
```

**Auto-Create .driveevt Logic:**
```python
def create_empty_driveevt(fileid_folder):
    """
    REQUIREMENTS:
    - Atomic operation (use temporary file + rename)
    - Thread-safe (file locking)
    - Standard header: "SessionToken,Distance,Chainage,Time,TimeUtc,Event,IsSpanEvent,SpanEvent,IsSpanStartEvent,IsSpanEndEvent"
    - Log creation to state file
    
    ERROR HANDLING:
    - Permission denied → log error, skip folder
    - Disk full → abort, show error dialog
    """
```

#### E. LaneManager (lane_manager.py)
```python
class LaneManager:
    """
    RESPONSIBILITIES:
    - Track current lane and turn state
    - Detect lane assignment conflicts (overlaps)
    - Export lane fixes to CSV
    - Merge lane fixes to master file
    
    DATA STRUCTURE:
    lane_fixes = [
        {
            'plate': str,
            'from_time': datetime,
            'to_time': datetime,
            'lane': str,  # '1'|'2'|'3'|'4'|'-1'|'TK1'|'TM2'...
            'file_id': str
        }
    ]
    
    KEY METHODS:
    - assign_lane(lane_code, timestamp)
    - start_turn(turn_type: 'TK'|'TM')
    - end_turn(timestamp)
    - check_overlap(timestamp) → bool
    - export_to_csv(output_path)
    """
```

**Lane Assignment Logic:**
```python
def assign_lane(self, lane_code, timestamp):
    """
    WORKFLOW:
    1. Check if timestamp overlaps existing period
       - If overlap: Show warning, return False
    2. If same lane as current:
       - Extend current period (no new record)
       - Return True
    3. If different lane:
       - End current period (set to_time = timestamp)
       - Start new period (set from_time = timestamp)
       - Update current_lane state
       - Return True
    
    VALIDATION:
    - Plate must be extracted from current image
    - Timestamp must be valid datetime
    - Lane code must be in valid set
    """
```

**Turn Period Logic:**
```python
def start_turn(self, turn_type):
    """
    1. Save current_lane to turn_start_lane
    2. End current lane period
    3. Set turn_active = True
    """

def end_turn(self, timestamp):
    """
    1. Create combined code: f"{turn_type}{turn_start_lane}"
       Example: TK1 (Turn Left from Lane 1)
    2. Add lane fix record with combined code
    3. Resume lane from turn_start_lane
    4. Set turn_active = False
    """
```

### 2.4 Data Flow Diagrams

#### Flow 1: Application Startup
```
User Launches App
    ↓
MainWindow.__init__()
    ↓
Load Settings (window size, theme, last folder)
    ↓
Initialize Managers (Memory, AutoSave, FileID)
    ↓
Create PhotoPreviewTab (central widget)
    ↓
Show MainWindow (maximized)
    ↓
[Wait for User Action]
```

#### Flow 2: Load Data Folder
```
User Selects Folder
    ↓
FileIDManager.scan_parent_folder()
    ├─→ Find .driveevt files
    ├─→ Create missing .driveevt files
    └─→ Return sorted FileID list
    ↓
Load First FileID
    ↓
Parse .driveevt → events[]
    ↓
Parse .driveiri → gps_data[]
    ↓
Enrich events with GPS coordinates
    ↓
Load Image Folder → image_paths[]
    ↓
TimelineWidget.set_events(events)
    ↓
PhotoPreviewTab.load_images(image_paths)
    ↓
Display First Image + Timeline
```

#### Flow 3: Event Editing
```
User Clicks Timeline Position
    ↓
TimelineWidget.handle_mouse_press()
    ↓
Detect Event at Position
    ├─→ No Event: Show "Add Event" menu
    └─→ Event Found: Show "Edit/Delete" menu
    ↓
User Selects "Edit"
    ↓
EventEditor Dialog Opens
    ├─→ Show event name, start/end times
    ├─→ Allow drag handles on mini-timeline
    └─→ Real-time validation
    ↓
User Clicks "Save"
    ↓
Validate Changes (no overlaps)
    ├─→ Invalid: Show error, keep dialog open
    └─→ Valid: Apply changes
    ↓
Mark Event as Modified
    ↓
TimelineWidget.repaint()
    ↓
AutoSaveManager.schedule_save()
```

#### Flow 4: Lane Assignment
```
User Navigates to Image
    ↓
PhotoPreviewTab displays image + metadata
    ↓
Extract Plate from Filename
    ↓
User Clicks Lane Button (e.g., "Lane 2")
    ↓
LaneManager.assign_lane('2', current_timestamp)
    ↓
Check Overlap with Existing Periods
    ├─→ Overlap Found: Show warning dialog
    └─→ No Overlap: Continue
    ↓
Check if Same Lane as Current
    ├─→ Same: Extend period (silent)
    └─→ Different: End current, start new
    ↓
Update UI (highlight active lane button)
    ↓
AutoSaveManager.schedule_save()
```

---

## PART 3: CRITICAL FIXES & IMPROVEMENTS

### 3.1 Performance Issues

**Problem 1: Slow Timeline Rendering**
- Current: Repaints all events on every mouse move
- **Solution:**
  ```python
  # Implement viewport culling
  def get_visible_events(self, viewport_start_time, viewport_end_time):
      return [e for e in self.events 
              if e['end_time'] >= viewport_start_time 
              and e['start_time'] <= viewport_end_time]
  
  # Only repaint on zoom/pan completion
  def paintEvent(self, event):
      visible = self.get_visible_events(self.view_start, self.view_end)
      self.render_events(visible)  # Only render visible subset
  ```

**Problem 2: GPS Data Loading Delays**
- Current: Loads entire .driveiri on startup
- **Solution:**
  ```python
  # Lazy load GPS segments
  class GPSDataCache:
      def __init__(self, driveiri_path):
          self.path = driveiri_path
          self.cache = {}  # {time_range: gps_data}
      
      def get_gps_for_range(self, start_time, end_time):
          key = (start_time, end_time)
          if key not in self.cache:
              self.cache[key] = self._load_segment(start_time, end_time)
          return self.cache[key]
  ```

**Problem 3: Image Loading Bottleneck**
- Current: Loads full-resolution images every navigation
- **Solution:**
  ```python
  # Implement image cache with size limit
  class ImageCache:
      def __init__(self, max_cache_mb=500):
          self.cache = OrderedDict()  # LRU cache
          self.max_bytes = max_cache_mb * 1024 * 1024
          self.current_bytes = 0
      
      def get_image(self, path):
          if path in self.cache:
              self.cache.move_to_end(path)  # Mark as recently used
              return self.cache[path]
          
          image = self._load_and_resize(path, max_width=1920)
          self._add_to_cache(path, image)
          return image
      
      def _add_to_cache(self, path, image):
          image_bytes = image.size().width() * image.size().height() * 4
          while self.current_bytes + image_bytes > self.max_bytes:
              self._evict_oldest()
          self.cache[path] = image
          self.current_bytes += image_bytes
  ```

### 3.2 Stability Issues

**Problem 1: Crash on Large Event Sets**
- Current: No memory monitoring
- **Solution:**
  ```python
  class MemoryMonitor(QThread):
      memory_warning = pyqtSignal(int)  # percentage
      
      def run(self):
          while True:
              usage = psutil.virtual_memory().percent
              if usage > 80:
                  self.memory_warning.emit(usage)
              time.sleep(5)
  
  # In MainWindow
  def handle_memory_warning(self, usage):
      if usage > 90:
          self.image_cache.clear()
          self.gps_cache.clear()
          QMessageBox.warning(self, "Memory Warning", 
              f"High memory usage ({usage}%). Cleared caches.")
  ```

**Problem 2: Race Conditions in FileID Navigation**
- Current: No thread safety
- **Solution:**
  ```python
  from threading import Lock
  
  class FileIDManager:
      def __init__(self):
          self.lock = Lock()
          self.current_index = 0
          self.fileid_list = []
      
      def next_fileid(self):
          with self.lock:
              if self.current_index < len(self.fileid_list) - 1:
                  self.current_index += 1
                  return self.fileid_list[self.current_index]
              return None
  ```

**Problem 3: Data Corruption on Autosave**
- Current: Overwrites file directly
- **Solution:**
  ```python
  def autosave(self, data, filepath):
      # Atomic write: temp file + rename
      temp_path = filepath + ".tmp"
      try:
          with open(temp_path, 'w', encoding='utf-8') as f:
              json.dump(data, f, indent=2)
          os.replace(temp_path, filepath)  # Atomic on POSIX
      except Exception as e:
          if os.path.exists(temp_path):
              os.remove(temp_path)
          raise e
  ```

### 3.3 Usability Issues

**Problem 1: No Visual Feedback on Lane Assignment**
- **Solution:**
  ```python
  # Add visual indicator on timeline
  class TimelineWidget:
      def paint_lane_periods(self, painter):
          for period in self.lane_manager.get_lane_fixes():
              start_x = self.time_to_pixel(period['from_time'])
              end_x = self.time_to_pixel(period['to_time'])
              
              # Draw colored bar below timeline
              color = self.get_lane_color(period['lane'])
              painter.fillRect(start_x, self.height() - 20, 
                              end_x - start_x, 15, color)
  ```

**Problem 2: Difficult Event Editing**
- **Solution:**
  ```python
  # Add snap-to-grid when dragging events
  def snap_time_to_grid(self, timestamp, grid_seconds=1):
      epoch = timestamp.timestamp()
      snapped = round(epoch / grid_seconds) * grid_seconds
      return datetime.fromtimestamp(snapped)
  
  # Add visual guides when dragging
  def paint_drag_guides(self, painter):
      if self.dragging_event:
          # Draw vertical line at drag position
          painter.setPen(QPen(QColor(255, 0, 0), 2, Qt.DashLine))
          painter.drawLine(self.drag_x, 0, self.drag_x, self.height())
          
          # Show time label
          time_str = self.pixel_to_time(self.drag_x).strftime("%H:%M:%S")
          painter.drawText(self.drag_x + 5, 15, time_str)
  ```

**Problem 3: No Undo for Lane Assignments**
- **Solution:**
  ```python
  class UndoRedoManager:
      def __init__(self):
          self.undo_stack = []
          self.redo_stack = []
      
      def push_action(self, action_type, old_state, new_state):
          action = {
              'type': action_type,  # 'lane_assign', 'event_edit', etc.
              'old': old_state,
              'new': new_state,
              'timestamp': datetime.now()
          }
          self.undo_stack.append(action)
          self.redo_stack.clear()
      
      def undo(self):
          if self.undo_stack:
              action = self.undo_stack.pop()
              self._apply_state(action['old'])
              self.redo_stack.append(action)
      
      def redo(self):
          if self.redo_stack:
              action = self.redo_stack.pop()
              self._apply_state(action['new'])
              self.undo_stack.append(action)
  ```

---

## PART 4: TESTING & VALIDATION

### 4.1 Unit Tests

**Test: Event Parsing**
```python
def test_parse_driveevt():
    # Given: .driveevt with span event pairs
    sample_csv = """
SessionToken,Distance,Chainage,Time,TimeUtc,Event,IsSpanEvent,SpanEvent,IsSpanStartEvent,IsSpanEndEvent
25100208201377,100.0,100.0,10/02/2025 08:22:53,10/01/2025 19:22:53,Bridge Start,True,Bridge,True,False
25100208201377,150.0,150.0,10/02/2025 08:23:00,10/01/2025 19:23:00,Bridge End,True,Bridge,False,True
"""
    
    # When: Parse events
    events = parse_driveevt(sample_csv)
    
    # Then: Should create 1 complete event
    assert len(events) == 1
    assert events[0]['event_name'] == 'Bridge'
    assert events[0]['start_chainage'] == 100.0
    assert events[0]['end_chainage'] == 150.0
```

**Test: Lane Overlap Detection**
```python
def test_lane_overlap_detection():
    manager = LaneManager()
    
    # Given: Existing lane period
    manager.assign_lane('1', datetime(2025, 1, 1, 10, 0, 0))
    manager.assign_lane('2', datetime(2025, 1, 1, 10, 5, 0))
    
    # When: Try to assign overlapping period
    result = manager.assign_lane('3', datetime(2025, 1, 1, 10, 3, 0))
    
    # Then: Should detect overlap
    assert result == False
```

**Test: FileID Auto-Create**
```python
def test_create_empty_driveevt(tmp_path):
    # Given: Folder without .driveevt
    fileid_folder = tmp_path / "0D2510020814007700"
    fileid_folder.mkdir()
    
    # When: Create empty file
    result = create_empty_driveevt(fileid_folder)
    
    # Then: File should exist with correct header
    assert result == True
    driveevt_path = fileid_folder / "0D2510020814007700.driveevt"
    assert driveevt_path.exists()
    with open(driveevt_path) as f:
        header = f.readline().strip()
        assert header == "SessionToken,Distance,Chainage,Time,TimeUtc,Event,IsSpanEvent,SpanEvent,IsSpanStartEvent,IsSpanEndEvent"
```

### 4.2 Integration Tests

**Test: Full Workflow - Load to Export**
```python
def test_full_workflow(test_data_folder):
    # 1. Load folder
    app = QApplication([])
    window = MainWindow()
    window.load_folder(test_data_folder)
    
    # 2. Verify data loaded
    assert len(window.photo_tab.timeline.events) > 0
    assert len(window.photo_tab.image_paths) > 0
    
    # 3. Navigate images
    window.photo_tab.navigate_to_image(5)
    assert window.photo_tab.current_index == 5
    
    # 4. Assign lane
    window.photo_tab.lane_manager.assign_lane('2', window.photo_tab.current_timestamp)
    assert len(window.photo_tab.lane_manager.lane_fixes) == 1
    
    # 5. Export
    output_path = test_data_folder / "export.csv"
    window.photo_tab.lane_manager.export_to_csv(output_path)
    assert output_path.exists()
    
    # 6. Verify export format
    df = pd.read_csv(output_path)
    assert 'Plate' in df.columns
    assert 'Lane' in df.columns
```

### 4.3 Performance Benchmarks

**Timeline Rendering:**
- Target: < 16ms per frame (60 FPS)
- Test with 1000+ events
- Measure with `QElapsedTimer`

**Image Loading:**
- Target: < 200ms per image
- Test with 1920x1080 JPEGs
- Cache hit ratio > 80%

**GPS Data Parsing:**
- Target: < 1 second for 10k GPS points
- Test with real .driveiri files

---

## PART 5: IMPLEMENTATION PRIORITIES

### Phase 1: Core Data Layer (Week 1)
1. Implement data models (Event, GPS, Lane)
2. Create file parsers (.driveevt, .driveiri, images)
3. Write unit tests for parsing logic
4. Implement FileIDManager with auto-create

**Deliverable:** Can load and parse all data files correctly

### Phase 2: Timeline Widget (Week 2)
1. Create TimelineWidget with basic rendering
2. Implement zoom/pan controls
3. Add event display with layers
4. Implement event editing (drag handles)
5. Add GPS synchronization

**Deliverable:** Functional timeline with event editing

### Phase 3: Image Navigation (Week 3)
1. Create PhotoPreviewTab with image display
2. Implement navigation controls (prev/next, slider)
3. Extract and display image metadata
4. Sync with timeline position

**Deliverable:** Can browse images with timeline sync

### Phase 4: Lane Coding (Week 4)
1. Implement LaneManager with overlap detection
2. Create lane assignment UI (buttons, status display)
3. Add turn period handling (TK/TM)
4. Implement CSV export

**Deliverable:** Complete lane coding workflow

### Phase 5: Polish & Integration (Week 5)
1. Implement MemoryManager and AutoSaveManager
2. Add UndoRedoManager for all operations
3. Create settings dialog and persistence
4. Add keyboard shortcuts
5. Implement error handling and logging

**Deliverable:** Stable, production-ready application

---

## PART 6: UI/UX SPECIFICATIONS

### 6.1 Main Window Layout

```
┌─────────────────────────────────────────────────────────┐
│ File  Edit  View  Tools  Help                    [Theme]│ Menu Bar
├─────────────────────────────────────────────────────────┤
│ [Open Folder] [◀ Prev FileID] [Next FileID ▶]          │ Toolbar
│ FileID: 0D2510020814007700  (2/15)                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│              ┌───────────────────────┐                  │
│              │                       │                  │
│              │   Current Image       │                  │
│              │   (Photo Preview)     │                  │ Main Area
│              │                       │                  │
│              │   1920 x 1080         │                  │
│              └───────────────────────┘                  │
│                                                         │
│  Timestamp: 10/02/2025 08:22:53.123                    │
│  GPS: -43.51759°, 172.66081°    Plate: QJS289          │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  Image: [◀◀] [◀] ═══■═══════════════════ [▶] [▶▶]      │ Navigation
│         [1    /    1547]                                │
├─────────────────────────────────────────────────────────┤
│  Lane: [Lane 1] [Lane 2] [Lane 3] [Lane 4] [Ignore]    │ Lane Coding
│  Turn: [TK ↰] [TM ↱]     Current: Lane 2               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │        Timeline (GPS Synchronized)                │ │
│  │ ┌─────────────────────────────────────────────┐   │ │
│  │ │ [Bridge]     [Speed Hump]    [Intersection] │   │ │ Timeline
│  │ │ ▬▬▬▬▬▬▬▬▬    ▬▬▬▬▬▬▬         ▬▬▬▬▬▬▬▬▬▬     │   │ │
│  │ │ ─────────────────■─────────────────────────  │   │ │
│  │ │ 08:20    08:25    08:30    08:35    08:40   │   │ │
│  │ └─────────────────────────────────────────────┘   │ │
│  │ [Zoom: ────■────] [Time] [Space]  [Add Event]    │ │
│  └───────────────────────────────────────────────────┘ │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ Status: Ready │ Memory: 45% │ Autosave: 2 min ago      │ Status Bar
└─────────────────────────────────────────────────────────┘
```

### 6.2 Color Scheme & Styling

**Event Colors (by type):**
- Bridge: `#3498DB` (Blue)
- Speed Hump: `#E74C3C` (Red)
- Intersection: `#F39C12` (Orange)
- Road Works: `#9B59B6` (Purple)
- Roundabout: `#1ABC9C` (Teal)
- Default: `#95A5A6` (Gray)

**Lane Colors:**
- Lane 1: `#2ECC71` (Green)
- Lane 2: `#3498DB` (Blue)
- Lane 3: `#F39C12` (Orange)
- Lane 4: `#E74C3C` (Red)
- Ignore: `#7F8C8D` (Dark Gray)
- Turn (TK/TM): `#9B59B6` (Purple)

**Theme: Modern Dark (Default)**
```css
/* Main background */
background-color: #2C3E50;
color: #ECF0F1;

/* Widgets */
QWidget {
    background-color: #34495E;
    border-radius: 4px;
}

/* Buttons */
QPushButton {
    background-color: #3498DB;
    color: white;
    padding: 8px 16px;
    border: none;
    border-radius: 4px;
}

QPushButton:hover {
    background-color: #2980B9;
}

QPushButton:pressed {
    background-color: #1F618D;
}

/* Timeline */
TimelineWidget {
    background-color: #1E2A38;
    border: 1px solid #3E4E5E;
}
```

### 6.3 Keyboard Shortcuts

**Navigation:**
- `Space`: Play/Pause slideshow
- `←` / `→`: Previous/Next image
- `Home` / `End`: First/Last image
- `Page Up` / `Page Down`: Jump 10 images
- `Ctrl + G`: Go to image number

**Lane Coding:**
- `1` - `4`: Assign Lane 1-4
- `0`: Assign Ignore
- `[`: Start Turn Left (TK)
- `]`: Start Turn Right (TM)
- `Backspace`: Undo last assignment

**Timeline:**
- `+` / `-`: Zoom in/out
- `Ctrl + Mouse Wheel`: Zoom at cursor
- `Middle Mouse Drag`: Pan timeline
- `Ctrl + Click`: Add event at position
- `Delete`: Delete selected event

**General:**
- `Ctrl + S`: Save
- `Ctrl + Z`: Undo
- `Ctrl + Shift + Z`: Redo
- `Ctrl + O`: Open folder
- `Ctrl + E`: Export data
- `F1`: Help
- `F11`: Toggle fullscreen

### 6.4 Dialogs & Popups

#### Event Editor Dialog
```
┌─────────────────────────────────────┐
│ Edit Event: Bridge           [X]    │
├─────────────────────────────────────┤
│                                     │
│ Event Name: [Bridge        ▼]       │
│                                     │
│ Start Time: [10/02/25 08:22:53.123] │
│ End Time:   [10/02/25 08:23:00.456] │
│                                     │
│ Duration: 7.333 seconds             │
│ Length: 50.0 meters                 │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │    Mini Timeline                │ │
│ │ [───────■═══■───────────]       │ │
│ │  (Drag handles to adjust)       │ │
│ └─────────────────────────────────┘ │
│                                     │
│ Start GPS: -43.51759, 172.66081     │
│ End GPS:   -43.51765, 172.66085     │
│                                     │
│ Color: [■] [Change]                 │
│                                     │
│        [Cancel]  [Save]             │
└─────────────────────────────────────┘
```

#### Lane Assignment Conflict Dialog
```
┌─────────────────────────────────────┐
│ Lane Assignment Conflict      [!]   │
├─────────────────────────────────────┤
│                                     │
│ Cannot assign lane at this time.   │
│                                     │
│ Overlapping period:                 │
│ • From: 10/02/25 08:20:00.000       │
│ • To:   10/02/25 08:25:00.000       │
│ • Lane: Lane 2                      │
│ • Plate: QJS289                     │
│                                     │
│ Options:                            │
│ ○ Adjust existing period            │
│ ○ Cancel new assignment             │
│                                     │
│        [Go to Conflict]  [OK]       │
└─────────────────────────────────────┘
```

#### Export Dialog
```
┌─────────────────────────────────────┐
│ Export Data                   [X]   │
├─────────────────────────────────────┤
│                                     │
│ Export Type:                        │
│ ☑ Lane Fixes (CSV)                  │
│ ☑ Events (CSV)                      │
│ ☐ GPS Data (CSV)                    │
│                                     │
│ Output Folder:                      │
│ [C:\Surveys\Export\  ] [Browse]     │
│                                     │
│ Filename Pattern:                   │
│ ○ Use default (laneFixes-DATE.csv) │
│ ○ Custom: [_____________]           │
│                                     │
│ Options:                            │
│ ☑ Include FileID in filename        │
│ ☑ Merge to master file              │
│ ☐ Open folder after export          │
│                                     │
│ Summary:                            │
│ • Lane fixes: 127 records           │
│ • Events: 45 records                │
│ • FileID: 0D2510020814007700        │
│                                     │
│        [Cancel]  [Export]           │
└─────────────────────────────────────┘
```

---

## PART 7: ERROR HANDLING & EDGE CASES

### 7.1 File System Errors

**Error: Permission Denied**
```python
def handle_permission_error(filepath):
    """
    Scenario: Cannot read/write file due to permissions
    
    Response:
    1. Log error with full path
    2. Show user-friendly dialog:
       "Cannot access file: {filename}
        Please check file permissions."
    3. Skip file and continue processing
    4. Add to error report
    """
```

**Error: Disk Full**
```python
def handle_disk_full_error():
    """
    Scenario: Cannot save due to insufficient disk space
    
    Response:
    1. Stop autosave immediately
    2. Show critical warning:
       "Disk space full! Cannot save changes.
        Free up space and try again."
    3. Disable autosave until space available
    4. Keep data in memory
    """
```

**Error: File Corruption**
```python
def handle_corrupted_file(filepath):
    """
    Scenario: CSV file has invalid format or encoding
    
    Response:
    1. Attempt to recover partial data:
       - Try different encodings (UTF-8, Latin-1, Windows-1252)
       - Skip malformed rows, log line numbers
    2. Show warning:
       "File partially corrupted: {filename}
        Loaded {n} of {m} records. See error log."
    3. Create backup of original file (.corrupted)
    4. Continue with recovered data
    """
```

### 7.2 Data Validation Errors

**Error: Invalid Timestamp Format**
```python
def parse_timestamp_safe(timestamp_str):
    """
    Scenario: Timestamp doesn't match expected format
    
    Formats to try (in order):
    1. "DD/MM/YYYY HH:MM:SS"
    2. "DD/MM/YYYY HH:MM:SS.mmm"
    3. "M/D/YYYY H:MM:SS AM/PM"
    4. ISO 8601
    
    If all fail:
    - Log warning with original string
    - Return None
    - Skip record with error note
    """
```

**Error: GPS Coordinates Out of Range**
```python
def validate_coordinates(lat, lon):
    """
    Scenario: Extracted coordinates are invalid
    
    Validation:
    - Latitude: -90 <= lat <= 90
    - Longitude: -180 <= lon <= 180
    
    If invalid:
    - Log warning with values
    - Set to None (mark as missing GPS)
    - Event still created, but no GPS enrichment
    """
```

**Error: Missing Span Event End**
```python
def handle_orphan_span_event(start_event):
    """
    Scenario: Found Start event but no matching End
    
    Response:
    1. Log warning: "Orphan span event: {event_name} at {time}"
    2. Try to infer end:
       - Use next event start as end (common in real data)
       - Or use start + 10 seconds as default
    3. Mark event as "incomplete" in metadata
    4. Show in UI with distinct color (yellow)
    """
```

### 7.3 UI State Errors

**Error: Timeline Overflow**
```python
def handle_timeline_overflow():
    """
    Scenario: Too many events to render efficiently
    
    Response:
    1. Detect when event count > 10,000
    2. Switch to "aggregated view" mode:
       - Group nearby events into clusters
       - Show cluster count instead of individual bars
    3. Show notification:
       "Large dataset detected. Switched to aggregated view.
        Zoom in to see individual events."
    """
```

**Error: Image Load Failure**
```python
def handle_image_load_error(image_path):
    """
    Scenario: Cannot load/decode image file
    
    Response:
    1. Log error with path and exception
    2. Show placeholder image with text:
       "Cannot load image
        {filename}"
    3. Metadata still extracted from filename
    4. Navigation continues to work
    5. Add to error report
    """
```

**Error: Memory Limit Exceeded**
```python
def handle_memory_limit():
    """
    Scenario: Application memory usage > 90%
    
    Response:
    1. Clear image cache
    2. Clear GPS cache
    3. Force garbage collection
    4. Show warning:
       "Memory usage high. Cleared caches to free memory."
    5. If still > 90%:
       - Disable image preview temporarily
       - Show critical warning
       - Suggest closing other applications
    """
```

### 7.4 Data Consistency Errors

**Error: Duplicate Event IDs**
```python
def resolve_duplicate_event_ids(events):
    """
    Scenario: Multiple events have same ID (data corruption)
    
    Response:
    1. Detect duplicates in loaded events
    2. Regenerate IDs: f"{event_name}_{start_time}_{random}"
    3. Log warning with original IDs
    4. Mark events as "ID regenerated" in metadata
    5. Continue processing
    """
```

**Error: Overlapping Lane Periods (in loaded data)**
```python
def detect_lane_overlaps(lane_fixes):
    """
    Scenario: Loaded CSV has overlapping periods (historical data issue)
    
    Response:
    1. Scan for overlaps on load
    2. Show dialog:
       "Detected {n} overlapping lane periods.
        Options:
        - Keep latest assignment
        - Keep earliest assignment
        - Manual review"
    3. Apply user choice
    4. Mark resolved overlaps in export metadata
    """
```

---

## PART 8: LOGGING & DEBUGGING

### 8.1 Logging Configuration

```python
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    """
    Configure application logging
    
    Logs location: ~/.geoevent/logs/
    Files:
    - geoevent.log: General application log
    - errors.log: Errors only
    - performance.log: Performance metrics
    """
    log_dir = Path.home() / ".geoevent" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # General log
    general_handler = RotatingFileHandler(
        log_dir / "geoevent.log",
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    general_handler.setLevel(logging.INFO)
    general_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # Error log
    error_handler = RotatingFileHandler(
        log_dir / "errors.log",
        maxBytes=5*1024*1024,
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    ))
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(general_handler)
    root_logger.addHandler(error_handler)
    
    # Console handler (only warnings and errors)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter(
        '%(levelname)s: %(message)s'
    ))
    root_logger.addHandler(console_handler)
```

### 8.2 Performance Logging

```python
import time
from functools import wraps

def log_performance(func):
    """
    Decorator to log function execution time
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        
        perf_logger = logging.getLogger('performance')
        perf_logger.info(f"{func.__name__}: {elapsed*1000:.2f}ms")
        
        # Warn if slow
        if elapsed > 0.5:  # 500ms threshold
            perf_logger.warning(f"SLOW: {func.__name__} took {elapsed:.2f}s")
        
        return result
    return wrapper

# Usage
class FileParser:
    @log_performance
    def parse_driveevt(self, filepath):
        # ... parsing logic ...
        pass
```

### 8.3 Debug Mode

```python
class DebugManager:
    """
    Enable debug features via command-line or settings
    
    Usage: python main.py --debug
    """
    def __init__(self, enabled=False):
        self.enabled = enabled
        if enabled:
            self._setup_debug_logging()
            self._enable_debug_widgets()
    
    def _setup_debug_logging(self):
        logging.getLogger().setLevel(logging.DEBUG)
        
    def _enable_debug_widgets(self):
        """Add debug panels to UI"""
        # Timeline debug overlay
        self.timeline_debug = True  # Show pixel coordinates, event IDs
        
        # Memory monitor widget
        self.show_memory_graph = True
        
        # Performance overlay
        self.show_fps_counter = True
    
    def log_event_details(self, event):
        """Detailed event logging in debug mode"""
        if self.enabled:
            logging.debug(f"Event Details:")
            logging.debug(f"  ID: {event['event_id']}")
            logging.debug(f"  Name: {event['event_name']}")
            logging.debug(f"  Start: {event['start_time']}")
            logging.debug(f"  End: {event['end_time']}")
            logging.debug(f"  GPS: ({event.get('start_lat')}, {event.get('start_lon')})")
```

---

## PART 9: CONFIGURATION & SETTINGS

### 9.1 Application Settings (JSON)

**Location:** `~/.geoevent/settings.json`

```json
{
  "version": "1.0.0",
  "window": {
    "width": 1920,
    "height": 1080,
    "maximized": true,
    "theme": "dark"
  },
  "folders": {
    "last_opened": "/path/to/survey/data",
    "recent": [
      "/path/to/survey1",
      "/path/to/survey2"
    ],
    "max_recent": 10
  },
  "timeline": {
    "default_zoom": 1.0,
    "auto_sync_gps": true,
    "show_event_labels": true,
    "event_layer_height": 25,
    "max_events_before_aggregate": 10000
  },
  "image_preview": {
    "cache_size_mb": 500,
    "slideshow_interval_ms": 1000,
    "auto_extract_metadata": true
  },
  "lane_coding": {
    "auto_extract_plate": true,
    "warn_on_overlap": true,
    "default_travel_direction": "N"
  },
  "export": {
    "default_folder": "/path/to/exports",
    "include_fileid": true,
    "merge_to_master": true,
    "filename_pattern": "laneFixes-{date}.csv"
  },
  "performance": {
    "max_memory_usage_percent": 85,
    "enable_lazy_loading": true,
    "cache_gps_segments": true
  },
  "autosave": {
    "enabled": true,
    "interval_seconds": 120,
    "keep_backups": 5
  },
  "debug": {
    "enabled": false,
    "log_level": "INFO",
    "show_performance_overlay": false
  }
}
```

### 9.2 Settings Manager

```python
class SettingsManager:
    """Manage application settings with validation"""
    
    DEFAULT_SETTINGS = { ... }  # From above JSON
    
    def __init__(self):
        self.settings_path = Path.home() / ".geoevent" / "settings.json"
        self.settings = self.load_settings()
    
    def load_settings(self):
        """Load settings with fallback to defaults"""
        try:
            if self.settings_path.exists():
                with open(self.settings_path, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults (for new keys)
                    return self._merge_settings(self.DEFAULT_SETTINGS, loaded)
            else:
                return self.DEFAULT_SETTINGS.copy()
        except Exception as e:
            logging.error(f"Cannot load settings: {e}. Using defaults.")
            return self.DEFAULT_SETTINGS.copy()
    
    def save_settings(self):
        """Atomic save with backup"""
        try:
            # Create backup
            if self.settings_path.exists():
                backup_path = self.settings_path.with_suffix('.json.bak')
                shutil.copy(self.settings_path, backup_path)
            
            # Atomic write
            temp_path = self.settings_path.with_suffix('.json.tmp')
            with open(temp_path, 'w') as f:
                json.dump(self.settings, f, indent=2)
            os.replace(temp_path, self.settings_path)
            
        except Exception as e:
            logging.error(f"Cannot save settings: {e}")
    
    def get(self, key_path, default=None):
        """Get nested setting: 'timeline.default_zoom'"""
        keys = key_path.split('.')
        value = self.settings
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def set(self, key_path, value):
        """Set nested setting"""
        keys = key_path.split('.')
        target = self.settings
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
        target[keys[-1]] = value
        self.save_settings()
```

---

## PART 10: DEPLOYMENT & PACKAGING

### 10.1 Requirements

**requirements.txt:**
```
PyQt6==6.6.0
pandas==2.1.3
psutil==5.9.6
Pillow==10.1.0
```

**Optional (for development):**
```
pytest==7.4.3
pytest-qt==4.2.0
black==23.11.0
flake8==6.1.0
```

### 10.2 Build Script (PyInstaller)

```python
# build.py
import PyInstaller.__main__
import sys
import shutil
from pathlib import Path

def build():
    """Build standalone executable"""
    
    # Clean previous build
    if Path('dist').exists():
        shutil.rmtree('dist')
    if Path('build').exists():
        shutil.rmtree('build')
    
    # PyInstaller arguments
    args = [
        'main.py',
        '--name=GeoEvent',
        '--windowed',  # No console on Windows
        '--onefile',   # Single executable
        '--icon=resources/icon.ico',
        '--add-data=app:app',
        '--add-data=resources:resources',
        '--hidden-import=PyQt6.QtCore',
        '--hidden-import=PyQt6.QtGui',
        '--hidden-import=PyQt6.QtWidgets',
        '--clean',
    ]
    
    # Platform-specific
    if sys.platform == 'win32':
        args.append('--uac-admin')  # Request admin on Windows
    
    PyInstaller.__main__.run(args)
    
    print("Build complete: dist/GeoEvent")

if __name__ == '__main__':
    build()
```

### 10.3 Installation Package Structure

```
GeoEvent_v1.0.0/
├── GeoEvent.exe (or GeoEvent on Linux/Mac)
├── README.txt
├── LICENSE.txt
├── User_Manual.pdf
├── resources/
│   ├── icon.ico
│   └── themes/
│       ├── dark.qss
│       └── light.qss
├── testdata/
│   └── sample_survey/
│       ├── 0D2510020814007700/
│       │   ├── 0D2510020814007700.driveevt
│       │   ├── 0D2510020814007700.driveiri
│       │   └── Cam1/
│       │       └── sample_images/
│       └── README.txt
└── docs/
    ├── Quick_Start_Guide.pdf
    └── API_Documentation.pdf
```

---

## PART 11: SUCCESS CRITERIA

### 11.1 Functional Requirements (Must Have)

✅ **Data Loading:**
- [ ] Successfully parse .driveevt files (100% of valid files)
- [ ] Successfully parse .driveiri files (100% of valid files)
- [ ] Extract metadata from image filenames (95%+ success rate)
- [ ] Auto-create missing .driveevt files
- [ ] Handle multi-FileID folders

✅ **Timeline:**
- [ ] Render 1000+ events without lag (< 16ms frame time)
- [ ] GPS-synchronized positioning
- [ ] Zoom and pan smoothly
- [ ] Event editing with drag-and-drop
- [ ] Event layers prevent overlap

✅ **Image Navigation:**
- [ ] Navigate through 1000+ images smoothly
- [ ] Sync with timeline position
- [ ] Display metadata accurately
- [ ] Cache images efficiently (< 500MB memory)

✅ **Lane Coding:**
- [ ] Assign lanes with no overlaps (100% validation)
- [ ] Support turn periods (TK/TM)
- [ ] Auto-extract plate numbers (95%+ accuracy)
- [ ] Export to CSV with correct format

✅ **Stability:**
- [ ] Run for 8+ hours without crashes
- [ ] Handle 10+ FileID folders in sequence
- [ ] Recover from file permission errors
- [ ] No memory leaks (< 10MB growth per hour)

### 11.2 Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Timeline FPS | 60 | QElapsedTimer per frame |
| Image load time | < 200ms | Per-image average |
| GPS parse time | < 1s for 10k points | Total parse duration |
| Event edit latency | < 50ms | Click to visual update |
| Memory usage | < 500MB typical | Process memory monitor |
| Startup time | < 3s | Launch to UI shown |

### 11.3 User Acceptance Tests

**Test 1: Complete Survey Processing**
1. Load multi-FileID folder (10+ folders)
2. Navigate through all images
3. Code 50+ events
4. Assign lanes for 100+ images
5. Export data
6. Verify exported CSVs match expectations

**Test 2: Error Recovery**
1. Load folder with corrupted .driveevt
2. Verify partial data loaded
3. Manually fix and reload
4. Continue processing without restart

**Test 3: Performance Under Load**
1. Load survey with 5000+ images
2. Navigate at slideshow speed (1 img/sec)
3. Monitor memory usage over 30 minutes
4. Verify no degradation in performance

---

## PART 12: DELIVERABLES CHECKLIST

### Code Deliverables
- [ ] Complete source code with modular architecture
- [ ] Unit tests (80%+ code coverage)
- [ ] Integration tests for key workflows
- [ ] Performance benchmarks
- [ ] Inline code documentation (docstrings)

### Documentation
- [ ] README.md with installation instructions
- [ ] User Manual (PDF) with screenshots
- [ ] Developer Guide for future maintenance
- [ ] API Documentation (auto-generated)
- [ ] CHANGELOG.md tracking all versions

### Assets
- [ ] Application icon (multiple sizes)
- [ ] Theme files (dark, light)
- [ ] Sample test data (anonymized)
- [ ] Error message catalog

### Build Artifacts
- [ ] Standalone executable (Windows, Linux, Mac)
- [ ] Installer package with dependencies
- [ ] Quick Start Guide (PDF)
- [ ] Release notes

### Quality Assurance
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] Performance benchmarks met
- [ ] No critical/high-priority bugs
- [ ] User acceptance testing completed

---

## APPENDIX A: Common Issues & Solutions

**Issue: Timeline rendering is slow**
- Solution: Implement viewport culling, only render visible events
- Check: Are you rendering > 10k events? Switch to aggregated view

**Issue: Images not loading**
- Solution: Verify Cam1/ folder exists, check file permissions
- Check: Are filenames in correct format? Run validator

**Issue: GPS coordinates not matching**
- Solution: Verify .driveiri timestamp format, check timezone
- Check: Are coordinates in DDMM.MMMMM format?

**Issue: Lane overlaps not detected**
- Solution: Check timestamp parsing, ensure microsecond precision
- Check: Are timestamps compared correctly (datetime objects)?

**Issue: Application crashes on large datasets**
- Solution: Enable lazy loading, increase memory limit in settings
- Check: Monitor memory usage, enable image cache limits

---

## APPENDIX B: Future Enhancements (Post-MVP)

### Phase 6: Advanced Features (Optional)

**1. Map Integration**
- Embed OpenStreetMap or Google Maps
- Display survey route with GPS track
- Click map to jump to nearest image
- Overlay events on map view

**2. Advanced Analytics**
- Event frequency statistics
- Lane usage patterns
- IRI roughness visualization
- Speed profile graphs

**3. Collaborative Features**
- Multi-user event coding
- Conflict resolution for concurrent edits
- Version control for events
- Comment/annotation system

**4. Machine Learning Integration**
- Auto-detect events from images (bridges, intersections)
- Suggest lane assignments based on patterns
- Anomaly detection for IRI spikes
- Plate recognition validation

**5. Reporting Module**
- Generate PDF reports with maps and statistics
- Custom report templates
- Scheduled exports
- Email notifications

**6. Mobile Companion App**
- Real-time data upload from field surveys
- Quick event tagging during survey
- Photo capture with auto-metadata
- Offline mode with sync

---

## APPENDIX C: Data Migration & Compatibility

### C.1 Handling Legacy Data

**Scenario: Import from older GeoEvent versions**
```python
class DataMigrator:
    """Migrate data from previous formats"""
    
    def migrate_v0_to_v1(self, old_data):
        """
        Changes in v1.0:
        - Added FileID field to events
        - Changed timestamp format
        - Added GPS enrichment fields
        """
        migrated = []
        for event in old_data:
            new_event = {
                'event_id': event.get('id'),
                'event_name': event.get('name'),
                'start_time': self._parse_old_timestamp(event['start']),
                'end_time': self._parse_old_timestamp(event['end']),
                'file_id': self._infer_fileid(event),  # Add missing field
                'start_lat': None,  # Will be enriched later
                'start_lon': None,
                'color': event.get('color', '#95A5A6'),
                'layer': 0
            }
            migrated.append(new_event)
        return migrated
```

### C.2 Export Formats

**CSV Export (Lane Fixes) - Standard Format:**
```csv
Plate,From,To,Lane,Ignore,RegionID,RoadID,Travel,FileID
QJS289,01/11/25 10:00:00.000,01/11/25 10:05:00.000,1,,,N,0D2510020814007700
QJS289,01/11/25 10:05:00.000,01/11/25 10:05:30.000,TK1,,,N,0D2510020814007700
ABC123,01/11/25 10:10:00.000,01/11/25 10:15:00.000,-1,1,,N,0D2510020920158900
```

**CSV Export (Events) - Extended Format:**
```csv
EventID,EventName,StartTime,EndTime,StartChainage,EndChainage,StartLat,StartLon,EndLat,EndLon,FileID,Duration,Length
evt_001,Bridge,01/11/25 10:00:00.000,01/11/25 10:00:15.000,1171.65,1187.75,-43.51759,172.66081,-43.51765,172.66085,0D2510020814007700,15.0,16.1
evt_002,Speed Hump,01/11/25 10:05:00.000,01/11/25 10:05:10.000,2345.20,2360.50,-43.51820,172.66150,-43.51825,172.66155,0D2510020814007700,10.0,15.3
```

**JSON Export (Full State) - For Backup:**
```json
{
  "version": "1.0.0",
  "export_timestamp": "2025-11-16T10:30:00Z",
  "fileid": "0D2510020814007700",
  "events": [
    {
      "event_id": "evt_001",
      "event_name": "Bridge",
      "start_time": "2025-11-01T10:00:00.000",
      "end_time": "2025-11-01T10:00:15.000",
      "start_chainage": 1171.65,
      "end_chainage": 1187.75,
      "start_lat": -43.51759,
      "start_lon": 172.66081,
      "end_lat": -43.51765,
      "end_lon": 172.66085,
      "color": "#3498DB",
      "layer": 0,
      "metadata": {
        "created_by": "user@example.com",
        "created_at": "2025-11-15T14:20:00Z",
        "modified_at": "2025-11-15T15:30:00Z"
      }
    }
  ],
  "lane_fixes": [ ... ],
  "settings": { ... }
}
```

---

## APPENDIX D: Testing Strategy Details

### D.1 Unit Test Structure

```python
# tests/test_event_parsing.py
import pytest
from app.utils.file_parser import EventParser

class TestEventParsing:
    
    @pytest.fixture
    def sample_driveevt(self):
        return """SessionToken,Distance,Chainage,Time,TimeUtc,Event,IsSpanEvent,SpanEvent,IsSpanStartEvent,IsSpanEndEvent
25100208201377,1171.65,1171.65,10/02/2025 08:22:53,10/01/2025 19:22:53,Bridge Start,True,Bridge,True,False
25100208201377,1187.75,1187.75,10/02/2025 08:23:00,10/01/2025 19:23:00,Bridge End,True,Bridge,False,True"""
    
    def test_parse_span_events(self, sample_driveevt):
        parser = EventParser()
        events = parser.parse_driveevt_string(sample_driveevt)
        
        assert len(events) == 1
        assert events[0]['event_name'] == 'Bridge'
        assert events[0]['start_chainage'] == 1171.65
        assert events[0]['end_chainage'] == 1187.75
    
    def test_parse_missing_end_event(self):
        incomplete = """SessionToken,Distance,Chainage,Time,TimeUtc,Event,IsSpanEvent,SpanEvent,IsSpanStartEvent,IsSpanEndEvent
25100208201377,1171.65,1171.65,10/02/2025 08:22:53,10/01/2025 19:22:53,Bridge Start,True,Bridge,True,False"""
        
        parser = EventParser()
        events = parser.parse_driveevt_string(incomplete)
        
        # Should create incomplete event with inferred end
        assert len(events) == 1
        assert 'incomplete' in events[0].get('metadata', {})
    
    def test_parse_invalid_timestamp(self):
        invalid = """SessionToken,Distance,Chainage,Time,TimeUtc,Event,IsSpanEvent,SpanEvent,IsSpanStartEvent,IsSpanEndEvent
25100208201377,1171.65,1171.65,INVALID,10/01/2025 19:22:53,Bridge Start,True,Bridge,True,False"""
        
        parser = EventParser()
        with pytest.raises(ValueError):
            parser.parse_driveevt_string(invalid)
```

### D.2 Integration Test Examples

```python
# tests/test_full_workflow.py
import pytest
from PyQt6.QtWidgets import QApplication
from app.main_window import MainWindow

@pytest.fixture
def app(qtbot):
    application = QApplication([])
    window = MainWindow()
    qtbot.addWidget(window)
    yield window
    application.quit()

def test_load_and_navigate(app, qtbot, test_data_dir):
    """Test loading data and navigating images"""
    
    # Load test folder
    app.load_folder(test_data_dir / "0D2510020814007700")
    
    # Verify data loaded
    assert len(app.photo_tab.image_paths) > 0
    assert len(app.photo_tab.timeline.events) > 0
    
    # Navigate to image 5
    app.photo_tab.navigate_to_image(5)
    qtbot.wait(100)
    
    assert app.photo_tab.current_index == 5
    assert app.photo_tab.current_image is not None

def test_event_creation(app, qtbot):
    """Test creating new event via timeline"""
    
    # Click timeline to add event
    timeline = app.photo_tab.timeline
    click_pos = timeline.time_to_pixel(datetime(2025, 11, 1, 10, 0, 0))
    
    qtbot.mouseClick(timeline, Qt.RightButton, pos=QPoint(click_pos, 50))
    qtbot.wait(100)
    
    # Context menu should appear
    # (Additional test code for menu interaction)

def test_lane_assignment_with_overlap(app, qtbot, test_data_dir):
    """Test lane assignment conflict detection"""
    
    app.load_folder(test_data_dir / "0D2510020814007700")
    app.photo_tab.navigate_to_image(0)
    
    # Assign lane 1
    timestamp1 = datetime(2025, 11, 1, 10, 0, 0)
    app.photo_tab.lane_manager.assign_lane('1', timestamp1)
    
    # Try to assign lane 2 at overlapping time
    timestamp2 = datetime(2025, 11, 1, 10, 2, 0)
    result = app.photo_tab.lane_manager.assign_lane('2', timestamp2)
    
    assert result == False  # Should detect overlap
```

### D.3 Performance Test Framework

```python
# tests/test_performance.py
import pytest
import time
from app.ui.timeline_widget import TimelineWidget

def test_timeline_render_performance(qtbot, benchmark):
    """Benchmark timeline rendering with 1000 events"""
    
    timeline = TimelineWidget()
    qtbot.addWidget(timeline)
    
    # Generate 1000 test events
    events = generate_test_events(1000)
    timeline.set_events(events)
    
    # Benchmark repaint time
    def repaint_timeline():
        timeline.update()
        QApplication.processEvents()
    
    result = benchmark(repaint_timeline)
    
    # Assert < 16ms (60 FPS)
    assert result.stats.mean < 0.016

def test_image_cache_performance(benchmark):
    """Benchmark image cache hit rate"""
    
    from app.utils.image_cache import ImageCache
    cache = ImageCache(max_cache_mb=100)
    
    test_images = [f"test_{i}.jpg" for i in range(100)]
    
    def cache_access_pattern():
        # Simulate typical access pattern
        for img in test_images[:50]:  # First 50
            cache.get_image(img)
        for img in test_images[25:75]:  # Overlapping 25-75
            cache.get_image(img)
    
    result = benchmark(cache_access_pattern)
    
    # Check cache hit rate
    hit_rate = cache.hits / (cache.hits + cache.misses)
    assert hit_rate > 0.80  # 80%+ hit rate
```

---

## APPENDIX E: Code Style & Conventions

### E.1 Python Style Guide

**Follow PEP 8 with these additions:**

```python
# Imports order
import os
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal, QThread

from app.models.event_model import Event
from app.utils.file_parser import EventParser

# Class naming
class TimelineWidget(QWidget):  # PascalCase
    pass

# Method naming
def calculate_event_position(self):  # snake_case
    pass

# Constants
MAX_CACHE_SIZE_MB = 500  # UPPER_SNAKE_CASE
DEFAULT_THEME = "dark"

# Private methods/attributes
def _internal_helper(self):  # Single underscore prefix
    pass

self._cache = {}  # Private attribute
```

**Docstring Format (Google Style):**

```python
def parse_driveevt(filepath: Path) -> List[Dict]:
    """Parse .driveevt file and return list of events.
    
    Reads CSV file containing span event pairs (Start/End) and creates
    complete event objects with start/end times, chainage, and metadata.
    
    Args:
        filepath: Path to .driveevt file
        
    Returns:
        List of event dictionaries with keys:
            - event_id: Unique identifier
            - event_name: Name from SpanEvent field
            - start_time: datetime object
            - end_time: datetime object
            - start_chainage: float (meters)
            - end_chainage: float (meters)
    
    Raises:
        FileNotFoundError: If filepath doesn't exist
        ValueError: If CSV format is invalid
        
    Example:
        >>> events = parse_driveevt(Path("data/survey.driveevt"))
        >>> print(events[0]['event_name'])
        'Bridge'
    """
    pass
```

### E.2 PyQt6 Conventions

**Signal/Slot Naming:**
```python
class PhotoPreviewTab(QWidget):
    # Signals: past tense, describe what happened
    image_changed = pyqtSignal(int, dict)  # index, metadata
    position_updated = pyqtSignal(float, float)  # lat, lon
    
    def __init__(self):
        super().__init__()
        
        # Connect signals: on_<source>_<signal>
        self.button.clicked.connect(self.on_button_clicked)
        self.slider.valueChanged.connect(self.on_slider_value_changed)
    
    def on_button_clicked(self):
        """Handle button click events"""
        pass
```

**Widget Initialization Pattern:**
```python
class CustomWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 1. Initialize attributes
        self.data = []
        self._cache = {}
        
        # 2. Setup UI
        self.setup_ui()
        
        # 3. Connect signals
        self.connect_signals()
        
        # 4. Load initial state
        self.load_initial_state()
    
    def setup_ui(self):
        """Create and layout UI components"""
        self.layout = QVBoxLayout(self)
        self.button = QPushButton("Click Me")
        self.layout.addWidget(self.button)
    
    def connect_signals(self):
        """Connect all signal/slot pairs"""
        self.button.clicked.connect(self.on_button_clicked)
```

### E.3 Error Handling Patterns

**Prefer specific exceptions:**
```python
# Good
try:
    data = parse_csv(filepath)
except FileNotFoundError:
    logger.error(f"File not found: {filepath}")
    return []
except ValueError as e:
    logger.error(f"Invalid CSV format: {e}")
    return []
except Exception as e:
    logger.exception(f"Unexpected error parsing {filepath}")
    raise

# Bad - too broad
try:
    data = parse_csv(filepath)
except Exception:
    return []
```

**Use context managers:**
```python
# Good
from contextlib import contextmanager

@contextmanager
def busy_cursor():
    """Show busy cursor during long operations"""
    QApplication.setOverrideCursor(Qt.WaitCursor)
    try:
        yield
    finally:
        QApplication.restoreOverrideCursor()

# Usage
with busy_cursor():
    load_large_dataset()

# Bad - manual try/finally everywhere
QApplication.setOverrideCursor(Qt.WaitCursor)
try:
    load_large_dataset()
finally:
    QApplication.restoreOverrideCursor()
```

---

## APPENDIX F: Development Environment Setup

### F.1 Recommended IDE Configuration

**VSCode settings.json:**
```json
{
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.flake8Args": [
        "--max-line-length=100",
        "--ignore=E203,W503"
    ],
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": [
        "--line-length=100"
    ],
    "editor.formatOnSave": true,
    "editor.rulers": [100],
    "[python]": {
        "editor.tabSize": 4
    }
}
```

**PyCharm configuration:**
- Enable PEP 8 checking
- Set line length to 100
- Enable auto-formatting with Black
- Configure PyQt6 as external library

### F.2 Virtual Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Install in editable mode
pip install -e .
```

### F.3 Pre-commit Hooks

**`.pre-commit-config.yaml`:**
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
        language_version: python3.9
        args: [--line-length=100]
  
  - repo: https://github.com/PyCQA/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: [--max-line-length=100, --ignore=E203,W503]
  
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
```

**Install pre-commit:**
```bash
pip install pre-commit
pre-commit install
```

---

## APPENDIX G: Troubleshooting Guide

### G.1 Common Development Issues

**Issue: PyQt6 not found**
```bash
# Solution: Ensure PyQt6 is installed in active environment
pip list | grep PyQt6
pip install PyQt6==6.6.0

# If still fails, check Python version
python --version  # Should be 3.9+
```

**Issue: Import errors for relative imports**
```python
# Bad
from utils.file_parser import EventParser

# Good - run as module
python -m app.main

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Issue: Qt platform plugin errors**
```bash
# Linux: Install Qt dependencies
sudo apt-get install libxcb-xinerama0 libxcb-cursor0

# Set Qt platform
export QT_QPA_PLATFORM=xcb
```

### G.2 Runtime Issues

**Issue: Slow timeline rendering**
```python
# Debug: Enable performance logging
logging.getLogger('performance').setLevel(logging.DEBUG)

# Check event count
print(f"Event count: {len(timeline.events)}")

# If > 10k, enable aggregation
timeline.enable_aggregated_view()
```

**Issue: High memory usage**
```python
# Check memory usage
import psutil
process = psutil.Process()
print(f"Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB")

# Clear caches
image_cache.clear()
gps_cache.clear()
import gc
gc.collect()
```

**Issue: GPS coordinates not enriching events**
```python
# Debug: Check GPS data loaded
print(f"GPS points: {len(gps_data)}")
print(f"First GPS: {gps_data[0]}")

# Check timestamp format matching
print(f"Event time: {event['start_time']}")
print(f"GPS time: {gps_data[0]['timestamp']}")

# Verify timezone handling
print(f"Event TZ: {event['start_time'].tzinfo}")
```

---

## FINAL SUMMARY: Key Success Factors

### Critical Path Items (Must Not Fail)

1. **Data Parsing Accuracy**
   - 100% correct parsing of .driveevt span event pairs
   - Robust GPS timestamp parsing with timezone handling
   - Accurate coordinate extraction from image filenames

2. **Timeline Performance**
   - < 16ms render time for 60 FPS
   - Viewport culling for large event sets
   - Efficient layer calculation

3. **Data Integrity**
   - Atomic file operations (no data corruption)
   - Lane overlap detection (no conflicts)
   - Autosave with crash recovery

4. **User Experience**
   - Responsive UI (no freezing during operations)
   - Clear error messages with recovery options
   - Intuitive event editing workflow

### Architecture Principles

1. **Separation of Concerns**
   - Models (data) separate from Views (UI)
   - Parsers separate from business logic
   - Managers for cross-cutting concerns

2. **Performance First**
   - Lazy loading wherever possible
   - Caching with size limits
   - Background threads for I/O

3. **Robustness**
   - Defensive programming (validate all inputs)
   - Graceful degradation (partial data loading)
   - Comprehensive logging

4. **Maintainability**
   - Clear module boundaries
   - Extensive documentation
   - Unit test coverage

### Recommended Development Order

1. **Start with data layer** - Get parsing 100% correct
2. **Build timeline core** - Nail rendering performance
3. **Add image preview** - Simple but functional
4. **Implement lane coding** - Critical business logic
5. **Polish UI/UX** - Make it pleasant to use
6. **Optimize performance** - Profile and improve
7. **Comprehensive testing** - Ensure reliability

### Quality Gates

Before considering complete:
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Performance benchmarks met
- [ ] No memory leaks detected
- [ ] User acceptance testing completed
- [ ] Documentation complete
- [ ] Code review passed

---

**END OF TASK DOCUMENT**

*This comprehensive task document provides all necessary information for an AI agent or development team to rebuild GeoEvent with improved stability, performance, and user experience. Follow the phased implementation approach, prioritize the critical path items, and validate against the success criteria throughout development.*