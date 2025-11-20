# Data Structure Extension Task

## Overview
Extend GeoEvent application to support LMD and MSD data structures alongside existing LCMS support.

## Current Status
- ✅ LCMS data structure fully supported
- ⏳ LMD structure analysis complete
- ⏳ MSD structure pending (need sample data)
- 📝 Extension guide created

## LMD Structure Details
**Example Folder:** `J:\Testing\250584 HTAUPO_LMD_25\Photos`

**Characteristics:**
- Images only in `Photos/` folder
- No `.driveiri`, `.driveevt`, or other binary GPS files
- Lane fixes as primary output (`lane_fixes.csv`)
- No GPS data available

## Implementation Tasks

### Phase 1: Core Infrastructure (Priority: High)
- [ ] Add `DataType` enum in `app/utils/data_loader.py`
- [ ] Implement `detect_data_type()` function
- [ ] Extend `DataLoader.load_fileid_data()` with data type routing
- [ ] Update `GPSData` class to handle missing GPS data
- [ ] Modify UI components for GPS-less projects

### Phase 2: LMD Support (Priority: High)
- [ ] Implement `_load_lmd_data()` method in DataLoader
- [ ] Test with sample LMD data: `J:\Testing\250584 HTAUPO_LMD_25\Photos`
- [ ] Update minimap to show "No GPS data" message
- [ ] Ensure timeline works without GPS data
- [ ] Verify lane fixes save correctly

### Phase 3: MSD Support (Priority: Medium)
- [ ] Obtain MSD sample data structure
- [ ] Implement `_load_msd_data()` method
- [ ] Test MSD loading and processing
- [ ] Update documentation with MSD details

### Phase 4: Testing & Validation (Priority: High)
- [ ] Unit tests for data type detection
- [ ] Integration tests with LMD sample data
- [ ] UI testing for GPS-less projects
- [ ] Performance testing with large image sets
- [ ] Regression testing for LCMS projects

## Files to Modify

### Core Logic
- `app/utils/data_loader.py` - Add data type detection and loading methods
- `app/models/gps_model.py` - Handle missing GPS data
- `app/models/lane_model.py` - Lane fixes as primary output

### UI Components
- `app/ui/photo_preview_tab.py` - Minimap adaptations
- `app/ui/timeline_widget.py` - GPS-less timeline handling
- `app/ui/event_editor.py` - Event creation without GPS

### Testing
- Create `test_lmd_loading.py` - LMD data loading tests
- Create `test_msd_loading.py` - MSD data loading tests
- Update existing tests for backward compatibility

## Risk Assessment

### Low Risk
- Data type detection logic
- Backward compatibility for LCMS

### Medium Risk
- UI adaptations for GPS-less projects
- Lane manager modifications

### High Risk
- Performance with large image-only datasets
- Ensuring all GPS-dependent features degrade gracefully

## Success Criteria

1. **LCMS Compatibility:** All existing LCMS projects continue to work unchanged
2. **LMD Support:** Can load and process LMD projects from Photos folder
3. **MSD Support:** Can load and process MSD projects (when structure known)
4. **User Experience:** Clear indication when GPS data unavailable
5. **Data Integrity:** Lane fixes save correctly for all project types
6. **Performance:** Acceptable performance with large image sets

## Timeline Estimate

- **Phase 1:** 2-3 days (Core infrastructure)
- **Phase 2:** 1-2 days (LMD support)
- **Phase 3:** 1-2 days (MSD support, pending sample data)
- **Phase 4:** 2-3 days (Testing and validation)

## Dependencies

- Sample LMD data: `J:\Testing\250584 HTAUPO_LMD_25\Photos`
- Sample MSD data: TBD
- Access to test environment with large datasets

## Next Steps

1. Review and approve extension guide
2. Begin Phase 1 implementation
3. Test with LMD sample data
4. Gather MSD structure information
5. Plan Phase 2 and 3 implementation</content>
<parameter name="filePath">c:\Users\du\Desktop\PyDeveloper\GeoEvent Ver2\data_structure_extension_task.md