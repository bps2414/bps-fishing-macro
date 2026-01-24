# Copyright (C) 2026 BPS
# This file is part of BPS Fishing Macro.
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

import customtkinter as ctk
import tkinter as tk
import threading
import time
import os
import sys
import json
import tempfile
import numpy as np
import mss
import ctypes
import win32api
import win32gui
import winsound  # V3: Sound notifications (fallback)
import logging   # V3: Activity logging
import sqlite3   # V3: Advanced stats database
try:
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
    import pygame  # V3: Custom audio support
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except:
    PYGAME_AVAILABLE = False
from datetime import datetime, timedelta  # V3: Daily summary
from pynput import keyboard
from pynput.keyboard import Key, Listener, Controller
from pynput.mouse import Listener as MouseListener, Button, Controller as MouseController
import pyautogui
import pydirectinput

# Disable fail-safe (prevent crash when mouse hits corner)
# User has F1/F3 hotkeys to stop the macro safely
pyautogui.FAILSAFE = False

# V3: Setup logging
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)) if not getattr(sys, 'frozen', False) else os.path.dirname(sys.executable), 'fishing_macro.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('FishingMacro')

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

# Get screen resolution
SCREEN_WIDTH = ctypes.windll.user32.GetSystemMetrics(0)
SCREEN_HEIGHT = ctypes.windll.user32.GetSystemMetrics(1)
REF_WIDTH = 1920  # Reference resolution width
REF_HEIGHT = 1080  # Reference resolution height

# Get base directory for persistent files (settings, db)
def get_app_dir():
    """Get the directory where the executable/script is located (for settings/logs)"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return os.path.dirname(sys.executable)
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))

# Get base directory for embedded resources (images, sounds)
def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller/Nuitka/Onefile"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Nuitka or normal script
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)

BASE_DIR = get_app_dir()
SETTINGS_FILE = os.path.join(BASE_DIR, 'bpsfishmacrosettings.json')
# Audio file is now looked for in the resource path (embedded) first, or relative to script
AUDIO_FILE = get_resource_path('you-got-a-devil-fruit-sound-gpo-made-with-Voicemod.mp3')

# Default coordinates for 1920x1080 (will be scaled to user's resolution)
# Only AREA configurations are set by default to match current user optimized settings
DEFAULT_COORDS_1920x1080 = {
    'area_coords': {
        'x': 1089,
        'y': -4,
        'width': 573,
        'height': 1084
    },
    'auto_craft_area_coords': {
        'x': 1269,
        'y': -4,
        'width': 498,
        'height': 1092
    },
    # Button coordinates are left essentially empty/None in defaults
    # to force/encourage user selection or are handled dynamically
    'water_point': None,
    'yes_button': None,
    'middle_button': None,
    'no_button': None,
    'fruit_point': None,
    'top_bait_point': None
}

def scale_coord(coord_dict):
    """Scale coordinates from 1920x1080 to current screen resolution"""
    if not coord_dict:
        return None
        
    scaled = {}
    for key, value in coord_dict.items():
        if key in ['x', 'width']:
            scaled[key] = int(value * SCREEN_WIDTH / REF_WIDTH)
        elif key in ['y', 'height']:
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

# ============================================================================
# V3: ADVANCED STATISTICS SYSTEM WITH SQLITE
# ============================================================================
class StatsManager:
    """Advanced Statistics Manager with SQLite persistence"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(BASE_DIR, 'fishing_stats.db')
        self.session_id = None
        self.session_start = None
        self._fish_count = 0
        self._fruit_count = 0
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        start_time TEXT NOT NULL,
                        end_time TEXT,
                        fish_count INTEGER DEFAULT 0,
                        fruit_count INTEGER DEFAULT 0
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS catches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id INTEGER,
                        type TEXT NOT NULL,
                        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES sessions(id)
                    )
                ''')
                conn.commit()
        except Exception as e:
            logger.error(f"Stats DB init error: {e}")
    
    def start_session(self) -> int:
        """Start a new fishing session"""
        try:
            self.session_start = datetime.now()
            self._fish_count = 0
            self._fruit_count = 0
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO sessions (start_time) VALUES (?)', 
                              (self.session_start.isoformat(),))
                self.session_id = cursor.lastrowid
                conn.commit()
            logger.info(f"Stats session started: {self.session_id}")
            return self.session_id
        except Exception as e:
            logger.error(f"Start session error: {e}")
            return -1
    
    def end_session(self):
        """End current session and save totals"""
        if not self.session_id:
            return
        try:
            end_time = datetime.now()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE sessions SET end_time = ?, fish_count = ?, fruit_count = ?
                    WHERE id = ?
                ''', (end_time.isoformat(), self._fish_count, self._fruit_count, self.session_id))
                conn.commit()
            duration = end_time - self.session_start if self.session_start else timedelta(0)
            logger.info(f"Session ended: fish={self._fish_count}, fruits={self._fruit_count}, duration={duration}")
            self.session_id = None
            self.session_start = None
        except Exception as e:
            logger.error(f"End session error: {e}")
    
    def log_fish(self):
        """Log a fish catch"""
        self._fish_count += 1
        self._log_catch('fish')
    
    def log_fruit(self):
        """Log a fruit catch"""
        self._fruit_count += 1
        self._log_catch('fruit')
    
    def _log_catch(self, catch_type: str):
        """Internal: log catch to database"""
        if not self.session_id:
            return
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO catches (session_id, type) VALUES (?, ?)',
                              (self.session_id, catch_type))
                conn.commit()
        except Exception as e:
            logger.error(f"Log catch error: {e}")
    
    @property
    def fish_count(self) -> int:
        return self._fish_count
    
    @property  
    def fruit_count(self) -> int:
        return self._fruit_count
    
    def get_session_duration(self) -> float:
        """Get current session duration in seconds"""
        if self.session_start:
            return (datetime.now() - self.session_start).total_seconds()
        return 0.0
    
    def get_today_summary(self) -> dict:
        """Get today's statistics"""
        today = datetime.now().date().isoformat()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*), COALESCE(SUM(fish_count), 0), COALESCE(SUM(fruit_count), 0)
                    FROM sessions WHERE date(start_time) = ?
                ''', (today,))
                row = cursor.fetchone()
                return {'date': today, 'sessions': row[0], 'fish': row[1], 'fruits': row[2]}
        except:
            return {'date': today, 'sessions': 0, 'fish': 0, 'fruits': 0}
    
    def get_historical(self, days: int = 7) -> list:
        """Get summary for last N days"""
        results = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).date().isoformat()
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT COALESCE(SUM(fish_count), 0), COALESCE(SUM(fruit_count), 0)
                        FROM sessions WHERE date(start_time) = ?
                    ''', (date,))
                    row = cursor.fetchone()
                    results.append({'date': date, 'fish': row[0], 'fruits': row[1]})
            except:
                results.append({'date': date, 'fish': 0, 'fruits': 0})
        return results
    
    def export_csv(self, filepath: str) -> bool:
        """Export all sessions to CSV"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM sessions ORDER BY start_time DESC')
                rows = cursor.fetchall()
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write('id,start_time,end_time,fish_count,fruit_count\n')
                    for row in rows:
                        f.write(','.join(str(x) if x else '' for x in row) + '\n')
            logger.info(f"Exported {len(rows)} sessions to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Export CSV error: {e}")
            return False

# Global stats manager instance
stats_manager = None

# ============================================================================
# TOOLTIP CLASS FOR HOVER HINTS
# ============================================================================
class CTkToolTip:
    """Tooltip widget for CustomTkinter - shows hint on hover"""
    
    def __init__(self, widget, text, delay=400, bg_color="#2d2d2d", fg_color="#ffffff", 
                 font=("Segoe UI", 10), wrap_length=250):
        """
        Create a tooltip for a widget.
        
        Args:
            widget: The widget to attach the tooltip to
            text: The tooltip text to display
            delay: Delay in ms before showing tooltip (default 400ms)
            bg_color: Background color of tooltip
            fg_color: Text color of tooltip
            font: Font tuple for text
            wrap_length: Maximum width before text wraps
        """
        self.widget = widget
        self.text = text
        self.delay = delay
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.font = font
        self.wrap_length = wrap_length
        self.tooltip_window = None
        self.after_id = None
        
        # Bind mouse events
        self.widget.bind("<Enter>", self._on_enter, add="+")
        self.widget.bind("<Leave>", self._on_leave, add="+")
        self.widget.bind("<Motion>", self._on_motion, add="+")
    
    def _on_enter(self, event):
        """Mouse entered widget - schedule tooltip"""
        self._schedule_tooltip()
    
    def _on_leave(self, event):
        """Mouse left widget - hide tooltip"""
        self._cancel_tooltip()
        self._hide_tooltip()
    
    def _on_motion(self, event):
        """Mouse moved - reschedule tooltip"""
        if self.tooltip_window:
            # Update position if tooltip is visible
            x = event.x_root + 15
            y = event.y_root + 10
            self.tooltip_window.geometry(f"+{x}+{y}")
        else:
            # Reschedule if not yet visible
            self._cancel_tooltip()
            self._schedule_tooltip()
    
    def _schedule_tooltip(self):
        """Schedule tooltip to appear after delay"""
        self._cancel_tooltip()
        self.after_id = self.widget.after(self.delay, self._show_tooltip)
    
    def _cancel_tooltip(self):
        """Cancel scheduled tooltip"""
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
    
    def _show_tooltip(self):
        """Show the tooltip window"""
        if self.tooltip_window or not self.text:
            return
        
        # Get mouse position
        try:
            x = self.widget.winfo_pointerx() + 15
            y = self.widget.winfo_pointery() + 10
        except:
            return
        
        # Create tooltip window
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_attributes("-topmost", True)
        
        # Create tooltip content with padding
        frame = tk.Frame(self.tooltip_window, bg=self.bg_color, padx=8, pady=6)
        frame.pack()
        
        # Add border effect
        frame.configure(highlightbackground="#555555", highlightthickness=1)
        
        label = tk.Label(
            frame,
            text=self.text,
            bg=self.bg_color,
            fg=self.fg_color,
            font=self.font,
            wraplength=self.wrap_length,
            justify="left"
        )
        label.pack()
        
        # Position tooltip
        self.tooltip_window.geometry(f"+{x}+{y}")
    
    def _hide_tooltip(self):
        """Hide the tooltip window"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
    
    def update_text(self, new_text):
        """Update the tooltip text"""
        self.text = new_text
        if self.tooltip_window:
            self._hide_tooltip()

class FishingMacroGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("BPS Fishing Macro")
        self.root.geometry("600x550")
        self.root.resizable(True, True)
        
        # CustomTkinter colors - V3 Dark + White Minimalist
        self.bg_color = "#141414"       # Main background
        self.fg_color = "#f5f5f5"       # Text color (soft white)
        self.accent_color = "#3a3a3a"   # Neutral accent (no neon)
        self.button_color = "#2a2a2a"   # Button background
        self.hover_color = "#3d3d3d"    # Hover state
        
        # Status accent colors (only for confirmations)
        self.success_color = "#34d399"  # Green for success
        self.warning_color = "#fbbf24"  # Amber for warnings
        self.error_color = "#f87171"    # Red for errors
        
        # Legacy color dict for compatibility with .config() calls on some widgets
        self.current_colors = {
            'success': '#34d399',
            'error': '#f87171',
            'warning': '#fbbf24',
            'info': '#60a5fa',
            'accent': '#4a4a4a',
            'fg': '#f5f5f5',
            'bg': '#141414'
        }
        
        # Create default settings if file doesn't exist
        self.create_default_settings_if_needed()
        
        # Dark mode flag (always True with customtkinter)
        self.dark_mode = True
        
        # Load settings
        self.always_on_top = self.load_always_on_top()
        
        # Status variables
        self.running = False
        self.area_active = False
        self.is_rebinding = None
        self.area_selector = None
        self.area_coords = self.load_area_coords()
        self.water_point = self.load_water_point()  # Water point coordinates
        self.selecting_water_point = False  # Flag for water point selection mode
        self.fruit_point = None  # Fruit detection coordinate
        self.fruit_color = None  # RGB color of fruit at fruit_point
        self.selecting_fruit_point = False  # Flag for fruit point selection mode
        
        # Auto craft variables
        auto_craft_settings = self.load_auto_craft_settings()
        self.auto_craft_enabled = auto_craft_settings.get('auto_craft_enabled', False)
        self.auto_craft_area_active = False
        self.auto_craft_area_selector = None
        self.auto_craft_area_coords = self.load_auto_craft_area_coords()
        self.auto_craft_water_point = auto_craft_settings.get('auto_craft_water_point', None)
        self.selecting_auto_craft_water_point = False
        
        # Auto craft configuration
        self.craft_every_n_fish = auto_craft_settings.get('craft_every_n_fish', 10)
        self.craft_menu_delay = auto_craft_settings.get('craft_menu_delay', 0.5)
        self.craft_click_speed = auto_craft_settings.get('craft_click_speed', 0.2)
        self.craft_legendary_quantity = auto_craft_settings.get('craft_legendary_quantity', 1)
        self.craft_rare_quantity = auto_craft_settings.get('craft_rare_quantity', 1)
        self.craft_common_quantity = auto_craft_settings.get('craft_common_quantity', 1)
        
        # Auto craft coordinates
        self.craft_button_coords = auto_craft_settings.get('craft_button_coords', None)
        self.plus_button_coords = auto_craft_settings.get('plus_button_coords', None)
        self.fish_icon_coords = auto_craft_settings.get('fish_icon_coords', None)
        self.legendary_bait_coords = auto_craft_settings.get('legendary_bait_coords', None)
        self.rare_bait_coords = auto_craft_settings.get('rare_bait_coords', None)
        self.common_bait_coords = auto_craft_settings.get('common_bait_coords', None)
        self.selecting_auto_craft_coord = None  # Track which coordinate is being selected
        
        # Casting settings
        casting_settings = self.load_casting_settings()
        self.cast_hold_duration = casting_settings['cast_hold_duration']
        self.recast_timeout = casting_settings['recast_timeout']
        self.fishing_end_delay = casting_settings.get('fishing_end_delay', 0.2)  # Minimum safe delay
        
        # Pre-cast settings
        precast_settings = self.load_precast_settings()
        self.auto_buy_bait = precast_settings.get('auto_buy_bait', True)
        self.auto_store_fruit = precast_settings.get('auto_store_fruit', False)
        self.loops_per_purchase = precast_settings.get('loops_per_purchase', 100)
        self.yes_button = precast_settings.get('yes_button', None)
        self.middle_button = precast_settings.get('middle_button', None)
        self.no_button = precast_settings.get('no_button', None)
        self.selecting_button = None  # Track which button is being selected
        self.bait_loop_counter = 0  # Starts at 0 so first run executes immediately
        self.fruit_point = precast_settings.get('fruit_point', None)  # Fruit detection coordinate
        self.fruit_color = precast_settings.get('fruit_color', None)  # RGB color of fruit
        self.selecting_fruit_point = False  # Flag for fruit point selection mode
        self.auto_select_top_bait = precast_settings.get('auto_select_top_bait', False)
        self.top_bait_point = precast_settings.get('top_bait_point', None)
        self.selecting_top_bait_point = False
        
        # New: Store in inventory instead of dropping
        self.store_in_inventory = precast_settings.get('store_in_inventory', False)
        self.inventory_fruit_point = precast_settings.get('inventory_fruit_point', None)
        self.inventory_center_point = precast_settings.get('inventory_center_point', None)
        self.selecting_inventory_fruit_point = False
        self.selecting_inventory_center_point = False
        
        # Debug arrows
        self.debug_arrow = None  # Debug arrow window
        self.horizontal_arrow_top = None  # Horizontal arrow for top
        self.horizontal_arrow_bottom = None  # Horizontal arrow for bottom
        self.white_middle_arrow = None  # Arrow pointing to white middle
        self.black_group_arrow = None  # Arrow pointing to biggest black group middle
        
        # Default hotkeys
        self.hotkeys = {
            'start': 'f1',
            'area': 'f2',
            'exit': 'f3'
        }
        
        # Item hotkeys (1-10 selectable)
        item_hotkeys = self.load_item_hotkeys()
        self.rod_hotkey = item_hotkeys.get('rod', '1')
        self.everything_else_hotkey = item_hotkeys.get('everything_else', '2')
        self.fruit_hotkey = item_hotkeys.get('fruit', '3')
        
        self.listener = None
        self.main_thread = None
        
        # Statistics tracking
        self.start_time = None
        self.fruits_caught = 0
        self.fish_caught = 0
        self.fish_at_last_fruit = 0
        self.hud_window = None
        self.first_run = True  # Flag to run initial scroll setup
        self.first_catch = True  # Flag to skip counting first catch after start
        self.current_status = "Idle"  # Current macro activity status
        self.area_outline = None  # Green outline window during macro execution
        self.hud_position = self.load_hud_position()  # HUD position: 'top', 'bottom-left', 'bottom-right'
        
        # V3: FPS tracking for detection rate
        self.detection_fps = 0.0  # Current detection FPS
        self.fps_frame_count = 0  # Frame counter for FPS calculation
        self.fps_last_time = time.time()  # Last time FPS was calculated
        
        # V3: Sound notification settings - load from file
        sound_settings = self.load_sound_settings()
        self.sound_enabled = sound_settings.get('sound_enabled', True)
        self.sound_frequency = sound_settings.get('sound_frequency', 400)  # Lower frequency is softer
        self.sound_duration = sound_settings.get('sound_duration', 150)  # Shorter duration is less annoying
        
        # V3: Daily summary tracking
        self.session_start_date = datetime.now().date()
        self.daily_fish = 0
        self.daily_fruits = 0
        
        # Mouse control constants
        self.mouse_pressed = False  # Track mouse state
        
        # V3 Performance: Reusable mss instance for screenshots
        self._mss_instance = None  # Lazy-loaded mss singleton
        
        # Advanced Timing Settings - load from settings FIRST (needed for disable_normal_camera)
        advanced_settings = self.load_advanced_settings()
        
        # New: option to disable rotation/zoom/camera in normal mode
        self.disable_normal_camera = advanced_settings.get('disable_normal_camera', False)
        self.detection_lost_counter = 0  # Counter for consecutive lost detections
        self.max_lost_frames = 10  # Max frames to keep last state before giving up
        
        # Resend mechanism to fix Roblox click bugs
        self.resend_interval = 0.5  # Default 500ms resend interval
        self.last_resend_time = 0.0  # Track last resend time
        
        # Continue loading advanced settings
        # Camera rotation delays
        self.camera_rotation_delay = advanced_settings.get('camera_rotation_delay', 0.01)
        self.camera_rotation_steps = advanced_settings.get('camera_rotation_steps', 6)
        self.camera_rotation_step_delay = advanced_settings.get('camera_rotation_step_delay', 0.01)
        self.camera_rotation_settle_delay = advanced_settings.get('camera_rotation_settle_delay', 0.05)
        # Zoom delays
        self.zoom_ticks = advanced_settings.get('zoom_ticks', 3)
        self.zoom_tick_delay = advanced_settings.get('zoom_tick_delay', 0.01)
        self.zoom_settle_delay = advanced_settings.get('zoom_settle_delay', 0.05)
        # Pre-cast delays
        self.pre_cast_minigame_wait = advanced_settings.get('pre_cast_minigame_wait', 0.2)
        self.store_click_delay = advanced_settings.get('store_click_delay', 0.1)
        self.backspace_delay = advanced_settings.get('backspace_delay', 0.05)
        self.rod_deselect_delay = advanced_settings.get('rod_deselect_delay', 0.05)
        self.rod_select_delay = advanced_settings.get('rod_select_delay', 0.05)
        self.bait_click_delay = advanced_settings.get('bait_click_delay', 0.05)
        # Detection & general delays
        self.fruit_detection_delay = advanced_settings.get('fruit_detection_delay', 0.01)
        self.fruit_detection_settle = advanced_settings.get('fruit_detection_settle', 0.05)
        self.general_action_delay = advanced_settings.get('general_action_delay', 0.01)
        self.mouse_move_settle = advanced_settings.get('mouse_move_settle', 0.01)
        # Focus settle delay after bringing Roblox to foreground
        self.focus_settle_delay = advanced_settings.get('focus_settle_delay', 0.1)
        # Delay after pressing fruit hotkey before checking/storing (wait for held animation)
        self.fruit_hold_delay = advanced_settings.get('fruit_hold_delay', 0.1)
        
        # PID controller variables - load from settings
        pid_settings = self.load_pid_settings()
        self.pid_kp = pid_settings.get('kp', 1.0)
        self.pid_kd = pid_settings.get('kd', 0.3)
        self.pid_clamp = pid_settings.get('clamp', 1.0)
        self.pid_last_error = 0.0
        self.pid_last_time = time.time()
        self.create_gui()
        # Sync checkbox var if it exists
        if hasattr(self, 'disable_normal_camera_var'):
            self.disable_normal_camera_var.set(self.disable_normal_camera)
        self.setup_hotkeys()
        
        # Print screen resolution info
        logger.info(f"=== BPS Fishing Macro V3 ===")
        logger.info(f"Screen Resolution: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
        logger.info(f"Reference Resolution: {REF_WIDTH}x{REF_HEIGHT}")
        if SCREEN_WIDTH != REF_WIDTH or SCREEN_HEIGHT != REF_HEIGHT:
            scale_x = SCREEN_WIDTH / REF_WIDTH
            scale_y = SCREEN_HEIGHT / REF_HEIGHT
            logger.warning(f"Coordinates scaled by {scale_x:.2f}x (horizontal) and {scale_y:.2f}x (vertical)")
        else:
            logger.info(f"OK: Using native {REF_WIDTH}x{REF_HEIGHT} coordinates")
        
        # Apply always on top if loaded from settings
        if self.always_on_top:
            self.root.attributes('-topmost', True)
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_default_settings_if_needed(self):
        """Create default settings file if it doesn't exist"""
        if not os.path.exists(SETTINGS_FILE):
            print("Creating default settings file...")
            default_settings = {
                'always_on_top': True,
                'area_coords': {
                    'x': 1089,
                    'y': -4,
                    'width': 573,
                    'height': 1084
                },
                'water_point': None,
                'item_hotkeys': {
                    'rod': '1',
                    'everything_else': '2',
                    'fruit': '3'
                },
                'pid_settings': {
                    'kp': 1.0,
                    'kd': 0.3,
                    'clamp': 1.0,
                    'deadband': 1.0
                },
                'casting_settings': {
                    'cast_hold_duration': 1.0,
                    'recast_timeout': 40.0,
                    'fishing_end_delay': 1.5
                },
                'precast_settings': {
                    'auto_buy_bait': True,
                    'auto_store_fruit': True,
                    'auto_select_top_bait': True,
                    'yes_button': None,
                    'middle_button': None,
                    'no_button': None,
                    'loops_per_purchase': 100,
                    'fruit_point': None,
                    'fruit_color': None,
                    'top_bait_point': None
                },
                'webhook_settings': {
                    'webhook_url': '',
                    'user_id': ''
                },
                'hud_position': 'top',
                'advanced_settings': {
                    'camera_rotation_delay': 0.05,
                    'camera_rotation_steps': 8,
                    'camera_rotation_step_delay': 0.05,
                    'camera_rotation_settle_delay': 0.3,
                    'zoom_ticks': 3,
                    'zoom_tick_delay': 0.05,
                    'zoom_settle_delay': 0.3,
                    'pre_cast_minigame_wait': 2.5,
                    'store_click_delay': 1.0,
                    'backspace_delay': 0.3,
                    'rod_deselect_delay': 0.5,
                    'rod_select_delay': 0.5,
                    'bait_click_delay': 0.3,
                    'fruit_detection_delay': 0.02,
                    'fruit_detection_settle': 0.3,
                    'general_action_delay': 0.05,
                    'mouse_move_settle': 0.05,
                    'focus_settle_delay': 1.0,
                    'disable_normal_camera': True,
                    'fruit_hold_delay': 0.1
                },
                'auto_craft_settings': {
                    'auto_craft_enabled': False,
                    'auto_craft_water_point': None,
                    'craft_every_n_fish': 1,
                    'craft_menu_delay': 0.1,
                    'craft_click_speed': 0.1,
                    'craft_legendary_quantity': 1,
                    'craft_rare_quantity': 1,
                    'craft_common_quantity': 1,
                    'craft_button_coords': None,
                    'plus_button_coords': None,
                    'fish_icon_coords': None,
                    'legendary_bait_coords': None,
                    'rare_bait_coords': None,
                    'common_bait_coords': None
                },
                'auto_craft_area_coords': {
                    'x': 1269,
                    'y': -4,
                    'width': 498,
                    'height': 1092
                }
            }
            try:
                with open(SETTINGS_FILE, 'w') as f:
                    json.dump(default_settings, f, indent=4)
                print("✓ Default settings created!")
            except Exception as e:
                print(f"Error creating default settings: {e}")
    
    def interruptible_sleep(self, duration):
        """Sleep that can be interrupted by setting self.running to False"""
        start = time.time()
        while time.time() - start < duration:
            if not self.running:
                return False
            time.sleep(0.05)  # Check every 50ms for faster response
        return True
    
    def create_spinbox_entry(self, parent, default_value, min_val, max_val, step, width=120, is_float=True):
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
            border_color=self.accent_color
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
            command=lambda: self._increment_spinbox(entry, step, max_val, is_float)
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
            command=lambda: self._decrement_spinbox(entry, step, min_val, is_float)
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
                    entry.insert(0, f"{new_value:.3f}" if step < 1 else f"{new_value:.1f}")
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
                    entry.insert(0, f"{new_value:.3f}" if step < 1 else f"{new_value:.1f}")
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
            scrollbar_button_hover_color=self.hover_color
        )
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.create_gui_content()
    
    def create_gui_content(self):
        #Create the main GUI content (separated for theme switching)
        # Clear the scrollable frame
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Title - Clean white text, no fancy colors
        title = ctk.CTkLabel(
            self.scrollable_frame,
            text="BPS Fishing Macro",
            font=("Segoe UI", 24, "bold"),
            text_color=self.fg_color
        )
        title.pack(pady=15)
        
        # Create Tabview (substitui Notebook)
        self.tabview = ctk.CTkTabview(
            self.scrollable_frame,
            fg_color=self.bg_color,
            segmented_button_selected_color="#2d2d2d",
            segmented_button_selected_hover_color=self.hover_color,
            segmented_button_fg_color="#1e1e1e",
            segmented_button_unselected_color="#1e1e1e",
            segmented_button_unselected_hover_color="#2a2a2a"
        )
        self.tabview.pack(fill="both", expand=True, padx=5, pady=10)
        
        # Create tabs - clean names without emojis
        general_tab = self.tabview.add("General")
        settings_tab = self.tabview.add("Settings")
        fishing_tab = self.tabview.add("Fishing")
        auto_craft_tab = self.tabview.add("Auto Craft")
        webhooks_tab = self.tabview.add("Webhooks")
        advanced_tab = self.tabview.add("Advanced")
        stats_tab = self.tabview.add("Stats")
        
        # ========== GENERAL TAB ==========
        # Settings toggles
        settings_frame = ctk.CTkFrame(general_tab, fg_color="transparent")
        settings_frame.pack(fill="x", pady=10)
        
        self.always_on_top_var = tk.BooleanVar(value=self.always_on_top)
        always_on_top_check = ctk.CTkCheckBox(
            settings_frame,
            text="Always on Top",
            variable=self.always_on_top_var,
            command=self.toggle_always_on_top,
            fg_color=self.success_color,
            hover_color=self.hover_color,
            font=("Segoe UI", 11)
        )
        always_on_top_check.pack(side="left", padx=10)
        
        # Status frame
        status_frame = ctk.CTkFrame(general_tab, fg_color=self.button_color, corner_radius=8)
        status_frame.pack(fill="x", pady=8)
        
        status_title = ctk.CTkLabel(
            status_frame,
            text="Status",
            font=("Segoe UI", 12, "bold"),
            text_color=self.fg_color
        )
        status_title.pack(pady=(8, 4))
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="Status: STOPPED",
            font=("Arial", 13, "bold"),
            text_color="#ff4444"
        )
        self.status_label.pack(pady=5)
        
        self.activity_label = ctk.CTkLabel(
            status_frame,
            text="Activity: Idle",
            font=("Arial", 11),
            text_color="#00ccff"
        )
        self.activity_label.pack(pady=(5, 10))
        
        # Controls frame
        controls_frame = ctk.CTkFrame(general_tab, fg_color=self.button_color, corner_radius=8)
        controls_frame.pack(fill="both", expand=True, pady=8)
        
        controls_title = ctk.CTkLabel(
            controls_frame,
            text="Hotkeys",
            font=("Segoe UI", 12, "bold"),
            text_color=self.fg_color
        )
        controls_title.pack(pady=(8, 10))
        
        # Start/Stop row
        start_row = ctk.CTkFrame(controls_frame, fg_color="transparent")
        start_row.pack(fill="x", padx=15, pady=8)
        
        ctk.CTkLabel(start_row, text="▶ Start/Stop", font=("Arial", 12, "bold"), width=120, anchor="w").pack(side="left", padx=5)
        self.start_button = ctk.CTkButton(
            start_row,
            text="START",
            command=self.toggle_start,
            width=100,
            fg_color="#00aa00",
            hover_color="#00dd00",
            font=("Arial", 12, "bold")
        )
        self.start_button.pack(side="left", padx=8)
        self.start_hotkey_label = ctk.CTkLabel(
            start_row,
            text="[F1]",
            font=("Arial", 11, "bold"),
            text_color=self.accent_color,
            width=60
        )
        self.start_hotkey_label.pack(side="left", padx=5)
        ctk.CTkButton(
            start_row,
            text="🔧 Rebind",
            command=lambda: self.start_rebind('start'),
            width=90,
            fg_color=self.button_color,
            hover_color=self.hover_color
        ).pack(side="left")
        
        # Change Area row
        area_row = ctk.CTkFrame(controls_frame, fg_color="transparent")
        area_row.pack(fill="x", padx=15, pady=8)
        
        ctk.CTkLabel(area_row, text="🎯 Change Area", font=("Arial", 12, "bold"), width=120, anchor="w").pack(side="left", padx=5)
        self.area_button = ctk.CTkButton(
            area_row,
            text="OFF",
            command=self.toggle_area,
            width=100,
            fg_color="#666666",
            hover_color="#888888",
            font=("Arial", 12, "bold")
        )
        self.area_button.pack(side="left", padx=8)
        self.area_hotkey_label = ctk.CTkLabel(
            area_row,
            text="[F2]",
            font=("Arial", 11, "bold"),
            text_color=self.accent_color,
            width=60
        )
        self.area_hotkey_label.pack(side="left", padx=5)
        ctk.CTkButton(
            area_row,
            text="🔧 Rebind",
            command=lambda: self.start_rebind('area'),
            width=90,
            fg_color=self.button_color,
            hover_color=self.hover_color
        ).pack(side="left")
        
        # Exit row
        exit_row = ctk.CTkFrame(controls_frame, fg_color="transparent")
        exit_row.pack(fill="x", padx=15, pady=(8, 15))
        
        ctk.CTkLabel(exit_row, text="❌ Exit", font=("Arial", 12, "bold"), width=120, anchor="w").pack(side="left", padx=5)
        self.exit_button = ctk.CTkButton(
            exit_row,
            text="EXIT",
            command=self.force_exit,
            width=100,
            fg_color="#cc0000",
            hover_color="#ff4444",
            font=("Arial", 12, "bold")
        )
        self.exit_button.pack(side="left", padx=8)
        self.exit_hotkey_label = ctk.CTkLabel(
            exit_row,
            text="[F3]",
            font=("Arial", 11, "bold"),
            text_color=self.accent_color,
            width=60
        )
        self.exit_hotkey_label.pack(side="left", padx=5)
        ctk.CTkButton(
            exit_row,
            text="🔧 Rebind",
            command=lambda: self.start_rebind('exit'),
            width=90,
            fg_color=self.button_color,
            hover_color=self.hover_color
        ).pack(side="left")
        
        # Item Hotkeys section
        item_frame = ctk.CTkFrame(general_tab, fg_color="#2b2b2b", corner_radius=10)
        item_frame.pack(fill="x", pady=10)
        
        item_title = ctk.CTkLabel(
            item_frame,
            text="🎣 ITEM HOTKEYS (1-10)",
            font=("Arial", 14, "bold"),
            text_color=self.accent_color
        )
        item_title.pack(pady=(10, 15))
        
        # Rod hotkey row
        rod_row = ctk.CTkFrame(item_frame, fg_color="transparent")
        rod_row.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(rod_row, text="🎣 Rod", font=("Arial", 12, "bold"), width=150, anchor="w").pack(side="left")
        self.rod_hotkey_var = tk.StringVar(value=self.rod_hotkey)
        rod_combo = ctk.CTkComboBox(
            rod_row,
            variable=self.rod_hotkey_var,
            values=[str(i) for i in range(1, 11)],
            width=80,
            state="readonly",
            fg_color=self.button_color,
            button_color=self.accent_color,
            button_hover_color=self.hover_color,
            command=lambda e: self.save_item_hotkeys()
        )
        rod_combo.pack(side="left", padx=8)
        
        # Everything else hotkey row
        everything_row = ctk.CTkFrame(item_frame, fg_color="transparent")
        everything_row.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(everything_row, text="📦 Everything Else", font=("Arial", 12, "bold"), width=150, anchor="w").pack(side="left")
        self.everything_else_hotkey_var = tk.StringVar(value=self.everything_else_hotkey)
        everything_combo = ctk.CTkComboBox(
            everything_row,
            variable=self.everything_else_hotkey_var,
            values=[str(i) for i in range(1, 11)],
            width=80,
            state="readonly",
            fg_color=self.button_color,
            button_color=self.accent_color,
            button_hover_color=self.hover_color,
            command=lambda e: self.save_item_hotkeys()
        )
        everything_combo.pack(side="left", padx=8)
        
        # HUD Position selector
        hud_frame = ctk.CTkFrame(general_tab, fg_color="#2b2b2b", corner_radius=10)
        hud_frame.pack(fill="x", pady=10)
        
        hud_title = ctk.CTkLabel(
            hud_frame,
            text="📊 HUD SETTINGS",
            font=("Arial", 14, "bold"),
            text_color=self.accent_color
        )
        hud_title.pack(pady=(10, 15))
        
        hud_pos_row = ctk.CTkFrame(hud_frame, fg_color="transparent")
        hud_pos_row.pack(fill="x", padx=15, pady=(5, 15))
        ctk.CTkLabel(hud_pos_row, text="HUD Position:", font=("Arial", 12, "bold"), width=150, anchor="w").pack(side="left")
        self.hud_position_var = tk.StringVar(value=self.hud_position.title().replace('-', ' '))
        hud_combo = ctk.CTkComboBox(
            hud_pos_row,
            variable=self.hud_position_var,
            values=['Top', 'Bottom Left', 'Bottom Right'],
            width=150,
            state="readonly",
            fg_color=self.button_color,
            button_color=self.accent_color,
            button_hover_color=self.hover_color,
            command=lambda e: self.save_hud_position()
        )
        hud_combo.pack(side="left", padx=5)
        
        # Info label
        self.info_label = ctk.CTkLabel(
            general_tab,
            text="✓ Ready to fish!",
            font=("Arial", 11, "bold"),
            text_color="#00dd00"
        )
        self.info_label.pack(pady=10)
        
        # ========== SETTINGS TAB ==========
        # V3: Sound Notification section
        sound_frame = ctk.CTkFrame(settings_tab, fg_color="#2b2b2b", corner_radius=10)
        sound_frame.pack(fill="x", pady=10)
        
        sound_title = ctk.CTkLabel(
            sound_frame,
            text="🔔 NOTIFICATIONS",
            font=("Arial", 14, "bold"),
            text_color=self.accent_color
        )
        sound_title.pack(pady=(10, 10))
        
        # Sound notification checkbox
        self.sound_enabled_var = tk.BooleanVar(value=self.sound_enabled)
        sound_check = ctk.CTkCheckBox(
            sound_frame,
            text="🔊 Play sound when fruit detected",
            variable=self.sound_enabled_var,
            command=self.toggle_sound_notification,
            fg_color=self.accent_color,
            hover_color=self.hover_color,
            font=("Arial", 12, "bold")
        )
        sound_check.pack(fill="x", pady=(5, 15), padx=15)
        
        # Pre-Cast section
        precast_frame = ctk.CTkFrame(settings_tab, fg_color="#2b2b2b", corner_radius=10)
        precast_frame.pack(fill="x", pady=10)
        
        precast_title = ctk.CTkLabel(
            precast_frame,
            text="🎣 PRE-CAST SETTINGS",
            font=("Arial", 14, "bold"),
            text_color=self.accent_color
        )
        precast_title.pack(pady=(10, 5))
        
        # Auto Buy Bait checkbox
        self.auto_buy_bait_var = tk.BooleanVar(value=self.auto_buy_bait)
        self.auto_bait_checkbox = ctk.CTkCheckBox(
            precast_frame,
            text="Auto Buy Bait",
            variable=self.auto_buy_bait_var,
            command=self.toggle_auto_buy_bait,
            fg_color=self.success_color,
            hover_color=self.hover_color,
            font=("Segoe UI", 11)
        )
        self.auto_bait_checkbox.pack(fill="x", pady=5, padx=15)
        
        # Warning about mutual exclusion with Auto Craft
        self.auto_bait_warning = ctk.CTkLabel(
            precast_frame,
            text="Cannot be used with Auto Craft mode",
            font=("Segoe UI", 9),
            text_color=self.warning_color
        )
        self.auto_bait_warning.pack(fill="x", pady=(0, 5), padx=15)
        
        # Auto Buy Bait section (shown/hidden based on checkbox)
        self.auto_bait_section = ctk.CTkFrame(precast_frame, fg_color="transparent")
        if self.auto_buy_bait:
            self.auto_bait_section.pack(fill="x", pady=5, padx=12)
        
        # Yes Button row
        yes_button_row = ctk.CTkFrame(self.auto_bait_section, fg_color="transparent")
        yes_button_row.pack(fill="x", pady=5)
        ctk.CTkLabel(yes_button_row, text="✅ Yes Button", font=("Arial", 11, "bold"), width=140, anchor="w").pack(side="left", padx=(0,6))
        self.yes_button_btn = ctk.CTkButton(
            yes_button_row,
            text="Select",
            command=lambda: self.start_button_selection('yes'),
            width=90,
            fg_color=self.button_color,
            hover_color=self.hover_color
        )
        self.yes_button_btn.pack(side="left", padx=6)
        self.yes_button_label = ctk.CTkLabel(yes_button_row, text="None", font=("Arial", 10), text_color="#ffaa00")
        self.yes_button_label.pack(side="left", padx=6)
        if self.yes_button:
            self.yes_button_label.configure(text=f"({self.yes_button['x']}, {self.yes_button['y']})", text_color="#00dd00")
        
        # Middle Button row
        middle_button_row = ctk.CTkFrame(self.auto_bait_section, fg_color="transparent")
        middle_button_row.pack(fill="x", pady=5)
        ctk.CTkLabel(middle_button_row, text="⏸️ Middle Button", font=("Arial", 11, "bold"), width=140, anchor="w").pack(side="left", padx=(0,6))
        self.middle_button_btn = ctk.CTkButton(
            middle_button_row,
            text="Select",
            command=lambda: self.start_button_selection('middle'),
            width=90,
            fg_color=self.button_color,
            hover_color=self.hover_color
        )
        self.middle_button_btn.pack(side="left", padx=6)
        self.middle_button_label = ctk.CTkLabel(middle_button_row, text="None", font=("Arial", 10), text_color="#ffaa00")
        self.middle_button_label.pack(side="left", padx=6)
        if self.middle_button:
            self.middle_button_label.configure(text=f"({self.middle_button['x']}, {self.middle_button['y']})", text_color="#00dd00")
        
        # No Button row
        no_button_row = ctk.CTkFrame(self.auto_bait_section, fg_color="transparent")
        no_button_row.pack(fill="x", pady=5)
        ctk.CTkLabel(no_button_row, text="❌ No Button", font=("Arial", 11, "bold"), width=140, anchor="w").pack(side="left", padx=(0,6))
        self.no_button_btn = ctk.CTkButton(
            no_button_row,
            text="Select",
            command=lambda: self.start_button_selection('no'),
            width=90,
            fg_color=self.button_color,
            hover_color=self.hover_color
        )
        self.no_button_btn.pack(side="left", padx=6)
        self.no_button_label = ctk.CTkLabel(no_button_row, text="None", font=("Arial", 10), text_color="#ffaa00")
        self.no_button_label.pack(side="left", padx=6)
        if self.no_button:
            self.no_button_label.configure(text=f"({self.no_button['x']}, {self.no_button['y']})", text_color="#00dd00")
        
        # Loops per purchase row
        loops_row = ctk.CTkFrame(self.auto_bait_section, fg_color="transparent")
        loops_row.pack(fill="x", pady=8)
        ctk.CTkLabel(loops_row, text="🔄 Loops per purchase:", font=("Arial", 11, "bold"), width=170, anchor="w").pack(side="left", padx=(0,6))
        loops_container, self.loops_entry = self.create_spinbox_entry(
            loops_row, self.loops_per_purchase, min_val=1, max_val=100, step=1, width=90, is_float=False
        )
        loops_container.pack(side="left", padx=5)
        self.loops_entry.bind('<FocusOut>', lambda e: self.save_loops_setting())
        self.loops_entry.bind('<Return>', lambda e: self.save_loops_setting())
        
        # Auto Store Devil Fruit checkbox
        self.auto_store_fruit_var = tk.BooleanVar(value=self.auto_store_fruit)
        self.auto_fruit_checkbox = ctk.CTkCheckBox(
            precast_frame,
            text="Auto Store Devil Fruit",
            variable=self.auto_store_fruit_var,
            command=self.toggle_auto_store_fruit,
            fg_color=self.success_color,
            hover_color=self.hover_color,
            font=("Segoe UI", 11)
        )
        self.auto_fruit_checkbox.pack(fill="x", pady=5, padx=15)
        
        # Auto Store Fruit section (shown/hidden based on checkbox)
        self.auto_fruit_section = ctk.CTkFrame(precast_frame, fg_color="transparent")
        if self.auto_store_fruit:
            self.auto_fruit_section.pack(fill="x", pady=5, padx=20)
        
        # Fruit hotkey row
        fruit_hotkey_row = ctk.CTkFrame(self.auto_fruit_section, fg_color="transparent")
        fruit_hotkey_row.pack(fill="x", pady=5)
        ctk.CTkLabel(fruit_hotkey_row, text="🍎 Fruit Hotkey", font=("Arial", 11, "bold"), width=120, anchor="w").pack(side="left")
        self.fruit_hotkey_var = tk.StringVar(value=self.fruit_hotkey)
        fruit_hotkey_combo = ctk.CTkComboBox(
            fruit_hotkey_row,
            variable=self.fruit_hotkey_var,
            values=[str(i) for i in range(1, 11)],
            width=80,
            state="readonly",
            fg_color=self.button_color,
            button_color=self.accent_color,
            button_hover_color=self.hover_color,
            command=lambda e: self.save_item_hotkeys()
        )
        fruit_hotkey_combo.pack(side="left", padx=8)
        
        # Fruit Point row
        fruit_point_row = ctk.CTkFrame(self.auto_fruit_section, fg_color="transparent")
        fruit_point_row.pack(fill="x", pady=5)
        ctk.CTkLabel(fruit_point_row, text="🍎 Fruit Point", font=("Arial", 11, "bold"), width=120, anchor="w").pack(side="left")
        self.fruit_point_btn = ctk.CTkButton(
            fruit_point_row,
            text="Select",
            command=self.start_fruit_point_selection,
            width=100,
            fg_color=self.button_color,
            hover_color=self.hover_color
        )
        self.fruit_point_btn.pack(side="left", padx=5)
        self.fruit_point_label = ctk.CTkLabel(fruit_point_row, text="None", font=("Arial", 10), text_color="#ffaa00")
        self.fruit_point_label.pack(side="left", padx=5)
        if self.fruit_point and self.fruit_color:
            color_hex = f"#{self.fruit_color[2]:02x}{self.fruit_color[1]:02x}{self.fruit_color[0]:02x}"
            self.fruit_point_label.configure(text=f"({self.fruit_point['x']}, {self.fruit_point['y']}) {color_hex}", text_color="#00dd00")
        
        # New: Checkbox "Não dropar, guardar no inventário"
        self.store_in_inventory_var = tk.BooleanVar(value=self.store_in_inventory)
        self.store_in_inventory_checkbox = ctk.CTkCheckBox(
            self.auto_fruit_section,
            text="Don't drop, save in inventory",
            variable=self.store_in_inventory_var,
            command=self.toggle_store_in_inventory,
            fg_color=self.success_color,
            hover_color=self.hover_color,
            font=("Segoe UI", 11)
        )
        self.store_in_inventory_checkbox.pack(fill="x", pady=5, padx=5)
        
        # Inventory Fruit Point section (shown/hidden based on checkbox)
        self.inventory_fruit_section = ctk.CTkFrame(self.auto_fruit_section, fg_color="transparent")
        if self.store_in_inventory:
            self.inventory_fruit_section.pack(fill="x", pady=5, padx=10)
            
        # Merged Row: Inventory Fruit Point & Center Point
        inventory_points_row = ctk.CTkFrame(self.inventory_fruit_section, fg_color="transparent")
        inventory_points_row.pack(fill="x", pady=5)
        
        # Left side: Inventory Fruit Point
        left_frame = ctk.CTkFrame(inventory_points_row, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True)
        
        ctk.CTkLabel(left_frame, text="📦 Inv. Slot", font=("Arial", 11, "bold"), width=80, anchor="w").pack(side="left")
        self.inventory_fruit_point_btn = ctk.CTkButton(
            left_frame,
            text="Select",
            command=self.start_inventory_fruit_point_selection,
            width=60,
            fg_color=self.button_color,
            hover_color=self.hover_color
        )
        self.inventory_fruit_point_btn.pack(side="left", padx=5)
        self.inventory_fruit_point_label = ctk.CTkLabel(left_frame, text="None", font=("Arial", 10), text_color="#ffaa00")
        self.inventory_fruit_point_label.pack(side="left", padx=5)
        
        # Right side: Center Point
        right_frame = ctk.CTkFrame(inventory_points_row, fg_color="transparent")
        right_frame.pack(side="left", fill="both", expand=True)
        
        ctk.CTkLabel(right_frame, text="🎯 Center", font=("Arial", 11, "bold"), width=80, anchor="w").pack(side="left")
        self.inventory_center_point_btn = ctk.CTkButton(
            right_frame,
            text="Select",
            command=self.start_inventory_center_point_selection,
            width=60,
            fg_color=self.button_color,
            hover_color=self.hover_color
        )
        self.inventory_center_point_btn.pack(side="left", padx=5)
        self.inventory_center_point_label = ctk.CTkLabel(right_frame, text="Default", font=("Arial", 10), text_color="#ffaa00")
        self.inventory_center_point_label.pack(side="left", padx=5)
        
        # Update labels if points exist
        if self.inventory_fruit_point:
            self.inventory_fruit_point_label.configure(text=f"({self.inventory_fruit_point['x']}, {self.inventory_fruit_point['y']})", text_color="#00dd00")
        if self.inventory_center_point:
            self.inventory_center_point_label.configure(text=f"({self.inventory_center_point['x']}, {self.inventory_center_point['y']})", text_color="#00dd00")
        
        # Auto Select Top Bait checkbox
        self.auto_select_top_bait_var = tk.BooleanVar(value=self.auto_select_top_bait)
        self.auto_top_bait_checkbox = ctk.CTkCheckBox(
            precast_frame,
            text="Auto Select Top Bait",
            variable=self.auto_select_top_bait_var,
            command=self.toggle_auto_select_top_bait,
            fg_color=self.success_color,
            hover_color=self.hover_color,
            font=("Segoe UI", 11)
        )
        self.auto_top_bait_checkbox.pack(fill="x", pady=5, padx=15)
        
        # Auto Select Top Bait section (shown/hidden based on checkbox)
        self.auto_top_bait_section = ctk.CTkFrame(precast_frame, fg_color="transparent")
        if self.auto_select_top_bait:
            self.auto_top_bait_section.pack(fill="x", pady=5, padx=20)
        
        # Top Bait Point row
        top_bait_point_row = ctk.CTkFrame(self.auto_top_bait_section, fg_color="transparent")
        top_bait_point_row.pack(fill="x", pady=5)
        ctk.CTkLabel(top_bait_point_row, text="🎯 Bait Point", font=("Arial", 11, "bold"), width=120, anchor="w").pack(side="left")
        self.top_bait_point_btn = ctk.CTkButton(
            top_bait_point_row,
            text="Select",
            command=self.start_top_bait_point_selection,
            width=100,
            fg_color=self.button_color,
            hover_color=self.hover_color
        )
        self.top_bait_point_btn.pack(side="left", padx=5)
        self.top_bait_point_label = ctk.CTkLabel(top_bait_point_row, text="None", font=("Arial", 10), text_color="#ffaa00")
        self.top_bait_point_label.pack(side="left", padx=5)
        if self.top_bait_point:
            self.top_bait_point_label.configure(text=f"({self.top_bait_point['x']}, {self.top_bait_point['y']})", text_color="#00dd00")

        
        # Casting section
        casting_frame = ctk.CTkFrame(settings_tab, fg_color="#2b2b2b", corner_radius=10)
        casting_frame.pack(fill="x", pady=10)
        
        casting_title = ctk.CTkLabel(
            casting_frame,
            text="🎯 CASTING SETTINGS",
            font=("Arial", 14, "bold"),
            text_color=self.accent_color
        )
        casting_title.pack(pady=(10, 15))
        
        # Water point row
        water_point_row = ctk.CTkFrame(casting_frame, fg_color="transparent")
        water_point_row.pack(fill="x", pady=10, padx=15)
        
        ctk.CTkLabel(water_point_row, text="🌊 Water Point", font=("Arial", 11, "bold"), width=150, anchor="w").pack(side="left")
        self.water_point_button = ctk.CTkButton(
            water_point_row,
            text="Select",
            command=self.start_water_point_selection,
            width=120,
            fg_color=self.button_color,
            hover_color=self.hover_color
        )
        self.water_point_button.pack(side="left", padx=5)
        self.water_point_label = ctk.CTkLabel(water_point_row, text="None", font=("Arial", 10), text_color="#ffaa00")
        self.water_point_label.pack(side="left", padx=5)
        
        # Update label if water point exists
        if self.water_point:
            self.water_point_label.configure(text=f"({self.water_point['x']}, {self.water_point['y']})", text_color="#00dd00")
        
        # Cast hold duration row
        cast_hold_row = ctk.CTkFrame(casting_frame, fg_color="transparent")
        cast_hold_row.pack(fill="x", pady=5, padx=15)
        ctk.CTkLabel(cast_hold_row, text="Cast hold duration (s):", font=("Arial", 11), width=150, anchor="w").pack(side="left")
        cast_hold_container, self.cast_hold_entry = self.create_spinbox_entry(
            cast_hold_row, self.cast_hold_duration, min_val=0.1, max_val=5.0, step=0.1, width=120
        )
        cast_hold_container.pack(side="left", padx=5)
        
        # Recast timeout row
        recast_timeout_row = ctk.CTkFrame(casting_frame, fg_color="transparent")
        recast_timeout_row.pack(fill="x", pady=5, padx=15)
        ctk.CTkLabel(recast_timeout_row, text="Recast timeout (s):", font=("Arial", 11), width=150, anchor="w").pack(side="left")
        recast_timeout_container, self.recast_timeout_entry = self.create_spinbox_entry(
            recast_timeout_row, self.recast_timeout, min_val=1.0, max_val=30.0, step=0.5, width=120
        )
        recast_timeout_container.pack(side="left", padx=5)
        
        # Save button for casting settings
        save_casting_btn_row = ctk.CTkFrame(casting_frame, fg_color="transparent")
        save_casting_btn_row.pack(fill="x", pady=(10, 15), padx=15)
        ctk.CTkButton(
            save_casting_btn_row,
            text="💾 Save Casting Settings",
            command=self.save_casting_from_ui,
            width=200,
            fg_color=self.accent_color,
            hover_color=self.hover_color,
            font=("Arial", 12, "bold")
        ).pack()
        
        # ========== FISHING TAB ==========
        # Fishing End Delay section
        fishing_delay_frame = ctk.CTkFrame(fishing_tab, fg_color="#2b2b2b", corner_radius=10)
        fishing_delay_frame.pack(fill="x", pady=10)
        
        fishing_delay_title = ctk.CTkLabel(
            fishing_delay_frame,
            text="⏱️ FISHING END DELAY",
            font=("Arial", 14, "bold"),
            text_color=self.accent_color
        )
        fishing_delay_title.pack(pady=(10, 10))
        
        delay_row = ctk.CTkFrame(fishing_delay_frame, fg_color="transparent")
        delay_row.pack(fill="x", pady=5, padx=15)
        ctk.CTkLabel(delay_row, text="End delay (s):", font=("Arial", 11), width=150, anchor="w").pack(side="left")
        delay_container, self.fishing_end_delay_entry = self.create_spinbox_entry(
            delay_row, self.fishing_end_delay, min_val=0.0, max_val=5.0, step=0.1, width=120
        )
        delay_container.pack(side="left", padx=5)
        
        ctk.CTkLabel(
            fishing_delay_frame,
            text="Delay before ending fishing phase",
            font=("Arial", 9),
            text_color="#aaaaaa"
        ).pack(pady=(5, 5))
        
        # V3: Save button for fishing end delay
        save_fishing_delay_btn = ctk.CTkButton(
            fishing_delay_frame,
            text="Save End Delay",
            command=self.save_fishing_end_delay_from_ui,
            width=150,
            fg_color=self.accent_color,
            hover_color=self.hover_color,
            font=("Arial", 11, "bold")
        )
        save_fishing_delay_btn.pack(pady=(5, 15))
        
        # PID Controller section
        pid_frame = ctk.CTkFrame(fishing_tab, fg_color="#2b2b2b", corner_radius=10)
        pid_frame.pack(fill="x", pady=10)
        
        pid_title = ctk.CTkLabel(
            pid_frame,
            text="🎮 PD CONTROLLER",
            font=("Arial", 14, "bold"),
            text_color=self.accent_color
        )
        pid_title.pack(pady=(10, 10))
        
        # Kp (Proportional gain)
        kp_row = ctk.CTkFrame(pid_frame, fg_color="transparent")
        kp_row.pack(fill="x", pady=5, padx=15)
        ctk.CTkLabel(kp_row, text="Kp (Proportional):", font=("Arial", 11), width=150, anchor="w").pack(side="left")
        kp_container, self.kp_entry = self.create_spinbox_entry(
            kp_row, self.pid_kp, min_val=0.0, max_val=10.0, step=0.1, width=120
        )
        kp_container.pack(side="left", padx=5)
        
        # Kd (Derivative gain)
        kd_row = ctk.CTkFrame(pid_frame, fg_color="transparent")
        kd_row.pack(fill="x", pady=5, padx=15)
        ctk.CTkLabel(kd_row, text="Kd (Derivative):", font=("Arial", 11), width=150, anchor="w").pack(side="left")
        kd_container, self.kd_entry = self.create_spinbox_entry(
            kd_row, self.pid_kd, min_val=0.0, max_val=5.0, step=0.05, width=120
        )
        kd_container.pack(side="left", padx=5)
        
        # Clamp (Output limit)
        clamp_row = ctk.CTkFrame(pid_frame, fg_color="transparent")
        clamp_row.pack(fill="x", pady=5, padx=15)
        ctk.CTkLabel(clamp_row, text="PD Clamp (Limit):", font=("Arial", 11), width=150, anchor="w").pack(side="left")
        clamp_container, self.clamp_entry = self.create_spinbox_entry(
            clamp_row, self.pid_clamp, min_val=1, max_val=100, step=5, is_float=False, width=120
        )
        clamp_container.pack(side="left", padx=5)
        
        # Save button
        save_btn_row = ctk.CTkFrame(pid_frame, fg_color="transparent")
        save_btn_row.pack(fill="x", pady=10, padx=15)
        ctk.CTkButton(
            save_btn_row,
            text="💾 Save PD Settings",
            command=self.save_pid_from_ui,
            width=200,
            fg_color=self.accent_color,
            hover_color=self.hover_color,
            font=("Arial", 12, "bold")
        ).pack()
        
        # Info label for PID
        ctk.CTkLabel(
            pid_frame,
            text="Default: Kp=1.0, Kd=0.3, Clamp=1.0",
            font=("Arial", 9),
            text_color="#aaaaaa"
        ).pack(pady=(5, 15))
        
        # ========== AUTO CRAFT TAB ==========
        # Auto Craft Enable Checkbox
        auto_craft_enable_frame = ctk.CTkFrame(auto_craft_tab, fg_color="#2b2b2b", corner_radius=10)
        auto_craft_enable_frame.pack(fill="x", pady=10)
        
        auto_craft_title = ctk.CTkLabel(
            auto_craft_enable_frame,
            text="⚒️ AUTO CRAFT SETTINGS",
            font=("Arial", 14, "bold"),
            text_color=self.accent_color
        )
        auto_craft_title.pack(pady=(10, 10))
        
        self.auto_craft_enabled_var = tk.BooleanVar(value=self.auto_craft_enabled)
        self.auto_craft_checkbox = ctk.CTkCheckBox(
            auto_craft_enable_frame,
            text="Enable Auto Craft",
            variable=self.auto_craft_enabled_var,
            command=self.toggle_auto_craft,
            font=("Arial", 12, "bold"),
            fg_color=self.accent_color,
            hover_color=self.hover_color
        )
        self.auto_craft_checkbox.pack(pady=15, padx=15)
        
        # Warning about mutual exclusion
        ctk.CTkLabel(
            auto_craft_enable_frame,
            text="⚠️ Note: Auto Craft and Auto Buy Bait cannot be enabled together!",
            font=("Arial", 10, "bold"),
            text_color="#ff9900"
        ).pack(pady=(0, 15), padx=15)
        
        # Auto Craft Area Selector
        auto_craft_area_frame = ctk.CTkFrame(auto_craft_tab, fg_color="#2b2b2b", corner_radius=10)
        auto_craft_area_frame.pack(fill="x", pady=10)
        
        auto_craft_area_title = ctk.CTkLabel(
            auto_craft_area_frame,
            text="🎯 MINIGAME AREA SELECTOR",
            font=("Arial", 14, "bold"),
            text_color=self.accent_color
        )
        auto_craft_area_title.pack(pady=(10, 10))
        
        auto_craft_area_row = ctk.CTkFrame(auto_craft_area_frame, fg_color="transparent")
        auto_craft_area_row.pack(fill="x", pady=10, padx=15)
        
        ctk.CTkLabel(auto_craft_area_row, text="⚒️ Auto Craft Area", font=("Arial", 11, "bold"), width=150, anchor="w").pack(side="left")
        self.auto_craft_area_button = ctk.CTkButton(
            auto_craft_area_row,
            text="OFF",
            command=self.toggle_auto_craft_area,
            width=100,
            fg_color="#666666",
            hover_color="#888888",
            font=("Arial", 12, "bold")
        )
        self.auto_craft_area_button.pack(side="left", padx=8)
        
        # Auto Craft Water Point row
        auto_craft_water_point_row = ctk.CTkFrame(auto_craft_area_frame, fg_color="transparent")
        auto_craft_water_point_row.pack(fill="x", pady=10, padx=15)
        
        ctk.CTkLabel(auto_craft_water_point_row, text="🌊 Water Point", font=("Arial", 11, "bold"), width=150, anchor="w").pack(side="left")
        self.auto_craft_water_point_button = ctk.CTkButton(
            auto_craft_water_point_row,
            text="Select",
            command=self.start_auto_craft_water_point_selection,
            width=120,
            fg_color=self.button_color,
            hover_color=self.hover_color
        )
        self.auto_craft_water_point_button.pack(side="left", padx=5)
        self.auto_craft_water_point_label = ctk.CTkLabel(auto_craft_water_point_row, text="None", font=("Arial", 10), text_color="#ffaa00")
        self.auto_craft_water_point_label.pack(side="left", padx=5)
        
        # Update label if water point exists
        if self.auto_craft_water_point:
            self.auto_craft_water_point_label.configure(text=f"({self.auto_craft_water_point['x']}, {self.auto_craft_water_point['y']})", text_color="#00dd00")
        
        ctk.CTkLabel(
            auto_craft_area_frame,
            text="Note: Configure the minigame area and water point for auto craft.",
            font=("Arial", 10),
            text_color="#aaaaaa"
        ).pack(pady=(5, 15), padx=15)
        
        # Craft Settings Frame
        craft_settings_frame = ctk.CTkFrame(auto_craft_tab, fg_color="#2b2b2b", corner_radius=10)
        craft_settings_frame.pack(fill="x", pady=10)
        
        craft_settings_title = ctk.CTkLabel(
            craft_settings_frame,
            text="⚙️ CRAFT CONFIGURATION",
            font=("Arial", 14, "bold"),
            text_color=self.accent_color
        )
        craft_settings_title.pack(pady=(10, 10))
        
        # Craft Every N Fish
        craft_every_row = ctk.CTkFrame(craft_settings_frame, fg_color="transparent")
        craft_every_row.pack(fill="x", pady=5, padx=15)
        ctk.CTkLabel(craft_every_row, text="Craft Every X Fish:", font=("Arial", 11), width=180, anchor="w").pack(side="left")
        craft_every_container, self.craft_every_n_fish_entry = self.create_spinbox_entry(
            craft_every_row, self.craft_every_n_fish, min_val=1, max_val=100, step=1, is_float=False, width=120
        )
        craft_every_container.pack(side="left", padx=5)
        
        # Menu Delay
        menu_delay_row = ctk.CTkFrame(craft_settings_frame, fg_color="transparent")
        menu_delay_row.pack(fill="x", pady=5, padx=15)
        ctk.CTkLabel(menu_delay_row, text="Menu Delay (s):", font=("Arial", 11), width=180, anchor="w").pack(side="left")
        menu_delay_container, self.craft_menu_delay_entry = self.create_spinbox_entry(
            menu_delay_row, self.craft_menu_delay, min_val=0.1, max_val=5.0, step=0.1, width=120
        )
        menu_delay_container.pack(side="left", padx=5)
        
        # Click Speed
        click_speed_row = ctk.CTkFrame(craft_settings_frame, fg_color="transparent")
        click_speed_row.pack(fill="x", pady=5, padx=15)
        ctk.CTkLabel(click_speed_row, text="Click Speed (s):", font=("Arial", 11), width=180, anchor="w").pack(side="left")
        click_speed_container, self.craft_click_speed_entry = self.create_spinbox_entry(
            click_speed_row, self.craft_click_speed, min_val=0.01, max_val=2.0, step=0.01, width=120
        )
        click_speed_container.pack(side="left", padx=5)
        
        # Legendary Quantity
        legendary_qty_row = ctk.CTkFrame(craft_settings_frame, fg_color="transparent")
        legendary_qty_row.pack(fill="x", pady=5, padx=15)
        ctk.CTkLabel(legendary_qty_row, text="🟡 Legendary Quantity:", font=("Arial", 11, "bold"), width=180, anchor="w").pack(side="left")
        legendary_container, self.craft_legendary_quantity_entry = self.create_spinbox_entry(
            legendary_qty_row, self.craft_legendary_quantity, min_val=0, max_val=200, step=5, is_float=False, width=120
        )
        legendary_container.pack(side="left", padx=5)
        
        # Rare Quantity
        rare_qty_row = ctk.CTkFrame(craft_settings_frame, fg_color="transparent")
        rare_qty_row.pack(fill="x", pady=5, padx=15)
        ctk.CTkLabel(rare_qty_row, text="🔵 Rare Quantity:", font=("Arial", 11, "bold"), width=180, anchor="w").pack(side="left")
        rare_container, self.craft_rare_quantity_entry = self.create_spinbox_entry(
            rare_qty_row, self.craft_rare_quantity, min_val=0, max_val=200, step=5, is_float=False, width=120
        )
        rare_container.pack(side="left", padx=5)
        
        # Common Quantity
        common_qty_row = ctk.CTkFrame(craft_settings_frame, fg_color="transparent")
        common_qty_row.pack(fill="x", pady=5, padx=15)
        ctk.CTkLabel(common_qty_row, text="⚪ Common Quantity:", font=("Arial", 11, "bold"), width=180, anchor="w").pack(side="left")
        common_container, self.craft_common_quantity_entry = self.create_spinbox_entry(
            common_qty_row, self.craft_common_quantity, min_val=0, max_val=200, step=5, is_float=False, width=120
        )
        common_container.pack(side="left", padx=5)
        
        # Save Button
        save_craft_settings_btn = ctk.CTkButton(
            craft_settings_frame,
            text="💾 Save Craft Settings",
            command=self.save_craft_settings_from_ui,
            fg_color=self.accent_color,
            hover_color=self.hover_color,
            font=("Arial", 12, "bold")
        )
        save_craft_settings_btn.pack(pady=15)
        
        # Coordinates Frame
        craft_coords_frame = ctk.CTkFrame(auto_craft_tab, fg_color="#2b2b2b", corner_radius=10)
        craft_coords_frame.pack(fill="x", pady=10)
        
        craft_coords_title = ctk.CTkLabel(
            craft_coords_frame,
            text="📍 CRAFT COORDINATES",
            font=("Arial", 14, "bold"),
            text_color=self.accent_color
        )
        craft_coords_title.pack(pady=(10, 10))
        
        # Helper function to create coordinate rows
        def create_coord_row(parent, label_text, coord_name):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=5, padx=15)
            
            ctk.CTkLabel(row, text=label_text, font=("Arial", 11), width=180, anchor="w").pack(side="left")
            
            btn = ctk.CTkButton(
                row,
                text="Set Position",
                command=lambda: self.start_auto_craft_coord_selection(coord_name),
                width=120,
                fg_color=self.button_color,
                hover_color=self.hover_color
            )
            btn.pack(side="left", padx=5)
            
            # Get current coordinate value
            coord_value = getattr(self, coord_name, None)
            if coord_value:
                label_text_val = f"X: {coord_value['x']}, Y: {coord_value['y']}"
                label_color = "#00dd00"
            else:
                label_text_val = "Not Set"
                label_color = "#ff4444"
            
            label = ctk.CTkLabel(row, text=label_text_val, font=("Arial", 10), text_color=label_color)
            label.pack(side="left", padx=5)
            
            return btn, label
        
        # Create all coordinate rows
        self.craft_button_btn, self.craft_button_label = create_coord_row(craft_coords_frame, "🎯 Craft Button:", "craft_button_coords")
        self.plus_button_btn, self.plus_button_label = create_coord_row(craft_coords_frame, "➕ Plus Button:", "plus_button_coords")
        self.fish_icon_btn, self.fish_icon_label = create_coord_row(craft_coords_frame, "🐟 Fish Icon:", "fish_icon_coords")
        self.legendary_bait_btn, self.legendary_bait_label = create_coord_row(craft_coords_frame, "🟡 Legendary Bait:", "legendary_bait_coords")
        self.rare_bait_btn, self.rare_bait_label = create_coord_row(craft_coords_frame, "🔵 Rare Bait:", "rare_bait_coords")
        self.common_bait_btn, self.common_bait_label = create_coord_row(craft_coords_frame, "⚪ Common Bait:", "common_bait_coords")
        
        ctk.CTkLabel(
            craft_coords_frame,
            text="Click 'Set Position' then right-click on the target location in-game.",
            font=("Arial", 10),
            text_color="#aaaaaa"
        ).pack(pady=(5, 15), padx=15)
        

        
        # ========== WEBHOOKS TAB ==========
        # Load webhook settings
        webhook_settings = self.load_webhook_settings()
        
        # Discord Webhook URL row
        webhook_url_frame = ctk.CTkFrame(webhooks_tab, fg_color="#2b2b2b", corner_radius=10)
        webhook_url_frame.pack(fill="x", pady=10)
        
        webhook_title = ctk.CTkLabel(
            webhook_url_frame,
            text="🔔 DISCORD WEBHOOK",
            font=("Arial", 14, "bold"),
            text_color=self.accent_color
        )
        webhook_title.pack(pady=(10, 10))
        
        ctk.CTkLabel(webhook_url_frame, text="Webhook URL:", font=("Arial", 11, "bold")).pack(fill="x", pady=5, padx=15)
        self.webhook_url_entry = ctk.CTkEntry(
            webhook_url_frame,
            width=500,
            fg_color=self.button_color,
            border_color=self.accent_color
        )
        self.webhook_url_entry.insert(0, webhook_settings.get('webhook_url', ''))
        self.webhook_url_entry.pack(fill="x", pady=(5, 15), padx=15)
        
        # User ID row
        user_id_frame = ctk.CTkFrame(webhooks_tab, fg_color="#2b2b2b", corner_radius=10)
        user_id_frame.pack(fill="x", pady=10)
        
        user_id_title = ctk.CTkLabel(
            user_id_frame,
            text="👤 USER ID",
            font=("Arial", 14, "bold"),
            text_color=self.accent_color
        )
        user_id_title.pack(pady=(10, 10))
        
        ctk.CTkLabel(user_id_frame, text="Discord User ID:", font=("Arial", 11, "bold")).pack(fill="x", pady=5, padx=15)
        self.user_id_entry = ctk.CTkEntry(
            user_id_frame,
            width=300,
            fg_color=self.button_color,
            border_color=self.accent_color
        )
        self.user_id_entry.insert(0, webhook_settings.get('user_id', ''))
        self.user_id_entry.pack(fill="x", pady=(5, 15), padx=15)
        
        # Buttons frame
        buttons_frame = ctk.CTkFrame(webhooks_tab, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=15)
        
        ctk.CTkButton(
            buttons_frame,
            text="🧪 Test Webhook",
            command=self.test_webhook,
            width=180,
            fg_color="#00aaff",
            hover_color="#0088cc",
            font=("Arial", 12, "bold")
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            buttons_frame,
            text="💾 Save Webhook Settings",
            command=self.save_webhook_settings_ui,
            width=200,
            fg_color=self.accent_color,
            hover_color=self.hover_color,
            font=("Arial", 12, "bold")
        ).pack(side="left", padx=5)
        
        # ========== ADVANCED SETTINGS TAB ==========
        # Warning label
        warning_frame = ctk.CTkFrame(advanced_tab, fg_color="transparent")
        warning_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(
            warning_frame,
            text="⚠️ WARNING: Advanced Settings ⚠️",
            font=("Arial", 12, "bold"),
            text_color="#ff4444"
        ).pack()
        ctk.CTkLabel(
            warning_frame,
            text="Only modify if you know what you're doing! Incorrect values may cause malfunction.",
            font=("Arial", 9),
            text_color="#ffaa00"
        ).pack(pady=5)
        
        # Checkbox to disable rotation/zoom/camera in normal mode
        disable_camera_frame = ctk.CTkFrame(advanced_tab, fg_color="#2b2b2b", corner_radius=10)
        disable_camera_frame.pack(fill="x", pady=8)
        
        disable_camera_title = ctk.CTkLabel(
            disable_camera_frame,
            text="🎮 NORMAL MODE - CAMERA",
            font=("Arial", 13, "bold"),
            text_color=self.accent_color
        )
        disable_camera_title.pack(pady=(10, 5))
        
        disable_normal_camera_row = ctk.CTkFrame(disable_camera_frame, fg_color="transparent")
        disable_normal_camera_row.pack(fill="x", pady=(5, 10), padx=15)
        self.disable_normal_camera_var = ctk.BooleanVar(value=self.disable_normal_camera)
        disable_normal_camera_checkbox = ctk.CTkCheckBox(
            disable_normal_camera_row,
            text="Disable rotation/zoom/camera in normal mode",
            variable=self.disable_normal_camera_var,
            command=self.save_disable_normal_camera,
            fg_color=self.accent_color,
            hover_color=self.hover_color,
            font=("Arial", 11)
        )
        disable_normal_camera_checkbox.pack(side="left")
        ctk.CTkLabel(
            disable_normal_camera_row, 
            text="(Does not affect Auto Craft)", 
            font=("Arial", 9), 
            text_color="#00ccff"
        ).pack(side="left", padx=8)
        
        ctk.CTkLabel(
            disable_camera_frame,
            text="When enabled: Disables 180° rotation, zoom in/out and camera initialization in normal mode.",
            font=("Arial", 9),
            text_color="#aaaaaa"
        ).pack(pady=(0, 10), padx=15)
        
        # Camera Rotation Settings
        camera_frame = ctk.CTkFrame(advanced_tab, fg_color="#2b2b2b", corner_radius=10)
        camera_frame.pack(fill="x", pady=8)
        
        camera_title = ctk.CTkLabel(
            camera_frame,
            text="📷 CAMERA ROTATION DELAYS",
            font=("Arial", 13, "bold"),
            text_color=self.accent_color
        )
        camera_title.pack(pady=(10, 10))
        
        # Camera rotation delay
        cam_delay_row = ctk.CTkFrame(camera_frame, fg_color="transparent")
        cam_delay_row.pack(fill="x", pady=4, padx=15)
        ctk.CTkLabel(cam_delay_row, text="Initial delay before rotation (s):", font=("Arial", 10), width=280, anchor="w").pack(side="left")
        cam_delay_container, self.camera_rotation_delay_entry = self.create_spinbox_entry(
            cam_delay_row, self.camera_rotation_delay, min_val=0.0, max_val=2.0, step=0.05, width=80
        )
        cam_delay_container.pack(side="left", padx=5)
        ctk.CTkLabel(cam_delay_row, text="Default: 0.05", font=("Arial", 9), text_color="#00ccff").pack(side="left", padx=5)
        
        # Camera rotation steps
        cam_steps_row = ctk.CTkFrame(camera_frame, fg_color="transparent")
        cam_steps_row.pack(fill="x", pady=4, padx=15)
        ctk.CTkLabel(cam_steps_row, text="Number of rotation steps:", font=("Arial", 10), width=280, anchor="w").pack(side="left")
        cam_steps_container, self.camera_rotation_steps_entry = self.create_spinbox_entry(
            cam_steps_row, self.camera_rotation_steps, min_val=1, max_val=20, step=1, is_float=False, width=80
        )
        cam_steps_container.pack(side="left", padx=5)
        ctk.CTkLabel(cam_steps_row, text="Default: 8 (8x100px = 800px total)", font=("Arial", 9), text_color="#00ccff").pack(side="left", padx=5)
        
        # Camera rotation step delay
        cam_step_delay_row = ctk.CTkFrame(camera_frame, fg_color="transparent")
        cam_step_delay_row.pack(fill="x", pady=4, padx=15)
        ctk.CTkLabel(cam_step_delay_row, text="Delay between each step (s):", font=("Arial", 10), width=280, anchor="w").pack(side="left")
        cam_step_delay_container, self.camera_rotation_step_delay_entry = self.create_spinbox_entry(
            cam_step_delay_row, self.camera_rotation_step_delay, min_val=0.0, max_val=1.0, step=0.01, width=80
        )
        cam_step_delay_container.pack(side="left", padx=5)
        ctk.CTkLabel(cam_step_delay_row, text="Default: 0.05", font=("Arial", 9), text_color="#00ccff").pack(side="left", padx=5)
        
        # Camera rotation settle delay
        cam_settle_row = ctk.CTkFrame(camera_frame, fg_color="transparent")
        cam_settle_row.pack(fill="x", pady=(4, 15), padx=15)
        ctk.CTkLabel(cam_settle_row, text="Delay after completing rotation (s):", font=("Arial", 10), width=280, anchor="w").pack(side="left")
        cam_settle_container, self.camera_rotation_settle_delay_entry = self.create_spinbox_entry(
            cam_settle_row, self.camera_rotation_settle_delay, min_val=0.0, max_val=2.0, step=0.05, width=80
        )
        cam_settle_container.pack(side="left", padx=5)
        ctk.CTkLabel(cam_settle_row, text="Default: 0.3", font=("Arial", 9), text_color="#00ccff").pack(side="left", padx=5)
        
        # Zoom Settings
        zoom_frame = ctk.CTkFrame(advanced_tab, fg_color="#2b2b2b", corner_radius=10)
        zoom_frame.pack(fill="x", pady=8)
        
        zoom_title = ctk.CTkLabel(
            zoom_frame,
            text="🔍 ZOOM DELAYS",
            font=("Arial", 13, "bold"),
            text_color=self.accent_color
        )
        zoom_title.pack(pady=(10, 10))
        
        # Zoom ticks
        zoom_ticks_row = ctk.CTkFrame(zoom_frame, fg_color="transparent")
        zoom_ticks_row.pack(fill="x", pady=4, padx=15)
        ctk.CTkLabel(zoom_ticks_row, text="Number of zoom ticks:", font=("Arial", 10), width=280, anchor="w").pack(side="left")
        zoom_ticks_container, self.zoom_ticks_entry = self.create_spinbox_entry(
            zoom_ticks_row, self.zoom_ticks, min_val=1, max_val=20, step=1, is_float=False, width=80
        )
        zoom_ticks_container.pack(side="left", padx=5)
        ctk.CTkLabel(zoom_ticks_row, text="Default: 3", font=("Arial", 9), text_color="#00ccff").pack(side="left", padx=5)
        
        # Zoom tick delay
        zoom_tick_delay_row = ctk.CTkFrame(zoom_frame, fg_color="transparent")
        zoom_tick_delay_row.pack(fill="x", pady=4, padx=15)
        ctk.CTkLabel(zoom_tick_delay_row, text="Delay between each zoom tick (s):", font=("Arial", 10), width=280, anchor="w").pack(side="left")
        zoom_tick_delay_container, self.zoom_tick_delay_entry = self.create_spinbox_entry(
            zoom_tick_delay_row, self.zoom_tick_delay, min_val=0.0, max_val=0.5, step=0.01, width=80
        )
        zoom_tick_delay_container.pack(side="left", padx=5)
        ctk.CTkLabel(zoom_tick_delay_row, text="Default: 0.05", font=("Arial", 9), text_color="#00ccff").pack(side="left", padx=5)
        
        # Zoom settle delay
        zoom_settle_row = ctk.CTkFrame(zoom_frame, fg_color="transparent")
        zoom_settle_row.pack(fill="x", pady=(4, 15), padx=15)
        ctk.CTkLabel(zoom_settle_row, text="Delay after completing zoom (s):", font=("Arial", 10), width=280, anchor="w").pack(side="left")
        self.zoom_settle_delay_entry = ctk.CTkEntry(zoom_settle_row, width=80, fg_color=self.button_color, border_color=self.accent_color)
        self.zoom_settle_delay_entry.insert(0, str(self.zoom_settle_delay))
        self.zoom_settle_delay_entry.pack(side="left", padx=5)
        ctk.CTkLabel(zoom_settle_row, text="Default: 0.3", font=("Arial", 9), text_color="#00ccff").pack(side="left", padx=5)
        
        # Pre-Cast Delays
        precast_delays_frame = ctk.CTkFrame(advanced_tab, fg_color="#2b2b2b", corner_radius=10)
        precast_delays_frame.pack(fill="x", pady=8)
        
        precast_title = ctk.CTkLabel(
            precast_delays_frame,
            text="🎣 PRE-CAST ACTION DELAYS",
            font=("Arial", 13, "bold"),
            text_color=self.accent_color
        )
        precast_title.pack(pady=(10, 10))
        
        # Minigame wait
        minigame_wait_row = ctk.CTkFrame(precast_delays_frame, fg_color="transparent")
        minigame_wait_row.pack(fill="x", pady=4, padx=15)
        ctk.CTkLabel(minigame_wait_row, text="Wait for minigame to appear (s):", font=("Arial", 10), width=280, anchor="w").pack(side="left")
        self.pre_cast_minigame_wait_entry = ctk.CTkEntry(minigame_wait_row, width=80, fg_color=self.button_color, border_color=self.accent_color)
        self.pre_cast_minigame_wait_entry.insert(0, str(self.pre_cast_minigame_wait))
        self.pre_cast_minigame_wait_entry.pack(side="left", padx=5)
        ctk.CTkLabel(minigame_wait_row, text="Default: 2.5 (prevents premature detection)", font=("Arial", 9), text_color="#00ccff").pack(side="left", padx=5)
        
        # Store click delay
        store_delay_row = ctk.CTkFrame(precast_delays_frame, fg_color="transparent")
        store_delay_row.pack(fill="x", pady=4, padx=15)
        ctk.CTkLabel(store_delay_row, text="Delay after clicking store (s):", font=("Arial", 10), width=280, anchor="w").pack(side="left")
        self.store_click_delay_entry = ctk.CTkEntry(store_delay_row, width=80, fg_color=self.button_color, border_color=self.accent_color)
        self.store_click_delay_entry.insert(0, str(self.store_click_delay))
        self.store_click_delay_entry.pack(side="left", padx=5)
        ctk.CTkLabel(store_delay_row, text="Default: 1.0", font=("Arial", 9), text_color="#00ccff").pack(side="left", padx=5)
        
        # Backspace delay
        backspace_delay_row = ctk.CTkFrame(precast_delays_frame, fg_color="transparent")
        backspace_delay_row.pack(fill="x", pady=4, padx=15)
        ctk.CTkLabel(backspace_delay_row, text="Delay after pressing backspace (s):", font=("Arial", 10), width=280, anchor="w").pack(side="left")
        self.backspace_delay_entry = ctk.CTkEntry(backspace_delay_row, width=80, fg_color=self.button_color, border_color=self.accent_color)
        self.backspace_delay_entry.insert(0, str(self.backspace_delay))
        self.backspace_delay_entry.pack(side="left", padx=5)
        ctk.CTkLabel(backspace_delay_row, text="Default: 0.3", font=("Arial", 9), text_color="#00ccff").pack(side="left", padx=5)
        
        # Rod deselect delay
        rod_deselect_row = ctk.CTkFrame(precast_delays_frame, fg_color="transparent")
        rod_deselect_row.pack(fill="x", pady=4, padx=15)
        ctk.CTkLabel(rod_deselect_row, text="Delay after deselecting rod (s):", font=("Arial", 10), width=280, anchor="w").pack(side="left")
        self.rod_deselect_delay_entry = ctk.CTkEntry(rod_deselect_row, width=80, fg_color=self.button_color, border_color=self.accent_color)
        self.rod_deselect_delay_entry.insert(0, str(self.rod_deselect_delay))
        self.rod_deselect_delay_entry.pack(side="left", padx=5)
        ctk.CTkLabel(rod_deselect_row, text="Default: 0.5", font=("Arial", 9), text_color="#00ccff").pack(side="left", padx=5)
        
        # Rod select delay
        rod_select_row = ctk.CTkFrame(precast_delays_frame, fg_color="transparent")
        rod_select_row.pack(fill="x", pady=4, padx=15)
        ctk.CTkLabel(rod_select_row, text="Delay after selecting rod (s):", font=("Arial", 10), width=280, anchor="w").pack(side="left")
        self.rod_select_delay_entry = ctk.CTkEntry(rod_select_row, width=80, fg_color=self.button_color, border_color=self.accent_color)
        self.rod_select_delay_entry.insert(0, str(self.rod_select_delay))
        self.rod_select_delay_entry.pack(side="left", padx=5)
        ctk.CTkLabel(rod_select_row, text="Default: 0.5", font=("Arial", 9), text_color="#00ccff").pack(side="left", padx=5)
        
        # Bait click delay
        bait_delay_row = ctk.CTkFrame(precast_delays_frame, fg_color="transparent")
        bait_delay_row.pack(fill="x", pady=(4, 15), padx=15)
        ctk.CTkLabel(bait_delay_row, text="Delay after clicking bait (s):", font=("Arial", 10), width=280, anchor="w").pack(side="left")
        self.bait_click_delay_entry = ctk.CTkEntry(bait_delay_row, width=80, fg_color=self.button_color, border_color=self.accent_color)
        self.bait_click_delay_entry.insert(0, str(self.bait_click_delay))
        self.bait_click_delay_entry.pack(side="left", padx=5)
        ctk.CTkLabel(bait_delay_row, text="Default: 0.3", font=("Arial", 9), text_color="#00ccff").pack(side="left", padx=5)
        
        # Detection & General Delays
        detection_frame = ctk.CTkFrame(advanced_tab, fg_color="#2b2b2b", corner_radius=10)
        detection_frame.pack(fill="x", pady=8)
        
        detection_title = ctk.CTkLabel(
            detection_frame,
            text="🔎 DETECTION & GENERAL DELAYS",
            font=("Arial", 13, "bold"),
            text_color=self.accent_color
        )
        detection_title.pack(pady=(10, 10))
        
        # Fruit detection delay
        fruit_det_delay_row = ctk.CTkFrame(detection_frame, fg_color="transparent")
        fruit_det_delay_row.pack(fill="x", pady=4, padx=15)
        ctk.CTkLabel(fruit_det_delay_row, text="Delay during fruit detection (s):", font=("Arial", 10), width=280, anchor="w").pack(side="left")
        self.fruit_detection_delay_entry = ctk.CTkEntry(fruit_det_delay_row, width=80, fg_color=self.button_color, border_color=self.accent_color)
        self.fruit_detection_delay_entry.insert(0, str(self.fruit_detection_delay))
        self.fruit_detection_delay_entry.pack(side="left", padx=5)
        ctk.CTkLabel(fruit_det_delay_row, text="Default: 0.02", font=("Arial", 9), text_color="#00ccff").pack(side="left", padx=5)
        
        # Fruit detection settle
        fruit_settle_row = ctk.CTkFrame(detection_frame, fg_color="transparent")
        fruit_settle_row.pack(fill="x", pady=4, padx=15)
        ctk.CTkLabel(fruit_settle_row, text="Delay after fruit detection (s):", font=("Arial", 10), width=280, anchor="w").pack(side="left")
        self.fruit_detection_settle_entry = ctk.CTkEntry(fruit_settle_row, width=80, fg_color=self.button_color, border_color=self.accent_color)
        self.fruit_detection_settle_entry.insert(0, str(self.fruit_detection_settle))
        self.fruit_detection_settle_entry.pack(side="left", padx=5)
        ctk.CTkLabel(fruit_settle_row, text="Default: 0.3", font=("Arial", 9), text_color="#00ccff").pack(side="left", padx=5)
        
        # General action delay
        general_delay_row = ctk.CTkFrame(detection_frame, fg_color="transparent")
        general_delay_row.pack(fill="x", pady=4, padx=15)
        ctk.CTkLabel(general_delay_row, text="General delay between actions (s):", font=("Arial", 10), width=280, anchor="w").pack(side="left")
        self.general_action_delay_entry = ctk.CTkEntry(general_delay_row, width=80, fg_color=self.button_color, border_color=self.accent_color)
        self.general_action_delay_entry.insert(0, str(self.general_action_delay))
        self.general_action_delay_entry.pack(side="left", padx=5)
        ctk.CTkLabel(general_delay_row, text="Default: 0.05", font=("Arial", 9), text_color="#00ccff").pack(side="left", padx=5)
        
        # Mouse move settle
        mouse_settle_row = ctk.CTkFrame(detection_frame, fg_color="transparent")
        mouse_settle_row.pack(fill="x", pady=4, padx=15)
        ctk.CTkLabel(mouse_settle_row, text="Delay after moving mouse (s):", font=("Arial", 10), width=280, anchor="w").pack(side="left")
        self.mouse_move_settle_entry = ctk.CTkEntry(mouse_settle_row, width=80, fg_color=self.button_color, border_color=self.accent_color)
        self.mouse_move_settle_entry.insert(0, str(self.mouse_move_settle))
        self.mouse_move_settle_entry.pack(side="left", padx=5)
        ctk.CTkLabel(mouse_settle_row, text="Default: 0.05", font=("Arial", 9), text_color="#00ccff").pack(side="left", padx=5)

        # Focus settle delay after focusing Roblox
        focus_settle_row = ctk.CTkFrame(detection_frame, fg_color="transparent")
        focus_settle_row.pack(fill="x", pady=(4, 15), padx=15)
        ctk.CTkLabel(focus_settle_row, text="Delay after focusing Roblox (s):", font=("Arial", 10), width=280, anchor="w").pack(side="left")
        self.focus_settle_delay_entry = ctk.CTkEntry(focus_settle_row, width=80, fg_color=self.button_color, border_color=self.accent_color)
        self.focus_settle_delay_entry.insert(0, str(self.focus_settle_delay))
        self.focus_settle_delay_entry.pack(side="left", padx=5)
        ctk.CTkLabel(focus_settle_row, text="Default: 1.0", font=("Arial", 9), text_color="#00ccff").pack(side="left", padx=5)
        
        # Save button for advanced settings
        save_advanced_row = ctk.CTkFrame(advanced_tab, fg_color="transparent")
        save_advanced_row.pack(fill="x", pady=15)
        ctk.CTkButton(
            save_advanced_row,
            text="💾 Save Advanced Settings",
            command=self.save_advanced_settings,
            width=250,
            fg_color=self.accent_color,
            hover_color=self.hover_color,
            font=("Arial", 12, "bold")
        ).pack()
        ctk.CTkButton(
            save_advanced_row,
            text="🔄 Reset to Default",
            command=self.reset_advanced_settings,
            width=250,
            fg_color="#ff8800",
            hover_color="#ffaa00",
            font=("Arial", 12, "bold")
        ).pack(pady=5)
        
        # ========== STATS TAB ==========
        # Today section
        today_frame = ctk.CTkFrame(stats_tab, fg_color=self.button_color, corner_radius=8)
        today_frame.pack(fill="x", pady=8, padx=5)
        
        ctk.CTkLabel(
            today_frame,
            text="Today",
            font=("Segoe UI", 12, "bold"),
            text_color=self.fg_color
        ).pack(anchor="w", padx=12, pady=(10, 6))
        
        # Today stats grid
        today_stats = ctk.CTkFrame(today_frame, fg_color="transparent")
        today_stats.pack(fill="x", padx=12, pady=(0, 12))
        
        for i in range(4):
            today_stats.grid_columnconfigure(i, weight=1)
        
        # Labels for today stats
        self.today_sessions_label = ctk.CTkLabel(today_stats, text="0", font=("Segoe UI", 16, "bold"))
        self.today_sessions_label.grid(row=0, column=0, padx=5)
        ctk.CTkLabel(today_stats, text="Sessions", font=("Segoe UI", 9), text_color=self.fg_color).grid(row=1, column=0)
        
        self.today_fish_label = ctk.CTkLabel(today_stats, text="0", font=("Segoe UI", 16, "bold"))
        self.today_fish_label.grid(row=0, column=1, padx=5)
        ctk.CTkLabel(today_stats, text="Fish", font=("Segoe UI", 9), text_color=self.fg_color).grid(row=1, column=1)
        
        self.today_fruits_label = ctk.CTkLabel(today_stats, text="0", font=("Segoe UI", 16, "bold"))
        self.today_fruits_label.grid(row=0, column=2, padx=5)
        ctk.CTkLabel(today_stats, text="Fruits", font=("Segoe UI", 9), text_color=self.fg_color).grid(row=1, column=2)
        
        self.today_rate_label = ctk.CTkLabel(today_stats, text="0/h", font=("Segoe UI", 16, "bold"))
        self.today_rate_label.grid(row=0, column=3, padx=5)
        ctk.CTkLabel(today_stats, text="Rate", font=("Segoe UI", 9), text_color=self.fg_color).grid(row=1, column=3)
        
        # V3.1: Estimated time to next fruit section
        estimate_frame = ctk.CTkFrame(stats_tab, fg_color=self.button_color, corner_radius=8)
        estimate_frame.pack(fill="x", pady=8, padx=5)
        
        ctk.CTkLabel(
            estimate_frame,
            text="⏱️ Estimated Time to Next Fruit",
            font=("Segoe UI", 12, "bold"),
            text_color=self.fg_color
        ).pack(anchor="w", padx=12, pady=(10, 6))
        
        self.estimate_label = ctk.CTkLabel(
            estimate_frame,
            text="Calculating...",
            font=("Segoe UI", 14, "bold"),
            text_color="#00ccff"
        )
        self.estimate_label.pack(anchor="w", padx=12, pady=(0, 10))
        
        self.estimate_detail_label = ctk.CTkLabel(
            estimate_frame,
            text="Start fishing to collect data",
            font=("Segoe UI", 9),
            text_color="#aaaaaa"
        )
        self.estimate_detail_label.pack(anchor="w", padx=12, pady=(0, 10))
        
        # History section
        history_frame = ctk.CTkFrame(stats_tab, fg_color=self.button_color, corner_radius=8)
        history_frame.pack(fill="both", expand=True, pady=8, padx=5)
        
        ctk.CTkLabel(
            history_frame,
            text="Last 7 Days",
            font=("Segoe UI", 12, "bold"),
            text_color=self.fg_color
        ).pack(anchor="w", padx=12, pady=(10, 6))
        
        # History table header
        history_header = ctk.CTkFrame(history_frame, fg_color="transparent")
        history_header.pack(fill="x", padx=12)
        ctk.CTkLabel(history_header, text="Date", width=100, anchor="w", font=("Segoe UI", 10, "bold")).pack(side="left")
        ctk.CTkLabel(history_header, text="Fish", width=60, font=("Segoe UI", 10, "bold")).pack(side="left")
        ctk.CTkLabel(history_header, text="Fruits", width=60, font=("Segoe UI", 10, "bold")).pack(side="left")
        
        # History rows container
        self.history_container = ctk.CTkFrame(history_frame, fg_color="transparent")
        self.history_container.pack(fill="both", expand=True, padx=12, pady=(4, 12))
        
        # Export button
        export_frame = ctk.CTkFrame(stats_tab, fg_color="transparent")
        export_frame.pack(fill="x", pady=8, padx=5)
        
        ctk.CTkButton(
            export_frame,
            text="Export CSV",
            command=self.export_stats_csv,
            width=100,
            fg_color=self.button_color,
            hover_color=self.hover_color
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            export_frame,
            text="Refresh",
            command=self.refresh_stats_display,
            width=80,
            fg_color=self.button_color,
            hover_color=self.hover_color
        ).pack(side="left", padx=5)
        
        # V3.1: Export/Import Config buttons
        config_frame = ctk.CTkFrame(stats_tab, fg_color="transparent")
        config_frame.pack(fill="x", pady=8, padx=5)
        
        ctk.CTkLabel(
            config_frame,
            text="⚙️ Configuration:",
            font=("Segoe UI", 10, "bold"),
            text_color=self.fg_color
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            config_frame,
            text="📤 Export Config",
            command=self.export_config,
            width=120,
            fg_color="#00aa88",
            hover_color="#00cc99"
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            config_frame,
            text="📥 Import Config",
            command=self.import_config,
            width=120,
            fg_color="#aa8800",
            hover_color="#cc9900"
        ).pack(side="left", padx=5)
        
        # Initial load of stats
        self.refresh_stats_display()
        
        # Setup tooltips for all widgets
        self.setup_tooltips()
    
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
        if hasattr(self, 'always_on_top_var'):
            for widget in self.scrollable_frame.winfo_children():
                self._add_tooltips_recursive(widget, {
                    'Always on Top': 'Keep this window above all other windows',
                })
        
        # Start/Stop button
        if hasattr(self, 'start_button'):
            add_tooltip(self.start_button, 
                'Start or stop the fishing macro.\nHotkey: F1 (default)')
        
        # Area button
        if hasattr(self, 'area_button'):
            add_tooltip(self.area_button, 
                'Select the fishing minigame detection area.\nDrag to draw a rectangle around the fishing bar.\nHotkey: F2 (default)')
        
        # Exit button
        if hasattr(self, 'exit_button'):
            add_tooltip(self.exit_button, 
                'Emergency exit - stops the macro and closes the application.\nHotkey: F3 (default)')
        
        # ===== SETTINGS TAB =====
        # Auto Buy Bait checkbox
        if hasattr(self, 'auto_bait_checkbox'):
            add_tooltip(self.auto_bait_checkbox, 
                'Automatically purchase bait from the shop.\nRequires button positions to be configured.\nCannot be used with Auto Craft mode.')
        
        # Auto Store Fruit checkbox
        if hasattr(self, 'auto_fruit_checkbox'):
            add_tooltip(self.auto_fruit_checkbox, 
                'Automatically store caught Devil Fruits in your inventory.\nRotates camera and zooms in to detect fruits.\nTakes a screenshot when a fruit is detected.')
        
        # Sound notification checkbox
        if hasattr(self, 'sound_enabled_var'):
            # Find the sound checkbox widget
            pass  # Added via config text
        
        # Yes/Middle/No buttons
        if hasattr(self, 'yes_button_btn'):
            add_tooltip(self.yes_button_btn, 
                'Click to select the YES button position in the bait shop dialog')
        
        if hasattr(self, 'middle_button_btn'):
            add_tooltip(self.middle_button_btn, 
                'Click to select the MIDDLE button position in the bait shop dialog')
        
        if hasattr(self, 'no_button_btn'):
            add_tooltip(self.no_button_btn, 
                'Click to select the NO button position in the bait shop dialog')
        
        # Loops entry
        if hasattr(self, 'loops_entry'):
            add_tooltip(self.loops_entry, 
                'Number of fishing loops before buying more bait.\nHigher = less interruption, but may run out of bait.')
        
        # Fruit point button
        if hasattr(self, 'fruit_point_btn'):
            add_tooltip(self.fruit_point_btn, 
                'Click to select a point on your character where the fruit appears.\nUsed to detect if you caught a Devil Fruit.')
        
        # Top bait checkbox/button
        if hasattr(self, 'auto_top_bait_checkbox'):
            add_tooltip(self.auto_top_bait_checkbox, 
                'Automatically select the top bait in your inventory before casting.')
        
        if hasattr(self, 'top_bait_btn'):
            add_tooltip(self.top_bait_btn, 
                'Click to select the position of the top bait in your bait menu.')
        
        # Disable camera checkbox
        if hasattr(self, 'disable_normal_camera_checkbox'):
            add_tooltip(self.disable_normal_camera_checkbox, 
                'Disable camera rotation and zoom in normal mode.\nUse this if you already have the camera positioned correctly.')
        
        # ===== FISHING TAB =====
        # Cast duration
        if hasattr(self, 'cast_duration_entry'):
            add_tooltip(self.cast_duration_entry, 
                'How long to hold the cast button (in seconds).\nLonger = further cast distance.')
        
        # Recast timeout
        if hasattr(self, 'recast_timeout_entry'):
            add_tooltip(self.recast_timeout_entry, 
                'Maximum time to wait for a fish (in seconds).\nAfter this time, the macro will recast automatically.')
        
        # Fishing end delay
        if hasattr(self, 'fishing_end_delay_entry'):
            add_tooltip(self.fishing_end_delay_entry, 
                'Delay after catching a fish before next action (in seconds).\nHelps prevent detection issues.')
        
        # Water point button
        if hasattr(self, 'water_point_btn'):
            add_tooltip(self.water_point_btn, 
                'Click to select where to cast your fishing rod.\nChoose a point in the water.')
        
        # ===== AUTO CRAFT TAB =====
        if hasattr(self, 'auto_craft_checkbox'):
            add_tooltip(self.auto_craft_checkbox, 
                'Enable Auto Craft mode.\nAutomatically crafts bait after catching fish.\nCannot be used with Auto Buy Bait.')
        
        if hasattr(self, 'craft_every_entry'):
            add_tooltip(self.craft_every_entry, 
                'Number of fish to catch before crafting bait.\nLower = more frequent crafting.')
        
        # Craft button positions
        if hasattr(self, 'craft_button_btn'):
            add_tooltip(self.craft_button_btn, 
                'Click to select the CRAFT button position in the crafting menu.')
        
        if hasattr(self, 'plus_button_btn'):
            add_tooltip(self.plus_button_btn, 
                'Click to select the PLUS (+) button to increase quantity.')
        
        if hasattr(self, 'fish_icon_btn'):
            add_tooltip(self.fish_icon_btn, 
                'Click to select the fish icon in the crafting menu.')
        
        # Bait coords
        if hasattr(self, 'legendary_bait_btn'):
            add_tooltip(self.legendary_bait_btn, 
                'Click to select the Legendary Bait position in crafting menu.')
        
        if hasattr(self, 'rare_bait_btn'):
            add_tooltip(self.rare_bait_btn, 
                'Click to select the Rare Bait position in crafting menu.')
        
        if hasattr(self, 'common_bait_btn'):
            add_tooltip(self.common_bait_btn, 
                'Click to select the Common Bait position in crafting menu.')
        
        # ===== WEBHOOKS TAB =====
        if hasattr(self, 'webhook_url_entry'):
            add_tooltip(self.webhook_url_entry, 
                'Discord webhook URL for notifications.\nGet this from your Discord server settings > Integrations > Webhooks.')
        
        if hasattr(self, 'user_id_entry'):
            add_tooltip(self.user_id_entry, 
                'Your Discord user ID for mentions.\nEnable Developer Mode in Discord, right-click your name, Copy ID.')
        
        if hasattr(self, 'test_webhook_btn'):
            add_tooltip(self.test_webhook_btn, 
                'Send a test message to verify your webhook is working.')
        
        # ===== ADVANCED TAB =====
        # PID settings
        if hasattr(self, 'kp_entry'):
            add_tooltip(self.kp_entry, 
                'Proportional gain for mouse movement.\nHigher = faster but may overshoot.')
        
        if hasattr(self, 'kd_entry'):
            add_tooltip(self.kd_entry, 
                'Derivative gain for damping.\nHigher = smoother but slower.')
        
        if hasattr(self, 'clamp_entry'):
            add_tooltip(self.clamp_entry, 
                'Maximum mouse movement speed limit.\nLower = more precise but slower.')
        
        # ===== STATS TAB =====
        if hasattr(self, 'export_csv_btn'):
            add_tooltip(self.export_csv_btn, 
                'Export all fishing sessions to a CSV file for analysis.')
        
        if hasattr(self, 'reset_stats_btn'):
            add_tooltip(self.reset_stats_btn, 
                'Clear all saved statistics. This cannot be undone!')
    
    def _add_tooltips_recursive(self, widget, tooltip_map):
        """Recursively find widgets by text and add tooltips"""
        try:
            # Check if widget has cget method for text
            if hasattr(widget, 'cget'):
                try:
                    text = widget.cget('text')
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
        if key_type == 'start':
            self.start_hotkey_label.configure(text="[WAITING...]", text_color="#ff4444")
        elif key_type == 'area':
            self.area_hotkey_label.configure(text="[WAITING...]", text_color="#ff4444")
        elif key_type == 'exit':
            self.exit_hotkey_label.configure(text="[WAITING...]", text_color="#ff4444")
        
        self.info_label.configure(text=f"Press a key to bind {key_type}...", text_color="#ffaa00")
        
    def on_press(self, key):
        """Handle key press for hotkey binding and execution"""
        try:
            # Handle rebinding
            if self.is_rebinding:
                try:
                    key_name = key.char.lower() if hasattr(key, 'char') else str(key).lower().replace('key.', '')
                except AttributeError:
                    key_name = str(key).lower().replace('key.', '')
                
                self.hotkeys[self.is_rebinding] = key_name
                
                # Update UI
                display_key = f"[{key_name.upper()}]"
                if self.is_rebinding == 'start':
                    self.start_hotkey_label.configure(text=display_key, text_color=self.accent_color)
                elif self.is_rebinding == 'area':
                    self.area_hotkey_label.configure(text=display_key, text_color=self.accent_color)
                elif self.is_rebinding == 'exit':
                    self.exit_hotkey_label.configure(text=display_key, text_color=self.accent_color)
                
                self.info_label.configure(text="✓ Key rebound successfully!", text_color="#00dd00")
                self.is_rebinding = None
                return
            
            # Handle hotkey execution
            try:
                key_name = key.char.lower() if hasattr(key, 'char') else str(key).lower().replace('key.', '')
            except AttributeError:
                key_name = str(key).lower().replace('key.', '')
            
            if key_name == self.hotkeys['start']:
                self.toggle_start()
            elif key_name == self.hotkeys['area']:
                self.toggle_area()
            elif key_name == self.hotkeys['exit']:
                self.force_exit()
                
        except Exception as e:
            pass
    
    def setup_hotkeys(self):
        """Setup global hotkey listener"""
        self.listener = Listener(on_press=self.on_press)
        self.listener.start()
    
    def toggle_start(self):
        """Toggle start/stop"""
        global stats_manager
        
        # Check if area selector is active
        if not self.running and self.area_active:
            self.info_label.configure(text="❌ Cannot start! Close Area Selector first!", text_color="#ff4444")
            return
        
        self.running = not self.running
        
        if self.running:
            self.status_label.configure(text="Status: ▶ RUNNING", text_color="#00dd00")
            self.start_button.configure(text="⏹ STOP")
            self.info_label.configure(text="✓ Macro started!", text_color="#00dd00")
            
            # Reset statistics
            self.start_time = time.time()
            self.fruits_caught = 0
            self.fish_caught = 0
            self.fish_at_last_fruit = 0
            self.last_craft_fish_count = -1  # Prevent infinite crafting loop if cast fails
            
            # V3: Start stats session
            if stats_manager is None:
                stats_manager = StatsManager()
            stats_manager.start_session()
            
            # Reset first_run flag to trigger camera initialization
            self.first_run = True
            # Reset first_catch to skip counting on first pre_cast
            self.first_catch = True
            
            # Minimize GUI window
            self.root.iconify()
            
            # Show HUD
            self.show_hud()
            
            # Start main loop thread
            self.main_thread = threading.Thread(target=self.main_loop, daemon=True)
            self.main_thread.start()
        else:
            self.status_label.configure(text="Status: STOPPED", text_color="#ff4444")
            self.start_button.configure(text="▶ START")
            self.info_label.configure(text="⏸ Macro stopped!", text_color="#ffaa00")
            self.running = False
            
            # V3 Stability: Guaranteed mouse release when stopping
            if self.mouse_pressed:
                try:
                    pyautogui.mouseUp()
                    self.mouse_pressed = False
                except:
                    pass
            
            # V3 Stability: End stats session to save data
            if stats_manager and stats_manager.session_id:
                try:
                    stats_manager.end_session()
                    # Refresh stats display to show latest session data
                    self.refresh_stats_display()
                except:
                    pass
            
            # Restore GUI window
            self.root.deiconify()
            
            # Hide HUD
            self.hide_hud()
    
    def toggle_area(self):
        """Toggle area active/inactive - opens Auto Craft area if Auto Craft is enabled, otherwise normal area"""
        # Check if main loop is running
        if self.running:
            self.info_label.configure(text="❌ Cannot open Area Selector! Stop macro first!", text_color="#ff4444")
            return
        
        # If Auto Craft is enabled, open Auto Craft area instead
        if self.auto_craft_enabled:
            self.toggle_auto_craft_area()
            return
        
        # Normal area logic
        self.area_active = not self.area_active
        
        if self.area_active:
            self.area_button.configure(text="✓ ON")
            self.info_label.configure(text="✓ Area selector activated!", text_color="#00dd00")
            self.show_area_selector()
        else:
            self.area_button.configure(text="✗ OFF")
            self.info_label.configure(text="✗ Area saved and closed!", text_color="#ffaa00")
            self.hide_area_selector()
    
    def toggle_auto_craft_area(self):
        """Toggle auto craft area selector active/inactive"""
        # Check if main loop is running
        if not self.auto_craft_area_active and self.running:
            self.info_label.configure(text="❌ Cannot open Auto Craft Area Selector! Stop macro first!", text_color="#ff4444")
            return
        
        self.auto_craft_area_active = not self.auto_craft_area_active
        
        if self.auto_craft_area_active:
            self.auto_craft_area_button.configure(text="✓ ON")
            self.info_label.configure(text="✓ Auto Craft area selector activated!", text_color="#00dd00")
            self.show_auto_craft_area_selector()
        else:
            self.auto_craft_area_button.configure(text="✗ OFF")
            self.info_label.configure(text="✗ Auto Craft area saved and closed!", text_color="#ffaa00")
            self.hide_auto_craft_area_selector()
    
    def toggle_auto_craft(self):
        """Toggle auto craft feature on/off"""
        # Check if trying to enable auto craft while auto buy bait is on
        if self.auto_craft_enabled_var.get() and self.auto_buy_bait:
            self.auto_craft_enabled_var.set(False)
            self.info_label.configure(text="❌ Cannot enable Auto Craft! Auto Buy Bait is active. Disable it first.", text_color="#ff4444")
            return
        
        self.auto_craft_enabled = self.auto_craft_enabled_var.get()
        self.save_auto_craft_settings()
        if self.auto_craft_enabled:
            self.info_label.configure(text="✓ Auto Craft enabled!", text_color="#00dd00")
        else:
            self.info_label.configure(text="✗ Auto Craft disabled!", text_color="#ffaa00")
    
    def main_loop(self):
        """Main fishing macro loop"""
        try:
            # Ensure mouse is released at start
            if self.mouse_pressed:
                win32api.mouse_event(0x0004, 0, 0)  # MOUSEEVENTF_LEFTUP
                self.mouse_pressed = False
            
            while self.running:
                if self.first_run:
                    # Focus Roblox window FIRST before any other operations
                    self.current_status = "Focusing window"
                    self.focus_roblox_window()
                    # Initialize keyboard controller
                    kb = Controller()
                    # Deselect any equipped item first
                    print("\rInitial setup: Deselecting items...", end='', flush=True)
                    kb.press(self.everything_else_hotkey)
                    kb.release(self.everything_else_hotkey)
                    if not self.interruptible_sleep(self.rod_deselect_delay):
                        return
                    # Select rod
                    print("\rInitial setup: Selecting rod...", end='', flush=True)
                    kb.press(self.rod_hotkey)
                    kb.release(self.rod_hotkey)
                    if not self.interruptible_sleep(self.rod_select_delay):
                        return
                    if not self.disable_normal_camera or self.auto_craft_enabled:
                        self.current_status = "Initializing camera"
                        print("\rInitial setup: Adjusting camera position (faster)...", end='', flush=True)
                        # Scroll in 30 ticks (first person guarantee) - FASTER
                        for _ in range(30):
                            win32api.mouse_event(0x0800, 0, 0, 120, 0)  # MOUSEEVENTF_WHEEL, scroll up
                            if not self.interruptible_sleep(0.01):  # Reduced from zoom_tick_delay
                                return
                        if not self.interruptible_sleep(0.1):  # Reduced from zoom_settle_delay
                            return
                        # Scroll out 13 ticks (standardize view) - FASTER
                        for _ in range(13):
                            win32api.mouse_event(0x0800, 0, 0, -120, 0)  # MOUSEEVENTF_WHEEL, scroll down
                            if not self.interruptible_sleep(0.01):  # Reduced from zoom_tick_delay
                                return
                        if not self.interruptible_sleep(self.rod_select_delay):
                            return
                        print("\r✓ Camera position set!", end='', flush=True)
                    else:
                        # Simplified initialization for when camera is disabled (User request)
                        # Ensures consistent starting camera state even if dynamic camera control is off
                        self.current_status = "Initializing camera (Simplified)"
                        print("\rInitial setup: Adjusting camera position (simplified)...", end='', flush=True)
                        
                        # Scroll in 30 ticks (first person guarantee)
                        for _ in range(30):
                            win32api.mouse_event(0x0800, 0, 0, 120, 0)  # MOUSEEVENTF_WHEEL, scroll up
                            if not self.interruptible_sleep(0.01):
                                return
                        if not self.interruptible_sleep(0.1):
                            return
                            
                        # Scroll out 5 ticks (specific setting for disabled camera mode)
                        for _ in range(5):
                            win32api.mouse_event(0x0800, 0, 0, -120, 0)  # MOUSEEVENTF_WHEEL, scroll down
                            if not self.interruptible_sleep(0.01):
                                return
                        if not self.interruptible_sleep(0.1):
                            return
                        print("\r✓ Camera position set (simplified)!", end='', flush=True)
                    self.first_run = False


                # Choose which mode to run based on auto_craft_enabled
                if self.auto_craft_enabled:
                    # ===== AUTO CRAFT MODE =====
                    # Auto Craft Pre-cast handles the entire cycle:
                    # 1. Craft baits (if needed)
                    # 2. Check for fruit
                    # 3. Cast rod
                    # 4. Rotate camera 90°
                    # 5. Wait for minigame (esperar)
                    # 6. Play minigame (pesca)
                    # 7. Rotate camera back 90°
                    # 8. Loop restarts
                    self.current_status = "Auto Craft Cycle"
                    cycle_success = self.auto_craft_pre_cast()
                    if not cycle_success:
                        continue  # Recast/restart cycle
                else:
                    # ===== NORMAL MODE =====
                    # Stage 1: Pre-cast
                    self.current_status = "Pre-casting"
                    pre_cast_success = self.pre_cast()
                    if not pre_cast_success:
                        continue  # Recast without camera restore
                    # Stage 2: Wait
                    self.current_status = "Scanning for fish"
                    wait_success = self.esperar()
                    if not wait_success:
                        continue  # Recast without camera restore
                    # Stage 3: Fish - Loop until blue is no longer detected
                    self.current_status = "Fishing (tracking bar)"
                    while self.running and self.pesca():
                        pass  # Keep fishing while pesca() returns True

                    # Count fish after fishing completes
                    # Auto craft mode counts fish internally, so only count for normal mode
                    if not self.auto_craft_enabled and self.running:
                        if not self.auto_store_fruit:
                            self.fish_caught += 1
                            if stats_manager: stats_manager.log_fish()
                            print(f"\r🐟 Fish caught! Total fish: {self.fish_caught}", end='', flush=True)

                    # Check for anti-macro after fishing ends (use correct area based on mode)
                    # Skip anti-macro check for auto_craft mode since it's handled internally
                    if not self.auto_craft_enabled:
                        print("\rChecking for anti-macro after fishing...", end='', flush=True)
                        screenshot = self.capture_area()
                        if screenshot is not None and self.check_anti_macro_black_screen(screenshot):
                            print(f"\r⚠️  Anti-macro detected after fishing! Handling...", end='', flush=True)
                            if not self.handle_anti_macro_detection():
                                break  # User stopped
                            # Anti-macro cleared - restart from beginning WITHOUT camera restore
                            continue  # Skip to next cycle

                    # Ensure mouse is released after fishing stage ends
                    if self.mouse_pressed:
                        win32api.mouse_event(0x0004, 0, 0)  # MOUSEEVENTF_LEFTUP
                        self.mouse_pressed = False

                    # Only restore camera if we completed the full fishing cycle successfully
                    # Skip camera restore for auto_craft mode since it's handled internally
                    # Also skip if disable_normal_camera is enabled
                    if self.running and not self.auto_craft_enabled and not self.disable_normal_camera:
                        self.current_status = "Restoring camera"
                        # Zoom out 3 ticks before rotating back
                        print("\rZooming out 3 ticks...", end='', flush=True)
                        for _ in range(3):
                            win32api.mouse_event(0x0800, 0, 0, -120, 0)  # MOUSEEVENTF_WHEEL, scroll down
                            if not self.interruptible_sleep(self.zoom_tick_delay):
                                return
                        if not self.interruptible_sleep(self.zoom_settle_delay):
                            return

                        # Rotate camera back to original position
                        print("\rRestoring camera position...", end='', flush=True)
                        # Hold right click
                        win32api.mouse_event(0x0008, 0, 0)  # MOUSEEVENTF_RIGHTDOWN
                        if not self.interruptible_sleep(self.camera_rotation_delay):
                            return
                        # Move mouse left to rotate back (slower movement)
                        for _ in range(self.camera_rotation_steps):
                            win32api.mouse_event(0x0001, -100, 0, 0, 0)  # MOUSEEVENTF_MOVE, move left 100 pixels
                            if not self.interruptible_sleep(self.camera_rotation_step_delay):
                                return
                        if not self.interruptible_sleep(self.camera_rotation_settle_delay):
                            return
                        # Release right click
                        win32api.mouse_event(0x0010, 0, 0)  # MOUSEEVENTF_RIGHTUP
                        if not self.interruptible_sleep(self.camera_rotation_settle_delay):
                            return

                    # Wait for fishing end delay before restarting cycle
                    if self.running:
                        print(f"\rFishing ended! Waiting {self.fishing_end_delay}s before next cast...", end='', flush=True)
                        if not self.interruptible_sleep(self.fishing_end_delay):
                            return


        except Exception as e:
            print(f"Error in main loop: {e}")
            # Release mouse on error
            if self.mouse_pressed:
                win32api.mouse_event(0x0004, 0, 0)  # MOUSEEVENTF_LEFTUP
                self.mouse_pressed = False
    
    def focus_roblox_window(self):
        """Focus the Roblox window"""
        try:
            # Find Roblox window
            hwnd = win32gui.FindWindow(None, "Roblox")
            if hwnd:
                win32gui.SetForegroundWindow(hwnd)
                # Wait a short time to ensure focus is stable
                self.interruptible_sleep(self.focus_settle_delay)
        except:
            pass  # Silently ignore if window not found
    
    def capture_center_screenshot(self, auto_craft_mode=False):
        """Capture screenshot of center area where character holds fruit"""
        try:
            with mss.mss() as sct:
                # Calculate center area (smaller for auto craft mode)
                if auto_craft_mode:
                    # Focused screenshot for auto craft with zoom (400x320 at 1920x1080)
                    # Larger area to capture character + fruit properly with 6 tick zoom
                    screenshot_width = int(400 * SCREEN_WIDTH / REF_WIDTH)
                    screenshot_height = int(320 * SCREEN_HEIGHT / REF_HEIGHT)
                else:
                    # Normal screenshot (800x500 at 1920x1080) - larger to capture full fruit
                    screenshot_width = int(800 * SCREEN_WIDTH / REF_WIDTH)
                    screenshot_height = int(500 * SCREEN_HEIGHT / REF_HEIGHT)
                center_x = SCREEN_WIDTH // 2
                center_y = SCREEN_HEIGHT // 2
                
                monitor = {
                    "top": center_y - screenshot_height // 2,
                    "left": center_x - screenshot_width // 2,
                    "width": screenshot_width,
                    "height": screenshot_height
                }
                
                # Capture screenshot
                screenshot = sct.grab(monitor)
                
                # Save to temporary file for webhook attachment
                fd, screenshot_path = tempfile.mkstemp(prefix="fruit_", suffix=".png")
                os.close(fd)  # Close the file descriptor; mss will write to the path
                
                # Apply brightness/contrast enhancement for auto craft mode
                if auto_craft_mode:
                    from PIL import Image, ImageEnhance
                    import io
                    
                    # Convert screenshot to PIL Image
                    img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
                    
                    # Increase brightness slightly (1.0 = original, 1.2 = 20% brighter)
                    enhancer = ImageEnhance.Brightness(img)
                    img = enhancer.enhance(1.25)
                    
                    # Increase contrast slightly (1.0 = original, 1.15 = 15% more contrast)
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(1.15)
                    
                    # Save enhanced image
                    img.save(screenshot_path, 'PNG')
                else:
                    # Normal mode - save without enhancement
                    mss.tools.to_png(screenshot.rgb, screenshot.size, output=screenshot_path)
                
                return screenshot_path
        except Exception as e:
            print(f"\rError capturing screenshot: {e}", end='', flush=True)
            return None
    
    def send_fruit_webhook(self, screenshot_path):
        """Send Discord webhook notification with fruit screenshot and statistics"""
        cleanup_path = screenshot_path
        try:
            import requests
            from datetime import datetime, timedelta
            
            webhook_url = self.webhook_url_entry.get().strip()
            user_id = self.user_id_entry.get().strip()
            
            if not webhook_url or not user_id:
                print(f"\rWebhook not configured, skipping notification...", end='', flush=True)
                return
            
            # Calculate runtime
            if self.start_time:
                runtime = time.time() - self.start_time
                hours = int(runtime // 3600)
                minutes = int((runtime % 3600) // 60)
                seconds = int(runtime % 60)
                runtime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                runtime_str = "00:00:00"
            
            # Create embed message
            embed = {
                "title": "🍎 DEVIL FRUIT CAUGHT! 🍎",
                "description": f"<@{user_id}> A devil fruit has been detected!",
                "color": 0xFF6B35,  # Orange color
                "fields": [
                    {"name": "⏱️ Runtime", "value": runtime_str, "inline": True},
                    {"name": "🍎 Fruits", "value": str(self.fruits_caught), "inline": True},
                    {"name": "🐟 Fish", "value": str(self.fish_caught), "inline": True}
                ],
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {"text": "BPS Fishing Macro"}
            }
            
            # Prepare multipart form data with screenshot
            with open(screenshot_path, 'rb') as f:
                files = {
                    'file': ('fruit.png', f, 'image/png')
                }
                data = {
                    'payload_json': json.dumps({
                        "content": f"<@{user_id}>",
                        "embeds": [embed]
                    })
                }
                
                response = requests.post(webhook_url, files=files, data=data)
                
            if response.status_code in [200, 204]:
                print(f"\r✅ Webhook notification sent!", end='', flush=True)
            else:
                print(f"\r⚠️ Webhook error: {response.status_code}", end='', flush=True)
                
        except ImportError:
            print(f"\r⚠️ requests library not installed!", end='', flush=True)
        except Exception as e:
            print(f"\rError sending webhook: {e}", end='', flush=True)
        finally:
            # Ensure temporary screenshot is removed after webhook attempt
            try:
                if cleanup_path and os.path.exists(cleanup_path):
                    os.remove(cleanup_path)
            except Exception:
                pass
    
    def simulate_click(self, x, y, hold_delay=0.05):
        """Simulate a click using the Anti-Roblox method: SetCursorPos + mouse_event(MOVE) + pyautogui"""
        try:
            x, y = int(x), int(y)
            ctypes.windll.user32.SetCursorPos(x, y)
            time.sleep(0.01)
            ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0)
            time.sleep(0.01)
            pyautogui.mouseDown()
            pyautogui.mouseUp()
            time.sleep(hold_delay)
        except Exception as e:
            print(f"Click Error: {e}")

    def simulate_drag(self, start_x, start_y, end_x, end_y):
        """Simulate a robust drag operation using Anti-Roblox method"""
        try:
            start_x, start_y = int(start_x), int(start_y)
            end_x, end_y = int(end_x), int(end_y)
            
            # Move to start
            ctypes.windll.user32.SetCursorPos(start_x, start_y)
            time.sleep(0.03)
            ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0) # Move 1px to register
            time.sleep(0.08)
            
            # Click down
            pyautogui.mouseDown()
            time.sleep(0.15)
            
            # Drag to end
            ctypes.windll.user32.SetCursorPos(end_x, end_y)
            time.sleep(0.03)
            ctypes.windll.user32.mouse_event(0x0001, 0, 1, 0, 0) # Move 1px to register
            time.sleep(0.25) # Wait for drag to register
            
            # Release
            pyautogui.mouseUp()
            time.sleep(0.08)
        except Exception as e:
            print(f"Drag Error: {e}")

    def pre_cast(self):
        """Stage 1: Pre-cast preparation - includes bait buying and fruit checking"""
        if not self.running:
            return False
        
        # Auto Buy Bait if enabled
        if self.auto_buy_bait:
            self.current_status = "Buying bait"
            if not self.buy_common_bait():
                return False
        
        # Deselect rod, select rod, select top bait, cast, check fruit
        try:
            kb = Controller()
            
            # Shift Lock Alignment (only when disable_normal_camera is enabled - like Auto Craft)
            if self.disable_normal_camera:
                print(f"\rPre-cast: Activating Shift Lock for alignment...", end='', flush=True)
                kb.press(Key.shift)
                kb.release(Key.shift)
                if not self.interruptible_sleep(0.2):
                    return False
                
                print(f"\rPre-cast: Deactivating Shift Lock...", end='', flush=True)
                kb.press(Key.shift)
                kb.release(Key.shift)
                if not self.interruptible_sleep(0.2):
                    return False
            
            # Steps 1-3: Deselect rod, select rod, select bait
            # Skip these if disable_normal_camera is enabled - will be done after fruit check
            if not self.disable_normal_camera:
                # 1. Deselect rod (press everything_else_hotkey)
                self.current_status = "Deselecting rod"
                print(f"\rPre-cast: Deselecting rod ({self.everything_else_hotkey})...", end='', flush=True)
                kb.press(self.everything_else_hotkey)
                kb.release(self.everything_else_hotkey)
                if not self.interruptible_sleep(self.rod_deselect_delay):
                    return False
                
                # 2. Select rod (press rod_hotkey)
                self.current_status = "Selecting rod"
                print(f"\rPre-cast: Selecting rod ({self.rod_hotkey})...", end='', flush=True)
                kb.press(self.rod_hotkey)
                kb.release(self.rod_hotkey)
                if not self.interruptible_sleep(self.rod_select_delay):
                    return False
                
                # 3. Auto Select Top Bait if enabled
                if self.auto_select_top_bait and self.top_bait_point:
                    self.current_status = "Selecting bait"
                    print(f"\rPre-cast: Selecting top bait at ({self.top_bait_point['x']}, {self.top_bait_point['y']})...", end='', flush=True)
                    self.simulate_click(self.top_bait_point['x'], self.top_bait_point['y'], hold_delay=0.1)
                    if not self.interruptible_sleep(self.bait_click_delay):
                        return False
            
            # 4. Cast to water point (ALIGNMENT CAST - skip if disable_normal_camera since shift lock replaces it)
            if not self.water_point:
                print("\rPre-cast: X No water point set!", end='', flush=True)
                if not self.interruptible_sleep(1):
                    return False
                return False
            
            # Only do alignment cast if camera mode is enabled (otherwise shift lock handles alignment)
            if not self.disable_normal_camera:
                self.current_status = "Casting rod"
                print(f"\rPre-cast: Casting to water point ({self.water_point['x']}, {self.water_point['y']})...", end='', flush=True)
                # Usar método anti-roblox para clicar e segurar
                self.simulate_click(self.water_point['x'], self.water_point['y'], hold_delay=self.cast_hold_duration)
                if not self.interruptible_sleep(self.mouse_move_settle):
                    return False
                
                # 5. Wait 0.5s (quick check, otimizado)
                print("\rPre-cast: Waiting 0.5s...", end='', flush=True)
                if not self.interruptible_sleep(0.5):
                    return False
            
            # 6-8. Auto Store Devil Fruit if enabled
            if self.auto_store_fruit:
                # 6a. Deselect rod before checking fruit
                print(f"\rPre-cast: Deselecting rod ({self.everything_else_hotkey}) before fruit check...", end='', flush=True)
                kb.press(self.everything_else_hotkey)
                kb.release(self.everything_else_hotkey)
                if not self.interruptible_sleep(0.2):
                    return False
                
                # 6b. Press fruit hotkey
                self.current_status = "Checking for fruit"
                print(f"\rPre-cast: Pressing fruit hotkey ({self.fruit_hotkey})...", end='', flush=True)
                kb.press(self.fruit_hotkey)
                kb.release(self.fruit_hotkey)
                
                # Espera mínima para garantir que o personagem segure a fruta (reduzido para configuravel)
                print(f"\rPre-cast: Waiting {self.fruit_hold_delay}s for character to hold fruit...", end='', flush=True)
                if not self.interruptible_sleep(self.fruit_hold_delay):
                    return False
                
                screenshot_path = None
                
                # 7. Check for fruit color at fruit_point (skip counting on first run)
                if self.fruit_point and self.fruit_color:
                    print(f"\rPre-cast: Checking for fruit at ({self.fruit_point['x']}, {self.fruit_point['y']})...", end='', flush=True)
                    try:
                        with mss.mss() as sct:
                            # Capture a 1x1 pixel area at fruit_point
                            monitor = {"top": self.fruit_point['y'], "left": self.fruit_point['x'], "width": 1, "height": 1}
                            screenshot = sct.grab(monitor)
                            # Get pixel color (BGRA format)
                            pixel = screenshot.pixel(0, 0)
                            current_color = (pixel[2], pixel[1], pixel[0])  # Convert to BGR
                            
                            # Compare colors (exact match or close tolerance)
                            color_match = (
                                abs(current_color[0] - self.fruit_color[0]) <= 5 and
                                abs(current_color[1] - self.fruit_color[1]) <= 5 and
                                abs(current_color[2] - self.fruit_color[2]) <= 5
                            )
                            
                            if color_match:
                                # ALWAYS increment fruit count before webhook (even on first catch)
                                # The webhook shows current stats, so we need to count first
                                if not self.first_catch:
                                    self.fruits_caught += 1
                                    self.fish_at_last_fruit = self.fish_caught
                                    self.daily_fruits += 1  # V3: Daily tracking
                                    if stats_manager: stats_manager.log_fruit()
                                    logger.info(f"FRUIT DETECTED! Total: {self.fruits_caught}")
                                else:
                                    self.fruits_caught += 1  # Still count for webhook display
                                    self.daily_fruits += 1  # V3: Daily tracking
                                    if stats_manager: stats_manager.log_fruit()
                                    logger.info(f"FRUIT DETECTED! Total: {self.fruits_caught} (First catch)")
                                    self.first_catch = False  # Next time won't show "first catch"
                                
                                # V3: Play sound notification
                                # V3: Play sound notification
                                if self.sound_enabled:
                                    try:
                                        threading.Thread(target=self.play_notification_sound, daemon=True).start()
                                    except:
                                        pass
                                
                                # Zoom in 3 ticks before screenshot for better visibility (only if camera enabled)
                                if not self.disable_normal_camera:
                                    print(f"\rPre-cast: Zooming in 3 ticks for screenshot...", end='', flush=True)
                                    for _ in range(3):
                                        win32api.mouse_event(0x0800, 0, 0, 120, 0)  # MOUSEEVENTF_WHEEL, scroll up
                                        if not self.interruptible_sleep(self.zoom_tick_delay):
                                            return False
                                    if not self.interruptible_sleep(self.zoom_settle_delay):
                                        return False
                                
                                # Small delay before screenshot
                                if not self.interruptible_sleep(0.2):
                                    return False
                                
                                # Take screenshot of center area where character holds fruit
                                print(f"\rPre-cast: Capturing screenshot...", end='', flush=True)
                                screenshot_path = self.capture_center_screenshot()
                                
                                # Small delay after screenshot
                                if not self.interruptible_sleep(0.2):
                                    return False
                                
                                # Zoom out 3 ticks after screenshot to restore view (only if camera enabled)
                                if not self.disable_normal_camera:
                                    print(f"\rPre-cast: Zooming out 3 ticks...", end='', flush=True)
                                    for _ in range(3):
                                        win32api.mouse_event(0x0800, 0, 0, -120, 0)  # MOUSEEVENTF_WHEEL, scroll down
                                        if not self.interruptible_sleep(self.zoom_tick_delay):
                                            return False
                                    if not self.interruptible_sleep(self.zoom_settle_delay):
                                        return False
                                
                                # Send webhook notification with screenshot
                                if screenshot_path:
                                    self.send_fruit_webhook(screenshot_path)
                            else:
                                # Count fish (only if not first catch to avoid counting before actually fishing)
                                if not self.first_catch:
                                    self.fish_caught += 1
                                    if stats_manager: stats_manager.log_fish()
                                    print(f"\r[FISH] Fish caught! Total fish: {self.fish_caught}", end='', flush=True)
                                else:
                                    # First catch - just set flag to False, don't count
                                    print(f"\r[FISH] First cycle - not counting", end='', flush=True)
                                    self.first_catch = False
                    except Exception as e:
                        print(f"\rWarning: Failed to check fruit color: {e}", end='', flush=True)
                        # Default to fish if detection fails - only count if not first catch
                        if not self.first_catch:
                            self.fish_caught += 1
                            if stats_manager: stats_manager.log_fish()
                        else:
                            self.first_catch = False
                else:
                    # No fruit detection configured, count as fish (only if not first catch)
                    if not self.first_catch:
                        self.fish_caught += 1
                        if stats_manager: stats_manager.log_fish()
                        print(f"\rFish caught (no fruit detection). Total fish: {self.fish_caught}", end='', flush=True)
                    else:
                        print(f"\rFirst cycle - not counting", end='', flush=True)
                        self.first_catch = False
                
                # 8. Store Fruit Logic
                if self.fruit_point:
                    print(f"\rPre-cast: Clicking fruit point to store...", end='', flush=True)
                    self.simulate_click(self.fruit_point['x'], self.fruit_point['y'], hold_delay=0.1)
                    if not self.interruptible_sleep(self.store_click_delay):
                        return False
                
                # 9. Handle fruit storage based on mode (Drop vs Inventory)
                if self.store_in_inventory and self.inventory_fruit_point:
                    # NEW: Store in inventory mode
                    print(f"\rPre-cast: Storing in inventory...", end='', flush=True)
                    
                    # 9a. Open inventory with `
                    kb.press('`')
                    kb.release('`')
                    if not self.interruptible_sleep(0.5):
                        return False
                    
                    # 9b & 9c. Click on fruit in inventory and drag to screen center
                    inv_x = self.inventory_fruit_point['x']
                    inv_y = self.inventory_fruit_point['y']
                    
                    if self.inventory_center_point:
                        center_x = self.inventory_center_point['x']
                        center_y = self.inventory_center_point['y']
                    else:
                        center_x = SCREEN_WIDTH // 2
                        center_y = SCREEN_HEIGHT // 2
                    
                    # Use robust drag simulation
                    print(f"\rPre-cast: Dragging from ({inv_x},{inv_y}) to ({center_x},{center_y})...", end='', flush=True)
                    self.simulate_drag(inv_x, inv_y, center_x, center_y)
                    
                    if not self.interruptible_sleep(0.2):
                         return False
                    if not self.interruptible_sleep(0.2):
                        return False
                    
                    # 9d. Close inventory
                    kb.press('`')
                    kb.release('`')
                    if not self.interruptible_sleep(0.5):
                        return False
                        
                else:
                    # ORIGINAL: Drop with backspace
                    # Only warn if enabled but no point set
                    if self.store_in_inventory and not self.inventory_fruit_point:
                        print(f"\rPre-cast: WARNING - Inventory store enabled but no point set! Dropping instead.", end='', flush=True)
                    
                    print(f"\rPre-cast: Pressing backspace to drop...", end='', flush=True)
                    kb.press(Key.backspace)
                    kb.release(Key.backspace)
                    if not self.interruptible_sleep(self.backspace_delay):
                        return False
                
                # 10. Deselect rod (press everything_else_hotkey)
                print(f"\rPre-cast: Deselecting rod ({self.everything_else_hotkey}) after fruit...", end='', flush=True)
                kb.press(self.everything_else_hotkey)
                kb.release(self.everything_else_hotkey)
                if not self.interruptible_sleep(self.rod_deselect_delay):
                    return False
                
                # 11. Select rod (press rod_hotkey)
                print(f"\rPre-cast: Selecting rod ({self.rod_hotkey}) after fruit...", end='', flush=True)
                kb.press(self.rod_hotkey)
                kb.release(self.rod_hotkey)
                if not self.interruptible_sleep(self.rod_select_delay):
                    return False
                
                # 12. Auto Select Top Bait if enabled
                if self.auto_select_top_bait and self.top_bait_point:
                    print(f"\rPre-cast: Selecting top bait again at ({self.top_bait_point['x']}, {self.top_bait_point['y']})...", end='', flush=True)
                    self.simulate_click(self.top_bait_point['x'], self.top_bait_point['y'], hold_delay=0.1)
                    if not self.interruptible_sleep(self.bait_click_delay):
                        return False
                
                # 13. Cast to water point again
                print(f"\rPre-cast: Casting to water point again ({self.water_point['x']}, {self.water_point['y']})...", end='', flush=True)
                
                # Manual cast sequence with pyautogui
                win32api.SetCursorPos((self.water_point['x'], self.water_point['y']))
                win32api.mouse_event(0x0001, 0, 1, 0, 0)  # MOUSEEVENTF_MOVE 1px down
                if not self.interruptible_sleep(self.mouse_move_settle):
                    return False
                win32api.mouse_event(0x0002, 0, 0)  # LEFTDOWN
                if not self.interruptible_sleep(self.cast_hold_duration):
                    win32api.mouse_event(0x0004, 0, 0)  # LEFTUP
                    return False
                win32api.mouse_event(0x0004, 0, 0)  # LEFTUP
                
                if not self.interruptible_sleep(self.bait_click_delay):
                    return False
                
                # 14-17. Camera/zoom/rotation steps (skip if disable_normal_camera is enabled)
                if not self.disable_normal_camera:
                    # 14. Wait a bit before rotation (let cast settle)
                    print("\rPre-cast: Waiting before camera rotation...", end='', flush=True)
                    if not self.interruptible_sleep(0.6):
                        return False
                    # 15. Rotate camera 180 degrees
                    print("\rPre-cast: Rotating camera 180°...", end='', flush=True)
                    # Hold right click
                    win32api.mouse_event(0x0008, 0, 0)  # MOUSEEVENTF_RIGHTDOWN
                    if not self.interruptible_sleep(self.camera_rotation_delay):
                        return False
                    # Move mouse right to rotate 180° (slower movement)
                    for _ in range(self.camera_rotation_steps):
                        win32api.mouse_event(0x0001, 100, 0, 0, 0)  # MOUSEEVENTF_MOVE, move right 100 pixels
                        if not self.interruptible_sleep(self.camera_rotation_step_delay):
                            return False
                    if not self.interruptible_sleep(self.camera_rotation_settle_delay):
                        return False
                    # Release right click
                    win32api.mouse_event(0x0010, 0, 0)  # MOUSEEVENTF_RIGHTUP
                    if not self.interruptible_sleep(self.camera_rotation_settle_delay):
                        return False
                    # 16. Zoom in 3 ticks after rotation
                    print("\rPre-cast: Zooming in 3 ticks...", end='', flush=True)
                    for _ in range(self.zoom_ticks):
                        win32api.mouse_event(0x0800, 0, 0, 120, 0)  # MOUSEEVENTF_WHEEL, scroll up
                        if not self.interruptible_sleep(self.zoom_tick_delay):
                            return False
                    if not self.interruptible_sleep(self.zoom_settle_delay):
                        return False
                    # 17. Wait for minigame to appear after rotation (prevent premature detection)
                    print("\rPre-cast: Waiting for minigame to appear...", end='', flush=True)
                    if not self.interruptible_sleep(self.pre_cast_minigame_wait):
                        return False
                else:
                    print("\rPre-cast: (Camera/zoom/rotation skipped by user setting)", end='', flush=True)
                    if not self.interruptible_sleep(self.pre_cast_minigame_wait):
                        return False
            else:
                # Auto Store Fruit disabled - fish will be counted after actual fishing completes
                # Need to do the full sequence: deselect rod, select rod, select bait, cast
                
                # When disable_normal_camera is enabled, we skipped these steps above, so do them now
                if self.disable_normal_camera:
                    # 1. Deselect rod (press everything_else_hotkey)
                    self.current_status = "Deselecting rod"
                    print(f"\rPre-cast: Deselecting rod ({self.everything_else_hotkey})...", end='', flush=True)
                    kb.press(self.everything_else_hotkey)
                    kb.release(self.everything_else_hotkey)
                    if not self.interruptible_sleep(self.rod_deselect_delay):
                        return False
                    
                    # 2. Select rod (press rod_hotkey)
                    self.current_status = "Selecting rod"
                    print(f"\rPre-cast: Selecting rod ({self.rod_hotkey})...", end='', flush=True)
                    kb.press(self.rod_hotkey)
                    kb.release(self.rod_hotkey)
                    if not self.interruptible_sleep(self.rod_select_delay):
                        return False
                    
                    # 3. Auto Select Top Bait if enabled
                    if self.auto_select_top_bait and self.top_bait_point:
                        self.current_status = "Selecting bait"
                        print(f"\rPre-cast: Selecting top bait at ({self.top_bait_point['x']}, {self.top_bait_point['y']})...", end='', flush=True)
                        self.simulate_click(self.top_bait_point['x'], self.top_bait_point['y'], hold_delay=0.1)
                        if not self.interruptible_sleep(self.bait_click_delay):
                            return False
                    
                    # 4. Cast to water point
                    self.current_status = "Casting rod"
                    print(f"\rPre-cast: Casting to water point ({self.water_point['x']}, {self.water_point['y']})...", end='', flush=True)
                    self.simulate_click(self.water_point['x'], self.water_point['y'], hold_delay=self.cast_hold_duration)
                    if not self.interruptible_sleep(self.mouse_move_settle):
                        return False
                    
                    # Skip camera/zoom, just wait for minigame
                    print("\rPre-cast: (Camera/zoom/rotation skipped by user setting)", end='', flush=True)
                    if not self.interruptible_sleep(self.pre_cast_minigame_wait):
                        return False
                else:
                    # Camera/zoom/rotation steps (normal camera mode)
                    # Wait before camera rotation
                    print("\rPre-cast: Waiting before camera rotation...", end='', flush=True)
                    if not self.interruptible_sleep(0.6):
                        return False
                    
                    # Rotate camera 180 degrees
                    print("\rPre-cast: Rotating camera 180°...", end='', flush=True)
                    # Hold right click
                    win32api.mouse_event(0x0008, 0, 0)  # MOUSEEVENTF_RIGHTDOWN
                    if not self.interruptible_sleep(self.camera_rotation_delay):
                        return False
                    # Move mouse right to rotate 180° (slower movement)
                    for _ in range(self.camera_rotation_steps):
                        win32api.mouse_event(0x0001, 100, 0, 0, 0)  # MOUSEEVENTF_MOVE, move right 100 pixels
                        if not self.interruptible_sleep(self.camera_rotation_step_delay):
                            return False
                    if not self.interruptible_sleep(self.camera_rotation_settle_delay):
                        return False
                    # Release right click
                    win32api.mouse_event(0x0010, 0, 0)  # MOUSEEVENTF_RIGHTUP
                    if not self.interruptible_sleep(self.camera_rotation_settle_delay):
                        return False
                    
                    # Zoom in 3 ticks after rotation
                    print("\rPre-cast: Zooming in 3 ticks...", end='', flush=True)
                    for _ in range(self.zoom_ticks):
                        win32api.mouse_event(0x0800, 0, 0, 120, 0)  # MOUSEEVENTF_WHEEL, scroll up
                        if not self.interruptible_sleep(self.zoom_tick_delay):
                            return False
                    if not self.interruptible_sleep(self.zoom_settle_delay):
                        return False
                    
                    # Wait for minigame to appear after rotation (prevent premature detection)
                    print("\rPre-cast: Waiting for minigame to appear...", end='', flush=True)
                    if not self.interruptible_sleep(self.pre_cast_minigame_wait):
                        return False
            
            if not self.interruptible_sleep(0.5):
                return False
            return True
            
        except Exception as e:
            print(f"\rError in pre_cast: {e}", end='', flush=True)
            return False
    
    def buy_common_bait(self):
        """Buy common bait from shop"""
        # Check if all button coordinates are set
        if not self.yes_button or not self.middle_button or not self.no_button:
            print("\r⚠️ Auto Buy Bait: Button coordinates not set! Please configure Yes, Middle, and No buttons.", end='', flush=True)
            if not self.interruptible_sleep(2):
                return False
            return True  # Continue anyway
        
        # Check loop counter
        if self.bait_loop_counter > 0:
            self.bait_loop_counter -= 1
            print(f"\rAuto Buy Bait: Skipping ({self.bait_loop_counter} loops until next purchase)", end='', flush=True)
            return True
        
        # Execute purchase sequence
        try:
            print("\rAuto Buy Bait: Starting purchase sequence...", end='', flush=True)
            kb = Controller()
            
            # 1) Press 'e' key, wait 3s
            kb.press('e')
            kb.release('e')
            if not self.interruptible_sleep(3):
                return False
            
            # 2) Click yes button, wait 3s
            self.simulate_click(self.yes_button['x'], self.yes_button['y'], hold_delay=0.1)
            if not self.interruptible_sleep(3):
                return False
            
            # 3) Click middle button, wait 3s
            self.simulate_click(self.middle_button['x'], self.middle_button['y'], hold_delay=0.1)
            if not self.interruptible_sleep(3):
                return False
            
            # 4) Type number (loops per purchase)
            number_str = str(self.loops_per_purchase)
            for char in number_str:
                kb.press(char)
                kb.release(char)
                if not self.interruptible_sleep(self.general_action_delay):
                    return False
            if not self.interruptible_sleep(0.5):
                return False
            
            # 5) Click yes button, wait 3s
            self.simulate_click(self.yes_button['x'], self.yes_button['y'], hold_delay=0.1)
            if not self.interruptible_sleep(3):
                return False
            
            # 6) Click no button (cancel to avoid problems), wait 3s
            self.simulate_click(self.no_button['x'], self.no_button['y'], hold_delay=0.1)
            if not self.interruptible_sleep(3):
                return False
            
            # 7) Click middle button again, wait 3s
            self.simulate_click(self.middle_button['x'], self.middle_button['y'], hold_delay=0.1)
            if not self.interruptible_sleep(3):
                return False
            
            # Set counter to loops_per_purchase for next time
            self.bait_loop_counter = self.loops_per_purchase
            
            print(f"\r✓ Bait purchased! Next purchase in {self.loops_per_purchase} loops.", end='', flush=True)
            return True
            
        except Exception as e:
            print(f"\rError buying bait: {e}", end='', flush=True)
            return True  # Continue anyway
    
    def esperar(self):
        """Stage 2: Wait for fish - Cast and wait for colors to appear"""
        if not self.running:
            return False
        
        # Check if area is set
        if not self.area_coords:
            print("\rWaiting: ✗ No area set!", end='', flush=True)
            if not self.interruptible_sleep(1):
                return False
            return False
        
        # Rod already selected in pre_cast, just need to cast and wait for colors
        print(f"\rScanning for colors (timeout: {self.recast_timeout}s)...", end='', flush=True)
        
        # Step 5: Start scanning for colors with timeout
        start_time = time.time()
        target_colors = [
            (85, 170, 255),   # Blue #55aaff - Main bar
            (255, 255, 255),  # White #ffffff - Center line
            (25, 25, 25),     # Black #191919 - Borders/shadows
            (170, 255, 0),    # Green-yellow #aaff00 - UI element
            (32, 34, 36)      # Dark gray #202224 - Frame/background
        ]
        
        while self.running:
            # Check timeout
            elapsed_time = time.time() - start_time
            if elapsed_time >= self.recast_timeout:
                print(f"\rWaiting: ✗ Timeout ({self.recast_timeout}s) - No colors found. Recasting...", end='', flush=True)
                return False  # Timeout - restart from pre_cast
            
            # Capture screenshot
            screenshot = self.capture_area()
            
            if screenshot is not None:
                # Check for anti-macro black screen
                if self.check_anti_macro_black_screen(screenshot):
                    print(f"\r⚠️  Anti-macro detected during scanning! Handling...", end='', flush=True)
                    if not self.handle_anti_macro_detection():
                        return False  # User stopped
                    # Anti-macro cleared - restart from beginning
                    return False  # Return to main loop to restart
                
                # Check for all 3 colors
                all_colors_found = True
                for color in target_colors:
                    found, _ = self.check_color_in_image(screenshot, color)
                    if not found:
                        all_colors_found = False
                        break
                
                if all_colors_found:
                    print(f"\rWaiting: ✓ All colors detected! Starting fishing... (took {elapsed_time:.1f}s)", end='', flush=True)
                    return True  # All colors found - proceed to fishing
                else:
                    # Still waiting
                    print(f"\rWaiting for colors... ({elapsed_time:.1f}s/{self.recast_timeout}s)", end='', flush=True)
            
            # Small delay to avoid excessive CPU usage (interruptible)
            if not self.interruptible_sleep(self.fruit_detection_delay):
                return False
        
        return False
    
    def pesca(self):
        """Stage 3: Fish catch"""
        if not self.running:
            # Release mouse if stopping
            if self.mouse_pressed:
                win32api.mouse_event(0x0004, 0, 0)  # MOUSEEVENTF_LEFTUP
                self.mouse_pressed = False
            return False
        
        # V3: Calculate detection FPS
        self.fps_frame_count += 1
        current_time = time.time()
        elapsed = current_time - self.fps_last_time
        if elapsed >= 1.0:  # Update FPS every second
            self.detection_fps = self.fps_frame_count / elapsed
            self.fps_frame_count = 0
            self.fps_last_time = current_time
        
        # Target color to detect
        target_color = (85, 170, 255)  # RGB: #55aaff
        
        # Take screenshot of the selected area
        screenshot = self.capture_area()
        
        if screenshot is not None:
            # Check if target color exists in screenshot and get middle X coordinate
            color_found, middle_x = self.check_color_in_image(screenshot, target_color)
            
            # Print result (1 line per loop)
            if color_found:
                # Convert relative X to absolute screen coordinate
                absolute_x = self.area_coords['x'] + middle_x
                
                # Crop the screenshot to a 1-pixel wide vertical line at middle_x
                vertical_line = self.crop_vertical_line(screenshot, middle_x)
                
                if vertical_line is not None:
                    # Find topmost and bottommost black pixels
                    black_color = (25, 25, 25)  # #191919
                    top_y, bottom_y = self.find_topmost_bottommost_color(vertical_line, black_color)
                    
                    if top_y is not None and bottom_y is not None:
                        # Second crop: Extract only the section between top_y and bottom_y
                        cropped_section = self.crop_vertical_section(vertical_line, top_y, bottom_y)
                        
                        if cropped_section is not None:
                            # Find white color in the cropped section
                            white_color = (255, 255, 255)  # #FFFFFF
                            white_top, white_bottom = self.find_topmost_bottommost_color(cropped_section, white_color, tolerance=5)
                            
                            if white_top is not None and white_bottom is not None:
                                # Calculate height of white section
                                white_height = white_bottom - white_top + 1
                                
                                # Calculate middle position for arrow (relative to cropped section)
                                white_middle = (white_top + white_bottom) // 2
                                
                                # Convert to absolute Y position (relative to original area)
                                absolute_white_middle_y = top_y + white_middle
                                
                                # Find biggest black group in cropped section
                                black_color_alt = (25, 25, 25)  # #191919
                                # Max gap: allow small gaps but not huge ones (max 20% of white height or 5 pixels, whichever is larger)
                                max_gap = max(5, int(white_height * 0.2))
                                black_group_middle = self.find_biggest_black_group(cropped_section, black_color_alt, max_gap)
                                
                                if black_group_middle is not None:
                                    # Convert to absolute Y position (relative to original area)
                                    absolute_black_group_y = top_y + black_group_middle
                                    
                                    # Reset lost counter - we have good detection
                                    self.detection_lost_counter = 0
                                    
                                    # PD Control: align black group center with white line center
                                    # Error: positive when group is BELOW white (Y larger, need to HOLD to go UP)
                                    # Error: negative when group is ABOVE white (Y smaller, need to RELEASE to go DOWN)
                                    error = black_group_middle - white_middle
                                    
                                    # Calculate PD output
                                    current_time = time.time()
                                    dt = current_time - self.pid_last_time
                                    if dt > 0:
                                        # Proportional term
                                        p_term = self.pid_kp * error
                                        
                                        # Derivative term
                                        d_term = self.pid_kd * (error - self.pid_last_error) / dt
                                        
                                        # PD output with clamp
                                        pd_output = p_term + d_term
                                        pd_output = max(-self.pid_clamp, min(self.pid_clamp, pd_output))  # Apply clamp
                                        
                                        # Convert to duty cycle (0 to 1)
                                        # Normalize by clamp*2 so pd_output range [-clamp, +clamp] maps to duty_cycle [0, 1]
                                        duty_cycle = 0.5 + (pd_output / (self.pid_clamp * 2))
                                        duty_cycle = max(0.0, min(1.0, duty_cycle))  # Ensure in range
                                        
                                        # Simple control: just check if we should hold or release
                                        should_hold = duty_cycle > 0.5
                                        
                                        # ALWAYS send the command, don't check previous state
                                        if should_hold:
                                            if not self.mouse_pressed:
                                                pyautogui.mouseDown()
                                                self.mouse_pressed = True
                                        else:
                                            if self.mouse_pressed:
                                                pyautogui.mouseUp()
                                                self.mouse_pressed = False
                                        
                                        # RESEND MECHANISM: Fix Roblox click bug where bar drops even when arrows track
                                        # Every resend_interval (default 500ms), resend the current mouse state
                                        if current_time - self.last_resend_time >= self.resend_interval:
                                            # Resend the current state to fix "bugged" bar
                                            if self.mouse_pressed:
                                                pyautogui.mouseDown()
                                            else:
                                                pyautogui.mouseUp()
                                            self.last_resend_time = current_time
                                        
                                        # Update PD state
                                        self.pid_last_error = error
                                        self.pid_last_time = current_time
                                        
                                        print(f"\rW:{white_middle} B:{black_group_middle} E:{error:+.0f} PD:{pd_output:+.2f} D:{duty_cycle:.2f} {'HOLD' if should_hold else 'FREE'} [{'ON' if self.mouse_pressed else 'OFF'}]", end='', flush=True)
                                    
                                    # Show debug arrows
                                    self.show_debug_arrow(middle_x)
                                    self.show_horizontal_arrows(top_y, bottom_y)
                                    self.show_white_middle_arrow(absolute_white_middle_y)
                                    self.show_black_group_arrow(absolute_black_group_y)
                                else:
                                    # Black group not found - increment lost counter
                                    self.detection_lost_counter += 1
                                    
                                    # Only release if we've lost detection for too many frames
                                    if self.detection_lost_counter > self.max_lost_frames:
                                        if self.mouse_pressed:
                                            pyautogui.mouseUp()
                                            self.mouse_pressed = False
                                        self.pid_last_error = 0.0
                                        print(f"\rBlue: \u2713 | X: {middle_x} | BlackGroup: LOST ({self.detection_lost_counter} frames)  ", end='', flush=True)
                                    else:
                                        # Keep last state - don't change mouse
                                        print(f"\rBlue: \u2713 | X: {middle_x} | BlackGroup: TEMP LOST ({self.detection_lost_counter}/{self.max_lost_frames}) - Keeping last state  ", end='', flush=True)
                                    
                                    # Show debug arrows
                                    self.show_debug_arrow(middle_x)
                                    self.show_horizontal_arrows(top_y, bottom_y)
                                    self.show_white_middle_arrow(absolute_white_middle_y)
                                    self.hide_black_group_arrow()
                            else:
                                # Hold mouse if white not found (to make it go to the top)
                                # This is because sometimes the white line gets behind text
                                if not self.mouse_pressed:
                                    pyautogui.mouseDown()
                                    self.mouse_pressed = True
                                
                                # Reset PD
                                self.pid_last_error = 0.0
                                
                                print(f"\rBlue: ✓ | X: {middle_x} | Black Y:[{top_y},{bottom_y}] | White: NOT FOUND - HOLDING  ", end='', flush=True)
                                self.show_debug_arrow(middle_x)
                                self.show_horizontal_arrows(top_y, bottom_y)
                                self.hide_white_middle_arrow()
                                self.hide_black_group_arrow()
                        else:
                            print(f"\rBlue: ✓ | Middle X: {middle_x} | Black Top Y: {top_y} | Bottom Y: {bottom_y}  ", end='', flush=True)
                            self.show_debug_arrow(middle_x)
                            self.show_horizontal_arrows(top_y, bottom_y)
                            self.hide_black_group_arrow()
                    else:
                        print(f"\rBlue: ✓ | Middle X: {middle_x} | Black pixels NOT FOUND  ", end='', flush=True)
                        self.show_debug_arrow(middle_x)
                        self.hide_horizontal_arrows()
                        self.hide_white_middle_arrow()
                        self.hide_black_group_arrow()
                else:
                    print(f"\rBlue color {target_color}: ✓ FOUND | Middle X: {middle_x}  ", end='', flush=True)
                    self.show_debug_arrow(middle_x)
                    self.hide_white_middle_arrow()
                    self.hide_black_group_arrow()
                
            else:
                print(f"\rBlue color {target_color}: ✗ NOT FOUND - Exiting fishing state  ", end='', flush=True)
                # Release mouse when exiting fishing state
                if self.mouse_pressed:
                    pyautogui.mouseUp()
                    self.mouse_pressed = False
                
                # Reset PD
                self.pid_last_error = 0.0
                
                # Hide all arrows
                self.hide_debug_arrow()
                self.hide_horizontal_arrows()
                self.hide_white_middle_arrow()
                self.hide_black_group_arrow()
                
                # Exit fishing state - return False to restart main loop
                return False
        else:
            print(f"\rNo area selected - skipping color check  ", end='', flush=True)
        
        # Blue color found - stay in fishing state
        # Brief interruptible delay to reduce CPU and improve stop responsiveness
        if not self.interruptible_sleep(self.fruit_detection_delay):
            return False
        return True
    
    # ========== AUTO CRAFT MODE LOOPS ==========
    def auto_craft_pre_cast(self):
        """Stage 1 (Auto Craft Mode): Pre-cast preparation for auto craft"""
        if not self.running:
            return False
        
        # Auto Craft Mode doesn't buy bait - it crafts instead
        # Check if we need to run craft cycle
        # craft_every_n_fish = 0 means craft on every cast
        should_craft = False
        if self.craft_every_n_fish == 0:
            # craft_every_n_fish = 0 means craft before every cast
            should_craft = True
        elif self.craft_every_n_fish > 0 and (self.fish_caught == 0 or self.fish_caught % self.craft_every_n_fish == 0):
            # Craft on first run or after catching N fish
            # Check if we already crafted for this fish count (prevents loop on failed cast)
            if not hasattr(self, 'last_craft_fish_count') or self.fish_caught != self.last_craft_fish_count:
                should_craft = True
        
        if should_craft:
            self.current_status = "Auto Crafting"
            print(f"\r⚒️ Auto Craft: Running craft cycle (fish caught: {self.fish_caught})...", end='', flush=True)
            self.run_auto_craft()
            self.last_craft_fish_count = self.fish_caught  # Mark this count as crafted
            # Don't reset fish_caught - let it accumulate
            if not self.interruptible_sleep(0.3):  # Reduced from 1.0
                return False
        
        # New flow: craft -> shift lock alignment -> cast -> zoom -> wait -> fish -> zoom out -> check fruit -> store
        try:
            kb = Controller()
            fruit_detected = False  # Flag to track if fruit was caught
            
            # ============ PART 1: ALIGNMENT ============
            # 1. Shift Lock Alignment (replaces the old casting for alignment)
            print(f"\r[Auto Craft] Activating Shift Lock for alignment...", end='', flush=True)
            kb.press(Key.shift)
            kb.release(Key.shift)
            if not self.interruptible_sleep(0.2):  # Reduced from 0.5
                return False
            
            print(f"\r[Auto Craft] Deactivating Shift Lock...", end='', flush=True)
            kb.press(Key.shift)
            kb.release(Key.shift)
            if not self.interruptible_sleep(0.2):  # Reduced from 0.5
                return False
            
            # ============ PART 2: CASTING & MINIGAME ============
            # 2. Deselect rod (press everything_else_hotkey to deselect)
            print(f"\r[Auto Craft] Deselecting rod ({self.everything_else_hotkey})...", end='', flush=True)
            kb.press(self.everything_else_hotkey)
            kb.release(self.everything_else_hotkey)
            if not self.interruptible_sleep(self.rod_deselect_delay):
                return False
            
            # 3. Select rod (press rod_hotkey)
            print(f"\r[Auto Craft] Selecting rod ({self.rod_hotkey})...", end='', flush=True)
            kb.press(self.rod_hotkey)
            kb.release(self.rod_hotkey)
            if not self.interruptible_sleep(self.rod_select_delay):
                return False
            
            # 4. Auto Select Top Bait
            bait_coord = None
            if self.auto_select_top_bait and self.top_bait_point:
                self.current_status = "Selecting bait"
                print(f"\r[Auto Craft] Selecting top bait at ({self.top_bait_point['x']}, {self.top_bait_point['y']})...", end='', flush=True)
                bait_coord = self.top_bait_point
            
            # Click the selected bait slot if we have one
            if bait_coord:
                self.simulate_click(bait_coord['x'], bait_coord['y'], hold_delay=0.1)
                if not self.interruptible_sleep(self.bait_click_delay):
                    return False
            
            # 5. Cast to auto craft water point for minigame
            if not self.auto_craft_water_point:
                print("\r[Auto Craft] ✗ No auto craft water point set!", end='', flush=True)
                if not self.interruptible_sleep(1):
                    return False
                return False
            
            self.current_status = "Casting rod"
            print(f"\r[Auto Craft] Casting to water point ({self.auto_craft_water_point['x']}, {self.auto_craft_water_point['y']})...", end='', flush=True)
            win32api.SetCursorPos((self.auto_craft_water_point['x'], self.auto_craft_water_point['y']))
            win32api.mouse_event(0x0001, 0, 1, 0, 0)  # MOUSEEVENTF_MOVE 1px down
            if not self.interruptible_sleep(self.mouse_move_settle):
                return False
            
            pyautogui.mouseDown()
            if not self.interruptible_sleep(self.cast_hold_duration):
                pyautogui.mouseUp()
                return False
            pyautogui.mouseUp()

            # Delay antes do zoom in para minigame (auto craft) - OPTIMIZED
            if not self.interruptible_sleep(0.3):  # Reduced from 0.6
                return False

            # 6. Zoom in 9 ticks after cast
            print(f"\r[Auto Craft] Zooming in 9 ticks...", end='', flush=True)
            # Move mouse to safe position first (screen center)
            win32api.SetCursorPos((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            if not self.interruptible_sleep(0.03):  # Reduced from 0.1
                return False
            for i in range(9):
                if not self.running:
                    return False
                win32api.mouse_event(0x0800, 0, 0, 120, 0)  # MOUSEEVENTF_WHEEL (scroll up)
                if not self.interruptible_sleep(self.zoom_tick_delay):
                    return False
            if not self.interruptible_sleep(self.zoom_settle_delay):
                return False
            
            # 7. Wait for minigame to appear (call auto_craft_esperar)
            self.current_status = "Scanning for fish (Auto Craft)"
            print(f"\r[Auto Craft] Waiting for minigame...", end='', flush=True)
            wait_success = self.auto_craft_esperar()
            if not wait_success:
                # Minigame didn't appear em tempo, recasting com camera initialize
                print(f"\r[Auto Craft] Minigame timeout, recasting with camera initialize...", end='', flush=True)
                self.current_status = "Restaurando câmera (auto craft)"
                # Inicializa a câmera igual ao first_run
                # Scroll in 30 ticks (first person guarantee)
                for _ in range(30):
                    win32api.mouse_event(0x0800, 0, 0, 120, 0)
                    if not self.interruptible_sleep(0.01):
                        return False
                if not self.interruptible_sleep(0.1):
                    return False
                # Scroll out 13 ticks (standardize view)
                for _ in range(13):
                    win32api.mouse_event(0x0800, 0, 0, -120, 0)
                    if not self.interruptible_sleep(0.01):
                        return False
                if not self.interruptible_sleep(self.rod_select_delay):
                    return False
                return False  # Signal to recast
            
            # 8. Play the minigame (call auto_craft_pesca)
            self.current_status = "Fishing (Auto Craft)"
            print(f"\r[Auto Craft] Playing minigame...", end='', flush=True)
            while self.running and self.auto_craft_pesca():
                pass  # Keep fishing while auto_craft_pesca() returns True
            
            # Ensure mouse is released after minigame
            if self.mouse_pressed:
                win32api.mouse_event(0x0004, 0, 0)  # MOUSEEVENTF_LEFTUP
                self.mouse_pressed = False
            
            # 9. Zoom out 9 ticks after minigame
            print(f"\r[Auto Craft] Zooming out 9 ticks after minigame...", end='', flush=True)
            # Move mouse to safe position first (screen center)
            win32api.SetCursorPos((SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            if not self.interruptible_sleep(0.03):  # Reduced from 0.1
                return False
            for i in range(9):
                if not self.running:
                    return False
                win32api.mouse_event(0x0800, 0, 0, -120, 0)
                if not self.interruptible_sleep(self.zoom_tick_delay):
                    return False
            if not self.interruptible_sleep(self.zoom_settle_delay):
                return False
            
            # ============ PART 3: FRUIT CHECK & STORAGE ============
            # 10. Shift Lock Alignment (before pressing fruit hotkey)
            print(f"\r[Auto Craft] Activating Shift Lock for alignment...", end='', flush=True)
            kb.press(Key.shift)
            kb.release(Key.shift)
            if not self.interruptible_sleep(0.2):  # Reduced from 0.5
                return False
            
            print(f"\r[Auto Craft] Deactivating Shift Lock...", end='', flush=True)
            kb.press(Key.shift)
            kb.release(Key.shift)
            if not self.interruptible_sleep(0.2):  # Reduced from 0.5
                return False
            
            # 11. Press fruit hotkey (3) to pick up fruit
            print(f"\r[Auto Craft] Pressing fruit hotkey ({self.fruit_hotkey})...", end='', flush=True)
            kb.press(self.fruit_hotkey)
            kb.release(self.fruit_hotkey)
            if not self.interruptible_sleep(0.5):  # Reduced from 1.0
                return False
            
            # 12. Check fruit color (ALWAYS - every cycle)
            if self.fruit_point and self.fruit_color:
                self.current_status = "Checking fruit color"
                print(f"\r[Auto Craft] Checking fruit color at ({self.fruit_point['x']}, {self.fruit_point['y']})...", end='', flush=True)
                
                try:
                    with mss.mss() as sct:
                        # Capture a 1x1 pixel area at fruit_point
                        monitor = {"top": self.fruit_point['y'], "left": self.fruit_point['x'], "width": 1, "height": 1}
                        screenshot = sct.grab(monitor)
                        # Get pixel color (BGRA format)
                        pixel = screenshot.pixel(0, 0)
                        current_color = (pixel[2], pixel[1], pixel[0])  # Convert to BGR
                        

                        # Compare colors (increased tolerance and debug info)
                        tolerance = 15
                        diff_r = abs(current_color[0] - self.fruit_color[0])
                        diff_g = abs(current_color[1] - self.fruit_color[1])
                        diff_b = abs(current_color[2] - self.fruit_color[2])
                        color_match = (
                            diff_r <= tolerance and
                            diff_g <= tolerance and
                            diff_b <= tolerance
                        )
                        print(f"[Auto Craft] Fruit color check: Detected={current_color} Expected={self.fruit_color} | ΔR={diff_r} ΔG={diff_g} ΔB={diff_b} | Tolerance={tolerance}", flush=True)

                        if color_match:
                            fruit_detected = True
                            self.fruits_caught += 1
                            self.fish_at_last_fruit = self.fish_caught
                            if stats_manager: stats_manager.log_fruit()
                            print(f"\r🍎 FRUIT DETECTED! Total fruits: {self.fruits_caught}", end='', flush=True)
                            # Zoom in 6 ticks for better fruit visibility in screenshot
                            print(f"\r[Auto Craft] Zooming in 6 ticks for screenshot...", end='', flush=True)
                            for _ in range(6):
                                win32api.mouse_event(0x0800, 0, 0, 120, 0)  # MOUSEEVENTF_WHEEL, scroll up
                                if not self.interruptible_sleep(self.zoom_tick_delay):
                                    return False
                            if not self.interruptible_sleep(self.zoom_settle_delay):
                                return False
                            # Take screenshot at zoomed position
                            print(f"\r[Auto Craft] 📸 Capturing screenshot...", end='', flush=True)
                            screenshot_path = self.capture_center_screenshot(auto_craft_mode=True)
                            # Zoom out 6 ticks to restore view
                            print(f"\r[Auto Craft] Zooming out 6 ticks...", end='', flush=True)
                            for _ in range(6):
                                win32api.mouse_event(0x0800, 0, 0, -120, 0)  # MOUSEEVENTF_WHEEL, scroll down
                                if not self.interruptible_sleep(self.zoom_tick_delay):
                                    return False
                            if not self.interruptible_sleep(self.zoom_settle_delay):
                                return False
                            # Send webhook notification with screenshot
                            if screenshot_path:
                                self.send_fruit_webhook(screenshot_path)
                            # Wait after screenshot
                            if not self.interruptible_sleep(0.3):
                                return False
                        else:
                            print(f"\r[Auto Craft] No fruit detected. Detected: {current_color}, Expected: {self.fruit_color} | ΔR={diff_r} ΔG={diff_g} ΔB={diff_b} | Tolerance={tolerance}", end='', flush=True)
                            
                except Exception as e:
                    print(f"\r[Auto Craft] Warning: Failed to check fruit color: {e}", end='', flush=True)
            
            # 13. Click Store button (only after fruit sequence or always if no fruit logic)
            if self.fruit_point:
                # Only store after fruit sequence if fruit was detected, otherwise always store
                if fruit_detected or not self.fruit_color:
                    self.current_status = "Storing fruit"
                    print(f"\r[Auto Craft] Clicking Store button at ({self.fruit_point['x']}, {self.fruit_point['y']})...", end='', flush=True)
                    win32api.SetCursorPos((self.fruit_point['x'], self.fruit_point['y']))
                    win32api.mouse_event(0x0001, 0, 1, 0, 0)  # MOUSEEVENTF_MOVE 1px down
                    if not self.interruptible_sleep(0.05):
                        return False
                    win32api.mouse_event(0x0002, 0, 0)  # LEFT DOWN
                    win32api.mouse_event(0x0004, 0, 0)  # LEFT UP
                    if not self.interruptible_sleep(self.store_click_delay):
                        return False
                    # Press backspace to close storage menu
                    print(f"\r[Auto Craft] Pressing backspace to close storage...", end='', flush=True)
                    kb.press(Key.backspace)
                    kb.release(Key.backspace)
                    if not self.interruptible_sleep(0.2):  # Reduced from 0.5
                        return False
            
            # Mark first run as done when we reach store
            if self.first_catch:
                self.first_catch = False
                print(f"\r[Auto Craft] First run completed, fruit check/store will run every cycle now...", end='', flush=True)
            
            # 13. Count fish ONLY if no fruit was caught
            if self.running and not fruit_detected:
                self.fish_caught += 1
                if stats_manager: stats_manager.log_fish()
                print(f"\r🐟 Fish caught! Total fish: {self.fish_caught}", end='', flush=True)
            
            print(f"\r[Auto Craft] ✅ Cycle complete! Restarting...", end='', flush=True)
            return True
            
        except Exception as e:
            print(f"\r[Auto Craft] Error in pre-cast: {e}", end='', flush=True)
            return False
    
    def rotate_camera_for_fruit_scan(self):
        """Rotate camera for fruit scanning: zoom in 30, zoom out 12 to detect fruit"""
        try:
            # Get screen center for mouse movements
            screen_width = win32api.GetSystemMetrics(0)
            screen_height = win32api.GetSystemMetrics(1)
            screen_center_x = screen_width // 2
            screen_center_y = screen_height // 2
            
            # Zoom in 30 ticks (mousewheel scroll up)
            print(f"\r[Auto Craft] Zooming in 30 ticks...", end='', flush=True)
            for i in range(30):
                if not self.running:
                    return
                win32api.mouse_event(0x0800, 0, 0, 120, 0)  # MOUSEEVENTF_WHEEL (scroll up)
                if not self.interruptible_sleep(self.zoom_tick_delay):
                    return
            
            if not self.interruptible_sleep(self.zoom_settle_delay):
                return
            
            # Zoom out 12 ticks (mousewheel scroll down)
            print(f"\r[Auto Craft] Zooming out 12 ticks...", end='', flush=True)
            for i in range(12):
                if not self.running:
                    return
                win32api.mouse_event(0x0800, 0, 0, -120, 0)  # MOUSEEVENTF_WHEEL (scroll down)
                if not self.interruptible_sleep(self.zoom_tick_delay):
                    return
            
        except Exception as e:
            print(f"\r[Auto Craft] Error in fruit scan camera: {e}", end='', flush=True)
    
    def rotate_camera_for_minigame(self):
        """Rotate camera 90 degrees RIGHT for minigame"""
        try:
            print(f"\r[Auto Craft] Rotating camera 90° right...", end='', flush=True)
            
            # Hold right-click
            win32api.mouse_event(0x0008, 0, 0)  # MOUSEEVENTF_RIGHTDOWN
            if not self.interruptible_sleep(self.camera_rotation_delay):
                return
            
            # Move mouse RIGHT to rotate camera
            for step in range(4):
                if not self.running:
                    win32api.mouse_event(0x0010, 0, 0)  # MOUSEEVENTF_RIGHTUP
                    return
                win32api.mouse_event(0x0001, 100, 0, 0, 0)  # MOUSEEVENTF_MOVE, move right 100 pixels
                if not self.interruptible_sleep(self.camera_rotation_step_delay):
                    return
            
            if not self.interruptible_sleep(self.camera_rotation_settle_delay):
                return
            
            # Release right-click
            win32api.mouse_event(0x0010, 0, 0)  # MOUSEEVENTF_RIGHTUP
            time.sleep(0.1)
            
        except Exception as e:
            print(f"\r[Auto Craft] Error in minigame camera rotation: {e}", end='', flush=True)
    
    def rotate_camera_back(self):
        """Rotate camera 90 degrees LEFT to reset position"""
        try:
            print(f"\r[Auto Craft] Rotating camera 90° left (back)...", end='', flush=True)
            
            # Hold right-click
            win32api.mouse_event(0x0008, 0, 0)  # MOUSEEVENTF_RIGHTDOWN
            if not self.interruptible_sleep(self.camera_rotation_delay):
                return
            
            # Move mouse LEFT to rotate camera back
            for step in range(4):
                if not self.running:
                    win32api.mouse_event(0x0010, 0, 0)  # MOUSEEVENTF_RIGHTUP
                    return
                win32api.mouse_event(0x0001, -100, 0, 0, 0)  # MOUSEEVENTF_MOVE, move LEFT 100 pixels
                if not self.interruptible_sleep(self.camera_rotation_step_delay):
                    return
            
            if not self.interruptible_sleep(self.camera_rotation_settle_delay):
                return
            
            # Release right-click
            win32api.mouse_event(0x0010, 0, 0)  # MOUSEEVENTF_RIGHTUP
            time.sleep(0.1)
            
        except Exception as e:
            print(f"\r[Auto Craft] Error rotating camera back: {e}", end='', flush=True)
    
    def auto_craft_esperar(self):
        """Stage 2 (Auto Craft Mode): Wait for fish - uses auto craft area"""
        if not self.running:
            return False
        
        # Check if auto craft area is set
        if not self.auto_craft_area_coords:
            print("\r[Auto Craft] ✗ No auto craft area set!", end='', flush=True)
            if not self.interruptible_sleep(1):
                return False
            return False
        
        print(f"\r[Auto Craft] Scanning for colors (timeout: {self.recast_timeout}s)...", end='', flush=True)
        
        # Target colors to detect
        target_colors = [
            (85, 170, 255),   # Blue #55aaff - Main bar
            (255, 255, 255),  # White #ffffff - Center line
            (25, 25, 25),     # Black #191919 - Borders/shadows
            (170, 255, 0),    # Green-yellow #aaff00 - UI element
            (32, 34, 36)      # Dark gray #202224 - Frame/background
        ]
        
        start_time = time.time()
        
        while self.running:
            # Check timeout
            elapsed_time = time.time() - start_time
            if elapsed_time >= self.recast_timeout:
                print(f"\r[Auto Craft] ✗ Timeout ({self.recast_timeout}s) - Recasting...", end='', flush=True)
                return False
            
            # Capture screenshot of auto craft area
            screenshot = self.capture_auto_craft_area()
            
            if screenshot is not None:
                # Check for anti-macro
                if self.check_anti_macro_black_screen(screenshot):
                    print(f"\r[Auto Craft] ⚠️  Anti-macro detected! Handling...", end='', flush=True)
                    if not self.handle_anti_macro_detection():
                        return False
                    return False
                
                # Check for all colors
                all_colors_found = True
                for color in target_colors:
                    found, _ = self.check_color_in_image(screenshot, color)
                    if not found:
                        all_colors_found = False
                        break
                
                if all_colors_found:
                    print(f"\r[Auto Craft] ✓ All colors detected! Starting fishing... (took {elapsed_time:.1f}s)", end='', flush=True)
                    return True
                else:
                    print(f"\r[Auto Craft] Waiting for colors... ({elapsed_time:.1f}s/{self.recast_timeout}s)", end='', flush=True)
            
            if not self.interruptible_sleep(self.fruit_detection_delay):
                return False
        
        return False
    
    def auto_craft_pesca(self):
        """Stage 3 (Auto Craft Mode): Fish catch - uses auto craft area"""
        if not self.running:
            if self.mouse_pressed:
                pyautogui.mouseUp()
                self.mouse_pressed = False
            return False
        
        # Target color to detect
        target_color = (85, 170, 255)  # RGB: #55aaff
        
        # Take screenshot of the auto craft area
        screenshot = self.capture_auto_craft_area()
        
        if screenshot is not None:
            # Check if target color exists
            color_found, middle_x = self.check_color_in_image(screenshot, target_color)
            
            if color_found:
                # Use same fishing logic as normal mode but with auto craft area
                absolute_x = self.auto_craft_area_coords['x'] + middle_x
                vertical_line = self.crop_vertical_line(screenshot, middle_x)
                
                if vertical_line is not None:
                    black_color = (25, 25, 25)
                    top_y, bottom_y = self.find_topmost_bottommost_color(vertical_line, black_color)
                    
                    if top_y is not None and bottom_y is not None:
                        cropped_section = self.crop_vertical_section(vertical_line, top_y, bottom_y)
                        
                        if cropped_section is not None:
                            white_color = (255, 255, 255)
                            white_top, white_bottom = self.find_topmost_bottommost_color(cropped_section, white_color, tolerance=5)
                            
                            if white_top is not None and white_bottom is not None:
                                white_height = white_bottom - white_top + 1
                                white_middle = (white_top + white_bottom) // 2
                                absolute_white_middle_y = top_y + white_middle
                                
                                max_gap = max(5, int(white_height * 0.2))
                                black_group_middle = self.find_biggest_black_group(cropped_section, (25, 25, 25), max_gap)
                                
                                if black_group_middle is not None:
                                    absolute_black_group_y = top_y + black_group_middle
                                    self.detection_lost_counter = 0
                                    
                                    error = black_group_middle - white_middle
                                    current_time = time.time()
                                    dt = current_time - self.pid_last_time
                                    
                                    if dt > 0:
                                        p_term = self.pid_kp * error
                                        d_term = self.pid_kd * (error - self.pid_last_error) / dt
                                        pd_output = p_term + d_term
                                        pd_output = max(-self.pid_clamp, min(self.pid_clamp, pd_output))
                                        
                                        duty_cycle = 0.5 + (pd_output / (self.pid_clamp * 2))
                                        duty_cycle = max(0.0, min(1.0, duty_cycle))
                                        should_hold = duty_cycle > 0.5
                                        
                                        # Execute mouse action
                                        if should_hold:
                                            if not self.mouse_pressed:
                                                pyautogui.mouseDown()
                                                self.mouse_pressed = True
                                                if hasattr(self, 'show_debug_arrows') and self.show_debug_arrows and hasattr(self, 'debug_root') and hasattr(self, 'debug_status_label'):
                                                    self.debug_root.after(0, lambda: self.debug_status_label.configure(text=f"Action: HOLD | Err: {error:.1f}", text_color="#00dd00"))
                                        else:
                                            if self.mouse_pressed:
                                                pyautogui.mouseUp()
                                                self.mouse_pressed = False
                                                if hasattr(self, 'show_debug_arrows') and self.show_debug_arrows and hasattr(self, 'debug_root') and hasattr(self, 'debug_status_label'):
                                                    self.debug_root.after(0, lambda: self.debug_status_label.configure(text=f"Action: RELEASE | Err: {error:.1f}", text_color="#ff4444"))
                                        
                                        # Update last state variables
                                        self.last_error = error
                                        self.last_bar_y = black_group_middle
                                        self.last_time = current_time
                                        self.pid_last_error = error
                                        self.pid_last_time = current_time
                                        self.detection_lost_counter = 0  # Reset detection lost counter
                                        
                                        print(f"\r[AC] W:{white_middle} B:{black_group_middle} E:{error:+.0f} PD:{pd_output:+.2f} {'HOLD' if should_hold else 'FREE'}", end='', flush=True)
                                else:
                                    # Black group not found - hold to go to top
                                    if not self.mouse_pressed:
                                        pyautogui.mouseDown()
                                        self.mouse_pressed = True
                                    print(f"\r[Auto Craft] White found but no black group - HOLDING", end='', flush=True)
                            else:
                                # White not found - hold to go to top
                                if not self.mouse_pressed:
                                    pyautogui.mouseDown()
                                    self.mouse_pressed = True
                                print(f"\r[Auto Craft] No white line - HOLDING to top", end='', flush=True)
            else:
                print(f"\r[Auto Craft] Blue not found - Exiting fishing", end='', flush=True)
                if self.mouse_pressed:
                     pyautogui.mouseUp()
                     self.mouse_pressed = False
                self.pid_last_error = 0.0
                return False
        
        if not self.interruptible_sleep(self.fruit_detection_delay):
            return False
        return True
    
    def capture_auto_craft_area(self):
        """Capture screenshot of the auto craft area using mss (optimized with singleton)"""
        if not self.auto_craft_area_coords:
            return None
        
        try:
            if self._mss_instance is None:
                self._mss_instance = mss.mss()
            
            monitor = {
                "left": self.auto_craft_area_coords['x'],
                "top": self.auto_craft_area_coords['y'],
                "width": self.auto_craft_area_coords['width'],
                "height": self.auto_craft_area_coords['height']
            }
            screenshot = self._mss_instance.grab(monitor)
            return np.array(screenshot)
        except Exception as e:
            self._mss_instance = None
            print(f"\r[Auto Craft] Error capturing area: {e}  ", end='', flush=True)
            return None
    
    def capture_area(self):
        """Capture screenshot of the selected area using mss (optimized with singleton)"""
        if not self.area_coords:
            return None
        
        try:
            # V3 Performance: Reuse mss instance instead of creating new each frame
            if self._mss_instance is None:
                self._mss_instance = mss.mss()
            
            monitor = {
                "left": self.area_coords['x'],
                "top": self.area_coords['y'],
                "width": self.area_coords['width'],
                "height": self.area_coords['height']
            }
            
            screenshot = self._mss_instance.grab(monitor)
            return np.array(screenshot)
        except Exception as e:
            # If mss fails, try recreating instance
            self._mss_instance = None
            print(f"\rError capturing area: {e}  ", end='', flush=True)
            return None
    
    def check_anti_macro_black_screen(self, img):
        """Check if at least half of the image is pure black (#000000) - Roblox anti-macro feature"""
        try:
            if img is None:
                return False
            
            # Extract RGB channels (ignore alpha)
            b, g, r = img[:, :, 0], img[:, :, 1], img[:, :, 2]
            
            # Check for pure black pixels (0, 0, 0)
            black_pixels = (r == 0) & (g == 0) & (b == 0)
            
            # Count black pixels
            total_pixels = img.shape[0] * img.shape[1]
            black_count = np.sum(black_pixels)
            
            # Check if at least 50% of pixels are black
            black_percentage = black_count / total_pixels
            
            return black_percentage >= 0.5
        except Exception as e:
            print(f"\rError checking anti-macro: {e}  ", end='', flush=True)
            return False
    
    def handle_anti_macro_detection(self):
        """Handle anti-macro black screen by spamming everything_else hotkey until cleared"""
        try:
            print("\r⚠️  ANTI-MACRO DETECTED! Spamming hotkey to clear...", end='', flush=True)
            kb = Controller()
            
            while self.running:
                # Check current screen
                screenshot = self.capture_area()
                
                if screenshot is None:
                    if not self.interruptible_sleep(0.25):
                        return False
                    continue
                
                # Check if still black
                if not self.check_anti_macro_black_screen(screenshot):
                    print("\r✅ Anti-macro cleared! Restarting...", end='', flush=True)
                    if not self.interruptible_sleep(0.5):
                        return False
                    return True  # Cleared - restart main loop
                
                # Spam everything_else hotkey
                kb.press(self.everything_else_hotkey)
                kb.release(self.everything_else_hotkey)
                print(f"\r⚠️  Anti-macro active... Pressing {self.everything_else_hotkey}...", end='', flush=True)
                
                if not self.interruptible_sleep(0.25):
                    return False
            
            return False  # Stopped by user
        except Exception as e:
            print(f"\rError handling anti-macro: {e}", end='', flush=True)
            return False
    
    def check_color_in_image(self, img, target_color, tolerance=10):
        """Check if a specific color exists in the image with tolerance and return middle X coordinate"""
        try:
            # img is in BGRA format from mss, convert to RGB
            # Extract RGB channels (ignore alpha)
            b, g, r = img[:, :, 0], img[:, :, 1], img[:, :, 2]
            
            # Target RGB values
            target_r, target_g, target_b = target_color
            
            # Check if any pixel matches the target color within tolerance
            matches = (
                (np.abs(r - target_r) <= tolerance) &
                (np.abs(g - target_g) <= tolerance) &
                (np.abs(b - target_b) <= tolerance)
            )
            
            # Check if color was found
            if np.any(matches):
                # Get coordinates of all matching pixels
                y_coords, x_coords = np.where(matches)
                
                # Calculate the middle X coordinate (mean of all X positions)
                middle_x = int(np.mean(x_coords))
                
                return True, middle_x
            else:
                return False, 0
                
        except Exception as e:
            print(f"\rError checking color: {e}  ", end='', flush=True)
            return False, 0
    
    def crop_vertical_line(self, img, x_position):
        """Crop a 1-pixel wide vertical line from the image at x_position"""
        try:
            # Extract the entire column at x_position
            # img shape is (height, width, channels)
            vertical_line = img[:, x_position:x_position+1, :]
            
            # vertical_line shape will be (height, 1, 4) for BGRA
            return vertical_line
            
        except Exception as e:
            print(f"\rError cropping vertical line: {e}  ", end='', flush=True)
            return None
    
    def find_topmost_bottommost_color(self, vertical_line, target_color, tolerance=5):
        """Find the topmost and bottommost Y coordinates of a color in the vertical line"""
        try:
            # vertical_line shape is (height, 1, 4) - BGRA format
            # Extract RGB channels
            b = vertical_line[:, 0, 0]
            g = vertical_line[:, 0, 1]
            r = vertical_line[:, 0, 2]
            
            # Target RGB values
            target_r, target_g, target_b = target_color
            
            # Find matching pixels
            matches = (
                (np.abs(r - target_r) <= tolerance) &
                (np.abs(g - target_g) <= tolerance) &
                (np.abs(b - target_b) <= tolerance)
            )
            
            # Get Y coordinates of matches
            y_coords = np.where(matches)[0]
            
            if len(y_coords) > 0:
                top_y = int(y_coords[0])  # First occurrence (topmost)
                bottom_y = int(y_coords[-1])  # Last occurrence (bottommost)
                return top_y, bottom_y
            else:
                return None, None
                
        except Exception as e:
            print(f"\rError finding color bounds: {e}  ", end='', flush=True)
            return None, None
    
    def crop_vertical_section(self, vertical_line, top_y, bottom_y):
        """Crop the vertical line to only include pixels between top_y and bottom_y"""
        try:
            # vertical_line shape is (height, 1, 4)
            # Extract section from top_y to bottom_y (inclusive)
            cropped_section = vertical_line[top_y:bottom_y+1, :, :]
            
            # cropped_section shape will be (bottom_y - top_y + 1, 1, 4)
            return cropped_section
            
        except Exception as e:
            print(f"\rError cropping vertical section: {e}  ", end='', flush=True)
            return None
    
    def force_exit(self):
        """Force exit the application"""
        self.running = False
        
        if self.listener:
            self.listener.stop()
        
        os._exit(0)  # Force exit even if in background
    
    def refresh_stats_display(self):
        """Refresh the stats tab display with current data"""
        global stats_manager
        if stats_manager is None:
            stats_manager = StatsManager()
        
        try:
            # Update today's summary
            today = stats_manager.get_today_summary()
            self.today_sessions_label.configure(text=str(today['sessions']))
            self.today_fish_label.configure(text=str(today['fish']))
            self.today_fruits_label.configure(text=str(today['fruits']))
            
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
                ctk.CTkLabel(row, text=day_data['date'], width=100, anchor="w", font=("Segoe UI", 9)).pack(side="left")
                ctk.CTkLabel(row, text=str(day_data['fish']), width=60, font=("Segoe UI", 9)).pack(side="left")
                ctk.CTkLabel(row, text=str(day_data['fruits']), width=60, font=("Segoe UI", 9)).pack(side="left")
        except Exception as e:
            logger.error(f"Error refreshing stats: {e}")
    
    def export_stats_csv(self):
        """Export stats to CSV file"""
        global stats_manager
        if stats_manager is None:
            stats_manager = StatsManager()
        
        try:
            filepath = os.path.join(BASE_DIR, f"fishing_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            if stats_manager.export_csv(filepath):
                self.info_label.configure(text=f"Exported to {os.path.basename(filepath)}", text_color=self.success_color)
            else:
                self.info_label.configure(text="Export failed", text_color=self.error_color)
        except Exception as e:
            logger.error(f"Export error: {e}")
    
    def on_closing(self):
        """Handle window close button"""
        self.force_exit()
    
    def show_hud(self):
        """Show the minimalist statistics HUD"""
        if self.hud_window is None:
            self.hud_window = tk.Toplevel(self.root)
            self.hud_window.title("Stats")
            self.hud_window.attributes('-topmost', True)
            self.hud_window.overrideredirect(True)
            self.hud_window.configure(bg='#141414')
            
            # Main container
            main_frame = tk.Frame(self.hud_window, bg='#141414', bd=1, relief='solid', 
                                 highlightbackground='#2a2a2a', highlightthickness=1)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Header with drag functionality
            header = tk.Frame(main_frame, bg='#1e1e1e', height=22)
            header.pack(fill=tk.X)
            header.pack_propagate(False)
            
            title = tk.Label(header, text="BPS Macro", font=("Segoe UI", 9, "bold"), 
                           fg="#f5f5f5", bg="#1e1e1e")
            title.pack(side=tk.LEFT, padx=8, pady=3)
            
            # Status dot
            self.hud_status_dot = tk.Label(header, text="●", font=("Arial", 8), 
                                          fg="#34d399", bg="#1e1e1e")
            self.hud_status_dot.pack(side=tk.RIGHT, padx=8)
            
            # Stats container
            stats = tk.Frame(main_frame, bg='#141414')
            stats.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
            
            # Row 1: Time and FPS
            row1 = tk.Frame(stats, bg='#141414')
            row1.pack(fill=tk.X, pady=1)
            self.hud_time_label = tk.Label(row1, text="00:00:00", 
                                          font=("Consolas", 11, "bold"), fg="#f5f5f5", bg="#141414")
            self.hud_time_label.pack(side=tk.LEFT)
            self.hud_fps_label = tk.Label(row1, text="0 FPS", 
                                         font=("Consolas", 9), fg="#606060", bg="#141414")
            self.hud_fps_label.pack(side=tk.RIGHT)
            
            # Row 2: Fish and Fruits
            row2 = tk.Frame(stats, bg='#141414')
            row2.pack(fill=tk.X, pady=2)
            self.hud_fish_label = tk.Label(row2, text="Fish: 0", 
                                          font=("Segoe UI", 10), fg="#a0a0a0", bg="#141414")
            self.hud_fish_label.pack(side=tk.LEFT)
            self.hud_fruits_label = tk.Label(row2, text="Fruits: 0", 
                                            font=("Segoe UI", 10), fg="#a0a0a0", bg="#141414")
            self.hud_fruits_label.pack(side=tk.RIGHT)
            
            # Row 3: Rates
            row3 = tk.Frame(stats, bg='#141414')
            row3.pack(fill=tk.X, pady=1)
            self.hud_fish_per_hour_label = tk.Label(row3, text="0/h", 
                                                    font=("Segoe UI", 9), fg="#606060", bg="#141414")
            self.hud_fish_per_hour_label.pack(side=tk.LEFT)
            self.hud_fruits_per_hour_label = tk.Label(row3, text="0/h", 
                                                      font=("Segoe UI", 9), fg="#606060", bg="#141414")
            self.hud_fruits_per_hour_label.pack(side=tk.RIGHT)
            
            # Separator
            sep = tk.Frame(stats, bg='#2a2a2a', height=1)
            sep.pack(fill=tk.X, pady=4)
            
            # V3.1: Estimated time to next fruit
            self.hud_estimate_label = tk.Label(stats, text="~Calculating...", 
                                              font=("Segoe UI", 9, "bold"), fg="#00ccff", bg="#141414",
                                              anchor='w')
            self.hud_estimate_label.pack(fill=tk.X)
            
            # Activity/Log label
            self.hud_activity_label = tk.Label(stats, text="Idle", 
                                              font=("Segoe UI", 9), fg="#a0a0a0", bg="#141414",
                                              anchor='w', wraplength=180)
            self.hud_activity_label.pack(fill=tk.X)
            
            # Position HUD
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            hud_width = 200
            hud_height = 150  # V3.1: Increased to fit estimate label
            
            if self.hud_position == 'top':
                x = (screen_width - hud_width) // 2
                y = 10
            elif self.hud_position == 'bottom-left':
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
            # Calculate elapsed time
            elapsed = time.time() - self.start_time
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            elapsed_hours = elapsed / 3600.0
            
            # Calculate rates
            fish_per_hour = int(self.fish_caught / elapsed_hours) if elapsed_hours > 0 else 0
            fruits_per_hour = int(self.fruits_caught / elapsed_hours) if elapsed_hours > 0 else 0
            
            # Update labels - clean format without emojis
            self.hud_time_label.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            self.hud_fish_label.config(text=f"Fish: {self.fish_caught}")
            self.hud_fruits_label.config(text=f"Fruits: {self.fruits_caught}")
            self.hud_fish_per_hour_label.config(text=f"{fish_per_hour}/h")
            self.hud_fruits_per_hour_label.config(text=f"{fruits_per_hour}/h")
            
            # Update status dot color
            if hasattr(self, 'hud_status_dot'):
                self.hud_status_dot.configure(fg="#34d399" if self.running else "#f87171")
            
            # Activity text - truncate if needed
            activity = self.current_status[:25] + "..." if len(self.current_status) > 25 else self.current_status
            self.hud_activity_label.configure(text=activity)
            
            # FPS - subtle
            if hasattr(self, 'hud_fps_label'):
                self.hud_fps_label.configure(text=f"{self.detection_fps:.0f} FPS")
            
            # Update main window activity
            if hasattr(self, 'activity_label'):
                self.activity_label.configure(text=f"Activity: {self.current_status}", 
                                            text_color=self.success_color if self.running else "#60a5fa")
            
            # V3.1: Update estimated time to next fruit
            self.update_estimated_time()
            
            # Next update in 1 second
            self.root.after(1000, self.update_hud)
    
    def toggle_always_on_top(self):
        """Toggle always on top"""
        self.always_on_top = self.always_on_top_var.get()
        self.root.attributes('-topmost', self.always_on_top)
        self.save_always_on_top()
    
    def toggle_sound_notification(self):
        """V3: Toggle sound notification for fruit detection"""
        self.sound_enabled = self.sound_enabled_var.get()
        self.save_sound_settings()
        logger.info(f"Sound notification {'enabled' if self.sound_enabled else 'disabled'}")
    
    def save_sound_settings(self):
        """V3: Save sound settings to settings file"""
        try:
            data = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
            
            data['sound_settings'] = {
                'sound_enabled': self.sound_enabled,
                'sound_frequency': self.sound_frequency,
                'sound_duration': self.sound_duration
            }
            
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving sound settings: {e}")
    
    def load_sound_settings(self):
        """V3: Load sound settings from settings file"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    sound_settings = data.get('sound_settings', {})
                    return {
                        'sound_enabled': sound_settings.get('sound_enabled', True),
                        'sound_frequency': sound_settings.get('sound_frequency', 400),
                        'sound_duration': sound_settings.get('sound_duration', 150)
                    }
        except Exception as e:
            logger.error(f"Error loading sound settings: {e}")
        return {'sound_enabled': True, 'sound_frequency': 400, 'sound_duration': 150}
    
    def play_notification_sound(self):
        """V3: Play notification sound (Custom or Beep)"""
        if not self.sound_enabled:
            return
            
        try:
            # Try to play custom sound with pygame
            if PYGAME_AVAILABLE and os.path.exists(AUDIO_FILE):
                try:
                    pygame.mixer.music.load(AUDIO_FILE)
                    pygame.mixer.music.play()
                    return
                except Exception as e:
                    logger.error(f"Error playing custom sound: {e}")
            
            # Fallback to system beep
            winsound.Beep(self.sound_frequency, self.sound_duration)
        except Exception as e:
            logger.error(f"Error playing sound: {e}")
    
    def toggle_auto_buy_bait(self):
        """Toggle auto buy bait section visibility"""
        # Check if trying to enable auto buy bait while auto craft is on
        if self.auto_buy_bait_var.get() and self.auto_craft_enabled:
            self.auto_buy_bait_var.set(False)
            self.info_label.configure(text="Cannot enable Auto Buy Bait! Auto Craft is active.", foreground=self.current_colors['error'])
            return
        
        self.auto_buy_bait = self.auto_buy_bait_var.get()
        if self.auto_buy_bait:
            # Pack after the warning label to maintain position
            self.auto_bait_section.pack(fill=tk.X, pady=5, padx=12, after=self.auto_bait_warning)
        else:
            self.auto_bait_section.pack_forget()
        self.save_precast_settings()
    
    def toggle_auto_store_fruit(self):
        """Toggle auto store fruit section visibility"""
        self.auto_store_fruit = self.auto_store_fruit_var.get()
        if self.auto_store_fruit:
            self.auto_fruit_section.pack(fill=tk.X, pady=5, padx=15, after=self.auto_fruit_checkbox)
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
        self.area_selector.attributes('-alpha', 0.3)
        self.area_selector.attributes('-fullscreen', True)
        self.area_selector.attributes('-topmost', True)
        self.area_selector.configure(bg='blue')
        self.area_selector.title("Select Inventory Fruit Point")
        
        # Label with instructions
        label = tk.Label(
            self.area_selector, 
            text="Click on the EMPTY SLOT in your inventory where you want the fruit to be", 
            font=("Arial", 24, "bold"), 
            fg="white", 
            bg="blue"
        )
        label.pack(expand=True)
        
        self.selecting_inventory_fruit_point = True
        
        def on_click(event):
            if self.selecting_inventory_fruit_point:
                self.inventory_fruit_point = {'x': event.x, 'y': event.y}
                self.inventory_fruit_point_label.configure(
                    text=f"({event.x}, {event.y})", 
                    text_color="#00dd00"
                )
                self.selecting_inventory_fruit_point = False
                self.save_precast_settings()
                self.area_selector.destroy()
                self.area_selector = None
                
                # Bring back main window
                self.root.deiconify()
                self.root.attributes('-topmost', True)
                if not self.always_on_top:
                     self.root.after(500, lambda: self.root.attributes('-topmost', False))
        
        self.area_selector.bind("<Button-1>", on_click)
        # Hide main window
        self.root.withdraw()
    
    def start_inventory_center_point_selection(self):
        """Start selecting inventory center point based on mouse click"""
        self.area_selector = tk.Toplevel(self.root)
        self.area_selector.attributes('-alpha', 0.3)
        self.area_selector.attributes('-fullscreen', True)
        self.area_selector.attributes('-topmost', True)
        self.area_selector.configure(bg='blue')
        self.area_selector.title("Select Center Point")
        
        # Label with instructions
        label = tk.Label(
            self.area_selector, 
            text="Click on the CENTER of the screen (or where you want to drop)", 
            font=("Arial", 24, "bold"), 
            fg="white", 
            bg="blue"
        )
        label.pack(expand=True)
        
        self.selecting_inventory_center_point = True
        
        def on_click(event):
            if self.selecting_inventory_center_point:
                self.inventory_center_point = {'x': event.x, 'y': event.y}
                self.inventory_center_point_label.configure(
                    text=f"({event.x}, {event.y})", 
                    text_color="#00dd00"
                )
                self.selecting_inventory_center_point = False
                self.save_precast_settings()
                self.area_selector.destroy()
                self.area_selector = None
                
                # Bring back main window
                self.root.deiconify()
                self.root.attributes('-topmost', True)
                if not self.always_on_top:
                     self.root.after(500, lambda: self.root.attributes('-topmost', False))
        
        self.area_selector.bind("<Button-1>", on_click)
        # Hide main window
        self.root.withdraw()
    
    def toggle_auto_select_top_bait(self):
        """Toggle auto select top bait section visibility"""
        self.auto_select_top_bait = self.auto_select_top_bait_var.get()
        if self.auto_select_top_bait:
            self.auto_top_bait_section.pack(fill=tk.X, pady=5, padx=15, after=self.auto_top_bait_checkbox)
        else:
            self.auto_top_bait_section.pack_forget()
        self.save_precast_settings()
    
    def load_hud_position(self):
        """Load HUD position from settings file"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get('hud_position', 'top')
        except:
            pass
        return 'top'
    
    def save_hud_position(self):
        """Save HUD position to settings file"""
        try:
            # Convert user-friendly name to internal format
            position_map = {
                'Top': 'top',
                'Bottom Left': 'bottom-left',
                'Bottom Right': 'bottom-right'
            }
            self.hud_position = position_map.get(self.hud_position_var.get(), 'top')
            data = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
            
            data['hud_position'] = self.hud_position
            
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f, indent=4)
            
            self.info_label.configure(text="✓ HUD position saved! Restart macro to apply.", text_color="#00dd00")
        except Exception as e:
            self.info_label.configure(text=f"❌ Error saving HUD position: {e}", text_color="#ff4444")
    
    def load_always_on_top(self):
        """Load always on top setting from settings file"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get('always_on_top', False)
        except:
            pass
        return False
    
    def save_always_on_top(self):
        """Save always on top setting to settings file"""
        try:
            data = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
            
            data['always_on_top'] = self.always_on_top
            
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f, indent=4)
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
                initialfile="bps_fishing_config_export.json"
            )
            
            if not filepath:
                return  # User cancelled
            
            # Copy current settings file to the selected location
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    config_data = json.load(f)
                
                # Add export metadata
                config_data['_export_info'] = {
                    'version': 'V3.1',
                    'exported_at': datetime.now().isoformat(),
                    'screen_resolution': f'{SCREEN_WIDTH}x{SCREEN_HEIGHT}'
                }
                
                with open(filepath, 'w') as f:
                    json.dump(config_data, f, indent=4)
                
                self.info_label.configure(text=f"✓ Config exported successfully!", text_color="#00dd00")
                logger.info(f"Config exported to: {filepath}")
            else:
                self.info_label.configure(text="❌ No settings file found to export!", text_color="#ff4444")
        except Exception as e:
            self.info_label.configure(text=f"❌ Export error: {e}", text_color="#ff4444")
            logger.error(f"Export config error: {e}")
    
    def import_config(self):
        """V3.1: Import settings from a user-selected file"""
        try:
            from tkinter import filedialog, messagebox
            
            # Open file dialog to choose file to import
            filepath = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Import Configuration"
            )
            
            if not filepath:
                return  # User cancelled
            
            # Read and validate the imported file
            with open(filepath, 'r') as f:
                imported_data = json.load(f)
            
            # Basic validation - check for some expected keys
            expected_keys = ['area_coords', 'water_point', 'casting_settings']
            valid_keys_found = sum(1 for key in expected_keys if key in imported_data)
            
            if valid_keys_found == 0:
                self.info_label.configure(text="❌ Invalid config file!", text_color="#ff4444")
                return
            
            # Confirm with user
            if not messagebox.askyesno("Import Configuration", 
                f"Import configuration from '{os.path.basename(filepath)}'?\n\n" +
                "This will overwrite your current settings.\n" +
                "The application will need to restart to apply all changes."):
                return
            
            # Remove export metadata before saving
            if '_export_info' in imported_data:
                del imported_data['_export_info']
            
            # Write to settings file
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(imported_data, f, indent=4)
            
            self.info_label.configure(text="✓ Config imported! Restart to apply.", text_color="#00dd00")
            logger.info(f"Config imported from: {filepath}")
            
            # Ask to restart
            if messagebox.askyesno("Restart Required", "Restart application now to apply imported settings?"):
                self.on_closing()
                
        except json.JSONDecodeError:
            self.info_label.configure(text="❌ Invalid JSON file!", text_color="#ff4444")
        except Exception as e:
            self.info_label.configure(text=f"❌ Import error: {e}", text_color="#ff4444")
            logger.error(f"Import config error: {e}")
    
    def update_estimated_time(self):
        """V3.1: Update the estimated time to next fruit label"""
        try:
            if not hasattr(self, 'estimate_label'):
                return
            
            # Get historical data from database
            if stats_manager:
                historical = stats_manager.get_historical(7)  # Last 7 days
                
                total_fish = sum(d['fish'] for d in historical)
                total_fruits = sum(d['fruits'] for d in historical)
                
                # Calculate average fish per fruit
                if total_fruits > 0:
                    avg_fish_per_fruit = total_fish / total_fruits
                else:
                    avg_fish_per_fruit = 700  # Default estimate if no data
                
                # Calculate current session progress
                session_fish = self.fish_caught if hasattr(self, 'fish_caught') else 0
                fish_at_last = self.fish_at_last_fruit if hasattr(self, 'fish_at_last_fruit') else 0
                
                # Calculate progress relative to LAST FRUIT caught event
                fish_since_last_fruit = session_fish - fish_at_last
                remaining_fish = max(0, int(avg_fish_per_fruit) - fish_since_last_fruit)
                
                # Calculate fish per hour from current session
                if hasattr(self, 'start_time') and self.start_time:
                    elapsed_hours = (time.time() - self.start_time) / 3600.0
                    fish_per_hour = session_fish / elapsed_hours if elapsed_hours > 0.01 else 0
                else:
                    fish_per_hour = 0
                
                # Estimate time remaining
                if fish_per_hour > 0:
                    hours_remaining = remaining_fish / fish_per_hour
                    hours = int(hours_remaining)
                    minutes = int((hours_remaining - hours) * 60)
                    
                    if hours > 0:
                        estimate_text = f"~{hours}h {minutes}m"
                    else:
                        estimate_text = f"~{minutes}m"
                    
                    detail_text = f"Avg: {int(avg_fish_per_fruit)} fish/fruit | {int(fish_per_hour)}/h | {remaining_fish} fish to go"
                    hud_text = f"🍎 {estimate_text} ({remaining_fish} fish)"
                else:
                    estimate_text = "Calculating..."
                    detail_text = f"Avg: {int(avg_fish_per_fruit)} fish/fruit (from history)"
                    hud_text = "🍎 Calculating..."
                
                # Update Stats tab labels
                self.estimate_label.configure(text=estimate_text)
                self.estimate_detail_label.configure(text=detail_text)
                
                # V3.1: Update mini HUD label
                if hasattr(self, 'hud_estimate_label') and self.hud_estimate_label:
                    self.hud_estimate_label.configure(text=hud_text)
            else:
                self.estimate_label.configure(text="No data yet")
                self.estimate_detail_label.configure(text="Start fishing to collect data")
                if hasattr(self, 'hud_estimate_label') and self.hud_estimate_label:
                    self.hud_estimate_label.configure(text="🍎 No data")
                
        except Exception as e:
            logger.error(f"Error updating estimated time: {e}")
    
    def load_item_hotkeys(self):
        """Load item hotkeys from settings file"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get('item_hotkeys', {'rod': '1', 'everything_else': '2', 'fruit': '3'})
        except:
            pass
        return {'rod': '1', 'everything_else': '2', 'fruit': '3'}
    
    def save_item_hotkeys(self):
        """Save item hotkeys to settings file"""
        try:
            self.rod_hotkey = self.rod_hotkey_var.get()
            self.everything_else_hotkey = self.everything_else_hotkey_var.get()
            self.fruit_hotkey = self.fruit_hotkey_var.get()
            
            data = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
            
            data['item_hotkeys'] = {
                'rod': self.rod_hotkey,
                'everything_else': self.everything_else_hotkey,
                'fruit': self.fruit_hotkey
            }
            
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f, indent=4)
            
            self.info_label.configure(text="✓ Item hotkeys saved!", text_color=self.current_colors['success'])
        except Exception as e:
            self.info_label.configure(text=f"❌ Error saving item hotkeys: {e}", text_color=self.current_colors['error'])
    
    def load_water_point(self):
        """Load water point coordinates from settings file"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get('water_point', get_default_coords()['water_point'])
        except:
            pass
        return get_default_coords()['water_point']
    
    def load_pid_settings(self):
        """Load PID settings from settings file"""
        default_pid = {'kp': 1.0, 'kd': 0.3, 'clamp': 1.0}
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get('pid_settings', default_pid)
        except:
            pass
        return default_pid
    
    def load_advanced_settings(self):
        """Load advanced timing settings from settings file"""
        default_advanced = {
            # Camera rotation delays
            'camera_rotation_delay': 0.05,
            'camera_rotation_steps': 8,
            'camera_rotation_step_delay': 0.05,
            'camera_rotation_settle_delay': 0.3,
            # Zoom delays
            'zoom_ticks': 3,
            'zoom_tick_delay': 0.05,
            'zoom_settle_delay': 0.3,
            # Pre-cast delays
            'pre_cast_minigame_wait': 2.5,
            'store_click_delay': 1.0,
            'backspace_delay': 0.3,
            'rod_deselect_delay': 0.5,
            'rod_select_delay': 0.5,
            'bait_click_delay': 0.3,
            # Detection & general delays
            'fruit_detection_delay': 0.02,
            'fruit_detection_settle': 0.3,
            'general_action_delay': 0.05,
            'mouse_move_settle': 0.05,
            # Focus settle delay after bringing Roblox to foreground
            'focus_settle_delay': 1.0,
            # Disable camera/zoom/rotation in normal mode (not Auto Craft)
            'disable_normal_camera': True  # Default: True (simplified mode)
        }
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get('advanced_settings', default_advanced)
        except:
            pass
        return default_advanced
    
    def save_disable_normal_camera(self):
        """Save disable_normal_camera setting to settings file"""
        self.disable_normal_camera = self.disable_normal_camera_var.get()
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
            else:
                data = {}
            
            if 'advanced_settings' not in data:
                data['advanced_settings'] = {}
            
            data['advanced_settings']['disable_normal_camera'] = self.disable_normal_camera
            
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f, indent=4)
            
            if self.disable_normal_camera:
                self.info_label.configure(text="OK: Camera/zoom/rotation DISABLED in normal mode!", text_color="#00dd00")
            else:
                self.info_label.configure(text="OK: Camera/zoom/rotation ENABLED in normal mode!", text_color="#00dd00")
        except Exception as e:
            self.info_label.configure(text=f"Error saving: {e}", text_color="#ff4444")
    
    def load_casting_settings(self):
        """Load casting settings from settings file"""
        default_casting = {'cast_hold_duration': 1.0, 'recast_timeout': 30.0, 'fishing_end_delay': 1.5}
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get('casting_settings', default_casting)
        except:
            pass
        return default_casting
    
    def load_precast_settings(self):
        """Load precast settings from settings file"""
        defaults = get_default_coords()
        default_precast = {
            'auto_buy_bait': True, 
            'auto_store_fruit': True,
            'yes_button': defaults['yes_button'],
            'middle_button': defaults['middle_button'],
            'no_button': defaults['no_button'],
            'loops_per_purchase': 100,
            'fruit_point': defaults['fruit_point'],
            'fruit_color': [7, 116, 45],
            'auto_select_top_bait': True,
            'top_bait_point': defaults['top_bait_point'],
            'store_in_inventory': False,
            'inventory_fruit_point': None,
            'inventory_center_point': None
        }
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get('precast_settings', default_precast)
        except:
            pass
        return default_precast
    
    def save_precast_settings(self):
        """Save precast settings to settings file"""
        try:
            data = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
            
            data['precast_settings'] = {
                'auto_buy_bait': self.auto_buy_bait,
                'auto_store_fruit': self.auto_store_fruit,
                'yes_button': self.yes_button,
                'middle_button': self.middle_button,
                'no_button': self.no_button,
                'loops_per_purchase': self.loops_per_purchase,
                'fruit_point': self.fruit_point,
                'fruit_color': self.fruit_color,
                'auto_select_top_bait': self.auto_select_top_bait,
                'top_bait_point': self.top_bait_point,
                'store_in_inventory': self.store_in_inventory,
                'inventory_fruit_point': self.inventory_fruit_point,
                'inventory_center_point': self.inventory_center_point
            }
            
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving precast settings: {e}")
    
    def load_auto_craft_settings(self):
        """Load auto craft settings from settings file"""
        default_auto_craft = {
            'auto_craft_enabled': False,
            'auto_craft_water_point': None,
            'craft_every_n_fish': 10,
            'craft_menu_delay': 0.5,
            'craft_click_speed': 0.2,
            'craft_legendary_quantity': 1,
            'craft_rare_quantity': 1,
            'craft_common_quantity': 1,
            'craft_button_coords': None,
            'plus_button_coords': None,
            'fish_icon_coords': None,
            'legendary_bait_coords': None,
            'rare_bait_coords': None,
            'common_bait_coords': None
        }
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get('auto_craft_settings', default_auto_craft)
        except:
            pass
        return default_auto_craft
    
    def save_loops_setting(self):
        """Save loops per purchase setting"""
        try:
            self.loops_per_purchase = int(self.loops_entry.get())
            self.save_precast_settings()
            self.info_label.configure(text="✓ Loops per purchase saved!", foreground=self.current_colors['success'])
        except ValueError:
            self.info_label.configure(text="❌ Invalid value! Use numbers only.", foreground=self.current_colors['error'])
    
    def save_water_point(self):
        """Save water point coordinates to settings file"""
        try:
            data = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
            
            data['water_point'] = self.water_point
            
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving water_point: {e}")
    
    def save_pid_settings(self):
        """Save PID settings to settings file"""
        try:
            data = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
            
            data['pid_settings'] = {
                'kp': self.pid_kp,
                'kd': self.pid_kd,
                'clamp': self.pid_clamp
            }
            
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f, indent=4)
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
            self.info_label.configure(text="❌ Invalid PD values! Use numbers only.", text_color="#ff4444")
    
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
            self.camera_rotation_step_delay = float(self.camera_rotation_step_delay_entry.get())
            self.camera_rotation_settle_delay = float(self.camera_rotation_settle_delay_entry.get())
            
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

            # Save to file
            data = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)

            data['advanced_settings'] = {
                'camera_rotation_delay': self.camera_rotation_delay,
                'camera_rotation_steps': self.camera_rotation_steps,
                'camera_rotation_step_delay': self.camera_rotation_step_delay,
                'camera_rotation_settle_delay': self.camera_rotation_settle_delay,
                'zoom_ticks': self.zoom_ticks,
                'zoom_tick_delay': self.zoom_tick_delay,
                'zoom_settle_delay': self.zoom_settle_delay,
                'pre_cast_minigame_wait': self.pre_cast_minigame_wait,
                'store_click_delay': self.store_click_delay,
                'backspace_delay': self.backspace_delay,
                'rod_deselect_delay': self.rod_deselect_delay,
                'rod_select_delay': self.rod_select_delay,
                'bait_click_delay': self.bait_click_delay,
                'fruit_detection_delay': self.fruit_detection_delay,
                'fruit_detection_settle': self.fruit_detection_settle,
                'general_action_delay': self.general_action_delay,
                'mouse_move_settle': self.mouse_move_settle,
                'focus_settle_delay': self.focus_settle_delay,
                'disable_normal_camera': self.disable_normal_camera_var.get()
            }

            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f, indent=4)

            self.info_label.configure(text="✓ Advanced settings saved!", foreground=self.current_colors['success'])
        except ValueError:
            self.info_label.configure(text="❌ Invalid values! Use numbers only.", foreground=self.current_colors['error'])
        except Exception as e:
            self.info_label.configure(text=f"❌ Error saving: {e}", foreground=self.current_colors['error'])
    
    def reset_advanced_settings(self):
        """Reset all advanced settings to default values"""
        # Set defaults
        defaults = {
            'camera_rotation_delay': 0.05,
            'camera_rotation_steps': 8,
            'camera_rotation_step_delay': 0.05,
            'camera_rotation_settle_delay': 0.3,
            'zoom_ticks': 3,
            'zoom_tick_delay': 0.05,
            'zoom_settle_delay': 0.3,
            'pre_cast_minigame_wait': 2.5,
            'store_click_delay': 1.0,
            'backspace_delay': 0.3,
            'rod_deselect_delay': 0.5,
            'rod_select_delay': 0.5,
            'bait_click_delay': 0.3,
            'fruit_detection_delay': 0.02,
            'fruit_detection_settle': 0.3,
            'general_action_delay': 0.05,
            'mouse_move_settle': 0.05,
            'focus_settle_delay': 1.0
        }
        
        # Update instance variables
        self.camera_rotation_delay = defaults['camera_rotation_delay']
        self.camera_rotation_steps = defaults['camera_rotation_steps']
        self.camera_rotation_step_delay = defaults['camera_rotation_step_delay']
        self.camera_rotation_settle_delay = defaults['camera_rotation_settle_delay']
        self.zoom_ticks = defaults['zoom_ticks']
        self.zoom_tick_delay = defaults['zoom_tick_delay']
        self.zoom_settle_delay = defaults['zoom_settle_delay']
        self.pre_cast_minigame_wait = defaults['pre_cast_minigame_wait']
        self.store_click_delay = defaults['store_click_delay']
        self.backspace_delay = defaults['backspace_delay']
        self.rod_deselect_delay = defaults['rod_deselect_delay']
        self.rod_select_delay = defaults['rod_select_delay']
        self.bait_click_delay = defaults['bait_click_delay']
        self.fruit_detection_delay = defaults['fruit_detection_delay']
        self.fruit_detection_settle = defaults['fruit_detection_settle']
        self.general_action_delay = defaults['general_action_delay']
        self.mouse_move_settle = defaults['mouse_move_settle']
        
        # Update UI fields
        self.camera_rotation_delay_entry.delete(0, tk.END)
        self.camera_rotation_delay_entry.insert(0, str(defaults['camera_rotation_delay']))
        
        self.camera_rotation_steps_entry.delete(0, tk.END)
        self.camera_rotation_steps_entry.insert(0, str(defaults['camera_rotation_steps']))
        
        self.camera_rotation_step_delay_entry.delete(0, tk.END)
        self.camera_rotation_step_delay_entry.insert(0, str(defaults['camera_rotation_step_delay']))
        
        self.camera_rotation_settle_delay_entry.delete(0, tk.END)
        self.camera_rotation_settle_delay_entry.insert(0, str(defaults['camera_rotation_settle_delay']))
        
        self.zoom_ticks_entry.delete(0, tk.END)
        self.zoom_ticks_entry.insert(0, str(defaults['zoom_ticks']))
        
        self.zoom_tick_delay_entry.delete(0, tk.END)
        self.zoom_tick_delay_entry.insert(0, str(defaults['zoom_tick_delay']))
        
        self.zoom_settle_delay_entry.delete(0, tk.END)
        self.zoom_settle_delay_entry.insert(0, str(defaults['zoom_settle_delay']))
        
        self.pre_cast_minigame_wait_entry.delete(0, tk.END)
        self.pre_cast_minigame_wait_entry.insert(0, str(defaults['pre_cast_minigame_wait']))
        
        self.store_click_delay_entry.delete(0, tk.END)
        self.store_click_delay_entry.insert(0, str(defaults['store_click_delay']))
        
        self.backspace_delay_entry.delete(0, tk.END)
        self.backspace_delay_entry.insert(0, str(defaults['backspace_delay']))
        
        self.rod_deselect_delay_entry.delete(0, tk.END)
        self.rod_deselect_delay_entry.insert(0, str(defaults['rod_deselect_delay']))
        
        self.rod_select_delay_entry.delete(0, tk.END)
        self.rod_select_delay_entry.insert(0, str(defaults['rod_select_delay']))
        
        self.bait_click_delay_entry.delete(0, tk.END)
        self.bait_click_delay_entry.insert(0, str(defaults['bait_click_delay']))
        
        self.fruit_detection_delay_entry.delete(0, tk.END)
        self.fruit_detection_delay_entry.insert(0, str(defaults['fruit_detection_delay']))
        
        self.fruit_detection_settle_entry.delete(0, tk.END)
        self.fruit_detection_settle_entry.insert(0, str(defaults['fruit_detection_settle']))
        
        self.general_action_delay_entry.delete(0, tk.END)
        self.general_action_delay_entry.insert(0, str(defaults['general_action_delay']))
        
        self.mouse_move_settle_entry.delete(0, tk.END)
        self.mouse_move_settle_entry.insert(0, str(defaults['mouse_move_settle']))

        # Update UI fields - Focus settle delay
        self.focus_settle_delay_entry.delete(0, tk.END)
        self.focus_settle_delay_entry.insert(0, str(defaults['focus_settle_delay']))
        
        # Update casting fields
        defaults['cast_hold_duration'] = 1.0
        defaults['recast_timeout'] = 30.0
        defaults['fishing_end_delay'] = 2.0
        defaults['pid_kp'] = 1.0
        defaults['pid_kd'] = 0.3
        defaults['pid_clamp'] = 1.0
        
        self.cast_hold_duration = defaults['cast_hold_duration']
        self.recast_timeout = defaults['recast_timeout']
        self.fishing_end_delay = defaults['fishing_end_delay']
        self.pid_kp = defaults['pid_kp']
        self.pid_kd = defaults['pid_kd']
        self.pid_clamp = defaults['pid_clamp']
        
        self.cast_hold_entry.delete(0, tk.END)
        self.cast_hold_entry.insert(0, str(defaults['cast_hold_duration']))
        
        self.recast_timeout_entry.delete(0, tk.END)
        self.recast_timeout_entry.insert(0, str(defaults['recast_timeout']))
        
        self.fishing_end_delay_entry.delete(0, tk.END)
        self.fishing_end_delay_entry.insert(0, str(defaults['fishing_end_delay']))
        
        self.kp_entry.delete(0, tk.END)
        self.kp_entry.insert(0, str(defaults['pid_kp']))
        
        self.kd_entry.delete(0, tk.END)
        self.kd_entry.insert(0, str(defaults['pid_kd']))
        
        self.clamp_entry.delete(0, tk.END)
        self.clamp_entry.insert(0, str(defaults['pid_clamp']))
        
        # Save to file
        try:
            data = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
            
            data['advanced_settings'] = {k: v for k, v in defaults.items() if k not in ['cast_hold_duration', 'recast_timeout', 'fishing_end_delay', 'pid_kp', 'pid_kd', 'pid_clamp']}
            
            data['casting_settings'] = {
                'cast_hold_duration': defaults['cast_hold_duration'],
                'recast_timeout': defaults['recast_timeout'],
                'fishing_end_delay': defaults['fishing_end_delay']
            }
            
            data['pid_settings'] = {
                'kp': defaults['pid_kp'],
                'kd': defaults['pid_kd'],
                'clamp': defaults['pid_clamp']
            }
            
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f, indent=4)
            
            self.info_label.configure(text="✓ All settings reset to default!", foreground=self.current_colors['success'])
        except Exception as e:
            self.info_label.configure(text=f"❌ Error resetting: {e}", foreground=self.current_colors['error'])
    
    def load_webhook_settings(self):
        """Load webhook settings from JSON"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get('webhook_settings', {'webhook_url': '', 'user_id': ''})
        except:
            pass
        return {'webhook_url': '', 'user_id': ''}
    
    def save_webhook_settings_ui(self):
        """Save webhook settings from UI entries"""
        try:
            webhook_url = self.webhook_url_entry.get().strip()
            user_id = self.user_id_entry.get().strip()
            
            if not webhook_url or not user_id:
                self.info_label.configure(text="❌ Webhook URL and User ID cannot be empty!", foreground=self.current_colors['error'])
                return
            
            # Save to JSON
            data = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
            
            data['webhook_settings'] = {
                'webhook_url': webhook_url,
                'user_id': user_id
            }
            
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f, indent=4)
            
            self.info_label.configure(text="✓ Webhook settings saved!", foreground=self.current_colors['success'])
        except Exception as e:
            self.info_label.configure(text=f"❌ Error saving webhook: {e}", foreground=self.current_colors['error'])
    
    def test_webhook(self):
        """Test Discord webhook by sending a test message"""
        try:
            import requests
            
            webhook_url = self.webhook_url_entry.get().strip()
            user_id = self.user_id_entry.get().strip()
            
            if not webhook_url or not user_id:
                self.info_label.configure(text="❌ Please enter Webhook URL and User ID first!", foreground=self.current_colors['error'])
                return
            
            # Send test message
            data = {
                "content": f"<@{user_id}> Test message from BPS Fishing Macro! ✅"
            }
            
            response = requests.post(webhook_url, json=data)
            
            if response.status_code == 204:
                self.info_label.configure(text="✓ Test message sent successfully!", foreground=self.current_colors['success'])
            else:
                self.info_label.configure(text=f"❌ Webhook error: {response.status_code}", foreground=self.current_colors['error'])
        except ImportError:
            self.info_label.configure(text="❌ requests library not installed! Run: pip install requests", foreground=self.current_colors['error'])
        except Exception as e:
            self.info_label.configure(text=f"❌ Error testing webhook: {e}", foreground=self.current_colors['error'])
    
    def save_casting_settings(self):
        """Save casting settings to settings file"""
        try:
            data = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
            
            data['casting_settings'] = {
                'cast_hold_duration': self.cast_hold_duration,
                'recast_timeout': self.recast_timeout,
                'fishing_end_delay': self.fishing_end_delay
            }
            
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving casting settings: {e}")
    
    def save_casting_from_ui(self):
        """Save casting settings from UI entries"""
        try:
            self.cast_hold_duration = float(self.cast_hold_entry.get())
            self.recast_timeout = float(self.recast_timeout_entry.get())
            self.fishing_end_delay = float(self.fishing_end_delay_entry.get())
            self.save_casting_settings()
            self.info_label.configure(text="✓ Casting settings saved!", foreground=self.current_colors['success'])
        except ValueError:
            self.info_label.configure(text="❌ Invalid casting values! Use numbers only.", foreground=self.current_colors['error'])
    
    def start_water_point_selection(self):
        """Start water point selection mode with overlay"""
        self.selecting_water_point = True
        self.water_point_button.configure(text="Waiting... (Right-Click)")
        self.water_point_label.configure(text="RIGHT-CLICK on water target", text_color=self.current_colors['warning'])
        
        # Show overlay popup
        self._show_coord_selection_overlay()
        
        # Cleanup old listener
        try:
            if hasattr(self, 'mouse_listener') and self.mouse_listener:
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
                self.water_point = {'x': x, 'y': y}
                self.save_water_point()
                self.selecting_water_point = False

                # Update UI
                self.water_point_button.configure(text="Select")
                self.water_point_label.configure(text=f"({x}, {y})", text_color="#00dd00")

                print(f"[Water Point] ✓ Saved: ({x}, {y})")

                # Close overlay if exists
                try:
                    if hasattr(self, 'coord_selection_overlay'):
                        self.coord_selection_overlay.destroy()
                except:
                    pass

                # Stop mouse listener
                try:
                    if hasattr(self, 'mouse_listener') and self.mouse_listener:
                        self.mouse_listener.stop()
                except:
                    pass
        self.save_always_on_top()
    
    def start_auto_craft_water_point_selection(self):
        """Start auto craft water point selection mode with overlay"""
        self.selecting_auto_craft_water_point = True
        self.auto_craft_water_point_button.configure(text="Waiting... (Right-Click)", fg_color="#ff6600")
        self.auto_craft_water_point_label.configure(text="RIGHT-CLICK on auto craft water target", text_color="#ffaa00")
        
        # Show overlay popup
        self._show_coord_selection_overlay()
        
        # Cleanup old listener
        try:
            if hasattr(self, 'mouse_listener') and self.mouse_listener:
                self.mouse_listener.stop()
        except:
            pass
        
        # Start mouse listener in background
        self.mouse_listener = MouseListener(on_click=self.on_mouse_click_auto_craft_water_point)
        self.mouse_listener.start()
    
    def on_mouse_click_auto_craft_water_point(self, x, y, button, pressed):
        """Handle mouse clicks during auto craft water point selection"""
        if not self.selecting_auto_craft_water_point:
            return
        
        if pressed:
            if button == Button.right:
                # Right click - save the auto craft water point
                self.auto_craft_water_point = {'x': x, 'y': y}
                self.save_auto_craft_water_point()
                self.selecting_auto_craft_water_point = False
                
                # Update UI
                self.auto_craft_water_point_button.configure(text="Select", fg_color=self.button_color)
                self.auto_craft_water_point_label.configure(text=f"({x}, {y})", text_color="#00dd00")
                
                print(f"[Auto Craft Water] ✓ Saved: ({x}, {y})")
                
                # Close overlay if exists
                try:
                    if hasattr(self, 'coord_selection_overlay'):
                        self.coord_selection_overlay.destroy()
                except:
                    pass
                
                # Stop mouse listener
                try:
                    if hasattr(self, 'mouse_listener') and self.mouse_listener:
                        self.mouse_listener.stop()
                except:
                    pass
    
    def save_auto_craft_water_point(self):
        """Save auto craft water point coordinates to settings file"""
        try:
            data = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
            
            # Get existing auto_craft_settings or create new
            auto_craft_settings = data.get('auto_craft_settings', {})
            auto_craft_settings['auto_craft_water_point'] = self.auto_craft_water_point
            data['auto_craft_settings'] = auto_craft_settings
            
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving auto craft water point: {e}")
    
    def save_craft_settings_from_ui(self):
        """Save craft settings from UI entries"""
        try:
            self.craft_every_n_fish = int(self.craft_every_n_fish_entry.get())
            self.craft_menu_delay = float(self.craft_menu_delay_entry.get())
            self.craft_click_speed = float(self.craft_click_speed_entry.get())
            self.craft_legendary_quantity = int(self.craft_legendary_quantity_entry.get())
            self.craft_rare_quantity = int(self.craft_rare_quantity_entry.get())
            self.craft_common_quantity = int(self.craft_common_quantity_entry.get())
            
            self.save_auto_craft_settings()
            self.info_label.configure(text="✓ Craft settings saved!", text_color="#00dd00")
        except ValueError:
            self.info_label.configure(text="❌ Invalid values! Use numbers only.", text_color="#ff4444")
    
    def start_auto_craft_coord_selection(self, coord_name):
        """Start coordinate selection mode for auto craft with popup overlay"""
        self.selecting_auto_craft_coord = coord_name
        
        # Update button text based on coordinate type
        button_map = {
            'craft_button_coords': (self.craft_button_btn, self.craft_button_label),
            'plus_button_coords': (self.plus_button_btn, self.plus_button_label),
            'fish_icon_coords': (self.fish_icon_btn, self.fish_icon_label),
            'legendary_bait_coords': (self.legendary_bait_btn, self.legendary_bait_label),
            'rare_bait_coords': (self.rare_bait_btn, self.rare_bait_label),
            'common_bait_coords': (self.common_bait_btn, self.common_bait_label)
        }
        
        if coord_name in button_map:
            btn, label = button_map[coord_name]
            btn.configure(text="Waiting...", fg_color="#ff6600")
            label.configure(text="Right-click on target in-game", text_color="#ffaa00")
        
        # Show overlay popup
        self._show_coord_selection_overlay()
        
        # Start mouse listener
        try:
            if hasattr(self, 'mouse_listener') and self.mouse_listener:
                self.mouse_listener.stop()
        except:
            pass
        
        self.mouse_listener = MouseListener(on_click=self.on_mouse_click_auto_craft_coord)
        self.mouse_listener.start()
    
    def _show_coord_selection_overlay(self):
        """Show a transparent overlay popup during coordinate selection"""
        try:
            # Create transparent overlay window
            overlay = tk.Toplevel(self.root)
            overlay.overrideredirect(True)  # Remove title bar and borders
            overlay.attributes('-alpha', 0.01)
            overlay.attributes('-topmost', True)
            overlay.geometry(f"{SCREEN_WIDTH}x{SCREEN_HEIGHT}+0+0")

            # Allow closing with ESC
            def on_esc(event=None):
                self._cancel_coord_selection()
                overlay.destroy()
            
            overlay.bind('<Escape>', on_esc)
            
            # Store reference to cleanup
            self.coord_selection_overlay = overlay
        except Exception as e:
            print(f"[Coord Select] Could not create overlay: {e}")
    
    def _cancel_coord_selection(self):
        """Cancel coordinate selection"""
        self.selecting_auto_craft_coord = None
        try:
            if hasattr(self, 'mouse_listener') and self.mouse_listener:
                self.mouse_listener.stop()
        except:
            pass
    
    def on_mouse_click_auto_craft_coord(self, x, y, button, pressed):
        """Handle mouse clicks during auto craft coordinate selection"""
        if not self.selecting_auto_craft_coord:
            return
        
        if pressed and button == Button.right:
            coord_name = self.selecting_auto_craft_coord
            coord_value = {'x': x, 'y': y}
            
            # Save coordinate
            setattr(self, coord_name, coord_value)
            self.save_auto_craft_settings()
            
            # Update UI
            button_map = {
                'craft_button_coords': (self.craft_button_btn, self.craft_button_label),
                'plus_button_coords': (self.plus_button_btn, self.plus_button_label),
                'fish_icon_coords': (self.fish_icon_btn, self.fish_icon_label),
                'legendary_bait_coords': (self.legendary_bait_btn, self.legendary_bait_label),
                'rare_bait_coords': (self.rare_bait_btn, self.rare_bait_label),
                'common_bait_coords': (self.common_bait_btn, self.common_bait_label)
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
                if hasattr(self, 'mouse_listener') and self.mouse_listener:
                    self.mouse_listener.stop()
            except:
                pass
            
            # Close overlay if exists
            try:
                if hasattr(self, 'coord_selection_overlay'):
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
            print(f"\r[Auto Craft] ⚒️ Starting crafting sequence...", end='', flush=True)
            

            
            # Initialize keyboard controller
            kb = Controller()
            
            # Step 0: Deselect rod (press rod hotkey)
            print(f"\r[Auto Craft] Deselecting rod ({self.rod_hotkey})...", end='', flush=True)
            kb.press(self.rod_hotkey)
            kb.release(self.rod_hotkey)
            time.sleep(0.3)
            
            # Wait for menu to open
            menu_delay = self.craft_menu_delay / 1000.0 if self.craft_menu_delay < 100 else self.craft_menu_delay
            print(f"\r[Auto Craft] Waiting {menu_delay:.2f}s for menu to open...", end='', flush=True)
            time.sleep(menu_delay)
            
            # Convert click speed (in ms to seconds)
            click_delay = self.craft_click_speed / 1000.0 if self.craft_click_speed < 100 else self.craft_click_speed
            
            # OCR removido do V2.7
            ocr_leg = 0
            ocr_rare = 0
            ocr_common = 0
            
            # Define bait types to craft in order: Common → Rare → Legendary (prevents overflow)
            baits_to_craft = [
                ('Common', self.common_bait_coords, self.craft_common_quantity, ocr_common),
                ('Rare', self.rare_bait_coords, self.craft_rare_quantity, ocr_rare),
                ('Legendary', self.legendary_bait_coords, self.craft_legendary_quantity, ocr_leg)
            ]
            
            for bait_name, bait_coords, quantity, current_count in baits_to_craft:
                if not self.running:
                    break
                    
                if quantity <= 0:
                    continue
                
                # Overflow protection: skip crafting if already at 280+ baits
                if current_count >= 280:
                    print(f"\r[Auto Craft] ⚠️ {bait_name} at {current_count}/280 baits. Skipping craft to prevent overflow...", end='', flush=True)
                    continue
                
                if not bait_coords:
                    print(f"\r[Auto Craft] ⚠️ {bait_name} bait coords not set, skipping...", end='', flush=True)
                    continue
                
                print(f"\r[Auto Craft] Crafting {quantity}x {bait_name} bait (current: {current_count}/280)...", end='', flush=True)
                
                # Validate all coords before starting
                if not self.plus_button_coords:
                    print(f"\r[Auto Craft] ⚠️ Plus button coords not set! Skipping {bait_name}...", end='', flush=True)
                    continue
                if not self.fish_icon_coords:
                    print(f"\r[Auto Craft] ⚠️ Fish icon coords not set! Skipping {bait_name}...", end='', flush=True)
                    continue
                if not self.craft_button_coords:
                    print(f"\r[Auto Craft] ⚠️ Craft button coords not set! Skipping {bait_name}...", end='', flush=True)
                    continue
                
                # Step 1: Click Bait Icon (ONCE - for the entire quantity)
                print(f"\r[AC] {bait_name}: Clicking bait icon at ({bait_coords['x']}, {bait_coords['y']})...", end='', flush=True)
                self.simulate_click(bait_coords['x'], bait_coords['y'], hold_delay=0.1)
                time.sleep(click_delay)
                
                # Process quantity in batches of 40 (max 40 fish per session)
                remaining = quantity
                batch_num = 1
                while remaining > 0:
                    batch_size = min(40, remaining)  # Max 40 per batch
                    
                    # Step 2: Click Plus Button (once per batch)
                    print(f"\r[AC] {bait_name} Batch {batch_num}: Clicking plus button at ({self.plus_button_coords['x']}, {self.plus_button_coords['y']})...", end='', flush=True)
                    self.simulate_click(self.plus_button_coords['x'], self.plus_button_coords['y'], hold_delay=0.1)
                    time.sleep(click_delay)
                    
                    # Step 3: Click Fish Icon (once per batch)
                    print(f"\r[AC] {bait_name} Batch {batch_num}: Clicking fish icon at ({self.fish_icon_coords['x']}, {self.fish_icon_coords['y']})...", end='', flush=True)
                    self.simulate_click(self.fish_icon_coords['x'], self.fish_icon_coords['y'], hold_delay=0.1)
                    time.sleep(click_delay)
                    
                    # Step 4: Click Craft Button (batch_size times)
                    for q in range(batch_size):
                        if not self.running:
                            break
                        print(f"\r[AC] {bait_name} Batch {batch_num}: Clicking craft button {q+1}/{batch_size}...", end='', flush=True)
                        self.simulate_click(self.craft_button_coords['x'], self.craft_button_coords['y'], hold_delay=0.1)
                        time.sleep(click_delay)
                    
                    remaining -= batch_size
                    batch_num += 1
                    
                    if remaining > 0:
                        print(f"\r[AC] {bait_name}: {remaining} remaining, preparing next batch...", end='', flush=True)
            
            print(f"\r[Auto Craft] ✅ Crafting sequence completed successfully!", end='', flush=True)
            
        except Exception as e:
            print(f"\r[Auto Craft] ❌ Error during crafting: {str(e)}", end='', flush=True)



    
    def start_button_selection(self, button_type):
        """Start button position selection mode"""
        self.selecting_button = button_type
        
        # Update UI based on button type
        if button_type == 'yes':
            self.yes_button_btn.configure(text="Waiting... (Right-Click)")
            self.yes_button_label.configure(text="RIGHT-CLICK on Yes button", text_color=self.current_colors['warning'])
        elif button_type == 'middle':
            self.middle_button_btn.configure(text="Waiting... (Right-Click)")
            self.middle_button_label.configure(text="RIGHT-CLICK on Middle button", text_color=self.current_colors['warning'])
        elif button_type == 'no':
            self.no_button_btn.configure(text="Waiting... (Right-Click)")
            self.no_button_label.configure(text="RIGHT-CLICK on No button", text_color=self.current_colors['warning'])
        
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
                coords = {'x': x, 'y': y}
                
                if self.selecting_button == 'yes':
                    self.yes_button = coords
                    self.yes_button_btn.configure(text="Select")
                    self.yes_button_label.configure(text=f"({x}, {y})", text_color=self.current_colors['success'])
                elif self.selecting_button == 'middle':
                    self.middle_button = coords
                    self.middle_button_btn.configure(text="Select")
                    self.middle_button_label.configure(text=f"({x}, {y})", text_color=self.current_colors['success'])
                elif self.selecting_button == 'no':
                    self.no_button = coords
                    self.no_button_btn.configure(text="Select")
                    self.no_button_label.configure(text=f"({x}, {y})", text_color=self.current_colors['success'])
                
                self.save_precast_settings()
                self.selecting_button = None
                
                # Stop mouse listener
                self.mouse_listener.stop()
    
    def start_fruit_point_selection(self):
        """Start fruit point selection mode - captures coordinate and color with overlay"""
        self.selecting_fruit_point = True
        self.fruit_point_btn.configure(text="Waiting... (Right-Click)")
        self.fruit_point_label.configure(text="RIGHT-CLICK on fruit location", text_color=self.current_colors['warning'])
        
        # Show overlay popup
        self._show_coord_selection_overlay()
        
        # Cleanup old listener
        try:
            if hasattr(self, 'fruit_mouse_listener') and self.fruit_mouse_listener:
                self.fruit_mouse_listener.stop()
        except:
            pass
        
        # Start mouse listener in background
        self.fruit_mouse_listener = MouseListener(on_click=self.on_mouse_click_fruit_point)
        self.fruit_mouse_listener.start()
    
    def on_mouse_click_fruit_point(self, x, y, button, pressed):
        """Handle mouse clicks during fruit point selection - save coordinate and color"""
        if not self.selecting_fruit_point:
            return
        
        if pressed:
            if button == Button.right:
                # Right click - save the fruit point position and capture color
                self.fruit_point = {'x': x, 'y': y}
                
                # Capture color at this coordinate
                try:
                    with mss.mss() as sct:
                        # Capture a 1x1 pixel area
                        monitor = {"top": y, "left": x, "width": 1, "height": 1}
                        screenshot = sct.grab(monitor)
                        # Get pixel color (BGRA format)
                        pixel = screenshot.pixel(0, 0)
                        # pixel is (R, G, B, A) - we need (B, G, R) which is the order in BGRA
                        self.fruit_color = (pixel[2], pixel[1], pixel[0])  # Convert to BGR for consistency
                        
                        color_hex = f"#{self.fruit_color[2]:02x}{self.fruit_color[1]:02x}{self.fruit_color[0]:02x}"
                        self.fruit_point_btn.configure(text="Select")
                        self.fruit_point_label.configure(text=f"({x}, {y}) {color_hex}", text_color=self.current_colors['success'])
                        
                        print(f"[Fruit Point] ✓ Saved: ({x}, {y}) Color: {color_hex}")
                except Exception as e:
                    print(f"Error capturing fruit color: {e}")
                    self.fruit_point_btn.configure(text="Select")
                    self.fruit_point_label.configure(text=f"({x}, {y}) [Color Error]", text_color=self.current_colors['warning'])
                
                # Close overlay if exists
                try:
                    if hasattr(self, 'coord_selection_overlay'):
                        self.coord_selection_overlay.destroy()
                except:
                    pass
                
                self.save_precast_settings()
                self.selecting_fruit_point = False
                
                # Stop mouse listener
                try:
                    if hasattr(self, 'fruit_mouse_listener') and self.fruit_mouse_listener:
                        self.fruit_mouse_listener.stop()
                except:
                    pass
    
    def start_top_bait_point_selection(self):
        """Start top bait point selection mode with overlay"""
        self.selecting_top_bait_point = True
        self.top_bait_point_btn.configure(text="Waiting... (Right-Click)")
        self.top_bait_point_label.configure(text="RIGHT-CLICK on bait location", text_color=self.current_colors['warning'])
        
        # Show overlay popup
        self._show_coord_selection_overlay()
        
        # Cleanup old listener
        try:
            if hasattr(self, 'top_bait_mouse_listener') and self.top_bait_mouse_listener:
                self.top_bait_mouse_listener.stop()
        except:
            pass
        
        # Start mouse listener in background
        self.top_bait_mouse_listener = MouseListener(on_click=self.on_mouse_click_top_bait_point)
        self.top_bait_mouse_listener.start()
    
    def on_mouse_click_top_bait_point(self, x, y, button, pressed):
        """Handle mouse clicks during top bait point selection"""
        if not self.selecting_top_bait_point:
            return
        
        if pressed:
            if button == Button.right:
                # Right click - save the top bait point position
                self.top_bait_point = {'x': x, 'y': y}
                self.top_bait_point_btn.configure(text="Select")
                self.top_bait_point_label.configure(text=f"({x}, {y})", text_color=self.current_colors['success'])
                
                print(f"[Top Bait Point] ✓ Saved: ({x}, {y})")
                
                # Close overlay if exists
                try:
                    if hasattr(self, 'coord_selection_overlay'):
                        self.coord_selection_overlay.destroy()
                except:
                    pass
                
                self.save_precast_settings()
                self.selecting_top_bait_point = False
                
                # Stop mouse listener
                try:
                    if hasattr(self, 'top_bait_mouse_listener') and self.top_bait_mouse_listener:
                        self.top_bait_mouse_listener.stop()
                except:
                    pass
    

    
    def load_area_coords(self):
        """Load area coordinates from settings file"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get('area_coords', get_default_coords()['area_coords'])
        except:
            pass
        return get_default_coords()['area_coords']
    
    def save_area_coords(self):
        """Save area coordinates to settings file"""
        if self.area_selector:
            # Get current position and size
            self.area_coords = {
                'x': self.area_selector.winfo_x(),
                'y': self.area_selector.winfo_y(),
                'width': self.area_selector.winfo_width(),
                'height': self.area_selector.winfo_height()
            }
            
            try:
                data = {}
                if os.path.exists(SETTINGS_FILE):
                    with open(SETTINGS_FILE, 'r') as f:
                        data = json.load(f)
                
                data['area_coords'] = self.area_coords
                
                with open(SETTINGS_FILE, 'w') as f:
                    json.dump(data, f, indent=4)
            except Exception as e:
                print(f"Error saving coordinates: {e}")
    
    def show_area_selector(self):
        """Show the area selector window"""
        if self.area_selector is None:
            self.area_selector = tk.Toplevel(self.root)
            self.area_selector.title("Area Selector")
            self.area_selector.attributes('-alpha', 0.3)
            self.area_selector.attributes('-topmost', True)
            self.area_selector.overrideredirect(True)
            
            # Set position and size from saved coords
            x = self.area_coords['x']
            y = self.area_coords['y']
            width = self.area_coords['width']
            height = self.area_coords['height']
            self.area_selector.geometry(f"{width}x{height}+{x}+{y}")
            
            # Create a frame with border
            frame = tk.Frame(self.area_selector, bg='red', highlightbackground='red', 
                           highlightthickness=3)
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
        tl_handle = tk.Frame(frame, bg='yellow', cursor='size_nw_se', width=handle_size, height=handle_size)
        tl_handle.place(x=0, y=0, anchor='nw')
        tl_handle.bind("<ButtonPress-1>", lambda e: self.start_resize(e, 'top-left'))
        tl_handle.bind("<B1-Motion>", lambda e: self.on_resize(e, 'top-left'))
        
        # Top-right corner
        tr_handle = tk.Frame(frame, bg='yellow', cursor='size_ne_sw', width=handle_size, height=handle_size)
        tr_handle.place(relx=1.0, y=0, anchor='ne')
        tr_handle.bind("<ButtonPress-1>", lambda e: self.start_resize(e, 'top-right'))
        tr_handle.bind("<B1-Motion>", lambda e: self.on_resize(e, 'top-right'))
        
        # Bottom-left corner
        bl_handle = tk.Frame(frame, bg='yellow', cursor='size_ne_sw', width=handle_size, height=handle_size)
        bl_handle.place(x=0, rely=1.0, anchor='sw')
        bl_handle.bind("<ButtonPress-1>", lambda e: self.start_resize(e, 'bottom-left'))
        bl_handle.bind("<B1-Motion>", lambda e: self.on_resize(e, 'bottom-left'))
        
        # Bottom-right corner
        br_handle = tk.Frame(frame, bg='yellow', cursor='size_nw_se', width=handle_size, height=handle_size)
        br_handle.place(relx=1.0, rely=1.0, anchor='se')
        br_handle.bind("<ButtonPress-1>", lambda e: self.start_resize(e, 'bottom-right'))
        br_handle.bind("<B1-Motion>", lambda e: self.on_resize(e, 'bottom-right'))
        
        # Edge handles
        # Top edge
        t_handle = tk.Frame(frame, bg='lime', cursor='sb_v_double_arrow', height=edge_thickness)
        t_handle.place(relx=0.5, y=0, anchor='n', relwidth=0.7)
        t_handle.bind("<ButtonPress-1>", lambda e: self.start_resize(e, 'top'))
        t_handle.bind("<B1-Motion>", lambda e: self.on_resize(e, 'top'))
        
        # Bottom edge
        b_handle = tk.Frame(frame, bg='lime', cursor='sb_v_double_arrow', height=edge_thickness)
        b_handle.place(relx=0.5, rely=1.0, anchor='s', relwidth=0.7)
        b_handle.bind("<ButtonPress-1>", lambda e: self.start_resize(e, 'bottom'))
        b_handle.bind("<B1-Motion>", lambda e: self.on_resize(e, 'bottom'))
        
        # Left edge
        l_handle = tk.Frame(frame, bg='lime', cursor='sb_h_double_arrow', width=edge_thickness)
        l_handle.place(x=0, rely=0.5, anchor='w', relheight=0.7)
        l_handle.bind("<ButtonPress-1>", lambda e: self.start_resize(e, 'left'))
        l_handle.bind("<B1-Motion>", lambda e: self.on_resize(e, 'left'))
        
        # Right edge
        r_handle = tk.Frame(frame, bg='lime', cursor='sb_h_double_arrow', width=edge_thickness)
        r_handle.place(relx=1.0, rely=0.5, anchor='e', relheight=0.7)
        r_handle.bind("<ButtonPress-1>", lambda e: self.start_resize(e, 'right'))
        r_handle.bind("<B1-Motion>", lambda e: self.on_resize(e, 'right'))
    
    def start_drag(self, event):
        """Start dragging the area selector"""
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
    
    def on_drag(self, event):
        """Handle dragging the area selector"""
        x = self.area_selector.winfo_x() + event.x - self._drag_data["x"]
        y = self.area_selector.winfo_y() + event.y - self._drag_data["y"]
        self.area_selector.geometry(f"+{x}+{y}")
    
    def start_resize(self, event, direction='both'):
        """Start resizing the area selector"""
        self._resize_data = {
            "x": event.x_root,
            "y": event.y_root,
            "width": self.area_selector.winfo_width(),
            "height": self.area_selector.winfo_height(),
            "win_x": self.area_selector.winfo_x(),
            "win_y": self.area_selector.winfo_y(),
            "direction": direction
        }
    
    def on_resize(self, event, direction='both'):
        """Handle resizing the area selector from any corner or edge"""
        if not hasattr(self, '_resize_data'):
            return
        
        dx = event.x_root - self._resize_data["x"]
        dy = event.y_root - self._resize_data["y"]
        
        new_width = self._resize_data["width"]
        new_height = self._resize_data["height"]
        new_x = self._resize_data["win_x"]
        new_y = self._resize_data["win_y"]
        
        direction = self._resize_data.get("direction", 'both')
        min_size = 50
        
        # Handle each direction
        if direction == 'right' or direction == 'bottom-right' or direction == 'top-right':
            new_width = max(min_size, self._resize_data["width"] + dx)
        if direction == 'left' or direction == 'bottom-left' or direction == 'top-left':
            new_width = max(min_size, self._resize_data["width"] - dx)
            new_x = self._resize_data["win_x"] + dx
        if direction == 'bottom' or direction == 'bottom-right' or direction == 'bottom-left':
            new_height = max(min_size, self._resize_data["height"] + dy)
        if direction == 'top' or direction == 'top-right' or direction == 'top-left':
            new_height = max(min_size, self._resize_data["height"] - dy)
            new_y = self._resize_data["win_y"] + dy
        if direction == 'both':
            new_width = max(min_size, self._resize_data["width"] + dx)
            new_height = max(min_size, self._resize_data["height"] + dy)
        
        self.area_selector.geometry(f"{new_width}x{new_height}+{new_x}+{new_y}")
    
    def hide_area_selector(self):
        """Hide and save the area selector"""
        if self.area_selector:
            self.save_area_coords()
            self.area_selector.destroy()
            self.area_selector = None
        
        # Also hide debug arrow when area selector closes
        self.hide_debug_arrow()
        self.hide_horizontal_arrows()
        self.hide_white_middle_arrow()
        self.hide_black_group_arrow()
    
    def show_area_outline(self):
        """Show a small green outline of the detection area during macro execution"""
        if self.area_outline is None and self.area_coords:
            self.area_outline = tk.Toplevel(self.root)
            self.area_outline.title("Area Outline")
            self.area_outline.attributes('-alpha', 0.7)
            self.area_outline.attributes('-topmost', True)
            self.area_outline.overrideredirect(True)
            
            # Set position and size from saved coords
            x = self.area_coords['x']
            y = self.area_coords['y']
            width = self.area_coords['width']
            height = self.area_coords['height']
            self.area_outline.geometry(f"{width}x{height}+{x}+{y}")
            
            # Create a frame with thin green border
            frame = tk.Frame(self.area_outline, bg='black', highlightbackground='#00ff00', 
                           highlightthickness=2)
            frame.pack(fill=tk.BOTH, expand=True)
            
            # Make it click-through (transparent to mouse)
            self.area_outline.attributes('-transparentcolor', 'black')
            
            # Prevent from closing
            self.area_outline.protocol("WM_DELETE_WINDOW", lambda: None)
    
    def hide_area_outline(self):
        """Hide the area outline"""
        if self.area_outline:
            self.area_outline.destroy()
            self.area_outline = None
    
    def load_auto_craft_area_coords(self):
        """Load auto craft area coordinates from settings file"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    # Default to center of screen if not set
                    default_coords = {
                        'x': SCREEN_WIDTH // 2 - 150,
                        'y': SCREEN_HEIGHT // 2 - 150,
                        'width': 300,
                        'height': 300
                    }
                    return data.get('auto_craft_area_coords', default_coords)
        except:
            pass
        # Default to center of screen
        return {
            'x': SCREEN_WIDTH // 2 - 150,
            'y': SCREEN_HEIGHT // 2 - 150,
            'width': 300,
            'height': 300
        }
    
    def save_auto_craft_area_coords(self):
        """Save auto craft area coordinates to settings file"""
        if self.auto_craft_area_selector:
            # Get current position and size
            self.auto_craft_area_coords = {
                'x': self.auto_craft_area_selector.winfo_x(),
                'y': self.auto_craft_area_selector.winfo_y(),
                'width': self.auto_craft_area_selector.winfo_width(),
                'height': self.auto_craft_area_selector.winfo_height()
            }
            
            try:
                data = {}
                if os.path.exists(SETTINGS_FILE):
                    with open(SETTINGS_FILE, 'r') as f:
                        data = json.load(f)
                
                data['auto_craft_area_coords'] = self.auto_craft_area_coords
                
                with open(SETTINGS_FILE, 'w') as f:
                    json.dump(data, f, indent=4)
            except Exception as e:
                print(f"Error saving auto craft area coordinates: {e}")
    
    def show_auto_craft_area_selector(self):
        """Show the auto craft area selector window"""
        if self.auto_craft_area_selector is None:
            self.auto_craft_area_selector = tk.Toplevel(self.root)
            self.auto_craft_area_selector.title("Auto Craft Area Selector")
            self.auto_craft_area_selector.attributes('-alpha', 0.3)
            self.auto_craft_area_selector.attributes('-topmost', True)
            self.auto_craft_area_selector.overrideredirect(True)
            
            # Set position and size from saved coords
            x = self.auto_craft_area_coords['x']
            y = self.auto_craft_area_coords['y']
            width = self.auto_craft_area_coords['width']
            height = self.auto_craft_area_coords['height']
            self.auto_craft_area_selector.geometry(f"{width}x{height}+{x}+{y}")
            
            # Create a frame with border (blue for auto craft)
            frame = tk.Frame(self.auto_craft_area_selector, bg='blue', highlightbackground='blue', 
                           highlightthickness=3)
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
        tl_handle = tk.Frame(frame, bg='yellow', cursor='size_nw_se', width=handle_size, height=handle_size)
        tl_handle.place(x=0, y=0, anchor='nw')
        tl_handle.bind("<ButtonPress-1>", lambda e: self.start_auto_craft_resize(e, 'top-left'))
        tl_handle.bind("<B1-Motion>", lambda e: self.on_auto_craft_resize(e, 'top-left'))
        
        # Top-right corner
        tr_handle = tk.Frame(frame, bg='yellow', cursor='size_ne_sw', width=handle_size, height=handle_size)
        tr_handle.place(relx=1.0, y=0, anchor='ne')
        tr_handle.bind("<ButtonPress-1>", lambda e: self.start_auto_craft_resize(e, 'top-right'))
        tr_handle.bind("<B1-Motion>", lambda e: self.on_auto_craft_resize(e, 'top-right'))
        
        # Bottom-left corner
        bl_handle = tk.Frame(frame, bg='yellow', cursor='size_ne_sw', width=handle_size, height=handle_size)
        bl_handle.place(x=0, rely=1.0, anchor='sw')
        bl_handle.bind("<ButtonPress-1>", lambda e: self.start_auto_craft_resize(e, 'bottom-left'))
        bl_handle.bind("<B1-Motion>", lambda e: self.on_auto_craft_resize(e, 'bottom-left'))
        
        # Bottom-right corner
        br_handle = tk.Frame(frame, bg='yellow', cursor='size_nw_se', width=handle_size, height=handle_size)
        br_handle.place(relx=1.0, rely=1.0, anchor='se')
        br_handle.bind("<ButtonPress-1>", lambda e: self.start_auto_craft_resize(e, 'bottom-right'))
        br_handle.bind("<B1-Motion>", lambda e: self.on_auto_craft_resize(e, 'bottom-right'))
        
        # Edge handles
        # Top edge
        t_handle = tk.Frame(frame, bg='lime', cursor='sb_v_double_arrow', height=edge_thickness)
        t_handle.place(relx=0.5, y=0, anchor='n', relwidth=0.7)
        t_handle.bind("<ButtonPress-1>", lambda e: self.start_auto_craft_resize(e, 'top'))
        t_handle.bind("<B1-Motion>", lambda e: self.on_auto_craft_resize(e, 'top'))
        
        # Bottom edge
        b_handle = tk.Frame(frame, bg='lime', cursor='sb_v_double_arrow', height=edge_thickness)
        b_handle.place(relx=0.5, rely=1.0, anchor='s', relwidth=0.7)
        b_handle.bind("<ButtonPress-1>", lambda e: self.start_auto_craft_resize(e, 'bottom'))
        b_handle.bind("<B1-Motion>", lambda e: self.on_auto_craft_resize(e, 'bottom'))
        
        # Left edge
        l_handle = tk.Frame(frame, bg='lime', cursor='sb_h_double_arrow', width=edge_thickness)
        l_handle.place(x=0, rely=0.5, anchor='w', relheight=0.7)
        l_handle.bind("<ButtonPress-1>", lambda e: self.start_auto_craft_resize(e, 'left'))
        l_handle.bind("<B1-Motion>", lambda e: self.on_auto_craft_resize(e, 'left'))
        
        # Right edge
        r_handle = tk.Frame(frame, bg='lime', cursor='sb_h_double_arrow', width=edge_thickness)
        r_handle.place(relx=1.0, rely=0.5, anchor='e', relheight=0.7)
        r_handle.bind("<ButtonPress-1>", lambda e: self.start_auto_craft_resize(e, 'right'))
        r_handle.bind("<B1-Motion>", lambda e: self.on_auto_craft_resize(e, 'right'))
    
    def start_auto_craft_drag(self, event):
        """Start dragging the auto craft area selector"""
        self._auto_craft_drag_data["x"] = event.x
        self._auto_craft_drag_data["y"] = event.y
    
    def on_auto_craft_drag(self, event):
        """Handle dragging the auto craft area selector"""
        x = self.auto_craft_area_selector.winfo_x() + event.x - self._auto_craft_drag_data["x"]
        y = self.auto_craft_area_selector.winfo_y() + event.y - self._auto_craft_drag_data["y"]
        self.auto_craft_area_selector.geometry(f"+{x}+{y}")
    
    def start_auto_craft_resize(self, event, direction='both'):
        """Start resizing the auto craft area selector"""
        self._auto_craft_resize_data = {
            "x": event.x_root,
            "y": event.y_root,
            "width": self.auto_craft_area_selector.winfo_width(),
            "height": self.auto_craft_area_selector.winfo_height(),
            "win_x": self.auto_craft_area_selector.winfo_x(),
            "win_y": self.auto_craft_area_selector.winfo_y(),
            "direction": direction
        }
    
    def on_auto_craft_resize(self, event, direction='both'):
        """Handle resizing the auto craft area selector from any corner or edge"""
        if not hasattr(self, '_auto_craft_resize_data'):
            return
        
        dx = event.x_root - self._auto_craft_resize_data["x"]
        dy = event.y_root - self._auto_craft_resize_data["y"]
        
        new_width = self._auto_craft_resize_data["width"]
        new_height = self._auto_craft_resize_data["height"]
        new_x = self._auto_craft_resize_data["win_x"]
        new_y = self._auto_craft_resize_data["win_y"]
        
        direction = self._auto_craft_resize_data.get("direction", 'both')
        min_size = 50
        
        # Handle each direction
        if direction == 'right' or direction == 'bottom-right' or direction == 'top-right':
            new_width = max(min_size, self._auto_craft_resize_data["width"] + dx)
        if direction == 'left' or direction == 'bottom-left' or direction == 'top-left':
            new_width = max(min_size, self._auto_craft_resize_data["width"] - dx)
            new_x = self._auto_craft_resize_data["win_x"] + dx
        if direction == 'bottom' or direction == 'bottom-right' or direction == 'bottom-left':
            new_height = max(min_size, self._auto_craft_resize_data["height"] + dy)
        if direction == 'top' or direction == 'top-right' or direction == 'top-left':
            new_height = max(min_size, self._auto_craft_resize_data["height"] - dy)
            new_y = self._auto_craft_resize_data["win_y"] + dy
        if direction == 'both':
            new_width = max(min_size, self._auto_craft_resize_data["width"] + dx)
            new_height = max(min_size, self._auto_craft_resize_data["height"] + dy)
        
        self.auto_craft_area_selector.geometry(f"{new_width}x{new_height}+{new_x}+{new_y}")
    
    def hide_auto_craft_area_selector(self):
        """Hide and save the auto craft area selector"""
        if self.auto_craft_area_selector:
            self.save_auto_craft_area_coords()
            self.auto_craft_area_selector.destroy()
            self.auto_craft_area_selector = None
    
    def save_auto_craft_settings(self):
        """Save auto craft settings to settings file"""
        try:
            data = {}
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
            
            data['auto_craft_settings'] = {
                'auto_craft_enabled': self.auto_craft_enabled,
                'auto_craft_water_point': self.auto_craft_water_point,
                'craft_every_n_fish': self.craft_every_n_fish,
                'craft_menu_delay': self.craft_menu_delay,
                'craft_click_speed': self.craft_click_speed,
                'craft_legendary_quantity': self.craft_legendary_quantity,
                'craft_rare_quantity': self.craft_rare_quantity,
                'craft_common_quantity': self.craft_common_quantity,
                'craft_button_coords': self.craft_button_coords,
                'plus_button_coords': self.plus_button_coords,
                'fish_icon_coords': self.fish_icon_coords,
                'legendary_bait_coords': self.legendary_bait_coords,
                'rare_bait_coords': self.rare_bait_coords,
                'common_bait_coords': self.common_bait_coords
            }
            
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f, indent=4)
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
            gap = matches[i] - matches[i-1] - 1  # Gap between consecutive matches
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
    
    def show_debug_arrow(self, middle_x):
        """Show debug arrow pointing to the X coordinate"""
        if not self.area_coords:
            return
        
        # Calculate absolute position
        arrow_x = self.area_coords['x'] + middle_x
        arrow_y = self.area_coords['y'] - 5  # 5 pixels above the area (closer)
        
        # Create or update arrow window
        if self.debug_arrow is None:
            self.debug_arrow = tk.Toplevel(self.root)
            self.debug_arrow.overrideredirect(True)
            self.debug_arrow.attributes('-topmost', True)
            self.debug_arrow.attributes('-transparentcolor', 'white')
            
            # Create canvas for arrow with transparent background
            canvas = tk.Canvas(self.debug_arrow, width=12, height=10, 
                             bg='white', highlightthickness=0)
            canvas.pack()
            
            # Draw arrow pointing down (triangle) - red only
            canvas.create_polygon(
                6, 9,     # Bottom center (ponta para baixo)
                1, 1,     # Top left
                11, 1,    # Top right
                fill='red', outline=''
            )
            
            # Prevent from closing
            self.debug_arrow.protocol("WM_DELETE_WINDOW", lambda: None)
        
        # Update position (centered on X coordinate)
        self.debug_arrow.geometry(f"12x10+{arrow_x - 6}+{arrow_y}")
    
    def hide_debug_arrow(self):
        """Hide debug arrow"""
        if self.debug_arrow:
            self.debug_arrow.destroy()
            self.debug_arrow = None
    
    def show_horizontal_arrows(self, top_y, bottom_y):
        """Show horizontal arrows pointing from right to left at top and bottom Y positions"""
        if not self.area_coords:
            return
        
        # Calculate absolute positions (right side of area)
        arrow_x = self.area_coords['x'] + self.area_coords['width'] + 5  # 5 pixels to the right of area
        top_arrow_y = self.area_coords['y'] + top_y
        bottom_arrow_y = self.area_coords['y'] + bottom_y
        
        # Create or update TOP arrow
        if self.horizontal_arrow_top is None:
            self.horizontal_arrow_top = tk.Toplevel(self.root)
            self.horizontal_arrow_top.overrideredirect(True)
            self.horizontal_arrow_top.attributes('-topmost', True)
            self.horizontal_arrow_top.attributes('-transparentcolor', 'white')
            
            canvas = tk.Canvas(self.horizontal_arrow_top, width=20, height=12, 
                             bg='white', highlightthickness=0)
            canvas.pack()
            
            # Draw arrow pointing LEFT (triangle) - green only
            canvas.create_polygon(
                2, 6,     # Left point (ponta para esquerda)
                18, 1,    # Top right
                18, 11,   # Bottom right
                fill='green', outline=''
            )
            
            self.horizontal_arrow_top.protocol("WM_DELETE_WINDOW", lambda: None)
        
        # Create or update BOTTOM arrow
        if self.horizontal_arrow_bottom is None:
            self.horizontal_arrow_bottom = tk.Toplevel(self.root)
            self.horizontal_arrow_bottom.overrideredirect(True)
            self.horizontal_arrow_bottom.attributes('-topmost', True)
            self.horizontal_arrow_bottom.attributes('-transparentcolor', 'white')
            
            canvas = tk.Canvas(self.horizontal_arrow_bottom, width=20, height=12, 
                             bg='white', highlightthickness=0)
            canvas.pack()
            
            # Draw arrow pointing LEFT (triangle) - green only
            canvas.create_polygon(
                2, 6,     # Left point (ponta para esquerda)
                18, 1,    # Top right
                18, 11,   # Bottom right
                fill='green', outline=''
            )
            
            self.horizontal_arrow_bottom.protocol("WM_DELETE_WINDOW", lambda: None)
        
        # Update positions - aligned without offset
        self.horizontal_arrow_top.geometry(f"20x12+{arrow_x}+{top_arrow_y}")
        self.horizontal_arrow_bottom.geometry(f"20x12+{arrow_x}+{bottom_arrow_y}")
    
    def hide_horizontal_arrows(self):
        """Hide horizontal arrows"""
        if self.horizontal_arrow_top:
            self.horizontal_arrow_top.destroy()
            self.horizontal_arrow_top = None
        if self.horizontal_arrow_bottom:
            self.horizontal_arrow_bottom.destroy()
            self.horizontal_arrow_bottom = None
    
    def show_white_middle_arrow(self, white_middle_y):
        """Show arrow pointing to the middle of white section from outside MSS area"""
        if not self.area_coords:
            return
        
        # Calculate position on the RIGHT side of the area
        arrow_x = self.area_coords['x'] + self.area_coords['width'] + 5  # 5 pixels to the right
        arrow_y = self.area_coords['y'] + white_middle_y
        
        # Create or update white middle arrow
        if self.white_middle_arrow is None:
            self.white_middle_arrow = tk.Toplevel(self.root)
            self.white_middle_arrow.overrideredirect(True)
            self.white_middle_arrow.attributes('-topmost', True)
            self.white_middle_arrow.attributes('-transparentcolor', 'white')
            
            canvas = tk.Canvas(self.white_middle_arrow, width=20, height=12, 
                             bg='white', highlightthickness=0)
            canvas.pack()
            
            # Draw arrow pointing LEFT (triangle) - yellow only
            canvas.create_polygon(
                2, 6,     # Left point (ponta para esquerda)
                18, 1,    # Top right
                18, 11,   # Bottom right
                fill='yellow', outline=''
            )
            
            self.white_middle_arrow.protocol("WM_DELETE_WINDOW", lambda: None)
        
        # Update position
        self.white_middle_arrow.geometry(f"20x12+{arrow_x}+{arrow_y}")
    
    def hide_white_middle_arrow(self):
        """Hide white middle arrow"""
        if self.white_middle_arrow:
            self.white_middle_arrow.destroy()
            self.white_middle_arrow = None
    
    def show_black_group_arrow(self, black_group_middle_y):
        """Show arrow pointing to the middle of biggest black group from left side"""
        if not self.area_coords:
            return
        
        # Calculate position on the LEFT side of the area
        arrow_x = self.area_coords['x'] - 25  # 25 pixels to the left (arrow width 20 + 5 gap)
        arrow_y = self.area_coords['y'] + black_group_middle_y
        
        # Create or update black group arrow
        if self.black_group_arrow is None:
            self.black_group_arrow = tk.Toplevel(self.root)
            self.black_group_arrow.overrideredirect(True)
            self.black_group_arrow.attributes('-topmost', True)
            self.black_group_arrow.attributes('-transparentcolor', 'white')
            
            canvas = tk.Canvas(self.black_group_arrow, width=20, height=12, 
                             bg='white', highlightthickness=0)
            canvas.pack()
            
            # Draw arrow pointing RIGHT (triangle) - blue only
            canvas.create_polygon(
                18, 6,    # Right point (pointing right)
                2, 1,     # Top left
                2, 11,    # Bottom left
                fill='blue', outline=''
            )
            
            self.black_group_arrow.protocol("WM_DELETE_WINDOW", lambda: None)
        
        # Update position
        self.black_group_arrow.geometry(f"20x12+{arrow_x}+{arrow_y}")
    
    def hide_black_group_arrow(self):
        """Hide black group arrow"""
        if self.black_group_arrow:
            self.black_group_arrow.destroy()
            self.black_group_arrow = None

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
    dialog.attributes('-topmost', True)
    dialog.grab_set()
    
    # Store user choice
    user_accepted = [False]
    
    # Header frame
    header_frame = tk.Frame(dialog, bg='#2c3e50', height=60)
    header_frame.pack(fill=tk.X)
    header_frame.pack_propagate(False)
    
    title_label = tk.Label(header_frame, text="⚡ BPS FISHING MACRO ⚡", 
                          font=("Arial", 16, "bold"), fg="#00ff88", bg='#2c3e50')
    title_label.pack(expand=True)
    
    # Text widget with scrollbar - FIXED HEIGHT
    text_frame = tk.Frame(dialog, bg='#ecf0f1', padx=20, pady=15)
    text_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=10)
    
    scrollbar = tk.Scrollbar(text_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Consolas", 9),
                         bg='#ffffff', fg='#2c3e50', padx=10, pady=10,
                         yscrollcommand=scrollbar.set, relief=tk.FLAT,
                         borderwidth=1, height=22, width=75)
    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=text_widget.yview)
    
    # Insert terms text
    text_widget.insert('1.0', terms_text)
    text_widget.config(state=tk.DISABLED)  # Make read-only
    
    # Spacer to separate buttons
    spacer = tk.Frame(dialog, bg='#ecf0f1', height=10)
    spacer.pack(fill=tk.X)
    spacer.pack_propagate(False)
    
    # Buttons frame - SEPARATE AND FIXED
    button_frame = tk.Frame(dialog, bg='#ecf0f1', height=60)
    button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
    button_frame.pack_propagate(False)
    
    def on_agree():
        user_accepted[0] = True
        dialog.destroy()
    
    def on_decline():
        user_accepted[0] = False
        dialog.destroy()
    
    # Decline button (red) - LEFT
    decline_btn = tk.Button(button_frame, text=f"❌ {btn_decline}", 
                           command=on_decline, font=("Arial", 11, "bold"),
                           bg='#e74c3c', fg='white', padx=25, pady=12,
                           relief=tk.RAISED, borderwidth=2, cursor='hand2',
                           width=15)
    decline_btn.pack(side=tk.LEFT, padx=10)
    
    # Agree button (green) - RIGHT
    agree_btn = tk.Button(button_frame, text=f"✓ {btn_agree}", 
                         command=on_agree, font=("Arial", 11, "bold"),
                         bg='#27ae60', fg='white', padx=25, pady=12,
                         relief=tk.RAISED, borderwidth=2, cursor='hand2',
                         width=15)
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
