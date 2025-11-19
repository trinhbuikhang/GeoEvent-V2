"""
User Guide Module for GeoEvent Application
Provides user guide content and dialog functionality
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox


class UserGuideDialog(QDialog):
    """
    Dialog to display user guide content
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GeoEvent - User Guide")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml(self.get_user_guide_content())
        layout.addWidget(text_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    def get_user_guide_content(self) -> str:
        """Get user guide content in HTML format"""
        return """
        <h1>GeoEvent User Guide</h1>

        <h2>Introduction</h2>
        <p>GeoEvent is a road survey event coding application that helps users analyze and code data from cameras and GPS in traffic survey projects. The application supports lane assignment, event coding, and data export for traffic analysis.</p>

        <h2>Installation and Startup</h2>
        <ol>
            <li>Ensure you have Python 3.8+ and required libraries installed (PyQt6, pandas, etc.)</li>
            <li>Run command: <code>python main.py</code></li>
            <li>The application will open with the main interface</li>
        </ol>

        <h2>Main Interface</h2>
        <h3>Menu Bar</h3>
        <ul>
            <li><b>File:</b> Open survey data folder, auto-save settings</li>
            <li><b>View:</b> Change theme (Light/Dark), force Fusion style for consistency</li>
            <li><b>Help:</b> User guide and application information</li>
        </ul>

        <h3>Toolbar</h3>
        <p>Contains main navigation and control tools</p>

        <h3>Status Bar</h3>
        <p>Displays status information, current FileID, memory usage, and autosave status</p>

        <h2>Workflow</h2>
        <h3>1. Open Data Folder</h3>
        <ol>
            <li>Select <b>File > Open Folder...</b></li>
            <li>Choose folder containing survey data (may contain multiple FileIDs)</li>
            <li>Application will automatically load the first FileID</li>
            <li>Use navigation buttons to switch between FileIDs</li>
        </ol>

        <h3>2. Navigate Images</h3>
        <ul>
            <li>Use slider or Previous/Next buttons to navigate between images</li>
            <li>Timeline below shows current time position and lane assignments</li>
            <li>Click on timeline to jump to specific time</li>
            <li>Double-click timeline to zoom in/out</li>
            <li>Keyboard shortcuts: Left/Right arrows, Space (play/pause)</li>
        </ul>

        <h3>3. Lane Coding</h3>
        <p>The application supports various lane assignment types:</p>
        <ul>
            <li><b>Lane 1-4:</b> Main traffic lanes</li>
            <li><b>SK (Shoulder):</b> Road shoulder (automatically appends lane number, e.g., SK1, SK2)</li>
            <li><b>TK/TM:</b> Left/right turns (automatically appends selected lane number, e.g., TK1, TM2)</li>
            <li><b>Ignore:</b> Ignore this time period (writes '1' to Ignore column in CSV)</li>
        </ul>

        <h4>How to Code Lanes:</h4>
        <ol>
            <li>Navigate to the time point to code</li>
            <li>Click the corresponding lane type button</li>
            <li>For lane changes, a dialog will appear with instructions</li>
            <li>Drag the yellow marker on the timeline to select the end time</li>
            <li>The image preview will update as you drag the marker</li>
            <li>Release the marker to confirm the lane change</li>
        </ol>

        <h4>Lane Change Feature:</h4>
        <p>When changing lanes, the application uses an interactive marker system:</p>
        <ul>
            <li>Click any lane button (1-4, SK, TK, TM) to initiate lane change</li>
            <li>A dialog appears explaining how to use the marker</li>
            <li>The yellow marker appears on the timeline at the current time</li>
            <li>Drag the marker to select the end time for the lane change</li>
            <li>The image preview automatically syncs with marker position</li>
            <li>Release the marker to apply the change</li>
            <li>Timeline colors update to show the new lane assignment</li>
        </ul>

        <h4>Special Lane Types:</h4>
        <ul>
            <li><b>SK Button:</b> Assigns shoulder lane. If currently on lane 1-4, automatically codes as SK1, SK2, etc.</li>
            <li><b>TK/TM Buttons:</b> Assigns turn lanes. Must select a base lane (1-4) first, then codes as TK1/TM1, etc.</li>
            <li><b>Ignore Button:</b> Marks time period as ignored. Useful for excluding invalid data periods.</li>
        </ul>

        <h3>4. Event Coding</h3>
        <p>The timeline shows events as colored bars. You can:</p>
        <ul>
            <li>Click events to view details</li>
            <li>Edit event properties</li>
            <li>Add new events</li>
            <li>Delete events</li>
        </ul>

        <h3>5. Data Export</h3>
        <ul>
            <li>Lane data is automatically saved on changes</li>
            <li>Individual FileID lane files: <code>{FileID}_lane_fixes.csv</code></li>
            <li>Merged lane files for multiple FileIDs</li>
            <li>Event data export to CSV</li>
            <li>CSV format includes: Plate, From, To, Lane, Ignore, FileID (for merged), etc.</li>
        </ul>

        <h2>Keyboard Shortcuts and Tips</h2>
        <ul>
            <li><b>Ctrl+O:</b> Open folder</li>
            <li><b>F1:</b> User guide</li>
            <li><b>Space:</b> Play/pause slideshow</li>
            <li><b>Left/Right arrows:</b> Previous/next image</li>
            <li>Double-click on timeline to zoom</li>
            <li>Right-click for context menu</li>
            <li>Theme switching in View menu</li>
        </ul>

        <h2>Advanced Features</h2>
        <h3>Memory Management</h3>
        <p>The application monitors memory usage and automatically clears caches when needed.</p>

        <h3>Autosave</h3>
        <p>Changes are automatically saved. Status shown in status bar.</p>

        <h3>Theme Support</h3>
        <p>Switch between Light and Dark themes. Themes persist across sessions and work consistently in exe builds.</p>

        <h2>Troubleshooting</h2>
        <h3>Application Won't Start</h3>
        <ul>
            <li>Check Python version (requires 3.8+)</li>
            <li>Reinstall dependencies: <code>pip install -r requirements.txt</code></li>
            <li>Check for missing PyQt6 installation</li>
        </ul>

        <h3>Data Won't Load</h3>
        <ul>
            <li>Check FileID folder structure</li>
            <li>Ensure .driveevt and .driveiri files exist</li>
            <li>Check Cam1 folder for images</li>
            <li>Check logs for specific errors</li>
        </ul>

        <h3>Lane Assignment Not Working</h3>
        <ul>
            <li>Ensure data folder is opened</li>
            <li>Check for overlap with current lane assignments</li>
            <li>Ignore periods don't allow other lane assignments</li>
            <li>For lane changes: ensure you drag the yellow marker to select end time</li>
            <li>Lane changes require releasing the marker to apply</li>
            <li>SK/TK/TM require proper lane selection</li>
        </ul>

        <h3>Theme Not Applying</h3>
        <ul>
            <li>Application forces Fusion style for consistency</li>
            <li>Custom palette overrides system theme</li>
            <li>Works in both development and exe builds</li>
        </ul>

        <h3>Performance Issues</h3>
        <ul>
            <li>Monitor memory usage in status bar</li>
            <li>Application auto-clears caches when memory is low</li>
            <li>Close other applications if needed</li>
        </ul>

        <h2>Contact</h2>
        <p>If you encounter issues, please contact the GeoEvent development team.</p>

        <h2>Version</h2>
        <p>Current version: 2.0.0</p>
        """


def show_user_guide(parent=None):
    """Convenience function to show user guide dialog"""
    dialog = UserGuideDialog(parent)
    dialog.exec()