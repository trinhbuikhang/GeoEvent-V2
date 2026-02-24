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

        <h2>Quick Start Workflow</h2>
        <p>GeoEvent is designed for efficient road survey data coding. Follow this workflow for best results:</p>

        <h3>1. Open Survey Data Folder</h3>
        <ol>
            <li>Select <b>File > Open Folder...</b> from the menu</li>
            <li>Choose a folder containing survey data (network paths supported)</li>
            <li>The application automatically scans for FileID folders</li>
            <li>First FileID loads automatically with images, GPS, and existing lane data</li>
        </ol>

        <h3>2. Navigate Between FileIDs</h3>
        <ul>
            <li>Use <b>Previous/Next FileID</b> buttons in toolbar</li>
            <li>Status bar shows current FileID and total count</li>
            <li><b>Auto-save:</b> Data automatically saves when switching FileIDs</li>
            <li><b>Performance:</b> Only current FileID data loads (fast switching)</li>
        </ul>

        <h3>3. Code Lane Assignments</h3>
        <p>Assign lanes using the lane buttons. Each FileID maintains separate lane data:</p>

        <h4>Basic Lane Assignment:</h4>
        <ol>
            <li>Navigate to desired time using slider or arrow keys</li>
            <li>Click lane button (1-4) to assign at current time</li>
            <li>For lane changes: drag the yellow marker to select end time</li>
            <li>Timeline colors update to show assignments</li>
        </ol>

        <h4>Special Lane Types:</h4>
        <ul>
            <li><b>SK (Shoulder):</b> Click SK button - automatically codes as SK + current lane</li>
            <li><b>TK/TM (Turns):</b> Click TK1/TM1 buttons directly for turn lanes</li>
            <li><b>Ignore:</b> Mark time periods to exclude from analysis</li>
        </ul>

        <h4>Lane Change Process:</h4>
        <ol>
            <li>Click any lane button to start change</li>
            <li>Dialog appears with marker instructions</li>
            <li>Yellow marker shows on timeline at current position</li>
            <li>Drag marker to select end time (image preview updates)</li>
            <li>Release marker to confirm change</li>
        </ol>

        <h3>4. Timeline Navigation</h3>
        <ul>
            <li><b>Click:</b> Jump to specific time</li>
            <li><b>Double-click:</b> Zoom in/out</li>
            <li><b>Drag:</b> Pan left/right when zoomed</li>
            <li>Colored bars show lane assignments and events</li>
            <li>Hover for time and lane details</li>
        </ul>

        <h4>Event name pop-up when marker passes through</h4>
        <p>When the yellow position marker moves through an event on the timeline, the app can show a small pop-up label with the event name. This is especially useful for short events where the colored bar is hard to see.</p>
        <p><b>Turn on/off:</b> <b>Tools &gt; Settings...</b> &rarr; <b>Timeline</b> &rarr; check or uncheck <b>Highlight event name when marker passes through event</b>. The change applies immediately.</p>

        <h3>5. Image Navigation</h3>
        <ul>
            <li><b>Slider:</b> Drag to navigate images</li>
            <li><b>Arrow keys:</b> Previous/next image</li>
            <li><b>Space:</b> Play/pause slideshow</li>
            <li>Image info shows timestamp, GPS coordinates</li>
        </ul>

        <h3>6. Data Management</h3>
        <h4>Automatic Saving:</h4>
        <ul>
            <li>Lane assignments save automatically on changes</li>
            <li>Data saves when switching FileIDs or folders</li>
            <li>Status bar shows autosave status</li>
            <li>Each FileID has separate lane data file</li>
        </ul>

        <h4>Manual Data Merge:</h4>
        <ul>
            <li>Select <b>File > Merge All Data</b> to combine all FileIDs</li>
            <li>Creates merged CSV files in root folder</li>
            <li>Individual FileID files remain unchanged</li>
            <li>Use when ready to export final combined dataset</li>
        </ul>

        <h3>7. Event Management</h3>
        <ul>
            <li>Timeline shows events as colored bars</li>
            <li>Click events to view/edit details</li>
            <li>Add, edit, or delete events as needed</li>
            <li>Events export with lane data</li>
        </ul>

        <h2>Interface Overview</h2>
        <h3>Main Components:</h3>
        <ul>
            <li><b>Menu Bar:</b> File operations, view options, help</li>
            <li><b>Toolbar:</b> FileID navigation, lane buttons, controls</li>
            <li><b>Image Panel:</b> Current camera image with timestamp/GPS</li>
            <li><b>Timeline:</b> Time-based view of lane assignments and events</li>
            <li><b>Status Bar:</b> FileID info, memory usage, autosave status</li>
        </ul>

        <h2>Keyboard Shortcuts</h2>
        <table border="1" cellpadding="5" cellspacing="0">
            <tr><th>Shortcut</th><th>Action</th></tr>
            <tr><td>Ctrl+O</td><td>Open folder</td></tr>
            <tr><td>F1</td><td>Show user guide</td></tr>
            <tr><td>Space</td><td>Play/pause slideshow</td></tr>
            <tr><td>← →</td><td>Previous/next image</td></tr>
            <tr><td>Ctrl+S</td><td>Manual save (if needed)</td></tr>
        </table>

        <h2>Best Practices</h2>
        <h3>Efficient Coding:</h3>
        <ul>
            <li>Work through FileIDs systematically using navigation buttons</li>
            <li>Use timeline zoom for detailed work</li>
            <li>Regularly check status bar for autosave confirmation</li>
            <li>Use Ignore for invalid data periods</li>
        </ul>

        <h3>Data Organization:</h3>
        <ul>
            <li>Each FileID maintains separate lane assignments</li>
            <li>Data automatically saves when switching</li>
            <li>Use manual merge only when all FileIDs are complete</li>
            <li>Individual files preserve original data integrity</li>
        </ul>

        <h3>Performance Tips:</h3>
        <ul>
            <li>Application loads only current FileID data</li>
            <li>Fast switching between FileIDs</li>
            <li>Memory usage monitored automatically</li>
            <li>Close other applications if experiencing slowdowns</li>
        </ul>

        <h2>Troubleshooting</h2>
        <h3>Common Issues:</h3>

        <h4>Data Won't Load:</h4>
        <ul>
            <li>Verify FileID folder structure</li>
            <li>Check for required files: .driveevt, .driveiri, Cam1 images</li>
            <li>Ensure network paths are accessible</li>
            <li>Check application logs for specific errors</li>
        </ul>

        <h4>Lane Assignment Problems:</h4>
        <ul>
            <li>Ensure data folder is loaded</li>
            <li>Check for time overlaps with existing assignments</li>
            <li>Ignore periods block other assignments</li>
            <li>For changes: always drag and release the yellow marker</li>
            <li>SK requires being on a lane (1-4) first</li>
            <li>TK/TM lanes work like regular lanes - click directly</li>
        </ul>

        <h4>Performance Issues:</h4>
        <ul>
            <li>Monitor memory usage in status bar</li>
            <li>Application auto-manages memory</li>
            <li>Close other applications if needed</li>
            <li>Large datasets may take time to merge</li>
        </ul>

        <h4>Data Concerns:</h4>
        <ul>
            <li>Each FileID has isolated lane data</li>
            <li>Auto-save prevents data loss</li>
            <li>Manual merge creates combined files</li>
            <li>Original individual files remain intact</li>
        </ul>

        <h2>Version Information</h2>
        <p><b>GeoEvent Version 2.0.0</b> - Optimized for efficient survey data coding</p>
        """


def show_user_guide(parent=None):
    """Convenience function to show user guide dialog"""
    dialog = UserGuideDialog(parent)
    dialog.exec()