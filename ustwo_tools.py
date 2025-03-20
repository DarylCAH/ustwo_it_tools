#!/usr/bin/env python3
"""
Unified ustwo IT Tools Application
Provides a tabbed interface for Google Groups, Shared Drives, and Offboarding tools.
"""

import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, 
                           QVBoxLayout, QWidget)
from PyQt5.QtGui import QIcon
import config

# Import tool modules
from Create_Group import MainWindow as GroupWindow
from Shared_Drive import MainWindow as DriveWindow
from Offboarding import MainWindow as OffboardWindow

class UstwooTools(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """Initialize the main UI with tabs for each tool"""
        self.setWindowTitle('ustwo IT Tools')
        
        # Set window icon if available
        if os.path.exists(config.ICON_PATH):
            self.setIcon(QIcon(config.ICON_PATH))
            
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Create tab widget
        tabs = QTabWidget()
        
        # Add tool tabs
        group_tab = GroupWindow()
        drive_tab = DriveWindow()
        offboard_tab = OffboardWindow()
        
        tabs.addTab(group_tab, "Google Groups")
        tabs.addTab(drive_tab, "Shared Drives")
        tabs.addTab(offboard_tab, "Offboarding")
        
        layout.addWidget(tabs)
        
        # Set window size
        self.setGeometry(100, 100, 1200, 800)
        self.show()

def main():
    app = QApplication(sys.argv)
    ex = UstwooTools()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 