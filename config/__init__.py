# Config module for BPS Fishing Macro v2.0.0
# Zero-behavior-change extraction from V4

from .settings_manager import SettingsManager
from .defaults import get_default_coords, DEFAULT_COORDS_1920x1080

__all__ = ['SettingsManager', 'get_default_coords', 'DEFAULT_COORDS_1920x1080']
