# GeoEvent Application

A PyQt6-based road survey event coding application with GPS-synchronized timeline for processing road survey data from GPS logs (.driveevt, .driveiri) and images to enable systematic event coding and lane assignment.

## Features

- GPS-synchronized timeline visualization and editing of road events
- Image navigation with GPS coordinate extraction
- Lane assignment with conflict detection
- Multi-FileID processing
- Data export to CSV

## Installation

1. Install Python 3.9+
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```

## Usage

1. Launch the application
2. Select a survey data folder
3. Navigate through images and assign lanes
4. Edit events on the timeline
5. Export coded data to CSV

## Building Executable

To create a standalone executable for distribution:

### Windows
1. Install build dependencies:
   ```bash
   pip install -r requirements-build.txt
   ```

2. Run the build script:
   ```bash
   python build.py
   ```
   Or use the batch file:
   ```bash
   build.bat
   ```

3. Find the executable in `dist/GeoEvent.exe`

### Notes
- The executable is self-contained and doesn't require Python installation
- Size is optimized by excluding unnecessary modules
- See `BUILD_README.md` for detailed instructions

## Data Format

- **.driveevt**: CSV with event data (span events)
- **.driveiri**: CSV with GPS/IRI data
- **Images**: JPEG with metadata in filename

## Architecture

- **UI Framework**: PyQt6
- **Data Processing**: pandas
- **Storage**: JSON/CSV