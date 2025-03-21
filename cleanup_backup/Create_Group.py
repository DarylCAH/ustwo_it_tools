#!/usr/bin/env python3
"""
A Python + PyQt5 script for creating and managing Google Groups, with member
management, permission settings, and custom dialogs for all user interaction.

This module can be run standalone or imported into the unified tools application.
"""

import sys
import os
import re
import subprocess
import json
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QCheckBox, QDialog, QDialogButtonBox,
    QPlainTextEdit, QComboBox, QGridLayout, QRadioButton, QGroupBox, QSlider,
    QScrollArea
)
import config

# Path to GAM binary
GAM_PATH = os.path.expanduser("~/bin/gam7/gam")

# Config file for persistent settings
CONFIG_FILE = os.path.expanduser("~/.group_tool.json")

##############################################################################
# WORKER THREAD for GAM COMMANDS
##############################################################################

class WorkerThread(QThread):
    output = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, command):
        super().__init__()
        self.command = command

    def run(self):
        try:
            process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=True
            )
            
            for line in process.stdout:
                self.output.emit(line.strip())
            
            process.wait()
            self.finished.emit()
        except Exception as e:
            self.output.emit(f"Error: {str(e)}")
            self.finished.emit()

##############################################################################
# PERMISSION MATRIX
##############################################################################

class PermissionMatrix(QGroupBox):
    """
    A 5x5 matrix of checkboxes for group permissions.
    Some combinations are invalid and will not have checkboxes.
    """
    def __init__(self, parent=None):
        super().__init__("Access Settings", parent)
        self.init_ui()

    def init_ui(self):
        layout = QGridLayout()
        self.setLayout(layout)

        # Column headers
        headers = ["Group\nOwners", "Group\nManagers", "Group\nMembers", "Entire\norganisation", "External"]
        for col, text in enumerate(headers):
            label = QLabel(text)
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label, 0, col + 1)

        # Row headers
        rows = [
            "Who can contact group owners",
            "Who can view conversations",
            "Who can post",
            "Who can view members",
            "Who can manage members"
        ]
        self.checkboxes = {}
        for row, text in enumerate(rows):
            label = QLabel(text)
            layout.addWidget(label, row + 1, 0)
            
            for col in range(5):
                # Skip invalid combinations
                if (col == 3 and row == 4) or (col == 4 and row >= 3):
                    # Add empty spacer widget to maintain grid alignment
                    spacer = QWidget()
                    layout.addWidget(spacer, row + 1, col + 1)
                    continue
                
                cb = QCheckBox()
                # Center the checkbox
                cb.setStyleSheet("QCheckBox { margin: 0px; padding: 0px; }")
                layout.addWidget(cb, row + 1, col + 1, 1, 1, Qt.AlignCenter)
                
                # Set default states
                if col == 0:  # Group Owners
                    cb.setChecked(True)
                    if row in [0, 1, 3, 4]:  # Mandatory settings
                        cb.setEnabled(False)
                elif col == 3:  # Entire organisation
                    cb.setChecked(True)
                elif col == 4:  # External
                    cb.setChecked(False)
                else:  # Group Managers and Members
                    if col == 2 and row == 4:  # Members can't manage by default
                        cb.setChecked(False)
                    else:
                        cb.setChecked(True)
                
                self.checkboxes[(row, col)] = cb

                # Connect checkbox to handle sliding scale behavior
                cb.stateChanged.connect(lambda state, r=row, c=col: self.handle_checkbox_change(r, c, state))

    def handle_checkbox_change(self, row, col, state):
        """Handle checkbox state changes to implement sliding scale behavior"""
        if state == Qt.Unchecked:
            # When unchecking a box, uncheck all boxes to the right
            for c in range(col + 1, 5):
                if (row, c) in self.checkboxes:
                    self.checkboxes[(row, c)].setChecked(False)
        else:
            # When checking a box, check all boxes to the left
            for c in range(col):
                if (row, c) in self.checkboxes and self.checkboxes[(row, c)].isEnabled():
                    self.checkboxes[(row, c)].setChecked(True)

