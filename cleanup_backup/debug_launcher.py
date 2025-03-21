#!/usr/bin/env python3
import os, sys, traceback, datetime
home_dir = os.path.expanduser("~"); log_dir = os.path.join(home_dir, "ustwo_logs"); os.makedirs(log_dir, exist_ok=True); log_file = os.path.join(log_dir, "debug.log")
def log(msg): open(log_file, "a").write(f"{datetime.datetime.now()}: {msg}
")
try: log("Starting app"); import ustwo_tools; ustwo_tools.main(); except Exception as e: log(f"Error: {e}"); log(traceback.format_exc()); from PyQt5.QtWidgets import QApplication, QMessageBox; app = QApplication(sys.argv); QMessageBox.critical(None, "Error", f"Error: {e}
Check log at {log_file}")
