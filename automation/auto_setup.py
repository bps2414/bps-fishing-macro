# Copyright (C) 2026 BPS
# This file is part of BPS Fishing Macro.
#
# Auto Setup - Automated game entry and VIP server joining
# Phase 2: Full automation logic
#
# Workflow:
#   1. Open browser → VIP server link
#   2. Click Play button (website)
#   3. Wait for Roblox menu (color detection)
#   4. Press Ctrl (dismiss dialog)
#   5. Click Private Server button
#   6. Click VIP Code input field
#   7. Paste VIP code
#   8. Click Enter Regular
#   9. Wait for game loaded (color detection)
#   10. Position character (movement sequence)
#   11. Done → macro starts fishing

"""
AutoSetup - Automated Roblox game entry and VIP server joining.

Uses the Anti-Roblox click method (mouse_controller.click) for all clicks.
Uses color_detector.check_color_match for visual state detection.
All coordinates and colors are configured by user in Auto Setup tab (Phase 1).
"""

import time
import logging
import webbrowser
import mss
from pynput.keyboard import Key

logger = logging.getLogger("FishingMacro")


class AutoSetup:
    """
    Automated game entry and VIP server joining.

    This class orchestrates the full auto-setup workflow:
    Browser → Play → Menu detection → VIP server → Game detection → Movement

    All clicks use the Anti-Roblox method via mouse_controller.
    All detection uses pixel-level color checking via color_detector.
    """

    # Status constants
    STATUS_IDLE = "idle"
    STATUS_OPENING_BROWSER = "opening_browser"
    STATUS_CLICKING_PLAY = "clicking_play"
    STATUS_WAITING_MENU = "waiting_menu"
    STATUS_JOINING_SERVER = "joining_server"
    STATUS_WAITING_GAME = "waiting_game"
    STATUS_POSITIONING = "positioning"
    STATUS_DONE = "done"
    STATUS_FAILED = "failed"

    def __init__(
        self,
        mouse_controller,
        keyboard_controller,
        color_detector,
        window_manager,
        settings,
    ):
        """
        Initialize AutoSetup with dependencies.

        Args:
            mouse_controller: MouseController instance (Anti-Roblox clicks)
            keyboard_controller: KeyboardController instance (key presses)
            color_detector: ColorDetector instance (color matching)
            window_manager: WindowManager instance (Roblox window focus)
            settings: Dict with all auto setup settings from SettingsManager
        """
        self.mouse = mouse_controller
        self.keyboard = keyboard_controller
        self.color_detector = color_detector
        self.window = window_manager
        self.settings = settings

        # State
        self.status = self.STATUS_IDLE
        self.should_stop = False  # Flag for cancellation
        self._status_callback = None  # GUI status update callback

        # Extract settings
        self.vip_code = settings.get("vip_code", "")
        self.max_retries = settings.get("max_retries", 5)
        self.game_open_timeout = settings.get("game_open_timeout", 30)
        self.game_load_timeout = settings.get("game_load_timeout", 60)

        # Coordinates
        self.play_button = settings.get("play_button")
        self.private_server_1 = settings.get("private_server_1")
        self.vip_code_input = settings.get("vip_code_input")
        self.enter_regular = settings.get("enter_regular")

        # Color detection
        self.menu_color_check = settings.get("menu_color_check", {})
        self.game_loaded_color_check = settings.get("game_loaded_color_check", {})

    def set_status_callback(self, callback):
        """Set callback for status updates (called on GUI thread)

        Args:
            callback: Function(status_text: str) to call on status change
        """
        self._status_callback = callback

    def _update_status(self, status, message=None):
        """Update internal status and notify callback

        Args:
            status: Status constant
            message: Optional human-readable message
        """
        self.status = status
        msg = message or status
        logger.info(f"[AutoSetup] {msg}")
        if self._status_callback:
            try:
                self._status_callback(msg)
            except Exception:
                pass  # GUI might be destroyed

    def stop(self):
        """Request graceful stop of auto setup"""
        self.should_stop = True
        logger.info("[AutoSetup] Stop requested")

    def validate_settings(self):
        """Validate that all required settings are configured

        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
        errors = []

        if not self.vip_code:
            errors.append("VIP server code not set")

        coords = {
            "Play Button": self.play_button,
            "Private Server 1": self.private_server_1,
            "VIP Code Input": self.vip_code_input,
            "Enter Regular": self.enter_regular,
        }
        for name, coord in coords.items():
            if not coord or "x" not in coord or "y" not in coord:
                errors.append(f"{name} coordinate not set")

        # Color checks
        menu = self.menu_color_check
        if not menu.get("coordinate") or not menu.get("color_rgb"):
            errors.append("Menu Color not configured")

        game = self.game_loaded_color_check
        if not game.get("coordinate") or not game.get("color_rgb"):
            errors.append("Game Loaded Color not configured")

        if errors:
            return False, "; ".join(errors)
        return True, ""

    def run(self):
        """
        Execute the full auto-setup workflow.

        Returns:
            bool: True if setup completed successfully, False on failure
        """
        self.should_stop = False

        # Validate settings
        valid, error = self.validate_settings()
        if not valid:
            self._update_status(self.STATUS_FAILED, f"❌ Config error: {error}")
            return False

        try:
            for attempt in range(1, self.max_retries + 1):
                if self.should_stop:
                    self._update_status(self.STATUS_IDLE, "⏹ Auto Setup cancelled")
                    return False

                logger.info(f"[AutoSetup] Attempt {attempt}/{self.max_retries}")
                self._update_status(
                    self.STATUS_OPENING_BROWSER,
                    f"🌐 Attempt {attempt}/{self.max_retries} - Opening browser...",
                )

                success = self._run_sequence()
                if success:
                    self._update_status(self.STATUS_DONE, "✅ Auto Setup complete!")
                    return True

                if attempt < self.max_retries:
                    wait_msg = f"⚠️ Attempt {attempt} failed, retrying in 5s..."
                    self._update_status(self.STATUS_FAILED, wait_msg)
                    self._sleep(5)

            self._update_status(
                self.STATUS_FAILED, f"❌ Failed after {self.max_retries} attempts"
            )
            return False

        except Exception as e:
            logger.error(f"[AutoSetup] Unexpected error: {e}", exc_info=True)
            self._update_status(self.STATUS_FAILED, f"❌ Error: {str(e)[:50]}")
            return False

    def _run_sequence(self):
        """Execute one full attempt of the auto-setup sequence

        Returns:
            bool: True if successful, False on failure
        """
        # Step 1: Open browser with VIP link
        if not self._step_open_browser():
            return False

        # Wait 3-5 seconds for page to load before clicking Play
        logger.info("[AutoSetup] ⏳ Waiting 3s for page to load...")
        self._sleep(3)

        # Step 2: Click Play button on website
        if not self._step_click_play():
            return False

        # Step 3: Wait for Roblox menu to appear
        if not self._step_wait_for_menu():
            return False

        # Step 4: Press Ctrl to dismiss any dialog
        if not self._step_press_ctrl():
            return False

        # Step 5: Click Private Server button
        if not self._step_click_private_server():
            return False

        # Step 6: Click VIP Code input field
        if not self._step_click_vip_input():
            return False

        # Step 7: Paste VIP code
        if not self._step_paste_vip_code():
            return False

        # Step 8: Press Enter key
        if not self._step_press_enter():
            return False

        # Step 9: Click Regular button
        if not self._step_click_regular():
            return False

        # Step 10: Wait for game to load
        if not self._step_wait_for_game():
            return False

        # Step 11: Position character
        if not self._step_position_character():
            return False

        return True

    # ── Individual Steps ──────────────────────────────────────────

    def _step_open_browser(self):
        """Step 1: Open browser with Roblox VIP server link"""
        if self.should_stop:
            return False

        self._update_status(self.STATUS_OPENING_BROWSER, "🌐 Opening browser...")

        try:
            # Open Grand Piece Online game page
            game_url = "https://www.roblox.com/games/1730877806/Grand-Piece-Online"
            webbrowser.open(game_url)
            logger.info(f"[AutoSetup] Browser opened with game URL")
            self._sleep(3)  # Wait for browser to open
            return True
        except Exception as e:
            logger.error(f"[AutoSetup] Failed to open browser: {e}")
            return False

    def _step_click_play(self):
        """Step 2: Click Play button on the website"""
        if self.should_stop:
            return False

        self._update_status(self.STATUS_CLICKING_PLAY, "🎮 Clicking Play button...")

        try:
            x = self.play_button["x"]
            y = self.play_button["y"]

            # Wait a moment for page to load, then click
            self._sleep(2)
            self.mouse.click(x, y, hold_delay=0.3)  # Longer hold for browser click
            logger.info(f"[AutoSetup] Clicked Play at ({x}, {y})")
            self._sleep(3)  # Wait longer for Roblox launcher to respond
            return True
        except Exception as e:
            logger.error(f"[AutoSetup] Failed to click Play: {e}")
            return False

    def _step_wait_for_menu(self):
        """Step 3: Wait for Roblox menu to appear (color detection)"""
        if self.should_stop:
            return False

        self._update_status(self.STATUS_WAITING_MENU, "⏳ Waiting for Roblox menu...")

        # Try to focus Roblox window periodically while waiting
        try:
            self.window.focus_roblox_window()
            logger.info("[AutoSetup] Focused Roblox window")
        except Exception:
            pass

        coord = self.menu_color_check["coordinate"]
        target_color = self.menu_color_check["color_rgb"]
        tolerance = self.menu_color_check.get("tolerance", 20)

        # Convert list to tuple if needed (JSON deserializes as list)
        if isinstance(target_color, list):
            target_color = tuple(target_color)

        detected = self._wait_for_color_with_focus(
            coord, target_color, tolerance, self.game_open_timeout
        )

        if detected:
            logger.info("[AutoSetup] Menu detected!")
            self._sleep(1)  # Extra settle time
            return True
        else:
            logger.warning("[AutoSetup] Menu not detected within timeout")
            return False

    def _step_press_ctrl(self):
        """Step 4: Press Ctrl to dismiss any dialog/overlay"""
        if self.should_stop:
            return False

        self._update_status(self.STATUS_JOINING_SERVER, "⌨️ Pressing Ctrl...")

        try:
            self.keyboard.tap(Key.ctrl_l, delay=0.1)
            logger.info("[AutoSetup] Pressed Ctrl")
            self._sleep(2.0)  # Wait longer for dialog to dismiss
            return True
        except Exception as e:
            logger.error(f"[AutoSetup] Failed to press Ctrl: {e}")
            return False

    def _step_click_private_server(self):
        """Step 5: Click Private Server button"""
        if self.should_stop:
            return False

        self._update_status(self.STATUS_JOINING_SERVER, "🔐 Clicking Private Server...")

        try:
            # Focus Roblox window first
            self.window.focus_roblox_window()
            self._sleep(0.5)

            x = self.private_server_1["x"]
            y = self.private_server_1["y"]
            self.mouse.click(x, y, hold_delay=0.1)
            logger.info(f"[AutoSetup] Clicked Private Server at ({x}, {y})")
            self._sleep(2.0)  # Wait for menu animation
            return True
        except Exception as e:
            logger.error(f"[AutoSetup] Failed to click Private Server: {e}")
            return False

    def _step_click_vip_input(self):
        """Step 6: Click VIP Code input field"""
        if self.should_stop:
            return False

        self._update_status(self.STATUS_JOINING_SERVER, "📝 Clicking VIP input...")

        try:
            x = self.vip_code_input["x"]
            y = self.vip_code_input["y"]
            self.mouse.click(x, y, hold_delay=0.1)
            logger.info(f"[AutoSetup] Clicked VIP Input at ({x}, {y})")
            self._sleep(1.5)  # Wait for input field to focus
            return True
        except Exception as e:
            logger.error(f"[AutoSetup] Failed to click VIP Input: {e}")
            return False

    def _step_paste_vip_code(self):
        """Step 7: Paste VIP server code"""
        if self.should_stop:
            return False

        self._update_status(self.STATUS_JOINING_SERVER, "📋 Pasting VIP code...")

        try:
            # Use clipboard to paste (Ctrl+V)
            import pyperclip

            pyperclip.copy(self.vip_code)
            self._sleep(0.2)

            # Ctrl+V paste using keyboard
            self.keyboard.press(Key.ctrl_l)
            self._sleep(0.05)
            self.keyboard.tap("v", delay=0.05)
            self.keyboard.release(Key.ctrl_l)

            logger.info("[AutoSetup] VIP code pasted")
            self._sleep(2.5)  # Wait for code to register
            return True
        except Exception as e:
            logger.error(f"[AutoSetup] Failed to paste VIP code: {e}")
            return False

    def _step_press_enter(self):
        """Step 8: Press Enter key to submit VIP code"""
        if self.should_stop:
            return False

        self._update_status(self.STATUS_JOINING_SERVER, "⏎ Pressing Enter key...")

        try:
            self.keyboard.tap(Key.enter, delay=0.1)
            logger.info("[AutoSetup] Pressed Enter key")
            self._sleep(1.5)  # Wait for Enter button to appear on screen
            return True
        except Exception as e:
            logger.error(f"[AutoSetup] Failed to press Enter: {e}")
            return False

    def _step_click_regular(self):
        """Step 9: Click Regular button after Enter key pressed"""
        if self.should_stop:
            return False

        self._update_status(
            self.STATUS_JOINING_SERVER, "✅ Waiting for Regular button..."
        )
        self._sleep(5.0)  # Wait for Regular button to appear

        self._update_status(self.STATUS_JOINING_SERVER, "✅ Clicking Regular...")

        try:
            x = self.enter_regular["x"]
            y = self.enter_regular["y"]
            self.mouse.click(x, y, hold_delay=0.2)
            logger.info(f"[AutoSetup] Clicked Regular at ({x}, {y})")
            self._sleep(0.5)  # Short delay before second click

            # Second click to ensure it registers
            self.mouse.click(x, y, hold_delay=0.2)
            logger.info(f"[AutoSetup] Clicked Regular again at ({x}, {y})")
            self._sleep(4.0)  # Wait longer for server to process and start teleport
            return True
        except Exception as e:
            logger.error(f"[AutoSetup] Failed to click Enter: {e}")
            return False

    def _step_wait_for_game(self):
        """Step 9: Wait for game to fully load (color detection)"""
        if self.should_stop:
            return False

        self._update_status(self.STATUS_WAITING_GAME, "⏳ Waiting for game to load...")

        coord = self.game_loaded_color_check["coordinate"]
        target_color = self.game_loaded_color_check["color_rgb"]
        tolerance = self.game_loaded_color_check.get("tolerance", 20)

        # Convert list to tuple if needed
        if isinstance(target_color, list):
            target_color = tuple(target_color)

        detected = self._wait_for_color(
            coord, target_color, tolerance, self.game_load_timeout
        )

        if detected:
            logger.info("[AutoSetup] Game loaded!")
            self._sleep(2)  # Extra settle time for game to fully initialize
            return True
        else:
            logger.warning("[AutoSetup] Game not loaded within timeout")
            return False

    def _step_position_character(self):
        """Step 11: Full positioning sequence.

        1. Hold S for 4s  (walk back)
        2. Hold A for 1s  (strafe left)
        3. Drag camera right→left ~45° (horizontal rotation)
        4. Drag camera up→down max  (top-down camera angle)
        """
        if self.should_stop:
            return False

        # Ensure Roblox is focused
        try:
            self.window.focus_roblox_window()
        except Exception:
            pass
        self._sleep(0.5)

        # ── Step 1: Hold S for 4 seconds ─────────────────────────
        self._update_status(self.STATUS_POSITIONING, "🚶 Recuando...")
        logger.info("[AutoSetup] Holding S for 4s")
        try:
            self.keyboard.press("s")
            start = time.time()
            while time.time() - start < 4.0:
                if self.should_stop:
                    break
                time.sleep(0.1)
        finally:
            try:
                self.keyboard.release("s")
            except Exception:
                pass

        if self.should_stop:
            return False
        self._sleep(0.2)

        # ── Step 2: Hold A for 1 second ──────────────────────────
        self._update_status(self.STATUS_POSITIONING, "↩️ Virando...")
        logger.info("[AutoSetup] Holding A for 0.55s")
        try:
            self.keyboard.press("a")
            start = time.time()
            while time.time() - start < 0.55:
                if self.should_stop:
                    break
                time.sleep(0.1)
        finally:
            try:
                self.keyboard.release("a")
            except Exception:
                pass

        if self.should_stop:
            return False
        self._sleep(0.3)

        # ── Steps 3 & 4: Camera rotation via right-button drag ───
        # Usa o mesmo método do fishing_cycle: RIGHTDOWN + mouse_event(0x0001, dx, dy) relativo

        # Step 3: Horizontal — rotate left ~45°
        # fishing_cycle usa -100px por step; 2 steps = ~45°
        self._update_status(self.STATUS_POSITIONING, "📷 Rotacionando câmera...")
        logger.info("[AutoSetup] Camera H rotation: -400px horizontal")
        self.mouse.drag_right(
            delta_x=-400,
            delta_y=0,
            steps=6,
            step_delay=0.05,
            hold_delay=0.2,
        )

        if self.should_stop:
            return False
        self._sleep(1.5)

        # Step 4: Vertical — push camera to top-down view
        # delta_y positivo = arrastar para baixo = câmera sobe (vista de cima)
        self._update_status(self.STATUS_POSITIONING, "📷 Ajustando ângulo da câmera...")
        logger.info("[AutoSetup] Camera V rotation: +800px vertical")
        self.mouse.drag_right(
            delta_x=0,
            delta_y=800,
            steps=15,
            step_delay=0.05,
            hold_delay=0.2,
        )

        if self.should_stop:
            return False
        self._sleep(0.5)

        self._update_status(
            self.STATUS_POSITIONING, "✅ Posicionado! Iniciando macro..."
        )
        logger.info("[AutoSetup] Character positioned (full sequence)")
        return True

    # ── Utility Methods ───────────────────────────────────────────
    def _wait_for_color_with_focus(self, coord, target_color, tolerance, timeout):
        """Wait for a specific color, periodically trying to focus Roblox window.

        Tries to focus Roblox every 5 seconds in case it didn't auto-focus.

        Args:
            coord: dict with "x" and "y" keys
            target_color: tuple (R, G, B)
            tolerance: int, color match tolerance per channel
            timeout: float, max seconds to wait

        Returns:
            bool: True if color detected within timeout
        """
        start_time = time.time()
        poll_interval = 0.5
        last_focus_time = time.time()

        while time.time() - start_time < timeout:
            if self.should_stop:
                return False

            try:
                # Try to focus Roblox window every 5 seconds
                if time.time() - last_focus_time >= 5.0:
                    try:
                        self.window.focus_roblox_window()
                        logger.debug("[AutoSetup] Re-focused Roblox window")
                    except Exception:
                        pass
                    last_focus_time = time.time()

                with mss.mss() as sct:
                    monitor = {
                        "top": coord["y"],
                        "left": coord["x"],
                        "width": 1,
                        "height": 1,
                    }
                    screenshot = sct.grab(monitor)
                    current_color = screenshot.pixel(0, 0)[:3]

                if self.color_detector.check_color_match(
                    current_color, target_color, tolerance
                ):
                    return True

                elapsed = int(time.time() - start_time)
                self._update_status(
                    self.status, f"⏳ Waiting... ({elapsed}s / {timeout}s)"
                )

            except Exception as e:
                logger.warning(f"[AutoSetup] Color check error: {e}")

            self._sleep(poll_interval)

        return False

    def _wait_for_color_with_focus(self, coord, target_color, tolerance, timeout):
        """Wait for a specific color, periodically trying to focus Roblox window.

        Tries to focus Roblox every 5 seconds in case it didn't auto-focus.

        Args:
            coord: dict with "x" and "y" keys
            target_color: tuple (R, G, B)
            tolerance: int, color match tolerance per channel
            timeout: float, max seconds to wait

        Returns:
            bool: True if color detected within timeout
        """
        start_time = time.time()
        poll_interval = 0.5
        last_focus_time = time.time()

        while time.time() - start_time < timeout:
            if self.should_stop:
                return False

            try:
                # Try to focus Roblox window every 5 seconds
                if time.time() - last_focus_time >= 5.0:
                    try:
                        self.window.focus_roblox_window()
                        logger.debug("[AutoSetup] Re-focused Roblox window")
                    except Exception:
                        pass
                    last_focus_time = time.time()

                with mss.mss() as sct:
                    monitor = {
                        "top": coord["y"],
                        "left": coord["x"],
                        "width": 1,
                        "height": 1,
                    }
                    screenshot = sct.grab(monitor)
                    current_color = screenshot.pixel(0, 0)[:3]

                if self.color_detector.check_color_match(
                    current_color, target_color, tolerance
                ):
                    return True

                elapsed = int(time.time() - start_time)
                self._update_status(
                    self.status, f"⏳ Waiting... ({elapsed}s / {timeout}s)"
                )

            except Exception as e:
                logger.warning(f"[AutoSetup] Color check error: {e}")

            self._sleep(poll_interval)

        return False

    def _wait_for_color(self, coord, target_color, tolerance, timeout):
        """Wait for a specific color to appear at a coordinate

        Args:
            coord: dict with "x" and "y" keys
            target_color: tuple (R, G, B)
            tolerance: int, color match tolerance per channel
            timeout: float, max seconds to wait

        Returns:
            bool: True if color detected within timeout
        """
        start_time = time.time()
        poll_interval = 0.5  # Check every 500ms

        while time.time() - start_time < timeout:
            if self.should_stop:
                return False

            try:
                with mss.mss() as sct:
                    monitor = {
                        "top": coord["y"],
                        "left": coord["x"],
                        "width": 1,
                        "height": 1,
                    }
                    screenshot = sct.grab(monitor)
                    current_color = screenshot.pixel(0, 0)[:3]  # RGB only

                if self.color_detector.check_color_match(
                    current_color, target_color, tolerance
                ):
                    return True

                # Update status with elapsed time
                elapsed = int(time.time() - start_time)
                self._update_status(
                    self.status, f"⏳ Waiting... ({elapsed}s / {timeout}s)"
                )

            except Exception as e:
                logger.warning(f"[AutoSetup] Color check error: {e}")

            self._sleep(poll_interval)

        return False

    def _sleep(self, seconds):
        """Sleep with cancellation support

        Args:
            seconds: float, seconds to sleep

        Sleeps in small increments to allow quick cancellation.
        """
        end_time = time.time() + seconds
        while time.time() < end_time:
            if self.should_stop:
                return
            time.sleep(min(0.1, end_time - time.time()))