class JoinSettings(QGroupBox):
    """
    Radio buttons for group join settings and external member toggle.
    """
    def __init__(self, parent=None):
        super().__init__("Who can join the group", parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Radio buttons in correct order
        self.radio_approval = QRadioButton("People in the organisation must ask and then be approved before they can join the group")
        self.radio_anyone = QRadioButton("Anyone in the organisation can join")
        self.radio_invited = QRadioButton("Only invited users")
        self.radio_invited.setChecked(True)  # Default

        layout.addWidget(self.radio_approval)
        layout.addWidget(self.radio_anyone)
        layout.addWidget(self.radio_invited)

        # External members toggle
        toggle_layout = QHBoxLayout()
        toggle_label = QLabel("Allow members outside your organisation")
        
        # Create a custom toggle button
        self.external_toggle = QPushButton()
        self.external_toggle.setCheckable(True)
        self.external_toggle.setFixedWidth(60)
        self.external_toggle.setText("OFF")  # Initial state
        self.external_toggle.setStyleSheet("""
            QPushButton {
                border: 2px solid #999;
                border-radius: 15px;
                padding: 5px;
                background: #ccc;
                color: #666;
                font-weight: bold;
            }
            QPushButton:checked {
                background: #2196F3;
                border-color: #1976D2;
                color: white;
            }
        """)
        self.external_toggle.clicked.connect(self.update_toggle_appearance)
        
        toggle_layout.addWidget(toggle_label)
        toggle_layout.addWidget(self.external_toggle)
        toggle_layout.addStretch()  # Add stretch to prevent toggle from expanding
        layout.addLayout(toggle_layout)

    def update_toggle_appearance(self):
        """Update toggle button text based on state"""
        self.external_toggle.setText("ON" if self.external_toggle.isChecked() else "OFF")

    def value(self):
        """Get the current state of the external toggle"""
        return self.external_toggle.isChecked()

##############################################################################
# MAIN WINDOW
##############################################################################

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Google Group Creation Tool")
        self.settings = config.load_config(config.GROUP_CONFIG)
        self.init_ui()
        
    def init_ui(self):
        self.workers = []
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main horizontal layout for two columns
        main_hbox = QHBoxLayout(central)
        
        # Left column (inputs) - wrapped in scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # Disable horizontal scroll
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        
        # Top area: logo left, fields right
        top_hbox = QHBoxLayout()
        left_layout.addLayout(top_hbox)

        # Logo
        self.logo_label = QLabel()
        pixmap = QPixmap("/Library/JAMF/Icon/brandingimage.icns")
        scaled = pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.logo_label.setPixmap(scaled)
        top_hbox.addWidget(self.logo_label)

        # Right side inputs
        right_vbox = QVBoxLayout()
        top_hbox.addLayout(right_vbox)

        # Email field
        email_hbox = QHBoxLayout()
        lbl_email = QLabel("Your Email Address:")
        self.input_email = QLineEdit()
        email_hbox.addWidget(lbl_email)
        email_hbox.addWidget(self.input_email)
        right_vbox.addLayout(email_hbox)

        # Group details
        self.input_group_name = QLineEdit()
        self.input_group_name.setPlaceholderText("Group Name")
        self.input_group_email = QLineEdit()
        self.input_group_email.setPlaceholderText("Group Email Address")
        
        # Description as a text box
        desc_label = QLabel("Group Description:")
        self.input_description = QPlainTextEdit()
        self.input_description.setPlaceholderText("Enter a description for the group...")
        self.input_description.setFixedHeight(75)  # Height for ~3 lines

        right_vbox.addWidget(self.input_group_name)
        right_vbox.addWidget(self.input_group_email)
        right_vbox.addWidget(desc_label)
        right_vbox.addWidget(self.input_description)

        # Member entry boxes
        member_group = QGroupBox("Group Members")
        member_layout = QVBoxLayout()
        member_group.setLayout(member_layout)

        # Owners
        owner_label = QLabel("Group Owners:")
        self.input_owners = QPlainTextEdit()
        self.input_owners.setPlaceholderText("Enter owner email addresses...")
        self.input_owners.setFixedHeight(100)
        member_layout.addWidget(owner_label)
        member_layout.addWidget(self.input_owners)

        # Managers
        manager_label = QLabel("Group Managers:")
        self.input_managers = QPlainTextEdit()
        self.input_managers.setPlaceholderText("Enter manager email addresses...")
        self.input_managers.setFixedHeight(100)
        member_layout.addWidget(manager_label)
        member_layout.addWidget(self.input_managers)

        # Members
        member_label = QLabel("Group Members:")
        self.input_members = QPlainTextEdit()
        self.input_members.setPlaceholderText("Enter member email addresses...")
        self.input_members.setFixedHeight(100)
        member_layout.addWidget(member_label)
        member_layout.addWidget(self.input_members)

        left_layout.addWidget(member_group)

        # Permission matrix
        self.permission_matrix = PermissionMatrix()
        left_layout.addWidget(self.permission_matrix)

        # Join settings
        self.join_settings = JoinSettings()
        left_layout.addWidget(self.join_settings)

        # Buttons
        btn_hbox = QHBoxLayout()
        left_layout.addLayout(btn_hbox)

        self.btn_start = QPushButton("Create Group")
        self.btn_start.clicked.connect(self.handle_workflow)
        btn_hbox.addWidget(self.btn_start)

        self.btn_quit = QPushButton("Quit")
        self.btn_quit.clicked.connect(self.close)
        btn_hbox.addWidget(self.btn_quit)

        # Add left column to scroll area
        scroll_area.setWidget(left_column)
        main_hbox.addWidget(scroll_area, stretch=1)

        # Right column (output)
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        
        # Log area with title
        log_label = QLabel("Output Log")
        log_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_layout.addWidget(log_label)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        right_layout.addWidget(self.log_area)

        # Add right column to main layout
        main_hbox.addWidget(right_column, stretch=1)

        # Set window size
        self.resize(1200, 800)
        self.load_config()

    def load_config(self):
        """Load saved configuration including email"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    if 'email' in config:
                        self.input_email.setText(config['email'])
            except Exception as e:
                self.log(f"[Warning] Could not load configuration: {str(e)}")

    def save_config(self):
        """Save configuration including email"""
        try:
            config = {
                'email': self.input_email.text().strip()
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            self.log(f"[Warning] Could not save configuration: {str(e)}")

    def log(self, text):
        self.log_area.append(text)

    def handle_workflow(self):
        """Main workflow for creating a group and adding members"""
        self.log_area.clear()
        
        # Validate inputs
        self.user_email = self.input_email.text().strip()
        self.group_name = self.input_group_name.text().strip()
        self.group_email = self.input_group_email.text().strip()
        self.description = self.input_description.toPlainText().strip()  # Changed to toPlainText()

        if not all([self.user_email, self.group_name, self.group_email]):
            self.show_warning("Missing Info", "Please provide your email, group name, and group email address.")
            return

        # Save the email for future use
        self.save_config()

        # Start the group creation process
        self.log(f"\nStarting group creation workflow for '{self.group_name}'...")
        self.create_group()

    def show_warning(self, title, message):
        """Show a warning dialog"""
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setWindowIcon(QIcon("/Library/JAMF/Icon/brandingimage.icns"))
        layout = QVBoxLayout(dlg)

        lbl = QLabel(message)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(dlg.accept)
        layout.addWidget(buttons)

        dlg.exec_()

    def closeEvent(self, event):
        """Handle application closure"""
        for w in self.workers:
            if w.isRunning():
                self.log("\n[Info] Waiting for background tasks to complete...")
                w.wait(2000)
                if w.isRunning():
                    self.log("\n[Warning] Forcibly terminating background task.")
                    w.terminate()
        super().closeEvent(event)

    def save_settings(self):
        """Save current settings to config file"""
        config.save_config(config.GROUP_CONFIG, self.settings)

    def run_gam_command(self, command):
        """Run a GAM command using the configured GAM path"""
        full_command = f"{config.GAM_PATH} {command}"
        worker = WorkerThread(full_command)
        worker.output.connect(self.log_output)
        worker.finished.connect(self.command_finished)
        worker.start()
        self.current_worker = worker

def standalone():
    """Run this tool as a standalone application"""
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("/Library/JAMF/Icon/brandingimage.icns"))
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    standalone() 