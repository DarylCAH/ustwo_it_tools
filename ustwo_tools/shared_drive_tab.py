#!/usr/bin/env python3
"""
Shared Drive Tab for ustwo IT Tools
"""

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QCheckBox, QDialog, QDialogButtonBox,
    QScrollArea
)
from . import config
import os
import json

# Config file for persistent settings
CONFIG_FILE = os.path.expanduser("~/.shared_drive_tool.json")

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

    def log(self, text):
        """Add text to the log area"""
        self.log_area.append(text)

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
                
            # Call next_step if available
            QTimer.singleShot(500, self.execute_next_step)

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
        """Handle window closing event"""
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
        config.save_config(config.DRIVE_CONFIG, self.settings) 