# Auto-Save on Folder Switch Feature

## Overview
GeoEvent now supports automatic saving of events and lane fixes when switching between FileID folders. This feature helps preserve work progress while ensuring data integrity.

## How It Works

### Default Behavior (Now Enabled)
- **Auto-save is ENABLED by default** - automatically preserves work progress
- Users can disable the feature in Settings if preferred

### When Enabled
- **Silent auto-save**: Automatically saves current folder's data when switching folders
- **Merge all data**: Also merges and saves all FileID data to root folder files
- **No confirmation dialogs**: Saves happen in the background
- **Current folder only**: Only saves the folder you're currently working on
- **No impact on other folders**: Other FileID folders remain unchanged

## Feature Details

### What Gets Saved
- **Events**: All events in `.driveevt` file (if modified)
- **Lane Fixes**: All lane fixes in `{FileID}_lane_fixes.csv` file (if modified)
- **Merged Events**: All events from all FileIDs in `merged.driveevt` (root folder)
- **Merged Lane Fixes**: All lane fixes from all FileIDs in `laneFixes-{date}.csv` (root folder)

### When Auto-Save Triggers
- Clicking "Previous FileID" button
- Clicking "Next FileID" button
- Any navigation that switches the active FileID

### Safety Measures
- Only saves if data has actually been modified (`events_modified` or `has_changes` flags)
- Creates proper backups before overwriting files
- Logs all save operations for debugging
- Resets change flags after successful saves

## User Interface

### Settings Dialog
Access via: **Tools → Settings**

```
Auto-Save
☐ Auto-save when switching FileID folders
  "Automatically save events and lane fixes when switching to another FileID folder.
   Only saves the current folder's changes, does not affect other folders."
```

### Status Messages
- Auto-save operations are logged to console
- Success/failure messages appear in logs
- No popup notifications to avoid workflow interruption

## Technical Implementation

### Code Flow
```
User clicks Next/Prev FileID
    ↓
auto_save_current_data_silent()
    ↓
Save current folder events (if modified)
Save current folder lane fixes (if modified)
Merge ALL folders data and save to root
    ↓
Load new FileID data
```

### Key Methods
- `auto_save_current_data_silent()`: Performs silent save operations
- `prev_fileid()` / `next_fileid()`: Navigation with auto-save
- Settings integration via `settings_manager`

### Data Integrity
- Uses existing save methods (`save_all_events_internal()`, `export_lane_fixes()`)
- Maintains all existing error handling and backup creation
- Resets change flags to prevent duplicate saves

## Benefits

### For Users
- **Never lose work**: Progress automatically preserved when switching folders
- **Seamless workflow**: No interruption for save confirmations
- **Data safety**: Only current folder affected, others remain untouched

### For Data Integrity
- **Atomic saves**: Either complete successfully or fail safely
- **Backup protection**: Existing files backed up before overwrite
- **Change tracking**: Only saves when data actually modified

## Migration & Compatibility

### Backward Compatibility
- Feature is **disabled by default** - no impact on existing users
- Existing save behavior unchanged
- All existing data formats supported

### Settings Persistence
- Setting saved in `~/.geoevent/settings.json`
- **Reset to defaults on every application startup** (to avoid conflicts)
- Can be changed at any time via Settings dialog

## Testing

Run the test suite:
```bash
python test_auto_save_navigation.py
```

Tests verify:
- Setting persistence
- Silent save logic
- No impact on other folders
- Proper error handling

## Troubleshooting

### Auto-save Not Working
1. Check Settings → Auto-save is enabled
2. Verify data has been modified (add/edit events or lane fixes)
3. Check console logs for error messages

### Data Loss Concerns
- Auto-save only affects current folder
- Other folders remain completely untouched
- Can disable feature anytime in Settings

### Performance Issues
- Auto-save is fast (uses existing save methods)
- Only triggers when switching folders
- No background processing

## Future Enhancements

Potential improvements:
- Auto-save on application focus loss
- Configurable auto-save intervals
- Save to temporary files first, then rename
- Undo functionality for accidental saves

## Background Processing Details

### Why Background Saves?
- **UI Responsiveness**: Prevents application freezing during file I/O operations
- **Better UX**: Users can continue working while saves happen in background
- **Performance**: No blocking operations on main UI thread

### Technical Implementation
- Uses `QThread` for background save operations
- `BackgroundSaveWorker` class handles threaded file operations
- Signals (`save_completed`) for thread-safe UI updates
- Automatic thread cleanup to prevent memory leaks

### Code Flow
```
User clicks Next/Prev FileID
    ↓
auto_save_current_data_silent()
    ↓
_start_background_save() → BackgroundSaveWorker thread
    ↓
Save events + lane fixes in background thread
    ↓
Emit save_completed signal (optional UI feedback)
    ↓
Load new FileID data (UI remains responsive)
```</content>
<parameter name="filePath">c:\Users\du\Desktop\PyDeveloper\GeoEvent Ver2\AUTO_SAVE_FEATURE.md