# Copyright (C) 2026 BPS
# This file is part of BPS Fishing Macro.
#
# Default configuration values and coordinate scaling
# Extracted from V4 - ZERO behavior changes

import ctypes
import os

# Get screen resolution (Windows-only; safe fallback for CI/non-Windows)
if os.name == "nt":
    SCREEN_WIDTH = ctypes.windll.user32.GetSystemMetrics(0)
    SCREEN_HEIGHT = ctypes.windll.user32.GetSystemMetrics(1)
else:
    SCREEN_WIDTH = 1920
    SCREEN_HEIGHT = 1080
REF_WIDTH = 1920  # Reference resolution width
REF_HEIGHT = 1080  # Reference resolution height

# Default coordinates for 1920x1080 (will be scaled to user's resolution)
# Only AREA configurations are set by default to match current user optimized settings
DEFAULT_COORDS_1920x1080 = {
    "area_coords": {"x": 1106, "y": 181, "width": 500, "height": 751},
    "auto_craft_area_coords": {"x": 1269, "y": -4, "width": 498, "height": 1092},
    # Smart Bait zones (1920x1080 optimized)
    "smart_bait_menu_zone": {"x": 831, "y": 783, "width": 257, "height": 127},
    "smart_bait_top_zone": {"x": 841, "y": 787, "width": 239, "height": 26},
    "smart_bait_mid_zone": {"x": 851, "y": 828, "width": 177, "height": 16},
    # Pity filter zone (1920x1080)
    "pity_zone": {"x": 851, "y": 135, "width": 222, "height": 32},
    # Button coordinates are left essentially empty/None in defaults
    # to force/encourage user selection or are handled dynamically
    "water_point": None,
    "yes_button": None,
    "middle_button": None,
    "no_button": None,
    "fruit_point": None,
    "top_bait_point": None,
    # Auto Craft button coords (user must configure)
    "craft_button_coords": None,
    "plus_button_coords": None,
    "fish_icon_coords": None,
    "legendary_bait_coords": None,
    "rare_bait_coords": None,
    "common_bait_coords": None,
    # Smart Bait 2nd rare bait coords (user must configure)
    "smart_bait_2nd_coords": None,
}

# Default feature states (applied on first run)
DEFAULT_FEATURE_STATES = {
    "always_on_top": True,
    "discord_rpc_enabled": True,
    "discord_bot_enabled": False,  # Discord Bot disabled by default
    "auto_craft_enabled": False,
    "smart_bait_enabled": False,
    "megalodon_enabled": True,
    "sound_enabled": True,
    "auto_buy_bait": True,
    "auto_store_fruit": True,
    "only_legendary": True,  # Webhook filter
    "disable_normal_camera": True,
}

# Default Discord RPC Application ID (public, can be shared)
DEFAULT_DISCORD_APP_ID = "659816357587845140"


def scale_coord(coord_dict):
    """Scale coordinates from 1920x1080 to current screen resolution"""
    if not coord_dict:
        return None

    scaled = {}
    for key, value in coord_dict.items():
        if key in ["x", "width"]:
            scaled[key] = int(value * SCREEN_WIDTH / REF_WIDTH)
        elif key in ["y", "height"]:
            scaled[key] = int(value * SCREEN_HEIGHT / REF_HEIGHT)
        else:
            scaled[key] = value
    return scaled


def get_default_coords():
    """Get default coordinates scaled to current resolution"""
    defaults = {}
    for key, val in DEFAULT_COORDS_1920x1080.items():
        defaults[key] = scale_coord(val)
    return defaults
