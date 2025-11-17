# GeoEvent Application - TODO List

## Completed Features ✅
- [x] Core application structure (main.py, main_window.py)
- [x] Data models (event_model.py, gps_model.py, lane_model.py)
- [x] File parsing (.driveevt, .driveiri, image metadata)
- [x] UI components (photo_preview_tab.py, timeline_widget.py)
- [x] GPS-synchronized timeline with event visualization
- [x] Image navigation with metadata display
- [x] Lane assignment with conflict detection
- [x] Multi-FileID folder scanning and navigation
- [x] Settings persistence (JSON)
- [x] Memory and autosave managers
- [x] Minimap with GPS position display
- [x] Theme support (light/dark)
- [x] Error handling and validation
- [x] Coordinate extraction from image filenames
- [x] Image scaling and display

## Remaining Tasks 📋

### High Priority
- [x] **Event Editor Dialog** - Create event_editor.py for editing event properties
- [ ] **Data Export** - Implement CSV export for coded events and lane assignments
- [ ] **Event Filtering** - Add filters for event types, time ranges, etc.
- [ ] **Keyboard Shortcuts** - Implement common shortcuts (play/pause, next/prev, etc.)
- [ ] **Zoom Controls** - Add zoom in/out for timeline and images

### Medium Priority
- [ ] **Advanced Minimap** - Integrate real map tiles (OpenStreetMap) using QWebEngineView
- [ ] **Batch Processing** - Process multiple FileIDs automatically
- [ ] **Data Validation** - Add comprehensive validation for imported data
- [ ] **Performance Optimization** - Implement lazy loading for large datasets
- [ ] **Undo/Redo** - Add undo/redo functionality for lane assignments

### Low Priority
- [ ] **Custom Themes** - Allow user-defined color schemes
- [ ] **Plugin System** - Extensible architecture for custom parsers
- [ ] **Report Generation** - Generate summary reports
- [ ] **Audio Feedback** - Sound notifications for events
- [ ] **Multi-language Support** - Localization

### Testing & Quality
- [ ] **Unit Tests** - Comprehensive test suite
- [ ] **Integration Tests** - End-to-end workflow testing
- [ ] **Performance Testing** - Memory and CPU usage analysis
- [ ] **User Documentation** - Complete user guide and tutorials

### Deployment
- [ ] **Packaging** - Create executable with PyInstaller
- [ ] **Installation Script** - Automated setup
- [ ] **Version Management** - Semantic versioning
- [ ] **Release Notes** - Document changes per version

## Next Steps
1. ✅ Event Editor Dialog - COMPLETED
2. Add Data Export functionality
3. Create comprehensive unit tests
4. Optimize performance for large datasets
5. Package application for distribution