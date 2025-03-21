#!/usr/bin/env python3
"""
Google Workspace Offboarding Tool
Provides functionality for offboarding users from Google Workspace.
"""

import sys
import os
import subprocess
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                          QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
                          QPushButton, QGroupBox, QCheckBox, QScrollArea)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon
import config

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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = config.load_config(config.OFFBOARD_CONFIG)
        self.init_ui()

    def init_ui(self):
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # Create left column for inputs
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        
        # Welcome message
        welcome_label = QLabel("Google Workspace Offboarding Tool")
        welcome_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(welcome_label)
        
        # Email input section
        email_container = QWidget()
        email_layout = QVBoxLayout(email_container)
        
        email_label = QLabel("Enter email addresses (one per line):")
        email_label.setAlignment(Qt.AlignCenter)
        email_layout.addWidget(email_label)
        
        self.email_input = QPlainTextEdit()
        self.email_input.setPlaceholderText("Enter email addresses here...")
        self.email_input.setMinimumHeight(100)
        email_layout.addWidget(self.email_input)
        
        # Center the email input section
        email_wrapper = QHBoxLayout()
        email_wrapper.addStretch()
        email_wrapper.addWidget(email_container)
        email_wrapper.addStretch()
        left_layout.addLayout(email_wrapper)
        
        # Options group
        options_group = QGroupBox("Offboarding Options")
        options_layout = QVBoxLayout()
        
        self.transfer_groups = QCheckBox("Transfer owned groups")
        self.remove_groups = QCheckBox("Remove from all groups")
        self.set_ooo = QCheckBox("Set out of office message")
        self.reset_pw = QCheckBox("Reset password")
        self.sign_out = QCheckBox("Sign out from all devices")
        self.hide_dir = QCheckBox("Hide from directory")
        self.move_ou = QCheckBox("Move to Leavers OU")
        
        options_layout.addWidget(self.transfer_groups)
        options_layout.addWidget(self.remove_groups)
        options_layout.addWidget(self.set_ooo)
        options_layout.addWidget(self.reset_pw)
        options_layout.addWidget(self.sign_out)
        options_layout.addWidget(self.hide_dir)
        options_layout.addWidget(self.move_ou)
        
        options_group.setLayout(options_layout)
        left_layout.addWidget(options_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Offboarding")
        self.quit_button = QPushButton("Quit")
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.quit_button)
        left_layout.addLayout(button_layout)
        
        # Create right column for output
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        
        output_label = QLabel("Output Log")
        output_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(output_label)
        
        self.output_log = QPlainTextEdit()
        self.output_log.setReadOnly(True)
        right_layout.addWidget(self.output_log)
        
        # Add columns to main layout
        layout.addWidget(left_column)
        layout.addWidget(right_column)
        
        # Connect signals
        self.start_button.clicked.connect(self.start_offboarding)
        self.quit_button.clicked.connect(self.close)
        
        # Load saved settings
        self.load_settings()

    def load_settings(self):
        """Load settings from config file"""
        if self.settings:
            self.transfer_groups.setChecked(self.settings.get('transfer_groups', True))
            self.remove_groups.setChecked(self.settings.get('remove_groups', True))
            self.set_ooo.setChecked(self.settings.get('set_ooo', True))
            self.reset_pw.setChecked(self.settings.get('reset_pw', True))
            self.sign_out.setChecked(self.settings.get('sign_out', True))
            self.hide_dir.setChecked(self.settings.get('hide_dir', True))
            self.move_ou.setChecked(self.settings.get('move_ou', True))

    def save_settings(self):
        """Save current settings to config file"""
        self.settings = {
            'transfer_groups': self.transfer_groups.isChecked(),
            'remove_groups': self.remove_groups.isChecked(),
            'set_ooo': self.set_ooo.isChecked(),
            'reset_pw': self.reset_pw.isChecked(),
            'sign_out': self.sign_out.isChecked(),
            'hide_dir': self.hide_dir.isChecked(),
            'move_ou': self.move_ou.isChecked()
        }
        config.save_config(config.OFFBOARD_CONFIG, self.settings)

    def log_output(self, text):
        """Add text to the output log"""
        self.output_log.appendPlainText(text)

    def run_gam_command(self, command):
        """Run a GAM command using the configured GAM path"""
        full_command = f"{config.GAM_PATH} {command}"
        worker = WorkerThread(full_command)
        worker.output.connect(self.log_output)
        worker.finished.connect(self.command_finished)
        worker.start()
        self.current_worker = worker

    def command_finished(self):
        """Handle command completion"""
        self.start_button.setEnabled(True)
        self.quit_button.setEnabled(True)

    def start_offboarding(self):
        """Start the offboarding process for the entered email addresses"""
        emails = self.email_input.toPlainText().strip().split('\n')
        if not emails:
            self.log_output("Error: No email addresses entered")
            return
        
        self.start_button.setEnabled(False)
        self.quit_button.setEnabled(False)
        
        for email in emails:
            email = email.strip()
            if not email:
                continue
                
            self.log_output(f"\nProcessing {email}...")
            
            if self.transfer_groups.isChecked():
                self.run_gam_command(f"user {email} show groups | grep 'Owner' | cut -d' ' -f2")
                # TODO: Transfer ownership of found groups
            
            if self.remove_groups.isChecked():
                self.run_gam_command(f"user {email} delete groups")
            
            if self.set_ooo.isChecked():
                self.run_gam_command(f'user {email} vacation on subject "Out of Office" message "This person no longer works at ustwo."')
            
            if self.reset_pw.isChecked():
                self.run_gam_command(f"user {email} password random")
            
            if self.sign_out.isChecked():
                self.run_gam_command(f"user {email} signout")
            
            if self.hide_dir.isChecked():
                self.run_gam_command(f"user {email} update gal off")
            
            if self.move_ou.isChecked():
                self.run_gam_command(f"update org '/Leavers' add users {email}")

    def closeEvent(self, event):
        """Save settings when closing the window"""
        self.save_settings()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    if os.path.exists(config.ICON_PATH):
        app.setWindowIcon(QIcon(config.ICON_PATH))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 