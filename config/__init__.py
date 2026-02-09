# Config module for BPS Fishing Macro V5
# Zero-behavior-change extraction from V4

from .settings_manager import SettingsManager
from .defaults import get_default_coords, DEFAULT_COORDS_1920x1080

__all__ = ['SettingsManager', 'get_default_coords', 'DEFAULT_COORDS_1920x1080']
