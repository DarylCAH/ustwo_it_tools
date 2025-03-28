#!/usr/bin/env python3
"""
A Python + PyQt5 script for creating and managing Google Groups, with member
management, permission settings, and custom dialogs for all user interaction.
Uses the same custom branding and UI style as the Shared Drive creation tool.

Key Features:
1) Create Google Groups with full permission configuration
2) Add members with different roles (owners, managers, members)
3) Configure access settings via a visual permission matrix
4) Persistent email storage for convenience
5) Custom branded dialogs for all user interactions
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
    QScrollArea
)

# Path to GAM binary
GAM_PATH = os.path.expanduser("~/bin/gam7/gam")

# Config file for persistent settings
CONFIG_FILE = os.path.expanduser("~/.group_tool.json")

##############################################################################
# WORKER THREAD for GAM COMMANDS
##############################################################################

class WorkerThread(QThread):
    line_signal = pyqtSignal(str)
    done_signal = pyqtSignal(int, list)  # (returncode, all_lines)

    def __init__(self, cmd_list):
        super().__init__()
        self.cmd_list = cmd_list
        self.captured_lines = []

    def run(self):
        if not os.path.isfile(self.cmd_list[0]):
            err_line = f"\n[Error] Could not find 'gam' at {self.cmd_list[0]}"
            self.line_signal.emit(err_line)
            self.captured_lines.append(err_line)
            self.done_signal.emit(1, self.captured_lines)
            return

        try:
            proc = subprocess.Popen(
                self.cmd_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                stripped = line.rstrip('\n')
                self.line_signal.emit(stripped)
                self.captured_lines.append(stripped)

            err_output = proc.stderr.read()
            if err_output:
                for e_line in err_output.splitlines():
                    combined = f"\n{e_line}"
                    self.line_signal.emit(combined)
                    self.captured_lines.append(combined)

            rc = proc.wait()
            self.done_signal.emit(rc, self.captured_lines)

        except Exception as e:
            ex_line = f"[Exception] {str(e)}"
            self.line_signal.emit(ex_line)
            self.captured_lines.append(ex_line)
            self.done_signal.emit(1, self.captured_lines)

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
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Google Group Creation Tool")
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

    def create_group(self):
        """Create the Google Group"""
        cmd = [
            GAM_PATH, "create", "group", self.group_email,
            "name", self.group_name
        ]
        
        if self.description:
            cmd.extend(["description", self.description])

        def creation_done(rc, lines):
            if rc != 0:
                self.log("\n[Error] Failed to create group.")
                return
            
            self.log("\nGroup created successfully. Waiting for propagation...")
            # Add a small initial delay before first verification attempt
            QThread.sleep(5)
            self.verify_group_exists()

        self.run_threaded_command(cmd, creation_done)

    def verify_group_exists(self, attempts=0):
        """Verify the group exists, with retries"""
        cmd = [GAM_PATH, "info", "group", self.group_email]

        def verify_done(rc, lines):
            if rc != 0:
                if attempts < 3:  # Try up to 3 times
                    self.log("\nGroup not found yet. Waiting 30 seconds...")
                    QThread.sleep(30)
                    self.verify_group_exists(attempts + 1)
                else:
                    # Even if verification fails, we'll proceed since the create command succeeded
                    self.log("\n[Warning] Group verification timed out, but group was created successfully.")
                    self.log("\nProceeding with member addition...")
                    self.collect_members()
                return
            
            self.log("\nGroup verified. Collecting member information...")
            self.collect_members()

        self.run_threaded_command(cmd, verify_done)

    def collect_members(self):
        """Collect member information from text boxes"""
        # Add a small delay before adding members to ensure group is ready
        QThread.sleep(5)
        
        owners = self.input_owners.toPlainText().strip()
        if not owners:
            self.log("\n[Error] At least one group owner is required.")
            return

        managers = self.input_managers.toPlainText().strip()
        members = self.input_members.toPlainText().strip()

        # Add another small delay before processing members
        QThread.sleep(2)
        self.process_members(owners, managers, members)

    def process_members(self, owners, managers, members):
        """Process and add members to the group"""
        success = True
        added_members = []
        
        # Process owners
        for owner in self.parse_addresses(owners):
            cmd = [
                GAM_PATH, "update", "group", self.group_email,
                "add", "owner", owner
            ]
            if self.run_blocking_command(cmd):
                added_members.append(f"Owner: {owner}")
                self.log(f"Added owner: {owner}")
            else:
                success = False
                self.log(f"\n[Warning] Failed to add owner: {owner}")

        # Process managers
        for manager in self.parse_addresses(managers):
            cmd = [
                GAM_PATH, "update", "group", self.group_email,
                "add", "manager", manager
            ]
            if self.run_blocking_command(cmd):
                added_members.append(f"Manager: {manager}")
                self.log(f"Added manager: {manager}")
            else:
                success = False
                self.log(f"\n[Warning] Failed to add manager: {manager}")

        # Process members
        for member in self.parse_addresses(members):
            cmd = [
                GAM_PATH, "update", "group", self.group_email,
                "add", "member", member
            ]
            if self.run_blocking_command(cmd):
                added_members.append(f"Member: {member}")
                self.log(f"Added member: {member}")
            else:
                success = False
                self.log(f"\n[Warning] Failed to add member: {member}")

        if success:
            self.log("\nAll members added successfully:")
            for member in added_members:
                self.log(member)
        else:
            self.log("\n[Warning] Some member additions failed. Check the log for details.")

        # Add a small delay before configuring permissions
        QThread.sleep(2)
        self.configure_permissions()

    def configure_permissions(self):
        """Configure group permissions based on matrix settings"""
        # Step 1: Basic group settings
        basic_settings = [
            "archiveonly", "false",
            "allowwebposting", "true",
            "memberscanpostasthegroup", "false",
            "sendmessagedenynotification", "false",
            "defaultsender", "DEFAULT_SELF",
            "showingroupdirectory", "true",
            "spammoderationlevel", "MODERATE",
            "messagemoderationlevel", "MODERATE_NONE"
        ]
        
        # Permission mapping from matrix positions to GAM settings
        permission_map = {
            0: {  # Who can contact group owners
                "setting": "whocancontactowner",
                "values": [
                    "ALL_OWNERS_CAN_CONTACT",     # Group Owners
                    "ALL_MANAGERS_CAN_CONTACT",   # Group Managers
                    "ALL_MEMBERS_CAN_CONTACT",    # Group Members
                    "ALL_IN_DOMAIN_CAN_CONTACT",  # Entire organisation
                    "ANYONE_CAN_CONTACT"          # External
                ]
            },
            1: {  # Who can view conversations
                "setting": "whocanviewgroup",
                "values": [
                    "ALL_OWNERS_CAN_VIEW",     # Group Owners
                    "ALL_MANAGERS_CAN_VIEW",   # Group Managers
                    "ALL_MEMBERS_CAN_VIEW",    # Group Members
                    "ALL_IN_DOMAIN_CAN_VIEW",  # Entire organisation
                    "ANYONE_CAN_VIEW"          # External
                ]
            },
            2: {  # Who can post
                "setting": "whocanpostmessage",
                "values": [
                    "ALL_OWNERS_CAN_POST",     # Group Owners
                    "ALL_MANAGERS_CAN_POST",   # Group Managers
                    "ALL_MEMBERS_CAN_POST",    # Group Members
                    "ALL_IN_DOMAIN_CAN_POST",  # Entire organisation
                    "ANYONE_CAN_POST"          # External
                ]
            },
            3: {  # Who can view members
                "setting": "whocanviewmembership",
                "values": [
                    "ALL_OWNERS_CAN_VIEW",     # Group Owners
                    "ALL_MANAGERS_CAN_VIEW",   # Group Managers
                    "ALL_MEMBERS_CAN_VIEW",    # Group Members
                    "ALL_IN_DOMAIN_CAN_VIEW",  # Entire organisation
                    "ANYONE_CAN_VIEW"          # External (not used)
                ]
            },
            4: {  # Who can manage members
                "setting": "whocanmodifymembers",
                "values": [
                    "OWNERS_ONLY",          # Group Owners
                    "OWNERS_AND_MANAGERS",  # Group Managers
                    "ALL_MEMBERS",          # Group Members
                    "NONE",                # Entire organisation (not used)
                    "NONE"                 # External (not used)
                ]
            }
        }
        
        # Process permission matrix
        permission_settings = []
        for row in range(5):
            highest_allowed = 0  # Start with owners only
            for col in range(5):
                # Skip invalid combinations
                if (col == 3 and row == 4) or (col == 4 and row >= 3):
                    continue
                    
                # Only check boxes that exist
                if (row, col) in self.permission_matrix.checkboxes:
                    if self.permission_matrix.checkboxes[(row, col)].isChecked():
                        highest_allowed = col
            
            # Set appropriate permission level
            perm = permission_map[row]
            permission_settings.extend([perm["setting"], perm["values"][highest_allowed]])

        # Process join settings
        if self.join_settings.radio_anyone.isChecked():
            permission_settings.extend(["whocanjoin", "ALL_IN_DOMAIN_CAN_JOIN"])
        elif self.join_settings.radio_approval.isChecked():
            permission_settings.extend(["whocanjoin", "CAN_REQUEST_TO_JOIN"])
        else:  # Invited only
            permission_settings.extend(["whocanjoin", "INVITED_CAN_JOIN"])

        # Step 1: Apply basic settings and permissions
        cmd1 = [
            GAM_PATH, "update", "group", self.group_email
        ] + basic_settings + permission_settings
        
        self.log("\nApplying basic group settings...")
        self.log(f"\nCommand: {' '.join(cmd1)}")
        self.run_blocking_command(cmd1)

        # Step 2: Handle external members setting separately
        external_setting = "true" if self.join_settings.value() else "false"
        cmd2 = [
            GAM_PATH, "update", "group", self.group_email,
            "allowexternalmembers", external_setting
        ]
        self.log("\nApplying external members setting...")
        self.log(f"\nCommand: {' '.join(cmd2)}")
        self.run_blocking_command(cmd2)

        # Step 3: Reply settings
        cmd3 = [
            GAM_PATH, "update", "group", self.group_email,
            "replyto", "REPLY_TO_IGNORE"
        ]
        self.log("\nApplying reply settings...")
        self.log(f"\nCommand: {' '.join(cmd3)}")
        self.run_blocking_command(cmd3)

        self.log("\nGroup setup completed successfully!")
        self.log("\nGroup URL: https://groups.google.com/a/ustwo.com/g/" + self.group_email.split("@")[0])

    def verify_settings(self, attempts=0):
        """Verify group settings after configuration"""
        cmd = [GAM_PATH, "info", "group", self.group_email]
        
        def verify_done(rc, lines):
            if rc != 0:
                if attempts < 3:
                    self.log("\nSettings not found yet. Waiting 30 seconds...")
                    QThread.sleep(30)
                    self.verify_settings(attempts + 1)
                else:
                    self.log("\n[Warning] Settings verification timed out.")
                return
            
            # Parse and verify settings
            settings_verified = True
            for line in lines:
                if "allowExternalMembers:" in line:
                    expected = "true" if self.join_settings.value() else "false"
                    if expected not in line.lower():
                        self.log(f"\n[Warning] External members setting mismatch: {line.strip()}")
                        settings_verified = False
                elif "whoCanJoin:" in line:
                    expected = "CAN_REQUEST_TO_JOIN" if self.join_settings.radio_approval.isChecked() else \
                             "ALL_IN_DOMAIN_CAN_JOIN" if self.join_settings.radio_anyone.isChecked() else \
                             "INVITED_CAN_JOIN"
                    if expected not in line:
                        self.log(f"\n[Warning] Join setting mismatch: {line.strip()}")
                        settings_verified = False
            
            if settings_verified:
                self.log("\nAll settings verified successfully!")
            else:
                self.log("\n[Warning] Some settings may not have been applied correctly.")
            
            self.log("\nGroup URL: https://groups.google.com/a/ustwo.com/g/" + self.group_email.split("@")[0])

        self.run_threaded_command(cmd, verify_done)

    def parse_addresses(self, text):
        """Parse addresses from text input"""
        if not text.strip():
            return []
        replaced = text.replace(",", " ")
        return [x.strip() for x in replaced.split() if x.strip()]

    def run_blocking_command(self, cmd_list):
        """Run a GAM command and wait for completion"""
        try:
            proc = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            out, err = proc.communicate()
            success = True
            
            if out:
                for line in out.splitlines():
                    self.log(line)
                    if "Failed" in line or "Error" in line:
                        success = False
            if err:
                for e_line in err.splitlines():
                    self.log(f"\n{e_line}")
                    success = False
                    
            return success and proc.returncode == 0
            
        except Exception as e:
            self.log(f"\n[Exception] {str(e)}")
            return False

    def run_threaded_command(self, cmd_list, callback):
        """Run a GAM command in a separate thread"""
        worker = WorkerThread(cmd_list)
        self.workers.append(worker)

        worker.line_signal.connect(self.log)
        worker.done_signal.connect(callback)
        worker.start()

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


def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("/Library/JAMF/Icon/brandingimage.icns"))
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 