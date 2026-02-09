# Copyright (C) 2026 BPS
# This file is part of BPS Fishing Macro.
#
# Path and resource utilities for PyInstaller/Nuitka compatibility
# Extracted from V4 - ZERO behavior changes

import os
import sys


def get_app_dir():
    """Get the directory where the executable/script is located (for settings/logs)

    Note: This mirrors the original behavior when defined in bps_fishing_macroV5.py,
    so for non-frozen runs we return the project root (parent of utils/).
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return os.path.dirname(sys.executable)
    # Running as script: parent of utils/ folder (same as main script directory)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller/Nuitka/Onefile"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Nuitka or normal script: use project root (parent of utils/)
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    
    return os.path.join(base_path, relative_path)
