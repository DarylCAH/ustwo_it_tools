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
import time
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QCheckBox, QDialog, QDialogButtonBox,
    QPlainTextEdit, QComboBox, QGridLayout, QRadioButton, QGroupBox, QSlider,
    QScrollArea, QMessageBox
)
from . import config

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
    done_signal = pyqtSignal(int, list)  # (returncode, all_lines)

    def __init__(self, command):
        super().__init__()
        self.command = command
        self.captured_lines = []

    def run(self):
        try:
            # Convert string command to list for Popen
            if isinstance(self.command, str):
                cmd_list = [config.GAM_PATH] + self.command.split()
            else:
                # Already a list, make sure first item is GAM path
                cmd_list = self.command
                if cmd_list[0] != config.GAM_PATH:
                    cmd_list.insert(0, config.GAM_PATH)
            
            # Log if GAM not found
            if not os.path.isfile(cmd_list[0]):
                error_msg = f"[ERROR] Could not find GAM at {cmd_list[0]}"
                self.output.emit(error_msg)
                self.captured_lines.append(error_msg)
                self.done_signal.emit(1, self.captured_lines)
                self.finished.emit()
                return
                
            # Execute command
            process = subprocess.Popen(
                cmd_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Capture stdout
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                stripped = line.rstrip('\n')
                self.output.emit(stripped)
                self.captured_lines.append(stripped)
            
            # Capture stderr
            err_output = process.stderr.read()
            if err_output:
                for e_line in err_output.splitlines():
                    combined = f"\n{e_line}"
                    self.output.emit(combined)
                    self.captured_lines.append(combined)
            
            # Get return code and emit signals
            rc = process.wait()
            self.done_signal.emit(rc, self.captured_lines)
            self.finished.emit()
        except Exception as e:
            ex_line = f"[Exception] {str(e)}"
            self.output.emit(ex_line)
            self.captured_lines.append(ex_line)
            self.done_signal.emit(1, self.captured_lines)
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
# DIALOGS
##############################################################################

class MultiLineAddressesDialog(QDialog):
    """Dialog for entering multiple email addresses"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel("Enter email addresses (one per line or comma-separated):")
        layout.addWidget(instructions)
        
        # Text input area
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("user1@example.com\nuser2@example.com")
        self.text_edit.setMinimumWidth(400)
        self.text_edit.setMinimumHeight(200)
        layout.addWidget(self.text_edit)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

##############################################################################
# MAIN WINDOW
##############################################################################

class CreateGroupTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.workers = []
        self.settings = config.load_config(config.GROUP_CONFIG)
        
        # Main horizontal layout for two columns
        main_hbox = QHBoxLayout(self)
        
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
        self.perm_matrix = PermissionMatrix()
        left_layout.addWidget(self.perm_matrix)

        # Join settings
        self.join_settings = JoinSettings()
        left_layout.addWidget(self.join_settings)

        # Add scroll area to main layout
        scroll_area.setWidget(left_column)
        main_hbox.addWidget(scroll_area)

        # Right column (log area)
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)

        # Log area title
        log_title = QLabel("Output Log")
        log_title.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(log_title)

        # Log area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        right_layout.addWidget(self.log_area)

        # Add right column to main layout
        main_hbox.addWidget(right_column)

        # Set column stretch factors (1:1 ratio)
        main_hbox.setStretch(0, 1)  # Left column
        main_hbox.setStretch(1, 1)  # Right column

        # Buttons at the bottom
        btn_hbox = QHBoxLayout()
        right_layout.addLayout(btn_hbox)

        self.btn_start = QPushButton("Start Workflow")
        self.btn_start.clicked.connect(self.handle_workflow)
        btn_hbox.addWidget(self.btn_start)

        self.btn_quit = QPushButton("Quit")
        self.btn_quit.clicked.connect(self.close)
        btn_hbox.addWidget(self.btn_quit)

        # Load saved email
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
        """Handle the workflow start button click"""
        # Get user inputs
        self.user_email = self.input_email.text().strip()
        self.group_name = self.input_group_name.text().strip()
        self.group_email = self.input_group_email.text().strip()
        self.description = self.input_description.toPlainText().strip()
        
        # Get member lists
        self.owners = self.parse_addresses(self.input_owners.toPlainText())
        self.managers = self.parse_addresses(self.input_managers.toPlainText())
        self.members = self.parse_addresses(self.input_members.toPlainText())
        
        # Clean up previous states
        self.log_area.clear()
        
        # Validate inputs
        if not self.user_email:
            self.show_warning("Missing Information", "Please enter your email address.")
            return
            
        if not all([self.group_name, self.group_email]):
            self.show_warning("Missing Information", "Please enter both group name and email address.")
            return
            
        # Save the settings
        self.settings["email"] = self.user_email
        self.save_config()
        
        # Start the workflow
        self.log(f"\nStarting workflow for group '{self.group_name}' with email {self.group_email}")
        self.create_group()

    def create_group(self):
        """Create a Google Group"""
        self.btn_start.setEnabled(False)
        self.log("\nCreating group...")
        
        # Build create command
        cmd_parts = [f"create group {self.group_email}"]
        cmd_parts.append(f"name \"{self.group_name}\"")
        if self.description:
            cmd_parts.append(f"description \"{self.description}\"")
        cmd_parts.append("who_can_join invited_can_join")
        
        cmd = " ".join(cmd_parts)
        
        def creation_done(rc, lines):
            if rc != 0:
                self.log("\n[Error] Failed to create the group.")
                self.btn_start.setEnabled(True)
                return
            
            self.log("\nGroup created successfully.")
            self.verify_group_exists()
        
        worker = WorkerThread(cmd)
        worker.output.connect(self.log_output)
        worker.done_signal.connect(creation_done)
        worker.finished.connect(lambda: self.cleanup_thread(worker))
        worker.start()
        self.workers.append(worker)

    def verify_group_exists(self, attempts=0):
        """Verify the group was created successfully"""
        self.log("\nVerifying group creation...")
        
        cmd = f"info group {self.group_email}"
        
        def verify_done(rc, lines):
            if rc != 0:
                if attempts < 3:
                    self.log("\nGroup not found yet, retrying...")
                    time.sleep(2)
                    self.verify_group_exists(attempts + 1)
                else:
                    self.log("\n[Error] Could not verify group creation.")
                    self.btn_start.setEnabled(True)
                return
            
            self.log("\nGroup verified. Configuring permissions...")
            self.configure_permissions()  # Configure permissions first
        
        worker = WorkerThread(cmd)
        worker.output.connect(self.log_output)
        worker.done_signal.connect(verify_done)
        worker.finished.connect(lambda: self.cleanup_thread(worker))
        worker.start()
        self.workers.append(worker)

    def configure_permissions(self):
        """Configure group permissions based on matrix settings"""
        self.log("\nConfiguring group permissions...")
        
        # Build settings dictionary
        settings = {
            "whoCanContactOwner": "ALL_MANAGERS_CAN_CONTACT",
            "whoCanViewGroup": "ALL_MEMBERS_CAN_VIEW",
            "whoCanViewMembership": "ALL_MEMBERS_CAN_VIEW",
            "whoCanJoin": "INVITED_CAN_JOIN",
            "whoCanPostMessage": "ALL_MEMBERS_CAN_POST",
            "allowExternalMembers": "true" if self.join_settings.value() else "false"
        }
        
        # Update based on permission matrix
        contact_map = ["OWNERS_ONLY", "ALL_MANAGERS_CAN_CONTACT", "ALL_MEMBERS_CAN_CONTACT", "ANYONE_CAN_CONTACT"]
        view_map = ["OWNERS_ONLY", "ALL_MANAGERS_CAN_VIEW", "ALL_MEMBERS_CAN_VIEW", "ALL_IN_DOMAIN_CAN_VIEW", "ANYONE_CAN_VIEW"]
        post_map = ["OWNERS_ONLY", "ALL_MANAGERS_CAN_POST", "ALL_MEMBERS_CAN_POST", "ALL_IN_DOMAIN_CAN_POST", "ANYONE_CAN_POST"]
        members_map = ["OWNERS_ONLY", "ALL_MANAGERS_CAN_VIEW", "ALL_MEMBERS_CAN_VIEW", "ALL_IN_DOMAIN_CAN_VIEW"]
        
        # Get highest checked column for each row
        for row in range(5):
            highest = -1
            for col in range(5):
                if (row, col) in self.perm_matrix.checkboxes and self.perm_matrix.checkboxes[(row, col)].isChecked():
                    highest = col
            
            # Update settings based on row
            if row == 0:  # Contact owners
                if highest >= 0:
                    settings["whoCanContactOwner"] = contact_map[min(highest, len(contact_map)-1)]
            elif row == 1:  # View conversations
                if highest >= 0:
                    settings["whoCanViewGroup"] = view_map[min(highest, len(view_map)-1)]
            elif row == 2:  # Post
                if highest >= 0:
                    settings["whoCanPostMessage"] = post_map[min(highest, len(post_map)-1)]
            elif row == 3:  # View members
                if highest >= 0:
                    settings["whoCanViewMembership"] = members_map[min(highest, len(members_map)-1)]
        
        # Update join settings based on radio buttons
        if self.join_settings.radio_approval.isChecked():
            settings["whoCanJoin"] = "CAN_REQUEST_TO_JOIN"
        elif self.join_settings.radio_anyone.isChecked():
            settings["whoCanJoin"] = "ALL_IN_DOMAIN_CAN_JOIN"
        else:  # radio_invited is checked
            settings["whoCanJoin"] = "INVITED_CAN_JOIN"
        
        # Build the command - fixing the syntax
        cmd = f"update group {self.group_email} "
        for key, value in settings.items():
            cmd += f"setting {key} {value} "  # Changed 'settings' to 'setting'
        
        def settings_done(rc, lines):
            if rc != 0:
                self.log("\n[Error] Failed to update group settings.")
                self.btn_start.setEnabled(True)
                return
            
            self.log("\nGroup settings updated successfully.")
            if any([self.owners, self.managers, self.members]):
                self.process_members()  # Process members after permissions are set
            else:
                self.verify_settings()
        
        worker = WorkerThread(cmd)
        worker.output.connect(self.log_output)
        worker.done_signal.connect(settings_done)
        worker.finished.connect(lambda: self.cleanup_thread(worker))
        worker.start()
        self.workers.append(worker)

    def process_members(self):
        """Add members to the group with their respective roles"""
        self.log("\nAdding members to the group...")
        
        # Track progress
        self.total_members = len(self.owners) + len(self.managers) + len(self.members)
        self.processed_members = 0
        
        def member_added(rc, lines):
            self.processed_members += 1
            if rc != 0:
                self.log("\n[Warning] Failed to add a member.")
            
            if self.processed_members >= self.total_members:
                self.log("\nAll members processed.")
                self.verify_settings()
        
        # Add owners
        for owner in self.owners:
            cmd = f"update group {self.group_email} add owner {owner}"
            worker = WorkerThread(cmd)
            worker.output.connect(self.log_output)
            worker.done_signal.connect(member_added)
            worker.finished.connect(lambda: self.cleanup_thread(worker))
            worker.start()
            self.workers.append(worker)
        
        # Add managers
        for manager in self.managers:
            cmd = f"update group {self.group_email} add manager {manager}"
            worker = WorkerThread(cmd)
            worker.output.connect(self.log_output)
            worker.done_signal.connect(member_added)
            worker.finished.connect(lambda: self.cleanup_thread(worker))
            worker.start()
            self.workers.append(worker)
        
        # Add members
        for member in self.members:
            cmd = f"update group {self.group_email} add member {member}"
            worker = WorkerThread(cmd)
            worker.output.connect(self.log_output)
            worker.done_signal.connect(member_added)
            worker.finished.connect(lambda: self.cleanup_thread(worker))
            worker.start()
            self.workers.append(worker)

    def verify_settings(self, attempts=0):
        """Verify the settings were applied correctly"""
        self.log("\nVerifying group settings...")
        
        cmd = f"info group {self.group_email} settings"
        
        def verify_done(rc, lines):
            if rc != 0:
                if attempts < 3:
                    self.log("\nSettings not updated yet, retrying...")
                    time.sleep(2)
                    self.verify_settings(attempts + 1)
                else:
                    self.log("\n[Error] Could not verify group settings.")
                self.btn_start.setEnabled(True)
                return
            
            self.log("\nGroup settings verified successfully.")
            self.log("\nGroup creation workflow completed!")
            self.btn_start.setEnabled(True)
        
        worker = WorkerThread(cmd)
        worker.output.connect(self.log_output)
        worker.done_signal.connect(verify_done)
        worker.finished.connect(lambda: self.cleanup_thread(worker))
        worker.start()
        self.workers.append(worker)

    def parse_addresses(self, text):
        """Parse email addresses from text input"""
        replaced = text.replace(",", " ")
        return [x.strip() for x in replaced.split() if x.strip()]

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
        worker.finished.connect(lambda: self.cleanup_thread(worker))
        worker.start()
        self.workers.append(worker)
        
    def log_output(self, text):
        """Log output from the worker thread"""
        self.log(text)
        
    def cleanup_thread(self, worker):
        """Remove the thread from our tracking list once it's done"""
        if worker in self.workers:
            self.workers.remove(worker)
        self.command_finished()
        
    def command_finished(self):
        """Enable buttons if all threads are done"""
        if not self.workers:
            self.btn_start.setEnabled(True)

def standalone():
    """Run this tool as a standalone application"""
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("/Library/JAMF/Icon/brandingimage.icns"))
    w = CreateGroupTab()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    standalone() 