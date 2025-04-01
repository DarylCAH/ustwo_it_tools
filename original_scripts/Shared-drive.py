#!/usr/bin/env python3
"""
A Python + PyQt5 script for creating Google Shared Drives, with an optional
2-folder template copy, bulk membership adds, optional external/GDPR drives,
and custom dialogs for all user interaction (no default QMessageBox).
Thus, all pop-up dialogs share the same custom branding icon on macOS.

Key Points:
1) If "Copy Client Folder Structure Template files?" is unchecked, we only create
   the main drive and add members (no external/GDPR drive prompts).
2) The main window has a logo at the top-left, fields to the right.
3) We show web-based roles (Manager, Content Manager, Contributor, Commenter, Viewer)
   but convert them to gam-based roles for commands.
4) We parse each drive creation's output to get the correct ID.
5) We store WorkerThreads to avoid "QThread: Destroyed while thread is still running."
6) All prompts use custom dialogs: no standard QMessageBox or QInputDialog.
   This ensures consistent branding icons in all pop-ups on macOS.

Adjust GAM_PATH, CLIENT_FOLDER_ID, INTERNAL_FOLDER_ID as needed.
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
    QPlainTextEdit, QComboBox
)

# Path to your 'gam' binary
GAM_PATH = os.path.expanduser("~/bin/gam7/gam")

# Template folder with contents to copy
INTERNAL_FOLDER_ID = "1rfE8iB-kt96m5JSJwX-X87OxTI5J7hIi"

# Config file for persistent settings
CONFIG_FILE = os.path.expanduser("~/.shared_drive_tool.json")

# Web roles vs. gam roles
WEB_TO_GAM = {
    "Manager": "organizer",
    "Content Manager": "contentmanager",
    "Contributor": "writer",
    "Commenter": "commenter",
    "Viewer": "reader"
}
WEB_ROLE_LIST = list(WEB_TO_GAM.keys())


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


class MultiLineAddressesDialog(QDialog):
    """
    A multiline text box for entering addresses.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enter Addresses")
        self.setWindowIcon(QIcon("/Library/JAMF/Icon/brandingimage.icns"))
        self.setModal(True)

        layout = QVBoxLayout(self)
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Paste addresses here, separated by spaces or commas...")
        self.text_edit.setFixedHeight(200)
        layout.addWidget(self.text_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_text(self):
        return self.text_edit.toPlainText()

    @staticmethod
    def get_addresses(parent=None):
        dlg = MultiLineAddressesDialog(parent)
        result = dlg.exec_()
        if result == QDialog.Accepted:
            return dlg.get_text()
        else:
            return ""


class SelectRoleDialog(QDialog):
    """
    A custom dialog to pick a web role from Manager, Content Manager, etc.
    Returns the chosen role or "" if canceled.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Role")
        self.setWindowIcon(QIcon("/Library/JAMF/Icon/brandingimage.icns"))
        self.setModal(True)

        layout = QVBoxLayout(self)
        label = QLabel("Choose a role:")
        layout.addWidget(label)

        self.combo = QComboBox()
        self.combo.addItems(WEB_ROLE_LIST)
        layout.addWidget(self.combo)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def selected_role(self):
        return self.combo.currentText()

    @staticmethod
    def get_role(parent=None):
        dlg = SelectRoleDialog(parent)
        result = dlg.exec_()
        if result == QDialog.Accepted:
            return dlg.selected_role()
        else:
            return ""


##############################################################################
# MAIN WINDOW
##############################################################################

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Google Shared Drive Creation Tool")

        self.workers = []
        self.drive_ids = {}     # { "main": "...", "external": "...", "gdpr": "..." }
        self.main_members = []  # [(web_role, [emails])]

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

    ########################################################################
    # MAIN WORKFLOW
    ########################################################################

    def handle_workflow(self):
        self.log_area.clear()
        self.drive_ids.clear()
        self.main_members.clear()

        self.user_email = self.input_email.text().strip()
        self.base_drive_name = self.input_drive.text().strip()
        if not self.user_email or not self.base_drive_name:
            self.show_warning("Missing Info", "Please provide an email and drive name.")
            return
            
        # Save the email for future use
        self.save_config()

        self.log(f"\nStarting workflow for base drive '{self.base_drive_name}' with user {self.user_email}")
        self.do_copy = "Yes" if self.copy_checkbox.isChecked() else ""

        self.create_shared_drive("main", "", self.do_copy, next_step=self.after_main_created)

    def after_main_created(self):
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
        if self.do_copy == "Yes":
            self.ask_external_drive()
        else:
            self.end_workflow()

    ########################################################################
    # EXTERNAL & GDPR
    ########################################################################

    def ask_external_drive(self):
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
        ext_id = self.drive_ids.get("external")
        if not ext_id:
            self.log("\n[Error] No external drive ID found.")
            self.ask_gdpr_drive()
            return

        if use_same and self.main_members:
            self.log("\nRe-adding main drive members to the external drive...")
            self.re_add_members("external", ext_id, next_step=self.ask_gdpr_drive)
        else:
            self.log("\nNew membership flow for the external drive...")
            self.bulk_add_members(drive_id=ext_id, store_in_main=False, label="external", next_step=self.ask_gdpr_drive)

    def ask_gdpr_drive(self):
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
        gdpr_id = self.drive_ids.get("gdpr")
        if not gdpr_id:
            self.log("\n[Error] No gdpr drive ID found.")
            self.end_workflow()
            return

        if use_same and self.main_members:
            self.log("\nRe-adding main drive members to the gdpr drive...")
            self.re_add_members("gdpr", gdpr_id, next_step=self.end_workflow)
        else:
            self.log("\nNew membership flow for the gdpr drive...")
            self.bulk_add_members(drive_id=gdpr_id, store_in_main=False, label="gdpr", next_step=self.end_workflow)

    def end_workflow(self):
        # Ask if user wants to remove themselves from drives
        self.ask_remove_self()

    def ask_remove_self(self):
        """Ask if the user wants to be removed from all created drives"""
        if not self.drive_ids:
            self.display_drive_urls()
            return
            
        yes = CustomYesNoDialog.ask(
            "Remove Self?",
            f"Would you like to remove your email address ({self.user_email}) as a member from all created drives?",
            parent=self
        )
        if yes:
            self.log(f"\nRemoving {self.user_email} from all created drives...")
            self.remove_self_from_drives(next_step=self.display_drive_urls)
        else:
            self.display_drive_urls()
            
    def remove_self_from_drives(self, next_step):
        """Remove the user from all created drives"""
        drive_count = len(self.drive_ids)
        self.processed_count = 0  # Using instance variable to track count
        
        for label, drive_id in self.drive_ids.items():
            self.log(f"\nRemoving {self.user_email} from {label} drive ({drive_id})...")
            cmd = [
                GAM_PATH, "delete", "drivefileacl", drive_id,
                self.user_email
            ]
            
            def removal_done(rc, lines, current_label=label):
                self.processed_count += 1
                
                if rc != 0:
                    self.log(f"\n[Warning] Could not remove {self.user_email} from {current_label} drive.")
                else:
                    self.log(f"\nSuccessfully removed {self.user_email} from {current_label} drive.")
                
                # If we've processed all drives, move to next step
                if self.processed_count >= drive_count and next_step:
                    next_step()
            
            self.run_threaded_command(cmd, removal_done)
    
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

    ########################################################################
    # CREATE SHARED DRIVE
    ########################################################################

    def create_shared_drive(self, label, suffix, copy_template, next_step):
        drive_name = f"{self.base_drive_name}{suffix}"
        self.log(f"\nCreating {label} drive: {drive_name}...")

        cmd = [
            GAM_PATH, "user", self.user_email,
            "create", "teamdrive", drive_name,
            "adminmanagedrestrictions", "true", "asadmin"
        ]
        def creation_done(rc, lines):
            if rc != 0:
                self.log(f"\n[Error] 'create teamdrive' command for the {label} drive failed.")
                if next_step:
                    next_step()
                return

            new_id = self.parse_drive_id(lines)
            if not new_id:
                self.log(f"\n[Error] Could not parse the {label} drive ID.")
                if next_step:
                    next_step()
                return

            self.drive_ids[label] = new_id
            self.log(f"\nDrive '{label}' created successfully. ID={new_id}")

            if label == "main" and copy_template == "Yes":
                self.log("\nCopying folder structure template to the main drive...")
                self.copy_folder_contents(new_id, next_step)
            else:
                if next_step:
                    next_step()

        self.run_threaded_command(cmd, creation_done)

    def copy_folder_contents(self, drive_id, next_step):
        """
        Copy contents directly from Internal folder to root of the drive using
        a temporary CSV file approach to bypass ownership restrictions:
        
        1. Copy the entire Internal folder to the drive first
        2. Then we'll get all its contents and move them to the root
        3. Finally delete the copied Internal folder
        """
        self.log("\nCopying template folder to drive...")
        
        # Step 1: Copy the Internal folder to the new drive (this bypasses the ownership limitations)
        cmd = [
            GAM_PATH, "user", self.user_email,
            "copy", "drivefile", INTERNAL_FOLDER_ID,
            "excludetrashed", "recursive",
            "copytopfolderpermissions", "false", 
            "copyfilepermissions", "false",
            "copysubfolderpermissions", "false",
            "teamdriveparentid", drive_id
        ]
        
        def after_folder_copy(rc, lines):
            if rc != 0:
                self.log("\n[Error] Failed to copy the template folder.")
                if next_step:
                    next_step()
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
                if next_step:
                    next_step()
                return
                
            self.log(f"\nTemplate folder copied with ID: {copied_folder_id}")
            
            # Step 2: List contents of the copied folder (now we own this copy)
            self.log("\nListing contents of copied folder...")
            self.list_copied_contents(copied_folder_id, drive_id, next_step)
        
        self.run_threaded_command(cmd, after_folder_copy)
    
    def list_copied_contents(self, folder_id, drive_id, next_step):
        """List contents of the copied folder"""
        cmd = [
            GAM_PATH, "user", self.user_email,
            "show", "filelist",
            "query", f"'{folder_id}' in parents",
            "fields", "id,name"
        ]
        
        def process_contents(rc, lines):
            if rc != 0:
                self.log("\n[Error] Failed to list contents of copied folder.")
                if next_step:
                    next_step()
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
                self.delete_template_folder(folder_id, drive_id, next_step)
                return
                
            self.log(f"\nFound {len(items)} items in the copied folder.")
            # Move each item to the drive root
            self.move_items_to_root(items, folder_id, drive_id, next_step)
        
        self.run_threaded_command(cmd, process_contents)
    
    def move_items_to_root(self, items, folder_id, drive_id, next_step):
        """Move items from the copied folder to the drive root"""
        self.move_count = 0
        self.total_items = len(items)
        
        for item_id, name in items:
            self.log(f"\nMoving '{name}' to drive root...")
            cmd = [
                GAM_PATH, "user", self.user_email,
                "update", "drivefile", item_id,
                "teamdriveparent", drive_id,
                "removeparent", folder_id
            ]
            
            def after_move(rc, lines, item_name=name):
                self.move_count += 1
                
                if rc != 0:
                    self.log(f"\n[Warning] Failed to move '{item_name}' to root.")
                else:
                    self.log(f"\nSuccessfully moved '{item_name}' to root.")
                
                # Once all items are moved, delete the template folder
                if self.move_count >= self.total_items:
                    self.delete_template_folder(folder_id, drive_id, next_step)
            
            self.run_threaded_command(cmd, after_move)
    
    def delete_template_folder(self, folder_id, drive_id, next_step):
        """Delete the template folder after moving its contents"""
        self.log("\nDeleting the copied template folder (contents already moved to root)...")
        
        cmd = [
            GAM_PATH, "user", self.user_email,
            "delete", "drivefile", folder_id
        ]
        
        def after_delete(rc, lines):
            if rc != 0:
                self.log("\n[Warning] Could not delete the template folder.")
            else:
                self.log("\nTemplate folder deleted.")
            
            self.log("\nFolder structure successfully copied to drive root.")
            if next_step:
                next_step()
        
        self.run_threaded_command(cmd, after_delete)

    def parse_drive_id(self, lines):
        for line in lines:
            m = re.search(r"Shared Drive ID:\s*(\S+)", line)
            if m:
                return m.group(1).rstrip(',')
        return ""

    ########################################################################
    # MEMBERSHIP
    ########################################################################

    def bulk_add_members(self, drive_id, store_in_main, label, next_step):
        """
        Repeatedly ask for a web role + multiline addresses.
        Convert to gam role, run 'gam add drivefileacl'.
        If store_in_main, store for re-adding to external/GDPR.
        """
        while True:
            web_role = SelectRoleDialog.get_role(parent=self)
            if not web_role:
                self.log(f"\nNo more members to add to the {label} drive.")
                break

            raw_text = MultiLineAddressesDialog.get_addresses(parent=self)
            if not raw_text.strip():
                self.log(f"\nNo addresses provided for the {label} drive. Skipping.")
                question = f"Add more Members to the {label} drive?"
                more = CustomYesNoDialog.ask(f"Add More Members to the {label} drive?", question, parent=self)
                if not more:
                    break
                else:
                    continue

            replaced = raw_text.replace(",", " ")
            addresses = [x.strip() for x in replaced.split() if x.strip()]

            gam_role = WEB_TO_GAM[web_role]
            for addr in addresses:
                self.log(f"\nAdding {addr} as {web_role} to the {label} drive...")
                cmd = [
                    GAM_PATH, "add", "drivefileacl", drive_id,
                    "user", addr, "role", gam_role
                ]
                self.run_blocking_command(cmd)

            if store_in_main:
                self.main_members.append((web_role, addresses))

            question = f"Add more members to the {label} drive?"
            more_roles = CustomYesNoDialog.ask(f"Add More Members to the {label} drive?", question, parent=self)
            if not more_roles:
                break

        if next_step:
            next_step()

    def re_add_members(self, label, drive_id, next_step):
        if not self.main_members:
            self.log(f"\n[Warning] No stored main membership found for the {label} drive.")
            if next_step:
                next_step()
            return

        for (web_role, addresses) in self.main_members:
            gam_role = WEB_TO_GAM[web_role]
            for addr in addresses:
                self.log(f"\nRe-adding {addr} as {web_role} to the {label} drive...")
                cmd = [
                    GAM_PATH, "add", "drivefileacl", drive_id,
                    "user", addr, "role", gam_role
                ]
                self.run_blocking_command(cmd)

        question = f"Add additional new members for the {label} drive?"
        more = CustomYesNoDialog.ask("Additional members?", question, parent=self)
        if more:
            self.bulk_add_members(drive_id=drive_id, store_in_main=False, label=label, next_step=next_step)
        else:
            if next_step:
                next_step()

    ########################################################################
    # RUNNING COMMANDS
    ########################################################################

    def run_blocking_command(self, cmd_list):
        try:
            proc = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            out, err = proc.communicate()
            if out:
                for line in out.splitlines():
                    self.log(line)
            if err:
                for e_line in err.splitlines():
                    self.log(f"\n{e_line}")
        except Exception as e:
            self.log(f"\n[Exception] {str(e)}")

    def run_threaded_command(self, cmd_list, callback):
        worker = WorkerThread(cmd_list)
        self.workers.append(worker)

        worker.line_signal.connect(self.log)

        def on_done(rc, lines):
            callback(rc, lines)

        worker.done_signal.connect(on_done)
        worker.start()

    ########################################################################
    # UTILITY
    ########################################################################

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


def main():
    app = QApplication(sys.argv)
    # Set an app-wide icon so new windows also share it by default
    app.setWindowIcon(QIcon("/Library/JAMF/Icon/brandingimage.icns"))

    w = MainWindow()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()