#!/usr/bin/env python3
"""
Main application module for ustwo IT Tools
"""

import sys
import logging
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout

from . import config
from . import Create_Group
from . import Shared_Drive
from . import Offboarding

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ustwo IT Tools")
        self.setGeometry(100, 100, 800, 600)
        
        # Create tab widget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Create tabs
        self.create_group_tab = Create_Group.CreateGroupTab()
        self.shared_drive_tab = Shared_Drive.SharedDriveTab()
        self.offboarding_tab = Offboarding.OffboardingTab()
        
        # Add tabs
        self.tabs.addTab(self.create_group_tab, "Create Group")
        self.tabs.addTab(self.shared_drive_tab, "Shared Drive")
        self.tabs.addTab(self.offboarding_tab, "Offboarding")

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 