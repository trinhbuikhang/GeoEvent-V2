#!/usr/bin/env python3
"""
Test script to check image loading in PyQt6
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap

def test_image_loading():
    image_path = 'testdata/err/0D2510020844387700/Cam1/250410.01-2025-10-01-19-44-42-984-4325.339064S-17239.124360E-204.4---QJS289-0D2510020844387700-6014062732920-13.23-LE-.jpg'

    print(f'Full path: {os.path.abspath(image_path)}')
    print(f'Exists: {os.path.exists(image_path)}')

    if os.path.exists(image_path):
        pixmap = QPixmap(image_path)
        print(f'QPixmap loaded: {not pixmap.isNull()}')
        if not pixmap.isNull():
            print(f'Size: {pixmap.width()}x{pixmap.height()}')
        else:
            print('QPixmap is null - loading failed')
    else:
        print('File does not exist')

if __name__ == "__main__":
    app = QApplication(sys.argv)
    test_image_loading()
    app.quit()