# Copyright (C) 2026 BPS
# This file is part of BPS Fishing Macro.
#
# Centralized settings manager
# Extracted from V4 - ZERO behavior changes
# All load_*_settings() and save_*_settings() methods consolidated here

import os
import json
import logging
import threading
from .defaults import get_default_coords

logger = logging.getLogger("FishingMacro")


class SettingsManager:
    """Centralized settings management for BPS Fishing Macro

    Replaces all individual load_*_settings() and save_*_settings() methods
    from V4 with a single unified interface.

    ZERO behavior changes - same JSON structure, same defaults, same validation.
    """

    def __init__(self, settings_file: str):
        """Initialize settings manager

        Args:
            settings_file: Absolute path to settings JSON file
        """
        self.settings_file = settings_file
        self._data = {}  # In-memory cache
        self._lock = threading.Lock()  # Thread-safe access
        self._ensure_settings_file_exists()
        self._load_all()

    def _ensure_settings_file_exists(self):
        """Create default settings file if it doesn't exist"""
        if not os.path.exists(self.settings_file):
            logger.info("Creating default settings file...")
            default_settings = {
                "always_on_top": True,
                "area_coords": {"x": 1089, "y": -4, "width": 573, "height": 1084},
                "water_point": None,
                "item_hotkeys": {"rod": "1", "everything_else": "2", "fruit": "3"},
                "pid_settings": {"kp": 1.0, "kd": 0.3, "clamp": 1.0, "deadband": 1.0},
                "casting_settings": {
                    "cast_hold_duration": 1.0,
                    "recast_timeout": 35.0,
                    "fishing_end_delay": 1.0,
                },
                "precast_settings": {
                    "auto_buy_bait": True,
                    "auto_store_fruit": True,
                    "auto_select_top_bait": True,
                    "yes_button": None,
                    "middle_button": None,
                    "no_button": None,
                    "loops_per_purchase": 100,
                    "fruit_point": None,
                    "fruit_color": None,
                    "top_bait_point": None,
                },
                "webhook_settings": {
                    "webhook_url": "",
                    "user_id": "",
                    "only_legendary": False,
                    # Use scaled default pity zone instead of None so it materializes on first run
                    "pity_zone": get_default_coords().get("pity_zone"),
                },
                "hud_position": "top",
                "advanced_settings": {
                    "camera_rotation_delay": 0.05,
                    "camera_rotation_steps": 8,
                    "camera_rotation_step_delay": 0.05,
                    "camera_rotation_settle_delay": 0.15,
                    "zoom_ticks": 3,
                    "zoom_tick_delay": 0.05,
                    "zoom_settle_delay": 0.15,
                    "pre_cast_minigame_wait": 1.5,
                    "store_click_delay": 1,
                    "backspace_delay": 0.3,
                    "rod_deselect_delay": 0.3,
                    "rod_select_delay": 0.3,
                    "bait_click_delay": 0.3,
                    "fruit_detection_delay": 0.02,
                    "fruit_detection_settle": 0.3,
                    "general_action_delay": 0.05,
                    "mouse_move_settle": 0.05,
                    "focus_settle_delay": 1.0,
                    "disable_normal_camera": True,
                    "fruit_hold_delay": 0.1,
                },
                "auto_craft_settings": {
                    "auto_craft_enabled": False,
                    "auto_craft_water_point": None,
                    "craft_every_n_fish": 1,
                    "craft_menu_delay": 0.1,
                    "craft_click_speed": 0.1,
                    "craft_legendary_quantity": 1,
                    "craft_rare_quantity": 1,
                    "craft_common_quantity": 1,
                    "craft_button_coords": None,
                    "plus_button_coords": None,
                    "fish_icon_coords": None,
                    "legendary_bait_coords": None,
                    "rare_bait_coords": None,
                    "common_bait_coords": None,
                    "smart_bait_2nd_coords": None,
                },
                "auto_craft_area_coords": {
                    "x": 1269,
                    "y": -4,
                    "width": 498,
                    "height": 1092,
                },
            }
            try:
                with open(self.settings_file, "w", encoding="utf-8") as f:
                    json.dump(default_settings, f, indent=4, ensure_ascii=False)
                logger.info(f"Default settings created at: {self.settings_file}")
            except Exception as e:
                logger.error(f"Failed to create default settings: {e}")

    def _load_all(self):
        """Load all settings from file (called at init, no lock needed)"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r") as f:
                    self._data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse settings file: {e}")
            self._data = {}
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            self._data = {}

    def _save_all(self):
        """Save all settings to file (assumes caller holds lock)"""
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    # ========================================================================
    # INDIVIDUAL SETTING LOADERS (V4 compatible)
    # ========================================================================

    def load_area_coords(self):
        """Load area coordinates from settings file"""
        with self._lock:
            return self._data.get("area_coords", get_default_coords()["area_coords"])

    def load_auto_craft_area_coords(self):
        """Load auto craft area coordinates from settings file"""
        from .defaults import SCREEN_WIDTH, SCREEN_HEIGHT

        default_coords = {
            "x": SCREEN_WIDTH // 2 - 150,
            "y": SCREEN_HEIGHT // 2 - 150,
            "width": 300,
            "height": 300,
        }
        with self._lock:
            return self._data.get("auto_craft_area_coords", default_coords)

    def load_water_point(self):
        """Load water point coordinates from settings file"""
        with self._lock:
            return self._data.get("water_point", get_default_coords()["water_point"])

    def load_item_hotkeys(self):
        """Load item hotkeys from settings file"""
        default_hotkeys = {"rod": "1", "everything_else": "2", "fruit": "3"}
        with self._lock:
            return self._data.get("item_hotkeys", default_hotkeys)

    def load_pid_settings(self):
        """Load PID settings from settings file"""
        default_pid = {"kp": 1.0, "kd": 0.3, "clamp": 1.0}
        with self._lock:
            return self._data.get("pid_settings", default_pid)

    def load_casting_settings(self):
        """Load casting settings from settings file"""
        default_casting = {
            "cast_hold_duration": 1.0,
            "recast_timeout": 30.0,
            "fishing_end_delay": 1.5,
        }
        with self._lock:
            return self._data.get("casting_settings", default_casting)

    def load_precast_settings(self):
        """Load precast settings from settings file"""
        defaults = get_default_coords()
        default_precast = {
            "auto_buy_bait": True,
            "auto_store_fruit": True,
            "yes_button": defaults["yes_button"],
            "middle_button": defaults["middle_button"],
            "no_button": defaults["no_button"],
            "loops_per_purchase": 100,
            "fruit_point": defaults["fruit_point"],
            "fruit_color": [7, 116, 45],
            "auto_select_top_bait": True,
            "top_bait_point": defaults["top_bait_point"],
            "store_in_inventory": False,
            "inventory_fruit_point": None,
            "inventory_center_point": None,
        }
        with self._lock:
            return self._data.get("precast_settings", default_precast)

    def load_auto_craft_settings(self):
        """Load auto craft settings from settings file"""
        default_auto_craft = {
            "auto_craft_enabled": False,
            "auto_craft_water_point": None,
            "craft_every_n_fish": 10,
            "craft_menu_delay": 0.5,
            "craft_click_speed": 0.2,
            "craft_legendary_quantity": 1,
            "craft_rare_quantity": 1,
            "craft_common_quantity": 1,
            "craft_button_coords": None,
            "plus_button_coords": None,
            "fish_icon_coords": None,
            "legendary_bait_coords": None,
            "rare_bait_coords": None,
            "common_bait_coords": None,
            "smart_bait_2nd_coords": None,
        }
        with self._lock:
            return self._data.get("auto_craft_settings", default_auto_craft)

    def load_smart_bait_settings(self):
        """Load Smart Bait settings from settings file"""
        # Get defaults scaled to current resolution
        defaults = get_default_coords()
        default_smart_bait = {
            "enabled": False,
            "mode": "stockpile",  # 'burning' or 'stockpile'
            "legendary_target": 50,
            "ocr_timeout_ms": 1500,  # Increased for gradient text
            "ocr_confidence_min": 0.4,  # Lowered for colorful text
            "fallback_bait": "legendary",  # 'legendary' or 'rare'
            "debug_screenshots": False,
            "use_ocr": True,
            "menu_zone": defaults.get(
                "smart_bait_menu_zone"
            ),  # Full bait list OCR zone
            # Top and mid bait color scan zones: only the bait name labels (no numbers)
            "top_bait_scan_zone": defaults.get("smart_bait_top_zone"),
            "mid_bait_scan_zone": defaults.get("smart_bait_mid_zone"),
        }
        with self._lock:
            return self._data.get("smart_bait_settings", default_smart_bait)

    def load_webhook_settings(self):
        """Load webhook settings from JSON"""
        # Get defaults scaled to current resolution
        defaults = get_default_coords()
        default_webhook = {
            "webhook_url": "",
            "user_id": "",
            "only_legendary": False,
            "pity_zone": defaults.get("pity_zone"),
        }
        with self._lock:
            settings = self._data.get("webhook_settings", default_webhook)
            # If pity_zone is absent or None, fall back to scaled default
            if settings.get("pity_zone") is None:
                settings["pity_zone"] = defaults.get("pity_zone")
            return settings

    def load_advanced_settings(self):
        """Load advanced timing settings from settings file"""
        default_advanced = {
            # Camera rotation delays
            "camera_rotation_delay": 0.05,
            "camera_rotation_steps": 8,
            "camera_rotation_step_delay": 0.05,
            "camera_rotation_settle_delay": 0.3,
            # Zoom delays
            "zoom_ticks": 3,
            "zoom_tick_delay": 0.05,
            "zoom_settle_delay": 0.3,
            # Pre-cast delays
            "pre_cast_minigame_wait": 2.5,
            "store_click_delay": 1.0,
            "backspace_delay": 0.3,
            "rod_deselect_delay": 0.5,
            "rod_select_delay": 0.5,
            "bait_click_delay": 0.3,
            # Detection & general delays
            "fruit_detection_delay": 0.02,
            "fruit_detection_settle": 0.3,
            "general_action_delay": 0.05,
            "mouse_move_settle": 0.05,
            # Focus settle delay after bringing Roblox to foreground
            "focus_settle_delay": 1.0,
            # Disable camera/zoom/rotation in normal mode (not Auto Craft)
            "disable_normal_camera": True,  # Default: True (simplified mode)
        }
        with self._lock:
            return self._data.get("advanced_settings", default_advanced)

    def load_sound_settings(self):
        """V3: Load sound settings from settings file"""
        default_sound = {
            "sound_enabled": True,
            "sound_frequency": 400,
            "sound_duration": 150,
        }
        with self._lock:
            return self._data.get("sound_settings", default_sound)

    def load_hud_position(self):
        """Load HUD position from settings file"""
        with self._lock:
            return self._data.get("hud_position", "top")

    def load_always_on_top(self):
        """Load always on top setting from settings file"""
        with self._lock:
            return self._data.get("always_on_top", False)

    # ========================================================================
    # INDIVIDUAL SETTING SAVERS (V4 compatible)
    # ========================================================================

    def save_area_coords(self, area_coords):
        """Save area coordinates to settings file"""
        with self._lock:
            self._data["area_coords"] = area_coords
            self._save_all()

    def save_auto_craft_area_coords(self, area_coords):
        """Save auto craft area coordinates to settings file"""
        with self._lock:
            self._data["auto_craft_area_coords"] = area_coords
            self._save_all()

    def save_water_point(self, water_point):
        """Save water point coordinates to settings file"""
        with self._lock:
            self._data["water_point"] = water_point
            self._save_all()

    def save_item_hotkeys(self, rod_hotkey, everything_else_hotkey, fruit_hotkey):
        """Save item hotkeys to settings file"""
        with self._lock:
            self._data["item_hotkeys"] = {
                "rod": rod_hotkey,
                "everything_else": everything_else_hotkey,
                "fruit": fruit_hotkey,
            }
            self._save_all()

    def save_pid_settings(self, pid_kp, pid_kd, pid_clamp):
        """Save PID settings to settings file"""
        with self._lock:
            self._data["pid_settings"] = {
                "kp": pid_kp,
                "kd": pid_kd,
                "clamp": pid_clamp,
            }
            self._save_all()

    def save_casting_settings(
        self, cast_hold_duration, recast_timeout, fishing_end_delay
    ):
        """Save casting settings to settings file"""
        with self._lock:
            self._data["casting_settings"] = {
                "cast_hold_duration": cast_hold_duration,
                "recast_timeout": recast_timeout,
                "fishing_end_delay": fishing_end_delay,
            }
            self._save_all()

    def save_precast_settings(self, settings_dict):
        """Save precast settings to settings file

        Args:
            settings_dict: Dictionary with keys:
                - auto_buy_bait
                - auto_store_fruit
                - yes_button
                - middle_button
                - no_button
                - loops_per_purchase
                - fruit_point
                - fruit_color
                - auto_select_top_bait
                - top_bait_point
                - store_in_inventory
                - inventory_fruit_point
                - inventory_center_point
        """
        with self._lock:
            self._data["precast_settings"] = settings_dict
            self._save_all()

    def save_auto_craft_settings(self, settings_dict):
        """Save auto craft settings to settings file

        Args:
            settings_dict: Dictionary with auto craft settings
        """
        with self._lock:
            self._data["auto_craft_settings"] = settings_dict
            self._save_all()

    def save_smart_bait_settings(self, settings_dict):
        """Save Smart Bait settings to settings file

        Args:
            settings_dict: Dictionary with smart bait settings
        """
        with self._lock:
            self._data["smart_bait_settings"] = settings_dict
            self._save_all()

    def save_webhook_settings(self, webhook_url, user_id, only_legendary, pity_zone):
        """Save webhook settings to settings file"""
        with self._lock:
            self._data["webhook_settings"] = {
                "webhook_url": webhook_url,
                "user_id": user_id,
                "only_legendary": only_legendary,
                "pity_zone": pity_zone,
            }
            self._save_all()

    def save_advanced_settings(self, settings_dict):
        """Save advanced timing settings to settings file

        Args:
            settings_dict: Dictionary with all advanced settings
        """
        with self._lock:
            self._data["advanced_settings"] = settings_dict
            self._save_all()

    def save_sound_settings(self, sound_enabled, sound_frequency, sound_duration):
        """V3: Save sound settings to settings file"""
        with self._lock:
            self._data["sound_settings"] = {
                "sound_enabled": sound_enabled,
                "sound_frequency": sound_frequency,
                "sound_duration": sound_duration,
            }
            self._save_all()
        logger.info("Sound settings saved successfully")

    def save_hud_position(self, hud_position):
        """Save HUD position to settings file"""
        with self._lock:
            self._data["hud_position"] = hud_position
            self._save_all()

    def save_always_on_top(self, always_on_top):
        """Save always on top setting to settings file"""
        with self._lock:
            self._data["always_on_top"] = always_on_top
            self._save_all()

    def load_discord_rpc_settings(self):
        """V5.2: Load Discord Rich Presence settings from settings file"""
        default_rpc = {
            "enabled": False,
        }
        with self._lock:
            return self._data.get("discord_rpc_settings", default_rpc)

    def save_discord_rpc_settings(self, enabled):
        """V5.2: Save Discord Rich Presence settings to settings file"""
        with self._lock:
            self._data["discord_rpc_settings"] = {
                "enabled": enabled,
            }
            self._save_all()
        logger.info("Discord RPC settings saved successfully")

    def load_discord_bot_settings(self):
        """V5.2: Load Discord Bot settings from settings file"""
        default_bot = {
            "enabled": False,
            "application_id": "",  # Discord Application ID
            "bot_token": "",  # Encrypted token
            "allowed_user_ids": [],  # List of Discord user IDs
            "guild_id": "",  # Discord Server (Guild) ID
            "auto_menu_channel_id": "",  # Channel ID for auto-sending menu
        }
        with self._lock:
            return self._data.get("discord_bot_settings", default_bot)

    def save_discord_bot_settings(
        self,
        enabled,
        application_id,
        bot_token,
        allowed_user_ids,
        guild_id="",
        auto_menu_channel_id="",
    ):
        """V5.2: Save Discord Bot settings to settings file"""
        with self._lock:
            self._data["discord_bot_settings"] = {
                "enabled": enabled,
                "application_id": application_id,
                "bot_token": bot_token,  # Already encrypted
                "allowed_user_ids": allowed_user_ids,
                "guild_id": guild_id,
                "auto_menu_channel_id": auto_menu_channel_id,
            }
            self._save_all()
        logger.info("Discord Bot settings saved successfully")
