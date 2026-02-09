# Copyright (C) 2026 BPS
# This file is part of BPS Fishing Macro.
#
# Validation utilities for coordinates, webhooks, etc.
# Extracted from V4 - ZERO behavior changes

import logging

logger = logging.getLogger('FishingMacro')


def validate_webhook_url(url):
    """Validate Discord webhook URL format"""
    if not url or not isinstance(url, str):
        return False
    # Discord webhook URL pattern
    return url.startswith('https://discord.com/api/webhooks/') or url.startswith('https://discordapp.com/api/webhooks/')


def validate_user_id(user_id):
    """Validate Discord user ID (must be numeric string)"""
    if not user_id or not isinstance(user_id, str):
        return True  # Empty is allowed
    return user_id.isdigit() and len(user_id) >= 17 and len(user_id) <= 20


def validate_coordinates(coords, coord_name="coordinates", screen_width=None, screen_height=None):
    """Validate coordinate dict has valid x, y values within screen bounds
    
    Args:
        coords: Dict with 'x' and 'y' keys
        coord_name: Name for error messages
        screen_width: Screen width limit (required if coords not None)
        screen_height: Screen height limit (required if coords not None)
    """
    if coords is None:
        return True  # None is allowed for optional coords
    if not isinstance(coords, dict):
        logger.warning(f"Invalid {coord_name}: not a dict")
        return False
    
    required_keys = ['x', 'y']
    if not all(key in coords for key in required_keys):
        logger.warning(f"Invalid {coord_name}: missing x or y")
        return False
    
    try:
        x, y = int(coords['x']), int(coords['y'])
        if x < 0 or y < 0 or x > screen_width or y > screen_height:
            logger.warning(f"Invalid {coord_name}: ({x}, {y}) out of screen bounds")
            return False
        return True
    except (ValueError, TypeError):
        logger.warning(f"Invalid {coord_name}: x or y not numeric")
        return False


def validate_area_coords(coords, screen_width=None, screen_height=None):
    """Validate area coordinates dict with x, y, width, height"""
    if coords is None:
        return False
    if not isinstance(coords, dict):
        return False
    
    required_keys = ['x', 'y', 'width', 'height']
    if not all(key in coords for key in required_keys):
        return False
    
    try:
        x, y = int(coords['x']), int(coords['y'])
        w, h = int(coords['width']), int(coords['height'])
        if w <= 0 or h <= 0:
            return False
        if x < 0 or y < 0 or (x + w) > screen_width or (y + h) > screen_height:
            return False
        return True
    except (ValueError, TypeError):
        return False
