#!/usr/bin/env python3
"""
Configuration settings for ustwo IT Tools
"""

import os
import json
import logging
from pathlib import Path

# Application paths
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(APP_DIR, 'assets')
ICON_PATH = os.path.join(ASSETS_DIR, 'brandingimage.icns')

# Logging configuration
LOG_DIR = os.path.expanduser("~/Library/Logs/ustwo_tools")
LOG_FILE = os.path.join(LOG_DIR, "ustwo_tools.log")

# Create log directory if it doesn't exist
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# GAM path - can be overridden by environment variable
GAM_PATH = os.getenv("GAM_PATH", os.path.expanduser("~/bin/gam7/gam"))

# Config file paths
SHARED_CONFIG = os.path.join(APP_DIR, "config", "shared_config.json")
GROUP_CONFIG = os.path.join(APP_DIR, "config", "group_config.json")
DRIVE_CONFIG = os.path.join(APP_DIR, "config", "drive_config.json")
OFFBOARD_CONFIG = os.path.join(APP_DIR, "config", "offboard_config.json")

# Ensure directories exist
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(SHARED_CONFIG), exist_ok=True)

def load_config(config_file):
    """Load configuration from a JSON file"""
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"[Warning] Could not load configuration: {str(e)}")
    return {}

def save_config(config_file, data):
    """Save configuration to a JSON file"""
    try:
        with open(config_file, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"[Warning] Could not save configuration: {str(e)}")
        return False

# Load shared configuration
shared_config = load_config(SHARED_CONFIG) 