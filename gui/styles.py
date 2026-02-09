# Copyright (C) 2026 BPS
# This file is part of BPS Fishing Macro.
#
# V5: GUI Module - Styles and Constants
# Pure extraction from main file - NO visual changes

"""
GUI color scheme and styling constants.
EXACT copy from main file - maintaining all visual consistency.
"""

# CustomTkinter colors - V3 Dark + White Minimalist
BG_COLOR = "#141414"       # Main background
FG_COLOR = "#f5f5f5"       # Text color (soft white)
ACCENT_COLOR = "#3a3a3a"   # Neutral accent (no neon)
BUTTON_COLOR = "#2a2a2a"   # Button background
HOVER_COLOR = "#3d3d3d"    # Hover state

# Status accent colors (only for confirmations)
SUCCESS_COLOR = "#34d399"  # Green for success
WARNING_COLOR = "#fbbf24"  # Amber for warnings
ERROR_COLOR = "#f87171"    # Red for errors
INFO_COLOR = "#60a5fa"     # Blue for info

# Legacy color dict for compatibility with .configure() calls
CURRENT_COLORS = {
    'success': SUCCESS_COLOR,
    'error': ERROR_COLOR,
    'warning': WARNING_COLOR,
    'info': INFO_COLOR,
    'accent': '#4a4a4a',
    'fg': FG_COLOR,
    'bg': BG_COLOR
}

# Font constants
DEFAULT_FONT = ("Segoe UI", 10)
TITLE_FONT = ("Segoe UI", 11, "bold")
TOOLTIP_FONT = ("Segoe UI", 10)

# Window constants
DEFAULT_WINDOW_WIDTH = 600
DEFAULT_WINDOW_HEIGHT = 550
DEFAULT_WINDOW_RESIZABLE = (True, True)

# Tooltip constants
TOOLTIP_DELAY = 400  # ms
TOOLTIP_BG_COLOR = "#2d2d2d"
TOOLTIP_FG_COLOR = "#ffffff"
TOOLTIP_WRAP_LENGTH = 250
