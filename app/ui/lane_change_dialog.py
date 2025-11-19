"""
Lane Change Confirmation Dialog
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from datetime import datetime
from enum import Enum

class LaneChangeResult(Enum):
    CONFIRMED = 0
    CONTINUE = 1
    CANCELLED = 2

class LaneChangeConfirmationDialog(QDialog):
    """
    Dialog for confirming lane changes with Yes/Continue/Cancel options
    """

    def __init__(self, parent=None, current_lane=None, new_lane=None,
                 start_time=None, end_time=None):
        super().__init__(parent)
        self.result = LaneChangeResult.CANCELLED
        self.current_lane = current_lane or "Unknown"
        self.new_lane = new_lane or "Unknown"
        self.start_time = start_time
        self.end_time = end_time

        self.setWindowTitle("Confirm Lane Change")
        self.setModal(True)
        self.setFixedWidth(400)

        self.setup_ui()

    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title_label = QLabel("Confirm Lane Change")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # Lane change info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)

        lane_info = QLabel(f"Current Lane: <b>{self.current_lane}</b> → New Lane: <b>{self.new_lane}</b>")
        lane_info.setTextFormat(Qt.TextFormat.RichText)
        info_layout.addWidget(lane_info)

        if self.start_time and self.end_time:
            time_info = QLabel(f"Time: {self.start_time.strftime('%H:%M:%S')} → {self.end_time.strftime('%H:%M:%S')}")
            info_layout.addWidget(time_info)

        layout.addLayout(info_layout)

        # Spacer
        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Question
        question_label = QLabel("Do you want to apply this change?")
        question_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(question_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # Yes button
        self.yes_button = QPushButton("Yes (Apply)")
        self.yes_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.yes_button.clicked.connect(self.on_yes)
        button_layout.addWidget(self.yes_button)

        # Continue button
        self.continue_button = QPushButton("Continue (Adjust)")
        self.continue_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.continue_button.clicked.connect(self.on_continue)
        button_layout.addWidget(self.continue_button)

        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.cancel_button.clicked.connect(self.on_cancel)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        # Set default button
        self.continue_button.setDefault(True)
        self.continue_button.setFocus()

    def on_yes(self):
        """Handle Yes button click"""
        self.result = LaneChangeResult.CONFIRMED
        self.accept()

    def on_continue(self):
        """Handle Continue button click"""
        self.result = LaneChangeResult.CONTINUE
        self.accept()

    def on_cancel(self):
        """Handle Cancel button click"""
        self.result = LaneChangeResult.CANCELLED
        self.reject()

    @staticmethod
    def show_dialog(parent=None, current_lane=None, new_lane=None,
                   start_time=None, end_time=None):
        """
        Static method to show dialog and return result
        Returns: LaneChangeResult enum
        """
        dialog = LaneChangeConfirmationDialog(
            parent=parent,
            current_lane=current_lane,
            new_lane=new_lane,
            start_time=start_time,
            end_time=end_time
        )
        dialog.exec()
        return dialog.result