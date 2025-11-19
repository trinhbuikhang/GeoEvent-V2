# Lane Change Enhancement - Marker Mode & Confirmation Dialog

## Tổng quan
Cải thiện chức năng đổi lane bằng cách sử dụng marker trên timeline với màu đỏ đậm khi đang trong chế độ đổi lane, và thêm dialog xác nhận với 3 lựa chọn: Yes/Continue/Cancel. Cho phép override lane tới thời điểm liền sau gần nhất hoặc cuối folder ảnh.

## Yêu cầu chi tiết

### 1. Visual Feedback cho Marker
- **Hành vi hiện tại**: Marker màu vàng khi ở vị trí hiện tại
- **Hành vi mới**: Marker đổi sang màu đỏ và đậm hơn khi user kích hoạt chế độ đổi lane
- **Mục đích**: Cung cấp feedback trực quan rằng đang trong chế độ edit lane

### 2. Dialog Xác nhận Đổi Lane
Khi user dịch chuyển marker xong (release mouse), hiện dialog với 3 lựa chọn:
- **Yes**: Đồng ý vị trí sau khi dịch chuyển là lane mới, áp dụng thay đổi
- **Continue**: Tiếp tục điều chỉnh vị trí marker để chọn thời gian/vị trí lane mới
- **Cancel**: Hủy bỏ việc đổi lane vừa rồi, trở về trạng thái ban đầu

### 3. Logic Override Lane
- Khi áp dụng thay đổi, override lane từ vị trí hiện tại tới:
  - Thời điểm liền sau gần nhất có lane change khác (nếu có)
  - Thời điểm cuối của folder ảnh (nếu không có lane change sau)
- Đảm bảo không overlap với lane changes trước đó

### 4. Tích hợp với Photo Navigation
- Cho phép user sử dụng nút Pre/Next/Play để dịch chuyển ảnh đã có
- Khi dịch chuyển ảnh, marker tự động cập nhật vị trí tương ứng
- Giúp user dễ dàng xác định thời điểm chính xác cho lane change

## Kế hoạch thực hiện

### Phase 1: Cập nhật Visual Marker (TimelineWidget)
1. **Sửa paint_current_position()**:
   - Kiểm tra `lane_change_mode_active`
   - Nếu active: đổi màu từ vàng sang đỏ, tăng độ đậm (pen width)
   - Thêm visual indicator cho chế độ edit

2. **Cập nhật enable_lane_change_mode()**:
   - Đảm bảo marker timestamp được set đúng
   - Trigger repaint để hiển thị màu mới

### Phase 2: Dialog Xác nhận (TimelineWidget + Dialog mới)
1. **Tạo LaneChangeConfirmationDialog**:
   - Kế thừa QDialog
   - 3 buttons: Yes, Continue, Cancel
   - Hiển thị thông tin: lane cũ -> lane mới, thời gian start->end
   - Return enum: CONFIRMED, CONTINUE, CANCELLED

2. **Tích hợp vào mouseReleaseEvent**:
   - Khi release marker trong lane_change_mode
   - Hiện dialog và xử lý kết quả
   - Nếu CONFIRMED: apply change
   - Nếu CONTINUE: giữ mode, cho drag tiếp
   - Nếu CANCELLED: exit mode, revert marker

### Phase 3: Logic Override Lane (LaneManager) ✅ HOÀN THÀNH
- ✅ Khi enable lane change mode: Tự động apply change từ start_timestamp đến next_lane_change_time (hoặc folder_end_time)
- ✅ Khi drag marker: Chỉ update lane_change_end_timestamp, không apply change ngay
- ✅ Khi confirm (click "OK"): Ưu tiên sử dụng end_timestamp do user chọn (không phải auto-calculated nếu user đã drag)
- ✅ Logic apply_lane_change_range: Đúng xác định period chứa end_time và preserve các periods xung quanh
- ✅ Test case: 10:15-10:30 Lane 2 giữa 10:00-11:00 Lane 1 và 11:00-12:00 Lane 2 → preserve đúng
1. **Cập nhật change_lane_smart()**:
   - Thêm parameter `end_timestamp` để chỉ định end time
   - Logic: từ start_timestamp tới min(end_timestamp, next_lane_change_time, folder_end_time)
   - Đảm bảo không overlap với periods trước

