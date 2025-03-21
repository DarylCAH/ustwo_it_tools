#!/usr/bin/env python3
"""
Shared configuration module for ustwo IT tools.
Provides centralized path management and configuration.
"""

import os
import json

# Get the directory containing this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Define standard paths
ASSETS_DIR = os.path.join(SCRIPT_DIR, "assets")
CONFIG_DIR = os.path.join(SCRIPT_DIR, "config")
ICON_PATH = os.path.join(ASSETS_DIR, "brandingimage.icns")

# GAM path - can be overridden by environment variable
GAM_PATH = os.getenv("GAM_PATH", os.path.expanduser("~/bin/gam7/gam"))

# Config file paths
SHARED_CONFIG = os.path.join(CONFIG_DIR, "shared_config.json")
GROUP_CONFIG = os.path.join(CONFIG_DIR, "group_config.json")
DRIVE_CONFIG = os.path.join(CONFIG_DIR, "drive_config.json")
OFFBOARD_CONFIG = os.path.join(CONFIG_DIR, "offboard_config.json")

# Ensure directories exist
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)

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