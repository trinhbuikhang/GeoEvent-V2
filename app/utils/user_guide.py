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
        <p>GeoEvent is a road survey event coding application that helps users analyze and code data from cameras and GPS in traffic survey projects.</p>

        <h2>Installation and Startup</h2>
        <ol>
            <li>Ensure you have Python 3.8+ and required libraries installed (PyQt6, pandas, etc.)</li>
            <li>Run command: <code>python main.py</code></li>
            <li>The application will open with the main interface</li>
        </ol>

        <h2>Main Interface</h2>
        <h3>Menu Bar</h3>
        <ul>
            <li><b>File:</b> Open survey data folder</li>
            <li><b>View:</b> Change theme (Light/Dark)</li>
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
        </ol>

        <h3>2. Navigate Images</h3>
        <ul>
            <li>Use slider or Previous/Next buttons to navigate between images</li>
            <li>Timeline below shows current time position</li>
            <li>Click on timeline to jump to specific time</li>
        </ul>

        <h3>3. Lane Coding</h3>
        <p>The application supports various lane assignment types:</p>
        <ul>
            <li><b>Lane 1-4:</b> Main traffic lanes</li>
            <li><b>SK (Shoulder):</b> Road shoulder</li>
            <li><b>TK/TM:</b> Left/right turns with selected lane</li>
            <li><b>Ignore:</b> Ignore this time period</li>
        </ul>

        <h4>How to Code:</h4>
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

        <h3>4. Export Data</h3>
        <ul>
            <li>Lane data is automatically saved on changes</li>
            <li>Can export CSV for individual FileIDs or merge multiple FileIDs</li>
        </ul>

        <h2>Keyboard Shortcuts and Tips</h2>
        <ul>
            <li><b>Ctrl+O:</b> Open folder</li>
            <li><b>F1:</b> User guide</li>
            <li>Double-click on timeline to zoom</li>
            <li>Right-click for context menu</li>
        </ul>

        <h2>Troubleshooting</h2>
        <h3>Application Won't Start</h3>
        <ul>
            <li>Check Python version (requires 3.8+)</li>
            <li>Reinstall dependencies: <code>pip install -r requirements.txt</code></li>
        </ul>

        <h3>Data Won't Load</h3>
        <ul>
            <li>Check FileID folder structure</li>
            <li>Ensure .driveevt and .driveiri files exist</li>
            <li>Check logs for specific errors</li>
        </ul>

        <h3>Lane Assignment Not Working</h3>
        <ul>
            <li>Ensure data folder is opened</li>
            <li>Check for overlap with current lane assignments</li>
            <li>Ignore periods don't allow other lane assignments</li>
            <li>For lane changes: ensure you drag the yellow marker to select end time</li>
            <li>Lane changes require releasing the marker to apply</li>
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