2. **Thêm method get_next_lane_change_time()**:
   - Tìm thời điểm lane change gần nhất sau timestamp
   - Return None nếu không có

### Phase 4: Tích hợp Photo Navigation
1. **Kết nối với PhotoPreviewTab**:
   - Khi user click Pre/Next/Play, cập nhật current_position
   - Nếu lane_change_mode active, marker tự động follow

2. **Sync marker với photo position**:
   - Khi photo thay đổi, marker timestamp = photo timestamp
   - Đảm bảo timeline scroll để marker visible

### Phase 5: Testing & Validation
1. **Unit tests**:
   - Test marker color change
   - Test dialog responses
   - Test override logic

2. **Integration tests**:
   - Test full flow: click lane -> drag marker -> confirm
   - Test với photo navigation
   - Test edge cases: no next change, folder end, etc.

## Lưu ý kỹ thuật

### Marker Visual States
```python
# Normal mode
pen = QPen(QColor('#FFFF00'), 1)  # Yellow, normal

# Lane change mode  
pen = QPen(QColor('#FF0000'), 3)  # Red, thicker
```

### Dialog Result Enum
```python
class LaneChangeResult:
    CONFIRMED = 0
    CONTINUE = 1
    CANCELLED = 2
```

### Override Logic Pseudocode
```python
def apply_lane_override(start_time, end_time, new_lane):
    # Find next lane change after start_time
    next_change = get_next_lane_change_after(start_time)
    
    # Determine actual end time
    if next_change and next_change < end_time:
        actual_end = next_change
    else:
        actual_end = min(end_time, folder_end_time)
    
    # Apply change from start_time to actual_end
    change_lane_range(new_lane, start_time, actual_end)
```

### Photo Navigation Integration
- Connect photo position changes to `timeline.set_current_position(timestamp)`
- Ensure timeline auto-scrolls to keep marker visible
- Update marker only when lane_change_mode is active

## Success Criteria
- [x] Marker đổi màu đỏ đậm khi lane change mode active
- [x] Dialog xác nhận xuất hiện khi release marker (đã thay bằng 3 nút action)
- [x] Yes: áp dụng change và exit mode
- [x] Continue: giữ mode để adjust tiếp
- [x] Cancel: hủy và revert
- [x] Override logic đúng: tới next change point hoặc folder end
- [x] Photo navigation (Pre/Next/Play) cập nhật marker position
- [x] Timeline auto-scroll để marker visible
- [x] Data persistence: lưu lane_fixes.csv đúng
- [x] UI state consistency: exit mode properly
- [x] Skip lane assignment when clicking same lane button (no error/warning)
- [x] Auto-save data when closing app (single FileID workflow)
- [x] Improved lane period visualization: thicker bars, higher position, white separators

## Action Buttons Implementation
- ✅ 3 circular buttons always visible above marker in lane change mode
- ✅ Red button (Cancel): Exit mode, reset marker
- ✅ Yellow button (Continue): Keep adjusting, stay in mode
- ✅ Green button (Yes): Apply lane change, exit mode
- ✅ Click detection using distance calculation
- ✅ Visual feedback with colored circles and labels

## Files Modified
- `app/ui/timeline_widget.py`: Added button painting, click detection, and actions
- Removed dialog-based confirmation, replaced with direct button clicks

## Test Files
- `test_buttons_simple.py`: Logic tests for button positions and click detection

## Files cần sửa
- `app/ui/timeline_widget.py`: paint_current_position, mouse events, dialog integration
- `app/models/lane_model.py`: change_lane_smart, override logic
- `app/ui/photo_preview_tab.py`: photo navigation sync
- New file: `app/ui/lane_change_dialog.py`: confirmation dialog

## Risk & Mitigation
- **Risk**: Dialog blocking UI -> Use modal dialog with proper parenting
- **Risk**: Marker position sync issues -> Test thoroughly with photo navigation
- **Risk**: Data corruption -> Backup files, validate before save
- **Risk**: Performance with large datasets -> Optimize repaint, use caching</content>
<parameter name="filePath">c:\Users\du\Desktop\PyDeveloper\GeoEvent Ver2\todo-lane.md