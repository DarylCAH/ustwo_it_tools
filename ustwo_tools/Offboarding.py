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
                          QPushButton, QGroupBox, QCheckBox, QScrollArea,
                          QTextEdit, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon
import logging

from . import config

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

class OffboardingTab(QWidget):
    def __init__(self):
        super().__init__()
        self.worker_threads = []  # List to track all worker threads
        self.init_ui()

    def init_ui(self):
        # Create main layout
        layout = QHBoxLayout(self)
        
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
        
        # Offboarding actions information
        actions_group = QGroupBox("Offboarding Actions")
        actions_layout = QVBoxLayout()
        
        actions_label = QLabel("The following actions will be performed for each user:")
        actions_layout.addWidget(actions_label)
        
        actions_list = QLabel("• Transfer owned groups\n• Remove from all groups\n• Set out of office message\n• Reset password\n• Sign out from all devices\n• Hide from directory\n• Move to Leavers OU")
        actions_layout.addWidget(actions_list)
        
        actions_group.setLayout(actions_layout)
        left_layout.addWidget(actions_group)
        
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

    def log_output(self, text):
        """Add text to the output log"""
        self.output_log.appendPlainText(text)

    def run_gam_command(self, command):
        """Run a GAM command using the configured GAM path"""
        full_command = f"{config.GAM_PATH} {command}"
        worker = WorkerThread(full_command)
        worker.output.connect(self.log_output)
        worker.finished.connect(self.command_finished)
        worker.finished.connect(lambda: self.cleanup_thread(worker))  # Clean up thread when finished
        self.worker_threads.append(worker)  # Track the thread
        worker.start()

    def cleanup_thread(self, worker):
        """Remove the worker thread from our list when it's done"""
        if worker in self.worker_threads:
            self.worker_threads.remove(worker)

    def command_finished(self):
        """Handle command completion"""
        # Only enable buttons if all commands have completed
        if not self.worker_threads:
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
            
            # Find manager email for group transfer
            self.log_output("Finding manager for the user...")
            self.run_gam_command(f"user {email} print manager | awk -F, 'NR>1 {{if ($4 != \"\") print $4}}'")
            
            # Check for owned groups and transfer ownership
            self.log_output("Finding and transferring owned groups...")
            # First get the list of owned groups
            self.run_gam_command(f"user {email} print groups roles owner")
            # NOTE: In a real implementation, we would capture the output and 
            # transfer groups to the manager, but this would require more complex
            # inter-thread communication. For now, we'll just show the groups.
            self.log_output("Group transfer would require capturing output between commands.")
            self.log_output("See the bash script for the full implementation.")
            
            # Remove from all groups
            self.log_output("Removing user from all groups...")
            self.run_gam_command(f"user {email} delete groups")
            
            # Set out of office message
            self.log_output("Setting out of office message...")
            # In a real implementation, we'd need to run commands to get the name first
            # and then use those results to set the vacation message
            self.run_gam_command(f"user {email} vacation on subject \"This person is no longer with ustwo\" message \"Thank you for your email, however this person is no longer with ustwo.\"")
            
            # Reset password
            self.log_output("Resetting password...")
            self.run_gam_command(f"update user {email} password random")
            
            # Sign out from all devices
            self.log_output("Signing out from all devices...")
            self.run_gam_command(f"user {email} signout")
            
            # Hide from directory
            self.log_output("Hiding user from directory...")
            self.run_gam_command(f"update user {email} gal false")
            
            # Move to Leavers OU
            self.log_output("Moving user to Leavers OU...")
            self.run_gam_command(f"update org '/Leavers' add users {email}")

    def closeEvent(self, event):
        """Handle window closing event"""
        # Wait for all worker threads to finish
        for worker in self.worker_threads[:]:
            worker.wait()
            self.worker_threads.remove(worker)
            
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    if os.path.exists(config.ICON_PATH):
        app.setWindowIcon(QIcon(config.ICON_PATH))
    window = OffboardingTab()
    window.show()
    sys.exit(app.exec_()) 