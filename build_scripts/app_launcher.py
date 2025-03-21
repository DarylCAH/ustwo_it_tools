#!/usr/bin/env python3
"""
MacOS App Launcher for ustwo IT Tools
This script is used as the main entry point for the macOS app bundle.
It ensures all paths and resources are properly set up.
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Set up logging
log_dir = os.path.expanduser("~/Library/Logs/ustwo_tools")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "ustwo_tools.log")

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    """Main entry point for the application"""
    try:
        # Log startup information
        logging.info("=== ustwo IT Tools starting ===")
        logging.info(f"Python version: {sys.version}")
        logging.info(f"Current directory: {os.getcwd()}")
        
        # Add app resources directory to path
        if getattr(sys, 'frozen', False):
            # Running as bundled app
            app_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            resources_path = os.path.join(app_path, 'Resources')
            if resources_path not in sys.path:
                sys.path.insert(0, resources_path)
            os.chdir(resources_path)  # Change working directory to resources
            logging.info(f"Running as bundled app, added {resources_path} to path")
        else:
            # Running as script
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if app_dir not in sys.path:
                sys.path.insert(0, app_dir)
            logging.info(f"Running as script, added {app_dir} to path")
        
        # Import main app
        logging.info("Importing main application...")
        sys.path.append(os.getcwd())  # Add current directory to path
        import ustwo_tools
        
        # Run the application
        logging.info("Starting main application")
        ustwo_tools.main()
        
    except Exception as e:
        logging.error(f"Error in launcher: {str(e)}", exc_info=True)
        
        # Show error dialog if possible
        try:
            from PyQt5.QtWidgets import QApplication, QMessageBox
            app = QApplication(sys.argv)
            error_box = QMessageBox()
            error_box.setIcon(QMessageBox.Critical)
            error_box.setWindowTitle("ustwo IT Tools Error")
            error_box.setText("An error occurred while starting the application")
            error_box.setInformativeText(f"See the log file for details: {log_file}")
            error_box.setDetailedText(str(e))
            error_box.exec_()
        except Exception as dialog_error:
            logging.error(f"Failed to show error dialog: {str(dialog_error)}", exc_info=True)
            print(f"Error starting application. See log file: {log_file}")
    
    logging.info("=== ustwo IT Tools exiting ===")

if __name__ == "__main__":
    main() 