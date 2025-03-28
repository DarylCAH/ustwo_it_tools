#!/usr/bin/env python3
"""
A Python + PyQt5 script for creating Google Shared Drives, with an optional
2-folder template copy, bulk membership adds, optional external/GDPR drives,
and custom dialogs for all user interaction.

This module can be run standalone or imported into the unified tools application.
"""

import sys
import os
import re
import subprocess
import json
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QCheckBox, QDialog, QDialogButtonBox,
    QPlainTextEdit, QComboBox, QGroupBox, QScrollArea, QMessageBox
)
from . import config

# Path to GAM binary
GAM_PATH = os.path.expanduser("~/bin/gam7/gam")

# Config file for persistent settings
CONFIG_FILE = os.path.expanduser("~/.shared_drive_tool.json")

# Web roles vs. gam roles
WEB_TO_GAM = {
    "Organizer": "organizer",
    "Content": "fileOrganizer",  # "Content Manager" gets split to "Content"
    "Contributor": "writer",
    "Commenter": "commenter",
    "Viewer": "reader"
}
WEB_ROLE_LIST = list(WEB_TO_GAM.keys())

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
# CUSTOM DIALOGS
##############################################################################

class CustomYesNoDialog(QDialog):
    """
    A custom "Yes/No" dialog with a branded icon and text.
    We return True if user clicked "Yes," False if user clicked "No."
    """
    def __init__(self, title, question, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        # Set the same icon
        self.setWindowIcon(QIcon("/Library/JAMF/Icon/brandingimage.icns"))
        self.setModal(True)

        main_layout = QVBoxLayout(self)

        label = QLabel(question)
        label.setWordWrap(True)
        main_layout.addWidget(label)

        button_box = QDialogButtonBox(QDialogButtonBox.Yes | QDialogButtonBox.No)
        button_box.button(QDialogButtonBox.Yes).setText("Yes")
        button_box.button(QDialogButtonBox.No).setText("No")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        main_layout.addWidget(button_box)
        self.setLayout(main_layout)

    @staticmethod
    def ask(title, question, parent=None):
        dlg = CustomYesNoDialog(title, question, parent)
        result = dlg.exec_()
        return (result == QDialog.Accepted)

class SelectRoleDialog(QDialog):
    """Dialog to select a role from the standard Google Drive roles"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Member Role")
        self.setWindowIcon(QIcon("/Library/JAMF/Icon/brandingimage.icns"))
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        info_label = QLabel("Select a role for the new members:")
        layout.addWidget(info_label)
        
        # Use proper role names that match GAM expectations
        self.role_combo = QComboBox()
        self.role_combo.addItems([
            "Organizer (Full control)", 
            "Content Manager (Edit and organize)",
            "Contributor (Edit only)",
            "Commenter (Comment only)",
            "Viewer (View only)"
        ])
        layout.addWidget(self.role_combo)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Add a "No More Members" button
        self.no_more_btn = QPushButton("No More Members")
        self.no_more_btn.clicked.connect(self.no_more_clicked)
        layout.addWidget(self.no_more_btn)
        
        self.selected_role = None
        
    def no_more_clicked(self):
        """User has selected that they don't want to add more members"""
        self.selected_role = None
        self.accept()
        
    def accept(self):
        """Override accept to store the selected role"""
        selected_text = self.role_combo.currentText()
        # Extract just the first word as the role
        self.selected_role = selected_text.split(" ")[0]
        super().accept()
        
    @staticmethod
    def get_role(parent=None):
        """Static method to show dialog and return selected role"""
        dialog = SelectRoleDialog(parent)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            return dialog.selected_role
        return None

class MultiLineAddressesDialog(QDialog):
    """Dialog to enter multiple email addresses"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enter Email Addresses")
        self.setWindowIcon(QIcon("/Library/JAMF/Icon/brandingimage.icns"))
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        info_label = QLabel("Enter email addresses (one per line or comma-separated):")
        layout.addWidget(info_label)
        
        self.text_edit = QPlainTextEdit()
        layout.addWidget(self.text_edit)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.resize(400, 300)
        
    def accept(self):
        """Override accept to validate input"""
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Warning", "Please enter at least one email address.")
            return
        super().accept()
        
    @staticmethod
    def get_addresses(parent=None):
        """Static method to show dialog and return entered text"""
        dialog = MultiLineAddressesDialog(parent)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            return dialog.text_edit.toPlainText()
        return ""

##############################################################################
# MAIN WINDOW
##############################################################################

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Google Shared Drive Creation Tool")
        self.settings = config.load_config(config.DRIVE_CONFIG)
        self.init_ui()

    def init_ui(self):
        self.workers = []
        self.drive_ids = {}
        self.main_members = []
        self.processed_count = 0
        self.total_addresses = 0
        self.processed_pairs = 0
        self.total_pairs = 0
        central = QWidget()
        self.setCentralWidget(central)
        self.main_layout = QVBoxLayout(central)

        # Top area: logo left, fields right
        top_hbox = QHBoxLayout()
        self.main_layout.addLayout(top_hbox)

        self.logo_label = QLabel()
        pixmap = QPixmap("/Library/JAMF/Icon/brandingimage.icns")
        scaled = pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.logo_label.setPixmap(scaled)
        top_hbox.addWidget(self.logo_label)

        right_vbox = QVBoxLayout()
        top_hbox.addLayout(right_vbox)

        # Email with reset button
        email_hbox = QHBoxLayout()
        lbl_email = QLabel("Your Email Address:")
        self.input_email = QLineEdit()
        email_hbox.addWidget(lbl_email)
        email_hbox.addWidget(self.input_email)
        right_vbox.addLayout(email_hbox)

        lbl_drive = QLabel("New Shared Drive Name:")
        self.input_drive = QLineEdit()

        self.copy_checkbox = QCheckBox("Copy Client Folder Structure Template files?")
        self.copy_checkbox.setChecked(True)

        right_vbox.addWidget(lbl_drive)
        right_vbox.addWidget(self.input_drive)
        right_vbox.addWidget(self.copy_checkbox)

        # Log area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.main_layout.addWidget(self.log_area)

        # Buttons
        btn_hbox = QHBoxLayout()
        self.main_layout.addLayout(btn_hbox)

        self.btn_start = QPushButton("Start Workflow")
        self.btn_start.clicked.connect(self.handle_workflow)
        btn_hbox.addWidget(self.btn_start)

        self.btn_quit = QPushButton("Quit")
        self.btn_quit.clicked.connect(self.close)
        btn_hbox.addWidget(self.btn_quit)

        self.resize(900, 600)
        
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
    
    def reset_email(self):
        """Reset stored email"""
        self.input_email.clear()
        self.save_config()
        self.log("\n[Info] Email address reset. Please enter a new email address.")

    def log(self, text):
        self.log_area.append(text)

    def handle_workflow(self):
        """Handle the workflow start button click"""
        # Get user inputs
        self.user_email = self.input_email.text().strip()
        self.base_drive_name = self.input_drive.text().strip()
        self.do_copy = "Yes" if self.copy_checkbox.isChecked() else "No"
        
        # Clean up previous states
        self.log_area.clear()
        self.drive_ids = {}
        self.main_members = []
        self.processed_count = 0
        self.total_addresses = 0
        self.processed_pairs = 0
        self.total_pairs = 0
        
        # Validate inputs
        if not self.user_email:
            self.show_warning("Missing Information", "Please enter your email address.")
            return
            
        if not self.base_drive_name:
            self.show_warning("Missing Information", "Please enter a name for the new shared drive.")
            return
            
        # Save the settings
        self.settings["email"] = self.user_email
        self.save_config()
        
        # Start the workflow
        self.log(f"\nStarting workflow for base drive '{self.base_drive_name}' with user {self.user_email}")
        
        # Create the main shared drive
        self.create_shared_drive("main", "", self.do_copy, next_step=self.after_main_created)

    def create_shared_drive(self, drive_type, modifier, do_copy, next_step=None):
        """Create a Google Shared Drive based on the provided parameters"""
        self.btn_start.setEnabled(False)
        
        # Determine the drive name - ensure valid drive names
        if drive_type == "main":
            drive_name = self.base_drive_name
        else:
            drive_name = f"{self.base_drive_name}{modifier}"
            
        self.log(f"\n[Info] Creating {drive_type} drive: {drive_name}...")
        
        # Sleep before drive creation to avoid rate limits
        self.log("\nPreparing to create drive...")
        
        # Build command as a list for proper argument handling
        cmd_list = [
            GAM_PATH, 
            "user", self.user_email,
            "create", "teamdrive", drive_name, 
            "adminmanagedrestrictions", "true", 
            "asadmin"
        ]
        
        # Run command with output handling
        def creation_done(rc, lines):
            if rc != 0:
                self.log(f"\n[Error] Failed to create the {drive_type} drive.")
                if next_step:
                    self.set_next_step(next_step)
                return
                
            # Parse drive ID from output
            new_id = self.parse_drive_id(lines)
            if not new_id:
                self.log(f"\n[Error] Could not identify drive ID for {drive_type} drive.")
                if next_step:
                    self.set_next_step(next_step)
                return
                
            # Store drive ID and report success
            self.drive_ids[drive_type] = new_id
            self.log(f"\nDrive '{drive_type}' created successfully. ID={new_id}")
            
            # Add sleep message
            self.log("\nWaiting for Shared Drive creation to complete. Sleeping 10 seconds")
            
            # For main drive, copy template if requested
            if drive_type == "main" and do_copy == "Yes":
                self.log("\nCopying folder structure template to the main drive...")
                INTERNAL_FOLDER_ID = "1rfE8iB-kt96m5JSJwX-X87OxTI5J7hIi"
                self.copy_folder_contents(new_id, INTERNAL_FOLDER_ID)
            
            # Store next step for later execution
            if next_step:
                self.set_next_step(next_step)
        
        # Execute command
        worker = WorkerThread(" ".join([str(x) for x in cmd_list[1:]]))  # Skip GAM_PATH
        worker.output.connect(self.log_output)
        worker.done_signal.connect(creation_done)
        worker.finished.connect(lambda: self.cleanup_thread(worker))
        worker.start()
        self.workers.append(worker)

    def bulk_add_members(self, drive_id, store_in_main, label, next_step):
        """
        Repeatedly ask for a web role + multiline addresses.
        Convert to gam role, run 'gam add drivefileacl'.
        If store_in_main, store for re-adding to external/GDPR.
        """
        self.log(f"\nAdding members to the {label} drive...")
        
        def add_members_workflow():
            # Show dialog to select role
            web_role = SelectRoleDialog.get_role(parent=self)
            if not web_role:
                self.log(f"\nNo more members to add to the {label} drive.")
                if next_step:
                    self.set_next_step(next_step)
                return

            # Get email addresses
            raw_text = MultiLineAddressesDialog.get_addresses(parent=self)
            if not raw_text.strip():
                self.log(f"\nNo addresses provided for the {label} drive. Skipping.")
                question = f"Add more Members to the {label} drive?"
                more = CustomYesNoDialog.ask(f"Add More Members to the {label} drive?", question, parent=self)
                if not more:
                    if next_step:
                        self.set_next_step(next_step)
                else:
                    add_members_workflow()
                return

            # Process addresses
            replaced = raw_text.replace(",", " ")
            addresses = [x.strip() for x in replaced.split() if x.strip()]

            # Store members if this is the main drive
            if store_in_main:
                self.main_members.append((web_role, addresses))

            # Reset counters
            self.processed_count = 0
            self.total_addresses = len(addresses)
            
            # Add each member using GAM
            gam_role = WEB_TO_GAM[web_role]
            for addr in addresses:
                self.log(f"\nAdding {addr} as {web_role} to the {label} drive...")
                
                # Create command list
                cmd_list = [
                    "add", "drivefileacl", drive_id,
                    "user", addr, "role", gam_role
                ]
                
                def after_add(rc, lines, addr_inner=addr):
                    self.processed_count += 1
                    if rc != 0:
                        self.log(f"\n[Warning] Failed to add {addr_inner} to the drive.")
                    else:
                        self.log(f"\nSuccessfully added {addr_inner} to the drive.")
                    
                    # Check if we've processed all addresses
                    if self.processed_count >= self.total_addresses:
                        # Ask if we want to add more members
                        question = f"Add more members to the {label} drive?"
                        more_roles = CustomYesNoDialog.ask(f"Add More Members to the {label} drive?", question, parent=self)
                        if not more_roles:
                            if next_step:
                                self.set_next_step(next_step)
                        else:
                            QTimer.singleShot(100, add_members_workflow)
                
                # Run command
                worker = WorkerThread(cmd_list)
                worker.output.connect(self.log_output)
                worker.done_signal.connect(after_add)
                worker.finished.connect(lambda: self.cleanup_thread(worker))
                worker.start()
                self.workers.append(worker)
        
        # Start the workflow
        add_members_workflow()

    def re_add_members(self, label, drive_id, next_step):
        """Re-add members from the main drive to another drive"""
        if not self.main_members:
            self.log(f"\n[Warning] No stored main membership found for the {label} drive.")
            if next_step:
                self.set_next_step(next_step)
            return

        self.log(f"\nRe-adding members from main drive to {label} drive...")
        
        # Reset tracking counters
        self.processed_pairs = 0
        self.total_pairs = sum(len(addresses) for _, addresses in self.main_members)
        
        # Add each member from the main drive
        for (web_role, addresses) in self.main_members:
            gam_role = WEB_TO_GAM[web_role]
            for addr in addresses:
                self.log(f"\nRe-adding {addr} as {web_role} to the {label} drive...")
                
                # Build command
                cmd_list = [
                    "add", "drivefileacl", drive_id,
                    "user", addr, "role", gam_role
                ]
                
                def after_add(rc, lines, addr_inner=addr):
                    self.processed_pairs += 1
                    if rc != 0:
                        self.log(f"\n[Warning] Failed to add {addr_inner} to the drive.")
                    else:
                        self.log(f"\nSuccessfully added {addr_inner} to the drive.")
                    
                    # Check if we've processed all members
                    if self.processed_pairs >= self.total_pairs:
                        # Ask if we want to add additional members
                        question = f"Add additional new members for the {label} drive?"
                        more = CustomYesNoDialog.ask("Additional members?", question, parent=self)
                        if more:
                            # Add new members specifically for this drive
                            self.bulk_add_members(drive_id=drive_id, store_in_main=False, label=label, next_step=next_step)
                        else:
                            if next_step:
                                self.set_next_step(next_step)
                
                # Run command
                worker = WorkerThread(cmd_list)
                worker.output.connect(self.log_output)
                worker.done_signal.connect(after_add)
                worker.finished.connect(lambda: self.cleanup_thread(worker))
                worker.start()
                self.workers.append(worker)

    def after_main_created(self):
        """Callback after main drive is created successfully"""
        main_id = self.drive_ids.get("main")
        if not main_id:
            self.log("\n[Error] No main drive ID found, skipping membership.")
            if self.do_copy == "Yes":
                self.ask_external_drive()
            else:
                self.end_workflow()
            return

        self.log("\nNow add members to the main drive.")
        self.bulk_add_members(drive_id=main_id, store_in_main=True, label="main", next_step=self.decide_post_main)
        
    def decide_post_main(self):
        """Decide next steps after main drive creation"""
        if self.do_copy == "Yes":
            self.ask_external_drive()
        else:
            self.end_workflow()
            
    def ask_external_drive(self):
        """Ask if an external drive should be created"""
        yes = CustomYesNoDialog.ask(
            "External Drive?",
            "Create an external drive?",
            parent=self
        )
        if yes:
            same = CustomYesNoDialog.ask(
                "Use same membership?",
                "Use the same members & roles as the main drive?\n"
                "\nYes = Add the exact same users and roles (additional members can be added after)\n"
                "\nNo = Add a different set of users.",
                parent=self
            )
            self.create_shared_drive("external", " (External)", "",
                                     next_step=lambda: self.after_ext_created(same))
        else:
            self.log("\nNot creating external drive.")
            self.ask_gdpr_drive()
            
    def after_ext_created(self, use_same):
        """Handle completion of external drive creation"""
        ext_id = self.drive_ids.get("external")
        if not ext_id:
            self.log("\n[Error] No external drive ID found.")
            self.ask_gdpr_drive()
            return

        self.log("\nExternal drive created successfully.")
        
        # Add members to the external drive
        if use_same:
            self.log("\nAdding the same members from the main drive to the external drive...")
            self.re_add_members(label="external", drive_id=ext_id, next_step=self.ask_gdpr_drive)
        else:
            self.log("\nPlease add members to the external drive...")
            self.bulk_add_members(drive_id=ext_id, store_in_main=False, label="external", next_step=self.ask_gdpr_drive)
            
    def ask_gdpr_drive(self):
        """Ask if a GDPR drive should be created"""
        yes = CustomYesNoDialog.ask(
            "GDPR Drive?",
            "Create a GDPR drive?",
            parent=self
        )
        if yes:
            same = CustomYesNoDialog.ask(
                "Use same membership?",
                "Use the same members & roles as the main drive?\n"
                "\nYes = Add the exact same users and roles (additional members can be added after)\n"
                "\nNo = Add a different set of users.",
                parent=self
            )
            self.create_shared_drive("gdpr", " (GDPR)", "",
                                     next_step=lambda: self.after_gdpr_created(same))
        else:
            self.log("\nNot creating GDPR drive.")
            self.end_workflow()
            
    def after_gdpr_created(self, use_same):
        """Handle completion of GDPR drive creation"""
        gdpr_id = self.drive_ids.get("gdpr")
        if not gdpr_id:
            self.log("\n[Error] No GDPR drive ID found.")
            self.end_workflow()
            return

        self.log("\nGDPR drive created successfully.")
        
        # Add members to the GDPR drive
        if use_same:
            self.log("\nAdding the same members from the main drive to the GDPR drive...")
            self.re_add_members(label="gdpr", drive_id=gdpr_id, next_step=self.end_workflow)
        else:
            self.log("\nPlease add members to the GDPR drive...")
            self.bulk_add_members(drive_id=gdpr_id, store_in_main=False, label="gdpr", next_step=self.end_workflow)
        
    def end_workflow(self):
        """End the workflow and display drive URLs"""
        self.display_drive_urls()
        
    def display_drive_urls(self):
        """Display URLs for all created drives"""
        if not self.drive_ids:
            self.log("\nNo drives were created in this session.")
            return
            
        self.log("\n" + "="*50)
        self.log("\nSUMMARY OF CREATED DRIVES:")
        
        for label, drive_id in self.drive_ids.items():
            drive_name = f"{self.base_drive_name}{' (External)' if label == 'external' else ' (GDPR)' if label == 'gdpr' else ''}"
            drive_url = f"https://drive.google.com/drive/folders/{drive_id}"
            self.log(f"\n{drive_name}:")
            self.log(f"{drive_url}")
        
        self.log("\n" + "="*50)
        self.log("\nAll requested operations completed.")

    def show_warning(self, title, message):
        """Show a single-button OK dialog with branding icon."""
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
        for w in self.workers:
            if w.isRunning():
                self.log("\n[Info] Waiting for a background thread to finish...")
                w.wait(2000)
                if w.isRunning():
                    self.log("\n[Warning] Forcibly terminating leftover thread.")
                    w.terminate()
        super().closeEvent(event)

    def save_settings(self):
        """Save current settings to config file"""
        config.save_config(config.DRIVE_CONFIG, self.settings)

    def run_gam_command(self, command, callback=None):
        """Run a GAM command using the configured GAM path"""
        # Log the command for debugging
        self.log(f"\nCommand: {GAM_PATH} {command}\n")
        
        # Create worker thread
        worker = WorkerThread(command)
        
        # Connect signals
        worker.output.connect(self.log_output)
        worker.finished.connect(lambda: self.cleanup_thread(worker))
        
        # Connect callback if provided
        if callback:
            worker.done_signal.connect(callback)
            
        # Start worker and track it
        worker.start()
        self.workers.append(worker)
        
    def get_current_drive_type(self, command):
        """Extract drive type from the command context"""
        if 'External' in command:
            return 'external'
        elif 'GDPR' in command:
            return 'gdpr'
        else:
            return 'main'
        
    def handle_drive_creation(self, rc, lines, drive_type):
        """Handle the completion of a drive creation command"""
        if rc != 0:
            self.log(f"\n[Error] 'create teamdrive' command for the {drive_type} drive failed.")
            return
            
        new_id = self.parse_drive_id(lines)
        if not new_id:
            self.log(f"\n[Error] Could not parse the {drive_type} drive ID.")
            return
            
        self.drive_ids[drive_type] = new_id
        self.log(f"\nDrive '{drive_type}' created successfully. ID={new_id}")
        
        # For main drive with copy template option
        if drive_type == "main" and hasattr(self, 'do_copy') and self.do_copy == "Yes":
            self.log("\nCopying folder structure template to the main drive...")
            # Add template folder ID to config
            INTERNAL_FOLDER_ID = "1rfE8iB-kt96m5JSJwX-X87OxTI5J7hIi"
            self.copy_folder_contents(new_id, INTERNAL_FOLDER_ID)
            
    def copy_folder_contents(self, drive_id, template_folder_id):
        """
        Copy contents from template folder to the drive using
        the approach from the original script.
        """
        self.log("\nCopying template folder to drive...")
        
        # Step 1: Copy the template folder to the new drive
        cmd = f"user {self.user_email} copy drivefile {template_folder_id} excludetrashed recursive " \
              f"copytopfolderpermissions false copyfilepermissions false " \
              f"copysubfolderpermissions false teamdriveparentid {drive_id}"
        
        worker = WorkerThread(cmd)
        worker.output.connect(self.log_output)
        
        def after_folder_copy(rc, lines):
            if rc != 0:
                self.log("\n[Error] Failed to copy the template folder.")
                return
                
            # Extract the ID of the copied folder
            copied_folder_id = None
            for line in lines:
                match = re.search(r"id: (\S+)", line)
                if match:
                    copied_folder_id = match.group(1)
                    break
                    
            if not copied_folder_id:
                self.log("\n[Error] Could not identify copied folder ID.")
                return
                
            self.log(f"\nTemplate folder copied with ID: {copied_folder_id}")
            self.list_copied_contents(copied_folder_id, drive_id)
        
        worker.done_signal.connect(after_folder_copy)
        worker.finished.connect(lambda: self.cleanup_thread(worker))
        worker.start()
        self.workers.append(worker)
        
    def list_copied_contents(self, folder_id, drive_id):
        """List contents of the copied folder"""
        cmd = f"user {self.user_email} show filelist query \"'{folder_id}' in parents\" fields id,name"
        
        worker = WorkerThread(cmd)
        worker.output.connect(self.log_output)
        
        def process_contents(rc, lines):
            if rc != 0:
                self.log("\n[Error] Failed to list contents of copied folder.")
                return
                
            # Parse contents
            items = []
            for line in lines:
                id_match = re.search(r"id: (\S+)", line)
                name_match = re.search(r"name: (.+)$", line)
                if id_match and name_match:
                    item_id = id_match.group(1)
                    name = name_match.group(1).strip()
                    items.append((item_id, name))
                    
            if not items:
                self.log("\n[Warning] Copied folder appears to be empty.")
                # Delete the empty folder
                self.delete_template_folder(folder_id, drive_id)
                return
                
            self.log(f"\nFound {len(items)} items in the copied folder.")
            # Move each item to the drive root
            self.move_items_to_root(items, folder_id, drive_id)
            
        worker.done_signal.connect(process_contents)
        worker.finished.connect(lambda: self.cleanup_thread(worker))
        worker.start()
        self.workers.append(worker)
        
    def move_items_to_root(self, items, folder_id, drive_id):
        """Move items from the copied folder to the drive root"""
        self.move_count = 0
        self.total_items = len(items)
        
        for item_id, name in items:
            self.log(f"\nMoving '{name}' to drive root...")
            cmd = f"user {self.user_email} update drivefile {item_id} teamdriveparent {drive_id} removeparent {folder_id}"
            
            worker = WorkerThread(cmd)
            worker.output.connect(self.log_output)
            
            def after_move(rc, lines, item_name=name):
                self.move_count += 1
                
                if rc != 0:
                    self.log(f"\n[Warning] Failed to move '{item_name}' to root.")
                else:
                    self.log(f"\nSuccessfully moved '{item_name}' to root.")
                    
                # Once all items are moved, delete the template folder
                if self.move_count >= self.total_items:
                    self.delete_template_folder(folder_id, drive_id)
                    
            worker.done_signal.connect(after_move)
            worker.finished.connect(lambda: self.cleanup_thread(worker))
            worker.start()
            self.workers.append(worker)
            
    def delete_template_folder(self, folder_id, drive_id):
        """Delete the template folder after moving its contents"""
        self.log("\nDeleting the copied template folder (contents already moved to root)...")
        
        cmd = f"user {self.user_email} delete drivefile {folder_id}"
        
        worker = WorkerThread(cmd)
        worker.output.connect(self.log_output)
        
        def after_delete(rc, lines):
            if rc != 0:
                self.log("\n[Warning] Could not delete the template folder.")
            else:
                self.log("\nTemplate folder deleted.")
                
            self.log("\nFolder structure successfully copied to drive root.")
            
        worker.done_signal.connect(after_delete)
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
        """Process command completion and handle next steps"""
        if not self.workers:
            # Only enable the button if we're at the end of a workflow
            if not hasattr(self, 'next_step') or self.next_step is None:
                self.btn_start.setEnabled(True)
                
            # Call next_step if available - important to do this before returning
            QTimer.singleShot(500, self.execute_next_step)

    def parse_drive_id(self, lines):
        """Parse the drive ID from command output"""
        for line in lines:
            m = re.search(r"Shared Drive ID:\s*(\S+)", line)
            if m:
                return m.group(1).rstrip(',')
        return ""

    def set_next_step(self, next_step):
        """Set the next step to execute and schedule it if no workers are active"""
        self.next_step = next_step
        
        # If no workers are active, schedule the next step immediately
        if not self.workers:
            QTimer.singleShot(500, self.execute_next_step)
    
    def execute_next_step(self):
        """Execute the stored next step if available"""
        if hasattr(self, 'next_step') and self.next_step:
            next_step = self.next_step
            self.next_step = None  # Clear to prevent multiple executions
            next_step()

def standalone():
    """Run this tool as a standalone application"""
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("/Library/JAMF/Icon/brandingimage.icns"))
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    standalone()

class SharedDriveTab(QWidget):
    def __init__(self):
        super().__init__()
        self.workers = []
        self.drive_ids = {}
        self.main_members = []
        self.processed_count = 0
        self.total_addresses = 0
        self.processed_pairs = 0
        self.total_pairs = 0
        self.settings = config.load_config(config.DRIVE_CONFIG)
        self.init_ui()

    def init_ui(self):
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

        lbl_drive = QLabel("New Shared Drive Name:")
        self.input_drive = QLineEdit()

        self.copy_checkbox = QCheckBox("Copy Client Folder Structure Template files?")
        self.copy_checkbox.setChecked(True)

        right_vbox.addWidget(lbl_drive)
        right_vbox.addWidget(self.input_drive)
        right_vbox.addWidget(self.copy_checkbox)

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

        # Buttons
        btn_hbox = QHBoxLayout()
        left_layout.addLayout(btn_hbox)

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
    
    def reset_email(self):
        """Reset stored email"""
        self.input_email.clear()
        self.save_config()
        self.log("\n[Info] Email address reset. Please enter a new email address.")

    def log(self, text):
        self.log_area.append(text)

    def handle_workflow(self):
        """Handle the workflow start button click"""
        # Get user inputs
        self.user_email = self.input_email.text().strip()
        self.base_drive_name = self.input_drive.text().strip()
        self.do_copy = "Yes" if self.copy_checkbox.isChecked() else "No"
        
        # Clean up previous states
        self.log_area.clear()
        self.drive_ids = {}
        self.main_members = []
        self.processed_count = 0
        self.total_addresses = 0
        self.processed_pairs = 0
        self.total_pairs = 0
        
        # Validate inputs
        if not self.user_email:
            self.show_warning("Missing Information", "Please enter your email address.")
            return
            
        if not self.base_drive_name:
            self.show_warning("Missing Information", "Please enter a name for the new shared drive.")
            return
            
        # Save the settings
        self.settings["email"] = self.user_email
        self.save_config()
        
        # Start the workflow
        self.log(f"\nStarting workflow for base drive '{self.base_drive_name}' with user {self.user_email}")
        
        # Create the main shared drive
        self.create_shared_drive("main", "", self.do_copy, next_step=self.after_main_created)

    def create_shared_drive(self, drive_type, modifier, do_copy, next_step=None):
        """Create a Google Shared Drive based on the provided parameters"""
        self.btn_start.setEnabled(False)
        
        # Determine the drive name - ensure valid drive names
        if drive_type == "main":
            drive_name = self.base_drive_name
        else:
            drive_name = f"{self.base_drive_name}{modifier}"
            
        self.log(f"\n[Info] Creating {drive_type} drive: {drive_name}...")
        
        # Sleep before drive creation to avoid rate limits
        self.log("\nPreparing to create drive...")
        
        # Build command as a list for proper argument handling
        cmd_list = [
            GAM_PATH, 
            "user", self.user_email,
            "create", "teamdrive", drive_name, 
            "adminmanagedrestrictions", "true", 
            "asadmin"
        ]
        
        # Run command with output handling
        def creation_done(rc, lines):
            if rc != 0:
                self.log(f"\n[Error] Failed to create the {drive_type} drive.")
                if next_step:
                    self.set_next_step(next_step)
                return
                
            # Parse drive ID from output
            new_id = self.parse_drive_id(lines)
            if not new_id:
                self.log(f"\n[Error] Could not identify drive ID for {drive_type} drive.")
                if next_step:
                    self.set_next_step(next_step)
                return
                
            # Store drive ID and report success
            self.drive_ids[drive_type] = new_id
            self.log(f"\nDrive '{drive_type}' created successfully. ID={new_id}")
            
            # Add sleep message
            self.log("\nWaiting for Shared Drive creation to complete. Sleeping 10 seconds")
            
            # For main drive, copy template if requested
            if drive_type == "main" and do_copy == "Yes":
                self.log("\nCopying folder structure template to the main drive...")
                INTERNAL_FOLDER_ID = "1rfE8iB-kt96m5JSJwX-X87OxTI5J7hIi"
                self.copy_folder_contents(new_id, INTERNAL_FOLDER_ID)
            
            # Store next step for later execution
            if next_step:
                self.set_next_step(next_step)
        
        # Execute command
        worker = WorkerThread(" ".join([str(x) for x in cmd_list[1:]]))  # Skip GAM_PATH
        worker.output.connect(self.log_output)
        worker.done_signal.connect(creation_done)
        worker.finished.connect(lambda: self.cleanup_thread(worker))
        worker.start()
        self.workers.append(worker)

    def bulk_add_members(self, drive_id, store_in_main, label, next_step):
        """
        Repeatedly ask for a web role + multiline addresses.
        Convert to gam role, run 'gam add drivefileacl'.
        If store_in_main, store for re-adding to external/GDPR.
        """
        self.log(f"\nAdding members to the {label} drive...")
        
        def add_members_workflow():
            # Show dialog to select role
            web_role = SelectRoleDialog.get_role(parent=self)
            if not web_role:
                self.log(f"\nNo more members to add to the {label} drive.")
                if next_step:
                    self.set_next_step(next_step)
                return

            # Get email addresses
            raw_text = MultiLineAddressesDialog.get_addresses(parent=self)
            if not raw_text.strip():
                self.log(f"\nNo addresses provided for the {label} drive. Skipping.")
                question = f"Add more Members to the {label} drive?"
                more = CustomYesNoDialog.ask(f"Add More Members to the {label} drive?", question, parent=self)
                if not more:
                    if next_step:
                        self.set_next_step(next_step)
                else:
                    add_members_workflow()
                return

            # Process addresses
            replaced = raw_text.replace(",", " ")
            addresses = [x.strip() for x in replaced.split() if x.strip()]

            # Store members if this is the main drive
            if store_in_main:
                self.main_members.append((web_role, addresses))

            # Reset counters
            self.processed_count = 0
            self.total_addresses = len(addresses)
            
            # Add each member using GAM
            gam_role = WEB_TO_GAM[web_role]
            for addr in addresses:
                self.log(f"\nAdding {addr} as {web_role} to the {label} drive...")
                
                # Create command list
                cmd_list = [
                    "add", "drivefileacl", drive_id,
                    "user", addr, "role", gam_role
                ]
                
                def after_add(rc, lines, addr_inner=addr):
                    self.processed_count += 1
                    if rc != 0:
                        self.log(f"\n[Warning] Failed to add {addr_inner} to the drive.")
                    else:
                        self.log(f"\nSuccessfully added {addr_inner} to the drive.")
                    
                    # Check if we've processed all addresses
                    if self.processed_count >= self.total_addresses:
                        # Ask if we want to add more members
                        question = f"Add more members to the {label} drive?"
                        more_roles = CustomYesNoDialog.ask(f"Add More Members to the {label} drive?", question, parent=self)
                        if not more_roles:
                            if next_step:
                                self.set_next_step(next_step)
                        else:
                            QTimer.singleShot(100, add_members_workflow)
                
                # Run command
                worker = WorkerThread(cmd_list)
                worker.output.connect(self.log_output)
                worker.done_signal.connect(after_add)
                worker.finished.connect(lambda: self.cleanup_thread(worker))
                worker.start()
                self.workers.append(worker)
        
        # Start the workflow
        add_members_workflow()

    def re_add_members(self, label, drive_id, next_step):
        """Re-add members from the main drive to another drive"""
        if not self.main_members:
            self.log(f"\n[Warning] No stored main membership found for the {label} drive.")
            if next_step:
                self.set_next_step(next_step)
            return

        self.log(f"\nRe-adding members from main drive to {label} drive...")
        
        # Reset tracking counters
        self.processed_pairs = 0
        self.total_pairs = sum(len(addresses) for _, addresses in self.main_members)
        
        # Add each member from the main drive
        for (web_role, addresses) in self.main_members:
            gam_role = WEB_TO_GAM[web_role]
            for addr in addresses:
                self.log(f"\nRe-adding {addr} as {web_role} to the {label} drive...")
                
                # Build command
                cmd_list = [
                    "add", "drivefileacl", drive_id,
                    "user", addr, "role", gam_role
                ]
                
                def after_add(rc, lines, addr_inner=addr):
                    self.processed_pairs += 1
                    if rc != 0:
                        self.log(f"\n[Warning] Failed to add {addr_inner} to the drive.")
                    else:
                        self.log(f"\nSuccessfully added {addr_inner} to the drive.")
                    
                    # Check if we've processed all members
                    if self.processed_pairs >= self.total_pairs:
                        # Ask if we want to add additional members
                        question = f"Add additional new members for the {label} drive?"
                        more = CustomYesNoDialog.ask("Additional members?", question, parent=self)
                        if more:
                            # Add new members specifically for this drive
                            self.bulk_add_members(drive_id=drive_id, store_in_main=False, label=label, next_step=next_step)
                        else:
                            if next_step:
                                self.set_next_step(next_step)
                
                # Run command
                worker = WorkerThread(cmd_list)
                worker.output.connect(self.log_output)
                worker.done_signal.connect(after_add)
                worker.finished.connect(lambda: self.cleanup_thread(worker))
                worker.start()
                self.workers.append(worker)

    def after_main_created(self):
        """Callback after main drive is created successfully"""
        main_id = self.drive_ids.get("main")
        if not main_id:
            self.log("\n[Error] No main drive ID found, skipping membership.")
            if self.do_copy == "Yes":
                self.ask_external_drive()
            else:
                self.end_workflow()
            return

        self.log("\nNow add members to the main drive.")
        self.bulk_add_members(drive_id=main_id, store_in_main=True, label="main", next_step=self.decide_post_main)
        
    def decide_post_main(self):
        """Decide next steps after main drive creation"""
        if self.do_copy == "Yes":
            self.ask_external_drive()
        else:
            self.end_workflow()
            
    def ask_external_drive(self):
        """Ask if an external drive should be created"""
        yes = CustomYesNoDialog.ask(
            "External Drive?",
            "Create an external drive?",
            parent=self
        )
        if yes:
            same = CustomYesNoDialog.ask(
                "Use same membership?",
                "Use the same members & roles as the main drive?\n"
                "\nYes = Add the exact same users and roles (additional members can be added after)\n"
                "\nNo = Add a different set of users.",
                parent=self
            )
            self.create_shared_drive("external", " (External)", "",
                                     next_step=lambda: self.after_ext_created(same))
        else:
            self.log("\nNot creating external drive.")
            self.ask_gdpr_drive()
            
    def after_ext_created(self, use_same):
        """Handle completion of external drive creation"""
        ext_id = self.drive_ids.get("external")
        if not ext_id:
            self.log("\n[Error] No external drive ID found.")
            self.ask_gdpr_drive()
            return

        self.log("\nExternal drive created successfully.")
        
        # Add members to the external drive
        if use_same:
            self.log("\nAdding the same members from the main drive to the external drive...")
            self.re_add_members(label="external", drive_id=ext_id, next_step=self.ask_gdpr_drive)
        else:
            self.log("\nPlease add members to the external drive...")
            self.bulk_add_members(drive_id=ext_id, store_in_main=False, label="external", next_step=self.ask_gdpr_drive)
            
    def ask_gdpr_drive(self):
        """Ask if a GDPR drive should be created"""
        yes = CustomYesNoDialog.ask(
            "GDPR Drive?",
            "Create a GDPR drive?",
            parent=self
        )
        if yes:
            same = CustomYesNoDialog.ask(
                "Use same membership?",
                "Use the same members & roles as the main drive?\n"
                "\nYes = Add the exact same users and roles (additional members can be added after)\n"
                "\nNo = Add a different set of users.",
                parent=self
            )
            self.create_shared_drive("gdpr", " (GDPR)", "",
                                     next_step=lambda: self.after_gdpr_created(same))
        else:
            self.log("\nNot creating GDPR drive.")
            self.end_workflow()
            
    def after_gdpr_created(self, use_same):
        """Handle completion of GDPR drive creation"""
        gdpr_id = self.drive_ids.get("gdpr")
        if not gdpr_id:
            self.log("\n[Error] No GDPR drive ID found.")
            self.end_workflow()
            return

        self.log("\nGDPR drive created successfully.")
        
        # Add members to the GDPR drive
        if use_same:
            self.log("\nAdding the same members from the main drive to the GDPR drive...")
            self.re_add_members(label="gdpr", drive_id=gdpr_id, next_step=self.end_workflow)
        else:
            self.log("\nPlease add members to the GDPR drive...")
            self.bulk_add_members(drive_id=gdpr_id, store_in_main=False, label="gdpr", next_step=self.end_workflow)
        
    def end_workflow(self):
        """End the workflow and display drive URLs"""
        self.display_drive_urls()
        
    def display_drive_urls(self):
        """Display URLs for all created drives"""
        if not self.drive_ids:
            self.log("\nNo drives were created in this session.")
            return
            
        self.log("\n" + "="*50)
        self.log("\nSUMMARY OF CREATED DRIVES:")
        
        for label, drive_id in self.drive_ids.items():
            drive_name = f"{self.base_drive_name}{' (External)' if label == 'external' else ' (GDPR)' if label == 'gdpr' else ''}"
            drive_url = f"https://drive.google.com/drive/folders/{drive_id}"
            self.log(f"\n{drive_name}:")
            self.log(f"{drive_url}")
        
        self.log("\n" + "="*50)
        self.log("\nAll requested operations completed.")

    def show_warning(self, title, message):
        """Show a single-button OK dialog with branding icon."""
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
        for w in self.workers:
            if w.isRunning():
                self.log("\n[Info] Waiting for a background thread to finish...")
                w.wait(2000)
                if w.isRunning():
                    self.log("\n[Warning] Forcibly terminating leftover thread.")
                    w.terminate()
        super().closeEvent(event)

    def save_settings(self):
        """Save current settings to config file"""
        config.save_config(config.DRIVE_CONFIG, self.settings)

    def run_gam_command(self, command, callback=None):
        """Run a GAM command using the configured GAM path"""
        # Log the command for debugging
        self.log(f"\nCommand: {GAM_PATH} {command}\n")
        
        # Create worker thread
        worker = WorkerThread(command)
        
        # Connect signals
        worker.output.connect(self.log_output)
        worker.finished.connect(lambda: self.cleanup_thread(worker))
        
        # Connect callback if provided
        if callback:
            worker.done_signal.connect(callback)
            
        # Start worker and track it
        worker.start()
        self.workers.append(worker)
        
    def get_current_drive_type(self, command):
        """Extract drive type from the command context"""
        if 'External' in command:
            return 'external'
        elif 'GDPR' in command:
            return 'gdpr'
        else:
            return 'main'
        
    def handle_drive_creation(self, rc, lines, drive_type):
        """Handle the completion of a drive creation command"""
        if rc != 0:
            self.log(f"\n[Error] 'create teamdrive' command for the {drive_type} drive failed.")
            return
            
        new_id = self.parse_drive_id(lines)
        if not new_id:
            self.log(f"\n[Error] Could not parse the {drive_type} drive ID.")
            return
            
        self.drive_ids[drive_type] = new_id
        self.log(f"\nDrive '{drive_type}' created successfully. ID={new_id}")
        
        # For main drive with copy template option
        if drive_type == "main" and hasattr(self, 'do_copy') and self.do_copy == "Yes":
            self.log("\nCopying folder structure template to the main drive...")
            # Add template folder ID to config
            INTERNAL_FOLDER_ID = "1rfE8iB-kt96m5JSJwX-X87OxTI5J7hIi"
            self.copy_folder_contents(new_id, INTERNAL_FOLDER_ID)
            
    def copy_folder_contents(self, drive_id, template_folder_id):
        """
        Copy contents from template folder to the drive using
        the approach from the original script.
        """
        self.log("\nCopying template folder to drive...")
        
        # Step 1: Copy the template folder to the new drive
        cmd = f"user {self.user_email} copy drivefile {template_folder_id} excludetrashed recursive " \
              f"copytopfolderpermissions false copyfilepermissions false " \
              f"copysubfolderpermissions false teamdriveparentid {drive_id}"
        
        worker = WorkerThread(cmd)
        worker.output.connect(self.log_output)
        
        def after_folder_copy(rc, lines):
            if rc != 0:
                self.log("\n[Error] Failed to copy the template folder.")
                return
                
            # Extract the ID of the copied folder
            copied_folder_id = None
            for line in lines:
                match = re.search(r"id: (\S+)", line)
                if match:
                    copied_folder_id = match.group(1)
                    break
                    
            if not copied_folder_id:
                self.log("\n[Error] Could not identify copied folder ID.")
                return
                
            self.log(f"\nTemplate folder copied with ID: {copied_folder_id}")
            self.list_copied_contents(copied_folder_id, drive_id)
        
        worker.done_signal.connect(after_folder_copy)
        worker.finished.connect(lambda: self.cleanup_thread(worker))
        worker.start()
        self.workers.append(worker)
        
    def list_copied_contents(self, folder_id, drive_id):
        """List contents of the copied folder"""
        cmd = f"user {self.user_email} show filelist query \"'{folder_id}' in parents\" fields id,name"
        
        worker = WorkerThread(cmd)
        worker.output.connect(self.log_output)
        
        def process_contents(rc, lines):
            if rc != 0:
                self.log("\n[Error] Failed to list contents of copied folder.")
                return
                
            # Parse contents
            items = []
            for line in lines:
                id_match = re.search(r"id: (\S+)", line)
                name_match = re.search(r"name: (.+)$", line)
                if id_match and name_match:
                    item_id = id_match.group(1)
                    name = name_match.group(1).strip()
                    items.append((item_id, name))
                    
            if not items:
                self.log("\n[Warning] Copied folder appears to be empty.")
                # Delete the empty folder
                self.delete_template_folder(folder_id, drive_id)
                return
                
            self.log(f"\nFound {len(items)} items in the copied folder.")
            # Move each item to the drive root
            self.move_items_to_root(items, folder_id, drive_id)
            
        worker.done_signal.connect(process_contents)
        worker.finished.connect(lambda: self.cleanup_thread(worker))
        worker.start()
        self.workers.append(worker)
        
    def move_items_to_root(self, items, folder_id, drive_id):
        """Move items from the copied folder to the drive root"""
        self.move_count = 0
        self.total_items = len(items)
        
        for item_id, name in items:
            self.log(f"\nMoving '{name}' to drive root...")
            cmd = f"user {self.user_email} update drivefile {item_id} teamdriveparent {drive_id} removeparent {folder_id}"
            
            worker = WorkerThread(cmd)
            worker.output.connect(self.log_output)
            
            def after_move(rc, lines, item_name=name):
                self.move_count += 1
                
                if rc != 0:
                    self.log(f"\n[Warning] Failed to move '{item_name}' to root.")
                else:
                    self.log(f"\nSuccessfully moved '{item_name}' to root.")
                    
                # Once all items are moved, delete the template folder
                if self.move_count >= self.total_items:
                    self.delete_template_folder(folder_id, drive_id)
                    
            worker.done_signal.connect(after_move)
            worker.finished.connect(lambda: self.cleanup_thread(worker))
            worker.start()
            self.workers.append(worker)
            
    def delete_template_folder(self, folder_id, drive_id):
        """Delete the template folder after moving its contents"""
        self.log("\nDeleting the copied template folder (contents already moved to root)...")
        
        cmd = f"user {self.user_email} delete drivefile {folder_id}"
        
        worker = WorkerThread(cmd)
        worker.output.connect(self.log_output)
        
        def after_delete(rc, lines):
            if rc != 0:
                self.log("\n[Warning] Could not delete the template folder.")
            else:
                self.log("\nTemplate folder deleted.")
                
            self.log("\nFolder structure successfully copied to drive root.")
            
        worker.done_signal.connect(after_delete)
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
        """Process command completion and handle next steps"""
        if not self.workers:
            # Only enable the button if we're at the end of a workflow
            if not hasattr(self, 'next_step') or self.next_step is None:
                self.btn_start.setEnabled(True)
                
            # Call next_step if available - important to do this before returning
            QTimer.singleShot(500, self.execute_next_step)

    def parse_drive_id(self, lines):
        """Parse the drive ID from command output"""
        for line in lines:
            m = re.search(r"Shared Drive ID:\s*(\S+)", line)
            if m:
                return m.group(1).rstrip(',')
        return ""

    def set_next_step(self, next_step):
        """Set the next step to execute and schedule it if no workers are active"""
        self.next_step = next_step
        
        # If no workers are active, schedule the next step immediately
        if not self.workers:
            QTimer.singleShot(500, self.execute_next_step)
    
    def execute_next_step(self):
        """Execute the stored next step if available"""
        if hasattr(self, 'next_step') and self.next_step:
            next_step = self.next_step
            self.next_step = None  # Clear to prevent multiple executions
            next_step()

def standalone():
    """Run this tool as a standalone application"""
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("/Library/JAMF/Icon/brandingimage.icns"))
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    standalone()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("/Library/JAMF/Icon/brandingimage.icns"))
    w = SharedDriveTab()
    w.show()
    sys.exit(app.exec_()) 