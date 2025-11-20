from app.utils.image_utils import extract_image_metadata
import os

image_path = 'testdata/err/0D2510020844387700/Cam1/250410.01-2025-10-01-19-44-42-984-4325.339064S-17239.124360E-204.4---QJS289-0D2510020844387700-6014062732920-13.23-LE-.jpg'
print(f'Image path exists: {os.path.exists(image_path)}')

try:
    metadata = extract_image_metadata(image_path)
    print(f'Metadata keys: {list(metadata.keys())}')
    print(f'Timestamp: {metadata.get("timestamp")}')
except Exception as e:
    print(f'Error extracting metadata: {e}')