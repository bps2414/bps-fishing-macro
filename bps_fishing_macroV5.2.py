# Copyright (C) 2026 BPS
# This file is part of BPS Fishing Macro.
#
# Smart Bait System: Developed by Murtaza
# - OCR-based bait counting and selection
# - Color-only detection mode for performance
# - Auto-switching between Burning/Stockpile modes
#
# BPS Fishing Macro is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BPS Fishing Macro is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BPS Fishing Macro.  If not, see <https://www.gnu.org/licenses/>.

# Fix for darkdetect/customtkinter Windows version detection issue
import os

os.environ.setdefault("DARKDETECT_SKIP_VERSION_CHECK", "1")

import customtkinter as ctk
import tkinter as tk
import threading
import time
import os
import sys
import json
import tempfile
from types import SimpleNamespace
from queue import Queue
import asyncio
import numpy as np
import mss
import ctypes
import win32api
import win32gui
import winsound  # V3: Sound notifications (fallback)
import logging  # V3: Activity logging

# V5: Import modules from package structure
from config import SettingsManager
from config.defaults import SCREEN_WIDTH, SCREEN_HEIGHT, REF_WIDTH, REF_HEIGHT
from utils import get_app_dir, get_resource_path, validate_webhook_url, validate_user_id
from utils.watchdog import GUIWatchdog
from services import (
    WebhookService,
    AudioService,
    StatsManager,
    LoggingService,
    RichPresenceService,
    DiscordBotService,
)
from input import MouseController, KeyboardController, WindowManager
from vision import ScreenCapture, ColorDetector, OCRService, AntiMacroDetector
from automation import BaitManager, FruitHandler, CraftAutomation, FishingCycle
from core import FishingEngine, MacroState
from gui.widgets import CTkToolTip
from gui.tabs import (
    general_tab,
    settings_tab,
    fishing_tab,
    craft_tab,
    webhook_tab,
    discord_bot_tab,
    advanced_tab,
    stats_tab,
    logging_tab,
)

# OCR dependencies removed - using external Tesseract
CV2_AVAILABLE = False


def ensure_ocr_dependencies():
    """Check if cv2 and numpy are available for vision processing."""
    import importlib
    import subprocess
    import sys

    global CV2_AVAILABLE
    missing = []
    for pkg in ["cv2", "numpy"]:
        try:
            importlib.import_module(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        # Skip pip install in frozen exe (PyInstaller) — packages are already bundled
        if getattr(sys, "frozen", False):
            return False, f"Missing packages (frozen mode): {missing}"
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
        except Exception as e:
            return False, f"Erro ao instalar dependências: {e}"
    try:
        importlib.import_module("cv2")
        CV2_AVAILABLE = True
    except ImportError:
        CV2_AVAILABLE = False
    return CV2_AVAILABLE, None


# V4: Timeout support for OCR
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from datetime import datetime, timedelta  # V3: Daily summary
from pynput import keyboard
from pynput.keyboard import Key, Listener, Controller
from pynput.mouse import Listener as MouseListener, Button
import pyautogui
import pydirectinput

# Disable fail-safe (prevent crash when mouse hits corner)
# User has F1/F3 hotkeys to stop the macro safely
pyautogui.FAILSAFE = False

# V5: Setup logging via LoggingService
logging_service = LoggingService()
logger = logging_service.get_logger()

# Set customtkinter appearance
ctk.set_appearance_mode("dark")  # Dark mode by default
ctk.set_default_color_theme("blue")  # Blue theme

# Set DPI awareness to fix Windows scaling issues
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()  # Fallback for older Windows
    except:
        pass

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

# Retry Logic
MAX_OCR_RETRIES = 2
RETRY_DELAY_SECONDS = 1.0

# Timeouts (seconds)
FRUIT_DETECTION_TIMEOUT = 10.0
RECAST_TIMEOUT_DEFAULT = 35.0

# Delays (seconds)
CLICK_SETTLE_DELAY = 0.05
DRAG_INITIAL_DELAY = 0.08
DRAG_MOVE_DELAY = 0.12
DRAG_HOLD_DELAY = 0.20
DRAG_RELEASE_DELAY = 0.30
DRAG_FINAL_DELAY = 0.12

# Frame Processing
FRAME_SKIP_RATIO = 3  # Process 1 out of every 3 frames
SCREENSHOT_CACHE_MS = 16  # Cache screenshots for 16ms
INTERRUPTIBLE_SLEEP_CHECK_MS = 100  # Check running flag every 100ms

# ============================================================================

# V5: Path helpers imported from utils module
BASE_DIR = get_app_dir()
SETTINGS_FILE = os.path.join(BASE_DIR, "bpsfishmacrosettings.json")
# Audio file is now looked for in the resource path (embedded) first, or relative to script
AUDIO_FILE = get_resource_path("you-got-a-devil-fruit-sound-gpo-made-with-Voicemod.mp3")

# Default coordinates for 1920x1080 (will be scaled to user's resolution)
# Only AREA configurations are set by default to match current user optimized settings
DEFAULT_COORDS_1920x1080 = {
    "area_coords": {"x": 1106, "y": 181, "width": 500, "height": 751},
    "auto_craft_area_coords": {"x": 1269, "y": -4, "width": 498, "height": 1092},
    # Smart Bait zones (1920x1080 optimized)
    "smart_bait_menu_zone": {"x": 834, "y": 782, "width": 250, "height": 110},
    "smart_bait_top_zone": {"x": 847, "y": 787, "width": 185, "height": 25},
    "smart_bait_mid_zone": {"x": 864, "y": 828, "width": 154, "height": 19},
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

# Global stats manager instance
stats_manager = None


class FishingMacroGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("BPS Fishing Macro")
        self.root.geometry("600x550")
        self.root.resizable(True, True)

        # Set window icon - Must be called AFTER geometry
        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "release", "icon.ico"
        )
        if os.path.exists(icon_path):
            try:
                self.root.wm_iconbitmap(icon_path)
            except:
                pass

        # CustomTkinter colors - V5.2 Darker Theme (reduced eye strain)
        self.bg_color = "#0d0d0d"  # Main background (darker)
        self.fg_color = "#f5f5f5"  # Text color (soft white, unchanged)
        self.accent_color = "#2d2d2d"  # Neutral accent (darker)
        self.button_color = "#1a1a1a"  # Button background (darker)
        self.hover_color = "#3d3d3d"  # Hover state (unchanged)

        # Status accent colors (only for confirmations)
        self.success_color = "#34d399"  # Green for success
        self.warning_color = "#fbbf24"  # Amber for warnings
        self.error_color = "#f87171"  # Red for errors

        # Legacy color dict for compatibility with .config() calls on some widgets
        self.current_colors = {
            "success": "#34d399",
            "error": "#f87171",
            "warning": "#fbbf24",
            "info": "#60a5fa",
            "accent": "#4a4a4a",
            "fg": "#f5f5f5",
            "bg": "#141414",
        }

        # Create default settings if file doesn't exist
        self.settings = SettingsManager(SETTINGS_FILE)

        # V5: Input controllers
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        self.window = WindowManager()

        # V5: Vision controllers
        self.screen = ScreenCapture(SCREEN_WIDTH, SCREEN_HEIGHT, REF_WIDTH, REF_HEIGHT)
        self.color_detector = ColorDetector()
        self.ocr = OCRService()
        self.anti_macro = AntiMacroDetector()

        # Dark mode flag (always True with customtkinter)
        self.dark_mode = True

        # Load settings
        self.always_on_top = self.settings.load_always_on_top()

        # V5.2: Pre-load Discord settings for GUI
        discord_rpc_settings = self.settings.load_discord_rpc_settings()
        self.discord_rpc_enabled = discord_rpc_settings.get("enabled", False)

        discord_bot_settings = self.settings.load_discord_bot_settings()
        self.discord_bot_enabled = discord_bot_settings.get("enabled", False)
        self.discord_bot_app_id = discord_bot_settings.get("application_id", "")
        self.discord_bot_allowed_users = discord_bot_settings.get(
            "allowed_user_ids", []
        )
        self.discord_bot_guild_id = discord_bot_settings.get("guild_id", "")
        self.discord_bot_auto_menu_channel = discord_bot_settings.get("auto_menu_channel_id", "")

        # Status variables
        self.running = False
        self.paused = False  # Pause state for F4 hotkey
        self.area_active = False
        self.is_rebinding = None
        self.area_selector = None
        self.area_coords = self.settings.load_area_coords()
        self.screen.set_scan_area(self.area_coords)  # Set default scan area
        self.water_point = self.settings.load_water_point()  # Water point coordinates
        self.selecting_water_point = False  # Flag for water point selection mode
        self.fruit_point = None  # Fruit detection coordinate
        self.fruit_color = None  # RGB color of fruit at fruit_point
        self.selecting_fruit_point = False  # Flag for fruit point selection mode

        # Auto craft variables
        auto_craft_settings = self.settings.load_auto_craft_settings()
        self.auto_craft_enabled = auto_craft_settings.get("auto_craft_enabled", False)
        self.auto_craft_area_active = False
        self.auto_craft_area_selector = None
        self.auto_craft_area_coords = self.settings.load_auto_craft_area_coords()
        self.screen.set_auto_craft_area(
            self.auto_craft_area_coords
        )  # Set auto craft area
        self.auto_craft_water_point = auto_craft_settings.get(
            "auto_craft_water_point", None
        )
        self.selecting_auto_craft_water_point = False

        # Auto craft configuration
        self.craft_every_n_fish = auto_craft_settings.get("craft_every_n_fish", 10)
        self.craft_menu_delay = auto_craft_settings.get("craft_menu_delay", 0.5)
        self.craft_click_speed = auto_craft_settings.get("craft_click_speed", 0.2)
        self.craft_legendary_quantity = auto_craft_settings.get(
            "craft_legendary_quantity", 1
        )
        self.craft_rare_quantity = auto_craft_settings.get("craft_rare_quantity", 1)
        self.craft_common_quantity = auto_craft_settings.get("craft_common_quantity", 1)

        # Auto craft coordinates
        self.craft_button_coords = auto_craft_settings.get("craft_button_coords", None)
        self.plus_button_coords = auto_craft_settings.get("plus_button_coords", None)
        self.fish_icon_coords = auto_craft_settings.get("fish_icon_coords", None)
        # Bait coordinates for CRAFTING (clicking slots in craft menu)
        self.legendary_bait_coords = auto_craft_settings.get(
            "legendary_bait_coords", None
        )
        self.rare_bait_coords = auto_craft_settings.get("rare_bait_coords", None)
        self.common_bait_coords = auto_craft_settings.get("common_bait_coords", None)
        # 2nd bait coordinate for FISHING (Smart Bait usage)
        self.smart_bait_2nd_coords = auto_craft_settings.get(
            "smart_bait_2nd_coords", None
        )
        self.selecting_auto_craft_coord = (
            None  # Track which coordinate is being selected
        )

        # V4: Smart Bait settings (OCR-based bait selection)
        smart_bait_settings = self.settings.load_smart_bait_settings()
        self.smart_bait_enabled = smart_bait_settings.get("enabled", False)
        self.smart_bait_mode = smart_bait_settings.get(
            "mode", "stockpile"
        )  # 'burning' or 'stockpile'
        self.smart_bait_legendary_target = smart_bait_settings.get(
            "legendary_target", 50
        )

        # Webhook legendary/mythical filter settings
        webhook_settings = self.settings.load_webhook_settings()
        self.webhook_only_legendary = webhook_settings.get("only_legendary", False)
        self.webhook_pity_zone = webhook_settings.get("pity_zone", None)
        self.selecting_pity_zone = False
        self.smart_bait_ocr_timeout = smart_bait_settings.get("ocr_timeout_ms", 500)
        self.smart_bait_ocr_confidence = smart_bait_settings.get(
            "ocr_confidence_min", 0.5
        )
        self.smart_bait_fallback = smart_bait_settings.get(
            "fallback_bait", "legendary"
        )  # 'legendary' or 'rare'
        self.smart_bait_debug = smart_bait_settings.get("debug_screenshots", False)
        self.smart_bait_use_ocr = smart_bait_settings.get(
            "use_ocr", True
        )  # True=OCR mode, False=Color-Only mode
        # OCR scan zone for full bait menu (x, y, width, height)
        self.smart_bait_menu_zone = smart_bait_settings.get("menu_zone", None)
        # Color-scan zones for top and mid bait labels
        self.smart_bait_top_zone = smart_bait_settings.get("top_bait_scan_zone", None)
        self.smart_bait_mid_zone = smart_bait_settings.get("mid_bait_scan_zone", None)
        self.selecting_smart_bait_zone = None  # Track which zone is being selected
        # UI labels for decision display (initialized in create_gui)
        self.smart_bait_mode_display = None
        self.smart_bait_decision_display = None
        self.hud_smart_bait_label = None

        # Casting settings
        casting_settings = self.settings.load_casting_settings()
        self.cast_hold_duration = casting_settings["cast_hold_duration"]
        self.recast_timeout = casting_settings["recast_timeout"]
        self.fishing_end_delay = casting_settings.get(
            "fishing_end_delay", 0.2
        )  # Minimum safe delay

        # Pre-cast settings
        precast_settings = self.settings.load_precast_settings()
        self.auto_buy_bait = precast_settings.get("auto_buy_bait", True)
        self.auto_store_fruit = precast_settings.get("auto_store_fruit", False)
        self.loops_per_purchase = precast_settings.get("loops_per_purchase", 100)
        self.yes_button = precast_settings.get("yes_button", None)
        self.middle_button = precast_settings.get("middle_button", None)
        self.no_button = precast_settings.get("no_button", None)
        self.selecting_button = None  # Track which button is being selected
        self.bait_loop_counter = 0  # Starts at 0 so first run executes immediately
        self.fruit_point = precast_settings.get(
            "fruit_point", None
        )  # Fruit detection coordinate
        self.fruit_color = precast_settings.get(
            "fruit_color", None
        )  # RGB color of fruit
        self.selecting_fruit_point = False  # Flag for fruit point selection mode
        self.auto_select_top_bait = precast_settings.get("auto_select_top_bait", False)
        self.top_bait_point = precast_settings.get("top_bait_point", None)
        self.selecting_top_bait_point = False

        # New: Store in inventory instead of dropping
        self.store_in_inventory = precast_settings.get("store_in_inventory", False)
        self.inventory_fruit_point = precast_settings.get("inventory_fruit_point", None)
        self.inventory_center_point = precast_settings.get(
            "inventory_center_point", None
        )
        self.selecting_inventory_fruit_point = False
        self.selecting_inventory_center_point = False

        # Default hotkeys
        self.hotkeys = {"start": "f1", "area": "f2", "exit": "f3", "pause": "f4"}

        # Item hotkeys (1-10 selectable)
        item_hotkeys = self.settings.load_item_hotkeys()
        self.rod_hotkey = item_hotkeys.get("rod", "1")
        self.everything_else_hotkey = item_hotkeys.get("everything_else", "2")
        self.fruit_hotkey = item_hotkeys.get("fruit", "3")

        self.listener = None
        self.main_thread = None

        # Statistics tracking
        self.start_time = None
        self.pause_start_time = None  # Track when pause started
        self.total_paused_time = 0.0  # Cumulative paused time
        self.fruits_caught = 0
        self.fish_caught = 0
        self.fish_at_last_fruit = 0
        self.hud_window = None
        self.first_run = True  # Flag to run initial scroll setup
        self.first_catch = True  # Flag to skip counting first catch after start
        self.current_status = "Idle"  # Current macro activity status
        self.status_lock = threading.Lock()  # Thread-safe status updates
        self.area_outline = None  # Green outline window during macro execution
        self.hud_position = (
            self.settings.load_hud_position()
        )  # HUD position: 'top', 'bottom-left', 'bottom-right'

        # V3: FPS tracking for detection rate
        self.detection_fps = 0.0  # Current detection FPS
        self.fps_frame_count = 0  # Frame counter for FPS calculation
        self.fps_last_time = time.time()  # Last time FPS was calculated

        # Cycle time tracking for mini HUD
        self.cycle_times = []  # List of recent cycle times (keep last 20)
        self.cycle_start_time = None  # Start time of current cycle
        self.average_cycle_time = 0.0  # Average cycle time in seconds

        # V3: Sound notification settings - load from file
        sound_settings = self.settings.load_sound_settings()
        self.sound_enabled = sound_settings.get("sound_enabled", True)
        self.sound_frequency = sound_settings.get(
            "sound_frequency", 400
        )  # Lower frequency is softer
        self.sound_duration = sound_settings.get(
            "sound_duration", 150
        )  # Shorter duration is less annoying

        # V3: Daily summary tracking
        self.session_start_date = datetime.now().date()
        self.daily_fish = 0
        self.daily_fruits = 0

        # Mouse control constants
        self.mouse_pressed = False  # Track mouse state

        # V4 Performance: Color detection cache (avoid re-detecting same frame)
        self._color_cache_result = None
        self._color_cache_time = 0
        self._color_cache_ttl = 0.5  # 500ms cache (max 2 detections/sec)

        # Advanced Timing Settings - load from settings FIRST (needed for disable_normal_camera)
        advanced_settings = self.settings.load_advanced_settings()

        # New: option to disable rotation/zoom/camera in normal mode
        self.disable_normal_camera = advanced_settings.get(
            "disable_normal_camera", False
        )
        self.detection_lost_counter = 0  # Counter for consecutive lost detections
        self.max_lost_frames = 10  # Max frames to keep last state before giving up

        # Resend mechanism to fix Roblox click bugs
        self.resend_interval = 0.5  # Default 500ms resend interval
        self.last_resend_time = 0.0  # Track last resend time

        # Continue loading advanced settings
        # Camera rotation delays
        self.camera_rotation_delay = advanced_settings.get(
            "camera_rotation_delay", 0.01
        )
        self.camera_rotation_steps = advanced_settings.get("camera_rotation_steps", 6)
        self.camera_rotation_step_delay = advanced_settings.get(
            "camera_rotation_step_delay", 0.01
        )
        self.camera_rotation_settle_delay = advanced_settings.get(
            "camera_rotation_settle_delay", 0.05
        )
        # Zoom delays
        self.zoom_ticks = advanced_settings.get("zoom_ticks", 3)
        self.zoom_tick_delay = advanced_settings.get("zoom_tick_delay", 0.01)
        self.zoom_settle_delay = advanced_settings.get("zoom_settle_delay", 0.05)
        # Pre-cast delays
        self.pre_cast_minigame_wait = advanced_settings.get(
            "pre_cast_minigame_wait", 0.2
        )
        self.store_click_delay = advanced_settings.get("store_click_delay", 0.1)
        self.backspace_delay = advanced_settings.get("backspace_delay", 0.05)
        self.rod_deselect_delay = advanced_settings.get("rod_deselect_delay", 0.05)
        self.rod_select_delay = advanced_settings.get("rod_select_delay", 0.05)
        self.bait_click_delay = advanced_settings.get("bait_click_delay", 0.05)
        # Detection & general delays
        self.fruit_detection_delay = advanced_settings.get(
            "fruit_detection_delay", 0.01
        )
        self.fruit_detection_settle = advanced_settings.get(
            "fruit_detection_settle", 0.05
        )
        self.general_action_delay = advanced_settings.get("general_action_delay", 0.01)
        self.mouse_move_settle = advanced_settings.get("mouse_move_settle", 0.01)
        # Focus settle delay after bringing Roblox to foreground
        self.focus_settle_delay = advanced_settings.get("focus_settle_delay", 0.1)
        # Delay after pressing fruit hotkey before checking/storing (wait for held animation)
        self.fruit_hold_delay = advanced_settings.get("fruit_hold_delay", 0.1)

        # PID controller variables - load from settings
        pid_settings = self.settings.load_pid_settings()
        self.pid_kp = pid_settings.get("kp", 1.0)
        self.pid_kd = pid_settings.get("kd", 0.3)
        self.pid_clamp = pid_settings.get("clamp", 1.0)
        self.pid_last_error = 0.0
        self.pid_last_time = time.time()

        # ============================================================
        # PHASE 5 & 6: Automation Modules Integration
        # ============================================================
        # Create automation modules (Phase 5) with dependency injection
        # These will be used by FishingCycle (Phase 6)

        # Phase 5.1: BaitManager - Smart Bait selection with OCR/Color detection
        bait_vision = SimpleNamespace(
            screen=self.screen, ocr=self.ocr, color_detector=self.color_detector
        )
        bait_settings = {
            "enabled": self.smart_bait_enabled,
            "mode": self.smart_bait_mode,
            "legendary_target": self.smart_bait_legendary_target,
            "ocr_timeout_ms": self.smart_bait_ocr_timeout,
            "ocr_confidence_min": self.smart_bait_ocr_confidence,
            "fallback_bait": self.smart_bait_fallback,
            "debug_screenshots": self.smart_bait_debug,
            "use_ocr": self.smart_bait_use_ocr,
            "menu_zone": self.smart_bait_menu_zone,
            "top_bait_scan_zone": self.smart_bait_top_zone,
            "mid_bait_scan_zone": self.smart_bait_mid_zone,
            "top_bait_point": self.top_bait_point,
            "smart_bait_2nd_coords": self.smart_bait_2nd_coords,
        }
        # BaitManager callbacks will be added after create_gui() since UI labels are needed
        self._bait_manager_vision = bait_vision
        self._bait_manager_settings = bait_settings

        # Phase 5.2: FruitHandler - Fruit detection and webhook notifications
        fruit_vision = SimpleNamespace(
            screen=self.screen, ocr=self.ocr, color_detector=self.color_detector
        )
        fruit_input = SimpleNamespace(mouse=self.mouse, keyboard=self.keyboard)
        fruit_settings = {
            "fruit_point": self.fruit_point,
            "fruit_color": self.fruit_color,
            "store_in_inventory": self.store_in_inventory,
            "inventory_fruit_point": self.inventory_fruit_point,
            "inventory_center_point": self.inventory_center_point,
            "use_store_keybind": False,  # Not implemented yet
            "store_keybind": "f",
            "webhook_only_legendary": self.webhook_only_legendary,
            "webhook_pity_zone": self.webhook_pity_zone,
            "store_click_delay": self.store_click_delay,
            "backspace_delay": self.backspace_delay,
            "zoom_tick_delay": self.zoom_tick_delay,
            "zoom_settle_delay": self.zoom_settle_delay,
        }
        # FruitHandler callbacks will be added after create_gui()
        self._fruit_handler_vision = fruit_vision
        self._fruit_handler_input = fruit_input
        self._fruit_handler_settings = fruit_settings

        # Phase 5.3: CraftAutomation - Automated bait crafting sequences
        craft_input = SimpleNamespace(mouse=self.mouse, keyboard=self.keyboard)
        craft_settings = {
            "craft_common_quantity": self.craft_common_quantity,
            "craft_rare_quantity": self.craft_rare_quantity,
            "craft_legendary_quantity": self.craft_legendary_quantity,
            "common_bait_coords": self.common_bait_coords,
            "rare_bait_coords": self.rare_bait_coords,
            "legendary_bait_coords": self.legendary_bait_coords,
            "plus_button_coords": self.plus_button_coords,
            "fish_icon_coords": self.fish_icon_coords,
            "craft_button_coords": self.craft_button_coords,
            "rod_hotkey": self.rod_hotkey,
            "craft_menu_delay": 0.5,  # Default from CraftAutomation
            "craft_click_speed": 0.1,  # Default from CraftAutomation
        }
        # CraftAutomation callbacks - minimal dependencies
        craft_callbacks = {
            "interruptible_sleep": self.interruptible_sleep,
            "is_running": lambda: self.running,
        }
        self.craft_automation = CraftAutomation(
            craft_input, craft_settings, craft_callbacks
        )

        # Phase 6: FishingCycle - will be created after create_gui() since callbacks need UI
        self._fishing_cycle = None  # Placeholder, created after GUI

        self.create_gui()
        # Sync checkbox var if it exists
        if hasattr(self, "disable_normal_camera_var"):
            self.disable_normal_camera_var.set(self.disable_normal_camera)
        self.setup_hotkeys()

        # ============================================================
        # PHASE 5 & 6: Finalize Automation Modules (after GUI created)
        # ============================================================
        self._init_automation_modules()

        # ============================================================
        # PHASE 8: Initialize Service Instances
        # ============================================================
        self.audio_service = AudioService(
            audio_file=AUDIO_FILE,
            sound_enabled=self.sound_enabled,
            sound_frequency=self.sound_frequency,
            sound_duration=self.sound_duration,
        )

        self.webhook_service = WebhookService(
            webhook_url=(
                self.webhook_url_entry.get()
                if hasattr(self, "webhook_url_entry")
                else ""
            ),
            user_id=self.user_id_entry.get() if hasattr(self, "user_id_entry") else "",
            only_legendary=self.webhook_only_legendary,
            pity_zone=self.webhook_pity_zone,
            ocr_checker=self.check_legendary_pity_ocr,
        )

        # V5.2: Discord Rich Presence Service
        discord_rpc_settings = self.settings.load_discord_rpc_settings()
        self.discord_rpc_enabled = discord_rpc_settings.get("enabled", False)
        self.rpc_service = None  # Initialized only if enabled
        if self.discord_rpc_enabled:
            self.rpc_service = RichPresenceService(logger=logger)
            logger.info("Discord Rich Presence enabled")
            # Update RPC status label (starts when macro starts)
            self.root.after(
                500,
                lambda: (
                    self.rpc_status_label.configure(
                        text="🟡 Ready (starts with macro)", text_color="#ffaa00"
                    )
                    if hasattr(self, "rpc_status_label")
                    else None
                ),
            )
        else:
            logger.debug("Discord Rich Presence disabled in settings")

        # V5.2: Discord Bot Service (Remote Control)
        from utils.token_encryption import decrypt_token

        discord_bot_settings = self.settings.load_discord_bot_settings()
        self.discord_bot_enabled = discord_bot_settings.get("enabled", False)
        self.discord_bot_app_id = discord_bot_settings.get("application_id", "")
        encrypted_token = discord_bot_settings.get("bot_token", "")
        self.discord_bot_allowed_users = discord_bot_settings.get(
            "allowed_user_ids", []
        )
        self.bot_service = None
        self.bot_command_queue = Queue()  # Thread-safe command queue

        if self.discord_bot_enabled and encrypted_token and self.discord_bot_app_id:
            try:
                # Decrypt token
                bot_token = decrypt_token(encrypted_token)

                # Initialize bot service
                self.bot_service = DiscordBotService(
                    bot_token=bot_token,
                    allowed_user_ids=self.discord_bot_allowed_users,
                    command_queue=self.bot_command_queue,
                    logger=logger,
                    command_prefix="!",
                )
                # Auto-start bot if enabled in settings
                self.bot_service.start()
                logger.info(
                    f"Discord Bot initialized and started (users: {len(self.discord_bot_allowed_users)})"
                )
                # Update bot status label after GUI is ready
                self.root.after(
                    2000,
                    lambda: (
                        self.bot_status_label.configure(
                            text="🟢 Online", text_color="#00dd00"
                        )
                        if hasattr(self, "bot_status_label")
                        and self.bot_service
                        and self.bot_service.is_running()
                        else None
                    ),
                )
            except Exception as e:
                logger.error(f"[BOT] Failed to initialize: {e}")
                self.bot_service = None
        else:
            logger.debug("Discord Bot disabled in settings")

        # Start bot command processor (GUI thread polling)
        self._process_bot_commands()

        # Print screen resolution info
        logger.info(f"=== BPS Fishing Macro V3 ===")
        logger.info(f"Screen Resolution: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
        logger.info(f"Reference Resolution: {REF_WIDTH}x{REF_HEIGHT}")
        if SCREEN_WIDTH != REF_WIDTH or SCREEN_HEIGHT != REF_HEIGHT:
            scale_x = SCREEN_WIDTH / REF_WIDTH
            scale_y = SCREEN_HEIGHT / REF_HEIGHT
            logger.warning(
                f"Coordinates scaled by {scale_x:.2f}x (horizontal) and {scale_y:.2f}x (vertical)"
            )
        else:
            logger.info(f"OK: Using native {REF_WIDTH}x{REF_HEIGHT} coordinates")

        # Apply always on top if loaded from settings
        if self.always_on_top:
            self.root.attributes("-topmost", True)

        # V5.2: GUI Thread Watchdog — detects freezes and dumps thread stacks
        self.watchdog = GUIWatchdog(self.root, freeze_threshold=3.0, check_interval=2.0)
        self.watchdog.start()
        logger.info("[INIT] GUI Watchdog armed (3s threshold)")

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def interruptible_sleep(self, duration):
        """Sleep that can be interrupted by setting self.running to False or self.paused to True"""
        from utils.timing import (
            interruptible_sleep_with_pause as _interruptible_sleep_with_pause,
        )

        return _interruptible_sleep_with_pause(
            duration, lambda: self.running, lambda: self.paused
        )

    def set_status(self, status):
        """Thread-safe status update"""
        with self.status_lock:
            self.current_status = status

    def _increment_fish_caught_with_rpc(self):
        """Increment fish count and update Discord RPC (V5.2)"""
        self.fish_caught += 1
        self._update_rpc_stats()

    def _increment_fruits_caught_with_rpc(self):
        """Increment fruit count and update Discord RPC (V5.2)"""
        self.fruits_caught += 1
        self._update_rpc_stats()

    def _update_rpc_stats(self):
        """Update Discord Rich Presence with current stats (non-blocking)"""
        if self.rpc_service and self.running:
            # Calculate runtime and stats
            runtime = self.get_runtime()
            total_catches = self.fish_caught + self.fruits_caught

            # Calculate hourly rate
            if self.start_time:
                elapsed_hours = (
                    time.time() - self.start_time - self.total_paused_time
                ) / 3600
                hourly_rate = (
                    int(total_catches / elapsed_hours) if elapsed_hours > 0 else 0
                )
            else:
                hourly_rate = 0

            # Get current state
            current_state = "Active" if self.running else "Stopped"
            if hasattr(self, "paused") and self.paused:
                current_state = "Paused"

            # Format state with runtime
            state = f"{current_state} | Runtime: {runtime}"

            # Format details with catches and hourly rate
            details = (
                f"🐟 {self.fish_caught} | 🍇 {self.fruits_caught} | ⚡ {hourly_rate}/hr"
            )

            # Update presence (non-blocking, runs in background thread)
            logger.debug(f"[RPC] Updating presence: {state} - {details}")
            self.rpc_service.update_presence(
                state=state,
                details=details,
                start_timestamp=int(self.start_time) if self.start_time else None,
            )

    def get_runtime(self):
        """Get formatted runtime string (HH:MM:SS) excluding paused time"""
        if self.start_time is None:
            return "00:00:00"

        # Calculate elapsed time excluding paused time
        current_time = time.time()
        elapsed = current_time - self.start_time - self.total_paused_time

        # If currently paused, don't include current pause duration yet
        if self.paused and self.pause_start_time:
            # Already excluded via total_paused_time being updated in toggle_pause
            pass

        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _process_bot_commands(self):
        """Process Discord bot commands on GUI thread (polling loop)"""
        try:
            # Process all pending commands (non-blocking)
            while not self.bot_command_queue.empty():
                cmd_data = self.bot_command_queue.get_nowait()
                self._execute_bot_command(cmd_data)
        except Exception as e:
            logger.error(f"[BOT] Error processing commands: {e}")

        # Schedule next poll (every 500ms)
        self.root.after(500, self._process_bot_commands)

    def _execute_bot_command(self, cmd_data):
        """Execute a bot command on GUI thread"""
        command = cmd_data.get("command")
        channel_id = cmd_data.get("channel_id")
        author_name = cmd_data.get("author_name", "Unknown")

        logger.info(f"[BOT] Executing command: {command} from {author_name}")

        try:
            if command == "start":
                if not self.running:
                    # Use the proper start method to ensure all initialization
                    self._actually_start_macro()

                    if self.running:
                        self._send_bot_response(
                            channel_id, f"✅ **Macro started by {author_name}**"
                        )
                    else:
                        self._send_bot_response(
                            channel_id, "❌ **Failed to start macro**"
                        )
                else:
                    self._send_bot_response(
                        channel_id, "⚠️ **Macro is already running**"
                    )

            elif command == "stop":
                if self.running:
                    # Use the proper stop method to ensure full cleanup
                    self._actually_stop_macro()

                    self._send_bot_response(
                        channel_id, f"⏹️ **Macro stopped by {author_name}**"
                    )
                else:
                    self._send_bot_response(channel_id, "⚠️ **Macro is not running**")

            elif command == "status":
                # Status now shows detailed stats (same as !stats)
                stats_msg = self._get_detailed_stats()
                self._send_bot_response(channel_id, stats_msg)

            elif command == "screenshot":
                self._take_and_send_screenshot(channel_id)

            elif command == "pause":
                if self.running and not self.paused:
                    self.toggle_pause()
                    self._send_bot_response(
                        channel_id, f"⏸️ **Macro paused by {author_name}**"
                    )
                elif self.paused:
                    self._send_bot_response(channel_id, "⚠️ **Already paused**")
                else:
                    self._send_bot_response(channel_id, "⚠️ **Macro is not running**")

            elif command == "resume":
                if self.running and self.paused:
                    self.toggle_pause()
                    self._send_bot_response(
                        channel_id, f"▶️ **Macro resumed by {author_name}**"
                    )
                elif not self.paused:
                    self._send_bot_response(channel_id, "⚠️ **Macro is not paused**")
                else:
                    self._send_bot_response(channel_id, "⚠️ **Macro is not running**")

            elif command == "restart":
                self._send_bot_response(
                    channel_id, f"🔄 **Restarting macro requested by {author_name}...**"
                )
                if self.running:
                    self._actually_stop_macro()
                    time.sleep(2)  # Wait for clean shutdown
                self._actually_start_macro()
                if self.running:
                    self._send_bot_response(
                        channel_id, "✅ **Macro restarted successfully!**"
                    )
                else:
                    self._send_bot_response(
                        channel_id, "❌ **Restart failed - check logs**"
                    )

            elif command == "debug":
                action = cmd_data.get("action", "help")
                self._handle_debug_command(channel_id, author_name, action)

            elif command == "menu":
                self._send_interactive_menu(channel_id)

            else:
                logger.warning(f"[BOT] Unknown command: {command}")

        except Exception as e:
            logger.error(f"[BOT] Error executing command {command}: {e}")
            self._send_bot_response(channel_id, f"❌ **Error executing command:** {e}")

    def _get_status_embed(self) -> str:
        """Generate status message for Discord"""
        runtime = self.get_runtime()
        state = "🟢 RUNNING" if self.running else "🔴 STOPPED"
        pause_state = " (⏸️ PAUSED)" if self.paused else ""

        # Calculate hourly rate
        total_catches = self.fish_caught + self.fruits_caught
        if self.start_time:
            elapsed_hours = (
                time.time() - self.start_time - self.total_paused_time
            ) / 3600
            hourly_rate = int(total_catches / elapsed_hours) if elapsed_hours > 0 else 0
        else:
            hourly_rate = 0

        # Get engine state
        engine_state = str(self.engine._state) if hasattr(self, "engine") else "N/A"

        status_msg = f"""**📊 BPS Fishing Macro**

**State:** {state}{pause_state}
**Engine:** {engine_state}
**Runtime:** {runtime}

**📈 Statistics:**
🐟 Fish: {self.fish_caught}
🍇 Fruits: {self.fruits_caught}
📦 Total: {total_catches}
⚡ Rate: {hourly_rate}/hr

**⚙️ Active Features:**
{"✅" if self.auto_craft_enabled else "❌"} Auto-Craft
{"✅" if self.smart_bait_enabled else "❌"} Smart Bait {f"({self.smart_bait_mode})" if self.smart_bait_enabled else ""}
{"✅" if self.anti_afk_enabled else "❌"} Anti-AFK
{"✅" if self.webhook_enabled else "❌"} Webhook Alerts
{"✅" if self.rpc_service and self.discord_rpc_enabled else "❌"} Rich Presence
"""
        return status_msg

    def _get_detailed_stats(self) -> str:
        """Generate detailed statistics message for Discord !stats command"""
        global stats_manager

        runtime = self.get_runtime()
        state = "🟢 RUNNING" if self.running else "🔴 STOPPED"
        pause_state = " (⏸️ PAUSED)" if self.paused else ""

        # Current session stats
        total_catches = self.fish_caught + self.fruits_caught
        if self.start_time:
            elapsed_hours = (
                time.time() - self.start_time - self.total_paused_time
            ) / 3600
            fish_rate = (
                int(self.fish_caught / elapsed_hours) if elapsed_hours > 0 else 0
            )
            fruit_rate = (
                int(self.fruits_caught / elapsed_hours) if elapsed_hours > 0 else 0
            )
        else:
            fish_rate = 0
            fruit_rate = 0

        # Database stats (today & all-time)
        today_fish = 0
        today_fruits = 0
        total_fish = 0
        total_fruits = 0
        total_sessions = 0

        if stats_manager:
            try:
                today = stats_manager.get_today_summary()
                today_fish = today.get("fish", 0)
                today_fruits = today.get("fruits", 0)

                alltime = stats_manager.get_alltime_summary()
                total_fish = alltime.get("fish", 0)
                total_fruits = alltime.get("fruits", 0)
                total_sessions = alltime.get("sessions", 0)
            except Exception:
                pass

        stats_msg = f"""**📊 DETAILED STATISTICS**

**Current Session:** {state}{pause_state}
⏱️ Runtime: {runtime}
🐟 Fish: {self.fish_caught} ({fish_rate}/hr)
🍇 Fruits: {self.fruits_caught} ({fruit_rate}/hr)
📦 Total: {total_catches}

**Today's Summary:**
🐟 Fish: {today_fish}
🍇 Fruits: {today_fruits}
📦 Total: {today_fish + today_fruits}

**All-Time Records:**
📅 Sessions: {total_sessions}
🐟 Fish: {total_fish}
🍇 Fruits: {total_fruits}
📦 Total: {total_fish + total_fruits}

**Performance:**
⚡ Avg cycle: {self.average_cycle_time:.1f}s
🎣 Total casts: {len(self.cycle_times) if hasattr(self, 'cycle_times') else 0}
"""
        return stats_msg

    def _take_and_send_screenshot(self, channel_id: int):
        """Capture game window and send to Discord"""
        try:
            import tempfile
            from pathlib import Path

            # Get game window handle
            hwnd = self.window.find_window()
            if not hwnd:
                self._send_bot_response(channel_id, "❌ **Game window not found**")
                return

            # Capture window
            screenshot = self.screen.capture_window(hwnd)
            if screenshot is None:
                self._send_bot_response(
                    channel_id, "❌ **Failed to capture screenshot**"
                )
                return

            # Save to temp file
            temp_dir = Path(tempfile.gettempdir())
            screenshot_path = temp_dir / f"bps_screenshot_{int(time.time())}.png"

            import cv2

            cv2.imwrite(str(screenshot_path), screenshot)

            # Send file
            if self.bot_service and self.bot_service.is_running():
                # Schedule async send in bot's event loop
                loop = self.bot_service.bot.loop
                if loop:
                    asyncio.run_coroutine_threadsafe(
                        self.bot_service.send_file(
                            channel_id, str(screenshot_path), "📸 **Game Screenshot**"
                        ),
                        loop,
                    )
                    logger.info(f"[BOT] Screenshot sent to channel {channel_id}")

        except Exception as e:
            logger.error(f"[BOT] Screenshot error: {e}")
            self._send_bot_response(channel_id, f"❌ **Screenshot failed:** {e}")

    def _send_bot_response(self, channel_id: int, message: str):
        """Send response message to Discord channel"""
        if self.bot_service and self.bot_service.is_running():
            try:
                # Schedule async send in bot's event loop
                loop = self.bot_service.bot.loop
                if loop:
                    asyncio.run_coroutine_threadsafe(
                        self.bot_service.send_message(channel_id, message), loop
                    )
            except Exception as e:
                logger.error(f"[BOT] Failed to send response: {e}")

    def _handle_debug_command(self, channel_id: int, author_name: str, action: str):
        """Handle debug command actions"""
        try:
            if action == "logs":
                # Send last 50 lines from logging service
                log_file = os.path.join(BASE_DIR, "fishing_macro.log")
                if os.path.exists(log_file):
                    with open(log_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        last_50 = "".join(lines[-50:])
                        # Discord has 2000 char limit per message
                        if len(last_50) > 1900:
                            last_50 = last_50[-1900:]
                        self._send_bot_response(channel_id, f"```\n{last_50}\n```")
                else:
                    self._send_bot_response(channel_id, "❌ **Log file not found**")

            elif action == "watchdog":
                # Send watchdog file
                watchdog_file = os.path.join(BASE_DIR, "debug_watchdog.txt")
                if os.path.exists(watchdog_file):
                    loop = self.bot_service.bot.loop
                    if loop:
                        asyncio.run_coroutine_threadsafe(
                            self.bot_service.send_file(
                                channel_id,
                                watchdog_file,
                                f"🐕 **Watchdog diagnostic file from {author_name}**",
                            ),
                            loop,
                        )
                else:
                    self._send_bot_response(
                        channel_id,
                        "❌ **Watchdog file not found (no freezes detected)**",
                    )

            elif action == "on":
                # Enable DEBUG logging
                logging.getLogger().setLevel(logging.DEBUG)
                self._send_bot_response(channel_id, "✅ **DEBUG logging enabled**")
                logger.debug(f"[BOT] Debug mode enabled by {author_name}")

            elif action == "off":
                # Disable DEBUG logging
                logging.getLogger().setLevel(logging.INFO)
                self._send_bot_response(
                    channel_id, "✅ **DEBUG logging disabled (INFO level)**"
                )
                logger.info(f"[BOT] Debug mode disabled by {author_name}")

            else:
                self._send_bot_response(
                    channel_id,
                    "❌ **Unknown debug action.** Use: `logs`, `watchdog`, `on`, `off`",
                )

        except Exception as e:
            logger.error(f"[BOT] Debug command error: {e}")
            self._send_bot_response(channel_id, f"❌ **Debug error:** {e}")

    async def _send_discord_menu(self, channel_id: int):
        """
        Async method to send interactive menu to a specific Discord channel.
        Can be called from bot service (on_ready) or from command handler.
        
        Args:
            channel_id: Discord channel ID where menu should be sent
        """
        import discord
        import tempfile
        from pathlib import Path
        import time

        try:
            # Capture screenshot first
            screenshot_file = None
            hwnd = self.window.find_window()
            if hwnd:
                screenshot = self.screen.capture_window(hwnd)
                if screenshot is not None:
                    import cv2

                    temp_dir = Path(tempfile.gettempdir())
                    screenshot_path = (
                        temp_dir / f"menu_screenshot_{int(time.time())}.png"
                    )
                    cv2.imwrite(str(screenshot_path), screenshot)
                    screenshot_file = str(screenshot_path)

            # Create embed with live stats
            runtime = self.get_runtime()
            state_emoji = "🟢" if self.running else "🔴"
            state_text = "RUNNING" if self.running else "STOPPED"
            if self.paused:
                state_emoji = "⏸️"
                state_text = "PAUSED"

            # Calculate stats
            total_catches = self.fish_caught + self.fruits_caught
            if self.start_time:
                elapsed_hours = (
                    time.time() - self.start_time - self.total_paused_time
                ) / 3600
                hourly_rate = (
                    int(total_catches / elapsed_hours) if elapsed_hours > 0 else 0
                )
            else:
                hourly_rate = 0

            # Create embed
            embed = discord.Embed(
                title="🎣 BPS Fishing Macro — Control Panel",
                description=f"**Status:** {state_emoji} {state_text}",
                color=(
                    0x00FF00
                    if self.running and not self.paused
                    else (0xFFAA00 if self.paused else 0xFF0000)
                ),
            )

            embed.add_field(name="⏱️ Runtime", value=runtime, inline=True)
            embed.add_field(name="🐟 Fish", value=str(self.fish_caught), inline=True)
            embed.add_field(
                name="🍇 Fruits", value=str(self.fruits_caught), inline=True
            )

            embed.add_field(name="📦 Total", value=str(total_catches), inline=True)
            embed.add_field(name="⚡ Rate", value=f"{hourly_rate}/hr", inline=True)
            embed.add_field(
                name="🔧 Engine",
                value=str(self.engine._state) if hasattr(self, "engine") else "N/A",
                inline=True,
            )

            # Set screenshot as image if captured
            if screenshot_file:
                embed.set_image(url="attachment://screenshot.png")

            embed.set_footer(
                text="Use buttons below to control | Click Refresh to update stats + screenshot"
            )

            # Create view with buttons
            class MacroMenuView(discord.ui.View):
                def __init__(self, app):
                    super().__init__(timeout=300)  # 5 min timeout
                    self.app = app

                @discord.ui.button(
                    label="▶️ Start",
                    style=discord.ButtonStyle.green,
                    custom_id="btn_start",
                )
                async def start_btn(
                    self, interaction: discord.Interaction, button: discord.ui.Button
                ):
                    # Whitelist check
                    if interaction.user.id not in self.app.bot_service.allowed_user_ids:
                        await interaction.response.send_message(
                            "❌ **Access denied:** You are not authorized to control this macro.",
                            ephemeral=True
                        )
                        return

                    await interaction.response.defer()
                    self.app.bot_service.command_queue.put(
                        {
                            "command": "start",
                            "channel_id": interaction.channel_id,
                            "author_name": str(interaction.user),
                        }
                    )
                    await interaction.followup.send(
                        "🎣 **Starting macro...**", ephemeral=True
                    )

                @discord.ui.button(
                    label="⏹️ Stop", style=discord.ButtonStyle.red, custom_id="btn_stop"
                )
                async def stop_btn(
                    self, interaction: discord.Interaction, button: discord.ui.Button
                ):
                    # Whitelist check
                    if interaction.user.id not in self.app.bot_service.allowed_user_ids:
                        await interaction.response.send_message(
                            "❌ **Access denied:** You are not authorized to control this macro.",
                            ephemeral=True
                        )
                        return

                    await interaction.response.defer()
                    self.app.bot_service.command_queue.put(
                        {
                            "command": "stop",
                            "channel_id": interaction.channel_id,
                            "author_name": str(interaction.user),
                        }
                    )
                    await interaction.followup.send(
                        "⏹️ **Stopping macro...**", ephemeral=True
                    )

                @discord.ui.button(
                    label="⏸️ Pause",
                    style=discord.ButtonStyle.blurple,
                    custom_id="btn_pause",
                )
                async def pause_btn(
                    self, interaction: discord.Interaction, button: discord.ui.Button
                ):
                    # Whitelist check
                    if interaction.user.id not in self.app.bot_service.allowed_user_ids:
                        await interaction.response.send_message(
                            "❌ **Access denied:** You are not authorized to control this macro.",
                            ephemeral=True
                        )
                        return

                    await interaction.response.defer()
                    self.app.bot_service.command_queue.put(
                        {
                            "command": "pause",
                            "channel_id": interaction.channel_id,
                            "author_name": str(interaction.user),
                        }
                    )
                    await interaction.followup.send(
                        "⏸️ **Pausing macro...**", ephemeral=True
                    )

                @discord.ui.button(
                    label="▶️ Resume",
                    style=discord.ButtonStyle.blurple,
                    custom_id="btn_resume",
                )
                async def resume_btn(
                    self, interaction: discord.Interaction, button: discord.ui.Button
                ):
                    # Whitelist check
                    if interaction.user.id not in self.app.bot_service.allowed_user_ids:
                        await interaction.response.send_message(
                            "❌ **Access denied:** You are not authorized to control this macro.",
                            ephemeral=True
                        )
                        return

                    await interaction.response.defer()
                    self.app.bot_service.command_queue.put(
                        {
                            "command": "resume",
                            "channel_id": interaction.channel_id,
                            "author_name": str(interaction.user),
                        }
                    )
                    await interaction.followup.send(
                        "▶️ **Resuming macro...**", ephemeral=True
                    )

                @discord.ui.button(
                    label="🔁 Restart",
                    style=discord.ButtonStyle.danger,
                    custom_id="btn_restart",
                )
                async def restart_btn(
                    self, interaction: discord.Interaction, button: discord.ui.Button
                ):
                    # Whitelist check
                    if interaction.user.id not in self.app.bot_service.allowed_user_ids:
                        await interaction.response.send_message(
                            "❌ **Access denied:** You are not authorized to control this macro.",
                            ephemeral=True
                        )
                        return

                    await interaction.response.defer()
                    self.app.bot_service.command_queue.put(
                        {
                            "command": "restart",
                            "channel_id": interaction.channel_id,
                            "author_name": str(interaction.user),
                        }
                    )
                    await interaction.followup.send(
                        "🔁 **Restarting macro...**", ephemeral=True
                    )

                @discord.ui.button(
                    label="🔄 Refresh",
                    style=discord.ButtonStyle.gray,
                    custom_id="btn_refresh",
                )
                async def refresh_btn(
                    self, interaction: discord.Interaction, button: discord.ui.Button
                ):
                    # Whitelist check
                    if interaction.user.id not in self.app.bot_service.allowed_user_ids:
                        await interaction.response.send_message(
                            "❌ **Access denied:** You are not authorized to control this macro.",
                            ephemeral=True
                        )
                        return

                    await interaction.response.defer()

                    try:
                        # Capture fresh screenshot
                        screenshot_file = None
                        hwnd = self.app.window.find_window()
                        if hwnd:
                            screenshot = self.app.screen.capture_window(hwnd)
                            if screenshot is not None:
                                import cv2

                                temp_dir = Path(tempfile.gettempdir())
                                screenshot_path = (
                                    temp_dir / f"menu_screenshot_{int(time.time())}.png"
                                )
                                cv2.imwrite(str(screenshot_path), screenshot)
                                screenshot_file = str(screenshot_path)

                        # Get fresh stats
                        runtime = self.app.get_runtime()
                        state_emoji = "🟢" if self.app.running else "🔴"
                        state_text = "RUNNING" if self.app.running else "STOPPED"
                        if self.app.paused:
                            state_emoji = "⏸️"
                            state_text = "PAUSED"

                        total_catches = self.app.fish_caught + self.app.fruits_caught
                        if self.app.start_time:
                            elapsed_hours = (
                                time.time()
                                - self.app.start_time
                                - self.app.total_paused_time
                            ) / 3600
                            hourly_rate = (
                                int(total_catches / elapsed_hours)
                                if elapsed_hours > 0
                                else 0
                            )
                        else:
                            hourly_rate = 0

                        # Create new embed
                        new_embed = discord.Embed(
                            title=f"{state_emoji} BPS Fishing Macro Control Panel",
                            description=f"**Status:** {state_text}",
                            color=(
                                discord.Color.green()
                                if self.app.running
                                else discord.Color.red()
                            ),
                            timestamp=discord.utils.utcnow(),
                        )
                        new_embed.add_field(
                            name="⏱️ Runtime", value=runtime, inline=True
                        )
                        new_embed.add_field(
                            name="🐟 Fish", value=str(self.app.fish_caught), inline=True
                        )
                        new_embed.add_field(
                            name="🍇 Fruits",
                            value=str(self.app.fruits_caught),
                            inline=True,
                        )
                        new_embed.add_field(
                            name="📦 Total", value=str(total_catches), inline=True
                        )
                        new_embed.add_field(
                            name="⚡ Rate", value=f"{hourly_rate}/hr", inline=True
                        )
                        new_embed.add_field(
                            name="🔧 Engine",
                            value=(
                                str(self.app.engine._state)
                                if hasattr(self.app, "engine")
                                else "N/A"
                            ),
                            inline=True,
                        )

                        if screenshot_file:
                            new_embed.set_image(url="attachment://screenshot.png")

                        new_embed.set_footer(
                            text="Use buttons below to control | Click Refresh to update stats + screenshot"
                        )

                        # Edit the original message
                        if screenshot_file:
                            file_obj = discord.File(
                                screenshot_file, filename="screenshot.png"
                            )
                            await interaction.message.edit(
                                embed=new_embed, attachments=[file_obj], view=self
                            )
                        else:
                            await interaction.message.edit(embed=new_embed, view=self)

                        await interaction.followup.send(
                            "✅ **Refreshed!**", ephemeral=True
                        )

                    except Exception as e:
                        logger.error(f"[BOT] Refresh error: {e}")
                        await interaction.followup.send(
                            f"❌ **Refresh failed:** {e}", ephemeral=True
                        )

            # Create view and send menu
            view = MacroMenuView(self)
            channel = self.bot_service.bot.get_channel(channel_id)
            
            if channel:
                if screenshot_file:
                    file_obj = discord.File(screenshot_file, filename="screenshot.png")
                    await channel.send(embed=embed, file=file_obj, view=view)
                else:
                    await channel.send(embed=embed, view=view)
                print(f"[BOT] Menu sent successfully to channel {channel_id}")
            else:
                print(f"[BOT] ERROR: Channel {channel_id} not found")

        except Exception as e:
            print(f"[BOT] Error sending menu: {e}")
            import traceback
            traceback.print_exc()

    def _send_interactive_menu(self, channel_id: int):
        """Send interactive menu with buttons, live stats, and screenshot"""
        try:
            import discord
            import tempfile
            from pathlib import Path

            logger.info(f"[BOT] Menu - Starting for channel {channel_id}")
            logger.info(
                f"[BOT] Menu - bot_service exists: {self.bot_service is not None}"
            )
            if self.bot_service:
                logger.info(
                    f"[BOT] Menu - bot exists: {self.bot_service.bot is not None}"
                )
                logger.info(
                    f"[BOT] Menu - bot is_running: {self.bot_service.is_running()}"
                )
                if self.bot_service.bot:
                    logger.info(
                        f"[BOT] Menu - bot.loop exists: {self.bot_service.bot.loop is not None}"
                    )
                    if self.bot_service.bot.loop:
                        logger.info(
                            f"[BOT] Menu - bot.loop.is_running: {self.bot_service.bot.loop.is_running()}"
                        )

            # Capture screenshot first
            screenshot_file = None
            hwnd = self.window.find_window()
            if hwnd:
                screenshot = self.screen.capture_window(hwnd)
                if screenshot is not None:
                    import cv2

                    temp_dir = Path(tempfile.gettempdir())
                    screenshot_path = (
                        temp_dir / f"menu_screenshot_{int(time.time())}.png"
                    )
                    cv2.imwrite(str(screenshot_path), screenshot)
                    screenshot_file = str(screenshot_path)

            # Create embed with live stats
            runtime = self.get_runtime()
            state_emoji = "🟢" if self.running else "🔴"
            state_text = "RUNNING" if self.running else "STOPPED"
            if self.paused:
                state_emoji = "⏸️"
                state_text = "PAUSED"

            # Calculate stats
            total_catches = self.fish_caught + self.fruits_caught
            if self.start_time:
                elapsed_hours = (
                    time.time() - self.start_time - self.total_paused_time
                ) / 3600
                hourly_rate = (
                    int(total_catches / elapsed_hours) if elapsed_hours > 0 else 0
                )
            else:
                hourly_rate = 0

            # Create embed
            embed = discord.Embed(
                title="🎣 BPS Fishing Macro — Control Panel",
                description=f"**Status:** {state_emoji} {state_text}",
                color=(
                    0x00FF00
                    if self.running and not self.paused
                    else (0xFFAA00 if self.paused else 0xFF0000)
                ),
            )

            embed.add_field(name="⏱️ Runtime", value=runtime, inline=True)
            embed.add_field(name="🐟 Fish", value=str(self.fish_caught), inline=True)
            embed.add_field(
                name="🍇 Fruits", value=str(self.fruits_caught), inline=True
            )

            embed.add_field(name="📦 Total", value=str(total_catches), inline=True)
            embed.add_field(name="⚡ Rate", value=f"{hourly_rate}/hr", inline=True)
            embed.add_field(
                name="🔧 Engine",
                value=str(self.engine._state) if hasattr(self, "engine") else "N/A",
                inline=True,
            )

            # Set screenshot as image if captured
            if screenshot_file:
                embed.set_image(url="attachment://screenshot.png")

            embed.set_footer(
                text="Use buttons below to control | Click Refresh to update stats + screenshot"
            )

            # Create view with buttons
            class MacroMenuView(discord.ui.View):
                def __init__(self, app):
                    super().__init__(timeout=300)  # 5 min timeout
                    self.app = app

                @discord.ui.button(
                    label="▶️ Start",
                    style=discord.ButtonStyle.green,
                    custom_id="btn_start",
                )
                async def start_btn(
                    self, interaction: discord.Interaction, button: discord.ui.Button
                ):
                    # Whitelist check
                    if interaction.user.id not in self.app.bot_service.allowed_user_ids:
                        await interaction.response.send_message(
                            "❌ **Access denied:** You are not authorized to control this macro.",
                            ephemeral=True
                        )
                        return

                    await interaction.response.defer()
                    self.app.bot_service.command_queue.put(
                        {
                            "command": "start",
                            "channel_id": interaction.channel_id,
                            "author_name": str(interaction.user),
                        }
                    )
                    await interaction.followup.send(
                        "🎣 **Starting macro...**", ephemeral=True
                    )

                @discord.ui.button(
                    label="⏹️ Stop", style=discord.ButtonStyle.red, custom_id="btn_stop"
                )
                async def stop_btn(
                    self, interaction: discord.Interaction, button: discord.ui.Button
                ):
                    # Whitelist check
                    if interaction.user.id not in self.app.bot_service.allowed_user_ids:
                        await interaction.response.send_message(
                            "❌ **Access denied:** You are not authorized to control this macro.",
                            ephemeral=True
                        )
                        return

                    await interaction.response.defer()
                    self.app.bot_service.command_queue.put(
                        {
                            "command": "stop",
                            "channel_id": interaction.channel_id,
                            "author_name": str(interaction.user),
                        }
                    )
                    await interaction.followup.send(
                        "⏹️ **Stopping macro...**", ephemeral=True
                    )

                @discord.ui.button(
                    label="⏸️ Pause",
                    style=discord.ButtonStyle.blurple,
                    custom_id="btn_pause",
                )
                async def pause_btn(
                    self, interaction: discord.Interaction, button: discord.ui.Button
                ):
                    # Whitelist check
                    if interaction.user.id not in self.app.bot_service.allowed_user_ids:
                        await interaction.response.send_message(
                            "❌ **Access denied:** You are not authorized to control this macro.",
                            ephemeral=True
                        )
                        return

                    await interaction.response.defer()
                    self.app.bot_service.command_queue.put(
                        {
                            "command": "pause",
                            "channel_id": interaction.channel_id,
                            "author_name": str(interaction.user),
                        }
                    )
                    await interaction.followup.send(
                        "⏸️ **Pausing macro...**", ephemeral=True
                    )

                @discord.ui.button(
                    label="▶️ Resume",
                    style=discord.ButtonStyle.blurple,
                    custom_id="btn_resume",
                )
                async def resume_btn(
                    self, interaction: discord.Interaction, button: discord.ui.Button
                ):
                    # Whitelist check
                    if interaction.user.id not in self.app.bot_service.allowed_user_ids:
                        await interaction.response.send_message(
                            "❌ **Access denied:** You are not authorized to control this macro.",
                            ephemeral=True
                        )
                        return

                    await interaction.response.defer()
                    self.app.bot_service.command_queue.put(
                        {
                            "command": "resume",
                            "channel_id": interaction.channel_id,
                            "author_name": str(interaction.user),
                        }
                    )
                    await interaction.followup.send(
                        "▶️ **Resuming macro...**", ephemeral=True
                    )

                @discord.ui.button(
                    label="� Restart",
                    style=discord.ButtonStyle.danger,
                    custom_id="btn_restart",
                )
                async def restart_btn(
                    self, interaction: discord.Interaction, button: discord.ui.Button
                ):
                    # Whitelist check
                    if interaction.user.id not in self.app.bot_service.allowed_user_ids:
                        await interaction.response.send_message(
                            "❌ **Access denied:** You are not authorized to control this macro.",
                            ephemeral=True
                        )
                        return

                    await interaction.response.defer()
                    self.app.bot_service.command_queue.put(
                        {
                            "command": "restart",
                            "channel_id": interaction.channel_id,
                            "author_name": str(interaction.user),
                        }
                    )
                    await interaction.followup.send(
                        "🔁 **Restarting macro...**", ephemeral=True
                    )

                @discord.ui.button(
                    label="�🔄 Refresh",
                    style=discord.ButtonStyle.gray,
                    custom_id="btn_refresh",
                )
                async def refresh_btn(
                    self, interaction: discord.Interaction, button: discord.ui.Button
                ):
                    # Whitelist check
                    if interaction.user.id not in self.app.bot_service.allowed_user_ids:
                        await interaction.response.send_message(
                            "❌ **Access denied:** You are not authorized to control this macro.",
                            ephemeral=True
                        )
                        return

                    await interaction.response.defer()

                    try:
                        # Capture fresh screenshot
                        screenshot_file = None
                        hwnd = self.app.window.find_window()
                        if hwnd:
                            screenshot = self.app.screen.capture_window(hwnd)
                            if screenshot is not None:
                                import cv2

                                temp_dir = Path(tempfile.gettempdir())
                                screenshot_path = (
                                    temp_dir / f"menu_screenshot_{int(time.time())}.png"
                                )
                                cv2.imwrite(str(screenshot_path), screenshot)
                                screenshot_file = str(screenshot_path)

                        # Get fresh stats
                        runtime = self.app.get_runtime()
                        state_emoji = "🟢" if self.app.running else "🔴"
                        state_text = "RUNNING" if self.app.running else "STOPPED"
                        if self.app.paused:
                            state_emoji = "⏸️"
                            state_text = "PAUSED"

                        total_catches = self.app.fish_caught + self.app.fruits_caught
                        if self.app.start_time:
                            elapsed_hours = (
                                time.time()
                                - self.app.start_time
                                - self.app.total_paused_time
                            ) / 3600
                            hourly_rate = (
                                int(total_catches / elapsed_hours)
                                if elapsed_hours > 0
                                else 0
                            )
                        else:
                            hourly_rate = 0

                        # Create new embed
                        new_embed = discord.Embed(
                            title=f"{state_emoji} BPS Fishing Macro Control Panel",
                            description=f"**Status:** {state_text}",
                            color=(
                                discord.Color.green()
                                if self.app.running
                                else discord.Color.red()
                            ),
                            timestamp=discord.utils.utcnow(),
                        )
                        new_embed.add_field(
                            name="⏱️ Runtime", value=runtime, inline=True
                        )
                        new_embed.add_field(
                            name="🐟 Fish", value=str(self.app.fish_caught), inline=True
                        )
                        new_embed.add_field(
                            name="🍇 Fruits",
                            value=str(self.app.fruits_caught),
                            inline=True,
                        )
                        new_embed.add_field(
                            name="📦 Total", value=str(total_catches), inline=True
                        )
                        new_embed.add_field(
                            name="⚡ Rate", value=f"{hourly_rate}/hr", inline=True
                        )
                        new_embed.add_field(
                            name="🔧 Engine",
                            value=(
                                str(self.app.engine._state)
                                if hasattr(self.app, "engine")
                                else "N/A"
                            ),
                            inline=True,
                        )

                        if screenshot_file:
                            new_embed.set_image(url="attachment://screenshot.png")

                        new_embed.set_footer(
                            text="Use buttons below to control | Click Refresh to update stats + screenshot"
                        )

                        # Edit the original message
                        if screenshot_file:
                            file_obj = discord.File(
                                screenshot_file, filename="screenshot.png"
                            )
                            await interaction.message.edit(
                                embed=new_embed, attachments=[file_obj], view=self
                            )
                        else:
                            await interaction.message.edit(embed=new_embed, view=self)

                        await interaction.followup.send(
                            "✅ **Refreshed!**", ephemeral=True
                        )

                    except Exception as e:
                        logger.error(f"[BOT] Refresh error: {e}")
                        await interaction.followup.send(
                            f"❌ **Refresh failed:** {e}", ephemeral=True
                        )

            # Send menu
            logger.info(f"[BOT] Menu - About to send menu")
            if (
                self.bot_service
                and self.bot_service.bot
                and self.bot_service.is_running()
            ):
                logger.info(f"[BOT] Menu - Bot service checks passed")
                loop = self.bot_service.bot.loop
                logger.info(f"[BOT] Menu - Got loop: {loop}")
                if loop and loop.is_running():
                    logger.info(f"[BOT] Menu - Loop is running, scheduling async menu send")

                    logger.info(f"[BOT] Menu - About to schedule coroutine")
                    future = asyncio.run_coroutine_threadsafe(
                        self._send_discord_menu(channel_id), loop
                    )
                    logger.info(f"[BOT] Menu - Coroutine scheduled: {future}")
                else:
                    logger.error(
                        f"[BOT] Menu - Loop check failed. loop={loop}, is_running={loop.is_running() if loop else 'N/A'}"
                    )
                    self._send_bot_response(
                        channel_id, "❌ **Bot event loop not running**"
                    )
            else:
                self._send_bot_response(channel_id, "❌ **Bot is not connected**")

        except Exception as e:
            logger.error(f"[BOT] Menu error: {e}")
            self._send_bot_response(channel_id, f"❌ **Menu error:** {e}")

    # ============================================================================
    # DISCORD UI HANDLERS (V5.2)
    # ============================================================================

    def toggle_discord_rpc(self):
        """Toggle Discord Rich Presence on/off"""
        enabled = self.discord_rpc_enabled_var.get()

        # Save to settings
        self.settings.save_discord_rpc_settings(enabled)
        self.discord_rpc_enabled = enabled

        if enabled:
            # Start RPC
            if not self.rpc_service:
                self.rpc_service = RichPresenceService(logger=logger)

            self.rpc_service.start()
            self.rpc_status_label.configure(text="🟢 Active", text_color="#00dd00")
            logger.info("[RPC] Rich Presence enabled via UI")
        else:
            # Stop RPC in background thread (stop() blocks up to 2s)
            self.rpc_status_label.configure(text="⚪ Not Running", text_color="#888888")
            logger.info("[RPC] Rich Presence disabled via UI")

            if self.rpc_service:
                rpc_ref = self.rpc_service

                def _stop_rpc():
                    try:
                        rpc_ref.clear_presence()
                        rpc_ref.stop()
                    except Exception as e:
                        logger.warning(f"[RPC] Error stopping: {e}")

                threading.Thread(target=_stop_rpc, daemon=True).start()

    def toggle_discord_bot(self):
        """Toggle Discord Bot on/off"""
        enabled = self.discord_bot_enabled_var.get()
        self.discord_bot_enabled = enabled

        if enabled:
            # Check if already configured
            app_id = (
                self.bot_app_id_entry.get().strip()
                if hasattr(self, "bot_app_id_entry")
                else ""
            )
            token = (
                self.bot_token_entry.get().strip()
                if hasattr(self, "bot_token_entry")
                else ""
            )

            if app_id and token:
                self.bot_status_label.configure(
                    text="⏳ Click Save Settings to start", text_color="#ffaa00"
                )
            else:
                self.bot_status_label.configure(
                    text="⚠️ Fill App ID & Token, then Save", text_color="#ffaa00"
                )
            logger.info("[BOT] Bot enabled via UI - click 'Save Settings' to apply")
        else:
            # Update UI immediately (on GUI thread)
            self.bot_status_label.configure(text="🔴 Offline", text_color="#ff4444")

            # Read widget values NOW on GUI thread (before spawning background thread)
            app_id = (
                self.bot_app_id_entry.get().strip()
                if hasattr(self, "bot_app_id_entry")
                else ""
            )
            token = (
                self.bot_token_entry.get().strip()
                if hasattr(self, "bot_token_entry")
                else ""
            )
            users_text = (
                self.bot_allowed_users_text.get("1.0", "end-1c").strip()
                if hasattr(self, "bot_allowed_users_text")
                else ""
            )

            # Stop bot in background thread to avoid GUI freeze
            def stop_bot_async(app_id=app_id, token=token, users_text=users_text):
                try:
                    if self.bot_service and self.bot_service.is_running():
                        logger.info("[BOT] Stopping bot service...")
                        self.bot_service.stop()
                        self.bot_service = None
                        logger.info("[BOT] Bot service stopped")

                    # Parse user IDs (from pre-read values)
                    allowed_user_ids = []
                    if users_text:
                        for line in users_text.split("\n"):
                            line = line.strip()
                            if line and line.isdigit():
                                allowed_user_ids.append(int(line))

                    # Encrypt token if exists
                    from utils.token_encryption import encrypt_token

                    encrypted_token = encrypt_token(token) if token else ""
                    
                    # Read guild_id and auto_menu_channel_id from UI (if available)
                    guild_id = self.bot_guild_id_entry.get().strip() if hasattr(self, 'bot_guild_id_entry') else ""
                    auto_menu_channel_id = self.bot_auto_menu_channel_entry.get().strip() if hasattr(self, 'bot_auto_menu_channel_entry') else ""

                    # Save with enabled=False
                    self.settings.save_discord_bot_settings(
                        False, app_id, encrypted_token, allowed_user_ids, guild_id, auto_menu_channel_id
                    )
                    logger.info("[BOT] Bot disabled and settings saved")
                except Exception as e:
                    logger.error(f"[BOT] Error stopping bot: {e}")

            # Stop in background
            threading.Thread(target=stop_bot_async, daemon=True).start()

    def save_discord_bot_settings(self):
        """Save Discord bot settings and restart bot if enabled"""
        from utils.token_encryption import encrypt_token

        try:
            # Get values from UI
            enabled = self.discord_bot_enabled_var.get()
            app_id = self.bot_app_id_entry.get().strip()
            token = self.bot_token_entry.get().strip()
            guild_id = self.bot_guild_id_entry.get().strip() if hasattr(self, 'bot_guild_id_entry') else ""
            auto_menu_channel_id = self.bot_auto_menu_channel_entry.get().strip() if hasattr(self, 'bot_auto_menu_channel_entry') else ""

            # Parse user IDs
            users_text = self.bot_allowed_users_text.get("1.0", "end-1c").strip()
            allowed_user_ids = []

            if users_text:
                for line in users_text.split("\n"):
                    line = line.strip()
                    if line and line.isdigit():
                        allowed_user_ids.append(int(line))

            # Validate if enabled
            if enabled:
                if not app_id:
                    self.info_label.configure(
                        text="❌ Application ID required", text_color=self.error_color
                    )
                    return

                if not token:
                    self.info_label.configure(
                        text="❌ Bot Token required", text_color=self.error_color
                    )
                    return

                if not allowed_user_ids:
                    self.info_label.configure(
                        text="❌ At least one User ID required",
                        text_color=self.error_color,
                    )
                    return

            # Encrypt token
            encrypted_token = encrypt_token(token) if token else ""

            # Save to settings
            self.settings.save_discord_bot_settings(
                enabled, app_id, encrypted_token, allowed_user_ids, guild_id, auto_menu_channel_id
            )

            # Update state
            self.discord_bot_enabled = enabled
            self.discord_bot_app_id = app_id
            self.discord_bot_allowed_users = allowed_user_ids
            self.discord_bot_guild_id = guild_id
            self.discord_bot_auto_menu_channel = auto_menu_channel_id

            # Restart bot if enabled
            if enabled:
                # Update UI to show connecting
                self.bot_status_label.configure(
                    text="⏳ Connecting...", text_color="#ffaa00"
                )
                self.info_label.configure(
                    text="Starting Discord bot...", text_color=self.warning_color
                )

                # Stop existing bot
                if self.bot_service and self.bot_service.is_running():
                    self.bot_service.stop()

                # Start new bot in background thread
                def start_bot_async():
                    try:
                        from utils.token_encryption import decrypt_token

                        decrypted_token = decrypt_token(encrypted_token)

                        self.bot_service = DiscordBotService(
                            bot_token=decrypted_token,
                            allowed_user_ids=allowed_user_ids,
                            command_queue=self.bot_command_queue,
                            logger=logger,
                            command_prefix="!",
                            auto_menu_channel_id=auto_menu_channel_id,
                            app_reference=self,
                        )
                        self.bot_service.start()

                        # Update UI after 2 seconds (bot should be connected)
                        self.root.after(
                            2000,
                            lambda: self.bot_status_label.configure(
                                text="🟢 Online", text_color="#00dd00"
                            ),
                        )
                        self.root.after(
                            2000,
                            lambda: self.info_label.configure(
                                text="✅ Bot started successfully!",
                                text_color=self.success_color,
                            ),
                        )

                        logger.info(
                            f"[BOT] Started with {len(allowed_user_ids)} allowed users"
                        )
                    except Exception as e:
                        logger.error(f"[BOT] Failed to start: {e}")
                        self.root.after(
                            100,
                            lambda: self.bot_status_label.configure(
                                text="❌ Failed", text_color="#ff4444"
                            ),
                        )
                        self.root.after(
                            100,
                            lambda: self.info_label.configure(
                                text=f"❌ Failed to start bot: {str(e)}",
                                text_color=self.error_color,
                            ),
                        )

                threading.Thread(target=start_bot_async, daemon=True).start()
            else:
                self.info_label.configure(
                    text="✅ Settings saved", text_color=self.success_color
                )

        except Exception as e:
            self.info_label.configure(
                text=f"❌ Error: {str(e)}", text_color=self.error_color
            )
            logger.error(f"[BOT] Save settings error: {e}")

    def test_discord_bot_connection(self):
        """Test Discord bot connection (non-blocking)"""

        def test_thread():
            import asyncio
            import discord

            # Update UI on main thread (thread-safe)
            self.root.after(
                0,
                lambda: self.bot_status_label.configure(
                    text="🔌 Testing...", text_color="#ffaa00"
                ),
            )
            self.root.after(
                0,
                lambda: self.info_label.configure(
                    text="Testing bot connection...", text_color=self.warning_color
                ),
            )

            try:
                # Check if bot is configured
                app_id = self.bot_app_id_entry.get().strip()
                token = self.bot_token_entry.get().strip()

                if not app_id or not token:
                    self.root.after(
                        0,
                        lambda: self.info_label.configure(
                            text="❌ Configure App ID & Token first",
                            text_color=self.error_color,
                        ),
                    )
                    self.root.after(
                        0,
                        lambda: self.bot_status_label.configure(
                            text="🔴 Offline", text_color="#ff4444"
                        ),
                    )
                    return

                # Create async test function
                async def test_connection():
                    test_bot = discord.Client(intents=discord.Intents.default())
                    connected = False

                    @test_bot.event
                    async def on_ready():
                        nonlocal connected
                        connected = True
                        logger.info(f"[BOT TEST] Connected as {test_bot.user}")

                        # Update UI on main thread
                        self.root.after(
                            0,
                            lambda: self.info_label.configure(
                                text=f"✅ Connected as {test_bot.user.name}!",
                                text_color=self.success_color,
                            ),
                        )
                        self.root.after(
                            0,
                            lambda: self.bot_status_label.configure(
                                text="✅ Test OK", text_color="#00dd00"
                            ),
                        )

                        # Close after 1 second
                        await asyncio.sleep(1)
                        await test_bot.close()

                    try:
                        # Start bot with timeout (non-blocking in this thread)
                        await asyncio.wait_for(
                            test_bot.start(token, reconnect=False), timeout=10.0
                        )
                    except asyncio.TimeoutError:
                        if not connected:
                            raise Exception("Connection timeout (10s)")
                    except discord.LoginFailure:
                        raise discord.LoginFailure("Invalid token")
                    finally:
                        if not test_bot.is_closed():
                            await test_bot.close()

                # Run async test (this will block THIS thread only, not GUI)
                asyncio.run(test_connection())

            except discord.LoginFailure:
                self.root.after(
                    0,
                    lambda: self.info_label.configure(
                        text="❌ Invalid token", text_color=self.error_color
                    ),
                )
                self.root.after(
                    0,
                    lambda: self.bot_status_label.configure(
                        text="🔴 Offline", text_color="#ff4444"
                    ),
                )
                logger.error("[BOT TEST] Invalid token")
            except Exception as e:
                self.root.after(
                    0,
                    lambda: self.info_label.configure(
                        text=f"❌ Test failed: {str(e)}", text_color=self.error_color
                    ),
                )
                self.root.after(
                    0,
                    lambda: self.bot_status_label.configure(
                        text="🔴 Offline", text_color="#ff4444"
                    ),
                )
                logger.error(f"[BOT TEST] Error: {e}")

        threading.Thread(target=test_thread, daemon=True).start()

    def toggle_bot_token_visibility(self):
        """Toggle bot token visibility"""
        if self.bot_token_entry.cget("show") == "•":
            self.bot_token_entry.configure(show="")
        else:
            self.bot_token_entry.configure(show="•")

    def list_discord_channels(self):
        """List all text channels in the configured guild"""
        guild_id = self.bot_guild_id_entry.get().strip()
        
        if not guild_id or not guild_id.isdigit():
            self.info_label.configure(
                text="❌ Enter valid Guild ID first", text_color=self.error_color
            )
            return

        # Check if bot is running
        if not self.bot_service or not self.bot_service.is_running():
            self.info_label.configure(
                text="❌ Bot must be running to list channels. Click 'Save Settings' first.",
                text_color=self.error_color
            )
            return

        self.info_label.configure(
            text="📋 Fetching channels...", text_color=self.warning_color
        )

        def fetch_channels():
            try:
                import asyncio
                
                async def get_channels():
                    bot = self.bot_service.bot
                    if not bot:
                        return None
                    
                    guild = bot.get_guild(int(guild_id))
                    if not guild:
                        return None
                    
                    # Get all text channels
                    text_channels = [ch for ch in guild.text_channels]
                    return guild, text_channels

                # Run in bot's event loop
                loop = self.bot_service.bot.loop
                if loop and loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(get_channels(), loop)
                    result = future.result(timeout=5)
                    
                    if result:
                        guild, channels = result
                        
                        # Create channels list window
                        self.root.after(0, lambda: self._show_channels_window(guild, channels))
                    else:
                        self.root.after(
                            0,
                            lambda: self.info_label.configure(
                                text=f"❌ Guild {guild_id} not found or bot not member",
                                text_color=self.error_color
                            )
                        )
                else:
                    self.root.after(
                        0,
                        lambda: self.info_label.configure(
                            text="❌ Bot event loop not running",
                            text_color=self.error_color
                        )
                    )

            except Exception as e:
                logger.error(f"[BOT] Error listing channels: {e}")
                self.root.after(
                    0,
                    lambda: self.info_label.configure(
                        text=f"❌ Error: {str(e)}", text_color=self.error_color
                    )
                )

        threading.Thread(target=fetch_channels, daemon=True).start()

    def _show_channels_window(self, guild, channels):
        """Show channels in a popup window"""
        import tkinter as tk
        from tkinter import ttk
        
        popup = tk.Toplevel(self.root)
        popup.title(f"📋 Channels in {guild.name}")
        popup.geometry("600x400")
        popup.configure(bg="#1e1e2e")
        
        # Header
        header_label = tk.Label(
            popup,
            text=f"Text Channels in {guild.name}",
            font=("Segoe UI", 14, "bold"),
            bg="#1e1e2e",
            fg="#00ff88"
        )
        header_label.pack(pady=10)
        
        info_label = tk.Label(
            popup,
            text="Click a channel to copy its ID",
            font=("Segoe UI", 10),
            bg="#1e1e2e",
            fg="#888888"
        )
        info_label.pack()
        
        # Channels frame with scrollbar
        frame = tk.Frame(popup, bg="#2a2a3e")
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")
        
        channels_text = tk.Text(
            frame,
            font=("Consolas", 11),
            bg="#2a2a3e",
            fg="#ffffff",
            yscrollcommand=scrollbar.set,
            wrap="word",
            relief="flat"
        )
        channels_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=channels_text.yview)
        
        # Add channels
        for ch in sorted(channels, key=lambda x: x.position):
            line = f"#{ch.name:<30} ID: {ch.id}\n"
            channels_text.insert("end", line)
            
        channels_text.configure(state="disabled")
        
        # Copy button
        def copy_selected():
            try:
                selection = channels_text.get("sel.first", "sel.last")
                # Extract ID from selection
                if "ID:" in selection:
                    channel_id = selection.split("ID:")[-1].strip()
                    popup.clipboard_clear()
                    popup.clipboard_append(channel_id)
                    info_label.configure(text=f"✅ Copied: {channel_id}")
            except:
                pass
        
        copy_btn = tk.Button(
            popup,
            text="📋 Copy Selected ID",
            command=copy_selected,
            bg="#4a5568",
            fg="#ffffff",
            font=("Segoe UI", 11),
            relief="flat",
            padx=20,
            pady=8
        )
        copy_btn.pack(pady=10)
        
        popup.transient(self.root)
        popup.grab_set()

    def smart_bait_capture_zone(self, zone_config):
        """Capture a screen region for OCR
        Args:
            zone_config: dict with x, y, width, height
        Returns:
            numpy array of the captured image, or None on failure
        """
        if not zone_config:
            return None
        try:
            if not hasattr(self, "_mss_instance") or self._mss_instance is None:
                self._mss_instance = mss.mss()
            monitor = {
                "left": zone_config["x"],
                "top": zone_config["y"],
                "width": zone_config["width"],
                "height": zone_config["height"],
            }
            screenshot = self._mss_instance.grab(monitor)
            return np.array(screenshot)
        except Exception as e:
            logger.debug(f"Smart Bait screenshot capture failed: {e}")
            return None

    def _init_automation_modules(self):
        """Initialize Phase 5 & 6 automation modules (called after GUI created)

        Creates BaitManager, FruitHandler, and FishingCycle with all dependencies.
        Must be called AFTER create_gui() since modules need UI callbacks.
        """
        global stats_manager

        # Phase 5.1: BaitManager callbacks (need UI labels created by create_gui)
        def update_smart_bait_ui_hint(zone_type, text, color):
            """Update Smart Bait UI hint label"""
            # Not implemented in main file - stub
            pass

        def update_smart_bait_mode_display(text, color):
            """Update Smart Bait mode display"""
            if (
                hasattr(self, "smart_bait_mode_display")
                and self.smart_bait_mode_display
            ):
                self.smart_bait_mode_display.configure(text=text, text_color=color)

        def update_smart_bait_decision_display(text, color):
            """Update Smart Bait decision display"""
            if (
                hasattr(self, "smart_bait_decision_display")
                and self.smart_bait_decision_display
            ):
                self.smart_bait_decision_display.configure(text=text, text_color=color)

        bait_callbacks = {
            "save_settings": self.save_smart_bait_settings,  # Use the complete save function
            "update_ui_hint": update_smart_bait_ui_hint,
            "update_mode_display": update_smart_bait_mode_display,
            "update_decision_display": update_smart_bait_decision_display,
        }
        self.bait_manager = BaitManager(
            self._bait_manager_vision, self._bait_manager_settings, bait_callbacks
        )

        # Phase 5.2: FruitHandler callbacks
        fruit_callbacks = {
            "check_legendary_pity": self.check_legendary_pity,
            "interruptible_sleep": self.interruptible_sleep,
            "get_webhook_url": lambda: (
                self.webhook_url if hasattr(self, "webhook_url") else ""
            ),
            "get_user_id": lambda: self.user_id if hasattr(self, "user_id") else "",
            "get_runtime": self.get_runtime,
            "get_fruits_caught": lambda: self.fruits_caught,
            "get_fish_caught": lambda: self.fish_caught,
            "send_fruit_webhook": self.send_fruit_webhook,  # Add webhook service delegation
        }
        self.fruit_handler = FruitHandler(
            self._fruit_handler_vision,
            self._fruit_handler_input,
            self._fruit_handler_settings,
            fruit_callbacks,
        )

        # Phase 6: FishingCycle - Main fishing loop orchestration
        fishing_vision = {
            "screen": self.screen,
            "color_detector": self.color_detector,
            "anti_macro": self.anti_macro,
        }
        fishing_input = {
            "mouse": self.mouse,
            "keyboard": self.keyboard,
            "window_manager": self.window,
        }
        fishing_settings = {
            # Area coordinates
            "area_coords": self.area_coords,
            "auto_craft_area_coords": self.auto_craft_area_coords,
            "water_point": self.water_point,
            "auto_craft_water_point": self.auto_craft_water_point,
            "top_bait_point": self.top_bait_point,
            "fruit_point": self.fruit_point,
            "inventory_fruit_point": self.inventory_fruit_point,
            "inventory_center_point": self.inventory_center_point,
            # Delays and timing
            "recast_timeout": self.recast_timeout,
            "fruit_detection_delay": self.fruit_detection_delay,
            "rod_deselect_delay": self.rod_deselect_delay,
            "rod_select_delay": (
                self.rod_select_delay if hasattr(self, "rod_select_delay") else 0.2
            ),
            "bait_click_delay": self.bait_click_delay,
            "mouse_move_settle": self.mouse_move_settle,
            "cast_hold_duration": self.cast_hold_duration,
            "pre_cast_minigame_wait": self.pre_cast_minigame_wait,
            "zoom_tick_delay": self.zoom_tick_delay,
            "zoom_settle_delay": self.zoom_settle_delay,
            "store_click_delay": self.store_click_delay,
            "backspace_delay": self.backspace_delay,
            "fruit_hold_delay": self.fruit_hold_delay,
            "camera_rotation_delay": self.camera_rotation_delay,
            "camera_rotation_step_delay": self.camera_rotation_step_delay,
            "camera_rotation_settle_delay": self.camera_rotation_settle_delay,
            "camera_rotation_steps": self.camera_rotation_steps,
            "resend_interval": self.resend_interval,
            "general_action_delay": self.general_action_delay,  # MISSING - used in buy_common_bait
            # Hotkeys
            "rod_hotkey": self.rod_hotkey,
            "fruit_hotkey": self.fruit_hotkey,
            "everything_else_hotkey": self.everything_else_hotkey,
            # Colors
            "fruit_color": self.fruit_color,
            # Flags
            "auto_buy_bait": self.auto_buy_bait,
            "auto_select_top_bait": self.auto_select_top_bait,
            "smart_bait_enabled": self.smart_bait_enabled,
            "auto_store_fruit": self.auto_store_fruit,
            "store_in_inventory": self.store_in_inventory,
            "auto_craft_enabled": self.auto_craft_enabled,
            "disable_normal_camera": self.disable_normal_camera,
            "webhook_only_legendary": self.webhook_only_legendary,
            # Bait purchase settings
            "yes_button": self.yes_button,
            "middle_button": self.middle_button,
            "no_button": self.no_button,
            "loops_per_purchase": self.loops_per_purchase,
            "bait_loop_counter": self.bait_loop_counter,
            # Auto craft settings
            "craft_every_n_fish": self.craft_every_n_fish,
            # PID control parameters
            "pid_kp": self.pid_kp,
            "pid_kd": self.pid_kd,
            "pid_clamp": self.pid_clamp,
            "max_lost_frames": self.max_lost_frames,
            # Zoom settings
            "zoom_ticks": self.zoom_ticks,
        }
        fishing_callbacks = {
            # Core callbacks
            "set_status": self.set_status,
            "interruptible_sleep": self.interruptible_sleep,
            "check_legendary_pity": self.check_legendary_pity,
            "send_fruit_webhook": (
                self.send_fruit_webhook
                if hasattr(self, "send_fruit_webhook")
                else lambda *args: None
            ),
            # State access callbacks - self.running is source of truth
            "get_running": lambda: self.running,
            "get_paused": lambda: self.paused,  # Pause/resume support
            "get_first_run": lambda: self.first_run,
            "set_first_run": lambda value: setattr(self, "first_run", value),
            "get_first_catch": lambda: self.first_catch,
            "set_first_catch": lambda value: setattr(self, "first_catch", value),
            "get_mouse_pressed": lambda: self.mouse_pressed,
            "set_mouse_pressed": lambda value: setattr(self, "mouse_pressed", value),
            "get_fish_caught": lambda: self.fish_caught,
            "increment_fish_caught": self._increment_fish_caught_with_rpc,
            "get_fruits_caught": lambda: self.fruits_caught,
            "increment_fruits_caught": self._increment_fruits_caught_with_rpc,
            "set_fish_at_last_fruit": lambda value: setattr(
                self, "fish_at_last_fruit", value
            ),
            # PID state access
            "get_pid_last_error": lambda: self.pid_last_error,
            "set_pid_last_error": lambda value: setattr(self, "pid_last_error", value),
            "get_pid_last_time": lambda: self.pid_last_time,
            "set_pid_last_time": lambda value: setattr(self, "pid_last_time", value),
            "get_detection_lost_counter": lambda: self.detection_lost_counter,
            "set_detection_lost_counter": lambda value: setattr(
                self, "detection_lost_counter", value
            ),
            "get_last_resend_time": lambda: self.last_resend_time,
            "set_last_resend_time": lambda value: setattr(
                self, "last_resend_time", value
            ),
            # FPS tracking
            "get_fps_frame_count": lambda: self.fps_frame_count,
            "increment_fps_frame_count": lambda: setattr(
                self, "fps_frame_count", self.fps_frame_count + 1
            ),
            "get_fps_last_time": lambda: self.fps_last_time,
            "set_fps_last_time": lambda value: setattr(self, "fps_last_time", value),
            "get_detection_fps": lambda: self.detection_fps,
            "set_detection_fps": lambda value: setattr(self, "detection_fps", value),
            # Cycle time tracking
            "start_cycle_timer": self.start_cycle_timer,
            "end_cycle_timer": self.end_cycle_timer,
            "get_average_cycle_time": lambda: self.average_cycle_time,
            # Auto craft state
            "get_last_craft_fish_count": lambda: getattr(
                self, "last_craft_fish_count", -1
            ),
            "set_last_craft_fish_count": lambda value: setattr(
                self, "last_craft_fish_count", value
            ),
            # Dynamic GUI settings (can change during execution)
            "get_auto_buy_bait": lambda: self.auto_buy_bait,
            "get_auto_craft_enabled": lambda: self.auto_craft_enabled,
            "get_auto_select_top_bait": lambda: self.auto_select_top_bait,
            "get_smart_bait_enabled": lambda: self.smart_bait_enabled,
            "get_auto_store_fruit": lambda: self.auto_store_fruit,
            "get_store_in_inventory": lambda: self.store_in_inventory,
            "get_disable_normal_camera": lambda: self.disable_normal_camera,
            "get_webhook_only_legendary": lambda: self.webhook_only_legendary,
        }
        self.fishing_cycle = FishingCycle(
            fishing_vision,
            fishing_input,
            self.bait_manager,
            self.fruit_handler,
            self.craft_automation,
            fishing_settings,
            fishing_callbacks,
            logger,
            stats_manager,
        )
        logger.info("✓ Phase 5 & 6 automation modules initialized")

        # Phase 7: Core Engine - Lifecycle orchestration
        engine_callbacks = {
            "on_state_change": self._on_engine_state_change,
            "on_start": self._on_engine_start,
            "on_stop": self._on_engine_stop,
            "on_error": self._on_engine_error,
        }
        self.engine = FishingEngine(
            fishing_cycle=self.fishing_cycle,
            settings_manager=self.settings,
            logger=logger,
            callbacks=engine_callbacks,
        )
        logger.info("✓ Phase 7 core engine initialized")

    # V5: Validators moved to utils.validators module - kept as wrappers for convenience
    # No need for wrapper methods - validators are now imported at module level

    def create_spinbox_entry(
        self, parent, default_value, min_val, max_val, step, width=120, is_float=True
    ):
        """Create an entry with up/down arrow buttons (spinbox-like)

        Args:
            parent: Parent frame
            default_value: Initial value
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            step: Increment/decrement step
            width: Width of entry field
            is_float: Whether value is float (True) or int (False)

        Returns:
            tuple: (container_frame, entry_widget)
        """
        container = ctk.CTkFrame(parent, fg_color="transparent")

        # Entry field
        entry = ctk.CTkEntry(
            container,
            width=width,
            fg_color=self.button_color,
            border_color=self.accent_color,
        )
        entry.insert(0, str(default_value))
        entry.pack(side="left", padx=(0, 2))

        # Buttons container
        buttons_frame = ctk.CTkFrame(container, fg_color="transparent", width=20)
        buttons_frame.pack(side="left")

        # Up arrow button
        up_btn = ctk.CTkButton(
            buttons_frame,
            text="▲",
            width=20,
            height=15,
            font=("Arial", 8),
            fg_color=self.accent_color,
            hover_color=self.hover_color,
            command=lambda: self._increment_spinbox(entry, step, max_val, is_float),
        )
        up_btn.pack(side="top", pady=(0, 1))

        # Down arrow button
        down_btn = ctk.CTkButton(
            buttons_frame,
            text="▼",
            width=20,
            height=15,
            font=("Arial", 8),
            fg_color=self.accent_color,
            hover_color=self.hover_color,
            command=lambda: self._decrement_spinbox(entry, step, min_val, is_float),
        )
        down_btn.pack(side="top")

        return container, entry

    def _increment_spinbox(self, entry, step, max_val, is_float):
        """Increment spinbox value"""
        try:
            current = float(entry.get()) if is_float else int(entry.get())
            new_value = current + step
            if new_value <= max_val:
                entry.delete(0, tk.END)
                if is_float:
                    entry.insert(
                        0, f"{new_value:.3f}" if step < 1 else f"{new_value:.1f}"
                    )
                else:
                    entry.insert(0, str(int(new_value)))
        except ValueError:
            pass

    def _decrement_spinbox(self, entry, step, min_val, is_float):
        """Decrement spinbox value"""
        try:
            current = float(entry.get()) if is_float else int(entry.get())
            new_value = current - step
            if new_value >= min_val:
                entry.delete(0, tk.END)
                if is_float:
                    entry.insert(
                        0, f"{new_value:.3f}" if step < 1 else f"{new_value:.1f}"
                    )
                else:
                    entry.insert(0, str(int(new_value)))
        except ValueError:
            pass

    def create_gui(self):
        """Create the GUI elements"""
        # Create scrollable frame using customtkinter
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self.root,
            fg_color=self.bg_color,
            scrollbar_button_color="#4a4a4a",
            scrollbar_button_hover_color=self.hover_color,
        )
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.create_gui_content()

    def create_gui_content(self):
        # Create the main GUI content (separated for theme switching)
        # Clear the scrollable frame
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Title - Clean white text, no fancy colors
        title = ctk.CTkLabel(
            self.scrollable_frame,
            text="BPS Fishing Macro",
            font=("Segoe UI", 24, "bold"),
            text_color=self.fg_color,
        )
        title.pack(pady=15)

        # Create Tabview (substitui Notebook)
        self.tabview = ctk.CTkTabview(
            self.scrollable_frame,
            fg_color=self.bg_color,
            segmented_button_selected_color="#1d1d1d",
            segmented_button_selected_hover_color=self.hover_color,
            segmented_button_fg_color="#0f0f0f",
            segmented_button_unselected_color="#0f0f0f",
            segmented_button_unselected_hover_color="#2a2a2a",
        )
        self.tabview.pack(fill="both", expand=True, padx=5, pady=10)

        # Create tabs - clean names without emojis
        general_tab_frame = self.tabview.add("General")
        settings_tab_frame = self.tabview.add("Settings")
        fishing_tab_frame = self.tabview.add("Fishing")
        auto_craft_tab_frame = self.tabview.add("Auto Craft")
        webhooks_tab_frame = self.tabview.add("Webhooks")
        discord_tab_frame = self.tabview.add("Discord")  # V5.2: RPC + Bot
        advanced_tab_frame = self.tabview.add("Advanced")
        stats_tab_frame = self.tabview.add("Stats")
        logging_tab_frame = self.tabview.add("Logging")

        # Build each tab from its module
        general_tab.build(self, general_tab_frame)
        settings_tab.build(self, settings_tab_frame)
        fishing_tab.build(self, fishing_tab_frame)
        craft_tab.build(self, auto_craft_tab_frame, ensure_ocr_dependencies)
        webhook_tab.build(self, webhooks_tab_frame)
        discord_bot_tab.create_discord_bot_tab(discord_tab_frame, self)  # V5.2
        advanced_tab.build(self, advanced_tab_frame)
        stats_tab.build(self, stats_tab_frame)
        logging_tab.build(self, logging_tab_frame)

        # Setup tooltips for all widgets
        self.setup_tooltips()

        # Auto-refresh is OFF by default - user can enable manually if desired

    def setup_tooltips(self):
        """Setup tooltips for all UI widgets with helpful hints"""
        # Store tooltips to prevent garbage collection
        self.tooltips = []

        def add_tooltip(widget, text):
            """Helper to create and store tooltip"""
            tooltip = CTkToolTip(widget, text)
            self.tooltips.append(tooltip)

        # ===== GENERAL TAB =====
        # Always on Top
        if hasattr(self, "always_on_top_var"):
            for widget in self.scrollable_frame.winfo_children():
                self._add_tooltips_recursive(
                    widget,
                    {
                        "Always on Top": "Keep this window above all other windows",
                    },
                )

        # Start/Stop button
        if hasattr(self, "start_button"):
            add_tooltip(
                self.start_button,
                "Start or stop the fishing macro.\nHotkey: F1 (default)",
            )

        # Area button
        if hasattr(self, "area_button"):
            add_tooltip(
                self.area_button,
                "Select the fishing minigame detection area.\nDrag to draw a rectangle around the fishing bar.\nHotkey: F2 (default)",
            )

        # Exit button
        if hasattr(self, "exit_button"):
            add_tooltip(
                self.exit_button,
                "Emergency exit - stops the macro and closes the application.\nHotkey: F3 (default)",
            )

        # ===== SETTINGS TAB =====
        # Auto Buy Bait checkbox
        if hasattr(self, "auto_bait_checkbox"):
            add_tooltip(
                self.auto_bait_checkbox,
                "Automatically purchase bait from the shop.\nRequires button positions to be configured.\nCannot be used with Auto Craft mode.",
            )

        # Auto Store Fruit checkbox
        if hasattr(self, "auto_fruit_checkbox"):
            add_tooltip(
                self.auto_fruit_checkbox,
                "Automatically store caught Devil Fruits in your inventory.\nRotates camera and zooms in to detect fruits.\nTakes a screenshot when a fruit is detected.",
            )

        # Sound notification checkbox
        if hasattr(self, "sound_enabled_var"):
            # Find the sound checkbox widget
            pass  # Added via config text

        # Yes/Middle/No buttons
        if hasattr(self, "yes_button_btn"):
            add_tooltip(
                self.yes_button_btn,
                "Click to select the YES button position in the bait shop dialog",
            )

        if hasattr(self, "middle_button_btn"):
            add_tooltip(
                self.middle_button_btn,
                "Click to select the MIDDLE button position in the bait shop dialog",
            )

        if hasattr(self, "no_button_btn"):
            add_tooltip(
                self.no_button_btn,
                "Click to select the NO button position in the bait shop dialog",
            )

        # Loops entry
        if hasattr(self, "loops_entry"):
            add_tooltip(
                self.loops_entry,
                "Number of fishing loops before buying more bait.\nHigher = less interruption, but may run out of bait.",
            )

        # Fruit point button
        if hasattr(self, "fruit_point_btn"):
            add_tooltip(
                self.fruit_point_btn,
                "Click to select a point on your character where the fruit appears.\nUsed to detect if you caught a Devil Fruit.",
            )

        # Top bait checkbox/button
        if hasattr(self, "auto_top_bait_checkbox"):
            add_tooltip(
                self.auto_top_bait_checkbox,
                "Automatically select the top bait in your inventory before casting.",
            )

        if hasattr(self, "top_bait_btn"):
            add_tooltip(
                self.top_bait_btn,
                "Click to select the position of the top bait in your bait menu.",
            )

        # Disable camera checkbox
        if hasattr(self, "disable_normal_camera_checkbox"):
            add_tooltip(
                self.disable_normal_camera_checkbox,
                "Disable camera rotation and zoom in normal mode.\nUse this if you already have the camera positioned correctly.",
            )

        # ===== FISHING TAB =====
        # Cast duration
        if hasattr(self, "cast_duration_entry"):
            add_tooltip(
                self.cast_duration_entry,
                "How long to hold the cast button (in seconds).\nLonger = further cast distance.",
            )

        # Recast timeout
        if hasattr(self, "recast_timeout_entry"):
            add_tooltip(
                self.recast_timeout_entry,
                "Maximum time to wait for a fish (in seconds).\nAfter this time, the macro will recast automatically.",
            )

        # Fishing end delay
        if hasattr(self, "fishing_end_delay_entry"):
            add_tooltip(
                self.fishing_end_delay_entry,
                "Delay after catching a fish before next action (in seconds).\nHelps prevent detection issues.",
            )

        # Water point button
        if hasattr(self, "water_point_btn"):
            add_tooltip(
                self.water_point_btn,
                "Click to select where to cast your fishing rod.\nChoose a point in the water.",
            )

        # ===== AUTO CRAFT TAB =====
        if hasattr(self, "auto_craft_checkbox"):
            add_tooltip(
                self.auto_craft_checkbox,
                "Enable Auto Craft mode.\nAutomatically crafts bait after catching fish.\nCannot be used with Auto Buy Bait.",
            )

        if hasattr(self, "craft_every_entry"):
            add_tooltip(
                self.craft_every_entry,
                "Number of fish to catch before crafting bait.\nLower = more frequent crafting.",
            )

        # Craft button positions
        if hasattr(self, "craft_button_btn"):
            add_tooltip(
                self.craft_button_btn,
                "Click to select the CRAFT button position in the crafting menu.",
            )

        if hasattr(self, "plus_button_btn"):
            add_tooltip(
                self.plus_button_btn,
                "Click to select the PLUS (+) button to increase quantity.",
            )

        if hasattr(self, "fish_icon_btn"):
            add_tooltip(
                self.fish_icon_btn,
                "Click to select the fish icon in the crafting menu.",
            )

        # Bait coords
        if hasattr(self, "legendary_bait_btn"):
            add_tooltip(
                self.legendary_bait_btn,
                "Click to select the Legendary Bait position in crafting menu.",
            )

        if hasattr(self, "rare_bait_btn"):
            add_tooltip(
                self.rare_bait_btn,
                "Click to select the Rare Bait position in crafting menu.",
            )

        if hasattr(self, "common_bait_btn"):
            add_tooltip(
                self.common_bait_btn,
                "Click to select the Common Bait position in crafting menu.",
            )

        # ===== WEBHOOKS TAB =====
        if hasattr(self, "webhook_url_entry"):
            add_tooltip(
                self.webhook_url_entry,
                "Discord webhook URL for notifications.\nGet this from your Discord server settings > Integrations > Webhooks.",
            )

        if hasattr(self, "user_id_entry"):
            add_tooltip(
                self.user_id_entry,
                "Your Discord user ID for mentions.\nEnable Developer Mode in Discord, right-click your name, Copy ID.",
            )

        if hasattr(self, "test_webhook_btn"):
            add_tooltip(
                self.test_webhook_btn,
                "Send a test message to verify your webhook is working.",
            )

        # ===== ADVANCED TAB =====
        # PID settings
        if hasattr(self, "kp_entry"):
            add_tooltip(
                self.kp_entry,
                "Proportional gain for mouse movement.\nHigher = faster but may overshoot.",
            )

        if hasattr(self, "kd_entry"):
            add_tooltip(
                self.kd_entry,
                "Derivative gain for damping.\nHigher = smoother but slower.",
            )

        if hasattr(self, "clamp_entry"):
            add_tooltip(
                self.clamp_entry,
                "Maximum mouse movement speed limit.\nLower = more precise but slower.",
            )

        # ===== STATS TAB =====
        if hasattr(self, "export_csv_btn"):
            add_tooltip(
                self.export_csv_btn,
                "Export all fishing sessions to a CSV file for analysis.",
            )

        if hasattr(self, "reset_stats_btn"):
            add_tooltip(
                self.reset_stats_btn,
                "Clear all saved statistics. This cannot be undone!",
            )

    def _add_tooltips_recursive(self, widget, tooltip_map):
        """Recursively find widgets by text and add tooltips"""
        try:
            # Check if widget has cget method for text
            if hasattr(widget, "cget"):
                try:
                    text = widget.cget("text")
                    if text in tooltip_map:
                        tooltip = CTkToolTip(widget, tooltip_map[text])
                        self.tooltips.append(tooltip)
                except:
                    pass

            # Recursively check children
            for child in widget.winfo_children():
                self._add_tooltips_recursive(child, tooltip_map)
        except:
            pass

    def start_rebind(self, key_type):
        """Start rebinding a hotkey"""
        self.is_rebinding = key_type

        # Update UI to show rebinding
        if key_type == "start":
            self.start_hotkey_label.configure(text="[WAITING...]", text_color="#ff4444")
        elif key_type == "area":
            self.area_hotkey_label.configure(text="[WAITING...]", text_color="#ff4444")
        elif key_type == "exit":
            self.exit_hotkey_label.configure(text="[WAITING...]", text_color="#ff4444")
        elif key_type == "pause":
            self.pause_hotkey_label.configure(text="[WAITING...]", text_color="#ff4444")

        self.info_label.configure(
            text=f"Press a key to bind {key_type}...", text_color="#ffaa00"
        )

    def on_press(self, key):
        """Handle key press for hotkey binding and execution"""
        try:
            # Handle rebinding
            if self.is_rebinding:
                try:
                    key_name = (
                        key.char.lower()
                        if hasattr(key, "char")
                        else str(key).lower().replace("key.", "")
                    )
                except AttributeError:
                    key_name = str(key).lower().replace("key.", "")

                self.hotkeys[self.is_rebinding] = key_name

                # Update UI — MUST use root.after() because on_press runs on pynput thread
                display_key = f"[{key_name.upper()}]"
                rebind_target = self.is_rebinding  # capture before clearing
                self.is_rebinding = None

                def _apply_rebind_ui(target=rebind_target, dk=display_key):
                    try:
                        if target == "start":
                            self.start_hotkey_label.configure(
                                text=dk, text_color=self.accent_color
                            )
                        elif target == "area":
                            self.area_hotkey_label.configure(
                                text=dk, text_color=self.accent_color
                            )
                        elif target == "exit":
                            self.exit_hotkey_label.configure(
                                text=dk, text_color=self.accent_color
                            )
                        elif target == "pause":
                            self.pause_hotkey_label.configure(
                                text=dk, text_color=self.accent_color
                            )
                        self.info_label.configure(
                            text="✓ Key rebound successfully!", text_color="#00dd00"
                        )
                    except Exception:
                        pass

                self.root.after(0, _apply_rebind_ui)
                return

            # Handle hotkey execution
            try:
                key_name = (
                    key.char.lower()
                    if hasattr(key, "char")
                    else str(key).lower().replace("key.", "")
                )
            except AttributeError:
                key_name = str(key).lower().replace("key.", "")

            if key_name == self.hotkeys["start"]:
                self.root.after(0, self.toggle_start)
            elif key_name == self.hotkeys["area"]:
                self.root.after(0, self.toggle_area)
            elif key_name == self.hotkeys["exit"]:
                self.root.after(0, self.force_exit)
            elif key_name == self.hotkeys.get(
                "pause", "f4"
            ):  # Use .get() for backward compatibility
                self.root.after(0, self.toggle_pause)

        except Exception as e:
            pass

    def setup_hotkeys(self):
        """Setup global hotkey listener"""
        self.listener = Listener(on_press=self.on_press)
        self.listener.start()

    def toggle_pause(self):
        """Toggle pause/resume state (F4 hotkey)"""
        if not self.running:
            # Cannot pause if not running
            self.info_label.configure(
                text="❌ Cannot pause - macro not running!", text_color="#ff4444"
            )
            return

        self.paused = not self.paused

        if self.paused:
            # Start tracking pause time
            self.pause_start_time = time.time()
            self.status_label.configure(text="Status: ⏸ PAUSED", text_color="#ffaa00")
            self.info_label.configure(
                text="⏸ Macro paused! Press F4 to resume.", text_color="#ffaa00"
            )
            logger.info("[Pause] Macro paused by user")
        else:
            # Accumulate paused time
            if self.pause_start_time:
                self.total_paused_time += time.time() - self.pause_start_time
                self.pause_start_time = None
            self.status_label.configure(text="Status: ▶ RUNNING", text_color="#00dd00")
            self.info_label.configure(text="▶ Macro resumed!", text_color="#00dd00")
            logger.info("[Resume] Macro resumed")

    def toggle_start(self):
        """Toggle start/stop"""
        global stats_manager

        # Diagnostic: log entry with thread info
        self.watchdog.log_event(
            "toggle_start", f"running={self.running}, area_active={self.area_active}"
        )

        # Check if area selector is active
        if not self.running and self.area_active:
            self.info_label.configure(
                text="❌ Cannot start! Close Area Selector first!", text_color="#ff4444"
            )
            return

        # If already running, stop it
        if self.running:
            print("\r[Toggle] Stop requested...", end="", flush=True)  # Debug F1
            self._actually_stop_macro()
            return

        # If starting with auto-craft AND smart bait enabled, show popup to choose mode
        if self.auto_craft_enabled and self.smart_bait_enabled:
            self.show_smart_bait_startup_dialog()
            return

        # Otherwise start normally
        self._actually_start_macro()

    def _actually_start_macro(self):
        """Actually start the macro (called after popup or directly)"""
        global stats_manager

        # Diagnostic logging
        self.watchdog.log_event(
            "_actually_start_macro:ENTER", f"running={self.running}"
        )

        # Only start if not already running
        if self.running:
            logger.warning("[Start] Already running, ignoring start request")
            return

        logger.info("[Start] ▶ Starting macro...")
        self.running = True

        if self.running:
            self.status_label.configure(text="Status: ▶ RUNNING", text_color="#00dd00")
            self.start_button.configure(text="⏹ STOP")
            self.info_label.configure(text="✓ Macro started!", text_color="#00dd00")

            # Reset statistics
            self.start_time = time.time()
            self.fruits_caught = 0
            self.fish_caught = 0
            self.fish_at_last_fruit = 0
            self.last_craft_fish_count = (
                -1
            )  # Prevent infinite crafting loop if cast fails

            # V3: Start stats session
            if stats_manager is None:
                stats_manager = StatsManager(
                    db_path=os.path.join(BASE_DIR, "fishing_stats.db")
                )
            stats_manager.start_session()

            # V5.2: Start Discord Rich Presence
            if self.rpc_service:
                logger.info("[RPC] Starting Rich Presence service...")
                self.rpc_service.start()
                # Initial presence update with detailed status
                logger.info("[RPC] Sending initial presence update...")
                self.rpc_service.update_presence(
                    state="Active | Runtime: 00:00:00",
                    details="🐟 0 | 🍇 0 | ⚡ 0/hr",
                    start_timestamp=int(time.time()),
                )
                logger.info("[RPC] Initial presence sent!")
            else:
                logger.warning("[RPC] rpc_service is None - Rich Presence disabled")

            # V5.2: Discord Bot stays alive independently (started at app launch)
            # No need to start/stop bot with macro - it just relays commands

            # Reset first_run flag to trigger camera initialization
            self.first_run = True
            # Reset first_catch to skip counting on first pre_cast
            self.first_catch = True

            # Start main loop thread FIRST (Phase 7: delegated to Core Engine)
            if not self.engine.start():
                logger.error("[Start] ❌ Engine failed to start!")
                self.running = False
                self.status_label.configure(
                    text="Status: STOPPED", text_color="#ff4444"
                )
                self.start_button.configure(text="▶ START")
                self.info_label.configure(
                    text="❌ Failed to start engine", text_color=self.error_color
                )
                return
            logger.info("[Start] ✅ Engine started successfully")
            self.watchdog.log_event("_actually_start_macro:ENGINE_OK")

            # Only minimize and show HUD AFTER engine confirmed running
            self.root.iconify()
            self.show_hud()
            self.watchdog.log_event("_actually_start_macro:HUD_SHOWN")

    def _actually_stop_macro(self):
        """Actually stop the macro (NON-BLOCKING — never freezes GUI)"""
        global stats_manager

        # Diagnostic logging
        self.watchdog.log_event("_actually_stop_macro:ENTER", f"running={self.running}")

        # Guard against double-stop
        if not self.running:
            logger.debug("[Stop] Already stopped, ignoring")
            return

        logger.info("[Stop] ⏹ Stopping macro...")
        # Set running flag FIRST so fishing loop can exit
        self.running = False

        # Update UI IMMEDIATELY (don't wait for engine)
        self.status_label.configure(text="Status: STOPPING...", text_color="#ffaa00")
        self.start_button.configure(text="▶ START")
        self.info_label.configure(text="⏳ Stopping macro...", text_color="#ffaa00")

        # Restore GUI window and hide HUD immediately
        self.root.deiconify()
        self.hide_hud()

        # V3 Stability: Guaranteed mouse release when stopping
        if self.mouse_pressed:
            try:
                self.mouse.left_up()
                self.mouse_pressed = False
            except:
                pass

        # Run engine stop + cleanup in background thread (NON-BLOCKING)
        def _stop_cleanup():
            try:
                # Stop engine (may take up to 3s — runs in background, NOT GUI thread)
                if hasattr(self, "engine"):
                    self.watchdog.log_event("_stop_cleanup:ENGINE_STOP_START")
                    self.engine.stop(timeout=3.0)
                    self.watchdog.log_event("_stop_cleanup:ENGINE_STOP_DONE")
            except Exception as e:
                self.watchdog.log_event("_stop_cleanup:ENGINE_STOP_ERROR", str(e))

            try:
                # V5.2: Stop Discord Rich Presence
                if self.rpc_service:
                    self.watchdog.log_event("_stop_cleanup:RPC_STOP_START")
                    self.rpc_service.clear_presence()
                    self.rpc_service.stop()
                    self.watchdog.log_event("_stop_cleanup:RPC_STOP_DONE")
            except Exception as e:
                self.watchdog.log_event("_stop_cleanup:RPC_STOP_ERROR", str(e))

            try:
                # V3 Stability: End stats session to save data
                if stats_manager and stats_manager.session_id:
                    stats_manager.end_session()
            except Exception:
                pass

            # V5.2: Discord Bot stays alive (can receive !start again)
            # Bot is only stopped on app exit (force_exit)

        # Start cleanup thread
        threading.Thread(target=_stop_cleanup, daemon=True).start()

        # Update final UI status immediately (don't wait for thread)
        self.status_label.configure(text="Status: STOPPED", text_color="#ff4444")
        self.info_label.configure(text="⏸ Macro stopped!", text_color="#ffaa00")

        # Refresh stats (safe to call from GUI thread)
        try:
            self.refresh_stats_display()
        except:
            pass

    def test_pity_fish_webhook(self):
        """[DEPRECATED] Old test method - overridden by newer version below.
        Kept as reference. The actual test_pity_fish_webhook is defined later in the class.
        """
        # This method is overridden by the one at the bottom of the class.
        # Python uses the LAST definition, so this code never executes.
        logger.debug(
            "[test_pity_fish_webhook] DEPRECATED: This should never be called (overridden)"
        )
        pass

    def toggle_area(self):
        """Toggle area active/inactive - opens Auto Craft area if Auto Craft is enabled, otherwise normal area"""
        # Check if main loop is running
        if self.running:
            self.info_label.configure(
                text="❌ Cannot open Area Selector! Stop macro first!",
                text_color="#ff4444",
            )
            return

        # If Auto Craft is enabled, open Auto Craft area instead
        if self.auto_craft_enabled:
            self.toggle_auto_craft_area()
            return

        # Normal area logic
        self.area_active = not self.area_active

        if self.area_active:
            self.area_button.configure(text="✓ ON")
            self.info_label.configure(
                text="✓ Area selector activated!", text_color="#00dd00"
            )
            self.show_area_selector()
        else:
            self.area_button.configure(text="✗ OFF")
            self.info_label.configure(
                text="✗ Area saved and closed!", text_color="#ffaa00"
            )
            self.hide_area_selector()

    def toggle_auto_craft_area(self):
        """Toggle auto craft area selector active/inactive"""
        # Check if main loop is running
        if not self.auto_craft_area_active and self.running:
            self.info_label.configure(
                text="❌ Cannot open Auto Craft Area Selector! Stop macro first!",
                text_color="#ff4444",
            )
            return

        self.auto_craft_area_active = not self.auto_craft_area_active

        if self.auto_craft_area_active:
            self.auto_craft_area_button.configure(text="✓ ON")
            self.info_label.configure(
                text="✓ Auto Craft area selector activated!", text_color="#00dd00"
            )
            self.show_auto_craft_area_selector()
        else:
            self.auto_craft_area_button.configure(text="✗ OFF")
            self.info_label.configure(
                text="✗ Auto Craft area saved and closed!", text_color="#ffaa00"
            )
            self.hide_auto_craft_area_selector()

    # ========== WEBHOOK METHODS (RESTORED - WERE DELETED BY MISTAKE) ==========
    def capture_center_screenshot(self, auto_craft_mode=False):
        """Capture screenshot of center area where character holds fruit"""
        try:
            with mss.mss() as sct:
                # Calculate center area (smaller for auto craft mode)
                if auto_craft_mode:
                    # Focused screenshot for auto craft with zoom (400x320 at 1920x1080)
                    screenshot_width = int(400 * SCREEN_WIDTH / REF_WIDTH)
                    screenshot_height = int(320 * SCREEN_HEIGHT / REF_HEIGHT)
                else:
                    # Normal screenshot (800x500 at 1920x1080)
                    screenshot_width = int(800 * SCREEN_WIDTH / REF_WIDTH)
                    screenshot_height = int(500 * SCREEN_HEIGHT / REF_HEIGHT)
                center_x = SCREEN_WIDTH // 2
                center_y = SCREEN_HEIGHT // 2

                # Manual offset for Normal Mode to look higher up
                offset_y = 0
                if not auto_craft_mode:
                    offset_y = int(100 * SCREEN_HEIGHT / REF_HEIGHT)

                monitor = {
                    "top": center_y - screenshot_height // 2 - offset_y,
                    "left": center_x - screenshot_width // 2,
                    "width": screenshot_width,
                    "height": screenshot_height,
                }

                screenshot = sct.grab(monitor)
                fd, screenshot_path = tempfile.mkstemp(prefix="fruit_", suffix=".png")
                os.close(fd)

                # Apply brightness/contrast enhancement for auto craft mode
                if auto_craft_mode:
                    from PIL import Image, ImageEnhance

                    img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                    enhancer = ImageEnhance.Brightness(img)
                    img = enhancer.enhance(1.25)
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(1.15)
                    img.save(screenshot_path, "PNG")
                else:
                    mss.tools.to_png(
                        screenshot.rgb, screenshot.size, output=screenshot_path
                    )

                return screenshot_path
        except Exception as e:
            print(f"\rError capturing screenshot: {e}", end="", flush=True)
            return None

    def send_fruit_webhook(self, screenshot_path, is_legendary=None):
        """Send Discord webhook notification - delegates to WebhookService"""
        self.webhook_service.send_fruit_webhook(
            screenshot_path=screenshot_path,
            fish_caught=self.fish_caught,
            fruits_caught=self.fruits_caught,
            start_time=self.start_time,
            override_is_legendary=is_legendary,
        )

    def check_legendary_pity_ocr(self, pity_zone):
        """OCR-based legendary pity detection - detects ONLY '0/40' number"""
        if not pity_zone:
            logger.warning("Pity zone not configured, assuming legendary fruit")
            return True

        if not self.ocr.is_available():
            logger.warning("Tesseract OCR not available, assuming legendary fruit")
            return True

        try:
            import cv2
            import re

            # Capture pity zone
            image = self.screen.capture_area(
                pity_zone["x"],
                pity_zone["y"],
                pity_zone["width"],
                pity_zone["height"],
                use_cache=False,
            )
            if image is None:
                logger.warning("Failed to capture pity zone, assuming legendary fruit")
                return True

            # Simple preprocessing: grayscale + 2x upscale only
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            height, width = gray.shape
            upscaled = cv2.resize(
                gray, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC
            )

            # OCR with PSM 7 (single line) + whitelist for numbers and slash
            text, confidence = self.ocr.perform_ocr(
                upscaled,
                timeout_ms=1500,
                psm_mode=7,
                preprocess=False,
                char_whitelist="0123456789/",
            )

            if not text or not text.strip():
                logger.debug("Pity OCR: No text detected")
                return False

            # Clean text
            clean_text = text.strip().replace(" ", "")

            logger.info(f"Pity OCR detected: '{clean_text}'")
            print(f"\r[Pity OCR] '{clean_text}'", end="", flush=True)

            # Match ONLY 0/40 (nothing else)
            if re.fullmatch(r"0/40", clean_text):
                print(f"\n{'='*60}")
                print(f"🌟 LEGENDARY PITY 0/40 DETECTED!")
                print(f"✅ This is a Legendary/Mythical fruit!")
                print(f"{'='*60}\n")
                logger.info("✅ LEGENDARY PITY 0/40 confirmed")
                return True
            else:
                logger.debug(f"Pity text does not match 0/40: '{clean_text}'")
                return False

        except Exception as e:
            logger.error(f"Error checking legendary pity: {e}", exc_info=True)
            return True  # Default to True on error

    def toggle_auto_craft(self):
        """Toggle auto craft feature on/off"""
        # Check if trying to enable auto craft while auto buy bait is on
        if self.auto_craft_enabled_var.get() and self.auto_buy_bait:
            self.auto_craft_enabled_var.set(False)
            self.info_label.configure(
                text="❌ Cannot enable Auto Craft! Auto Buy Bait is active. Disable it first.",
                text_color="#ff4444",
            )
            return

        self.auto_craft_enabled = self.auto_craft_enabled_var.get()
        self.save_auto_craft_settings()
        if self.auto_craft_enabled:
            self.info_label.configure(
                text="✓ Auto Craft enabled!", text_color="#00dd00"
            )
        else:
            self.info_label.configure(
                text="✗ Auto Craft disabled!", text_color="#ffaa00"
            )

    # ============================================================
    # PHASE 6 INTEGRATION: Removed duplicated methods
    # ============================================================
    # The following 7 methods have been extracted to automation/fishing_cycle.py:
    # - main_loop()
    # - pre_cast()
    # - buy_common_bait()
    # - esperar()
    # - pesca()
    # - auto_craft_pre_cast()
    # - auto_craft_esperar()
    # - auto_craft_pesca()
    #
    # The following 6 helper methods have also been extracted:
    # - handle_anti_macro_detection()
    # - check_color_in_image()
    # - crop_vertical_line()
    # - find_topmost_bottommost_color()
    # - crop_vertical_section()
    # (Note: find_biggest_black_group was already moved to the end of the file)
    #
    # Total lines removed: ~1,871 lines
    # All functionality is now delegated to self.fishing_cycle.main_loop()
    # ============================================================

    def force_exit(self):
        """Force exit the application - guaranteed to exit within 2 seconds"""
        logger.info("[EXIT] Force exit requested")
        if hasattr(self, "watchdog"):
            self.watchdog.log_event("force_exit:ENTER")
        # Set running flag first
        self.running = False

        # Run cleanup in a thread with a hard deadline
        def cleanup_and_exit():
            try:
                # Stop engine (short timeout)
                if hasattr(self, "engine"):
                    self.engine.stop(timeout=1.0)
            except Exception:
                pass
            try:
                # Stop Discord RPC
                if hasattr(self, "rpc_service") and self.rpc_service:
                    self.rpc_service.clear_presence()
                    self.rpc_service.stop()
            except Exception:
                pass
            try:
                # Stop Discord Bot
                if hasattr(self, "bot_service") and self.bot_service:
                    self.bot_service.stop()
            except Exception:
                pass
            try:
                if self.listener:
                    self.listener.stop()
            except Exception:
                pass
            # Force exit regardless
            os._exit(0)

        # Start cleanup in daemon thread
        cleanup_thread = threading.Thread(target=cleanup_and_exit, daemon=True)
        cleanup_thread.start()

        # Hard deadline: if cleanup takes too long, force exit anyway
        def hard_exit():
            os._exit(0)

        # Schedule hard exit after 2 seconds as failsafe
        try:
            self.root.after(2000, hard_exit)
        except Exception:
            os._exit(0)

    def refresh_stats_display(self):
        """Refresh the stats tab display with current data"""
        global stats_manager
        if stats_manager is None:
            stats_manager = StatsManager(
                db_path=os.path.join(BASE_DIR, "fishing_stats.db")
            )

        try:
            # Update today's summary
            today = stats_manager.get_today_summary()
            self.today_sessions_label.configure(text=str(today["sessions"]))
            self.today_fish_label.configure(text=str(today["fish"]))
            self.today_fruits_label.configure(text=str(today["fruits"]))

            # Calculate rate if there's session time
            if self.start_time and self.running:
                elapsed_hours = (time.time() - self.start_time) / 3600
                if elapsed_hours > 0:
                    rate = int(self.fish_caught / elapsed_hours)
                    self.today_rate_label.configure(text=f"{rate}/h")

            # Update history
            for widget in self.history_container.winfo_children():
                widget.destroy()

            history = stats_manager.get_historical(7)
            for day_data in history:
                row = ctk.CTkFrame(self.history_container, fg_color="transparent")
                row.pack(fill="x", pady=1)
                ctk.CTkLabel(
                    row,
                    text=day_data["date"],
                    width=100,
                    anchor="w",
                    font=("Segoe UI", 9),
                ).pack(side="left")
                ctk.CTkLabel(
                    row, text=str(day_data["fish"]), width=60, font=("Segoe UI", 9)
                ).pack(side="left")
                ctk.CTkLabel(
                    row, text=str(day_data["fruits"]), width=60, font=("Segoe UI", 9)
                ).pack(side="left")
        except Exception as e:
            logger.error(f"Error refreshing stats: {e}")

    def export_stats_csv(self):
        """Export stats to CSV file"""
        global stats_manager
        if stats_manager is None:
            stats_manager = StatsManager(
                db_path=os.path.join(BASE_DIR, "fishing_stats.db")
            )

        try:
            filepath = os.path.join(
                BASE_DIR,
                f"fishing_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            )
            if stats_manager.export_csv(filepath):
                self.info_label.configure(
                    text=f"Exported to {os.path.basename(filepath)}",
                    text_color=self.success_color,
                )
            else:
                self.info_label.configure(
                    text="Export failed", text_color=self.error_color
                )
        except Exception as e:
            logger.error(f"Export error: {e}")

    def start_cycle_timer(self):
        """Start timing a fishing cycle"""
        self.cycle_start_time = time.time()

    def end_cycle_timer(self):
        """End timing a fishing cycle and update average"""
        if self.cycle_start_time is not None:
            cycle_time = time.time() - self.cycle_start_time
            self.cycle_times.append(cycle_time)

            # Keep only last 20 cycles for rolling average
            if len(self.cycle_times) > 20:
                self.cycle_times.pop(0)

            # Calculate average
            self.average_cycle_time = sum(self.cycle_times) / len(self.cycle_times)
            self.cycle_start_time = None

    # ========== CORE ENGINE CALLBACKS ==========

    def _on_engine_state_change(self, old_state, new_state):
        """Callback when engine state changes"""
        logger.debug(f"Engine state: {old_state} → {new_state}")
        # Additional GUI updates can be added here if needed

    def _on_engine_start(self):
        """Callback when engine successfully starts"""
        logger.info("Engine started callback - macro is now running")
        # GUI already updated in start_macro(), but this confirms thread started

    def _on_engine_stop(self):
        """Callback when engine successfully stops"""
        logger.info("Engine stopped callback - macro has cleanly shutdown")
        # Additional cleanup can be added here if needed

    def _on_engine_error(self, exception):
        """Callback when engine encounters an error"""
        logger.error(f"Engine error callback: {exception}", exc_info=True)
        # Show error to user
        try:
            self.info_label.configure(
                text=f"Engine error: {str(exception)[:50]}", text_color=self.error_color
            )
        except:
            pass  # GUI might be destroyed

    def on_closing(self):
        """Handle window close button"""
        self.force_exit()

    def show_hud(self):
        """Show the minimalist statistics HUD"""
        if self.hud_window is None:
            self.hud_window = tk.Toplevel(self.root)
            self.hud_window.title("Stats")
            self.hud_window.attributes("-topmost", True)
            self.hud_window.overrideredirect(True)
            self.hud_window.configure(bg="#141414")

            # Main container
            main_frame = tk.Frame(
                self.hud_window,
                bg="#141414",
                bd=1,
                relief="solid",
                highlightbackground="#2a2a2a",
                highlightthickness=1,
            )
            main_frame.pack(fill=tk.BOTH, expand=True)

            # Header with drag functionality
            header = tk.Frame(main_frame, bg="#1e1e1e", height=22)
            header.pack(fill=tk.X)
            header.pack_propagate(False)

            title = tk.Label(
                header,
                text="BPS Macro",
                font=("Segoe UI", 9, "bold"),
                fg="#f5f5f5",
                bg="#1e1e1e",
            )
            title.pack(side=tk.LEFT, padx=8, pady=3)

            # Status dot
            self.hud_status_dot = tk.Label(
                header, text="●", font=("Arial", 8), fg="#34d399", bg="#1e1e1e"
            )
            self.hud_status_dot.pack(side=tk.RIGHT, padx=8)

            # Stats container
            stats = tk.Frame(main_frame, bg="#141414")
            stats.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

            # Row 1: Time and FPS
            row1 = tk.Frame(stats, bg="#141414")
            row1.pack(fill=tk.X, pady=1)
            self.hud_time_label = tk.Label(
                row1,
                text="00:00:00",
                font=("Consolas", 11, "bold"),
                fg="#f5f5f5",
                bg="#141414",
            )
            self.hud_time_label.pack(side=tk.LEFT)
            self.hud_fps_label = tk.Label(
                row1, text="0 FPS", font=("Consolas", 9), fg="#606060", bg="#141414"
            )
            self.hud_fps_label.pack(side=tk.RIGHT)

            # Row 2: Fish and Fruits
            row2 = tk.Frame(stats, bg="#141414")
            row2.pack(fill=tk.X, pady=2)
            self.hud_fish_label = tk.Label(
                row2, text="Fish: 0", font=("Segoe UI", 10), fg="#a0a0a0", bg="#141414"
            )
            self.hud_fish_label.pack(side=tk.LEFT)
            self.hud_fruits_label = tk.Label(
                row2,
                text="Fruits: 0",
                font=("Segoe UI", 10),
                fg="#a0a0a0",
                bg="#141414",
            )
            self.hud_fruits_label.pack(side=tk.RIGHT)

            # Row 3: Rates
            row3 = tk.Frame(stats, bg="#141414")
            row3.pack(fill=tk.X, pady=1)
            self.hud_fish_rate_label = tk.Label(
                row3, text="0 Fish/h", font=("Segoe UI", 9), fg="#00cc88", bg="#141414"
            )
            self.hud_fish_rate_label.pack(side=tk.LEFT)
            self.hud_fruit_rate_label = tk.Label(
                row3, text="0 Fruit/h", font=("Segoe UI", 9), fg="#00cc88", bg="#141414"
            )
            self.hud_fruit_rate_label.pack(side=tk.RIGHT)

            # Separator
            sep = tk.Frame(stats, bg="#2a2a2a", height=1)
            sep.pack(fill=tk.X, pady=4)

            # Activity/Log label
            self.hud_activity_label = tk.Label(
                stats,
                text="Idle",
                font=("Segoe UI", 9),
                fg="#a0a0a0",
                bg="#141414",
                anchor="w",
                wraplength=180,
            )
            self.hud_activity_label.pack(fill=tk.X)

            # Smart Bait decision info
            self.hud_smart_bait_label = tk.Label(
                stats,
                text="",
                font=("Segoe UI", 8),
                fg="#00cc88",
                bg="#141414",
                anchor="w",
                wraplength=180,
            )
            self.hud_smart_bait_label.pack(fill=tk.X, pady=(2, 0))

            # Position HUD
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            hud_width = 200
            hud_height = 130

            if self.hud_position == "top":
                x = (screen_width - hud_width) // 2
                y = 10
            elif self.hud_position == "bottom-left":
                x = 10
                y = screen_height - hud_height - 50
            else:
                x = screen_width - hud_width - 10
                y = screen_height - hud_height - 50

            self.hud_window.geometry(f"{hud_width}x{hud_height}+{x}+{y}")
            self.update_hud()

    def hide_hud(self):
        """Hide the statistics HUD"""
        if self.hud_window is not None:
            self.hud_window.destroy()
            self.hud_window = None

    def update_hud(self):
        """Update HUD with current statistics"""
        if self.hud_window is not None and self.running:
            try:
                # Calculate elapsed time excluding paused time
                current_time = time.time()
                elapsed = current_time - self.start_time - self.total_paused_time

                # If currently paused, show current pause in real-time
                if self.paused and self.pause_start_time:
                    current_pause = current_time - self.pause_start_time
                    elapsed -= current_pause

                hours = int(elapsed // 3600)
                minutes = int((elapsed % 3600) // 60)
                seconds = int(elapsed % 60)
                elapsed_hours = elapsed / 3600.0

                # Calculate rates
                fish_per_hour = (
                    int(self.fish_caught / elapsed_hours) if elapsed_hours > 0 else 0
                )
                fruits_per_hour = (
                    int(self.fruits_caught / elapsed_hours) if elapsed_hours > 0 else 0
                )

                # Update labels - clean format without emojis
                if (
                    hasattr(self, "hud_time_label")
                    and self.hud_time_label.winfo_exists()
                ):
                    self.hud_time_label.config(
                        text=f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    )
                if (
                    hasattr(self, "hud_fish_label")
                    and self.hud_fish_label.winfo_exists()
                ):
                    self.hud_fish_label.config(text=f"Fish: {self.fish_caught}")
                if (
                    hasattr(self, "hud_fruits_label")
                    and self.hud_fruits_label.winfo_exists()
                ):
                    self.hud_fruits_label.config(text=f"Fruits: {self.fruits_caught}")

                # Update rates
                if (
                    hasattr(self, "hud_fish_rate_label")
                    and self.hud_fish_rate_label.winfo_exists()
                ):
                    self.hud_fish_rate_label.config(text=f"{fish_per_hour} Fish/h")
                if (
                    hasattr(self, "hud_fruit_rate_label")
                    and self.hud_fruit_rate_label.winfo_exists()
                ):
                    self.hud_fruit_rate_label.config(text=f"{fruits_per_hour} Fruit/h")

                # Update status dot color - yellow if paused, green if running, red if stopped
                if (
                    hasattr(self, "hud_status_dot")
                    and self.hud_status_dot.winfo_exists()
                ):
                    if self.paused:
                        self.hud_status_dot.configure(fg="#fbbf24")  # Yellow for paused
                    elif self.running:
                        self.hud_status_dot.configure(fg="#34d399")  # Green for running
                    else:
                        self.hud_status_dot.configure(fg="#f87171")  # Red for stopped
            except Exception as e:
                # Widget destroyed - stop updating
                pass

            # Activity text - truncate if needed (thread-safe read)
            with self.status_lock:
                current_status = self.current_status

            # Show PAUSED in activity if paused
            if self.paused:
                activity = "⏸ PAUSED"
            else:
                activity = (
                    current_status[:25] + "..."
                    if len(current_status) > 25
                    else current_status
                )
            self.hud_activity_label.configure(text=activity)

            # FPS - only show during active minigame detection
            # Reset FPS if not in minigame (elapsed > 2 seconds since last update)
            fps_elapsed = time.time() - self.fps_last_time
            if fps_elapsed > 2.0:
                # Not actively detecting - reset FPS to 0
                display_fps = 0
            else:
                # Active detection - show current FPS (max 999 for display)
                display_fps = min(self.detection_fps, 999)

            if hasattr(self, "hud_fps_label"):
                self.hud_fps_label.configure(text=f"{display_fps:.0f} FPS")

            # Update main window activity
            if hasattr(self, "activity_label"):
                self.activity_label.configure(
                    text=f"Activity: {current_status}",
                    text_color=self.success_color if self.running else "#60a5fa",
                )

            # Next update in 500ms ONLY if HUD still exists
            if self.hud_window is not None:
                self.root.after(500, self.update_hud)

    def toggle_always_on_top(self):
        """Toggle always on top"""
        self.always_on_top = self.always_on_top_var.get()
        self.root.attributes("-topmost", self.always_on_top)
        self.save_always_on_top()

    def toggle_sound_notification(self):
        """V3: Toggle sound notification for fruit detection"""
        self.sound_enabled = self.sound_enabled_var.get()
        self.save_sound_settings()
        self.audio_service.set_enabled(self.sound_enabled)
        logger.info(
            f"Sound notification {'enabled' if self.sound_enabled else 'disabled'}"
        )

    def save_sound_settings(self):
        """V3: Save sound settings to settings file"""
        try:
            self.settings.save_sound_settings(
                self.sound_enabled, self.sound_frequency, self.sound_duration
            )
            # Update audio service
            self.audio_service.update_settings(
                sound_enabled=self.sound_enabled,
                sound_frequency=self.sound_frequency,
                sound_duration=self.sound_duration,
            )
            logger.info("Sound settings saved successfully")
        except Exception as e:
            logger.error(f"Unexpected error saving sound settings: {e}", exc_info=True)

    def play_notification_sound(self):
        """V3: Play notification sound - delegates to AudioService"""
        self.audio_service.play_notification_sound()

    def toggle_auto_buy_bait(self):
        """Toggle auto buy bait section visibility"""
        # Check if trying to enable auto buy bait while auto craft is on
        if self.auto_buy_bait_var.get() and self.auto_craft_enabled:
            self.auto_buy_bait_var.set(False)
            self.info_label.configure(
                text="Cannot enable Auto Buy Bait! Auto Craft is active.",
                text_color=self.current_colors["error"],
            )
            return

        self.auto_buy_bait = self.auto_buy_bait_var.get()
        if self.auto_buy_bait:
            # Pack after the warning label to maintain position
            self.auto_bait_section.pack(
                fill=tk.X, pady=5, padx=12, after=self.auto_bait_warning
            )
        else:
            self.auto_bait_section.pack_forget()
        self.save_precast_settings()

    def toggle_auto_store_fruit(self):
        """Toggle auto store fruit section visibility"""
        self.auto_store_fruit = self.auto_store_fruit_var.get()
        if self.auto_store_fruit:
            self.auto_fruit_section.pack(
                fill=tk.X, pady=5, padx=15, after=self.auto_fruit_checkbox
            )
        else:
            self.auto_fruit_section.pack_forget()
        self.save_precast_settings()

    def toggle_store_in_inventory(self):
        """Toggle store in inventory section visibility"""
        self.store_in_inventory = self.store_in_inventory_var.get()
        if self.store_in_inventory:
            self.inventory_fruit_section.pack(fill=tk.X, pady=5, padx=10)
        else:
            self.inventory_fruit_section.pack_forget()
        self.save_precast_settings()

    def start_inventory_fruit_point_selection(self):
        """Start selecting inventory fruit point based on mouse click"""
        self.area_selector = tk.Toplevel(self.root)
        self.area_selector.attributes("-alpha", 0.3)
        self.area_selector.attributes("-fullscreen", True)
        self.area_selector.attributes("-topmost", True)
        self.area_selector.configure(bg="blue")
        self.area_selector.title("Select Inventory Fruit Point")

        # Label with instructions
        label = tk.Label(
            self.area_selector,
            text="Click on the EMPTY SLOT in your inventory where you want the fruit to be",
            font=("Arial", 24, "bold"),
            fg="white",
            bg="blue",
        )
        label.pack(expand=True)

        self.selecting_inventory_fruit_point = True

        def on_click(event):
            if self.selecting_inventory_fruit_point:
                self.inventory_fruit_point = {"x": event.x, "y": event.y}
                self.inventory_fruit_point_label.configure(
                    text=f"({event.x}, {event.y})", text_color="#00dd00"
                )
                self.selecting_inventory_fruit_point = False
                self.save_precast_settings()
                self.area_selector.destroy()
                self.area_selector = None

                # Bring back main window
                self.root.deiconify()
                self.root.attributes("-topmost", True)
                if not self.always_on_top:
                    self.root.after(
                        500, lambda: self.root.attributes("-topmost", False)
                    )

        self.area_selector.bind("<Button-1>", on_click)
        # Hide main window
        self.root.withdraw()

    def start_inventory_center_point_selection(self):
        """Start selecting inventory center point based on mouse click"""
        self.area_selector = tk.Toplevel(self.root)
        self.area_selector.attributes("-alpha", 0.3)
        self.area_selector.attributes("-fullscreen", True)
        self.area_selector.attributes("-topmost", True)
        self.area_selector.configure(bg="blue")
        self.area_selector.title("Select Center Point")

        # Label with instructions
        label = tk.Label(
            self.area_selector,
            text="Click on the CENTER of the screen (or where you want to drop)",
            font=("Arial", 24, "bold"),
            fg="white",
            bg="blue",
        )
        label.pack(expand=True)

        self.selecting_inventory_center_point = True

        def on_click(event):
            if self.selecting_inventory_center_point:
                self.inventory_center_point = {"x": event.x, "y": event.y}
                self.inventory_center_point_label.configure(
                    text=f"({event.x}, {event.y})", text_color="#00dd00"
                )
                self.selecting_inventory_center_point = False
                self.save_precast_settings()
                self.area_selector.destroy()
                self.area_selector = None

                # Bring back main window
                self.root.deiconify()
                self.root.attributes("-topmost", True)
                if not self.always_on_top:
                    self.root.after(
                        500, lambda: self.root.attributes("-topmost", False)
                    )

        self.area_selector.bind("<Button-1>", on_click)
        # Hide main window
        self.root.withdraw()

    def toggle_auto_select_top_bait(self):
        """Toggle auto select top bait section visibility"""
        self.auto_select_top_bait = self.auto_select_top_bait_var.get()
        if self.auto_select_top_bait:
            self.auto_top_bait_section.pack(
                fill=tk.X, pady=5, padx=15, after=self.auto_top_bait_checkbox
            )
        else:
            self.auto_top_bait_section.pack_forget()
        self.save_precast_settings()

    def save_hud_position(self):
        """Save HUD position to settings file"""
        try:
            # Convert user-friendly name to internal format
            position_map = {
                "Top": "top",
                "Bottom Left": "bottom-left",
                "Bottom Right": "bottom-right",
            }
            self.hud_position = position_map.get(self.hud_position_var.get(), "top")
            self.settings.save_hud_position(self.hud_position)

            self.info_label.configure(
                text="✓ HUD position saved! Restart macro to apply.",
                text_color="#00dd00",
            )
        except Exception as e:
            self.info_label.configure(
                text=f"❌ Error saving HUD position: {e}", text_color="#ff4444"
            )

    def save_always_on_top(self):
        """Save always on top setting to settings file"""
        try:
            self.settings.save_always_on_top(self.always_on_top)
        except Exception as e:
            print(f"Error saving always_on_top: {e}")

    # ============================================================================
    # V3.1: EXPORT/IMPORT CONFIG FUNCTIONS
    # ============================================================================
    def export_config(self):
        """V3.1: Export current settings to a user-selected file"""
        try:
            from tkinter import filedialog

            # Open file dialog to choose save location
            filepath = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Export Configuration",
                initialfile="bps_fishing_config_export.json",
            )

            if not filepath:
                return  # User cancelled

            # Copy current settings file to the selected location
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    config_data = json.load(f)

                # Add export metadata
                config_data["_export_info"] = {
                    "version": "V3.1",
                    "exported_at": datetime.now().isoformat(),
                    "screen_resolution": f"{SCREEN_WIDTH}x{SCREEN_HEIGHT}",
                }

                with open(filepath, "w") as f:
                    json.dump(config_data, f, indent=4)

                self.info_label.configure(
                    text=f"✓ Config exported successfully!", text_color="#00dd00"
                )
                logger.info(f"Config exported to: {filepath}")
            else:
                self.info_label.configure(
                    text="❌ No settings file found to export!", text_color="#ff4444"
                )
        except Exception as e:
            self.info_label.configure(
                text=f"❌ Export error: {e}", text_color="#ff4444"
            )
            logger.error(f"Export config error: {e}")

    def import_config(self):
        """V3.1: Import settings from a user-selected file"""
        try:
            from tkinter import filedialog, messagebox

            # Open file dialog to choose file to import
            filepath = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Import Configuration",
            )

            if not filepath:
                return  # User cancelled

            # Read and validate the imported file
            with open(filepath, "r") as f:
                imported_data = json.load(f)

            # Comprehensive validation
            expected_keys = ["area_coords", "water_point", "casting_settings"]
            valid_keys_found = sum(1 for key in expected_keys if key in imported_data)

            if valid_keys_found == 0:
                self.info_label.configure(
                    text="❌ Invalid config file - missing core settings!",
                    text_color="#ff4444",
                )
                logger.error(
                    f"Import failed: config missing core keys. Found keys: {list(imported_data.keys())}"
                )
                return

            # Validate critical coordinates if present
            if "area_coords" in imported_data and not validate_area_coords(
                imported_data["area_coords"], SCREEN_WIDTH, SCREEN_HEIGHT
            ):
                self.info_label.configure(
                    text="❌ Invalid area coordinates in config!", text_color="#ff4444"
                )
                logger.error(
                    f"Import failed: invalid area_coords {imported_data['area_coords']}"
                )
                return

            if "water_point" in imported_data and not validate_coordinates(
                imported_data["water_point"], "water_point", SCREEN_WIDTH, SCREEN_HEIGHT
            ):
                self.info_label.configure(
                    text="❌ Invalid water point in config!", text_color="#ff4444"
                )
                logger.error(
                    f"Import failed: invalid water_point {imported_data['water_point']}"
                )
                return

            # Validate webhook settings if present
            if "webhook_settings" in imported_data:
                webhook_url = imported_data["webhook_settings"].get("webhook_url", "")
                if webhook_url and not validate_webhook_url(webhook_url):
                    logger.warning(
                        f"Import warning: invalid webhook URL will be imported: {webhook_url[:50]}..."
                    )

                user_id = imported_data["webhook_settings"].get("user_id", "")
                if user_id and not validate_user_id(user_id):
                    logger.warning(
                        f"Import warning: invalid user ID will be imported: {user_id}"
                    )

            # Confirm with user
            if not messagebox.askyesno(
                "Import Configuration",
                f"Import configuration from '{os.path.basename(filepath)}'?\n\n"
                + "This will overwrite your current settings.\n"
                + "The application will need to restart to apply all changes.",
            ):
                return

            # Remove export metadata before saving
            if "_export_info" in imported_data:
                del imported_data["_export_info"]

            # Write to settings file
            with open(SETTINGS_FILE, "w") as f:
                json.dump(imported_data, f, indent=4)

            self.info_label.configure(
                text="✓ Config imported! Restart to apply.", text_color="#00dd00"
            )
            logger.info(f"Config imported from: {filepath}")

            # Ask to restart
            if messagebox.askyesno(
                "Restart Required",
                "Restart application now to apply imported settings?",
            ):
                self.on_closing()

        except json.JSONDecodeError:
            self.info_label.configure(
                text="❌ Invalid JSON file!", text_color="#ff4444"
            )
        except Exception as e:
            self.info_label.configure(
                text=f"❌ Import error: {e}", text_color="#ff4444"
            )
            logger.error(f"Import config error: {e}")

    def save_item_hotkeys(self):
        """Save item hotkeys to settings file"""
        try:
            self.rod_hotkey = self.rod_hotkey_var.get()
            self.everything_else_hotkey = self.everything_else_hotkey_var.get()
            self.fruit_hotkey = self.fruit_hotkey_var.get()

            self.settings.save_item_hotkeys(
                self.rod_hotkey, self.everything_else_hotkey, self.fruit_hotkey
            )

            self.info_label.configure(
                text="✓ Item hotkeys saved!",
                text_color=self.current_colors["success"],
            )
        except Exception as e:
            self.info_label.configure(
                text=f"❌ Error saving: {e}", text_color=self.current_colors["error"]
            )

    def save_disable_normal_camera(self):
        """Save disable_normal_camera setting to settings file"""
        self.disable_normal_camera = self.disable_normal_camera_var.get()
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
            else:
                data = {}

            if "advanced_settings" not in data:
                data["advanced_settings"] = {}

            data["advanced_settings"][
                "disable_normal_camera"
            ] = self.disable_normal_camera

            with open(SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=4)

            if self.disable_normal_camera:
                self.info_label.configure(
                    text="OK: Camera/zoom/rotation DISABLED in normal mode!",
                    text_color="#00dd00",
                )
            else:
                self.info_label.configure(
                    text="OK: Camera/zoom/rotation ENABLED in normal mode!",
                    text_color="#00dd00",
                )
        except Exception as e:
            self.info_label.configure(text=f"Error saving: {e}", text_color="#ff4444")

    def save_precast_settings(self):
        """Save precast settings to settings file"""
        precast_dict = {
            "auto_buy_bait": self.auto_buy_bait,
            "auto_store_fruit": self.auto_store_fruit,
            "yes_button": self.yes_button,
            "middle_button": self.middle_button,
            "no_button": self.no_button,
            "loops_per_purchase": self.loops_per_purchase,
            "fruit_point": self.fruit_point,
            "fruit_color": self.fruit_color,
            "auto_select_top_bait": self.auto_select_top_bait,
            "top_bait_point": self.top_bait_point,
            "store_in_inventory": self.store_in_inventory,
            "inventory_fruit_point": self.inventory_fruit_point,
            "inventory_center_point": self.inventory_center_point,
        }
        self.settings.save_precast_settings(precast_dict)

        # Sync coordinates with automation modules
        if hasattr(self, "bait_manager") and self.bait_manager:
            self.bait_manager.update_coords(top_bait_point=self.top_bait_point)

        if hasattr(self, "fruit_handler") and self.fruit_handler:
            self.fruit_handler.update_coords(
                fruit_point=self.fruit_point,
                inventory_fruit_point=self.inventory_fruit_point,
                inventory_center_point=self.inventory_center_point,
            )

        if hasattr(self, "fishing_cycle") and self.fishing_cycle:
            self.fishing_cycle.update_coords(
                top_bait_point=self.top_bait_point,
                fruit_point=self.fruit_point,
                inventory_fruit_point=self.inventory_fruit_point,
                inventory_center_point=self.inventory_center_point,
                yes_button=self.yes_button,
                middle_button=self.middle_button,
                no_button=self.no_button,
            )

        # Update bait_manager with new settings if it exists
        if hasattr(self, "bait_manager"):
            self.bait_manager.update_settings(precast_dict)
            logger.info("Bait manager settings updated")

        # Update fruit_handler with new settings if it exists
        if hasattr(self, "fruit_handler"):
            self.fruit_handler.update_settings(precast_dict)
            logger.info("Fruit handler settings updated")

    # ========== V4: SMART BAIT SYSTEM ==========
    def save_smart_bait_settings(self):
        """Save Smart Bait settings to settings file"""
        try:
            smart_bait_dict = {
                "enabled": self.smart_bait_enabled,
                "mode": self.smart_bait_mode,
                "legendary_target": self.smart_bait_legendary_target,
                "ocr_timeout_ms": self.smart_bait_ocr_timeout,
                "ocr_confidence_min": self.smart_bait_ocr_confidence,
                "fallback_bait": self.smart_bait_fallback,
                "debug_screenshots": self.smart_bait_debug,
                "use_ocr": self.smart_bait_use_ocr,
                "menu_zone": self.smart_bait_menu_zone,
                "top_bait_scan_zone": self.smart_bait_top_zone,
                "mid_bait_scan_zone": self.smart_bait_mid_zone,
            }
            self.settings.save_smart_bait_settings(smart_bait_dict)

            # Sync settings with BaitManager
            if hasattr(self, "bait_manager") and self.bait_manager:
                self.bait_manager.update_settings(smart_bait_dict)
        except Exception as e:
            print(f"Error saving smart bait settings: {e}")

    def _detect_bait_color_by_hsv(
        self, zone, zone_name="unknown", update_label_callback=None
    ):
        """Detect bait color using HSV analysis (shared implementation for top/mid zones).

        Args:
            zone: dict with x, y, width, height for bait detection area
            zone_name: str for logging (e.g., 'top', 'mid')
            update_label_callback: optional function(bait_type) to update UI label

        Returns: 'legendary', 'rare', 'common', or None if undetermined.
        """
        if not zone:
            logger.debug(f"Smart Bait {zone_name}: zone not configured")
            return None

        # Capture zone
        image = self.screen.capture_area(
            zone["x"], zone["y"], zone["width"], zone["height"], use_cache=False
        )
        if image is None:
            logger.debug(f"Smart Bait {zone_name}: failed to capture zone")
            return None

        # Convert BGRA→RGB
        if image.shape[2] == 4:
            image = image[:, :, :3]
        image = image[:, :, [2, 1, 0]]

        # Check dependencies
        available, _ = ensure_ocr_dependencies()
        if not available:
            logger.debug(f"Smart Bait {zone_name}: cv2/numpy not available")
            return None

        import importlib

        cv2 = importlib.import_module("cv2")
        np = importlib.import_module("numpy")

        # Convert to HSV and extract channels
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV).astype(np.float32)
        hues = hsv[:, :, 0].flatten()  # 0..180 in OpenCV
        sats = hsv[:, :, 1].flatten() / 255.0
        vals = hsv[:, :, 2].flatten() / 255.0

        # Mask out dark/low-saturation pixels (background noise)
        mask = (sats > 0.2) & (vals > 0.2)
        if np.count_nonzero(mask) > 0:
            hues_m = hues[mask]
            sats_m = sats[mask]
        else:
            hues_m = hues
            sats_m = sats

        # Calculate circular hue variance (1 - resultant length)
        angles = hues_m / 180.0 * 2 * np.pi
        mean_x = np.mean(np.cos(angles))
        mean_y = np.mean(np.sin(angles))
        r = np.sqrt(mean_x**2 + mean_y**2)
        hue_var = 1 - r

        sat_mean = float(np.mean(sats_m))

        # Find dominant hue by histogram
        hist, bins = np.histogram(hues_m, bins=36, range=(0, 180))
        dom_idx = int(np.argmax(hist))
        dom_hue = (bins[dom_idx] + bins[dom_idx + 1]) / 2.0

        logger.debug(
            f"ColorScan ({zone_name}): hue_var={hue_var:.2f}, sat_mean={sat_mean:.2f}, dom_hue={dom_hue:.0f}°"
        )

        # Heuristic classification
        bait_type = None
        if hue_var < 0.20:
            bait_type = "common"  # Low variance = solid color
        elif 85 <= dom_hue <= 155 and 0.20 <= hue_var < 0.75 and sat_mean > 0.20:
            bait_type = "rare"  # Cyan/blue gradient
        elif hue_var >= 0.75:
            bait_type = "legendary"  # High variance = rainbow
        elif sat_mean > 0.60 and (dom_hue < 85 or dom_hue > 155):
            bait_type = "legendary"  # High saturation fallback

        # Update UI label if callback provided
        if update_label_callback:
            try:
                update_label_callback(bait_type)
            except Exception:
                pass

        return bait_type

    def smart_bait_detect_top_bait_color(self):
        """Detect which bait is on top using color analysis (no OCR).

        Returns: 'legendary', 'rare', 'common', or None if undetermined.
        """
        # Early return if zone not configured (performance)
        if not self.smart_bait_top_zone:
            return None

        # Performance: Use cached result if recent (500ms)
        now = time.time()
        if (
            self._color_cache_result is not None
            and (now - self._color_cache_time) < self._color_cache_ttl
        ):
            return self._color_cache_result

        # Update UI label callback
        def update_top_label(bait_type):
            if (
                hasattr(self, "smart_bait_top_hint_label")
                and self.smart_bait_top_hint_label
            ):
                txt = bait_type if bait_type else "n/a"
                color = {
                    "legendary": "#ff66ff",
                    "rare": "#55ccff",
                    "common": "#dddddd",
                }.get(bait_type, "#aaaaaa")
                self.smart_bait_top_hint_label.configure(
                    text=f"Last detected (top): {txt}", text_color=color
                )

        # Delegate to shared HSV detection
        bait_type = self._detect_bait_color_by_hsv(
            self.smart_bait_top_zone,
            zone_name="top",
            update_label_callback=update_top_label,
        )

        # Cache result for performance (500ms TTL)
        self._color_cache_result = bait_type
        self._color_cache_time = time.time()

        return bait_type

    def smart_bait_detect_mid_bait_color(self, mid_zone):
        """Detect mid bait color using the same heuristics as top.

        Args:
            mid_zone: dict with x, y, width, height for mid bait area

        Returns: 'legendary', 'rare', 'common', or None if undetermined.
        """

        # Update UI label callback
        def update_mid_label(bait_type):
            if (
                hasattr(self, "smart_bait_mid_hint_label")
                and self.smart_bait_mid_hint_label
            ):
                txt = bait_type if bait_type else "n/a"
                color = {
                    "legendary": "#ff66ff",
                    "rare": "#55ccff",
                    "common": "#dddddd",
                }.get(bait_type, "#aaaaaa")
                self.smart_bait_mid_hint_label.configure(
                    text=f"Last detected (mid): {txt}", text_color=color
                )

        # Delegate to shared HSV detection
        bait_type = self._detect_bait_color_by_hsv(
            mid_zone, zone_name="mid", update_label_callback=update_mid_label
        )

        return bait_type

    def smart_bait_get_counts(self):
        """Get current bait counts from OCR by scanning full bait menu text.
        Looks for 'Legendary Fish Bait x4', 'Rare Fish Bait x5', etc.

        HYBRID STRATEGY:
        1. Try LOCAL OCR model first (fast, offline)
        2. If local OCR fails/missing models → try ONLINE OCR (slow but more accurate)
        3. Use Color Detection to VALIDATE results when available

        Returns: dict with 'legendary' and 'rare' counts (or None if failed)
        """
        counts = {"legendary": None, "rare": None, "common": None}

        if not self.smart_bait_menu_zone:
            return counts

        # Capture full bait menu area
        image = (
            self.screen.capture_area(
                self.smart_bait_menu_zone["x"],
                self.smart_bait_menu_zone["y"],
                self.smart_bait_menu_zone["width"],
                self.smart_bait_menu_zone["height"],
                use_cache=False,
            )
            if self.smart_bait_menu_zone
            else None
        )
        if image is None:
            logger.debug("Smart Bait: Failed to capture menu zone")
            return counts

        # Convert BGR to RGB (OpenCV format)
        if image.shape[2] == 4:
            image = image[:, :, :3]  # Remove alpha channel

        # Check OCR availability
        if not self.ocr.is_available():
            logger.warning("Smart Bait: Tesseract OCR not available")
            return counts

        # Call OCR extraction (now using Tesseract-based approach)
        return self._try_ocr_counting_tesseract(image)

    def _try_ocr_counting_tesseract(self, image):
        """Extract bait counts using Tesseract OCR (simplified approach)"""
        counts = {"legendary": None, "rare": None, "common": None}

        # Save debug screenshot if enabled
        if self.smart_bait_debug:
            try:
                from PIL import Image as PILImage
                import cv2

                # Convert RGB to BGR for cv2
                image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                debug_path = os.path.join(BASE_DIR, "smart_bait_debug_menu.png")
                cv2.imwrite(debug_path, image_bgr)
                logger.info(f"Debug screenshot saved: {debug_path}")
            except Exception as e:
                logger.warning(f"Failed to save debug screenshot: {e}")

        # Convert RGB image to BGR for OCR service (expects BGR)
        try:
            import cv2

            image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        except Exception as e:
            logger.error(f"Failed to convert image for OCR: {e}")
            return counts

        # Perform OCR on the full menu image
        # Note: This gives us ALL text, we need to parse it
        text, confidence = self.ocr.perform_ocr(
            image_bgr, timeout_ms=self.smart_bait_ocr_timeout
        )

        if not text:
            logger.warning("Smart Bait: Tesseract returned no text")
            return counts

        logger.debug(f"[Smart Bait OCR] Raw text: '{text}'")

        # Parse the text for bait counts
        # Expected format: "Legendary Fish Bait x4" or "Rare Fish Bait x5"
        import re

        # Strategy 1: Look for "Legendary" + number pattern
        legendary_match = re.search(
            r"(?:legendary|legend).*?(?:x|:|\s)(\d+)", text, re.IGNORECASE
        )
        rare_match = re.search(r"(?:rare).*?(?:x|:|\s)(\d+)", text, re.IGNORECASE)
        common_match = re.search(r"(?:common).*?(?:x|:|\s)(\d+)", text, re.IGNORECASE)

        if legendary_match:
            counts["legendary"] = int(legendary_match.group(1))
        if rare_match:
            counts["rare"] = int(rare_match.group(1))
        if common_match:
            counts["common"] = int(common_match.group(1))

        # Strategy 2: If no matches, try to extract all numbers and assume order
        if not any([legendary_match, rare_match, common_match]):
            numbers = re.findall(r"\d+", text)
            if numbers:
                try:
                    if len(numbers) >= 1:
                        counts["legendary"] = int(numbers[0])
                    if len(numbers) >= 2:
                        counts["rare"] = int(numbers[1])
                    if len(numbers) >= 3:
                        counts["common"] = int(numbers[2])
                except ValueError:
                    pass

        logger.info(
            f"[Smart Bait OCR] Detected counts: legendary={counts['legendary']}, rare={counts['rare']}, common={counts['common']}"
        )

        # Update UI counters
        try:
            if counts["legendary"] is not None:
                self.smart_bait_legendary_count_label.configure(
                    text=str(counts["legendary"]), text_color="#ffaa00"
                )
                self.smart_bait_legendary_conf_label.configure(text=f"{confidence:.2f}")

            if counts["rare"] is not None:
                self.smart_bait_rare_count_label.configure(
                    text=str(counts["rare"]), text_color="#00aaff"
                )
                self.smart_bait_rare_conf_label.configure(text=f"{confidence:.2f}")
        except Exception as e:
            logger.debug(f"Failed to update UI labels: {e}")

        return counts

    def _try_ocr_counting_old(self, image, ocr_instance):
        counts = {"legendary": None, "rare": None, "common": None}

        if not ocr_instance:
            logger.warning("Smart Bait: No OCR instance available")
            return counts

        # Save debug screenshot if enabled
        if self.smart_bait_debug:
            try:
                from PIL import Image as PILImage

                debug_path = os.path.join(BASE_DIR, "smart_bait_debug_menu.png")
                PILImage.fromarray(image).save(debug_path)
                logger.info(f"Debug screenshot saved: {debug_path}")
            except:
                pass

        # Strategy 1: Try original image with RETRY LOGIC (up to 3 attempts)
        result = None
        for attempt in range(3):
            try:
                logger.info(f"Smart Bait OCR attempt {attempt + 1}/3")
                with ThreadPoolExecutor() as executor:
                    future = executor.submit(ocr_instance, image)
                    result = future.result(timeout=self.smart_bait_ocr_timeout / 1000.0)

                if result and result[0]:  # Success - text detected
                    logger.info(f"Smart Bait OCR successful on attempt {attempt + 1}")
                    logger.info(
                        f"Smart Bait OCR raw result: boxes={len(result[0])}, texts={result[1] if len(result) > 1 else 'N/A'}"
                    )
                    break
                else:
                    logger.info(
                        f"Smart Bait OCR attempt {attempt + 1} returned no text"
                    )

                # Small delay between retries
                if attempt < 2:  # Don't delay after last attempt
                    time.sleep(0.1)

            except FuturesTimeoutError:
                logger.warning(
                    f"Smart Bait: OCR timeout on attempt {attempt + 1} ({self.smart_bait_ocr_timeout}ms)"
                )
                if attempt < 2:
                    time.sleep(0.1)
            except Exception as e:
                logger.error(f"Smart Bait: OCR error on attempt {attempt + 1}: {e}")
                if attempt < 2:
                    time.sleep(0.1)

        # Strategy 2: Preprocessed image if all original attempts failed
        if not result or not result[0]:
            logger.info(
                "Smart Bait: All original OCR attempts failed, trying preprocessing..."
            )
            if CV2_AVAILABLE:
                try:
                    import cv2

                    # Convert to grayscale
                    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
                    # Increase contrast using CLAHE
                    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                    enhanced = clahe.apply(gray)
                    # Apply adaptive threshold
                    thresh = cv2.adaptiveThreshold(
                        enhanced,
                        255,
                        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                        cv2.THRESH_BINARY,
                        11,
                        2,
                    )
                    # Invert for white text on black background
                    inverted = cv2.bitwise_not(thresh)

                    # Save preprocessed debug if enabled
                    if self.smart_bait_debug:
                        try:
                            from PIL import Image as PILImage

                            debug_path2 = os.path.join(
                                BASE_DIR, "smart_bait_debug_preprocessed.png"
                            )
                            PILImage.fromarray(inverted).save(debug_path2)
                            logger.info(
                                f"Preprocessed debug screenshot saved: {debug_path2}"
                            )
                        except Exception:
                            pass

                    # Try OCR on preprocessed image
                    with ThreadPoolExecutor() as executor:
                        future = executor.submit(ocr_instance, inverted)
                        result = future.result(
                            timeout=self.smart_bait_ocr_timeout / 1000.0
                        )

                    # DEBUG: Log preprocessed OCR result
                    if result:
                        logger.info(
                            f"Smart Bait OCR preprocessed result: boxes={len(result[0]) if result[0] else 0}, texts={result[1] if len(result) > 1 else 'N/A'}"
                        )

                    if result and result[0]:
                        logger.info("Smart Bait: Preprocessed OCR succeeded!")
                except Exception as e:
                    logger.warning(
                        f"Smart Bait: Preprocessing failed: {e}", exc_info=True
                    )
            else:
                logger.debug("Smart Bait: OpenCV (cv2) not available for preprocessing")

        if not result or not result[0]:
            logger.warning("Smart Bait: OCR returned no text (both strategies)")
            logger.warning(f"OCR result details: result={result}")
            if result:
                logger.warning(f"OCR boxes: {result[0] if len(result) > 0 else 'N/A'}")
                logger.warning(f"OCR texts: {result[1] if len(result) > 1 else 'N/A'}")
                logger.warning(f"OCR scores: {result[2] if len(result) > 2 else 'N/A'}")
            return counts

        # Helper to choose the most plausible number from multiple OCR variants
        def _pick_best_number(nums):
            """Choose best number from multiple OCR attempts of THE SAME line.

            IMPORTANT: This voting happens WITHIN a single line, not across lines.
            So legendary=6 and rare=9 will NOT interfere with each other.
            """
            if not nums:
                return None
            try:
                from collections import Counter

                c = Counter(nums)
                # Special handling for 6 vs 9 ambiguity (9 is MUCH more common in this game)
                if len(c) == 2:
                    vals = list(c.keys())
                    # If we see both 6 and 9, strongly prefer 9
                    if (
                        (6 in vals and 9 in vals)
                        or (60 in vals and 90 in vals)
                        or (16 in vals and 19 in vals)
                    ):
                        for v in vals:
                            if "9" in str(v):
                                logger.info(
                                    f"Smart Bait: Voting resolved 6vs9 ambiguity → chose {v} (candidates: {nums})"
                                )
                                return v
                # prefer most frequent; if tie, prefer larger
                best = sorted(c.items(), key=lambda kv: (-kv[1], -kv[0]))[0][0]
                return best
            except Exception:
                return nums[0]

        # Try line-based extraction first: group OCR results by Y position (top to bottom)
        # This avoids relying on the keyword "legendary" which the OCR misses due to gradient text.
        try:
            ocr_items = result[0]
            items_with_xy = []
            for itm in ocr_items:
                # RapidOCR returns [points, text, score]
                if len(itm) >= 2:
                    box = itm[0]
                    text = itm[1]
                    y_center = sum(pt[1] for pt in box) / len(box) if box else 0
                    x_center = sum(pt[0] for pt in box) / len(box) if box else 0
                    y_min = min(pt[1] for pt in box) if box else y_center
                    y_max = max(pt[1] for pt in box) if box else y_center
                    items_with_xy.append((y_center, x_center, y_min, y_max, text))
            # Sort top-to-bottom
            items_with_xy.sort(key=lambda t: t[0])
            # Group into lines by proximity in Y
            grouped_lines = []
            line_tol = 10  # pixels; tighter tolerance to avoid merging rows
            for y, x, y_min, y_max, text in items_with_xy:
                if not grouped_lines or abs(y - grouped_lines[-1]["y"]) > line_tol:
                    grouped_lines.append(
                        {
                            "y": y,
                            "y_min": y_min,
                            "y_max": y_max,
                            "items": [(x, text)],
                            "boxes": [(y_min, y_max, text)],
                        }
                    )
                else:
                    g = grouped_lines[-1]
                    g["items"].append((x, text))
                    g["boxes"].append((y_min, y_max, text))
                    g["y"] = ((g["y"] * (len(g["items"]) - 1)) + y) / len(g["items"])
                    g["y_min"] = min(g["y_min"], y_min)
                    g["y_max"] = max(g["y_max"], y_max)
            # Sort items within each line by X (left to right) and join
            for g in grouped_lines:
                g["items"].sort(key=lambda t: t[0])  # Sort by x position
                g["texts"] = [t[1] for t in g["items"]]
            line_texts = [" ".join(g["texts"]) for g in grouped_lines]
            logger.info(f"Smart Bait line texts (top->bottom): {line_texts}")

            # Color-based hint for top line (validates OCR keywords)
            top_hint = None
            try:
                top_hint = self.smart_bait_detect_top_bait_color()
                if top_hint:
                    logger.info(f"Smart Bait ColorScan hint (top): {top_hint}")
                    # Cross-validation: check if top line OCR keyword matches color
                    if len(line_texts) > 0:
                        top_text_lower = line_texts[0].lower()
                        has_leg_kw = (
                            "legendary" in top_text_lower or "legend" in top_text_lower
                        )
                        has_rare_kw = (
                            "rare" in top_text_lower and "raref" not in top_text_lower
                        )
                        has_common_kw = "common" in top_text_lower
                        # Warn if mismatch
                        if (
                            top_hint == "legendary"
                            and not has_leg_kw
                            and (has_rare_kw or has_common_kw)
                        ):
                            logger.warning(
                                f"⚠️ MISMATCH: Color={top_hint} but OCR text='{line_texts[0]}' → trusting COLOR"
                            )
                        elif (
                            top_hint == "rare"
                            and not has_rare_kw
                            and (has_leg_kw or has_common_kw)
                        ):
                            logger.warning(
                                f"⚠️ MISMATCH: Color={top_hint} but OCR text='{line_texts[0]}' → trusting COLOR"
                            )
                        elif (
                            top_hint == "common"
                            and not has_common_kw
                            and (has_leg_kw or has_rare_kw)
                        ):
                            logger.warning(
                                f"⚠️ MISMATCH: Color={top_hint} but OCR text='{line_texts[0]}' → trusting COLOR"
                            )
            except Exception as e:
                logger.debug(f"Smart Bait ColorScan hint failed: {e}")

            import re

            x_number_pattern = r"(?:[xX]\s*(\d+)|(\d+)\s*[xX])"  # supports x8 or 8x

            def _num_from_match(m):
                return int(m.group(1) or m.group(2))

            def _extract_line_number(g):
                candidates = []
                line_text = " ".join(g["texts"])
                # Try x-number pattern first
                m = re.search(x_number_pattern, line_text)
                if m:
                    candidates.append(_num_from_match(m))
                for _, _, t in g["boxes"]:
                    m2 = re.search(x_number_pattern, t)
                    if m2:
                        candidates.append(_num_from_match(m2))

                # If x-pattern failed, try to extract any standalone number (fallback)
                if not candidates:
                    # Look for standalone numbers (2-4 digits)
                    standalone_pattern = r"\b(\d{1,4})\b"
                    for match in re.finditer(standalone_pattern, line_text):
                        num = int(match.group(1))
                        if 1 <= num <= 9999:  # Reasonable bait count range
                            candidates.append(num)

                if candidates:
                    return _pick_best_number(candidates), candidates

                # band OCR on this line with multiple preprocessing strategies
                try:
                    band_pad = 2  # Reduced padding to avoid capturing adjacent lines
                    y0 = max(int(g["y_min"]) - band_pad, 0)
                    y1 = min(int(g["y_max"]) + band_pad, image.shape[0])
                    # Focus on rightmost 35% where numbers typically appear
                    x0 = int(image.shape[1] * 0.65)
                    x1 = image.shape[1]
                    line_crop = image[y0:y1, x0:x1]

                    # Try multiple preprocessing variants for band OCR
                    band_variants = [line_crop]
                    if CV2_AVAILABLE:
                        import cv2

                        # Convert to grayscale
                        gray = cv2.cvtColor(line_crop, cv2.COLOR_RGB2GRAY)
                        # Variant 1: CLAHE + adaptive threshold
                        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                        enhanced = clahe.apply(gray)
                        thresh1 = cv2.adaptiveThreshold(
                            enhanced,
                            255,
                            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                            cv2.THRESH_BINARY,
                            11,
                            2,
                        )
                        band_variants.append(cv2.bitwise_not(thresh1))
                        # Variant 2: Simple threshold
                        _, thresh2 = cv2.threshold(
                            gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
                        )
                        band_variants.append(cv2.bitwise_not(thresh2))
                        # Variant 3: Upscale 2x for better OCR
                        upscaled = cv2.resize(
                            gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC
                        )
                        band_variants.append(upscaled)

                    # Try OCR on all variants and collect candidates
                    band_candidates = []
                    for variant in band_variants:
                        try:
                            with ThreadPoolExecutor() as executor:
                                future = executor.submit(ocr_instance, variant)
                                sub_result = future.result(
                                    timeout=self.smart_bait_ocr_timeout / 1000.0
                                )
                            if sub_result and sub_result[0]:
                                sub_text = " ".join(
                                    [itm[1] for itm in sub_result[0] if len(itm) >= 2]
                                )
                                # Try x-pattern first
                                m2 = re.search(x_number_pattern, sub_text)
                                if m2:
                                    band_candidates.append(_num_from_match(m2))
                                # Also try standalone numbers
                                for m in re.finditer(r"\b(\d{1,4})\b", sub_text):
                                    num = int(m.group(1))
                                    if 1 <= num <= 9999:
                                        band_candidates.append(num)
                        except:
                            pass

                    if band_candidates:
                        logger.debug(
                            f"Smart Bait: Band OCR candidates from {len(band_variants)} variants: {band_candidates}"
                        )
                        return _pick_best_number(band_candidates), band_candidates
                except Exception as sub_e:
                    logger.debug(f"Smart Bait: line-band OCR failed: {sub_e}")
                return None, []

            def _has_kw(text, kw):
                return kw in text.lower()

            # Filter out header lines (lines without x-number patterns AND without bait keywords)
            # Keep lines that have: x-number pattern OR bait keywords (legendary/rare/common)
            bait_lines = []
            for g in grouped_lines:
                line_text = " ".join(g["texts"])
                line_lower = line_text.lower()
                # Keep if has x-number pattern OR has bait keyword
                has_number = re.search(x_number_pattern, line_text)
                has_keyword = (
                    "legendary" in line_lower
                    or "rare" in line_lower
                    or "common" in line_lower
                )
                if has_number or has_keyword:
                    bait_lines.append(g)

            if bait_lines:
                logger.info(
                    f"Smart Bait: Filtered {len(bait_lines)} bait lines (skipped {len(grouped_lines) - len(bait_lines)} header lines)"
                )
            else:
                logger.warning("Smart Bait: No bait lines found!")
                bait_lines = grouped_lines  # Fallback to all lines

            # Three lines detected: standard mapping
            if len(bait_lines) >= 3:
                bait_order = ["legendary", "rare", "common"]
                for idx, g in enumerate(bait_lines[:3]):
                    if counts[bait_order[idx]] is not None:
                        continue
                    val, cand = _extract_line_number(g)
                    if val is not None:
                        counts[bait_order[idx]] = val
                        logger.info(
                            f"Smart Bait: {bait_order[idx].capitalize()} = {counts[bait_order[idx]]} (line-based, voted {cand})"
                        )
                # Optional: validate mid zone if configured (for debug purposes)
                logger.info(
                    f"Smart Bait: smart_bait_mid_zone = {self.smart_bait_mid_zone}"
                )
                if self.smart_bait_mid_zone:
                    logger.info(
                        f"Smart Bait: Calling mid zone validation (3-line case)"
                    )
                    try:
                        mid_hint = self.smart_bait_detect_mid_bait_color(
                            self.smart_bait_mid_zone
                        )
                        logger.info(
                            f"Smart Bait: Mid zone validation result: {mid_hint}"
                        )
                    except Exception as e:
                        logger.info(f"Smart Bait: Mid zone validation failed: {e}")
                else:
                    logger.info("Smart Bait: mid_zone not configured (3-line case)")
            # Two lines: use keywords plus color hint; fallback assume top=Rare, bottom=Common
            elif len(bait_lines) == 2:
                top, mid = bait_lines[0], bait_lines[1]
                top_text = " ".join(top["texts"])
                mid_text = " ".join(mid["texts"])
                top_leg = _has_kw(top_text, "legendary")
                top_rare = _has_kw(top_text, "rare")
                top_common = _has_kw(top_text, "common")
                mid_leg = _has_kw(mid_text, "legendary")
                mid_rare = _has_kw(mid_text, "rare")
                mid_common = _has_kw(mid_text, "common")

                # Apply color hint when present
                if top_hint == "legendary":
                    top_leg = True
                elif top_hint == "rare":
                    top_rare = True
                elif top_hint == "common":
                    top_common = True

                # If top_hint was legendary, try color scan on bottom to determine rare vs common
                mid_hint = None
                if top_hint == "legendary" and self.smart_bait_mid_zone:
                    try:
                        mid_hint = self.smart_bait_detect_mid_bait_color(
                            self.smart_bait_mid_zone
                        )
                    except Exception as e:
                        logger.debug(f"Smart Bait: mid-line color scan failed: {e}")
                elif top_hint == "legendary":
                    try:
                        # Fallback: estimate mid zone from OCR line position if not configured
                        mid_y_min = int(mid["y_min"])
                        mid_y_max = int(mid["y_max"])
                        pad = 4
                        mid_zone = {
                            "x": (
                                self.smart_bait_top_zone["x"]
                                if self.smart_bait_top_zone
                                else 0
                            ),
                            "y": max(mid_y_min - pad, 0),
                            "width": (
                                self.smart_bait_top_zone["width"]
                                if self.smart_bait_top_zone
                                else 200
                            ),
                            "height": min(mid_y_max + pad, image.shape[0])
                            - max(mid_y_min - pad, 0),
                        }
                        mid_hint = self.smart_bait_detect_mid_bait_color(mid_zone)
                    except Exception as e:
                        logger.debug(f"Smart Bait: mid-line color scan failed: {e}")

                # Legend present on top (by keyword or color)
                if top_leg:
                    if counts["legendary"] is None:
                        val, cand = _extract_line_number(top)
                        if val is not None:
                            counts["legendary"] = val
                            logger.info(
                                f"Smart Bait: Legendary = {val} (2-line, top, voted {cand})"
                            )
                    # Use mid_hint if available, else keyword, else default
                    if mid_hint:
                        target = mid_hint
                    else:
                        target = (
                            "rare" if mid_rare else ("common" if mid_common else "rare")
                        )
                    if counts[target] is None:
                        val, cand = _extract_line_number(mid)
                        if val is not None:
                            counts[target] = val
                            logger.info(
                                f"Smart Bait: {target.capitalize()} = {val} (2-line, bottom, voted {cand})"
                            )
                # Top is rare (by keyword or color): map top->Rare, bottom->Common
                elif top_rare and not top_common:
                    if counts["rare"] is None:
                        val, cand = _extract_line_number(top)
                        if val is not None:
                            counts["rare"] = val
                            logger.info(
                                f"Smart Bait: Rare = {val} (2-line, top-as-rare, voted {cand})"
                            )
                    if counts["common"] is None:
                        val, cand = _extract_line_number(mid)
                        if val is not None:
                            counts["common"] = val
                            logger.info(
                                f"Smart Bait: Common = {val} (2-line, bottom-as-common, voted {cand})"
                            )
                # Top is common (unlikely layout, but handle): map top->Common, bottom->Rare if keyword says so
                elif top_common:
                    if counts["common"] is None:
                        val, cand = _extract_line_number(top)
                        if val is not None:
                            counts["common"] = val
                            logger.info(
                                f"Smart Bait: Common = {val} (2-line, top-as-common, voted {cand})"
                            )
                    if counts["rare"] is None:
                        val, cand = _extract_line_number(mid)
                        if val is not None:
                            counts["rare"] = val
                            logger.info(
                                f"Smart Bait: Rare = {val} (2-line, bottom-as-rare, voted {cand})"
                            )
                # No keywords nor hint: default assumption top=Rare, bottom=Common
                else:
                    if counts["rare"] is None:
                        val, cand = _extract_line_number(top)
                        if val is not None:
                            counts["rare"] = val
                            logger.info(
                                f"Smart Bait: Rare = {val} (2-line, default top-as-rare, voted {cand})"
                            )
                    if counts["common"] is None:
                        val, cand = _extract_line_number(mid)
                        if val is not None:
                            counts["common"] = val
                            logger.info(
                                f"Smart Bait: Common = {val} (2-line, default bottom-as-common, voted {cand})"
                            )
            # One line: use keywords if present, else use color hint
            elif len(bait_lines) == 1:
                only = bait_lines[0]
                only_text = " ".join(only["texts"])
                bait_detected = None

                if _has_kw(only_text, "legendary"):
                    bait_detected = "legendary"
                elif _has_kw(only_text, "rare"):
                    bait_detected = "rare"
                elif _has_kw(only_text, "common"):
                    bait_detected = "common"
                # Fallback to color hint if no keyword
                elif top_hint:
                    bait_detected = top_hint

                if bait_detected:
                    val, cand = _extract_line_number(only)
                    if val is not None and counts[bait_detected] is None:
                        counts[bait_detected] = val
                        logger.info(
                            f"Smart Bait: {bait_detected.capitalize()} = {val} (1-line, voted {cand})"
                        )
                else:
                    logger.debug(
                        "Smart Bait: Single line without keyword or color hint; skipping assignment"
                    )
        except Exception as e:
            import traceback

            logger.error(f"Smart Bait: line-based extraction failed: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")

        # Fallback: OCR faixa direita do terço superior (Legendary) e meio (Rare)
        if counts["legendary"] is None:
            try:
                h, w = image.shape[0], image.shape[1]
                y0, y1 = 0, max(4, int(h / 3))
                x0, x1 = int(w * 0.48), w  # capture a wider band on the right
                band = image[y0:y1, x0:x1]
                band_variants = [band]
                try:
                    if CV2_AVAILABLE:
                        import cv2

                        gray = cv2.cvtColor(band, cv2.COLOR_RGB2GRAY)
                        clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(8, 8))
                        enhanced = clahe.apply(gray)
                        kernels = [
                            cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)),
                            cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)),
                        ]
                        for bs in (9, 11, 13):
                            thresh = cv2.adaptiveThreshold(
                                enhanced,
                                255,
                                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY,
                                bs,
                                2,
                            )
                            inv = cv2.bitwise_not(thresh)
                            band_variants.append(inv)
                            _, otsu = cv2.threshold(
                                enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
                            )
                            band_variants.append(cv2.bitwise_not(otsu))
                            for scale in (2.0, 2.5, 3.0):
                                up = cv2.resize(
                                    inv,
                                    None,
                                    fx=scale,
                                    fy=scale,
                                    interpolation=cv2.INTER_CUBIC,
                                )
                                band_variants.append(up)
                                for k in kernels:
                                    closed = cv2.morphologyEx(up, cv2.MORPH_CLOSE, k)
                                    band_variants.append(closed)
                except Exception:
                    pass
                import re

                num_pattern = r"(?:[xX]\s*(\d+)|(\d+)\s*[xX])"

                def _parse_num(s):
                    m = re.search(num_pattern, s)
                    return int(m.group(1) or m.group(2)) if m else None

                band_candidates = []
                for variant in band_variants:
                    with ThreadPoolExecutor() as executor:
                        future = executor.submit(ocr_instance, variant)
                        sub_result = future.result(
                            timeout=self.smart_bait_ocr_timeout / 1000.0
                        )
                    if sub_result and sub_result[0]:
                        sub_text = " ".join(
                            [itm[1] for itm in sub_result[0] if len(itm) >= 2]
                        )
                        num_val = _parse_num(sub_text)
                        if num_val is not None:
                            band_candidates.append(num_val)
                val = _pick_best_number(band_candidates)
                if val is not None:
                    counts["legendary"] = val
                    logger.info(
                        f"Smart Bait: Legendary = {counts['legendary']} (top-band OCR, voted {band_candidates})"
                    )
            except Exception as sub_e:
                logger.debug(f"Smart Bait: top-band OCR failed: {sub_e}")

        if counts["rare"] is None:
            logger.info(
                "Smart Bait: Rare still None after line-based OCR, trying mid-band fallback..."
            )
            try:
                h, w = image.shape[0], image.shape[1]
                y0, y1 = int(h / 3), int(h * 2 / 3)
                x0, x1 = int(w * 0.48), w  # wider band
                band = image[y0:y1, x0:x1]
                band_variants = [band]
                try:
                    if CV2_AVAILABLE:
                        import cv2

                        gray = cv2.cvtColor(band, cv2.COLOR_RGB2GRAY)
                        clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(8, 8))
                        enhanced = clahe.apply(gray)
                        kernels = [
                            cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)),
                            cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)),
                        ]
                        for bs in (9, 11, 13):
                            thresh = cv2.adaptiveThreshold(
                                enhanced,
                                255,
                                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY,
                                bs,
                                2,
                            )
                            inv = cv2.bitwise_not(thresh)
                            band_variants.append(inv)
                            # Otsu variants
                            _, otsu = cv2.threshold(
                                enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
                            )
                            band_variants.append(cv2.bitwise_not(otsu))
                            for scale in (2.0, 2.5, 3.0):
                                up = cv2.resize(
                                    inv,
                                    None,
                                    fx=scale,
                                    fy=scale,
                                    interpolation=cv2.INTER_CUBIC,
                                )
                                band_variants.append(up)
                                for k in kernels:
                                    closed = cv2.morphologyEx(up, cv2.MORPH_CLOSE, k)
                                    band_variants.append(closed)
                except Exception:
                    pass
                import re

                num_pattern = r"(?:[xX]\s*(\d+)|(\d+)\s*[xX])"

                def _parse_num(s):
                    m = re.search(num_pattern, s)
                    return int(m.group(1) or m.group(2)) if m else None

                band_candidates = []
                for variant in band_variants:
                    with ThreadPoolExecutor() as executor:
                        future = executor.submit(ocr_instance, variant)
                        sub_result = future.result(
                            timeout=self.smart_bait_ocr_timeout / 1000.0
                        )
                    if sub_result and sub_result[0]:
                        sub_text = " ".join(
                            [itm[1] for itm in sub_result[0] if len(itm) >= 2]
                        )
                        num_val = _parse_num(sub_text)
                        if num_val is not None:
                            band_candidates.append(num_val)
                val = _pick_best_number(band_candidates)
                if val is not None:
                    counts["rare"] = val
                    logger.info(
                        f"Smart Bait: Rare = {counts['rare']} (mid-band OCR, voted {band_candidates})"
                    )
            except Exception as sub_e:
                logger.debug(f"Smart Bait: mid-band OCR failed: {sub_e}")

        # Extract all text into one string
        full_text = ""
        for item in result[0]:
            if len(item) >= 2:
                full_text += " " + item[1]

        full_text_lower = full_text.lower()
        logger.info(f"Smart Bait OCR RAW text: '{full_text}'")
        logger.info(f"Smart Bait OCR LOWER text: '{full_text_lower}'")

        # Search for bait counts using improved pattern matching
        # STRATEGY: Look for "x" followed by numbers (e.g., "x4", "x120")
        # The "x" is consistently read, numbers after "x" are blue and clear
        import re

        # AGGRESSIVE OCR error recovery: Some digits misread (6↔9, 0↔O, 3↔E, 1↔I, 5↔S)
        recovery_text = full_text
        recovery_map = {
            "O": "0",  # O → 0 (very common)
            "E": "3",  # E might be 3
            "l": "1",  # lowercase L → 1
            "I": "1",  # uppercase I → 1
        }

        # Try variants: original + corrections
        variants_to_try = [full_text]  # Original first

        # Try applying individual character replacements
        for char_from, char_to in recovery_map.items():
            variant = full_text.replace(char_from, char_to)
            if variant != full_text and variant not in variants_to_try:
                variants_to_try.append(variant)

        # Find all number-with-x patterns in all variants
        # Support: X, x, × (unicode multiplication)
        x_number_pattern = r"(?:[xX×]\s*(\d+)|(\d+)\s*[xX×])"

        def _num_from_match(m):
            """Extract number from regex match object"""
            return int(m.group(1) or m.group(2))

        # Collect ORIGINAL matches (for position-based extraction)
        original_matches = list(re.finditer(x_number_pattern, full_text))

        logger.info(f"Smart Bait OCR extraction (original + recovery attempts):")
        logger.info(f"  Original text: {full_text}")
        logger.info(
            f"  Original matches: {[(m.group(), _num_from_match(m)) for m in original_matches]}"
        )
        if len(variants_to_try) > 1:
            logger.info(
                f"  Trying {len(variants_to_try)-1} recovery variants due to potential OCR errors"
            )

        # Use ORIGINAL matches for position-based extraction
        # Find positions of bait type keywords (case insensitive)
        legendary_pos = full_text_lower.find("legendary")
        rare_pos = full_text_lower.find("rare")
        common_pos = full_text_lower.find("common")

        # Extract Legendary: first "xN" pattern AFTER "legendary" and BEFORE "rare"
        if counts["legendary"] is None and legendary_pos != -1:
            for match in original_matches:
                match_pos = match.start()
                if match_pos > legendary_pos:
                    # Check if this match is before rare (if rare exists)
                    if rare_pos == -1 or match_pos < rare_pos:
                        counts["legendary"] = _num_from_match(match)
                        logger.info(
                            f"Smart Bait: Found Legendary = {counts['legendary']} from pattern '{match.group()}'"
                        )
                        break

        # Extract Rare: first "xN" pattern AFTER "rare" and BEFORE "common"
        if counts["rare"] is None and rare_pos != -1:
            for match in original_matches:
                match_pos = match.start()
                if match_pos > rare_pos:
                    # Check if this match is before common (if common exists)
                    if common_pos == -1 or match_pos < common_pos:
                        counts["rare"] = _num_from_match(match)
                        logger.info(
                            f"Smart Bait: Found Rare = {counts['rare']} from pattern '{match.group()}'"
                        )
                        break

        # Extract Common: first "xN" pattern AFTER "common"
        if counts["common"] is None and common_pos != -1:
            for match in original_matches:
                match_pos = match.start()
                if match_pos > common_pos:
                    counts["common"] = _num_from_match(match)
                    logger.info(
                        f"Smart Bait: Found Common = {counts['common']} from pattern '{match.group()}'"
                    )
                    break

        # FALLBACK with error recovery: If position-based matching failed, use recovery variants
        # This handles cases where OCR errors prevent keyword detection
        if (
            counts["legendary"] is None
            or counts["rare"] is None
            or counts["common"] is None
        ):
            logger.info(
                "Smart Bait: Position-based extraction incomplete, trying recovery variants..."
            )
            for variant in variants_to_try[1:]:  # Skip original (already tried)
                variant_matches = list(re.finditer(x_number_pattern, variant))
                variant_lower = variant.lower()

                if counts["legendary"] is None and "legendary" in variant_lower:
                    leg_pos = variant_lower.find("legendary")
                    for match in variant_matches:
                        if match.start() > leg_pos and (
                            rare_pos == -1 or match.start() < variant_lower.find("rare")
                        ):
                            counts["legendary"] = _num_from_match(match)
                            logger.info(
                                f"Smart Bait: RECOVERED Legendary = {counts['legendary']} from variant"
                            )
                            break

                if counts["rare"] is None and "rare" in variant_lower:
                    rare_pos_var = variant_lower.find("rare")
                    for match in variant_matches:
                        if match.start() > rare_pos_var and (
                            common_pos == -1
                            or match.start() < variant_lower.find("common")
                        ):
                            counts["rare"] = _num_from_match(match)
                            logger.info(
                                f"Smart Bait: RECOVERED Rare = {counts['rare']} from variant"
                            )
                            break

                if counts["common"] is None and "common" in variant_lower:
                    com_pos_var = variant_lower.find("common")
                    for match in variant_matches:
                        if match.start() > com_pos_var:
                            counts["common"] = _num_from_match(match)
                            logger.info(
                                f"Smart Bait: RECOVERED Common = {counts['common']} from variant"
                            )
                            break
            # Extract all numbers from original matches
            all_numbers = [_num_from_match(m) for m in original_matches]
            logger.info(f"Smart Bait: All extracted numbers: {all_numbers}")

            if counts["legendary"] is None and counts["rare"] is None:
                # Neither found - use first two matches
                if len(all_numbers) >= 2:
                    counts["legendary"] = all_numbers[0]
                    counts["rare"] = all_numbers[1]
                    logger.info(
                        f"Smart Bait: FALLBACK - Legendary = {counts['legendary']}, Rare = {counts['rare']} (by order)"
                    )
            elif counts["legendary"] is None and counts["rare"] is not None:
                # Only Legendary missing - prefer numbers that are not obviously Common
                rare_val = counts["rare"]
                # UPDATED: Exclude known Common count from candidates
                candidates = [
                    n
                    for n in all_numbers
                    if n != rare_val
                    and (counts["common"] is None or n != counts["common"])
                ]
                for num in candidates:
                    if num <= rare_val * 3:  # heuristic: Legendary is close to Rare
                        counts["legendary"] = num
                        logger.info(
                            f"Smart Bait: FALLBACK - Legendary = {counts['legendary']} (near Rare)"
                        )
                        break
                if counts["legendary"] is None:
                    logger.info(
                        "Smart Bait: FALLBACK - Legendary still missing; likely Common only detected"
                    )
            elif counts["legendary"] is not None and counts["rare"] is None:
                # Only Rare missing - prefer numbers close to Legendary
                legendary_val = counts["legendary"]
                # UPDATED: Exclude known Common count from candidates
                candidates = [
                    n
                    for n in all_numbers
                    if n != legendary_val
                    and (counts["common"] is None or n != counts["common"])
                ]
                for num in candidates:
                    if num <= legendary_val * 3:
                        counts["rare"] = num
                        logger.info(
                            f"Smart Bait: FALLBACK - Rare = {counts['rare']} (near Legendary)"
                        )
                        break

        if counts["legendary"] is None:
            logger.warning(
                f"Smart Bait: Legendary number not found - OCR issue with gradient text"
            )
        if counts["rare"] is None:
            logger.warning(f"Smart Bait: Rare number not found")

        # Final validation: log warnings if values seem wrong
        if counts["legendary"] is not None and counts["rare"] is not None:
            # Check if legendary and rare are suspiciously close (might indicate 6vs9 swap)
            if abs(counts["legendary"] - counts["rare"]) == 3:  # e.g., 6 and 9
                # If legendary < rare, that's normal stockpiling
                # If legendary > rare by exactly 3, might be 6vs9 swap
                if counts["legendary"] - counts["rare"] == 3:
                    logger.warning(
                        f"⚠️ ALERT: Legendary ({counts['legendary']}) = Rare ({counts['rare']}) + 3 → Possible 6vs9 swap. Check 'Test OCR Now' output!"
                    )

            if counts["legendary"] > counts["rare"] * 5:
                logger.warning(
                    f"⚠️ SUSPICIOUS: Legendary ({counts['legendary']}) >> Rare ({counts['rare']}) - might be swapped!"
                )
            if counts["rare"] is not None and counts["common"] is not None:
                if counts["rare"] > counts["common"]:
                    logger.warning(
                        f"⚠️ SUSPICIOUS: Rare ({counts['rare']}) > Common ({counts['common']}) - unusual but possible"
                    )

        # Final summary
        logger.info(
            f"✅ Smart Bait Final Counts: Legendary={counts['legendary']}, Rare={counts['rare']}, Common={counts['common']}"
        )

        # Update live counter in GUI if it exists
        try:
            if hasattr(self, "smart_bait_legendary_count_label"):

                def update_gui():
                    # Update legendary
                    if counts["legendary"] is not None:
                        self.smart_bait_legendary_count_label.configure(
                            text=str(counts["legendary"]), text_color="#00dd00"
                        )
                        self.smart_bait_legendary_conf_label.configure(text="✓ Found")
                    else:
                        self.smart_bait_legendary_count_label.configure(
                            text="?", text_color="#ff4444"
                        )
                        self.smart_bait_legendary_conf_label.configure(text="Not found")

                    # Update rare
                    if counts["rare"] is not None:
                        self.smart_bait_rare_count_label.configure(
                            text=str(counts["rare"]), text_color="#00dd00"
                        )
                        self.smart_bait_rare_conf_label.configure(text="✓ Found")
                    else:
                        self.smart_bait_rare_count_label.configure(
                            text="?", text_color="#ff4444"
                        )
                        self.smart_bait_rare_conf_label.configure(text="Not found")

                self.root.after(0, update_gui)
        except:
            pass  # Ignore if GUI update fails

        return counts

    def smart_bait_decide(self, counts):
        """Decide which bait to use based on mode and counts

        Auto-switches between modes:
        - Burning: Use legendary until 1 left → switch to Stockpile
        - Stockpile: Use rare until target reached → switch to Burning

        Args:
            counts: dict with 'legendary' and 'rare' counts

        Returns:
            'legendary', 'rare', or None (use fallback)
        """
        legendary = counts.get("legendary")
        rare = counts.get("rare")

        logger.info(
            f"[Smart Bait Decision] Mode: {self.smart_bait_mode}, Legendary: {legendary}, Rare: {rare}, Target: {self.smart_bait_legendary_target}"
        )

        # Auto-switch logic based on legendary count
        if legendary is not None:
            if self.smart_bait_mode == "burning" and legendary <= 1:
                # Switch to stockpile when only 1 legendary left
                self.smart_bait_mode = "stockpile"
                try:
                    if (
                        hasattr(self, "smart_bait_mode_display_label")
                        and self.smart_bait_mode_display_label.winfo_exists()
                    ):
                        self.smart_bait_mode_display_label.configure(
                            text="STOCKPILE", text_color="#00ddff"
                        )
                except (AttributeError, tk.TclError):
                    pass
                self.save_smart_bait_settings()
                logger.warning(
                    f"🔄 AUTO-SWITCH: Burning → Stockpile (legendary: {legendary}/1)"
                )
            elif (
                self.smart_bait_mode == "stockpile"
                and legendary >= self.smart_bait_legendary_target
            ):
                # Switch to burning when target reached
                self.smart_bait_mode = "burning"
                try:
                    if (
                        hasattr(self, "smart_bait_mode_display_label")
                        and self.smart_bait_mode_display_label.winfo_exists()
                    ):
                        self.smart_bait_mode_display_label.configure(
                            text="BURNING", text_color="#ff8800"
                        )
                except (AttributeError, tk.TclError):
                    pass
                self.save_smart_bait_settings()
                logger.warning(
                    f"🔄 AUTO-SWITCH: Stockpile → Burning (legendary: {legendary}/{self.smart_bait_legendary_target})"
                )

        # Update mode display
        try:
            if hasattr(self, "smart_bait_mode_display"):
                mode_text = self.smart_bait_mode.upper()
                mode_color = (
                    "#ff8800" if self.smart_bait_mode == "burning" else "#00ddff"
                )
                self.smart_bait_mode_display.configure(
                    text=mode_text, text_color=mode_color
                )
        except:
            pass

        decision_text = ""

        if self.smart_bait_mode == "burning":
            # Burning mode: Use legendary until only 1 left (auto-switches to stockpile)
            # Priority: Legendary > Rare
            if legendary is not None and legendary > 1:
                logger.info(
                    f"[Burning] → Using legendary ({legendary} available, burning until 1)"
                )
                decision_text = f"🔥 Use legendary ({legendary} → burning until 1)"
                self._update_decision_display(decision_text, "#ffaa00")
                return "legendary"
            elif legendary == 1:
                # Last legendary - preserve it, switch to stockpile mode happens above
                logger.info(
                    "[Burning] → Last legendary detected, switching to stockpile mode"
                )
                decision_text = "⚠️ Last legendary (switching to stockpile)"
                self._update_decision_display(decision_text, "#ff8800")
                # Will use rare or fallback after mode switch
                if rare is not None and rare > 0:
                    return "rare"
                return None
            elif legendary == 0 or legendary is None:
                # No legendary, use rare if available
                if rare is not None and rare > 0:
                    logger.info("[Burning] → Using rare (no legendary)")
                    decision_text = f"Use rare ({rare} available, no legendary)"
                    self._update_decision_display(decision_text, "#00aaff")
                    return "rare"
                # Nothing available
                logger.info("[Burning] → Fallback (no baits)")
                decision_text = "Fallback (no baits)"
                self._update_decision_display(decision_text, "#888888")
                return None

        elif self.smart_bait_mode == "stockpile":
            # Stockpile mode: Use rare to accumulate legendary until target (auto-switches to burning)

            # CRITICAL: If we can't read legendary count, we cannot make stockpile decisions
            if legendary is None:
                logger.info("[Stockpile] → Fallback (legendary count unknown)")
                decision_text = "Fallback (can't read legendary)"
                self._update_decision_display(decision_text, "#ff4444")
                return None  # Fallback

            # Check if target reached - will auto-switch to burning mode above
            if legendary >= self.smart_bait_legendary_target:
                logger.info(f"[Stockpile] → Target reached, switching to burning mode")
                decision_text = f"✓ Target reached ({legendary}/{self.smart_bait_legendary_target}) → burning"
                self._update_decision_display(decision_text, "#00ff00")
                # After switch, will use legendary in burning mode
                if legendary > 1:
                    return "legendary"
                return None

            # Target NOT reached - PRESERVE legendary, use rare to accumulate
            if rare is not None and rare > 0:
                logger.info(
                    f"[Stockpile] → Using rare (accumulating: {legendary}/{self.smart_bait_legendary_target})"
                )
                decision_text = f"💎 Use rare (accumulating {legendary}/{self.smart_bait_legendary_target})"
                self._update_decision_display(decision_text, "#00aaff")
                return "rare"

            # No rare available BUT target not reached - forced to use legendary (burns stockpile)
            if legendary > 0:
                logger.warning(
                    f"[Stockpile] → Forced legendary (no rare: {legendary}/{self.smart_bait_legendary_target})"
                )
                decision_text = f"⚠️ Forced legendary (no rare, {legendary}/{self.smart_bait_legendary_target})"
                self._update_decision_display(decision_text, "#ff8800")
                return "legendary"

            # Nothing available - need to craft baits
            logger.info("[Stockpile] → Fallback (no baits available)")
            decision_text = "Fallback (no baits, craft needed)"
            self._update_decision_display(decision_text, "#888888")
            return None

        # Unknown mode
        logger.warning(f"Smart Bait: Unknown mode '{self.smart_bait_mode}'")
        decision_text = f"Unknown mode: {self.smart_bait_mode}"
        self._update_decision_display(decision_text, "#ff4444")
        return None

    def _update_decision_display(self, text, color):
        """Update decision display in UI and HUD (thread-safe via root.after)"""

        def _do_update():
            try:
                # Update Live OCR Counter (check if widget exists)
                if (
                    hasattr(self, "smart_bait_decision_display")
                    and self.smart_bait_decision_display
                ):
                    if self.smart_bait_decision_display.winfo_exists():
                        self.smart_bait_decision_display.configure(
                            text=text, text_color=color
                        )

                # Update HUD (only if it exists - it's created when macro starts)
                if (
                    hasattr(self, "hud_smart_bait_label")
                    and self.hud_smart_bait_label
                    and self.hud_window
                ):
                    try:
                        if self.hud_smart_bait_label.winfo_exists():
                            self.hud_smart_bait_label.config(
                                text=f"🎣 {text}", fg=color
                            )
                    except tk.TclError:
                        pass  # HUD widget destroyed
            except (AttributeError, tk.TclError):
                pass
            except Exception as e:
                logger.debug(f"Failed to update decision display: {e}")

        # Schedule on GUI thread (this method is called from worker thread)
        try:
            self.root.after(0, _do_update)
        except Exception:
            pass

    def smart_bait_select(self):
        """Main entry point for Smart Bait selection

        Smart Bait System developed by Murtaza:
        - OCR Mode: Counts exact bait numbers, auto-switches both directions
        - Color-Only Mode: Visual HSV detection, optimized for performance
        - Auto-cycle: Burning (use legendary) ↔ Stockpile (save legendary)

        Called from auto_craft_pre_cast after crafting, before fishing.
        This also updates the live counter automatically.

        Returns:
            dict {'x': x, 'y': y} of bait coordinates to click,
            or None if Smart Bait is disabled/failed (use default behavior)
        """
        # Gate 1: Feature enabled?
        if not self.smart_bait_enabled:
            return None

        # Gate 2: Check if OCR mode or Color-Only mode
        if not self.smart_bait_use_ocr:
            # Color-Only mode: Visual detection without counting
            # Logic:
            # - Burning: Check top slot color. If Legendary → use it. If Rare → switch to Stockpile.
            # - Stockpile: Always use rare (2nd slot) until manually switched back

            if self.smart_bait_mode == "burning":
                # Scan top slot to check if legendary is still there
                top_color = self.smart_bait_detect_top_bait_color()

                if top_color == "legendary":
                    if self.top_bait_point:
                        return self.top_bait_point
                    return self._smart_bait_get_fallback_coords()

                elif top_color == "rare":
                    # Legendary depleted! Auto-switch to stockpile mode
                    logger.warning(
                        "[Color-Only] AUTO-SWITCH: Burning → Stockpile (rare detected)"
                    )
                    self.smart_bait_mode = "stockpile"
                    if hasattr(self, "smart_bait_mode_display_label"):
                        self.smart_bait_mode_display_label.configure(
                            text="STOCKPILE", text_color="#00ddff"
                        )
                    self.save_smart_bait_settings()

                    # Use rare bait (2nd slot)
                    if self.smart_bait_2nd_coords:
                        return self.smart_bait_2nd_coords
                    return self._smart_bait_get_fallback_coords()

                else:
                    # Common or unknown - use fallback
                    return self._smart_bait_get_fallback_coords()

            elif self.smart_bait_mode == "stockpile":
                # Stockpiling: always use rare (2nd slot) to save legendary
                # User must manually switch back to burning when ready
                # PERFORMANCE: Skip color detection entirely in stockpile (always same choice)

                if self.smart_bait_2nd_coords:
                    return self.smart_bait_2nd_coords

                # Fallback: If no 2nd coords configured, use top as safety
                if self.top_bait_point:
                    logger.warning(
                        "[Color-Only Stockpile] → No 2nd slot coords, using top"
                    )
                    return self.top_bait_point

                return self._smart_bait_get_fallback_coords()

        # OCR mode: Continue with full OCR detection
        # Gate 3: OCR service available?
        if not self.ocr.is_available():
            logger.debug("Smart Bait: Tesseract OCR not available, using fallback")
            return self._smart_bait_get_fallback_coords()

        # Gate 3: Critical zones configured?
        if not self.smart_bait_menu_zone:
            logger.warning(
                "Smart Bait: Menu zone NOT configured! Please configure in UI."
            )
            return None
        if not self.smart_bait_top_zone:
            logger.warning(
                "Smart Bait: Top Label zone NOT configured! Please configure in UI."
            )
            return None
        if not self.smart_bait_mid_zone:
            logger.warning(
                "Smart Bait: Mid Label zone NOT configured! Please configure in UI."
            )
            return None

        # Execute OCR
        try:
            counts = self.smart_bait_get_counts()
        except Exception as e:
            logger.warning(f"Smart Bait: OCR scan failed: {e}")
            return self._smart_bait_get_fallback_coords()

        # Make decision
        selected_bait = self.smart_bait_decide(counts)

        if selected_bait is None:
            # Decision logic returned None = needs fallback
            logger.info(f"Smart Bait: Using fallback bait ({self.smart_bait_fallback})")
            return self._smart_bait_get_fallback_coords()

        # Get coordinates for selected bait
        # Legendary uses 'Top Bait Point' from Pre-Cast Settings
        # Rare uses 'smart_bait_2nd_coords' configured separately
        if selected_bait == "legendary":
            coords = self.top_bait_point
            logger.info(
                f"[Smart Bait Select] Decision: legendary → top_bait_point = {coords}"
            )
        elif selected_bait == "rare":
            coords = self.smart_bait_2nd_coords
            logger.info(
                f"[Smart Bait Select] Decision: rare → smart_bait_2nd_coords = {coords}"
            )
        else:
            coords = None
            logger.warning(f"[Smart Bait Select] Unknown bait type: {selected_bait}")

        if coords:
            logger.info(
                f"✅ Smart Bait: Selected {selected_bait} bait at ({coords['x']}, {coords['y']})"
            )
            return coords
        else:
            logger.error(
                f"❌ Smart Bait: No coords for {selected_bait}! Configure in UI (legendary=Top Bait, rare=2nd Bait Selection)."
            )
            return self._smart_bait_get_fallback_coords()

    def _smart_bait_get_fallback_coords(self):
        """Get fallback bait coordinates"""
        # Legendary fallback uses top_bait_point
        if self.smart_bait_fallback == "legendary" and self.top_bait_point:
            return self.top_bait_point
        elif self.smart_bait_fallback == "rare" and self.smart_bait_2nd_coords:
            return self.smart_bait_2nd_coords
        # Ultimate fallback: use top_bait_point if available
        elif self.top_bait_point:
            return self.top_bait_point
        return None

    def start_smart_bait_zone_selection(self, zone_type):
        """Start zone selection for Smart Bait OCR area

        Args:
            zone_type: 'menu', 'top', or 'mid'
        """
        self.selecting_smart_bait_zone = zone_type

        # Update UI according to zone
        if zone_type == "menu":
            self.smart_bait_menu_zone_btn.configure(
                text="Drawing...", fg_color="#ff6600"
            )
            self.smart_bait_menu_zone_label.configure(
                text="Draw rectangle (click & drag)", text_color="#ffaa00"
            )
        elif zone_type == "top":
            if hasattr(self, "smart_bait_top_zone_btn"):
                self.smart_bait_top_zone_btn.configure(
                    text="Drawing...", fg_color="#ff6600"
                )
            if hasattr(self, "smart_bait_top_zone_label"):
                self.smart_bait_top_zone_label.configure(
                    text="Draw rectangle (click & drag)", text_color="#ffaa00"
                )
        elif zone_type == "mid":
            if hasattr(self, "smart_bait_mid_zone_btn"):
                self.smart_bait_mid_zone_btn.configure(
                    text="Drawing...", fg_color="#ff6600"
                )
            if hasattr(self, "smart_bait_mid_zone_label"):
                self.smart_bait_mid_zone_label.configure(
                    text="Draw rectangle (click & drag)", text_color="#ffaa00"
                )

        # Create transparent drawing overlay
        self._create_zone_selection_overlay()

    def _create_zone_selection_overlay(self):
        """Create a fullscreen overlay for drawing zone selection rectangle"""
        try:
            overlay = tk.Toplevel(self.root)
            overlay.attributes("-fullscreen", True)
            overlay.attributes("-alpha", 0.3)
            overlay.attributes("-topmost", True)
            overlay.configure(bg="black")
            overlay.focus_force()  # Force focus to capture all events

            # Canvas for drawing
            canvas = tk.Canvas(
                overlay, bg="black", highlightthickness=0, cursor="crosshair"
            )
            canvas.pack(fill="both", expand=True)

            # Track drawing state
            draw_state = {"start": None, "rect": None, "finished": False}

            def cleanup_overlay():
                """Safely destroy overlay"""
                try:
                    if overlay.winfo_exists():
                        overlay.destroy()
                except:
                    pass

            def on_press(event):
                if draw_state["finished"]:
                    return
                draw_state["start"] = (event.x, event.y)
                draw_state["rect"] = canvas.create_rectangle(
                    event.x, event.y, event.x, event.y, outline="lime", width=3
                )

            def on_drag(event):
                if draw_state["finished"] or not draw_state["start"]:
                    return
                if draw_state["rect"]:
                    canvas.coords(
                        draw_state["rect"],
                        draw_state["start"][0],
                        draw_state["start"][1],
                        event.x,
                        event.y,
                    )

            def on_release(event):
                if draw_state["finished"]:
                    return
                draw_state["finished"] = True

                if draw_state["start"]:
                    x1, y1 = draw_state["start"]
                    x2, y2 = event.x, event.y

                    # Normalize coordinates
                    x = min(x1, x2)
                    y = min(y1, y2)
                    width = abs(x2 - x1)
                    height = abs(y2 - y1)

                    # Minimum size check
                    if width >= 10 and height >= 10:
                        zone_config = {"x": x, "y": y, "width": width, "height": height}
                        self._finish_zone_selection(zone_config)
                    else:
                        self._cancel_zone_selection()

                cleanup_overlay()

            def on_escape(event):
                if not draw_state["finished"]:
                    draw_state["finished"] = True
                    self._cancel_zone_selection()
                    cleanup_overlay()

            # Bind events
            canvas.bind("<ButtonPress-1>", on_press)
            canvas.bind("<B1-Motion>", on_drag)
            canvas.bind("<ButtonRelease-1>", on_release)
            overlay.bind("<Escape>", on_escape)

            # Unbind after first use to prevent multiple selections
            def unbind_after_release(event):
                canvas.unbind("<ButtonPress-1>")
                canvas.unbind("<B1-Motion>")
                canvas.unbind("<ButtonRelease-1>")

            self._zone_selection_overlay = overlay
        except Exception as e:
            print(f"[Smart Bait] Could not create zone overlay: {e}")
            self._cancel_zone_selection()

    def _finish_zone_selection(self, zone_config):
        """Complete zone selection and save"""
        zone_type = self.selecting_smart_bait_zone

        if zone_type == "top":
            self.smart_bait_top_zone = zone_config
            if hasattr(self, "smart_bait_top_zone_btn"):
                self.smart_bait_top_zone_btn.configure(
                    text="Select Zone", fg_color=self.button_color
                )
            if hasattr(self, "smart_bait_top_zone_label"):
                self.smart_bait_top_zone_label.configure(
                    text=f"({zone_config['x']}, {zone_config['y']}) {zone_config['width']}x{zone_config['height']}",
                    text_color="#00dd00",
                )
            self.info_label.configure(
                text="✓ Top bait label zone saved!", text_color="#00dd00"
            )
            logger.info(f"Smart Bait top label zone saved: {zone_config}")
            print(f"[Smart Bait] ✓ Top label zone saved: {zone_config}")
            # Update BaitManager with new zone
            if hasattr(self, "bait_manager") and self.bait_manager:
                self.bait_manager.top_zone = zone_config
                logger.info(f"BaitManager top_zone updated: {zone_config}")
        elif zone_type == "mid":
            self.smart_bait_mid_zone = zone_config
            if hasattr(self, "smart_bait_mid_zone_btn"):
                self.smart_bait_mid_zone_btn.configure(
                    text="Select Zone", fg_color=self.button_color
                )
            if hasattr(self, "smart_bait_mid_zone_label"):
                self.smart_bait_mid_zone_label.configure(
                    text=f"({zone_config['x']}, {zone_config['y']}) {zone_config['width']}x{zone_config['height']}",
                    text_color="#00dd00",
                )
            self.info_label.configure(
                text="✓ Mid bait label zone saved!", text_color="#00dd00"
            )
            logger.info(f"Smart Bait mid label zone saved: {zone_config}")
            print(f"[Smart Bait] ✓ Mid label zone saved: {zone_config}")
            # Update BaitManager with new zone
            if hasattr(self, "bait_manager") and self.bait_manager:
                self.bait_manager.mid_zone = zone_config
                logger.info(f"BaitManager mid_zone updated: {zone_config}")
        else:
            # Default: menu zone
            self.smart_bait_menu_zone = zone_config
            self.smart_bait_menu_zone_btn.configure(
                text="Select Zone", fg_color=self.button_color
            )
            self.smart_bait_menu_zone_label.configure(
                text=f"({zone_config['x']}, {zone_config['y']}) {zone_config['width']}x{zone_config['height']}",
                text_color="#00dd00",
            )
            self.info_label.configure(
                text="✓ Bait menu zone saved!", text_color="#00dd00"
            )
            logger.info(f"Smart Bait menu zone saved: {zone_config}")
            print(f"[Smart Bait] ✓ Menu zone saved: {zone_config}")
            # Update BaitManager with new zone
            if hasattr(self, "bait_manager") and self.bait_manager:
                self.bait_manager.menu_zone = zone_config
                logger.info(f"BaitManager menu_zone updated: {zone_config}")

        self.save_smart_bait_settings()
        self.selecting_smart_bait_zone = None

    def _zones_overlap(self, zone1, zone2):
        """Check if two zones overlap

        Args:
            zone1, zone2: dicts with x, y, width, height

        Returns:
            True if zones overlap
        """
        if not zone1 or not zone2:
            return False

        x1, y1, w1, h1 = zone1["x"], zone1["y"], zone1["width"], zone1["height"]
        x2, y2, w2, h2 = zone2["x"], zone2["y"], zone2["width"], zone2["height"]

        # Check if rectangles overlap
        return not (x1 + w1 < x2 or x2 + w2 < x1 or y1 + h1 < y2 or y2 + h2 < y1)

    def _cancel_zone_selection(self):
        """Cancel zone selection"""
        if hasattr(self, "smart_bait_menu_zone_btn"):
            self.smart_bait_menu_zone_btn.configure(
                text="Select Zone", fg_color=self.button_color
            )
            self.smart_bait_menu_zone_label.configure(
                text="Cancelled", text_color="#ff4444"
            )

        self.selecting_smart_bait_zone = None

    def toggle_smart_bait(self):
        """Toggle Smart Bait enabled state"""
        # Check if trying to enable Smart Bait while Auto Craft is OFF
        if self.smart_bait_enabled_var.get() and not self.auto_craft_enabled:
            self.smart_bait_enabled_var.set(False)
            self.info_label.configure(
                text="Cannot enable Smart Bait! Auto Craft must be active.",
                text_color=self.current_colors["error"],
            )
            return

        self.smart_bait_enabled = self.smart_bait_enabled_var.get()
        self.save_smart_bait_settings()

        status = "enabled" if self.smart_bait_enabled else "disabled"
        self.info_label.configure(
            text=f"✓ Smart Bait {status}!",
            text_color="#00dd00" if self.smart_bait_enabled else "#aaaaaa",
        )

    def show_smart_bait_startup_dialog(self):
        """Popup to choose starting mode when enabling Smart Bait"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Smart Bait - Choose Starting Mode")
        dialog.geometry("400x280")
        dialog.configure(bg="#1a1a1a")
        dialog.attributes("-topmost", True)
        dialog.resizable(False, False)

        # Center dialog
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 200
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 140
        dialog.geometry(f"+{x}+{y}")

        # Title
        title_label = ctk.CTkLabel(
            dialog,
            text="🎣 Smart Bait - Choose Starting Mode",
            font=("Arial", 14, "bold"),
            text_color="#00ff88",
        )
        title_label.pack(pady=(20, 5))

        # Subtitle
        subtitle_label = ctk.CTkLabel(
            dialog,
            text="Which bait do you want to use right now?",
            font=("Arial", 10),
            text_color="#cccccc",
        )
        subtitle_label.pack(pady=(0, 20))

        def start_burning():
            self.smart_bait_enabled = True
            self.smart_bait_mode = "burning"
            if hasattr(self, "smart_bait_mode_display_label"):
                self.smart_bait_mode_display_label.configure(
                    text="BURNING", text_color="#ff8800"
                )
            self.save_smart_bait_settings()
            # Update BaitManager mode
            if hasattr(self, "bait_manager") and self.bait_manager:
                self.bait_manager.mode = "burning"
            logger.info("Smart Bait started in BURNING mode")
            dialog.destroy()
            # Start macro after mode selection
            self.root.after(100, self._actually_start_macro)

        def start_stockpile():
            self.smart_bait_enabled = True
            self.smart_bait_mode = "stockpile"
            if hasattr(self, "smart_bait_mode_display_label"):
                self.smart_bait_mode_display_label.configure(
                    text="STOCKPILE", text_color="#00ddff"
                )
            self.save_smart_bait_settings()
            # Update BaitManager mode
            if hasattr(self, "bait_manager") and self.bait_manager:
                self.bait_manager.mode = "stockpile"
            logger.info("Smart Bait started in STOCKPILE mode")
            dialog.destroy()
            # Start macro after mode selection
            self.root.after(100, self._actually_start_macro)

        # Burning button
        burning_btn = ctk.CTkButton(
            dialog,
            text="🔥 BURNING\n(Use Legendary - I have legendaries)",
            command=start_burning,
            fg_color="#ff8800",
            hover_color="#cc6600",
            font=("Arial", 12, "bold"),
            height=70,
        )
        burning_btn.pack(fill="x", padx=30, pady=8)

        # Stockpile button
        stockpile_btn = ctk.CTkButton(
            dialog,
            text="💎 STOCKPILE\n(Save Legendary - use Rare to accumulate)",
            command=start_stockpile,
            fg_color="#00aadd",
            hover_color="#0088bb",
            font=("Arial", 12, "bold"),
            height=70,
        )
        stockpile_btn.pack(fill="x", padx=30, pady=8)

        def on_close():
            self.smart_bait_enabled_var.set(False)
            self.smart_bait_enabled = False
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_close)

    def save_smart_bait_from_ui(self):
        """Save Smart Bait settings from UI"""
        try:
            # Note: Mode is set by startup popup, not from UI
            self.smart_bait_legendary_target = int(self.smart_bait_target_entry.get())
            self.smart_bait_fallback = self.smart_bait_fallback_var.get().lower()
            self.smart_bait_debug = self.smart_bait_debug_var.get()

            # Check if OCR mode changed
            ocr_changed = self.smart_bait_use_ocr != self.smart_bait_use_ocr_var.get()
            self.smart_bait_use_ocr = self.smart_bait_use_ocr_var.get()

            # Update frame title and visibility based on OCR mode
            if ocr_changed and hasattr(self, "live_counter_frame"):
                # Update title
                if hasattr(self, "smart_bait_frame_title"):
                    title_text = (
                        "📊 Live OCR Counter & Color Preview"
                        if self.smart_bait_use_ocr
                        else "🎨 Live Color Detection"
                    )
                    self.smart_bait_frame_title.configure(text=title_text)

                # Swap test buttons
                if hasattr(self, "smart_bait_test_ocr_btn") and hasattr(
                    self, "smart_bait_test_color_btn"
                ):
                    if self.smart_bait_use_ocr:
                        self.smart_bait_test_color_btn.pack_forget()
                        self.smart_bait_test_ocr_btn.pack(pady=(5, 10))
                    else:
                        self.smart_bait_test_ocr_btn.pack_forget()
                        self.smart_bait_test_color_btn.pack(pady=(5, 10))

                # Show/hide OCR-specific elements
                if self.smart_bait_use_ocr:
                    # Show OCR counters and decision info
                    if hasattr(self, "smart_bait_counter_grid"):
                        self.smart_bait_counter_grid.pack(fill="x", padx=10, pady=5)
                    if hasattr(self, "smart_bait_decision_frame"):
                        self.smart_bait_decision_frame.pack(
                            fill="x", pady=(5, 5), padx=10
                        )
                    # Show OCR settings
                    if hasattr(self, "smart_bait_target_row"):
                        self.smart_bait_target_row.pack(fill="x", pady=5, padx=15)
                    if hasattr(self, "smart_bait_fallback_row"):
                        self.smart_bait_fallback_row.pack(fill="x", pady=5, padx=15)
                    self.info_label.configure(
                        text="✓ OCR Mode: Live counter & auto-cycle enabled",
                        text_color="#00dd00",
                    )
                else:
                    # Hide OCR counters and decision info
                    if hasattr(self, "smart_bait_counter_grid"):
                        self.smart_bait_counter_grid.pack_forget()
                    if hasattr(self, "smart_bait_decision_frame"):
                        self.smart_bait_decision_frame.pack_forget()
                    # Hide OCR settings
                    if hasattr(self, "smart_bait_target_row"):
                        self.smart_bait_target_row.pack_forget()
                    if hasattr(self, "smart_bait_fallback_row"):
                        self.smart_bait_fallback_row.pack_forget()
                    self.info_label.configure(
                        text="✓ Color-Only Mode: Live preview active (better FPS)",
                        text_color="#00ddff",
                    )

            self.save_smart_bait_settings()
            if not ocr_changed:
                self.info_label.configure(
                    text="✓ Smart Bait settings saved!", text_color="#00dd00"
                )
        except ValueError:
            self.info_label.configure(
                text="❌ Invalid values! Use numbers only.", text_color="#ff4444"
            )

    def toggle_smart_bait_auto_refresh(self):
        """Toggles auto-refresh based on checkbox state."""
        if self.smart_bait_auto_refresh_var.get():
            self.start_smart_bait_auto_refresh()
        else:
            self.stop_smart_bait_auto_refresh()

    def start_smart_bait_auto_refresh(self):
        """Start auto-refresh timer for live counter"""
        if self._smart_bait_auto_refresh_enabled:
            return  # Already running

        self._smart_bait_auto_refresh_enabled = True
        self.smart_bait_refresh_status.configure(
            text=f"⚡ Live (refreshing every {self._smart_bait_refresh_interval/1000:.1f}s)",
            text_color="#00ff00",
        )
        self._smart_bait_auto_refresh_loop()
        logger.info("✓ Smart Bait auto-refresh enabled")

    def stop_smart_bait_auto_refresh(self):
        """Stop auto-refresh timer"""
        self._smart_bait_auto_refresh_enabled = False
        if self._smart_bait_refresh_timer:
            self.root.after_cancel(self._smart_bait_refresh_timer)
            self._smart_bait_refresh_timer = None
        self.smart_bait_refresh_status.configure(
            text=f"(updates every {self._smart_bait_refresh_interval/1000:.1f}s)",
            text_color="#aaaaaa",
        )
        logger.info("○ Smart Bait auto-refresh disabled")

    def _smart_bait_auto_refresh_loop(self):
        """Auto-refresh loop - runs detection in background (OCR or Color)"""
        if not self._smart_bait_auto_refresh_enabled:
            return

        def refresh():
            try:
                # ONLY run OCR if OCR mode is enabled
                if self.smart_bait_use_ocr:
                    counts = self.smart_bait_get_counts()
                    self.root.after(0, lambda c=counts: self._update_test_ocr_ui(c))

                # ALWAYS update color preview (works in both modes)
                if self.bait_manager:
                    top_color = self.bait_manager.detect_top_bait_color()

                    # Mid detection - need to pass mid_zone dict
                    mid_color = None
                    if (
                        hasattr(self.bait_manager, "mid_zone")
                        and self.bait_manager.mid_zone
                    ):
                        mid_color = self.bait_manager.detect_mid_bait_color(
                            self.bait_manager.mid_zone
                        )

                    method = "HSV Threshold"

                    self.root.after(
                        0,
                        lambda t=top_color, m=mid_color, meth=method: self._update_color_preview(
                            t, m, meth
                        ),
                    )

            except Exception as e:
                error_msg = str(e)
                logger.debug(f"Auto-refresh error: {error_msg}")

        thread = threading.Thread(target=refresh, daemon=True)
        thread.start()

        # Schedule next refresh
        self._smart_bait_refresh_timer = self.root.after(
            self._smart_bait_refresh_interval, self._smart_bait_auto_refresh_loop
        )

    def _update_color_preview(self, top_color, mid_color, method):
        """Update the live color detection preview labels"""
        try:
            # Color mapping
            color_map = {
                "legendary": ("#ff66ff", "LEGENDARY"),
                "rare": ("#55ccff", "RARE"),
                "common": ("#dddddd", "COMMON"),
                None: ("#888888", "N/A"),
            }

            # Update TOP preview
            top_gui_color, top_text = color_map.get(top_color, ("#ff4444", "ERROR"))
            self.smart_bait_top_preview.configure(
                text=top_text, text_color=top_gui_color
            )

            # Update MID preview
            mid_gui_color, mid_text = color_map.get(mid_color, ("#888888", "N/A"))
            self.smart_bait_mid_preview.configure(
                text=mid_text, text_color=mid_gui_color
            )

            # Update method indicator
            mode_text = (
                f"OCR + {method}" if self.smart_bait_use_ocr else f"{method} Color"
            )
            self.smart_bait_method_preview.configure(text=mode_text)

        except Exception as e:
            logger.error(f"Color preview update error: {e}")

    def test_smart_bait_color(self):
        """Test Smart Bait Color Detection (Color-Only mode)"""
        logger.info("[Smart Bait Color Test] Starting color detection test...")
        if not self.bait_manager:
            self.info_label.configure(
                text="❌ Bait manager not initialized!", text_color="#ff4444"
            )
            return

        # Update preview labels to show scanning
        self.smart_bait_top_preview.configure(text="Scanning...", text_color="#ffaa00")
        self.smart_bait_mid_preview.configure(text="Scanning...", text_color="#ffaa00")
        self.root.update()

        # Run color detection in background thread
        def _run_color_detection():
            try:
                # Force fresh scan (bypass cache) for manual test
                top_color = self.bait_manager.detect_top_bait_color(force_scan=True)

                mid_color = None
                if (
                    hasattr(self.bait_manager, "mid_zone")
                    and self.bait_manager.mid_zone
                ):
                    mid_color = self.bait_manager.detect_mid_bait_color(
                        self.bait_manager.mid_zone
                    )

                method = "HSV Threshold"

                self.root.after(
                    0,
                    lambda t=top_color, m=mid_color, meth=method: self._update_color_test_result(
                        t, m, meth
                    ),
                )
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Color detection test error: {error_msg}")
                self.root.after(
                    0, lambda err=error_msg: self._update_color_test_error(err)
                )

        import threading

        threading.Thread(target=_run_color_detection, daemon=True).start()

    def _update_color_test_result(self, top_color, mid_color, method):
        """Update UI with color detection test results"""
        try:
            self._update_color_preview(top_color, mid_color, method)

            if top_color or mid_color:
                self.info_label.configure(
                    text="✓ Color detection complete!", text_color="#00dd00"
                )
            else:
                self.info_label.configure(
                    text="⚠️ No colors detected - check zones!", text_color="#ffaa00"
                )
        except Exception as e:
            self.info_label.configure(
                text=f"❌ Color test error: {e}", text_color="#ff4444"
            )

    def _update_color_test_error(self, error_msg):
        """Update UI with color detection error"""
        self.smart_bait_top_preview.configure(text="ERROR", text_color="#ff4444")
        self.smart_bait_mid_preview.configure(text="ERROR", text_color="#ff4444")
        self.info_label.configure(
            text=f"❌ Color test error: {error_msg}", text_color="#ff4444"
        )

    def test_smart_bait_ocr(self):
        """Test Smart Bait OCR and update live counter display"""
        logger.info("[Smart Bait Test] Starting OCR test scan...")
        # Reset labels
        self.smart_bait_legendary_count_label.configure(
            text="...", text_color="#ffaa00"
        )
        self.smart_bait_rare_count_label.configure(text="...", text_color="#ffaa00")
        self.smart_bait_legendary_conf_label.configure(text="scanning...")
        self.smart_bait_rare_conf_label.configure(text="scanning...")
        self.root.update()

        # Check if Tesseract OCR is available
        if not self.ocr.is_available():
            self.smart_bait_legendary_count_label.configure(
                text="N/A", text_color="#ff4444"
            )
            self.smart_bait_rare_count_label.configure(text="N/A", text_color="#ff4444")
            self.smart_bait_legendary_conf_label.configure(text="Tesseract not found")
            self.smart_bait_rare_conf_label.configure(text="Tesseract not found")
            self.info_label.configure(
                text="❌ Tesseract not found! Install from: https://github.com/UB-Mannheim/tesseract/wiki",
                text_color="#ff4444",
            )
            return

        # Check if menu zone is configured
        if not self.smart_bait_menu_zone:
            self.smart_bait_legendary_count_label.configure(
                text="N/A", text_color="#ff4444"
            )
            self.smart_bait_rare_count_label.configure(text="N/A", text_color="#ff4444")
            self.smart_bait_legendary_conf_label.configure(
                text="Menu zone not configured"
            )
            self.smart_bait_rare_conf_label.configure(text="Menu zone not configured")
            self.info_label.configure(
                text="❌ Configure bait menu zone first!", text_color="#ff4444"
            )
            return

        # Run OCR in background thread to prevent UI freeze
        def _run_ocr_background():
            try:
                # Run OCR scan - uses the new smart_bait_get_counts which updates GUI automatically
                counts = self.smart_bait_get_counts()

                # Schedule UI update on main thread
                self.root.after(0, lambda c=counts: self._update_test_ocr_ui(c))
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Smart Bait Test OCR error: {error_msg}")
                self.root.after(
                    0, lambda err=error_msg: self._update_test_ocr_error(err)
                )

        # Start background thread
        import threading

        threading.Thread(target=_run_ocr_background, daemon=True).start()

    def _update_test_ocr_ui(self, counts):
        """Update UI with OCR results (called from main thread)"""
        try:
            # Update the decision display with test data
            decision = self.smart_bait_decide(counts)

            if counts["legendary"] is not None or counts["rare"] is not None:
                self.info_label.configure(
                    text="✓ OCR scan complete!", text_color="#00dd00"
                )
            else:
                self.info_label.configure(
                    text="No baits detected - check console log", text_color="#ffaa00"
                )
                print(
                    "[Smart Bait] OCR did not find bait text. Check console log for what OCR read."
                )

        except Exception as e:
            self.smart_bait_legendary_count_label.configure(
                text="ERR", text_color="#ff4444"
            )
            self.smart_bait_rare_count_label.configure(text="ERR", text_color="#ff4444")
            self.smart_bait_legendary_conf_label.configure(text=str(e)[:30])
            self.smart_bait_rare_conf_label.configure(text="")
            self.info_label.configure(
                text=f"❌ OCR test error: {e}", text_color="#ff4444"
            )

    def _update_test_ocr_error(self, error_msg):
        """Update UI with OCR error (called from main thread)"""
        self.smart_bait_legendary_count_label.configure(
            text="ERR", text_color="#ff4444"
        )
        self.smart_bait_rare_count_label.configure(text="ERR", text_color="#ff4444")
        self.smart_bait_legendary_conf_label.configure(text=error_msg[:30])
        self.smart_bait_rare_conf_label.configure(text="")
        self.info_label.configure(
            text=f"❌ OCR test error: {error_msg}", text_color="#ff4444"
        )

    def save_loops_setting(self):
        """Save loops per purchase setting"""
        try:
            self.loops_per_purchase = int(self.loops_entry.get())
            self.save_precast_settings()
            self.info_label.configure(
                text="✓ Loops per purchase saved!",
                text_color=self.current_colors["success"],
            )
        except ValueError:
            self.info_label.configure(
                text="❌ Invalid value! Use numbers only.",
                text_color=self.current_colors["error"],
            )

    def save_pid_settings(self):
        """Save PID settings to settings file"""
        try:
            self.settings.save_pid_settings(self.pid_kp, self.pid_kd, self.pid_clamp)
        except Exception as e:
            print(f"Error saving PID settings: {e}")

    def save_pid_from_ui(self):
        """Save PID settings from UI entries"""
        try:
            self.pid_kp = float(self.kp_entry.get())
            self.pid_kd = float(self.kd_entry.get())
            self.pid_clamp = float(self.clamp_entry.get())
            self.save_pid_settings()
            self.info_label.configure(text="✓ PD settings saved!", text_color="#00dd00")
        except ValueError:
            self.info_label.configure(
                text="❌ Invalid PD values! Use numbers only.", text_color="#ff4444"
            )

    def save_fishing_end_delay_from_ui(self):
        """V3: Save fishing end delay from UI entry"""
        try:
            self.fishing_end_delay = float(self.fishing_end_delay_entry.get())
            self.save_casting_settings()
            logger.info(f"Fishing end delay saved: {self.fishing_end_delay}s")
        except ValueError as e:
            logger.error(f"Invalid fishing end delay value: {e}")

    def save_advanced_settings(self):
        """Save advanced timing settings from UI to settings file"""
        try:
            # Read values from UI
            self.camera_rotation_delay = float(self.camera_rotation_delay_entry.get())
            self.camera_rotation_steps = int(self.camera_rotation_steps_entry.get())
            self.camera_rotation_step_delay = float(
                self.camera_rotation_step_delay_entry.get()
            )
            self.camera_rotation_settle_delay = float(
                self.camera_rotation_settle_delay_entry.get()
            )

            self.zoom_ticks = int(self.zoom_ticks_entry.get())
            self.zoom_tick_delay = float(self.zoom_tick_delay_entry.get())
            self.zoom_settle_delay = float(self.zoom_settle_delay_entry.get())

            self.pre_cast_minigame_wait = float(self.pre_cast_minigame_wait_entry.get())
            self.store_click_delay = float(self.store_click_delay_entry.get())
            self.backspace_delay = float(self.backspace_delay_entry.get())
            self.rod_deselect_delay = float(self.rod_deselect_delay_entry.get())
            self.rod_select_delay = float(self.rod_select_delay_entry.get())
            self.bait_click_delay = float(self.bait_click_delay_entry.get())

            self.fruit_detection_delay = float(self.fruit_detection_delay_entry.get())
            self.fruit_detection_settle = float(self.fruit_detection_settle_entry.get())
            self.general_action_delay = float(self.general_action_delay_entry.get())
            self.mouse_move_settle = float(self.mouse_move_settle_entry.get())
            self.focus_settle_delay = float(self.focus_settle_delay_entry.get())

            # Save to file via settings manager
            advanced_dict = {
                "camera_rotation_delay": self.camera_rotation_delay,
                "camera_rotation_steps": self.camera_rotation_steps,
                "camera_rotation_step_delay": self.camera_rotation_step_delay,
                "camera_rotation_settle_delay": self.camera_rotation_settle_delay,
                "zoom_ticks": self.zoom_ticks,
                "zoom_tick_delay": self.zoom_tick_delay,
                "zoom_settle_delay": self.zoom_settle_delay,
                "pre_cast_minigame_wait": self.pre_cast_minigame_wait,
                "store_click_delay": self.store_click_delay,
                "backspace_delay": self.backspace_delay,
                "rod_deselect_delay": self.rod_deselect_delay,
                "rod_select_delay": self.rod_select_delay,
                "bait_click_delay": self.bait_click_delay,
                "fruit_detection_delay": self.fruit_detection_delay,
                "fruit_detection_settle": self.fruit_detection_settle,
                "general_action_delay": self.general_action_delay,
                "mouse_move_settle": self.mouse_move_settle,
                "focus_settle_delay": self.focus_settle_delay,
                "disable_normal_camera": self.disable_normal_camera_var.get(),
            }
            self.settings.save_advanced_settings(advanced_dict)

            self.info_label.configure(
                text="✓ Advanced settings saved!",
                text_color=self.current_colors["success"],
            )
        except ValueError:
            self.info_label.configure(
                text="❌ Invalid values! Use numbers only.",
                text_color=self.current_colors["error"],
            )
        except Exception as e:
            self.info_label.configure(
                text=f"❌ Error saving: {e}", text_color=self.current_colors["error"]
            )

    def reset_advanced_settings(self):
        """Reset all advanced settings to default values"""
        # Set defaults
        defaults = {
            "camera_rotation_delay": 0.05,
            "camera_rotation_steps": 8,
            "camera_rotation_step_delay": 0.05,
            "camera_rotation_settle_delay": 0.3,
            "zoom_ticks": 3,
            "zoom_tick_delay": 0.05,
            "zoom_settle_delay": 0.3,
            "pre_cast_minigame_wait": 2.5,
            "store_click_delay": 1.0,
            "backspace_delay": 0.3,
            "rod_deselect_delay": 0.5,
            "rod_select_delay": 0.5,
            "bait_click_delay": 0.3,
            "fruit_detection_delay": 0.02,
            "fruit_detection_settle": 0.3,
            "general_action_delay": 0.05,
            "mouse_move_settle": 0.05,
            "focus_settle_delay": 1.0,
        }

        # Update instance variables
        self.camera_rotation_delay = defaults["camera_rotation_delay"]
        self.camera_rotation_steps = defaults["camera_rotation_steps"]
        self.camera_rotation_step_delay = defaults["camera_rotation_step_delay"]
        self.camera_rotation_settle_delay = defaults["camera_rotation_settle_delay"]
        self.zoom_ticks = defaults["zoom_ticks"]
        self.zoom_tick_delay = defaults["zoom_tick_delay"]
        self.zoom_settle_delay = defaults["zoom_settle_delay"]
        self.pre_cast_minigame_wait = defaults["pre_cast_minigame_wait"]
        self.store_click_delay = defaults["store_click_delay"]
        self.backspace_delay = defaults["backspace_delay"]
        self.rod_deselect_delay = defaults["rod_deselect_delay"]
        self.rod_select_delay = defaults["rod_select_delay"]
        self.bait_click_delay = defaults["bait_click_delay"]
        self.fruit_detection_delay = defaults["fruit_detection_delay"]
        self.fruit_detection_settle = defaults["fruit_detection_settle"]
        self.general_action_delay = defaults["general_action_delay"]
        self.mouse_move_settle = defaults["mouse_move_settle"]

        # Update UI fields
        self.camera_rotation_delay_entry.delete(0, tk.END)
        self.camera_rotation_delay_entry.insert(
            0, str(defaults["camera_rotation_delay"])
        )

        self.camera_rotation_steps_entry.delete(0, tk.END)
        self.camera_rotation_steps_entry.insert(
            0, str(defaults["camera_rotation_steps"])
        )

        self.camera_rotation_step_delay_entry.delete(0, tk.END)
        self.camera_rotation_step_delay_entry.insert(
            0, str(defaults["camera_rotation_step_delay"])
        )

        self.camera_rotation_settle_delay_entry.delete(0, tk.END)
        self.camera_rotation_settle_delay_entry.insert(
            0, str(defaults["camera_rotation_settle_delay"])
        )

        self.zoom_ticks_entry.delete(0, tk.END)
        self.zoom_ticks_entry.insert(0, str(defaults["zoom_ticks"]))

        self.zoom_tick_delay_entry.delete(0, tk.END)
        self.zoom_tick_delay_entry.insert(0, str(defaults["zoom_tick_delay"]))

        self.zoom_settle_delay_entry.delete(0, tk.END)
        self.zoom_settle_delay_entry.insert(0, str(defaults["zoom_settle_delay"]))

        self.pre_cast_minigame_wait_entry.delete(0, tk.END)
        self.pre_cast_minigame_wait_entry.insert(
            0, str(defaults["pre_cast_minigame_wait"])
        )

        self.store_click_delay_entry.delete(0, tk.END)
        self.store_click_delay_entry.insert(0, str(defaults["store_click_delay"]))

        self.backspace_delay_entry.delete(0, tk.END)
        self.backspace_delay_entry.insert(0, str(defaults["backspace_delay"]))

        self.rod_deselect_delay_entry.delete(0, tk.END)
        self.rod_deselect_delay_entry.insert(0, str(defaults["rod_deselect_delay"]))

        self.rod_select_delay_entry.delete(0, tk.END)
        self.rod_select_delay_entry.insert(0, str(defaults["rod_select_delay"]))

        self.bait_click_delay_entry.delete(0, tk.END)
        self.bait_click_delay_entry.insert(0, str(defaults["bait_click_delay"]))

        self.fruit_detection_delay_entry.delete(0, tk.END)
        self.fruit_detection_delay_entry.insert(
            0, str(defaults["fruit_detection_delay"])
        )

        self.fruit_detection_settle_entry.delete(0, tk.END)
        self.fruit_detection_settle_entry.insert(
            0, str(defaults["fruit_detection_settle"])
        )

        self.general_action_delay_entry.delete(0, tk.END)
        self.general_action_delay_entry.insert(0, str(defaults["general_action_delay"]))

        self.mouse_move_settle_entry.delete(0, tk.END)
        self.mouse_move_settle_entry.insert(0, str(defaults["mouse_move_settle"]))

        # Update UI fields - Focus settle delay
        self.focus_settle_delay_entry.delete(0, tk.END)
        self.focus_settle_delay_entry.insert(0, str(defaults["focus_settle_delay"]))

        # Update casting fields
        defaults["cast_hold_duration"] = 1.0
        defaults["recast_timeout"] = 30.0
        defaults["fishing_end_delay"] = 2.0
        defaults["pid_kp"] = 1.0
        defaults["pid_kd"] = 0.3
        defaults["pid_clamp"] = 1.0

        self.cast_hold_duration = defaults["cast_hold_duration"]
        self.recast_timeout = defaults["recast_timeout"]
        self.fishing_end_delay = defaults["fishing_end_delay"]
        self.pid_kp = defaults["pid_kp"]
        self.pid_kd = defaults["pid_kd"]
        self.pid_clamp = defaults["pid_clamp"]

        self.cast_hold_entry.delete(0, tk.END)
        self.cast_hold_entry.insert(0, str(defaults["cast_hold_duration"]))

        self.recast_timeout_entry.delete(0, tk.END)
        self.recast_timeout_entry.insert(0, str(defaults["recast_timeout"]))

        self.fishing_end_delay_entry.delete(0, tk.END)
        self.fishing_end_delay_entry.insert(0, str(defaults["fishing_end_delay"]))

        self.kp_entry.delete(0, tk.END)
        self.kp_entry.insert(0, str(defaults["pid_kp"]))

        self.kd_entry.delete(0, tk.END)
        self.kd_entry.insert(0, str(defaults["pid_kd"]))

        self.clamp_entry.delete(0, tk.END)
        self.clamp_entry.insert(0, str(defaults["pid_clamp"]))

        # Save to file
        try:
            data = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)

            data["advanced_settings"] = {
                k: v
                for k, v in defaults.items()
                if k
                not in [
                    "cast_hold_duration",
                    "recast_timeout",
                    "fishing_end_delay",
                    "pid_kp",
                    "pid_kd",
                    "pid_clamp",
                ]
            }

            data["casting_settings"] = {
                "cast_hold_duration": defaults["cast_hold_duration"],
                "recast_timeout": defaults["recast_timeout"],
                "fishing_end_delay": defaults["fishing_end_delay"],
            }

            data["pid_settings"] = {
                "kp": defaults["pid_kp"],
                "kd": defaults["pid_kd"],
                "clamp": defaults["pid_clamp"],
            }

            with open(SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=4)

            self.info_label.configure(
                text="✓ All settings reset to default!",
                text_color=self.current_colors["success"],
            )
        except Exception as e:
            self.info_label.configure(
                text=f"❌ Error resetting: {e}", text_color=self.current_colors["error"]
            )

    def save_webhook_settings_ui(self):
        """Save webhook settings from UI entries"""
        try:
            webhook_url = self.webhook_url_entry.get().strip()
            user_id = self.user_id_entry.get().strip()

            # Validate inputs
            if not webhook_url or not user_id:
                self.info_label.configure(
                    text="❌ Webhook URL and User ID cannot be empty!",
                    text_color="#ff4444",
                )
                logger.warning("Save webhook attempted with empty URL or user ID")
                return

            # Validate webhook URL format
            if not validate_webhook_url(webhook_url):
                self.info_label.configure(
                    text="❌ Invalid Discord webhook URL format!", text_color="#ff4444"
                )
                logger.warning(f"Invalid webhook URL format: {webhook_url[:50]}...")
                return

            # Validate user ID format
            if not validate_user_id(user_id):
                self.info_label.configure(
                    text="❌ Invalid Discord User ID! Must be 17-20 digits",
                    text_color="#ff4444",
                )
                logger.warning(f"Invalid user ID format: {user_id}")
                return

            # Save to JSON
            data = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)

            data["webhook_settings"] = {
                "webhook_url": webhook_url,
                "user_id": user_id,
                "only_legendary": self.webhook_only_legendary,
                "pity_zone": self.webhook_pity_zone,
            }

            with open(SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=4)

            # Update webhook service
            self.webhook_service.update_settings(
                webhook_url=webhook_url,
                user_id=user_id,
                only_legendary=self.webhook_only_legendary,
                pity_zone=self.webhook_pity_zone,
            )

            self.info_label.configure(
                text="✓ Webhook settings saved!", text_color="#00dd00"
            )
            logger.info(
                f"Webhook settings saved: URL={webhook_url[:30]}..., UserID={user_id}, LegendaryOnly={self.webhook_only_legendary}"
            )
        except json.JSONDecodeError as e:
            self.info_label.configure(
                text="❌ Error: Settings file corrupted!", text_color="#ff4444"
            )
            logger.error(f"Failed to parse settings file when saving webhook: {e}")
        except IOError as e:
            self.info_label.configure(
                text="❌ Error: Cannot write settings file!", text_color="#ff4444"
            )
            logger.error(f"IO error saving webhook settings: {e}")
        except Exception as e:
            self.info_label.configure(
                text=f"❌ Error saving webhook: {str(e)[:40]}", text_color="#ff4444"
            )
            logger.error(
                f"Unexpected error saving webhook settings: {e}", exc_info=True
            )

    def toggle_webhook_legendary_filter(self):
        """Toggle legendary/mythical filter for webhook notifications"""
        self.webhook_only_legendary = self.webhook_only_legendary_var.get()

        # Show/hide pity zone section
        if self.webhook_only_legendary:
            self.pity_zone_section.pack(fill="x", pady=5, padx=15)
            self.info_label.configure(
                text="✓ Legendary filter enabled - configure pity zone",
                text_color="#00dd00",
            )
        else:
            self.pity_zone_section.pack_forget()
            self.info_label.configure(
                text="✓ Legendary filter disabled - will notify all fruits",
                text_color="#00dd00",
            )

        self.save_webhook_settings_ui()

    def start_pity_zone_selection(self):
        """Start zone selection for pity counter OCR area"""
        self.selecting_pity_zone = True
        self.pity_zone_btn.configure(text="Drawing...", fg_color="#ff6600")
        self.pity_zone_label.configure(
            text="Draw rectangle (click & drag)", text_color="#ffaa00"
        )

        # Create transparent drawing overlay
        self._create_pity_zone_overlay()

    def _create_pity_zone_overlay(self):
        """Create a fullscreen overlay for drawing pity zone selection rectangle"""
        try:
            overlay = tk.Toplevel(self.root)
            overlay.attributes("-fullscreen", True)
            overlay.attributes("-alpha", 0.3)
            overlay.attributes("-topmost", True)
            overlay.configure(bg="black")

            # Canvas for drawing
            canvas = tk.Canvas(overlay, bg="black", highlightthickness=0)
            canvas.pack(fill="both", expand=True)

            # Track drawing state
            self._pity_draw_start = None
            self._pity_draw_rect = None

            def on_press(event):
                self._pity_draw_start = (event.x, event.y)
                self._pity_draw_rect = canvas.create_rectangle(
                    event.x, event.y, event.x, event.y, outline="lime", width=3
                )

            def on_drag(event):
                if self._pity_draw_start and self._pity_draw_rect:
                    canvas.coords(
                        self._pity_draw_rect,
                        self._pity_draw_start[0],
                        self._pity_draw_start[1],
                        event.x,
                        event.y,
                    )

            def on_release(event):
                if self._pity_draw_start:
                    x1, y1 = self._pity_draw_start
                    x2, y2 = event.x, event.y

                    # Normalize coordinates
                    x = min(x1, x2)
                    y = min(y1, y2)
                    width = abs(x2 - x1)
                    height = abs(y2 - y1)

                    # Destroy overlay first
                    overlay.destroy()

                    # Then process zone selection
                    if width >= 10 and height >= 10:
                        zone_config = {"x": x, "y": y, "width": width, "height": height}
                        self.root.after(
                            50, lambda: self._finish_pity_zone_selection(zone_config)
                        )
                    else:
                        self.root.after(50, self._cancel_pity_zone_selection)

            def on_escape(event):
                overlay.destroy()
                self.root.after(50, self._cancel_pity_zone_selection)

            canvas.bind("<ButtonPress-1>", on_press)
            canvas.bind("<B1-Motion>", on_drag)
            canvas.bind("<ButtonRelease-1>", on_release)
            overlay.bind("<Escape>", on_escape)
        except Exception as e:
            print(f"[Webhook] Could not create pity zone overlay: {e}")
            self._cancel_pity_zone_selection()

    def _finish_pity_zone_selection(self, zone_config):
        """Complete pity zone selection and save"""
        self.webhook_pity_zone = zone_config
        self.pity_zone_btn.configure(text="Select Zone", fg_color=self.button_color)
        self.pity_zone_label.configure(
            text=f"({zone_config['x']}, {zone_config['y']}) {zone_config['width']}x{zone_config['height']}",
            text_color="#00dd00",
        )
        self.info_label.configure(
            text="✓ Pity counter zone saved!", text_color="#00dd00"
        )
        logger.info(f"Webhook pity zone saved: {zone_config}")

        self.selecting_pity_zone = False

        # Save only pity zone to settings without validation
        try:
            data = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)

            # Update or create webhook_settings
            if "webhook_settings" not in data:
                data["webhook_settings"] = {
                    "webhook_url": "",
                    "user_id": "",
                    "only_legendary": False,
                    "pity_zone": None,
                }

            data["webhook_settings"]["pity_zone"] = self.webhook_pity_zone
            data["webhook_settings"]["only_legendary"] = self.webhook_only_legendary

            with open(SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving pity zone: {e}")

    def _cancel_pity_zone_selection(self):
        """Cancel pity zone selection"""
        self.pity_zone_btn.configure(text="Select Zone", fg_color=self.button_color)
        self.pity_zone_label.configure(text="Cancelled", text_color="#ff4444")
        self.selecting_pity_zone = False

    def check_legendary_pity(self):
        """Check if fruit is legendary/mythical by scanning pity counter

        Returns:
            True if LEGENDARY PITY 0/40 detected (legendary/mythical fruit)
            False otherwise
        """
        if not self.webhook_pity_zone:
            logger.warning("[Pity Check] Zone not configured, assuming legendary fruit")
            return True  # Default to True if zone not set

        if not self.ocr.is_available():
            logger.warning(
                "[Pity Check] Tesseract OCR not available, assuming legendary fruit"
            )
            return True

        try:
            # Capture pity zone
            zone = self.webhook_pity_zone
            logger.debug(
                f"[Pity Check] Capturing zone: x={zone['x']}, y={zone['y']}, w={zone['width']}, h={zone['height']}"
            )

            image = self.screen.capture_area(
                zone["x"], zone["y"], zone["width"], zone["height"], use_cache=False
            )
            if image is None:
                logger.warning("[Pity Check] Failed to capture pity zone")
                return True

            logger.debug(
                f"[Pity Check] Image captured: shape={image.shape if hasattr(image, 'shape') else 'N/A'}"
            )

            # Run OCR on pity zone with PSM 6 (uniform block of text)
            # PSM 6 is more robust than PSM 7 for noisy text with multiple words
            # NO preprocessing - it destroys game UI text quality
            text, confidence = self.ocr.perform_ocr(
                image, timeout_ms=1500, psm_mode=6, preprocess=False
            )

            if not text or not text.strip():
                logger.debug("[Pity Check] No text detected in pity zone")
                return False

            # Extract and clean text
            raw_text = text.upper()
            logger.info(f"[Pity Check] OCR detected: '{raw_text}'")

            # Apply fuzzy corrections for common OCR errors
            cleaned_text = self._clean_pity_text(raw_text)
            logger.debug(f"[Pity Check] Cleaned text: '{cleaned_text}'")

            # Check for "LEGENDARY PITY 0/40" or variations
            import re

            # Use fuzzy matching to detect "LEGENDARY PITY X/40"
            is_legendary, pity_value = self._fuzzy_match_pity(cleaned_text)

            if is_legendary and pity_value == 0:
                logger.info(
                    f"[Pity Check] ✅ LEGENDARY PITY 0/40 DETECTED! Raw: '{raw_text}' | Cleaned: '{cleaned_text}'"
                )
                print(f"\n{'='*60}")
                print(f"🌟 LEGENDARY PITY 0/40 DETECTED!")
                print(f"📝 Raw OCR: '{raw_text}'")
                print(f"🧹 Cleaned: '{cleaned_text}'")
                print(f"✅ This is a Legendary/Mythical fruit!")
                print(f"{'='*60}\n")
                return True
            elif is_legendary and pity_value is not None:
                # Detected legendary pity but not 0/40
                logger.info(
                    f"[Pity Check] Pity {pity_value}/40 detected (not 0/40): '{cleaned_text}'"
                )
                print(
                    f"\n📊 Legendary pity {pity_value}/40 detected (not 0/40): {cleaned_text}"
                )
                return False
            else:
                logger.info(
                    f"[Pity Check] Text does not match legendary pattern: '{cleaned_text}'"
                )
                print(
                    f"\n📝 Pity text does not match legendary pattern: {cleaned_text}"
                )
                return False

        except Exception as e:
            logger.error(f"[Pity Check] Error: {e}", exc_info=True)
            return True  # Default to True on error

    def _clean_pity_text(self, text):
        """
        Clean OCR text with common pity counter misreads.

        Fixes:
        - LEGENDARY variants: MEGENDARY, HEGENDARY, LOCENDARY, TEGENDARY, SEEGENDARY, etc.
        - PITY variants: PLLY, PILY, PEN, DTNY, PEEY, PERV, PERY, etc.
        - Character fixes: }→0, $→S, )→space, O→0, £→E, [→I

        Args:
            text (str): Raw OCR text

        Returns:
            str: Cleaned text
        """
        # Remove leading/trailing quotes, spaces, and newlines
        text = text.strip(" \"'\n\r")
        text = text.replace("\n", " ")  # Replace newlines with spaces

        import re

        # LEGENDARY corrections (most aggressive patterns first)
        text = text.replace("SEEGENDARY", "LEGENDARY")
        text = text.replace("TEGENDARY", "LEGENDARY")
        text = text.replace("LOCENDARY", "LEGENDARY")
        text = text.replace("MEGENDARY", "LEGENDARY")
        text = text.replace("HEGENDARY", "LEGENDARY")
        text = text.replace("LEGEDARY", "LEGENDARY")
        text = text.replace("LECENDARY", "LEGENDARY")
        # Fix split words
        text = text.replace("REGEN DARY", "LEGENDARY")
        text = text.replace("IEEGEN DARY", "LEGENDARY")
        text = text.replace("EE GENDARY", "LEGENDARY")
        text = re.sub(r"[A-Z]{1,3}\s*GENDARY", "LEGENDARY", text)  # Catch variants

        # PITY corrections (most specific first)
        text = text.replace("DTNY", "PITY")
        text = text.replace("PEEY", "PITY")
        text = text.replace("PERV", "PITY")
        text = text.replace("PERY", "PITY")
        text = text.replace("PLLY", "PITY")
        text = text.replace("PILY", "PITY")
        text = text.replace("PIIY", "PITY")
        text = text.replace("PIII", "PITY")
        text = text.replace("GPEEY", "PITY")
        text = text.replace(" PEN ", " PITY ")  # PEN surrounded by spaces
        text = text.replace("PEN:", "PITY:")  # PEN before colon
        text = text.replace("PEN ", "PITY ")  # PEN followed by space
        text = text.replace("PEN O", "PITY 0")  # FIX: PEN O/40 → PITY 0/40

        # Character corrections (before number fixes)
        text = text.replace("}", "0")  # } → 0
        text = text.replace("$", "S")  # $ → S
        text = text.replace("£", "E")  # £ → E
        text = text.replace("[", "I")  # [ → I (sometimes I is read as [)
        text = text.replace(")", " ")  # ) → space
        text = text.replace(",", " ")  # , → space
        text = text.replace("|", " ")  # | → space
        text = text.replace("@", " ")  # @ → space
        text = text.replace("~", " ")  # ~ → space
        text = text.replace("_", " ")  # _ → space
        text = text.replace('"', " ")  # " → space
        text = text.replace("§", " ")  # § → space (Unicode)
        text = text.replace(";", ":")  # ; → :
        text = text.replace(".", ":")  # . → : (in pity context)
        text = text.replace("-", ":")  # - → : (in pity context)

        # Fix O→0 in numbers (only in X/40 pattern context)
        text = re.sub(r"\bO\s*/\s*4\s*0\b", "0/40", text)  # O /40 (with space)
        text = re.sub(r"\bO/4\s*0\b", "0/40", text)  # FIX: O/40 (no space before /)

        # Clean multiple spaces and slashes
        text = re.sub(r"/+", "/", text)  # Multiple slashes → single slash
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def _fuzzy_match_pity(self, text):
        """
        Fuzzy match for "LEGENDARY PITY X/40" pattern.

        Returns tuple: (is_legendary: bool, pity_value: int or None)

        Args:
            text (str): Cleaned OCR text

        Returns:
            tuple: (is_legendary, pity_value)
                - is_legendary: True if "LEGENDARY" and "PITY" detected
                - pity_value: Extracted number before "/40", or None if not found
        """
        import re

        # Check for LEGENDARY and PITY keywords
        has_legendary = "LEGENDARY" in text or "LEGEND" in text
        has_pity = "PITY" in text or "PITI" in text or "PIIY" in text

        if not (has_legendary and has_pity):
            return False, None

        # Extract X/40 pattern (handle variations like "0 / 40", "0/40", "0/4 0", "/47", "/4O")
        # Match: digit(s) followed by optional spaces, /, optional spaces, 4, then any digit or O
        # Tesseract may misread /40 as /47, /4O, /4 0, etc. Since game only shows /40, any /4X is likely /40
        pity_pattern = r"(\d+)\s*/\s*4\s*[0-9Oo]"
        match = re.search(pity_pattern, text)

        if match:
            try:
                pity_value = int(match.group(1))
                return True, pity_value
            except ValueError:
                pass

        # Fallback: just check for "/40" presence
        if "/40" in text or "/ 40" in text or "/4 0" in text:
            return True, None  # Legendary detected but can't extract exact value

        return False, None

    def test_pity_zone(self):
        """Test pity zone detection (debugging)"""
        if not self.webhook_pity_zone:
            self.pity_test_result_label.configure(
                text="❌ Pity zone not configured!", text_color="#ff4444"
            )
            logger.warning("[Pity Zone Test] Zone not configured")
            return

        self.pity_test_result_label.configure(
            text="🔍 Testing...", text_color="#ffaa00"
        )
        self.root.update()
        logger.info(f"[Pity Zone Test] Starting scan of zone: {self.webhook_pity_zone}")

        try:
            # Capture pity zone
            image = (
                self.screen.capture_area(
                    self.webhook_pity_zone["x"],
                    self.webhook_pity_zone["y"],
                    self.webhook_pity_zone["width"],
                    self.webhook_pity_zone["height"],
                    use_cache=False,
                )
                if self.webhook_pity_zone
                else None
            )
            if image is None:
                self.pity_test_result_label.configure(
                    text="❌ Failed to capture zone!", text_color="#ff4444"
                )
                return

            # Run OCR
            text, confidence = self.ocr.perform_ocr(image, timeout_ms=1500)

            if not text or not text.strip():
                self.pity_test_result_label.configure(
                    text="❌ No text detected", text_color="#ff4444"
                )
                return

            # Extract text
            full_text = text.upper()
            logger.info(f"[Pity Zone Test] OCR detected: '{full_text}'")

            # Log to terminal
            print(f"\n{'='*60}")
            print(f"🔍 PITY ZONE TEST RESULTS:")
            print(f"📝 Detected Text: '{full_text}'")

            # Check if legendary
            is_legendary = (
                "LEGENDARY" in full_text and "PITY" in full_text and "0/40" in full_text
            )

            if is_legendary:
                logger.info("[Pity Zone Test] ✅ LEGENDARY PITY 0/40 DETECTED!")
                print(f"✅ LEGENDARY PITY 0/40 DETECTED!")
                print(f"{'='*60}\n")
                self.pity_test_result_label.configure(
                    text=f"✅ LEGENDARY! Text: '{full_text}'", text_color="#00ff00"
                )
            else:
                logger.info(f"[Pity Zone Test] ❌ Not legendary pattern: '{full_text}'")
                print(f"❌ Not legendary (0/40 not found)")
                print(f"{'='*60}\n")
                self.pity_test_result_label.configure(
                    text=f"📝 Detected: '{full_text}'", text_color="#00ccff"
                )

        except Exception as e:
            logger.error(f"[Pity Zone Test] Error: {e}", exc_info=True)
            self.pity_test_result_label.configure(
                text=f"❌ Error: {e}", text_color="#ff4444"
            )

    def test_pity_zone_ocr(self):
        """Test pity zone OCR and display results"""
        try:
            # Reset result label
            self.pity_test_result_label.configure(
                text="🔍 Scanning pity zone...", text_color="#ffaa00"
            )
            self.root.update()

            # Check if zone is configured
            if not self.webhook_pity_zone:
                self.pity_test_result_label.configure(
                    text="❌ Pity zone not configured! Select zone first.",
                    text_color="#ff4444",
                )
                return

            # Log the zone being scanned for verification
            logger.info(f"[Pity Test] Scanning zone: {self.webhook_pity_zone}")
            print(
                f"📍 Pity Zone: x={self.webhook_pity_zone['x']}, y={self.webhook_pity_zone['y']}, "
                f"w={self.webhook_pity_zone['width']}, h={self.webhook_pity_zone['height']}"
            )

            # Check if Tesseract OCR is available
            if not self.ocr.is_available():
                self.pity_test_result_label.configure(
                    text="❌ Tesseract not found! Install from: https://github.com/UB-Mannheim/tesseract/wiki",
                    text_color="#ff4444",
                )
                return

            # Capture pity zone (VERIFY IT'S USING THE RIGHT ZONE)
            image = self.screen.capture_area(
                self.webhook_pity_zone["x"],
                self.webhook_pity_zone["y"],
                self.webhook_pity_zone["width"],
                self.webhook_pity_zone["height"],
                use_cache=False,
            )
            if image is None:
                self.pity_test_result_label.configure(
                    text="❌ Failed to capture pity zone", text_color="#ff4444"
                )
                logger.error("[Pity Test] Failed to capture screen area!")
                return

            # Run OCR with same settings as actual check (NO preprocess, psm_mode=6)
            logger.info("[Pity Test] Running OCR with PSM 6 (no preprocessing)...")
            text, confidence = self.ocr.perform_ocr(
                image, timeout_ms=1500, psm_mode=6, preprocess=False
            )

            if not text or not text.strip():
                self.pity_test_result_label.configure(
                    text="❌ No text detected in zone", text_color="#ff4444"
                )
                logger.warning("[Pity Test] No text detected")
                return

            # Extract and clean text (same as actual check)
            raw_text = text.upper()
            cleaned_text = self._clean_pity_text(raw_text)

            logger.info(f"[Pity Test] Raw OCR: '{raw_text}'")
            logger.info(f"[Pity Test] Cleaned: '{cleaned_text}'")

            # Use fuzzy matching
            is_legendary, pity_value = self._fuzzy_match_pity(cleaned_text)

            # Display results
            if is_legendary and pity_value == 0:
                self.pity_test_result_label.configure(
                    text=f"✅ LEGENDARY PITY 0/40 DETECTED!\n📝 Raw: '{raw_text}'\n🧹 Cleaned: '{cleaned_text}'",
                    text_color="#00ff00",
                )
                logger.info("[Pity Test] ✅ LEGENDARY PITY 0/40 detected!")
            elif is_legendary and pity_value is not None:
                self.pity_test_result_label.configure(
                    text=f"⚠️ Legendary pity {pity_value}/40 detected (not 0/40)\n📝 Raw: '{raw_text}'\n🧹 Cleaned: '{cleaned_text}'",
                    text_color="#ffaa00",
                )
                logger.info(f"[Pity Test] Legendary pity {pity_value}/40 (not 0/40)")
            else:
                self.pity_test_result_label.configure(
                    text=f"❌ Not legendary pattern\n📝 Raw: '{raw_text}'\n🧹 Cleaned: '{cleaned_text}'",
                    text_color="#ff4444",
                )
                logger.info(f"[Pity Test] Text does not match legendary pattern")

        except Exception as e:
            error_msg = str(e)
            self.pity_test_result_label.configure(
                text=f"❌ Error: {error_msg[:50]}", text_color="#ff4444"
            )
            logger.error(f"[Pity Test] Error: {e}", exc_info=True)

    def test_pity_fish_webhook(self):
        """Test pity fish webhook filter by scanning and showing OCR text in GUI"""
        try:
            # Reset result label
            self.pity_test_result_label.configure(
                text="🔍 Testing pity filter + OCR...", text_color="#ffaa00"
            )
            self.root.update()

            # Check if zone is configured
            if not self.webhook_pity_zone:
                self.pity_test_result_label.configure(
                    text="❌ Pity zone not configured! Select zone first.",
                    text_color="#ff4444",
                )
                logger.warning("[Pity Fish Test] Zone not configured")
                return

            # Check Tesseract OCR
            if not self.ocr.is_available():
                self.pity_test_result_label.configure(
                    text="❌ Tesseract not found! Install from: https://github.com/UB-Mannheim/tesseract/wiki",
                    text_color="#ff4444",
                )
                logger.error("[Pity Fish Test] Tesseract OCR not available")
                return

            # Log zone info
            zone = self.webhook_pity_zone
            logger.info(
                f"[Pity Fish Test] Scanning zone: x={zone['x']}, y={zone['y']}, w={zone['width']}, h={zone['height']}"
            )

            # Capture pity zone
            image = self.screen.capture_area(
                zone["x"], zone["y"], zone["width"], zone["height"], use_cache=False
            )
            if image is None:
                self.pity_test_result_label.configure(
                    text="❌ Failed to capture pity zone!", text_color="#ff4444"
                )
                logger.error("[Pity Fish Test] Screen capture returned None")
                return

            logger.debug(
                f"[Pity Fish Test] Captured image shape: {image.shape if hasattr(image, 'shape') else 'unknown'}"
            )

            # Run OCR with retry (3 attempts)
            full_text = ""
            avg_conf = 0.0
            for attempt in range(3):
                try:
                    logger.info(f"[Pity Fish Test] OCR attempt {attempt + 1}/3...")
                    self.pity_test_result_label.configure(
                        text=f"🔍 OCR attempt {attempt + 1}/3...", text_color="#ffaa00"
                    )
                    self.root.update()

                    text, confidence = self.ocr.perform_ocr(image, timeout_ms=1500)
                    if text and text.strip():
                        full_text = text.upper()
                        avg_conf = confidence
                        logger.info(
                            f"[Pity Fish Test] OCR success on attempt {attempt + 1}"
                        )
                        break
                    time.sleep(0.15)
                except Exception as e:
                    logger.warning(
                        f"[Pity Fish Test] OCR attempt {attempt + 1} error: {e}"
                    )
                    time.sleep(0.15)

            if not full_text:
                self.pity_test_result_label.configure(
                    text="❌ No text detected after 3 OCR attempts.\nCheck zone position and game visibility.",
                    text_color="#ff4444",
                )
                logger.warning("[Pity Fish Test] No text detected after 3 attempts")
                return

            logger.info(
                f"[Pity Fish Test] OCR raw text: '{full_text}' (avg confidence: {avg_conf:.2f})"
            )

            # Clean text for matching (common OCR misreads)
            import re

            clean_text = full_text.replace("O", "0").replace("o", "0")

            # Check patterns
            pity_reset_pattern = r"0\s*[/|\\:\s]+\s*40"
            has_keyword = any(
                kw in clean_text for kw in ["LEGENDARY", "PITY", "LEGEND", "MYTHICAL"]
            )
            match = re.search(pity_reset_pattern, clean_text)

            if match and has_keyword:
                self.pity_test_result_label.configure(
                    text=f"✅ LEGENDARY PITY 0/40 DETECTED!\n"
                    f"📝 OCR Text: '{full_text}'\n"
                    f"🎯 Matched: '{match.group(0)}' | Confidence: {avg_conf:.2f}\n"
                    f"🔔 Webhook WOULD be sent.",
                    text_color="#00ff00",
                )
                logger.info(
                    f"[Pity Fish Test] ✅ LEGENDARY 0/40 matched! Text: '{full_text}'"
                )
            elif has_keyword and "/40" in clean_text:
                self.pity_test_result_label.configure(
                    text=f"⚠️ Legendary pity detected but NOT 0/40.\n"
                    f"📝 OCR Text: '{full_text}'\n"
                    f"🎯 Confidence: {avg_conf:.2f}\n"
                    f"🔕 Webhook would NOT be sent.",
                    text_color="#ffaa00",
                )
                logger.info(
                    f"[Pity Fish Test] ⚠️ Pity detected but not 0/40: '{full_text}'"
                )
            else:
                self.pity_test_result_label.configure(
                    text=f"❌ Not legendary pattern.\n"
                    f"📝 OCR Text: '{full_text}'\n"
                    f"🎯 Keywords: {'Yes' if has_keyword else 'No'} | Match: {'Yes' if match else 'No'}\n"
                    f"🔕 Webhook would NOT be sent.",
                    text_color="#ff4444",
                )
                logger.info(f"[Pity Fish Test] ❌ No match. Text: '{full_text}'")

        except Exception as e:
            self.pity_test_result_label.configure(
                text=f"❌ Error: {str(e)[:80]}", text_color="#ff4444"
            )
            logger.error(f"[Pity Fish Test] Error: {e}", exc_info=True)

    def test_webhook(self):
        """Test Discord webhook by sending a test message (non-blocking)"""
        self.info_label.configure(
            text="⏳ Sending test message...", text_color="#ffaa00"
        )

        def _test_webhook_bg():
            try:
                success, message = self.webhook_service.send_test_message()
                # Update UI on main thread
                if success:
                    self.root.after(
                        0,
                        lambda: self.info_label.configure(
                            text=f"✓ {message}", text_color="#00dd00"
                        ),
                    )
                else:
                    self.root.after(
                        0,
                        lambda: self.info_label.configure(
                            text=f"❌ {message}", text_color="#ff4444"
                        ),
                    )
            except Exception as e:
                self.root.after(
                    0,
                    lambda: self.info_label.configure(
                        text=f"❌ Webhook error: {e}", text_color="#ff4444"
                    ),
                )

        threading.Thread(target=_test_webhook_bg, daemon=True).start()

    def save_casting_settings(self):
        """Save casting settings to settings file"""
        try:
            self.settings.save_casting_settings(
                self.cast_hold_duration, self.recast_timeout, self.fishing_end_delay
            )
        except Exception as e:
            print(f"Error saving casting settings: {e}")

    def save_casting_from_ui(self):
        """Save casting settings from UI entries"""
        try:
            self.cast_hold_duration = float(self.cast_hold_entry.get())
            self.recast_timeout = float(self.recast_timeout_entry.get())
            self.fishing_end_delay = float(self.fishing_end_delay_entry.get())
            self.save_casting_settings()
            self.info_label.configure(
                text="✓ Casting settings saved!",
                text_color=self.current_colors["success"],
            )
        except ValueError:
            self.info_label.configure(
                text="❌ Invalid casting values! Use numbers only.",
                text_color=self.current_colors["error"],
            )

    def start_water_point_selection(self):
        """Start water point selection mode with overlay"""
        self.selecting_water_point = True
        self.water_point_button.configure(text="Waiting... (Right-Click)")
        self.water_point_label.configure(
            text="RIGHT-CLICK on water target",
            text_color=self.current_colors["warning"],
        )

        # Show overlay popup
        self._show_coord_selection_overlay()

        # Cleanup old listener
        try:
            if hasattr(self, "mouse_listener") and self.mouse_listener:
                self.mouse_listener.stop()
        except:
            pass

        # Start mouse listener in background
        self.mouse_listener = MouseListener(on_click=self.on_mouse_click_water_point)
        self.mouse_listener.start()

    def on_mouse_click_water_point(self, x, y, button, pressed):
        """Handle mouse clicks during water point selection"""
        if not self.selecting_water_point:
            return

        if pressed:
            if button == Button.right:
                # Right click - save the water point
                self.water_point = {"x": x, "y": y}
                self.settings.save_water_point(self.water_point)

                # Sync with FishingCycle
                if hasattr(self, "fishing_cycle") and self.fishing_cycle:
                    self.fishing_cycle.update_coords(water_point=self.water_point)

                self.selecting_water_point = False

                # Update UI
                self.water_point_button.configure(text="Select")
                self.water_point_label.configure(
                    text=f"({x}, {y})", text_color="#00dd00"
                )

                print(f"[Water Point] ✓ Saved: ({x}, {y})")

                # Close overlay if exists
                try:
                    if hasattr(self, "coord_selection_overlay"):
                        self.coord_selection_overlay.destroy()
                except:
                    pass

                # Stop mouse listener
                try:
                    if hasattr(self, "mouse_listener") and self.mouse_listener:
                        self.mouse_listener.stop()
                except:
                    pass
        self.save_always_on_top()

    def start_auto_craft_water_point_selection(self):
        """Start auto craft water point selection mode with overlay"""
        self.selecting_auto_craft_water_point = True
        self.auto_craft_water_point_button.configure(
            text="Waiting... (Right-Click)", fg_color="#ff6600"
        )
        self.auto_craft_water_point_label.configure(
            text="RIGHT-CLICK on auto craft water target", text_color="#ffaa00"
        )

        # Show overlay popup
        self._show_coord_selection_overlay()

        # Cleanup old listener
        try:
            if hasattr(self, "mouse_listener") and self.mouse_listener:
                self.mouse_listener.stop()
        except:
            pass

        # Start mouse listener in background
        self.mouse_listener = MouseListener(
            on_click=self.on_mouse_click_auto_craft_water_point
        )
        self.mouse_listener.start()

    def on_mouse_click_auto_craft_water_point(self, x, y, button, pressed):
        """Handle mouse clicks during auto craft water point selection"""
        if not self.selecting_auto_craft_water_point:
            return

        if pressed:
            if button == Button.right:
                # Right click - save the auto craft water point
                self.auto_craft_water_point = {"x": x, "y": y}
                self.save_auto_craft_settings()  # Use unified save method
                self.selecting_auto_craft_water_point = False

                # Update UI
                self.auto_craft_water_point_button.configure(
                    text="Select", fg_color=self.button_color
                )
                self.auto_craft_water_point_label.configure(
                    text=f"({x}, {y})", text_color="#00dd00"
                )

                print(f"[Auto Craft Water] ✓ Saved: ({x}, {y})")

                # Close overlay if exists
                try:
                    if hasattr(self, "coord_selection_overlay"):
                        self.coord_selection_overlay.destroy()
                except:
                    pass

                # Stop mouse listener
                try:
                    if hasattr(self, "mouse_listener") and self.mouse_listener:
                        self.mouse_listener.stop()
                except:
                    pass

    def save_auto_craft_water_point(self):
        """Save auto craft water point coordinates to settings file"""
        try:
            data = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)

            # Get existing auto_craft_settings or create new
            auto_craft_settings = data.get("auto_craft_settings", {})
            auto_craft_settings["auto_craft_water_point"] = self.auto_craft_water_point
            data["auto_craft_settings"] = auto_craft_settings

            with open(SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving auto craft water point: {e}")

    def save_craft_settings_from_ui(self):
        """Save craft settings from UI entries"""
        try:
            self.craft_every_n_fish = int(self.craft_every_n_fish_entry.get())
            self.craft_menu_delay = float(self.craft_menu_delay_entry.get())
            self.craft_click_speed = float(self.craft_click_speed_entry.get())
            self.craft_legendary_quantity = int(
                self.craft_legendary_quantity_entry.get()
            )
            self.craft_rare_quantity = int(self.craft_rare_quantity_entry.get())
            self.craft_common_quantity = int(self.craft_common_quantity_entry.get())

            self.save_auto_craft_settings()
            self.info_label.configure(
                text="✓ Craft settings saved!", text_color="#00dd00"
            )
        except ValueError:
            self.info_label.configure(
                text="❌ Invalid values! Use numbers only.", text_color="#ff4444"
            )

    def start_auto_craft_coord_selection(self, coord_name):
        """Start coordinate selection mode for auto craft with popup overlay"""
        self.selecting_auto_craft_coord = coord_name

        # Update button text based on coordinate type
        button_map = {
            "craft_button_coords": (self.craft_button_btn, self.craft_button_label),
            "plus_button_coords": (self.plus_button_btn, self.plus_button_label),
            "fish_icon_coords": (self.fish_icon_btn, self.fish_icon_label),
            "legendary_bait_coords": (
                self.legendary_bait_btn,
                self.legendary_bait_label,
            ),
            "rare_bait_coords": (self.rare_bait_btn, self.rare_bait_label),
            "common_bait_coords": (self.common_bait_btn, self.common_bait_label),
            "smart_bait_2nd_coords": (
                self.smart_bait_2nd_btn,
                self.smart_bait_2nd_label,
            ),
        }

        if coord_name in button_map:
            btn, label = button_map[coord_name]
            btn.configure(text="Waiting...", fg_color="#ff6600")
            label.configure(text="Right-click on target in-game", text_color="#ffaa00")

        # Show overlay popup
        self._show_coord_selection_overlay()

        # Start mouse listener
        try:
            if hasattr(self, "mouse_listener") and self.mouse_listener:
                self.mouse_listener.stop()
        except:
            pass

        self.mouse_listener = MouseListener(
            on_click=self.on_mouse_click_auto_craft_coord
        )
        self.mouse_listener.start()

    def _show_coord_selection_overlay(self):
        """Show a transparent overlay popup during coordinate selection"""
        try:
            # Create transparent overlay window
            overlay = tk.Toplevel(self.root)
            overlay.overrideredirect(True)  # Remove title bar and borders
            overlay.attributes("-alpha", 0.01)
            overlay.attributes("-topmost", True)
            overlay.geometry(f"{SCREEN_WIDTH}x{SCREEN_HEIGHT}+0+0")

            # Allow closing with ESC
            def on_esc(event=None):
                self._cancel_coord_selection()
                overlay.destroy()

            overlay.bind("<Escape>", on_esc)

            # Store reference to cleanup
            self.coord_selection_overlay = overlay
        except Exception as e:
            print(f"[Coord Select] Could not create overlay: {e}")

    def _cancel_coord_selection(self):
        """Cancel coordinate selection"""
        self.selecting_auto_craft_coord = None
        try:
            if hasattr(self, "mouse_listener") and self.mouse_listener:
                self.mouse_listener.stop()
        except:
            pass

    def on_mouse_click_auto_craft_coord(self, x, y, button, pressed):
        """Handle mouse clicks during auto craft coordinate selection"""
        if not self.selecting_auto_craft_coord:
            return

        if pressed and button == Button.right:
            coord_name = self.selecting_auto_craft_coord
            coord_value = {"x": x, "y": y}

            # Save coordinate
            setattr(self, coord_name, coord_value)
            self.save_auto_craft_settings()

            # Update UI
            button_map = {
                "craft_button_coords": (self.craft_button_btn, self.craft_button_label),
                "plus_button_coords": (self.plus_button_btn, self.plus_button_label),
                "fish_icon_coords": (self.fish_icon_btn, self.fish_icon_label),
                "legendary_bait_coords": (
                    self.legendary_bait_btn,
                    self.legendary_bait_label,
                ),
                "rare_bait_coords": (self.rare_bait_btn, self.rare_bait_label),
                "common_bait_coords": (self.common_bait_btn, self.common_bait_label),
                "smart_bait_2nd_coords": (
                    self.smart_bait_2nd_btn,
                    self.smart_bait_2nd_label,
                ),
            }

            if coord_name in button_map:
                btn, label = button_map[coord_name]
                btn.configure(text="Set Position", fg_color=self.button_color)
                label.configure(text=f"X: {x}, Y: {y}", text_color="#00dd00")

            # Print confirmation
            print(f"[Coord Select] ✓ {coord_name}: ({x}, {y})")

            # Clear selection
            self.selecting_auto_craft_coord = None

            # Stop mouse listener
            try:
                if hasattr(self, "mouse_listener") and self.mouse_listener:
                    self.mouse_listener.stop()
            except:
                pass

            # Close overlay if exists
            try:
                if hasattr(self, "coord_selection_overlay"):
                    self.coord_selection_overlay.destroy()
            except:
                pass

    def run_auto_craft(self):
        """Execute the crafting sequence for Auto Craft mode

        Crafting sequence (for each bait type with quantity > 0):
        1. Click Bait Icon (legendary/rare/common) - ONCE
        2. Click Plus Button - ONCE
        3. Click Fish Icon (the fish to use as material) - ONCE
        4. Click Craft Button - QUANTITY times (in batches of 40)

        Uses same click method as water point and minigame (win32api)

        Craft Order: Common → Rare → Legendary (prevents inventory overflow at 280)
        """
        try:
            print(
                f"\r[Auto Craft] ⚒️ Starting crafting sequence...",
                end="",
                flush=True,
            )

            # Initialize keyboard controller

            # Step 0: Deselect rod (press rod hotkey)
            print(
                f"\r[Auto Craft] Deselecting rod ({self.rod_hotkey})...",
                end="",
                flush=True,
            )
            self.keyboard.press(self.rod_hotkey)
            self.keyboard.release(self.rod_hotkey)
            time.sleep(0.3)

            # Wait for menu to open
            menu_delay = (
                self.craft_menu_delay / 1000.0
                if self.craft_menu_delay < 100
                else self.craft_menu_delay
            )
            print(
                f"\r[Auto Craft] Waiting {menu_delay:.2f}s for menu to open...",
                end="",
                flush=True,
            )
            time.sleep(menu_delay)

            # Convert click speed (in ms to seconds)
            click_delay = (
                self.craft_click_speed / 1000.0
                if self.craft_click_speed < 100
                else self.craft_click_speed
            )

            # OCR removido do V2.7
            ocr_leg = 0
            ocr_rare = 0
            ocr_common = 0

            # Define bait types to craft in order: Common → Rare → Legendary (prevents overflow)
            baits_to_craft = [
                (
                    "Common",
                    self.common_bait_coords,
                    self.craft_common_quantity,
                    ocr_common,
                ),
                ("Rare", self.rare_bait_coords, self.craft_rare_quantity, ocr_rare),
                (
                    "Legendary",
                    self.legendary_bait_coords,
                    self.craft_legendary_quantity,
                    ocr_leg,
                ),
            ]

            for bait_name, bait_coords, quantity, current_count in baits_to_craft:
                if not self.running:
                    break

                if quantity <= 0:
                    continue

                # Overflow protection: skip crafting if already at 280+ baits
                if current_count >= 280:
                    print(
                        f"\r[Auto Craft] ⚠️ {bait_name} at {current_count}/280 baits. Skipping craft to prevent overflow...",
                        end="",
                        flush=True,
                    )
                    continue

                if not bait_coords:
                    print(
                        f"\r[Auto Craft] ⚠️ {bait_name} bait coords not set, skipping...",
                        end="",
                        flush=True,
                    )
                    continue

                print(
                    f"\r[Auto Craft] Crafting {quantity}x {bait_name} bait (current: {current_count}/280)...",
                    end="",
                    flush=True,
                )

                # Validate all coords before starting
                if not self.plus_button_coords:
                    print(
                        f"\r[Auto Craft] ⚠️ Plus button coords not set! Skipping {bait_name}...",
                        end="",
                        flush=True,
                    )
                    continue
                if not self.fish_icon_coords:
                    print(
                        f"\r[Auto Craft] ⚠️ Fish icon coords not set! Skipping {bait_name}...",
                        end="",
                        flush=True,
                    )
                    continue
                if not self.craft_button_coords:
                    print(
                        f"\r[Auto Craft] ⚠️ Craft button coords not set! Skipping {bait_name}...",
                        end="",
                        flush=True,
                    )
                    continue

                # Step 1: Click Bait Icon (ONCE - for the entire quantity)
                print(
                    f"\r[AC] {bait_name}: Clicking bait icon at ({bait_coords['x']}, {bait_coords['y']})...",
                    end="",
                    flush=True,
                )
                self.mouse.click(bait_coords["x"], bait_coords["y"], hold_delay=0.1)
                time.sleep(click_delay)

                # Process quantity in batches of 40 (max 40 fish per session)
                remaining = quantity
                batch_num = 1
                while remaining > 0:
                    batch_size = min(40, remaining)  # Max 40 per batch

                    # Step 2: Click Plus Button (once per batch)
                    print(
                        f"\r[AC] {bait_name} Batch {batch_num}: Clicking plus button at ({self.plus_button_coords['x']}, {self.plus_button_coords['y']})...",
                        end="",
                        flush=True,
                    )
                    self.mouse.click(
                        self.plus_button_coords["x"],
                        self.plus_button_coords["y"],
                        hold_delay=0.1,
                    )
                    time.sleep(click_delay)

                    # Step 3: Click Fish Icon (once per batch)
                    print(
                        f"\r[AC] {bait_name} Batch {batch_num}: Clicking fish icon at ({self.fish_icon_coords['x']}, {self.fish_icon_coords['y']})...",
                        end="",
                        flush=True,
                    )
                    self.mouse.click(
                        self.fish_icon_coords["x"],
                        self.fish_icon_coords["y"],
                        hold_delay=0.1,
                    )
                    time.sleep(click_delay)

                    # Step 4: Click Craft Button (batch_size times)
                    for q in range(batch_size):
                        if not self.running:
                            break
                        print(
                            f"\r[AC] {bait_name} Batch {batch_num}: Clicking craft button {q+1}/{batch_size}...",
                            end="",
                            flush=True,
                        )
                        self.mouse.click(
                            self.craft_button_coords["x"],
                            self.craft_button_coords["y"],
                            hold_delay=0.1,
                        )
                        time.sleep(click_delay)

                    remaining -= batch_size
                    batch_num += 1

                    if remaining > 0:
                        print(
                            f"\r[AC] {bait_name}: {remaining} remaining, preparing next batch...",
                            end="",
                            flush=True,
                        )

            print(
                f"\r[Auto Craft] ✅ Crafting sequence completed successfully!",
                end="",
                flush=True,
            )

        except Exception as e:
            print(
                f"\r[Auto Craft] ❌ Error during crafting: {str(e)}", end="", flush=True
            )

    def start_button_selection(self, button_type):
        """Start button position selection mode"""
        self.selecting_button = button_type

        # Update UI based on button type
        if button_type == "yes":
            self.yes_button_btn.configure(text="Waiting... (Right-Click)")
            self.yes_button_label.configure(
                text="RIGHT-CLICK on Yes button",
                text_color=self.current_colors["warning"],
            )
        elif button_type == "middle":
            self.middle_button_btn.configure(text="Waiting... (Right-Click)")
            self.middle_button_label.configure(
                text="RIGHT-CLICK on Middle button",
                text_color=self.current_colors["warning"],
            )
        elif button_type == "no":
            self.no_button_btn.configure(text="Waiting... (Right-Click)")
            self.no_button_label.configure(
                text="RIGHT-CLICK on No button",
                text_color=self.current_colors["warning"],
            )

        # Start mouse listener in background
        self.mouse_listener = MouseListener(on_click=self.on_mouse_click_button)
        self.mouse_listener.start()

    def on_mouse_click_button(self, x, y, button, pressed):
        """Handle mouse clicks during button position selection"""
        if not self.selecting_button:
            return

        if pressed:
            if button == Button.right:
                # Right click - save the button position
                coords = {"x": x, "y": y}

                if self.selecting_button == "yes":
                    self.yes_button = coords
                    self.yes_button_btn.configure(text="Select")
                    self.yes_button_label.configure(
                        text=f"({x}, {y})", text_color=self.current_colors["success"]
                    )
                elif self.selecting_button == "middle":
                    self.middle_button = coords
                    self.middle_button_btn.configure(text="Select")
                    self.middle_button_label.configure(
                        text=f"({x}, {y})", text_color=self.current_colors["success"]
                    )
                elif self.selecting_button == "no":
                    self.no_button = coords
                    self.no_button_btn.configure(text="Select")
                    self.no_button_label.configure(
                        text=f"({x}, {y})", text_color=self.current_colors["success"]
                    )

                self.save_precast_settings()
                self.selecting_button = None

                # Stop mouse listener
                self.mouse_listener.stop()

    def start_fruit_point_selection(self):
        """Start fruit point selection mode - captures coordinate and color with overlay"""
        self.selecting_fruit_point = True
        self.fruit_point_btn.configure(text="Waiting... (Right-Click)")
        self.fruit_point_label.configure(
            text="RIGHT-CLICK on fruit location",
            text_color=self.current_colors["warning"],
        )

        # Show overlay popup
        self._show_coord_selection_overlay()

        # Cleanup old listener
        try:
            if hasattr(self, "fruit_mouse_listener") and self.fruit_mouse_listener:
                self.fruit_mouse_listener.stop()
        except:
            pass

        # Start mouse listener in background
        self.fruit_mouse_listener = MouseListener(
            on_click=self.on_mouse_click_fruit_point
        )
        self.fruit_mouse_listener.start()

    def on_mouse_click_fruit_point(self, x, y, button, pressed):
        """Handle mouse clicks during fruit point selection - save coordinate and color"""
        if not self.selecting_fruit_point:
            return

        if pressed:
            if button == Button.right:
                # Right click - save the fruit point position and capture color
                self.fruit_point = {"x": x, "y": y}

                # Capture color at this coordinate
                try:
                    with mss.mss() as sct:
                        # Capture a 1x1 pixel area
                        monitor = {"top": y, "left": x, "width": 1, "height": 1}
                        screenshot = sct.grab(monitor)
                        # Get pixel color (BGRA format)
                        pixel = screenshot.pixel(0, 0)
                        # pixel is (R, G, B, A) - we need (B, G, R) which is the order in BGRA
                        self.fruit_color = (
                            pixel[2],
                            pixel[1],
                            pixel[0],
                        )  # Convert to BGR for consistency

                        color_hex = f"#{self.fruit_color[2]:02x}{self.fruit_color[1]:02x}{self.fruit_color[0]:02x}"
                        self.fruit_point_btn.configure(text="Select")
                        self.fruit_point_label.configure(
                            text=f"({x}, {y}) {color_hex}",
                            text_color=self.current_colors["success"],
                        )

                        print(f"[Fruit Point] ✓ Saved: ({x}, {y}) Color: {color_hex}")
                except Exception as e:
                    print(f"Error capturing fruit color: {e}")
                    self.fruit_point_btn.configure(text="Select")
                    self.fruit_point_label.configure(
                        text=f"({x}, {y}) [Color Error]",
                        text_color=self.current_colors["warning"],
                    )

                # Close overlay if exists
                try:
                    if hasattr(self, "coord_selection_overlay"):
                        self.coord_selection_overlay.destroy()
                except:
                    pass

                self.save_precast_settings()
                self.selecting_fruit_point = False

                # Stop mouse listener
                try:
                    if (
                        hasattr(self, "fruit_mouse_listener")
                        and self.fruit_mouse_listener
                    ):
                        self.fruit_mouse_listener.stop()
                except:
                    pass

    def start_top_bait_point_selection(self):
        """Start top bait point selection mode with overlay"""
        self.selecting_top_bait_point = True
        self.top_bait_point_btn.configure(text="Waiting... (Right-Click)")
        self.top_bait_point_label.configure(
            text="RIGHT-CLICK on bait location",
            text_color=self.current_colors["warning"],
        )

        # Show overlay popup
        self._show_coord_selection_overlay()

        # Cleanup old listener
        try:
            if (
                hasattr(self, "top_bait_mouse_listener")
                and self.top_bait_mouse_listener
            ):
                self.top_bait_mouse_listener.stop()
        except:
            pass

        # Start mouse listener in background
        self.top_bait_mouse_listener = MouseListener(
            on_click=self.on_mouse_click_top_bait_point
        )
        self.top_bait_mouse_listener.start()

    def on_mouse_click_top_bait_point(self, x, y, button, pressed):
        """Handle mouse clicks during top bait point selection"""
        if not self.selecting_top_bait_point:
            return

        if pressed:
            if button == Button.right:
                # Right click - save the top bait point position
                self.top_bait_point = {"x": x, "y": y}
                self.top_bait_point_btn.configure(text="Select")
                self.top_bait_point_label.configure(
                    text=f"({x}, {y})", text_color=self.current_colors["success"]
                )

                print(f"[Top Bait Point] ✓ Saved: ({x}, {y})")

                # Close overlay if exists
                try:
                    if hasattr(self, "coord_selection_overlay"):
                        self.coord_selection_overlay.destroy()
                except:
                    pass

                self.save_precast_settings()
                self.selecting_top_bait_point = False

                # Stop mouse listener
                try:
                    if (
                        hasattr(self, "top_bait_mouse_listener")
                        and self.top_bait_mouse_listener
                    ):
                        self.top_bait_mouse_listener.stop()
                except:
                    pass

    def show_area_selector(self):
        """Show the area selector window"""
        if self.area_selector is None:
            self.area_selector = tk.Toplevel(self.root)
            self.area_selector.title("Area Selector")
            self.area_selector.attributes("-alpha", 0.3)
            self.area_selector.attributes("-topmost", True)
            self.area_selector.overrideredirect(True)

            # Set position and size from saved coords
            x = self.area_coords["x"]
            y = self.area_coords["y"]
            width = self.area_coords["width"]
            height = self.area_coords["height"]
            self.area_selector.geometry(f"{width}x{height}+{x}+{y}")

            # Create a frame with border
            frame = tk.Frame(
                self.area_selector,
                bg="red",
                highlightbackground="red",
                highlightthickness=3,
            )
            frame.pack(fill=tk.BOTH, expand=True)

            # Make draggable
            self._drag_data = {"x": 0, "y": 0}
            frame.bind("<ButtonPress-1>", self.start_drag)
            frame.bind("<B1-Motion>", self.on_drag)

            # Make resizable - create resize handles
            self.create_resize_handles(frame)

            # Prevent from closing
            self.area_selector.protocol("WM_DELETE_WINDOW", lambda: None)

    def create_resize_handles(self, frame):
        """Create resize handles on all corners and edges of the area selector"""
        handle_size = 12
        edge_thickness = 6

        # Corner handles
        # Top-left corner
        tl_handle = tk.Frame(
            frame,
            bg="yellow",
            cursor="size_nw_se",
            width=handle_size,
            height=handle_size,
        )
        tl_handle.place(x=0, y=0, anchor="nw")
        tl_handle.bind("<ButtonPress-1>", lambda e: self.start_resize(e, "top-left"))
        tl_handle.bind("<B1-Motion>", lambda e: self.on_resize(e, "top-left"))

        # Top-right corner
        tr_handle = tk.Frame(
            frame,
            bg="yellow",
            cursor="size_ne_sw",
            width=handle_size,
            height=handle_size,
        )
        tr_handle.place(relx=1.0, y=0, anchor="ne")
        tr_handle.bind("<ButtonPress-1>", lambda e: self.start_resize(e, "top-right"))
        tr_handle.bind("<B1-Motion>", lambda e: self.on_resize(e, "top-right"))

        # Bottom-left corner
        bl_handle = tk.Frame(
            frame,
            bg="yellow",
            cursor="size_ne_sw",
            width=handle_size,
            height=handle_size,
        )
        bl_handle.place(x=0, rely=1.0, anchor="sw")
        bl_handle.bind("<ButtonPress-1>", lambda e: self.start_resize(e, "bottom-left"))
        bl_handle.bind("<B1-Motion>", lambda e: self.on_resize(e, "bottom-left"))

        # Bottom-right corner
        br_handle = tk.Frame(
            frame,
            bg="yellow",
            cursor="size_nw_se",
            width=handle_size,
            height=handle_size,
        )
        br_handle.place(relx=1.0, rely=1.0, anchor="se")
        br_handle.bind(
            "<ButtonPress-1>", lambda e: self.start_resize(e, "bottom-right")
        )
        br_handle.bind("<B1-Motion>", lambda e: self.on_resize(e, "bottom-right"))

        # Edge handles
        # Top edge
        t_handle = tk.Frame(
            frame, bg="lime", cursor="sb_v_double_arrow", height=edge_thickness
        )
        t_handle.place(relx=0.5, y=0, anchor="n", relwidth=0.7)
        t_handle.bind("<ButtonPress-1>", lambda e: self.start_resize(e, "top"))
        t_handle.bind("<B1-Motion>", lambda e: self.on_resize(e, "top"))

        # Bottom edge
        b_handle = tk.Frame(
            frame, bg="lime", cursor="sb_v_double_arrow", height=edge_thickness
        )
        b_handle.place(relx=0.5, rely=1.0, anchor="s", relwidth=0.7)
        b_handle.bind("<ButtonPress-1>", lambda e: self.start_resize(e, "bottom"))
        b_handle.bind("<B1-Motion>", lambda e: self.on_resize(e, "bottom"))

        # Left edge
        l_handle = tk.Frame(
            frame, bg="lime", cursor="sb_h_double_arrow", width=edge_thickness
        )
        l_handle.place(x=0, rely=0.5, anchor="w", relheight=0.7)
        l_handle.bind("<ButtonPress-1>", lambda e: self.start_resize(e, "left"))
        l_handle.bind("<B1-Motion>", lambda e: self.on_resize(e, "left"))

        # Right edge
        r_handle = tk.Frame(
            frame, bg="lime", cursor="sb_h_double_arrow", width=edge_thickness
        )
        r_handle.place(relx=1.0, rely=0.5, anchor="e", relheight=0.7)
        r_handle.bind("<ButtonPress-1>", lambda e: self.start_resize(e, "right"))
        r_handle.bind("<B1-Motion>", lambda e: self.on_resize(e, "right"))

    def start_drag(self, event):
        """Start dragging the area selector"""
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def on_drag(self, event):
        """Handle dragging the area selector"""
        x = self.area_selector.winfo_x() + event.x - self._drag_data["x"]
        y = self.area_selector.winfo_y() + event.y - self._drag_data["y"]
        self.area_selector.geometry(f"+{x}+{y}")

    def start_resize(self, event, direction="both"):
        """Start resizing the area selector"""
        self._resize_data = {
            "x": event.x_root,
            "y": event.y_root,
            "width": self.area_selector.winfo_width(),
            "height": self.area_selector.winfo_height(),
            "win_x": self.area_selector.winfo_x(),
            "win_y": self.area_selector.winfo_y(),
            "direction": direction,
        }

    def on_resize(self, event, direction="both"):
        """Handle resizing the area selector from any corner or edge"""
        if not hasattr(self, "_resize_data"):
            return

        dx = event.x_root - self._resize_data["x"]
        dy = event.y_root - self._resize_data["y"]

        new_width = self._resize_data["width"]
        new_height = self._resize_data["height"]
        new_x = self._resize_data["win_x"]
        new_y = self._resize_data["win_y"]

        direction = self._resize_data.get("direction", "both")
        min_size = 50

        # Handle each direction
        if (
            direction == "right"
            or direction == "bottom-right"
            or direction == "top-right"
        ):
            new_width = max(min_size, self._resize_data["width"] + dx)
        if direction == "left" or direction == "bottom-left" or direction == "top-left":
            new_width = max(min_size, self._resize_data["width"] - dx)
            new_x = self._resize_data["win_x"] + dx
        if (
            direction == "bottom"
            or direction == "bottom-right"
            or direction == "bottom-left"
        ):
            new_height = max(min_size, self._resize_data["height"] + dy)
        if direction == "top" or direction == "top-right" or direction == "top-left":
            new_height = max(min_size, self._resize_data["height"] - dy)
            new_y = self._resize_data["win_y"] + dy
        if direction == "both":
            new_width = max(min_size, self._resize_data["width"] + dx)
            new_height = max(min_size, self._resize_data["height"] + dy)

        self.area_selector.geometry(f"{new_width}x{new_height}+{new_x}+{new_y}")

    def hide_area_selector(self):
        """Hide and save the area selector"""
        if self.area_selector:
            self.settings.save_area_coords(self.area_coords)
            self.screen.set_scan_area(self.area_coords)  # Update screen capture
            self.area_selector.destroy()
            self.area_selector = None

    def show_area_outline(self):
        """Show a small green outline of the detection area during macro execution"""
        if self.area_outline is None and self.area_coords:
            self.area_outline = tk.Toplevel(self.root)
            self.area_outline.title("Area Outline")
            self.area_outline.attributes("-alpha", 0.7)
            self.area_outline.attributes("-topmost", True)
            self.area_outline.overrideredirect(True)

            # Set position and size from saved coords
            x = self.area_coords["x"]
            y = self.area_coords["y"]
            width = self.area_coords["width"]
            height = self.area_coords["height"]
            self.area_outline.geometry(f"{width}x{height}+{x}+{y}")

            # Create a frame with thin green border
            frame = tk.Frame(
                self.area_outline,
                bg="black",
                highlightbackground="#00ff00",
                highlightthickness=2,
            )
            frame.pack(fill=tk.BOTH, expand=True)

            # Make it click-through (transparent to mouse)
            self.area_outline.attributes("-transparentcolor", "black")

            # Prevent from closing
            self.area_outline.protocol("WM_DELETE_WINDOW", lambda: None)

    def hide_area_outline(self):
        """Hide the area outline"""
        if self.area_outline:
            self.area_outline.destroy()
            self.area_outline = None

    def show_auto_craft_area_selector(self):
        """Show the auto craft area selector window"""
        if self.auto_craft_area_selector is None:
            self.auto_craft_area_selector = tk.Toplevel(self.root)
            self.auto_craft_area_selector.title("Auto Craft Area Selector")
            self.auto_craft_area_selector.attributes("-alpha", 0.3)
            self.auto_craft_area_selector.attributes("-topmost", True)
            self.auto_craft_area_selector.overrideredirect(True)

            # Set position and size from saved coords
            x = self.auto_craft_area_coords["x"]
            y = self.auto_craft_area_coords["y"]
            width = self.auto_craft_area_coords["width"]
            height = self.auto_craft_area_coords["height"]
            self.auto_craft_area_selector.geometry(f"{width}x{height}+{x}+{y}")

            # Create a frame with border (blue for auto craft)
            frame = tk.Frame(
                self.auto_craft_area_selector,
                bg="blue",
                highlightbackground="blue",
                highlightthickness=3,
            )
            frame.pack(fill=tk.BOTH, expand=True)

            # Make draggable
            self._auto_craft_drag_data = {"x": 0, "y": 0}
            frame.bind("<ButtonPress-1>", self.start_auto_craft_drag)
            frame.bind("<B1-Motion>", self.on_auto_craft_drag)

            # Make resizable - create resize handles
            self.create_auto_craft_resize_handles(frame)

            # Prevent from closing
            self.auto_craft_area_selector.protocol("WM_DELETE_WINDOW", lambda: None)

    def create_auto_craft_resize_handles(self, frame):
        """Create resize handles on all corners and edges of the auto craft area selector"""
        handle_size = 12
        edge_thickness = 6

        # Corner handles
        # Top-left corner
        tl_handle = tk.Frame(
            frame,
            bg="yellow",
            cursor="size_nw_se",
            width=handle_size,
            height=handle_size,
        )
        tl_handle.place(x=0, y=0, anchor="nw")
        tl_handle.bind(
            "<ButtonPress-1>", lambda e: self.start_auto_craft_resize(e, "top-left")
        )
        tl_handle.bind(
            "<B1-Motion>", lambda e: self.on_auto_craft_resize(e, "top-left")
        )

        # Top-right corner
        tr_handle = tk.Frame(
            frame,
            bg="yellow",
            cursor="size_ne_sw",
            width=handle_size,
            height=handle_size,
        )
        tr_handle.place(relx=1.0, y=0, anchor="ne")
        tr_handle.bind(
            "<ButtonPress-1>", lambda e: self.start_auto_craft_resize(e, "top-right")
        )
        tr_handle.bind(
            "<B1-Motion>", lambda e: self.on_auto_craft_resize(e, "top-right")
        )

        # Bottom-left corner
        bl_handle = tk.Frame(
            frame,
            bg="yellow",
            cursor="size_ne_sw",
            width=handle_size,
            height=handle_size,
        )
        bl_handle.place(x=0, rely=1.0, anchor="sw")
        bl_handle.bind(
            "<ButtonPress-1>", lambda e: self.start_auto_craft_resize(e, "bottom-left")
        )
        bl_handle.bind(
            "<B1-Motion>", lambda e: self.on_auto_craft_resize(e, "bottom-left")
        )

        # Bottom-right corner
        br_handle = tk.Frame(
            frame,
            bg="yellow",
            cursor="size_nw_se",
            width=handle_size,
            height=handle_size,
        )
        br_handle.place(relx=1.0, rely=1.0, anchor="se")
        br_handle.bind(
            "<ButtonPress-1>", lambda e: self.start_auto_craft_resize(e, "bottom-right")
        )
        br_handle.bind(
            "<B1-Motion>", lambda e: self.on_auto_craft_resize(e, "bottom-right")
        )

        # Edge handles
        # Top edge
        t_handle = tk.Frame(
            frame, bg="lime", cursor="sb_v_double_arrow", height=edge_thickness
        )
        t_handle.place(relx=0.5, y=0, anchor="n", relwidth=0.7)
        t_handle.bind(
            "<ButtonPress-1>", lambda e: self.start_auto_craft_resize(e, "top")
        )
        t_handle.bind("<B1-Motion>", lambda e: self.on_auto_craft_resize(e, "top"))

        # Bottom edge
        b_handle = tk.Frame(
            frame, bg="lime", cursor="sb_v_double_arrow", height=edge_thickness
        )
        b_handle.place(relx=0.5, rely=1.0, anchor="s", relwidth=0.7)
        b_handle.bind(
            "<ButtonPress-1>", lambda e: self.start_auto_craft_resize(e, "bottom")
        )
        b_handle.bind("<B1-Motion>", lambda e: self.on_auto_craft_resize(e, "bottom"))

        # Left edge
        l_handle = tk.Frame(
            frame, bg="lime", cursor="sb_h_double_arrow", width=edge_thickness
        )
        l_handle.place(x=0, rely=0.5, anchor="w", relheight=0.7)
        l_handle.bind(
            "<ButtonPress-1>", lambda e: self.start_auto_craft_resize(e, "left")
        )
        l_handle.bind("<B1-Motion>", lambda e: self.on_auto_craft_resize(e, "left"))

        # Right edge
        r_handle = tk.Frame(
            frame, bg="lime", cursor="sb_h_double_arrow", width=edge_thickness
        )
        r_handle.place(relx=1.0, rely=0.5, anchor="e", relheight=0.7)
        r_handle.bind(
            "<ButtonPress-1>", lambda e: self.start_auto_craft_resize(e, "right")
        )
        r_handle.bind("<B1-Motion>", lambda e: self.on_auto_craft_resize(e, "right"))

    def start_auto_craft_drag(self, event):
        """Start dragging the auto craft area selector"""
        self._auto_craft_drag_data["x"] = event.x
        self._auto_craft_drag_data["y"] = event.y

    def on_auto_craft_drag(self, event):
        """Handle dragging the auto craft area selector"""
        x = (
            self.auto_craft_area_selector.winfo_x()
            + event.x
            - self._auto_craft_drag_data["x"]
        )
        y = (
            self.auto_craft_area_selector.winfo_y()
            + event.y
            - self._auto_craft_drag_data["y"]
        )
        self.auto_craft_area_selector.geometry(f"+{x}+{y}")

    def start_auto_craft_resize(self, event, direction="both"):
        """Start resizing the auto craft area selector"""
        self._auto_craft_resize_data = {
            "x": event.x_root,
            "y": event.y_root,
            "width": self.auto_craft_area_selector.winfo_width(),
            "height": self.auto_craft_area_selector.winfo_height(),
            "win_x": self.auto_craft_area_selector.winfo_x(),
            "win_y": self.auto_craft_area_selector.winfo_y(),
            "direction": direction,
        }

    def on_auto_craft_resize(self, event, direction="both"):
        """Handle resizing the auto craft area selector from any corner or edge"""
        if not hasattr(self, "_auto_craft_resize_data"):
            return

        dx = event.x_root - self._auto_craft_resize_data["x"]
        dy = event.y_root - self._auto_craft_resize_data["y"]

        new_width = self._auto_craft_resize_data["width"]
        new_height = self._auto_craft_resize_data["height"]
        new_x = self._auto_craft_resize_data["win_x"]
        new_y = self._auto_craft_resize_data["win_y"]

        direction = self._auto_craft_resize_data.get("direction", "both")
        min_size = 50

        # Handle each direction
        if (
            direction == "right"
            or direction == "bottom-right"
            or direction == "top-right"
        ):
            new_width = max(min_size, self._auto_craft_resize_data["width"] + dx)
        if direction == "left" or direction == "bottom-left" or direction == "top-left":
            new_width = max(min_size, self._auto_craft_resize_data["width"] - dx)
            new_x = self._auto_craft_resize_data["win_x"] + dx
        if (
            direction == "bottom"
            or direction == "bottom-right"
            or direction == "bottom-left"
        ):
            new_height = max(min_size, self._auto_craft_resize_data["height"] + dy)
        if direction == "top" or direction == "top-right" or direction == "top-left":
            new_height = max(min_size, self._auto_craft_resize_data["height"] - dy)
            new_y = self._auto_craft_resize_data["win_y"] + dy
        if direction == "both":
            new_width = max(min_size, self._auto_craft_resize_data["width"] + dx)
            new_height = max(min_size, self._auto_craft_resize_data["height"] + dy)

        self.auto_craft_area_selector.geometry(
            f"{new_width}x{new_height}+{new_x}+{new_y}"
        )

    def hide_auto_craft_area_selector(self):
        """Hide and save the auto craft area selector"""
        if self.auto_craft_area_selector:
            self.settings.save_auto_craft_area_coords(self.auto_craft_area_coords)
            self.screen.set_auto_craft_area(
                self.auto_craft_area_coords
            )  # Update screen capture
            self.auto_craft_area_selector.destroy()
            self.auto_craft_area_selector = None

    def save_auto_craft_settings(self):
        """Save auto craft settings to settings file"""
        try:
            auto_craft_dict = {
                "auto_craft_enabled": self.auto_craft_enabled,
                "auto_craft_water_point": self.auto_craft_water_point,
                "craft_every_n_fish": self.craft_every_n_fish,
                "craft_menu_delay": self.craft_menu_delay,
                "craft_click_speed": self.craft_click_speed,
                "craft_legendary_quantity": self.craft_legendary_quantity,
                "craft_rare_quantity": self.craft_rare_quantity,
                "craft_common_quantity": self.craft_common_quantity,
                "craft_button_coords": self.craft_button_coords,
                "plus_button_coords": self.plus_button_coords,
                "fish_icon_coords": self.fish_icon_coords,
                "legendary_bait_coords": self.legendary_bait_coords,
                "rare_bait_coords": self.rare_bait_coords,
                "common_bait_coords": self.common_bait_coords,
                "smart_bait_2nd_coords": self.smart_bait_2nd_coords,
            }
            self.settings.save_auto_craft_settings(auto_craft_dict)

            # Sync coordinates with automation modules
            if hasattr(self, "craft_automation") and self.craft_automation:
                self.craft_automation.update_coords(
                    common_bait_coords=self.common_bait_coords,
                    rare_bait_coords=self.rare_bait_coords,
                    legendary_bait_coords=self.legendary_bait_coords,
                    plus_button_coords=self.plus_button_coords,
                    fish_icon_coords=self.fish_icon_coords,
                    craft_button_coords=self.craft_button_coords,
                )

            if hasattr(self, "bait_manager") and self.bait_manager:
                self.bait_manager.update_coords(
                    smart_bait_2nd_coords=self.smart_bait_2nd_coords
                )

            if hasattr(self, "fishing_cycle") and self.fishing_cycle:
                self.fishing_cycle.update_coords(
                    auto_craft_water_point=self.auto_craft_water_point
                )
        except Exception as e:
            print(f"Error saving auto craft settings: {e}")

    def find_biggest_black_group(self, image, target_color, max_gap):
        """Find the biggest group of black pixels with allowed gap tolerance"""
        if image is None or image.size == 0:
            return None

        height = image.shape[0]

        # Find all pixels that match the target color (with tolerance)
        tolerance = 5
        matches = []
        for y in range(height):
            pixel = image[y, 0, :3]  # Get RGB values
            if all(abs(int(pixel[i]) - target_color[i]) <= tolerance for i in range(3)):
                matches.append(y)

        if not matches:
            return None

        # Group pixels with gap tolerance
        groups = []
        current_group = [matches[0]]

        for i in range(1, len(matches)):
            gap = matches[i] - matches[i - 1] - 1  # Gap between consecutive matches
            if gap <= max_gap:
                # Continue current group
                current_group.append(matches[i])
            else:
                # Start new group
                groups.append(current_group)
                current_group = [matches[i]]

        # Don't forget the last group
        groups.append(current_group)

        # Find biggest group
        biggest_group = max(groups, key=len)

        # Return middle of biggest group
        return (biggest_group[0] + biggest_group[-1]) // 2


def show_terms_of_use():
    """Show Terms of Use dialog - returns True if accepted, False if declined"""

    # Terms of Use text in English only
    terms_text = """BPS FISHING MACRO - TERMS OF USE

1. PURPOSE
This software is designed for educational and personal use only.
The user assumes full responsibility for its usage.

2. DISCLAIMER
- This macro is provided "AS IS" without warranty of any kind.
- The developers are not responsible for any bans, suspensions, 
  or account actions taken by game developers.
- Use at your own risk.

3. RESTRICTIONS
- Do NOT sell, redistribute, or claim this software as your own.
- Do NOT use this software for commercial purposes.
- Respect the game's terms of service.

4. CREDITS
• Developed by: BPS
• Inspired by: Asphalt Cake's original work
• Special thanks to the GPO Community

By clicking "I AGREE", you acknowledge that you have read and 
accept these terms and understand the risks involved.

Do you agree to these terms?"""

    btn_agree = "I AGREE"
    btn_decline = "I DECLINE"

    # Create dialog window
    dialog = tk.Tk()
    dialog.title("Terms of Use - BPS Fishing Macro")
    dialog.geometry("650x700")
    dialog.resizable(False, False)

    # Make it always on top and modal
    dialog.attributes("-topmost", True)
    dialog.grab_set()

    # Store user choice
    user_accepted = [False]

    # Header frame
    header_frame = tk.Frame(dialog, bg="#2c3e50", height=60)
    header_frame.pack(fill=tk.X)
    header_frame.pack_propagate(False)

    title_label = tk.Label(
        header_frame,
        text="⚡ BPS FISHING MACRO ⚡",
        font=("Arial", 16, "bold"),
        fg="#00ff88",
        bg="#2c3e50",
    )
    title_label.pack(expand=True)

    # Text widget with scrollbar - FIXED HEIGHT
    text_frame = tk.Frame(dialog, bg="#ecf0f1", padx=20, pady=15)
    text_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=10)

    scrollbar = tk.Scrollbar(text_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    text_widget = tk.Text(
        text_frame,
        wrap=tk.WORD,
        font=("Consolas", 9),
        bg="#ffffff",
        fg="#2c3e50",
        padx=10,
        pady=10,
        yscrollcommand=scrollbar.set,
        relief=tk.FLAT,
        borderwidth=1,
        height=22,
        width=75,
    )
    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=text_widget.yview)

    # Insert terms text
    text_widget.insert("1.0", terms_text)
    text_widget.config(state=tk.DISABLED)  # Make read-only

    # Spacer to separate buttons
    spacer = tk.Frame(dialog, bg="#ecf0f1", height=10)
    spacer.pack(fill=tk.X)
    spacer.pack_propagate(False)

    # Buttons frame - SEPARATE AND FIXED
    button_frame = tk.Frame(dialog, bg="#ecf0f1", height=60)
    button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
    button_frame.pack_propagate(False)

    def on_agree():
        user_accepted[0] = True
        dialog.destroy()

    def on_decline():
        user_accepted[0] = False
        dialog.destroy()

    # Decline button (red) - LEFT
    decline_btn = tk.Button(
        button_frame,
        text=f"❌ {btn_decline}",
        command=on_decline,
        font=("Arial", 11, "bold"),
        bg="#e74c3c",
        fg="white",
        padx=25,
        pady=12,
        relief=tk.RAISED,
        borderwidth=2,
        cursor="hand2",
        width=15,
    )
    decline_btn.pack(side=tk.LEFT, padx=10)

    # Agree button (green) - RIGHT
    agree_btn = tk.Button(
        button_frame,
        text=f"✓ {btn_agree}",
        command=on_agree,
        font=("Arial", 11, "bold"),
        bg="#27ae60",
        fg="white",
        padx=25,
        pady=12,
        relief=tk.RAISED,
        borderwidth=2,
        cursor="hand2",
        width=15,
    )
    agree_btn.pack(side=tk.RIGHT, padx=10)

    # Handle window close (treat as decline)
    dialog.protocol("WM_DELETE_WINDOW", on_decline)

    # Center the dialog on screen
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (600 // 2)
    y = (dialog.winfo_screenheight() // 2) - (500 // 2)
    dialog.geometry(f"600x500+{x}+{y}")

    # Run dialog
    dialog.mainloop()

    return user_accepted[0]


def main():
    # Check if running as administrator
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except:
        is_admin = False

    if not is_admin:
        # Re-run the program with admin rights
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        return

    # Check if settings file exists
    if not os.path.exists(SETTINGS_FILE):
        # First run - show Terms of Use
        if not show_terms_of_use():
            # User declined terms - exit application
            return
        # User accepted - settings will be created by FishingMacroGUI.__init__

    # Create main application with customtkinter
    root = ctk.CTk()
    app = FishingMacroGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
