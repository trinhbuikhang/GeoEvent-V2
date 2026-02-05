"""
Keyboard Shortcuts Dialog - Display available keyboard shortcuts
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTextEdit, QPushButton, QDialogButtonBox
)
from PyQt6.QtCore import Qt


class ShortcutsDialog(QDialog):
    """Dialog to display keyboard shortcuts and UI navigation help"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        self.setModal(True)
        self.resize(600, 500)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Create dialog UI showing all shortcuts organized by category"""
        layout = QVBoxLayout(self)
        
        # Create text display for shortcuts
        shortcuts_text = QTextEdit()
        shortcuts_text.setReadOnly(True)
        shortcuts_text.setHtml(self._get_shortcuts_html())
        
        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.close)
        
        layout.addWidget(shortcuts_text)
        layout.addWidget(button_box)
        
    def _get_shortcuts_html(self) -> str:
        """Generate HTML content for shortcuts display"""
        return """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 10px; }
                h2 { color: #2874A6; border-bottom: 2px solid #2874A6; padding-bottom: 5px; }
                h3 { color: #1F618D; margin-top: 15px; }
                table { width: 100%; border-collapse: collapse; margin: 10px 0; }
                td { padding: 5px 10px; }
                .key { 
                    font-weight: bold; 
                    background-color: #F4F6F7; 
                    padding: 3px 8px; 
                    border-radius: 3px;
                    font-family: monospace;
                    color: #34495E;
                }
                .desc { padding-left: 20px; }
            </style>
        </head>
        <body>
            <h2>GeoEvent Keyboard Shortcuts</h2>
            
            <h3>🖼️ Image Navigation</h3>
            <table>
                <tr>
                    <td><span class="key">Left Arrow</span> or <span class="key">A</span></td>
                    <td class="desc">Previous image</td>
                </tr>
                <tr>
                    <td><span class="key">Right Arrow</span> or <span class="key">D</span></td>
                    <td class="desc">Next image</td>
                </tr>
                <tr>
                    <td><span class="key">Space</span></td>
                    <td class="desc">Play/Pause auto-play slideshow</td>
                </tr>
                <tr>
                    <td><span class="key">Home</span></td>
                    <td class="desc">Jump to first image</td>
                </tr>
                <tr>
                    <td><span class="key">End</span></td>
                    <td class="desc">Jump to last image</td>
                </tr>
            </table>
            
            <h3>🛣️ Lane Assignment</h3>
            <table>
                <tr>
                    <td><span class="key">Q</span></td>
                    <td class="desc">Assign lane 1 (Leftmost)</td>
                </tr>
                <tr>
                    <td><span class="key">W</span></td>
                    <td class="desc">Assign lane 2</td>
                </tr>
                <tr>
                    <td><span class="key">E</span></td>
                    <td class="desc">Assign lane 3</td>
                </tr>
                <tr>
                    <td><span class="key">R</span></td>
                    <td class="desc">Assign lane 4</td>
                </tr>
                <tr>
                    <td><span class="key">T</span></td>
                    <td class="desc">Assign lane 5 (Rightmost)</td>
                </tr>
                <tr>
                    <td><span class="key">K</span></td>
                    <td class="desc">Assign shoulder lane</td>
                </tr>
            </table>
            
            <h3>⚡ Speed Control</h3>
            <table>
                <tr>
                    <td><span class="key">1</span></td>
                    <td class="desc">Slow speed (500ms between images)</td>
                </tr>
                <tr>
                    <td><span class="key">2</span></td>
                    <td class="desc">Normal speed (100ms between images)</td>
                </tr>
                <tr>
                    <td><span class="key">3</span></td>
                    <td class="desc">Fast speed (50ms between images)</td>
                </tr>
            </table>
            
            <h3>⏱️ Timeline Navigation</h3>
            <table>
                <tr>
                    <td><span class="key">Click</span></td>
                    <td class="desc">Jump to clicked timestamp</td>
                </tr>
                <tr>
                    <td><span class="key">Drag</span></td>
                    <td class="desc">Scroll through timeline</td>
                </tr>
            </table>
            
            <h3>📝 Event Management</h3>
            <table>
                <tr>
                    <td><span class="key">Double-click event</span></td>
                    <td class="desc">Open event editor</td>
                </tr>
                <tr>
                    <td><span class="key">Ctrl+S</span></td>
                    <td class="desc">Save all changes</td>
                </tr>
                <tr>
                    <td><span class="key">Ctrl+Z</span></td>
                    <td class="desc">Undo last change (when supported)</td>
                </tr>
            </table>
            
            <h3>🗺️ Minimap</h3>
            <table>
                <tr>
                    <td><span class="key">Click marker</span></td>
                    <td class="desc">Jump to image location</td>
                </tr>
                <tr>
                    <td><span class="key">Scroll wheel</span></td>
                    <td class="desc">Zoom in/out</td>
                </tr>
            </table>
            
            <h3>💡 Tips</h3>
            <ul>
                <li>Hover over buttons to see tooltips with shortcuts</li>
                <li>Use arrow keys for quick image navigation</li>
                <li>Use number keys (Q-W-E-R-T) for fast lane assignment</li>
                <li>Auto-play with Space bar for continuous review</li>
                <li>Timeline shows event markers - click to jump</li>
            </ul>
        </body>
        </html>
        """
