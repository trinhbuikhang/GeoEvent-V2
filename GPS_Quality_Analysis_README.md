# GPS Quality Analysis Tool

Công cụ phân tích chuyên sâu chất lượng dữ liệu GPS cho ứng dụng GeoEvent.

## Tổng quan

Tool này thực hiện phân tích toàn diện chất lượng dữ liệu GPS trong các folder test, đặc biệt tập trung vào dữ liệu GPS bị lỗi hoặc có vấn đề có thể gây ra hiện tượng ứng dụng bị freeze hoặc lỗi rendering.

## Tính năng chính

### 1. Phân tích toàn diện GPS
- **Chainage validation**: Kiểm tra giá trị chainage hợp lệ (0-10,000 km)
- **Timestamp validation**: Đảm bảo timestamp theo thứ tự thời gian
- **Coordinate validation**: Kiểm tra tọa độ GPS hợp lệ
- **Data integrity**: Phát hiện dữ liệu bị corrupt hoặc không nhất quán

### 2. Phân tích chuyển động
- **Tốc độ trung bình, tối đa, tối thiểu**
- **Phát hiện tốc độ bất thường** (> 200 km/h)
- **Khoảng cách giữa các điểm GPS**
- **Thời gian gap giữa các điểm**

### 3. Báo cáo chất lượng
- **Điểm chất lượng tổng thể** (0-100)
- **Thống kê chi tiết** về lỗi và vấn đề
- **Khuyến nghị cải thiện**
- **So sánh giữa các folder**

## Cách sử dụng

### Chạy phân tích mặc định
```bash
python test_gps_quality_analysis.py
```
Phân tích tất cả folder trong `testdata/err/`

### Phân tích folder cụ thể
```bash
python test_gps_quality_analysis.py "path/to/folder"
```
Ví dụ:
```bash
python test_gps_quality_analysis.py "C:\Users\du\Desktop\PyDeveloper\GeoEvent Ver2\testdata\20251002"
```

## Định dạng dữ liệu GPS

Tool hỗ trợ định dạng file `.driveiri` với cấu trúc CSV:

```
Session,System,GPSDateTime,Elevation [m],HDOP,Quality,Unix,Position (begin) (LAT),Position (begin) (LON),AverageSpeed [km/h],StartChainage [km],EndChainage [km],IRI Left [m/km],IRI Right [m/km]
```

## Các chỉ số chất lượng

### Điểm chất lượng (0-100)
- **100**: Dữ liệu hoàn hảo, không có lỗi
- **80-99**: Dữ liệu tốt, có một số vấn đề nhỏ
- **50-79**: Dữ liệu có vấn đề, cần kiểm tra
- **< 50**: Dữ liệu kém chất lượng, cần xử lý

### Các loại lỗi được phát hiện

1. **Chainage Issues**:
   - Giá trị âm
   - Quá lớn (> 10,000 km)
   - NaN hoặc Infinite
   - Không tăng dần (non-monotonic)

2. **Timestamp Issues**:
   - Timestamp không hợp lệ
   - Thứ tự thời gian bị đảo lộn

3. **Coordinate Issues**:
   - Tọa độ không hợp lệ
   - Vượt ra ngoài phạm vi (-90/+90 lat, -180/+180 lon)

4. **Movement Anomalies**:
   - Tốc độ quá cao (> 200 km/h)
   - Khoảng thời gian quá lớn giữa các điểm

## Output

### Báo cáo console
Hiển thị báo cáo chi tiết trực tiếp trên terminal với:
- Thống kê tổng quan
- Phân tích chi tiết từng folder
- Khuyến nghị cải thiện

### File báo cáo
Tự động lưu báo cáo vào file `gps_quality_report.txt` trong thư mục gốc của project.

## Ví dụ output

```
================================================================================
GPS QUALITY ANALYSIS REPORT
================================================================================
Analysis Date: 2025-11-21 08:21:33
Base Path: C:\path\to\data

SUMMARY STATISTICS:
  Total folders analyzed: 5
  Average quality score: 100.0
  Best quality folder: Folder_A (100)
  Worst quality folder: Folder_B (85)

DETAILED FOLDER ANALYSIS:
--------------------------------------------------------------------------------
Folder: Folder_A
  Quality Score: 100/100
  Data Overview:
    Total GPS points: 438
    Valid points: 438 (100.0%)
    Invalid points: 0 (0.0%)
  Movement Analysis:
    Average speed: 5.5 km/h
    Max speed: 7.2 km/h
    Min speed: 3.6 km/h
```

## Khuyến nghị sử dụng

1. **Trước khi xử lý dữ liệu**: Chạy tool để đánh giá chất lượng GPS
2. **Khi gặp lỗi ứng dụng**: Sử dụng tool để chẩn đoán vấn đề GPS
3. **Định kỳ kiểm tra**: Theo dõi chất lượng dữ liệu GPS theo thời gian
4. **So sánh dữ liệu**: Đánh giá chất lượng giữa các folder khác nhau

## Lợi ích

- **Phòng ngừa lỗi**: Phát hiện sớm vấn đề GPS có thể gây crash
- **Tối ưu hóa**: Cải thiện hiệu suất xử lý dữ liệu
- **Chẩn đoán**: Xác định nguyên nhân gây lỗi ứng dụng
- **Báo cáo**: Cung cấp thông tin chi tiết cho người dùng và nhà phát triển

## Yêu cầu hệ thống

- Python 3.7+
- Thư viện tiêu chuẩn (không cần cài đặt thêm)
- File dữ liệu GPS định dạng .driveiri

## Mở rộng

Tool có thể được mở rộng để:
- Hỗ trợ thêm định dạng file GPS
- Thêm các chỉ số chất lượng mới
- Tích hợp với giao diện người dùng
- Xuất báo cáo định dạng JSON/HTML