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
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QCheckBox, QDialog, QDialogButtonBox,
    QPlainTextEdit, QComboBox, QGroupBox, QScrollArea
)
import config

# Path to GAM binary
GAM_PATH = os.path.expanduser("~/bin/gam7/gam")

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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Google Shared Drive Creation Tool")
        self.settings = config.load_config(config.DRIVE_CONFIG)
        self.init_ui()

    def init_ui(self):
        self.workers = []
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