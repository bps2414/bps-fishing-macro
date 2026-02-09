"""
Fishing Cycle Module (Phase 6)
--------------------------------
Main fishing loop orchestration - extracted from bps_fishing_macroV5.py

CRITICAL: This is a LITERAL extraction with ZERO behavior changes.
All code is copied exactly as-is from the original implementation.

Architecture:
- FishingCycle is a "dumb shell" (casca burra) - no new logic
- Receives all dependencies via constructor (dependency injection)
- Contains 7 methods:
  * main_loop() - Orchestration and mode selection
  * pre_cast() - Normal mode pre-cast with fruit checking
  * buy_common_bait() - Bait purchase sequence
  * esperar() - Wait for fish colors
  * pesca() - Minigame with PID control
  * auto_craft_pre_cast() - Auto craft cycle
  * auto_craft_esperar() - Auto craft wait
  * auto_craft_pesca() - Auto craft minigame

All timing, delays, sleeps, conditionals, variable names, print statements
are preserved EXACTLY as they were in the original code.
"""

import time
import numpy as np
import mss
from pynput.keyboard import Key

# Screen dimensions (constants from main file)
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080


class FishingCycle:
    """
    Main fishing loop orchestration.

    This is a LITERAL extraction from the main file with ZERO behavioral changes.
    All code is copied exactly as-is.
    """

    def __init__(
        self,
        vision,
        input_ctrl,
        bait_manager,
        fruit_handler,
        craft_automation,
        settings,
        callbacks,
        logger,
        stats_manager,
    ):
        """
        Initialize FishingCycle with all dependencies.

        Args:
            vision: Vision control bundle (screen, color_detector, anti_macro)
            input_ctrl: Input control bundle (mouse, keyboard, window_manager)
            bait_manager: BaitManager instance for smart bait selection
            fruit_handler: FruitHandler instance for fruit detection/storage
            craft_automation: CraftAutomation instance for crafting sequences
            settings: Dict with all settings (area_coords, delays, flags, etc.)
            callbacks: Dict with all callback functions (set_status, interruptible_sleep, etc.)
            logger: Logger instance for logging
            stats_manager: StatsManager instance for stats tracking
        """
        # Vision components
        self.screen = vision["screen"]
        self.color_detector = vision["color_detector"]
        self.anti_macro = vision["anti_macro"]

        # Input components
        self.mouse = input_ctrl["mouse"]
        self.keyboard = input_ctrl["keyboard"]
        self.window_manager = input_ctrl["window_manager"]

        # Automation modules (Phase 5)
        self.bait_manager = bait_manager
        self.fruit_handler = fruit_handler
        self.craft_automation = craft_automation

        # Settings (copy all settings from dict)
        # Area coordinates
        self.area_coords = settings.get("area_coords")
        self.auto_craft_area_coords = settings.get("auto_craft_area_coords")
        self.water_point = settings.get("water_point")
        self.auto_craft_water_point = settings.get("auto_craft_water_point")
        self.top_bait_point = settings.get("top_bait_point")
        self.fruit_point = settings.get("fruit_point")
        self.inventory_fruit_point = settings.get("inventory_fruit_point")
        self.inventory_center_point = settings.get("inventory_center_point")

        # Delays and timing
        self.recast_timeout = settings.get("recast_timeout", 30)
        self.fruit_detection_delay = settings.get("fruit_detection_delay", 0.03)
        self.rod_deselect_delay = settings.get("rod_deselect_delay", 0.2)
        self.rod_select_delay = settings.get("rod_select_delay", 0.2)
        self.bait_click_delay = settings.get("bait_click_delay", 0.3)
        self.mouse_move_settle = settings.get("mouse_move_settle", 0.01)
        self.cast_hold_duration = settings.get("cast_hold_duration", 0.5)
        self.pre_cast_minigame_wait = settings.get("pre_cast_minigame_wait", 2.0)
        self.zoom_tick_delay = settings.get("zoom_tick_delay", 0.01)
        self.zoom_settle_delay = settings.get("zoom_settle_delay", 0.1)
        self.store_click_delay = settings.get("store_click_delay", 0.3)
        self.backspace_delay = settings.get("backspace_delay", 0.3)
        self.fruit_hold_delay = settings.get("fruit_hold_delay", 0.5)
        self.camera_rotation_delay = settings.get("camera_rotation_delay", 0.1)
        self.camera_rotation_step_delay = settings.get(
            "camera_rotation_step_delay", 0.01
        )
        self.camera_rotation_settle_delay = settings.get(
            "camera_rotation_settle_delay", 0.1
        )
        self.camera_rotation_steps = settings.get("camera_rotation_steps", 10)
        self.resend_interval = settings.get("resend_interval", 0.5)
        self.general_action_delay = settings.get(
            "general_action_delay", 0.01
        )  # MISSING - used in buy_common_bait

        # Hotkeys
        self.rod_hotkey = settings.get("rod_hotkey", "1")
        self.fruit_hotkey = settings.get("fruit_hotkey", "3")
        self.everything_else_hotkey = settings.get("everything_else_hotkey", "2")

        # Store callbacks dict for access in main_loop
        self.callbacks = callbacks

        # Colors
        self.fruit_color = settings.get("fruit_color")

        # Flags
        self.auto_buy_bait = settings.get("auto_buy_bait", False)
        self.auto_select_top_bait = settings.get("auto_select_top_bait", False)
        self.smart_bait_enabled = settings.get("smart_bait_enabled", False)
        self.auto_store_fruit = settings.get("auto_store_fruit", False)
        self.store_in_inventory = settings.get("store_in_inventory", False)
        self.auto_craft_enabled = settings.get("auto_craft_enabled", False)
        self.disable_normal_camera = settings.get("disable_normal_camera", False)
        self.webhook_only_legendary = settings.get("webhook_only_legendary", False)

        # Bait purchase settings
        self.yes_button = settings.get("yes_button")
        self.middle_button = settings.get("middle_button")
        self.no_button = settings.get("no_button")
        self.loops_per_purchase = settings.get("loops_per_purchase", 10)
        self.bait_loop_counter = settings.get("bait_loop_counter", 0)

        # Auto craft settings
        self.craft_every_n_fish = settings.get("craft_every_n_fish", 0)

        # PID control parameters
        self.pid_kp = settings.get("pid_kp", 1.0)
        self.pid_kd = settings.get("pid_kd", 0.1)
        self.pid_clamp = settings.get("pid_clamp", 100.0)
        self.max_lost_frames = settings.get("max_lost_frames", 3)

        # Zoom settings
        self.zoom_ticks = settings.get("zoom_ticks", 3)

        # Callbacks
        self.set_status = callbacks["set_status"]
        self.interruptible_sleep = callbacks["interruptible_sleep"]
        self.check_legendary_pity = callbacks["check_legendary_pity"]
        self.send_fruit_webhook = callbacks["send_fruit_webhook"]

        # Dynamic GUI settings callbacks (values can change during execution)
        self.get_auto_buy_bait = callbacks.get(
            "get_auto_buy_bait", lambda: self.auto_buy_bait
        )
        self.get_auto_craft_enabled = callbacks.get(
            "get_auto_craft_enabled", lambda: self.auto_craft_enabled
        )
        self.get_auto_select_top_bait = callbacks.get(
            "get_auto_select_top_bait", lambda: self.auto_select_top_bait
        )
        self.get_smart_bait_enabled = callbacks.get(
            "get_smart_bait_enabled", lambda: self.smart_bait_enabled
        )
        self.get_auto_store_fruit = callbacks.get(
            "get_auto_store_fruit", lambda: self.auto_store_fruit
        )
        self.get_store_in_inventory = callbacks.get(
            "get_store_in_inventory", lambda: self.store_in_inventory
        )
        self.get_disable_normal_camera = callbacks.get(
            "get_disable_normal_camera", lambda: self.disable_normal_camera
        )
        self.get_webhook_only_legendary = callbacks.get(
            "get_webhook_only_legendary", lambda: self.webhook_only_legendary
        )

        # State access callbacks
        self.get_running = callbacks["get_running"]
        self.get_first_run = callbacks["get_first_run"]
        self.set_first_run = callbacks["set_first_run"]
        self.get_first_catch = callbacks["get_first_catch"]
        self.set_first_catch = callbacks["set_first_catch"]
        self.get_mouse_pressed = callbacks["get_mouse_pressed"]
        self.set_mouse_pressed = callbacks["set_mouse_pressed"]
        self.get_fish_caught = callbacks["get_fish_caught"]
        self.increment_fish_caught = callbacks["increment_fish_caught"]
        self.get_fruits_caught = callbacks["get_fruits_caught"]
        self.increment_fruits_caught = callbacks["increment_fruits_caught"]
        self.set_fish_at_last_fruit = callbacks["set_fish_at_last_fruit"]

        # PID state access
        self.get_pid_last_error = callbacks["get_pid_last_error"]
        self.set_pid_last_error = callbacks["set_pid_last_error"]
        self.get_pid_last_time = callbacks["get_pid_last_time"]
        self.set_pid_last_time = callbacks["set_pid_last_time"]
        self.get_detection_lost_counter = callbacks["get_detection_lost_counter"]
        self.set_detection_lost_counter = callbacks["set_detection_lost_counter"]
        self.get_last_resend_time = callbacks["get_last_resend_time"]
        self.set_last_resend_time = callbacks["set_last_resend_time"]

        # FPS tracking
        self.get_fps_frame_count = callbacks["get_fps_frame_count"]
        self.increment_fps_frame_count = callbacks["increment_fps_frame_count"]
        self.get_fps_last_time = callbacks["get_fps_last_time"]
        self.set_fps_last_time = callbacks["set_fps_last_time"]
        self.get_detection_fps = callbacks["get_detection_fps"]
        self.set_detection_fps = callbacks["set_detection_fps"]

        # Cycle time tracking
        self.start_cycle_timer = callbacks["start_cycle_timer"]
        self.end_cycle_timer = callbacks["end_cycle_timer"]
        self.get_average_cycle_time = callbacks["get_average_cycle_time"]

        # Auto craft state
        self.get_last_craft_fish_count = callbacks.get(
            "get_last_craft_fish_count", lambda: 0
        )
        self.set_last_craft_fish_count = callbacks.get(
            "set_last_craft_fish_count", lambda x: None
        )

        # Logger and stats
        self.logger = logger
        self.stats_manager = stats_manager

        # FPS Internal Calibration (Local to this Thread)
        self.local_fps_frame_count = 0
        self.local_fps_last_time = time.time()

    def update_coords(
        self,
        top_bait_point=None,
        fruit_point=None,
        water_point=None,
        auto_craft_water_point=None,
        inventory_fruit_point=None,
        inventory_center_point=None,
        yes_button=None,
        middle_button=None,
        no_button=None,
    ):
        """Update coordinates after user changes them in UI

        Args:
            top_bait_point: New top bait coordinates or None to keep current
            fruit_point: New fruit point coordinates or None to keep current
            water_point: New water point coordinates or None to keep current
            auto_craft_water_point: New auto craft water point or None to keep current
            inventory_fruit_point: New inventory fruit point or None to keep current
            inventory_center_point: New inventory center point or None to keep current
            yes_button: New yes button coordinates or None to keep current
            middle_button: New middle button coordinates or None to keep current
            no_button: New no button coordinates or None to keep current
        """
        if top_bait_point is not None:
            self.top_bait_point = top_bait_point
        if fruit_point is not None:
            self.fruit_point = fruit_point
        if water_point is not None:
            self.water_point = water_point
        if auto_craft_water_point is not None:
            self.auto_craft_water_point = auto_craft_water_point
        if inventory_fruit_point is not None:
            self.inventory_fruit_point = inventory_fruit_point
        if inventory_center_point is not None:
            self.inventory_center_point = inventory_center_point
        if yes_button is not None:
            self.yes_button = yes_button
        if middle_button is not None:
            self.middle_button = middle_button
        if no_button is not None:
            self.no_button = no_button

    @property
    def running(self):
        """Get running state from callback"""
        return self.get_running()

    @property
    def first_run(self):
        """Get first_run state from callback"""
        return self.get_first_run()

    @first_run.setter
    def first_run(self, value):
        """Set first_run state via callback"""
        self.set_first_run(value)

    @property
    def first_catch(self):
        """Get first_catch state from callback"""
        return self.get_first_catch()

    @first_catch.setter
    def first_catch(self, value):
        """Set first_catch state via callback"""
        self.set_first_catch(value)

    @property
    def mouse_pressed(self):
        """Get mouse_pressed state from callback"""
        return self.get_mouse_pressed()

    @mouse_pressed.setter
    def mouse_pressed(self, value):
        """Set mouse_pressed state via callback"""
        self.set_mouse_pressed(value)

    @property
    def fish_caught(self):
        """Get fish_caught from callback"""
        return self.get_fish_caught()

    @fish_caught.setter
    def fish_caught(self, value):
        """Increment fish_caught (setter used as += in original code)"""
        # Note: Original code does self.fish_caught += 1, so we use increment callback
        self.increment_fish_caught()

    @property
    def fruits_caught(self):
        """Get fruits_caught from callback"""
        return self.get_fruits_caught()

    @fruits_caught.setter
    def fruits_caught(self, value):
        """Increment fruits_caught (setter used as += in original code)"""
        self.increment_fruits_caught()

    @property
    def pid_last_error(self):
        return self.get_pid_last_error()

    @pid_last_error.setter
    def pid_last_error(self, value):
        self.set_pid_last_error(value)

    @property
    def pid_last_time(self):
        return self.get_pid_last_time()

    @pid_last_time.setter
    def pid_last_time(self, value):
        self.set_pid_last_time(value)

    @property
    def detection_lost_counter(self):
        return self.get_detection_lost_counter()

    @detection_lost_counter.setter
    def detection_lost_counter(self, value):
        self.set_detection_lost_counter(value)

    @property
    def last_resend_time(self):
        return self.get_last_resend_time()

    @last_resend_time.setter
    def last_resend_time(self, value):
        self.set_last_resend_time(value)

    @property
    def fps_frame_count(self):
        return self.get_fps_frame_count()

    @fps_frame_count.setter
    def fps_frame_count(self, value):
        # Original uses += 1, so we call increment
        self.increment_fps_frame_count()

    @property
    def fps_last_time(self):
        return self.get_fps_last_time()

    @fps_last_time.setter
    def fps_last_time(self, value):
        self.set_fps_last_time(value)

    @property
    def detection_fps(self):
        return self.get_detection_fps()

    @detection_fps.setter
    def detection_fps(self, value):
        self.set_detection_fps(value)

    @property
    def last_craft_fish_count(self):
        return self.get_last_craft_fish_count()

    @last_craft_fish_count.setter
    def last_craft_fish_count(self, value):
        self.set_last_craft_fish_count(value)

    @property
    def last_error(self):
        """Placeholder for compatibility - not used in extracted methods"""
        return 0

    @last_error.setter
    def last_error(self, value):
        """Placeholder for compatibility - not used in extracted methods"""
        pass

    @property
    def last_bar_y(self):
        """Placeholder for compatibility - not used in extracted methods"""
        return 0

    @last_bar_y.setter
    def last_bar_y(self, value):
        """Placeholder for compatibility - not used in extracted methods"""
        pass

    @property
    def last_time(self):
        """Placeholder for compatibility - not used in extracted methods"""
        return time.time()

    @last_time.setter
    def last_time(self, value):
        """Placeholder for compatibility - not used in extracted methods"""
        pass

    # ========== MAIN LOOP (LITERAL COPY) ==========
    def main_loop(self):
        """Main fishing loop - orchestration and mode selection (LITERAL COPY from lines 3253-3450)"""
        try:
            self.logger.info("[Main Loop] ▶ Fishing loop started")
            while self.running:
                # Check pause state (F4 hotkey)
                while self.callbacks.get("get_paused", lambda: False)():
                    time.sleep(0.1)  # Wait for resume
                    if not self.running:  # Stopped during pause
                        return

                # SAFETY: Release mouse at start of every loop iteration
                if self.mouse_pressed:
                    self.mouse.mouse_event(0x0004, 0, 0)  # MOUSEEVENTF_LEFTUP
                    self.mouse_pressed = False

                # First run initialization
                if self.first_run:
                    self.set_status("First run setup")

                    # Focus Roblox window
                    self.window_manager.focus_roblox_window()
                    if not self.interruptible_sleep(0.5):
                        return

                    # Deselect (press everything_else_hotkey)
                    print(
                        f"\r[First Run] Deselecting ({self.everything_else_hotkey})...",
                        end="",
                        flush=True,
                    )
                    self.keyboard.press(self.everything_else_hotkey)
                    self.keyboard.release(self.everything_else_hotkey)
                    if not self.interruptible_sleep(self.rod_deselect_delay):
                        return

                    # Select rod (press rod_hotkey)
                    print(
                        f"\r[First Run] Selecting rod ({self.rod_hotkey})...",
                        end="",
                        flush=True,
                    )
                    self.keyboard.press(self.rod_hotkey)
                    self.keyboard.release(self.rod_hotkey)
                    if not self.interruptible_sleep(self.rod_select_delay):
                        return

                    # Camera initialization (zoom in 30, zoom out for standardized view)
                    print(f"\r[First Run] Initializing camera...", end="", flush=True)

                    # Scroll in 30 ticks (force first person guarantee)
                    for _ in range(30):
                        self.mouse.mouse_event(
                            0x0800, 0, 0, 120, 0
                        )  # MOUSEEVENTF_WHEEL, scroll up
                        if not self.interruptible_sleep(0.01):
                            return

                    if not self.interruptible_sleep(0.1):
                        return

                    # Scroll out based on disable_normal_camera setting (use dynamic getter)
                    if (
                        not self.get_disable_normal_camera()
                        or self.get_auto_craft_enabled()
                    ):
                        # Standard camera mode OR Auto Craft: zoom out 13 ticks
                        for _ in range(13):
                            self.mouse.mouse_event(
                                0x0800, 0, 0, -120, 0
                            )  # MOUSEEVENTF_WHEEL, scroll down
                            if not self.interruptible_sleep(0.01):
                                return
                    else:
                        # Disabled camera mode (simplified): zoom out 5 ticks
                        for _ in range(5):
                            self.mouse.mouse_event(
                                0x0800, 0, 0, -120, 0
                            )  # MOUSEEVENTF_WHEEL, scroll down
                            if not self.interruptible_sleep(0.01):
                                return

                    if not self.interruptible_sleep(self.rod_select_delay):
                        return

                    # Mark first run as complete
                    self.first_run = False
                    self.logger.info(
                        "[First Run] ✅ Setup complete (hotkeys, camera initialized)"
                    )
                    print("\r[First Run] ✅ Setup complete", end="", flush=True)

                # Mode selection: Auto Craft vs Normal (use dynamic getter)
                if self.get_auto_craft_enabled():
                    # ========== AUTO CRAFT MODE ==========
                    self.set_status("Auto Craft Mode")
                    self.logger.debug("[Main Loop] Mode: Auto Craft")

                    # Auto craft mode only runs auto_craft_pre_cast() in a loop
                    # pre_cast handles: craft -> cast -> zoom in -> wait -> fish -> zoom out -> fruit check -> store
                    if not self.auto_craft_pre_cast():
                        # Restart from beginning if pre_cast fails
                        if not self.interruptible_sleep(0.5):
                            return
                        continue

                    # Brief delay between cycles
                    if not self.interruptible_sleep(0.2):
                        return

                else:
                    # ========== NORMAL MODE ==========
                    # Start cycle timer
                    self.start_cycle_timer()
                    self.logger.debug(
                        f"[Main Loop] Mode: Normal | Fish count: {self.fish_caught}"
                    )

                    # Stage 1: Pre-cast (select bait, cast, wait for minigame)
                    self.set_status("Pre-casting")
                    if not self.pre_cast():
                        # Restart if pre_cast fails
                        if not self.interruptible_sleep(0.5):
                            return
                        continue

                    # Stage 2: Wait for colors (fish detection)
                    self.set_status("Scanning for fish")
                    if not self.esperar():
                        # Timeout or user stopped - restart from pre_cast
                        if not self.interruptible_sleep(0.5):
                            return
                        continue

                    # Stage 3: Fish (minigame with PID control)
                    self.set_status("Fishing")
                    while self.running and self.pesca():
                        pass  # Keep fishing while pesca() returns True

                    # Ensure mouse is released after fishing
                    if self.mouse_pressed:
                        self.mouse.mouse_event(0x0004, 0, 0)  # MOUSEEVENTF_LEFTUP
                        self.mouse_pressed = False

                    # Check for anti-macro after fishing
                    screenshot = self.screen.capture_area()
                    if screenshot is not None and self.anti_macro.is_black_screen(
                        screenshot
                    ):
                        self.logger.warning(
                            "[Main Loop] ⚠️ Anti-macro black screen detected after fishing!"
                        )
                        print(
                            f"\r⚠️  Anti-macro detected after fishing! Handling...",
                            end="",
                            flush=True,
                        )
                        if not self.handle_anti_macro_detection():
                            return  # User stopped
                        # Anti-macro cleared - restart from beginning
                        continue

                    # Camera restoration (rotate back 180° only - NO zoom out, already zoomed out in pre_cast)
                    self.set_status("Restoring camera")

                    # Rotate camera back 180° (reverse the rotation from pre_cast)
                    if not self.get_disable_normal_camera():
                        print(
                            f"\r[Normal] Rotating camera back 180°...",
                            end="",
                            flush=True,
                        )
                        self.mouse.mouse_event(
                            0x0008, 0, 0
                        )  # MOUSEEVENTF_RIGHTDOWN (right-click hold)
                        if not self.interruptible_sleep(self.camera_rotation_delay):
                            return

                        # Move mouse LEFT to rotate camera back (reverse direction)
                        for step in range(self.camera_rotation_steps):
                            if not self.running:
                                self.mouse.mouse_event(
                                    0x0010, 0, 0
                                )  # MOUSEEVENTF_RIGHTUP
                                return
                            self.mouse.mouse_event(
                                0x0001, -100, 0, 0, 0
                            )  # MOUSEEVENTF_MOVE, move LEFT 100 pixels
                            if not self.interruptible_sleep(
                                self.camera_rotation_step_delay
                            ):
                                return

                        if not self.interruptible_sleep(
                            self.camera_rotation_settle_delay
                        ):
                            return

                        self.mouse.mouse_event(
                            0x0010, 0, 0
                        )  # MOUSEEVENTF_RIGHTUP (release right-click)
                        time.sleep(0.1)

                    # Brief delay between cycles
                    if not self.interruptible_sleep(0.5):
                        return

        except Exception as e:
            self.logger.error(f"[Main Loop] ❌ Unhandled exception: {e}", exc_info=True)
            print(f"\rError in main loop: {e}", end="", flush=True)
            # SAFETY: Release mouse on exception
            if self.mouse_pressed:
                self.mouse.mouse_event(0x0004, 0, 0)  # MOUSEEVENTF_LEFTUP
                self.mouse_pressed = False

    # ========== NORMAL MODE METHODS (LITERAL COPY) ==========
    def pre_cast(self):
        """Stage 1 (Normal Mode): Pre-cast preparation (LITERAL COPY from lines 3897-4330)"""
        if not self.running:
            return False

        # Auto buy bait if enabled (use dynamic getter)
        if self.get_auto_buy_bait():
            self.set_status("Buying bait")
            bait_result = self.buy_common_bait()
            if not bait_result:
                print(
                    f"\r[Pre-cast] Auto buy bait returned False - stopping pre_cast",
                    end="",
                    flush=True,
                )
                return False
            print(
                f"\r[Pre-cast] Auto buy bait completed successfully", end="", flush=True
            )

        # Shift Lock Alignment (only when disable_normal_camera is enabled)
        if self.get_disable_normal_camera():
            print(
                f"\r[Pre-cast] Activating Shift Lock for alignment...",
                end="",
                flush=True,
            )
            self.keyboard.press(Key.shift)
            self.keyboard.release(Key.shift)
            if not self.interruptible_sleep(0.2):
                return False

            print(f"\r[Pre-cast] Deactivating Shift Lock...", end="", flush=True)
            self.keyboard.press(Key.shift)
            self.keyboard.release(Key.shift)
            if not self.interruptible_sleep(0.2):
                return False

        # Steps 1-4: Deselect rod, select rod, select bait, ALIGNMENT CAST
        # Skip these if disable_normal_camera is enabled - will be done after fruit check
        if not self.get_disable_normal_camera():
            # 1. Deselect rod
            self.set_status("Deselecting rod")
            print(
                f"\r[Pre-cast] Deselecting rod ({self.everything_else_hotkey})...",
                end="",
                flush=True,
            )
            self.keyboard.press(self.everything_else_hotkey)
            self.keyboard.release(self.everything_else_hotkey)
            if not self.interruptible_sleep(self.rod_deselect_delay):
                return False

            # 2. Select rod
            self.set_status("Selecting rod")
            print(
                f"\r[Pre-cast] Selecting rod ({self.rod_hotkey})...", end="", flush=True
            )
            self.keyboard.press(self.rod_hotkey)
            self.keyboard.release(self.rod_hotkey)
            if not self.interruptible_sleep(self.rod_select_delay):
                return False

            # 3. Auto Select Top Bait (NO Smart Bait in normal mode - only in auto_craft)
            if self.get_auto_select_top_bait() and self.top_bait_point:
                self.set_status("Selecting bait")
                print(
                    f"\r[Pre-cast] Selecting top bait at ({self.top_bait_point['x']}, {self.top_bait_point['y']})...",
                    end="",
                    flush=True,
                )
                self.mouse.click(
                    self.top_bait_point["x"], self.top_bait_point["y"], hold_delay=0.1
                )
                if not self.interruptible_sleep(self.bait_click_delay):
                    return False

            # 4. ALIGNMENT CAST to water point (first cast - before fruit check)
            if not self.water_point:
                print("\r[Pre-cast] ✗ No water point set!", end="", flush=True)
                if not self.interruptible_sleep(1):
                    return False
                return False

            self.set_status("Casting rod (alignment)")
            print(
                f"\r[Pre-cast] Casting to water point ({self.water_point['x']}, {self.water_point['y']})...",
                end="",
                flush=True,
            )
            self.mouse.click(
                self.water_point["x"],
                self.water_point["y"],
                hold_delay=self.cast_hold_duration,
            )
            if not self.interruptible_sleep(self.mouse_move_settle):
                return False

            # Wait 0.3s after alignment cast
            print("\r[Pre-cast] Waiting 0.3s...", end="", flush=True)
            if not self.interruptible_sleep(0.3):
                return False

        # Auto Store Fruit sequence (V3)
        if self.get_auto_store_fruit():
            # 6a. Deselect rod BEFORE fruit check
            print(
                f"\r[Pre-cast] Deselecting rod ({self.everything_else_hotkey}) before fruit check...",
                end="",
                flush=True,
            )
            self.keyboard.press(self.everything_else_hotkey)
            self.keyboard.release(self.everything_else_hotkey)
            if not self.interruptible_sleep(0.2):
                return False

            # 6b. Press fruit hotkey
            self.set_status("Checking for fruit")
            print(
                f"\r[Pre-cast] Pressing fruit hotkey ({self.fruit_hotkey})...",
                end="",
                flush=True,
            )
            self.keyboard.press(self.fruit_hotkey)
            self.keyboard.release(self.fruit_hotkey)
            if not self.interruptible_sleep(self.fruit_hold_delay):
                return False

            # 7. Check for fruit color
            fruit_detected = False  # Track if fruit was detected
            if self.fruit_point and self.fruit_color:
                print(
                    f"\r[Pre-cast] Checking for fruit at ({self.fruit_point['x']}, {self.fruit_point['y']})...",
                    end="",
                    flush=True,
                )
                try:
                    with mss.mss() as sct:
                        monitor = {
                            "top": self.fruit_point["y"],
                            "left": self.fruit_point["x"],
                            "width": 1,
                            "height": 1,
                        }
                        screenshot = sct.grab(monitor)
                        pixel = screenshot.pixel(0, 0)
                        current_color = (pixel[2], pixel[1], pixel[0])  # BGR

                        tolerance = 5
                        color_match = (
                            abs(current_color[0] - self.fruit_color[0]) <= tolerance
                            and abs(current_color[1] - self.fruit_color[1]) <= tolerance
                            and abs(current_color[2] - self.fruit_color[2]) <= tolerance
                        )
                        fruit_detected = color_match  # Store result for later use

                        if color_match:
                            # FRUIT DETECTED
                            if not self.first_catch:
                                self.fruits_caught += 1
                                self.set_fish_at_last_fruit(self.fish_caught)
                                if self.stats_manager:
                                    self.stats_manager.log_fruit()
                                print(
                                    f"\r🍎 FRUIT DETECTED! Total: {self.fruits_caught}",
                                    end="",
                                    flush=True,
                                )
                            else:
                                self.fruits_caught += 1
                                if self.stats_manager:
                                    self.stats_manager.log_fruit()
                                print(
                                    f"\r🍎 FRUIT DETECTED! Total: {self.fruits_caught} (First catch)",
                                    end="",
                                    flush=True,
                                )
                                self.first_catch = False

                            # Decide if we should zoom + screenshot (same logic as Auto Craft mode)
                            do_zoom_and_ss = True
                            is_legendary = False  # Initialize flag
                            if self.get_webhook_only_legendary():
                                # Only zoom/SS when pity says Legendary/Mythical (0/40)
                                is_legendary = self.check_legendary_pity()
                                if not is_legendary:
                                    do_zoom_and_ss = False
                                    print(
                                        f"\r[Pre-cast] Pity filter ON and not 0/40 → skipping zoom/screenshot",
                                        end="",
                                        flush=True,
                                    )

                            screenshot_path = None
                            if do_zoom_and_ss:
                                # Zoom in for screenshot (if camera enabled)
                                if not self.get_disable_normal_camera():
                                    print(
                                        f"\r[Pre-cast] Zooming in {self.zoom_ticks} ticks for screenshot...",
                                        end="",
                                        flush=True,
                                    )
                                    for _ in range(self.zoom_ticks):
                                        self.mouse.mouse_event(0x0800, 0, 0, 120, 0)
                                        if not self.interruptible_sleep(
                                            self.zoom_tick_delay
                                        ):
                                            return False
                                    if not self.interruptible_sleep(
                                        self.zoom_settle_delay
                                    ):
                                        return False

                                if not self.interruptible_sleep(0.2):
                                    return False

                                # Take screenshot
                                print(
                                    f"\r[Pre-cast] 📸 Capturing screenshot...",
                                    end="",
                                    flush=True,
                                )
                                screenshot_path = self.screen.capture_center()

                                if not self.interruptible_sleep(0.2):
                                    return False

                                # Zoom out after screenshot
                                if not self.get_disable_normal_camera():
                                    print(
                                        f"\r[Pre-cast] Zooming out {self.zoom_ticks} ticks...",
                                        end="",
                                        flush=True,
                                    )
                                    for _ in range(self.zoom_ticks):
                                        self.mouse.mouse_event(0x0800, 0, 0, -120, 0)
                                        if not self.interruptible_sleep(
                                            self.zoom_tick_delay
                                        ):
                                            return False
                                    if not self.interruptible_sleep(
                                        self.zoom_settle_delay
                                    ):
                                        return False

                                # Send webhook (pass is_legendary to avoid duplicate pity check)
                                if screenshot_path:
                                    self.send_fruit_webhook(
                                        screenshot_path, is_legendary=is_legendary
                                    )
                        else:
                            # FISH (not fruit) - DON'T count here, wait for minigame completion
                            if not self.first_catch:
                                print(
                                    f"\r🐟 Fish detected (will count after minigame)",
                                    end="",
                                    flush=True,
                                )
                            else:
                                print(
                                    f"\r[Pre-cast] First cycle - not counting",
                                    end="",
                                    flush=True,
                                )
                                self.first_catch = False
                except Exception as e:
                    print(
                        f"\r[Pre-cast] Warning: Fruit check error: {e}",
                        end="",
                        flush=True,
                    )
                    if self.first_catch:
                        self.first_catch = False

            # 8. Click Store button (ONLY if fruit detected)
            if fruit_detected and self.fruit_point:
                print(
                    f"\r[Pre-cast] Clicking fruit point to store...", end="", flush=True
                )
                self.mouse.click(
                    self.fruit_point["x"], self.fruit_point["y"], hold_delay=0.1
                )
                if not self.interruptible_sleep(self.store_click_delay):
                    return False

                # 9. Handle fruit storage (Drop vs Inventory) - ONLY runs when fruit detected
                if self.get_store_in_inventory() and self.inventory_fruit_point:
                    print(f"\r[Pre-cast] Storing in inventory...", end="", flush=True)
                    self.keyboard.press("`")
                    self.keyboard.release("`")
                    if not self.interruptible_sleep(0.5):
                        return False

                    inv_x = self.inventory_fruit_point["x"]
                    inv_y = self.inventory_fruit_point["y"]
                    center_x = (
                        self.inventory_center_point["x"]
                        if self.inventory_center_point
                        else SCREEN_WIDTH // 2
                    )
                    center_y = (
                        self.inventory_center_point["y"]
                        if self.inventory_center_point
                        else SCREEN_HEIGHT // 2
                    )

                    print(
                        f"\r[Pre-cast] Dragging from ({inv_x},{inv_y}) to ({center_x},{center_y})...",
                        end="",
                        flush=True,
                    )
                    self.mouse.drag(inv_x, inv_y, center_x, center_y)

                    if not self.interruptible_sleep(0.2):
                        return False
                    if not self.interruptible_sleep(0.2):
                        return False

                    self.keyboard.press("`")
                    self.keyboard.release("`")
                    if not self.interruptible_sleep(0.5):
                        return False
                else:
                    if self.get_store_in_inventory() and not self.inventory_fruit_point:
                        print(
                            f"\r[Pre-cast] WARNING - Inventory store enabled but no point set!",
                            end="",
                            flush=True,
                        )

                    print(
                        f"\r[Pre-cast] Pressing backspace to drop...",
                        end="",
                        flush=True,
                    )
                    self.keyboard.press(Key.backspace)
                    self.keyboard.release(Key.backspace)
                    if not self.interruptible_sleep(self.backspace_delay):
                        return False
            # 10. Deselect rod AFTER fruit
            print(
                f"\r[Pre-cast] Deselecting rod ({self.everything_else_hotkey}) after fruit...",
                end="",
                flush=True,
            )
            self.keyboard.press(self.everything_else_hotkey)
            self.keyboard.release(self.everything_else_hotkey)
            if not self.interruptible_sleep(self.rod_deselect_delay):
                return False

            # 11. Select rod AFTER fruit
            print(
                f"\r[Pre-cast] Selecting rod ({self.rod_hotkey}) after fruit...",
                end="",
                flush=True,
            )
            self.keyboard.press(self.rod_hotkey)
            self.keyboard.release(self.rod_hotkey)
            if not self.interruptible_sleep(self.rod_select_delay):
                return False

            # 12. Select bait AFTER fruit
            if self.get_auto_select_top_bait() and self.top_bait_point:
                print(f"\r[Pre-cast] Selecting top bait again...", end="", flush=True)
                self.mouse.click(
                    self.top_bait_point["x"], self.top_bait_point["y"], hold_delay=0.1
                )
                if not self.interruptible_sleep(self.bait_click_delay):
                    return False

            # 13. FISHING CAST to water point (second cast - for actual fishing)
            print(
                f"\r[Pre-cast] Casting to water point again ({self.water_point['x']}, {self.water_point['y']})...",
                end="",
                flush=True,
            )
            self.mouse.move_to(self.water_point["x"], self.water_point["y"])
            self.mouse.mouse_event(0x0001, 0, 1, 0, 0)  # MOUSEEVENTF_MOVE 1px down
            if not self.interruptible_sleep(self.mouse_move_settle):
                return False
            self.mouse.mouse_event(0x0002, 0, 0)  # LEFTDOWN
            if not self.interruptible_sleep(self.cast_hold_duration):
                self.mouse.mouse_event(0x0004, 0, 0)  # LEFTUP
                return False
            self.mouse.mouse_event(0x0004, 0, 0)  # LEFTUP

            if not self.interruptible_sleep(self.bait_click_delay):
                return False

            # 14-17. Camera/zoom/rotation (skip if disable_normal_camera)
            if not self.get_disable_normal_camera():
                # 14. Wait before rotation
                print(
                    "\r[Pre-cast] Waiting before camera rotation...", end="", flush=True
                )
                if not self.interruptible_sleep(0.6):
                    return False

                # 15. Rotate camera 180°
                print("\r[Pre-cast] Rotating camera 180°...", end="", flush=True)
                self.mouse.mouse_event(0x0008, 0, 0)  # MOUSEEVENTF_RIGHTDOWN
                if not self.interruptible_sleep(self.camera_rotation_delay):
                    return False
                for _ in range(self.camera_rotation_steps):
                    self.mouse.mouse_event(
                        0x0001, 100, 0, 0, 0
                    )  # MOUSEEVENTF_MOVE right
                    if not self.interruptible_sleep(self.camera_rotation_step_delay):
                        return False
                if not self.interruptible_sleep(self.camera_rotation_settle_delay):
                    return False
                self.mouse.mouse_event(0x0010, 0, 0)  # MOUSEEVENTF_RIGHTUP
                if not self.interruptible_sleep(self.camera_rotation_settle_delay):
                    return False

                # 16. Zoom in 3 ticks after rotation
                print(
                    f"\r[Pre-cast] Zooming in {self.zoom_ticks} ticks...",
                    end="",
                    flush=True,
                )
                for _ in range(self.zoom_ticks):
                    self.mouse.mouse_event(0x0800, 0, 0, 120, 0)
                    if not self.interruptible_sleep(self.zoom_tick_delay):
                        return False
                if not self.interruptible_sleep(self.zoom_settle_delay):
                    return False

                # 17. Wait for minigame
                print(
                    "\r[Pre-cast] Waiting for minigame to appear...", end="", flush=True
                )
                if not self.interruptible_sleep(self.pre_cast_minigame_wait):
                    return False
            else:
                print("\r[Pre-cast] (Camera/zoom/rotation skipped)", end="", flush=True)
                if not self.interruptible_sleep(self.pre_cast_minigame_wait):
                    return False
        else:
            # Auto Store Fruit DISABLED - do full sequence now
            if self.get_disable_normal_camera():
                # We skipped deselect/select/bait/cast above, do them now
                # 1. Deselect rod
                self.set_status("Deselecting rod")
                print(
                    f"\r[Pre-cast] Deselecting rod ({self.everything_else_hotkey})...",
                    end="",
                    flush=True,
                )
                self.keyboard.press(self.everything_else_hotkey)
                self.keyboard.release(self.everything_else_hotkey)
                if not self.interruptible_sleep(self.rod_deselect_delay):
                    return False

                # 2. Select rod
                self.set_status("Selecting rod")
                print(
                    f"\r[Pre-cast] Selecting rod ({self.rod_hotkey})...",
                    end="",
                    flush=True,
                )
                self.keyboard.press(self.rod_hotkey)
                self.keyboard.release(self.rod_hotkey)
                if not self.interruptible_sleep(self.rod_select_delay):
                    return False

                # 3. Select bait
                if self.get_auto_select_top_bait() and self.top_bait_point:
                    self.set_status("Selecting bait")
                    print(f"\r[Pre-cast] Selecting top bait...", end="", flush=True)
                    self.mouse.click(
                        self.top_bait_point["x"],
                        self.top_bait_point["y"],
                        hold_delay=0.1,
                    )
                    if not self.interruptible_sleep(self.bait_click_delay):
                        return False

                # 4. Cast
                self.set_status("Casting rod")
                print(f"\r[Pre-cast] Casting to water point...", end="", flush=True)
                self.mouse.click(
                    self.water_point["x"],
                    self.water_point["y"],
                    hold_delay=self.cast_hold_duration,
                )
                if not self.interruptible_sleep(self.mouse_move_settle):
                    return False

                # Skip camera, wait for minigame
                print("\r[Pre-cast] (Camera/zoom/rotation skipped)", end="", flush=True)
                if not self.interruptible_sleep(self.pre_cast_minigame_wait):
                    return False
            else:
                # Normal camera mode, no fruit check
                # 14. Wait before rotation
                print(
                    "\r[Pre-cast] Waiting before camera rotation...", end="", flush=True
                )
                if not self.interruptible_sleep(0.6):
                    return False

                # 15. Rotate camera 180°
                print("\r[Pre-cast] Rotating camera 180°...", end="", flush=True)
                self.mouse.mouse_event(0x0008, 0, 0)  # MOUSEEVENTF_RIGHTDOWN
                if not self.interruptible_sleep(self.camera_rotation_delay):
                    return False
                for _ in range(self.camera_rotation_steps):
                    self.mouse.mouse_event(0x0001, 100, 0, 0, 0)
                    if not self.interruptible_sleep(self.camera_rotation_step_delay):
                        return False
                if not self.interruptible_sleep(self.camera_rotation_settle_delay):
                    return False
                self.mouse.mouse_event(0x0010, 0, 0)  # MOUSEEVENTF_RIGHTUP
                if not self.interruptible_sleep(self.camera_rotation_settle_delay):
                    return False

                # 16. Zoom in
                print(
                    f"\r[Pre-cast] Zooming in {self.zoom_ticks} ticks...",
                    end="",
                    flush=True,
                )
                for _ in range(self.zoom_ticks):
                    self.mouse.mouse_event(0x0800, 0, 0, 120, 0)
                    if not self.interruptible_sleep(self.zoom_tick_delay):
                        return False
                if not self.interruptible_sleep(self.zoom_settle_delay):
                    return False

                # 17. Wait for minigame
                print(
                    "\r[Pre-cast] Waiting for minigame to appear...", end="", flush=True
                )
                if not self.interruptible_sleep(self.pre_cast_minigame_wait):
                    return False

        if not self.interruptible_sleep(0.5):
            return False
        return True

    def buy_common_bait(self):
        """Buy common bait from shop (LITERAL COPY from lines 4332-4429)"""
        # Validate required button coordinates
        if not self.yes_button or not self.middle_button or not self.no_button:
            print(
                "\r⚠️ Auto Buy Bait: Button coordinates not set! Please configure Yes, Middle, and No buttons.",
                end="",
                flush=True,
            )
            if not self.interruptible_sleep(2):
                return False
            return True  # Continue anyway

        # Check bait loop counter
        if self.bait_loop_counter > 0:
            # Still have bait loops left, decrement and skip
            self.bait_loop_counter -= 1
            print(
                f"\rAuto Buy Bait: Skipping ({self.bait_loop_counter} loops until next purchase)",
                end="",
                flush=True,
            )
            return True

        # Execute purchase sequence (V4 behavior - uses interruptible_sleep)
        try:
            print("\r[Auto Buy Bait] Starting purchase sequence...", end="", flush=True)

            # 1) Press 'e' key, wait 3s
            self.keyboard.press("e")
            self.keyboard.release("e")
            if not self.running or not self.interruptible_sleep(3):
                print(
                    "\r[Auto Buy Bait] CANCELLED at step 1 (after E press)",
                    end="",
                    flush=True,
                )
                return False

            # 2) Click yes button, wait 3s
            if not self.running:
                print(
                    "\r[Auto Buy Bait] CANCELLED at step 2 (before Yes click)",
                    end="",
                    flush=True,
                )
                return False
            self.mouse.click(self.yes_button["x"], self.yes_button["y"], hold_delay=0.1)
            if not self.interruptible_sleep(3):
                print(
                    "\r[Auto Buy Bait] CANCELLED at step 2 (after Yes click)",
                    end="",
                    flush=True,
                )
                return False

            # 3) Click middle button, wait 3s
            if not self.running:
                print(
                    "\r[Auto Buy Bait] CANCELLED at step 3 (before Middle click)",
                    end="",
                    flush=True,
                )
                return False
            self.mouse.click(
                self.middle_button["x"], self.middle_button["y"], hold_delay=0.1
            )
            if not self.interruptible_sleep(3):
                print(
                    "\r[Auto Buy Bait] CANCELLED at step 3 (after Middle click)",
                    end="",
                    flush=True,
                )
                return False

            # 4) Type number (loops per purchase)
            if not self.running:
                print(
                    f"\r[Auto Buy Bait] CANCELLED at step 4 (before typing {self.loops_per_purchase})",
                    end="",
                    flush=True,
                )
                return False
            number_str = str(self.loops_per_purchase)
            for char in number_str:
                if not self.running:
                    print(
                        f"\r[Auto Buy Bait] CANCELLED while typing character '{char}'",
                        end="",
                        flush=True,
                    )
                    return False
                self.keyboard.press(char)
                self.keyboard.release(char)
                if not self.interruptible_sleep(self.general_action_delay):
                    print(
                        f"\r[Auto Buy Bait] CANCELLED during typing delay",
                        end="",
                        flush=True,
                    )
                    return False
            if not self.interruptible_sleep(0.5):
                print(
                    "\r[Auto Buy Bait] CANCELLED after typing number",
                    end="",
                    flush=True,
                )
                return False

            # 5) Click yes button, wait 3s
            if not self.running:
                return False
            self.mouse.click(self.yes_button["x"], self.yes_button["y"], hold_delay=0.1)
            if not self.interruptible_sleep(3):
                return False

            # 6) Click no button (cancel to avoid problems), wait 3s
            if not self.running:
                return False
            self.mouse.click(self.no_button["x"], self.no_button["y"], hold_delay=0.1)
            if not self.interruptible_sleep(3):
                return False

            # 7) Click middle button again, wait 3s
            if not self.running:
                return False
            self.mouse.click(
                self.middle_button["x"], self.middle_button["y"], hold_delay=0.1
            )
            if not self.interruptible_sleep(3):
                return False

            # Set counter to loops_per_purchase for next time (AFTER successful purchase)
            self.bait_loop_counter = self.loops_per_purchase

            print(
                f"\r✓ Bait purchased! Next purchase in {self.loops_per_purchase} loops.",
                end="",
                flush=True,
            )
            self.logger.info(
                f"[Auto Buy Bait] ✅ Purchase complete. Next in {self.loops_per_purchase} loops"
            )
            return True

        except Exception as e:
            self.logger.error(f"[Auto Buy Bait] ❌ Error: {e}", exc_info=True)
            print(f"\rError buying bait: {e}", end="", flush=True)
            return True  # Continue anyway

    def esperar(self):
        """Stage 2: Wait for fish - Cast and wait for colors to appear (LITERAL COPY from lines 4098-4371)"""
        if not self.running:
            return False

        # Check if area is set
        if not self.area_coords:
            print("\rWaiting: ✗ No area set!", end="", flush=True)
            if not self.interruptible_sleep(1):
                return False
            return False

        # Rod already selected in pre_cast, just need to cast and wait for colors
        print(
            f"\rScanning for colors (timeout: {self.recast_timeout}s)...",
            end="",
            flush=True,
        )

        # Performance: Frame skip counter (only process every 3rd frame)
        frame_counter = 0

        # Step 5: Start scanning for colors with timeout
        start_time = time.time()
        target_colors = [
            (85, 170, 255),  # Blue #55aaff - Main bar
            (255, 255, 255),  # White #ffffff - Center line
            (25, 25, 25),  # Black #191919 - Borders/shadows
            (170, 255, 0),  # Green-yellow #aaff00 - UI element
            (32, 34, 36),  # Dark gray #202224 - Frame/background
        ]

        while self.running:
            # Check timeout
            elapsed_time = time.time() - start_time
            if elapsed_time >= self.recast_timeout:
                self.logger.debug(
                    f"[Esperar] ⏰ Timeout ({self.recast_timeout}s) - No colors. Recasting."
                )
                print(
                    f"\rWaiting: ✗ Timeout ({self.recast_timeout}s) - No colors found. Recasting...",
                    end="",
                    flush=True,
                )
                return False  # Timeout - restart from pre_cast

            # Performance: Skip frames (only process every 3rd frame = ~20 FPS for detection - lower CPU)
            frame_counter += 1
            if frame_counter % 3 != 0:
                if not self.interruptible_sleep(
                    0.03
                ):  # 30ms sleep between skipped frames (lower CPU)
                    return False
                continue

            # Capture screenshot of minigame area (set by user)
            screenshot = self.screen.capture_area()

            if screenshot is not None:
                # Check for anti-macro black screen
                if self.anti_macro.is_black_screen(screenshot):
                    self.logger.warning(
                        "[Esperar] ⚠️ Anti-macro black screen detected during scanning!"
                    )
                    print(
                        f"\r⚠️  Anti-macro detected during scanning! Handling...",
                        end="",
                        flush=True,
                    )
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
                    self.logger.info(
                        f"[Esperar] ✅ All colors detected after {elapsed_time:.1f}s - starting fishing"
                    )
                    print(
                        f"\rWaiting: ✓ All colors detected! Starting fishing... (took {elapsed_time:.1f}s)",
                        end="",
                        flush=True,
                    )
                    return True  # All colors found - proceed to fishing
                else:
                    # Still waiting
                    print(
                        f"\rWaiting for colors... ({elapsed_time:.1f}s/{self.recast_timeout}s)",
                        end="",
                        flush=True,
                    )

            # Small delay to avoid excessive CPU usage (interruptible)
            # Increased from fruit_detection_delay to reduce CPU load
            if not self.interruptible_sleep(max(self.fruit_detection_delay, 0.05)):
                return False

        return False

    def pesca(self):
        """Stage 3: Fish catch (LITERAL COPY from lines 4372-4898)"""
        if not self.running:
            # Release mouse if stopping
            if self.mouse_pressed:
                self.mouse.mouse_event(0x0004, 0, 0)  # MOUSEEVENTF_LEFTUP
                self.mouse_pressed = False
            return False

        # SAFETY: Ensure mouse is always released on exception
        try:
            return self._pesca_internal()
        finally:
            # Guarantee mouse release even on unexpected errors
            if self.mouse_pressed:
                try:
                    self.mouse.mouse_event(0x0004, 0, 0)  # MOUSEEVENTF_LEFTUP
                    self.mouse_pressed = False
                except Exception:
                    pass  # Ignore errors during cleanup (but not KeyboardInterrupt)

    def _pesca_internal(self):
        """Internal pesca logic with guaranteed cleanup"""

        # Limit minigame FPS to prevent excessive CPU usage and lag
        # Target: 60 FPS to match Roblox (16.67ms per frame)
        loop_start_time = time.time()

        # V3: Calculate detection FPS
        self.local_fps_frame_count += 1
        current_time = time.time()
        elapsed = current_time - self.local_fps_last_time
        if elapsed >= 1.0:  # Update FPS every second
            fps = self.local_fps_frame_count / elapsed
            self.set_detection_fps(fps)  # Push to GUI
            self.local_fps_frame_count = 0
            self.local_fps_last_time = current_time

        # Target color to detect
        target_color = (85, 170, 255)  # RGB: #55aaff

        # Take screenshot of the selected area
        # CRITICAL: Disable cache for minigame - needs fresh screenshots every frame for accurate tracking
        screenshot = self.screen.capture_area(use_cache=False)

        if screenshot is not None:
            # Check if target color exists in screenshot and get middle X coordinate
            color_found, middle_x = self.check_color_in_image(screenshot, target_color)

            # Print result (1 line per loop)
            if color_found:
                # Convert relative X to absolute screen coordinate
                absolute_x = self.area_coords["x"] + middle_x

                # Crop the screenshot to a 1-pixel wide vertical line at middle_x
                vertical_line = self.crop_vertical_line(screenshot, middle_x)

                if vertical_line is not None:
                    # Find topmost and bottommost black pixels
                    black_color = (25, 25, 25)  # #191919
                    top_y, bottom_y = self.find_topmost_bottommost_color(
                        vertical_line, black_color
                    )

                    if top_y is not None and bottom_y is not None:
                        # Second crop: Extract only the section between top_y and bottom_y
                        cropped_section = self.crop_vertical_section(
                            vertical_line, top_y, bottom_y
                        )

                        if cropped_section is not None:
                            # Find white color in the cropped section
                            white_color = (255, 255, 255)  # #FFFFFF
                            white_top, white_bottom = (
                                self.find_topmost_bottommost_color(
                                    cropped_section, white_color, tolerance=5
                                )
                            )

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
                                black_group_middle = self.find_biggest_black_group(
                                    cropped_section, black_color_alt, max_gap
                                )

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
                                        d_term = (
                                            self.pid_kd
                                            * (error - self.pid_last_error)
                                            / dt
                                        )

                                        # PD output with clamp
                                        pd_output = p_term + d_term
                                        pd_output = max(
                                            -self.pid_clamp,
                                            min(self.pid_clamp, pd_output),
                                        )  # Apply clamp

                                        # Convert to duty cycle (0 to 1)
                                        # Normalize by clamp*2 so pd_output range [-clamp, +clamp] maps to duty_cycle [0, 1]
                                        duty_cycle = 0.5 + (
                                            pd_output / (self.pid_clamp * 2)
                                        )
                                        duty_cycle = max(
                                            0.0, min(1.0, duty_cycle)
                                        )  # Ensure in range

                                        # Simple control: just check if we should hold or release
                                        should_hold = duty_cycle > 0.5

                                        # ALWAYS send the command, don't check previous state
                                        if should_hold:
                                            if not self.mouse_pressed:
                                                self.mouse.left_down()
                                                self.mouse_pressed = True
                                        else:
                                            if self.mouse_pressed:
                                                self.mouse.left_up()
                                                self.mouse_pressed = False

                                        # RESEND MECHANISM: Fix Roblox click bug where bar drops even when arrows track
                                        # Every resend_interval (default 500ms), resend the current mouse state
                                        if (
                                            current_time - self.last_resend_time
                                            >= self.resend_interval
                                        ):
                                            # Resend the current state to fix "bugged" bar
                                            if self.mouse_pressed:
                                                self.mouse.left_down()
                                            else:
                                                self.mouse.left_up()
                                            self.last_resend_time = current_time

                                        # Update PD state
                                        self.pid_last_error = error
                                        self.pid_last_time = current_time

                                        print(
                                            f"\rW:{white_middle} B:{black_group_middle} E:{error:+.0f} PD:{pd_output:+.2f} D:{duty_cycle:.2f} {'HOLD' if should_hold else 'FREE'} [{'ON' if self.mouse_pressed else 'OFF'}]",
                                            end="",
                                            flush=True,
                                        )

                                else:
                                    # Black group not found - increment lost counter
                                    self.detection_lost_counter += 1

                                    # Only release if we've lost detection for too many frames
                                    if (
                                        self.detection_lost_counter
                                        > self.max_lost_frames
                                    ):
                                        if self.mouse_pressed:
                                            self.mouse.left_up()
                                            self.mouse_pressed = False
                                        self.pid_last_error = 0.0
                                        print(
                                            f"\rBlue: \u2713 | X: {middle_x} | BlackGroup: LOST ({self.detection_lost_counter} frames)  ",
                                            end="",
                                            flush=True,
                                        )
                                    else:
                                        # Keep last state - don't change mouse
                                        print(
                                            f"\rBlue: \u2713 | X: {middle_x} | BlackGroup: TEMP LOST ({self.detection_lost_counter}/{self.max_lost_frames}) - Keeping last state  ",
                                            end="",
                                            flush=True,
                                        )

                            else:
                                # Hold mouse if white not found (to make it go to the top)
                                # This is because sometimes the white line gets behind text
                                if not self.mouse_pressed:
                                    self.mouse.left_down()
                                    self.mouse_pressed = True

                                # Reset PD
                                self.pid_last_error = 0.0

                                print(
                                    f"\rBlue: ✓ | X: {middle_x} | Black Y:[{top_y},{bottom_y}] | White: NOT FOUND - HOLDING  ",
                                    end="",
                                    flush=True,
                                )
                        else:
                            print(
                                f"\rBlue: ✓ | Middle X: {middle_x} | Black Top Y: {top_y} | Bottom Y: {bottom_y}  ",
                                end="",
                                flush=True,
                            )
                    else:
                        print(
                            f"\rBlue: ✓ | Middle X: {middle_x} | Black pixels NOT FOUND  ",
                            end="",
                            flush=True,
                        )
                else:
                    print(
                        f"\rBlue color {target_color}: ✓ FOUND | Middle X: {middle_x}  ",
                        end="",
                        flush=True,
                    )

            else:
                print(
                    f"\rBlue color {target_color}: ✗ NOT FOUND - Exiting fishing state  ",
                    end="",
                    flush=True,
                )
                # Release mouse when exiting fishing state
                if self.mouse_pressed:
                    self.mouse.left_up()
                    self.mouse_pressed = False

                # Reset PD
                self.pid_last_error = 0.0

                # Minigame completed successfully - count the fish
                if not self.first_catch:
                    self.fish_caught += 1
                    if self.stats_manager:
                        self.stats_manager.log_fish()
                    self.logger.info(
                        f"[Pesca] 🐟 Fish caught! Total: {self.fish_caught}"
                    )
                    print(
                        f"\r🐟 Fish caught! Total: {self.fish_caught}  ",
                        end="",
                        flush=True,
                    )
                    # End cycle timer (successful fish catch)
                    self.end_cycle_timer()
                else:
                    self.first_catch = False

                # Exit fishing state - return False to restart main loop
                return False
        else:
            print(f"\rNo area selected - skipping color check  ", end="", flush=True)

        # FPS limiter: Force 60 FPS cap (always sleep at least the frame time)
        loop_elapsed = time.time() - loop_start_time
        target_frame_time = 1.0 / 60.0  # 16.67ms per frame
        sleep_time = max(0.001, target_frame_time - loop_elapsed)  # Minimum 1ms
        time.sleep(sleep_time)

        # Blue color found - stay in fishing state
        return True

    # ========== AUTO CRAFT MODE METHODS (LITERAL COPY) ==========
    def auto_craft_pre_cast(self):
        """Stage 1 (Auto Craft Mode): Pre-cast preparation for auto craft (LITERAL COPY from lines 4372-4814)"""
        if not self.running:
            return False

        # Start cycle timer for auto craft mode
        self.start_cycle_timer()

        # Auto Craft Mode doesn't buy bait - it crafts instead
        # Check if we need to run craft cycle
        # craft_every_n_fish = 0 means craft on every cast
        should_craft = False
        if self.craft_every_n_fish == 0:
            # craft_every_n_fish = 0 means craft before every cast
            should_craft = True
        elif self.craft_every_n_fish > 0 and (
            self.fish_caught == 0 or self.fish_caught % self.craft_every_n_fish == 0
        ):
            # Craft on first run or after catching N fish
            # Check if we already crafted for this fish count (prevents loop on failed cast)
            if (
                not hasattr(self, "_last_craft_fish_count")
                or self.fish_caught != self.last_craft_fish_count
            ):
                should_craft = True

        if should_craft:
            self.set_status("Auto Crafting")
            print(
                f"\r⚒️ Auto Craft: Running craft cycle (fish caught: {self.fish_caught})...",
                end="",
                flush=True,
            )
            self.craft_automation.run_craft_sequence()
            self.last_craft_fish_count = self.fish_caught  # Mark this count as crafted
            # Don't reset fish_caught - let it accumulate
            if not self.interruptible_sleep(0.1):  # Faster craft cycle
                return False

        # New flow: craft -> shift lock alignment -> cast -> zoom -> wait -> fish -> zoom out -> check fruit -> store
        try:
            fruit_detected = False  # Flag to track if fruit was caught

            # ============ PART 1: ALIGNMENT ============
            # 1. Shift Lock Alignment (replaces the old casting for alignment)
            print(
                f"\r[Auto Craft] Activating Shift Lock for alignment...",
                end="",
                flush=True,
            )
            self.keyboard.press(Key.shift)
            self.keyboard.release(Key.shift)
            if not self.interruptible_sleep(0.08):  # Faster alignment
                return False

            print(f"\r[Auto Craft] Deactivating Shift Lock...", end="", flush=True)
            self.keyboard.press(Key.shift)
            self.keyboard.release(Key.shift)
            if not self.interruptible_sleep(0.08):  # Faster alignment
                return False

            # ============ PART 2: CASTING & MINIGAME ============
            # 2. Deselect rod (press everything_else_hotkey to deselect)
            print(
                f"\r[Auto Craft] Deselecting rod ({self.everything_else_hotkey})...",
                end="",
                flush=True,
            )
            self.keyboard.press(self.everything_else_hotkey)
            self.keyboard.release(self.everything_else_hotkey)
            if not self.interruptible_sleep(self.rod_deselect_delay):
                return False

            # 3. Select rod (press rod_hotkey)
            print(
                f"\r[Auto Craft] Selecting rod ({self.rod_hotkey})...",
                end="",
                flush=True,
            )
            self.keyboard.press(self.rod_hotkey)
            self.keyboard.release(self.rod_hotkey)
            if not self.interruptible_sleep(self.rod_select_delay):
                return False

            # 4. Bait Selection - Try Smart Bait first, fallback to top bait
            bait_coord = None

            # V4: Smart Bait OCR-based selection
            if self.get_smart_bait_enabled():
                self.set_status("Smart Bait (OCR)")
                print(f"\r[Auto Craft] Running Smart Bait OCR...", end="", flush=True)
                try:
                    smart_bait_coord = self.bait_manager.select_bait()
                    if smart_bait_coord:
                        bait_coord = smart_bait_coord
                        self.logger.info(
                            f"[Smart Bait] Selected bait at ({bait_coord['x']}, {bait_coord['y']})"
                        )
                        print(
                            f"\r[Auto Craft] Smart Bait selected: ({bait_coord['x']}, {bait_coord['y']})",
                            end="",
                            flush=True,
                        )
                except Exception as e:
                    self.logger.error(f"Smart Bait selection error: {e}", exc_info=True)
                    # Continue to fallback

            # Fallback: Use top bait if Smart Bait didn't select anything
            if (
                bait_coord is None
                and self.get_auto_select_top_bait()
                and self.top_bait_point
            ):
                self.set_status("Selecting bait")
                print(
                    f"\r[Auto Craft] Selecting top bait at ({self.top_bait_point['x']}, {self.top_bait_point['y']})...",
                    end="",
                    flush=True,
                )
                bait_coord = self.top_bait_point

            # Click the selected bait slot if we have one
            if bait_coord:
                self.mouse.click(bait_coord["x"], bait_coord["y"], hold_delay=0.1)
                if not self.interruptible_sleep(self.bait_click_delay):
                    return False

            # 5. Cast to auto craft water point for minigame
            if not self.auto_craft_water_point:
                print(
                    "\r[Auto Craft] ✗ No auto craft water point set!",
                    end="",
                    flush=True,
                )
                if not self.interruptible_sleep(1):
                    return False
                return False

            self.set_status("Casting rod")
            print(
                f"\r[Auto Craft] Casting to water point ({self.auto_craft_water_point['x']}, {self.auto_craft_water_point['y']})...",
                end="",
                flush=True,
            )
            self.mouse.move_to(
                self.auto_craft_water_point["x"], self.auto_craft_water_point["y"]
            )
            self.mouse.mouse_event(0x0001, 0, 1, 0, 0)  # MOUSEEVENTF_MOVE 1px down
            if not self.interruptible_sleep(self.mouse_move_settle):
                return False

            self.mouse.left_down()
            if not self.interruptible_sleep(self.cast_hold_duration):
                self.mouse.left_up()
                return False
            self.mouse.left_up()

            # Delay antes do zoom in para minigame (auto craft) - OPTIMIZED
            if not self.interruptible_sleep(0.3):  # Reduced from 0.6
                return False

            # Flag to track if we already handled camera (avoid double zoom-out)
            _camera_already_reset = False

            try:
                # 6. Zoom in 9 ticks after cast (non-interruptible to prevent camera desync)
                print(f"\r[Auto Craft] Zooming in 9 ticks...", end="", flush=True)
                # Move mouse to safe position first (screen center)
                self.mouse.move_to(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                time.sleep(0.03)  # Non-interruptible
                for i in range(9):
                    self.mouse.mouse_event(
                        0x0800, 0, 0, 120, 0
                    )  # MOUSEEVENTF_WHEEL (scroll up)
                    time.sleep(self.zoom_tick_delay)  # Non-interruptible
                time.sleep(self.zoom_settle_delay)  # Non-interruptible

                # 7. Wait for minigame to appear (call auto_craft_esperar)
                self.set_status("Scanning for fish (Auto Craft)")
                print(f"\r[Auto Craft] Waiting for minigame...", end="", flush=True)
                wait_success = self.auto_craft_esperar()
                if not wait_success:
                    # Minigame didn't appear em tempo, recasting com camera initialize
                    print(
                        f"\r[Auto Craft] Minigame timeout, recasting with camera initialize...",
                        end="",
                        flush=True,
                    )
                    self.set_status("Restaurando câmera (auto craft)")
                    # Mark that we're handling camera now (skip finally zoom-out)
                    _camera_already_reset = True
                    # Inicializa a câmera igual ao first_run
                    # Scroll in 30 ticks (first person guarantee)
                    for _ in range(30):
                        self.mouse.mouse_event(0x0800, 0, 0, 120, 0)
                        if not self.interruptible_sleep(0.01):
                            return False
                    if not self.interruptible_sleep(0.1):
                        return False
                    # Scroll out 13 ticks (standardize view)
                    for _ in range(13):
                        self.mouse.mouse_event(0x0800, 0, 0, -120, 0)
                        if not self.interruptible_sleep(0.01):
                            return False
                    if not self.interruptible_sleep(self.rod_select_delay):
                        return False
                    return False  # Signal to recast

                # 8. Play the minigame (call auto_craft_pesca)
                self.set_status("Fishing (Auto Craft)")
                print(f"\r[Auto Craft] Playing minigame...", end="", flush=True)
                while self.running and self.auto_craft_pesca():
                    pass  # Keep fishing while auto_craft_pesca() returns True

                # Ensure mouse is released after minigame
                if self.mouse_pressed:
                    self.mouse.mouse_event(0x0004, 0, 0)  # MOUSEEVENTF_LEFTUP
                    self.mouse_pressed = False
            finally:
                # ONLY zoom out if we didn't already reset camera (timeout handler already did it)
                if not _camera_already_reset:
                    # ALWAYS zoom out 9 ticks after minigame, even if it fails
                    print(
                        f"\r[Auto Craft] Zooming out 9 ticks after minigame...",
                        end="",
                        flush=True,
                    )
                    # Move mouse to safe position first (screen center)
                    self.mouse.move_to(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                    time.sleep(0.03)  # Non-interruptible
                    for i in range(9):
                        self.mouse.mouse_event(0x0800, 0, 0, -120, 0)
                        time.sleep(self.zoom_tick_delay)  # Non-interruptible
                    time.sleep(self.zoom_settle_delay)  # Non-interruptible

            # ============ PART 3: FRUIT CHECK & STORAGE ============
            # 10. Shift Lock Alignment (before pressing fruit hotkey)
            print(
                f"\r[Auto Craft] Activating Shift Lock for alignment...",
                end="",
                flush=True,
            )
            self.keyboard.press(Key.shift)
            self.keyboard.release(Key.shift)
            if not self.interruptible_sleep(0.15):  # Optimized from 0.2
                return False

            print(f"\r[Auto Craft] Deactivating Shift Lock...", end="", flush=True)
            self.keyboard.press(Key.shift)
            self.keyboard.release(Key.shift)
            if not self.interruptible_sleep(0.15):  # Optimized from 0.2
                return False

            # 11. Press fruit hotkey (3) to pick up fruit
            print(
                f"\r[Auto Craft] Pressing fruit hotkey ({self.fruit_hotkey})...",
                end="",
                flush=True,
            )
            self.keyboard.press(self.fruit_hotkey)
            self.keyboard.release(self.fruit_hotkey)
            if not self.interruptible_sleep(0.3):  # Optimized from 0.5
                return False

            # 12. Check fruit color (ALWAYS - every cycle)
            if self.fruit_point and self.fruit_color:
                self.set_status("Checking fruit color")
                print(
                    f"\r[Auto Craft] Checking fruit color at ({self.fruit_point['x']}, {self.fruit_point['y']})...",
                    end="",
                    flush=True,
                )

                try:
                    with mss.mss() as sct:
                        # Capture a 1x1 pixel area at fruit_point
                        monitor = {
                            "top": self.fruit_point["y"],
                            "left": self.fruit_point["x"],
                            "width": 1,
                            "height": 1,
                        }
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
                            diff_r <= tolerance
                            and diff_g <= tolerance
                            and diff_b <= tolerance
                        )
                        print(
                            f"[Auto Craft] Fruit color check: Detected={current_color} Expected={self.fruit_color} | ΔR={diff_r} ΔG={diff_g} ΔB={diff_b} | Tolerance={tolerance}",
                            flush=True,
                        )

                        if color_match:
                            fruit_detected = True
                            self.fruits_caught += 1
                            self.set_fish_at_last_fruit(self.fish_caught)
                            if self.stats_manager:
                                self.stats_manager.log_fruit()
                            print(
                                f"\r🍎 FRUIT DETECTED! Total fruits: {self.fruits_caught}",
                                end="",
                                flush=True,
                            )

                            # Decide if we should zoom + screenshot
                            do_zoom_and_ss = True
                            is_legendary = False  # Initialize flag
                            if self.get_webhook_only_legendary():
                                # Only zoom/SS when pity says Legendary/Mythical (0/40)
                                is_legendary = self.check_legendary_pity()
                                if not is_legendary:
                                    do_zoom_and_ss = False
                                    print(
                                        f"\r[Auto Craft] Pity filter ON and not 0/40 → skipping zoom/screenshot",
                                        end="",
                                        flush=True,
                                    )

                            if do_zoom_and_ss:
                                try:
                                    # Zoom in 6 ticks for fruit screenshot (non-interruptible to prevent camera desync)
                                    print(
                                        f"\r[Auto Craft] Zooming in 6 ticks for screenshot...",
                                        end="",
                                        flush=True,
                                    )
                                    for _ in range(6):
                                        self.mouse.mouse_event(
                                            0x0800, 0, 0, 120, 0
                                        )  # MOUSEEVENTF_WHEEL, scroll up
                                        time.sleep(
                                            self.zoom_tick_delay
                                        )  # Non-interruptible
                                    time.sleep(
                                        self.zoom_settle_delay
                                    )  # Non-interruptible

                                    # Take screenshot at zoomed position
                                    print(
                                        f"\r[Auto Craft] 📸 Capturing screenshot...",
                                        end="",
                                        flush=True,
                                    )
                                    screenshot_path = self.screen.capture_center(
                                        auto_craft_mode=True
                                    )

                                    # Send webhook notification with screenshot (pity filter is checked INSIDE send_fruit_webhook)
                                    if screenshot_path:
                                        # Pass the already-checked legendary status to avoid double-checking
                                        self.send_fruit_webhook(
                                            screenshot_path, is_legendary=is_legendary
                                        )
                                finally:
                                    # ALWAYS zoom out to restore view, even if screenshot/webhook fails
                                    print(
                                        f"\r[Auto Craft] Zooming out 6 ticks...",
                                        end="",
                                        flush=True,
                                    )
                                    for _ in range(6):
                                        self.mouse.mouse_event(
                                            0x0800, 0, 0, -120, 0
                                        )  # MOUSEEVENTF_WHEEL, scroll down
                                        time.sleep(
                                            self.zoom_tick_delay
                                        )  # Non-interruptible
                                    time.sleep(
                                        self.zoom_settle_delay
                                    )  # Non-interruptible

                                # Wait after screenshot
                                if not self.interruptible_sleep(0.3):
                                    return False
                        else:
                            print(
                                f"\r[Auto Craft] No fruit detected. Detected: {current_color}, Expected: {self.fruit_color} | ΔR={diff_r} ΔG={diff_g} ΔB={diff_b} | Tolerance={tolerance}",
                                end="",
                                flush=True,
                            )

                except Exception as e:
                    print(
                        f"\r[Auto Craft] Warning: Failed to check fruit color: {e}",
                        end="",
                        flush=True,
                    )

            # 13. Click Store button and handle fruit storage (Drop vs Inventory)
            if self.fruit_point:
                # Only store after fruit sequence if fruit was detected, otherwise always store
                if fruit_detected or not self.fruit_color:
                    self.set_status("Storing fruit")
                    print(
                        f"\r[Auto Craft] Clicking Store button at ({self.fruit_point['x']}, {self.fruit_point['y']})...",
                        end="",
                        flush=True,
                    )
                    self.mouse.move_to(self.fruit_point["x"], self.fruit_point["y"])
                    self.mouse.mouse_event(
                        0x0001, 0, 1, 0, 0
                    )  # MOUSEEVENTF_MOVE 1px down
                    if not self.interruptible_sleep(0.01):
                        return False
                    self.mouse.mouse_event(0x0002, 0, 0)  # LEFT DOWN
                    self.mouse.mouse_event(0x0004, 0, 0)  # LEFT UP
                    if not self.interruptible_sleep(self.store_click_delay):
                        return False

                    # Handle fruit storage based on mode (Drop vs Inventory)
                    if self.get_store_in_inventory() and self.inventory_fruit_point:
                        # NEW: Store in inventory mode
                        print(
                            f"\r[Auto Craft] Storing in inventory...",
                            end="",
                            flush=True,
                        )

                        # Open inventory with `
                        self.keyboard.press("`")
                        self.keyboard.release("`")
                        if not self.interruptible_sleep(0.3):  # Faster for auto craft
                            return False

                        # Click and drag fruit to screen center
                        inv_x = self.inventory_fruit_point["x"]
                        inv_y = self.inventory_fruit_point["y"]

                        if self.inventory_center_point:
                            center_x = self.inventory_center_point["x"]
                            center_y = self.inventory_center_point["y"]
                        else:
                            center_x = SCREEN_WIDTH // 2
                            center_y = SCREEN_HEIGHT // 2

                        print(
                            f"\r[Auto Craft] Dragging from ({inv_x},{inv_y}) to ({center_x},{center_y})...",
                            end="",
                            flush=True,
                        )
                        self.mouse.drag(inv_x, inv_y, center_x, center_y)

                        if not self.interruptible_sleep(0.15):  # Faster
                            return False

                        # Close inventory
                        self.keyboard.press("`")
                        self.keyboard.release("`")
                        if not self.interruptible_sleep(0.3):  # Faster
                            return False
                    else:
                        # ORIGINAL: Drop with backspace
                        if (
                            self.get_store_in_inventory()
                            and not self.inventory_fruit_point
                        ):
                            print(
                                f"\r[Auto Craft] WARNING - Inventory store enabled but no point set! Dropping instead.",
                                end="",
                                flush=True,
                            )

                        print(
                            f"\r[Auto Craft] Pressing backspace to close storage...",
                            end="",
                            flush=True,
                        )
                        self.keyboard.press(Key.backspace)
                        self.keyboard.release(Key.backspace)
                        if not self.interruptible_sleep(self.backspace_delay):
                            return False

            # Mark first run as done when we reach store
            if self.first_catch:
                self.first_catch = False
                print(
                    f"\r[Auto Craft] First run completed, fruit check/store will run every cycle now...",
                    end="",
                    flush=True,
                )

            # 13. Count fish ONLY if no fruit was caught
            if self.running and not fruit_detected:
                self.fish_caught += 1
                if self.stats_manager:
                    self.stats_manager.log_fish()
                print(
                    f"\r🐟 Fish caught! Total fish: {self.fish_caught}",
                    end="",
                    flush=True,
                )
                # End cycle timer (successful fish catch in auto craft)
                self.end_cycle_timer()

            print(
                f"\r[Auto Craft] ✅ Cycle complete! Restarting...", end="", flush=True
            )
            return True

        except Exception as e:
            print(f"\r[Auto Craft] Error in pre-cast: {e}", end="", flush=True)
            return False

    def auto_craft_esperar(self):
        """Stage 2 (Auto Craft Mode): Wait for fish - uses auto craft area (LITERAL COPY from lines 4815-4882)"""
        if not self.running:
            return False

        # Check if auto craft area is set
        if not self.auto_craft_area_coords:
            print("\r[Auto Craft] ✗ No auto craft area set!", end="", flush=True)
            if not self.interruptible_sleep(1):
                return False
            return False

        print(
            f"\r[Auto Craft] Scanning for colors (timeout: {self.recast_timeout}s)...",
            end="",
            flush=True,
        )

        # Target colors to detect
        target_colors = [
            (85, 170, 255),  # Blue #55aaff - Main bar
            (255, 255, 255),  # White #ffffff - Center line
            (25, 25, 25),  # Black #191919 - Borders/shadows
            (170, 255, 0),  # Green-yellow #aaff00 - UI element
            (32, 34, 36),  # Dark gray #202224 - Frame/background
        ]

        start_time = time.time()

        while self.running:
            # Check timeout
            elapsed_time = time.time() - start_time
            if elapsed_time >= self.recast_timeout:
                print(
                    f"\r[Auto Craft] ✗ Timeout ({self.recast_timeout}s) - Recasting...",
                    end="",
                    flush=True,
                )
                return False

            # Capture screenshot of auto craft area
            screenshot = (
                self.screen.capture_area(
                    self.auto_craft_area_coords["x"],
                    self.auto_craft_area_coords["y"],
                    self.auto_craft_area_coords["width"],
                    self.auto_craft_area_coords["height"],
                    use_cache=False,
                )
                if self.auto_craft_area_coords
                else None
            )

            if screenshot is not None:
                # Check for anti-macro
                if self.anti_macro.is_black_screen(screenshot):
                    print(
                        f"\r[Auto Craft] ⚠️  Anti-macro detected! Handling...",
                        end="",
                        flush=True,
                    )
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
                    print(
                        f"\r[Auto Craft] ✓ All colors detected! Starting fishing... (took {elapsed_time:.1f}s)",
                        end="",
                        flush=True,
                    )
                    return True
                else:
                    print(
                        f"\r[Auto Craft] Waiting for colors... ({elapsed_time:.1f}s/{self.recast_timeout}s)",
                        end="",
                        flush=True,
                    )

            if not self.interruptible_sleep(self.fruit_detection_delay):
                return False

        return False

    def auto_craft_pesca(self):
        """Stage 3 (Auto Craft Mode): Fish catch - uses auto craft area (LITERAL COPY from lines 4883-5020)"""
        if not self.running:
            if self.mouse_pressed:
                self.mouse.left_up()
                self.mouse_pressed = False
            return False

        # Target color to detect
        target_color = (85, 170, 255)  # RGB: #55aaff

        # Take screenshot of the auto craft area
        screenshot = (
            self.screen.capture_area(
                self.auto_craft_area_coords["x"],
                self.auto_craft_area_coords["y"],
                self.auto_craft_area_coords["width"],
                self.auto_craft_area_coords["height"],
                use_cache=False,
            )
            if self.auto_craft_area_coords
            else None
        )

        if screenshot is not None:
            # Check if target color exists
            color_found, middle_x = self.check_color_in_image(screenshot, target_color)

            if color_found:
                # Use same fishing logic as normal mode but with auto craft area
                absolute_x = self.auto_craft_area_coords["x"] + middle_x
                vertical_line = self.crop_vertical_line(screenshot, middle_x)

                if vertical_line is not None:
                    black_color = (25, 25, 25)
                    top_y, bottom_y = self.find_topmost_bottommost_color(
                        vertical_line, black_color
                    )

                    if top_y is not None and bottom_y is not None:
                        cropped_section = self.crop_vertical_section(
                            vertical_line, top_y, bottom_y
                        )

                        if cropped_section is not None:
                            white_color = (255, 255, 255)
                            white_top, white_bottom = (
                                self.find_topmost_bottommost_color(
                                    cropped_section, white_color, tolerance=5
                                )
                            )

                            if white_top is not None and white_bottom is not None:
                                white_height = white_bottom - white_top + 1
                                white_middle = (white_top + white_bottom) // 2
                                absolute_white_middle_y = top_y + white_middle

                                max_gap = max(5, int(white_height * 0.2))
                                black_group_middle = self.find_biggest_black_group(
                                    cropped_section, (25, 25, 25), max_gap
                                )

                                if black_group_middle is not None:
                                    absolute_black_group_y = top_y + black_group_middle
                                    self.detection_lost_counter = 0

                                    error = black_group_middle - white_middle
                                    current_time = time.time()
                                    dt = current_time - self.pid_last_time

                                    if dt > 0:
                                        p_term = self.pid_kp * error
                                        d_term = (
                                            self.pid_kd
                                            * (error - self.pid_last_error)
                                            / dt
                                        )
                                        pd_output = p_term + d_term
                                        pd_output = max(
                                            -self.pid_clamp,
                                            min(self.pid_clamp, pd_output),
                                        )

                                        duty_cycle = 0.5 + (
                                            pd_output / (self.pid_clamp * 2)
                                        )
                                        duty_cycle = max(0.0, min(1.0, duty_cycle))
                                        should_hold = duty_cycle > 0.5

                                        # Execute mouse action
                                        if should_hold:
                                            if not self.mouse_pressed:
                                                self.mouse.left_down()
                                                self.mouse_pressed = True
                                                if (
                                                    hasattr(self, "show_debug_arrows")
                                                    and self.show_debug_arrows
                                                    and hasattr(self, "debug_root")
                                                    and hasattr(
                                                        self, "debug_status_label"
                                                    )
                                                ):
                                                    self.debug_root.after(
                                                        0,
                                                        lambda: self.debug_status_label.configure(
                                                            text=f"Action: HOLD | Err: {error:.1f}",
                                                            text_color="#00dd00",
                                                        ),
                                                    )
                                        else:
                                            if self.mouse_pressed:
                                                self.mouse.left_up()
                                                self.mouse_pressed = False
                                                if (
                                                    hasattr(self, "show_debug_arrows")
                                                    and self.show_debug_arrows
                                                    and hasattr(self, "debug_root")
                                                    and hasattr(
                                                        self, "debug_status_label"
                                                    )
                                                ):
                                                    self.debug_root.after(
                                                        0,
                                                        lambda: self.debug_status_label.configure(
                                                            text=f"Action: RELEASE | Err: {error:.1f}",
                                                            text_color="#ff4444",
                                                        ),
                                                    )

                                        # Update last state variables
                                        self.last_error = error
                                        self.last_bar_y = black_group_middle
                                        self.last_time = current_time
                                        self.pid_last_error = error
                                        self.pid_last_time = current_time
                                        self.detection_lost_counter = (
                                            0  # Reset detection lost counter
                                        )

                                        print(
                                            f"\r[AC] W:{white_middle} B:{black_group_middle} E:{error:+.0f} PD:{pd_output:+.2f} {'HOLD' if should_hold else 'FREE'}",
                                            end="",
                                            flush=True,
                                        )
                                else:
                                    # Black group not found - hold to go to top
                                    if not self.mouse_pressed:
                                        self.mouse.left_down()
                                        self.mouse_pressed = True
                                    print(
                                        f"\r[Auto Craft] White found but no black group - HOLDING",
                                        end="",
                                        flush=True,
                                    )
                            else:
                                # White not found - hold to go to top
                                if not self.mouse_pressed:
                                    self.mouse.left_down()
                                    self.mouse_pressed = True
                                print(
                                    f"\r[Auto Craft] No white line - HOLDING to top",
                                    end="",
                                    flush=True,
                                )
            else:
                print(
                    f"\r[Auto Craft] Blue not found - Exiting fishing",
                    end="",
                    flush=True,
                )
                if self.mouse_pressed:
                    self.mouse.left_up()
                    self.mouse_pressed = False
                self.pid_last_error = 0.0
                return False

        if not self.interruptible_sleep(self.fruit_detection_delay):
            return False
        return True

    # ========== HELPER METHODS (LITERAL COPY) ==========
    def handle_anti_macro_detection(self):
        """Handle anti-macro black screen by spamming everything_else hotkey until cleared"""
        try:
            print(
                "\r⚠️  ANTI-MACRO DETECTED! Spamming hotkey to clear...",
                end="",
                flush=True,
            )

            while self.running:
                # Check current screen
                screenshot = self.screen.capture_area()

                if screenshot is None:
                    if not self.interruptible_sleep(0.25):
                        return False
                    continue

                # Check if still black
                if not self.anti_macro.is_black_screen(screenshot):
                    print("\r✅ Anti-macro cleared! Restarting...", end="", flush=True)
                    if not self.interruptible_sleep(0.5):
                        return False
                    return True  # Cleared - restart main loop

                # Spam everything_else hotkey
                self.keyboard.press(self.everything_else_hotkey)
                self.keyboard.release(self.everything_else_hotkey)
                print(
                    f"\r⚠️  Anti-macro active... Pressing {self.everything_else_hotkey}...",
                    end="",
                    flush=True,
                )

                if not self.interruptible_sleep(0.25):
                    return False

            return False  # Stopped by user
        except Exception as e:
            print(f"\rError handling anti-macro: {e}", end="", flush=True)
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
                (np.abs(r - target_r) <= tolerance)
                & (np.abs(g - target_g) <= tolerance)
                & (np.abs(b - target_b) <= tolerance)
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
            print(f"\rError checking color: {e}  ", end="", flush=True)
            return False, 0

    def crop_vertical_line(self, img, x_position):
        """Crop a 1-pixel wide vertical line from the image at x_position"""
        try:
            # Extract the entire column at x_position
            # img shape is (height, width, channels)
            vertical_line = img[:, x_position : x_position + 1, :]

            # vertical_line shape will be (height, 1, 4) for BGRA
            return vertical_line

        except Exception as e:
            print(f"\rError cropping vertical line: {e}  ", end="", flush=True)
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
                (np.abs(r - target_r) <= tolerance)
                & (np.abs(g - target_g) <= tolerance)
                & (np.abs(b - target_b) <= tolerance)
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
            print(f"\rError finding color bounds: {e}  ", end="", flush=True)
            return None, None

    def crop_vertical_section(self, vertical_line, top_y, bottom_y):
        """Crop the vertical line to only include pixels between top_y and bottom_y"""
        try:
            # vertical_line shape is (height, 1, 4)
            # Extract section from top_y to bottom_y (inclusive)
            cropped_section = vertical_line[top_y : bottom_y + 1, :, :]

            # cropped_section shape will be (bottom_y - top_y + 1, 1, 4)
            return cropped_section

        except Exception as e:
            print(f"\rError cropping vertical section: {e}  ", end="", flush=True)
            return None

    def find_biggest_black_group(self, cropped_section, black_color, max_gap):
        """Find the biggest continuous group of black pixels with gap tolerance"""
        try:
            # cropped_section shape is (height, 1, 4) - BGRA format
            # Extract RGB channels
            b = cropped_section[:, 0, 0]
            g = cropped_section[:, 0, 1]
            r = cropped_section[:, 0, 2]

            # Target RGB values
            target_r, target_g, target_b = black_color
            tolerance = 5

            # Find matching pixels
            matches = (
                (np.abs(r - target_r) <= tolerance)
                & (np.abs(g - target_g) <= tolerance)
                & (np.abs(b - target_b) <= tolerance)
            )

            # Get Y coordinates of matches
            y_coords = np.where(matches)[0]

            if len(y_coords) == 0:
                return None

            # Find groups of black pixels with gap tolerance
            groups = []
            current_group = [y_coords[0]]

            for i in range(1, len(y_coords)):
                gap = y_coords[i] - y_coords[i - 1]
                if gap <= max_gap:
                    # Extend current group
                    current_group.append(y_coords[i])
                else:
                    # Start new group
                    groups.append(current_group)
                    current_group = [y_coords[i]]

            # Add last group
            groups.append(current_group)

            # Find biggest group
            biggest_group = max(groups, key=len)

            # Return middle Y of biggest group
            middle_y = int(np.mean(biggest_group))
            return middle_y

        except Exception as e:
            print(f"\rError finding biggest black group: {e}  ", end="", flush=True)
            return None
