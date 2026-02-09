"""
FruitHandler - Fruit detection and webhook notification system for V5 fishing macro

Handles fruit detection, storage (multiple modes), and Discord webhooks:
- Color detection: Check if fruit or fish was caught
- Pity detection: OCR to detect legendary/mythical fruits (0/40)
- Storage modes: Drop (backspace), Store (keybind), Inventory (drag)
- Webhooks: Discord notifications with screenshots and statistics

Extracted to module by BPS.
"""

import logging
import time
import os
import json

logger = logging.getLogger(__name__)

# Webhook constants
MAX_WEBHOOK_RETRIES = 3
RETRY_DELAY_SECONDS = 2.0
WEBHOOK_TIMEOUT = 10  # seconds


class FruitHandler:
    """Manages fruit detection, storage, and webhook notifications"""

    def __init__(self, vision, input_ctrl, settings, callbacks):
        """
        Args:
            vision: Vision controller object with screen and ocr
            input_ctrl: Input controller object with mouse and keyboard
            settings: Dictionary with all fruit settings
            callbacks: Dictionary with callback functions {
                'check_legendary_pity': function() -> bool,
                'interruptible_sleep': function(duration) -> bool,
                'get_webhook_url': function() -> str,
                'get_user_id': function() -> str,
                'get_runtime': function() -> str,
                'get_fruits_caught': function() -> int,
                'get_fish_caught': function() -> int
            }
        """
        self.screen = vision.screen
        self.ocr = vision.ocr
        self.mouse = input_ctrl.mouse
        self.keyboard = input_ctrl.keyboard

        # Settings
        self.fruit_point = settings.get("fruit_point", None)
        self.fruit_color = settings.get("fruit_color", None)
        self.store_in_inventory = settings.get("store_in_inventory", False)
        self.inventory_fruit_point = settings.get("inventory_fruit_point", None)
        self.inventory_center_point = settings.get("inventory_center_point", None)
        self.use_store_keybind = settings.get("use_store_keybind", False)
        self.store_keybind = settings.get("store_keybind", "f")
        self.webhook_only_legendary = settings.get("webhook_only_legendary", False)
        self.webhook_pity_zone = settings.get("webhook_pity_zone", None)

        # Delays
        self.store_click_delay = settings.get("store_click_delay", 0.5)
        self.backspace_delay = settings.get("backspace_delay", 0.5)
        self.zoom_tick_delay = settings.get("zoom_tick_delay", 0.016)
        self.zoom_settle_delay = settings.get("zoom_settle_delay", 0.1)

        # Callbacks
        self.check_legendary_pity_callback = callbacks.get("check_legendary_pity")
        self.interruptible_sleep = callbacks.get("interruptible_sleep")
        self.get_webhook_url = callbacks.get("get_webhook_url")
        self.get_user_id = callbacks.get("get_user_id")
        self.get_runtime = callbacks.get("get_runtime")
        self.get_fruits_caught = callbacks.get("get_fruits_caught")
        self.get_fish_caught = callbacks.get("get_fish_caught")
        self.send_fruit_webhook = callbacks.get(
            "send_fruit_webhook"
        )  # Delegate to WebhookService

        # Screen dimensions (for inventory drag fallback)
        self.screen_width = settings.get("screen_width", 1920)
        self.screen_height = settings.get("screen_height", 1080)

    def update_coords(
        self, fruit_point=None, inventory_fruit_point=None, inventory_center_point=None
    ):
        """Update fruit coordinates after user changes them in UI

        Args:
            fruit_point: New fruit detection point dict {'x': x, 'y': y} or None to keep current
            inventory_fruit_point: New inventory fruit point or None to keep current
            inventory_center_point: New inventory center point or None to keep current
        """
        if fruit_point is not None:
            self.fruit_point = fruit_point
            logger.info(f"FruitHandler: Updated fruit_point to {fruit_point}")

        if inventory_fruit_point is not None:
            self.inventory_fruit_point = inventory_fruit_point
            logger.info(
                f"FruitHandler: Updated inventory_fruit_point to {inventory_fruit_point}"
            )

        if inventory_center_point is not None:
            self.inventory_center_point = inventory_center_point
            logger.info(
                f"FruitHandler: Updated inventory_center_point to {inventory_center_point}"
            )

    def check_fruit_color(self):
        """Check if caught item is a fruit using color detection

        Returns:
            True if fruit color detected at fruit_point
            False if different color (fish)
            None if detection failed or not configured
        """
        if not self.fruit_point or not self.fruit_color:
            logger.debug("[Fruit] Color check skipped - point or color not configured")
            return None

        try:
            # Capture 1x1 pixel at fruit point
            import mss

            with mss.mss() as sct:
                monitor = {
                    "top": self.fruit_point["y"],
                    "left": self.fruit_point["x"],
                    "width": 1,
                    "height": 1,
                }
                screenshot = sct.grab(monitor)
                pixel = screenshot.pixel(0, 0)  # (R, G, B, A)
                # Convert to BGR for comparison
                current_color = (pixel[2], pixel[1], pixel[0])

                # Compare with stored fruit color
                is_fruit = current_color == self.fruit_color
                logger.debug(
                    f"Fruit color check: current={current_color}, expected={self.fruit_color}, match={is_fruit}"
                )
                return is_fruit
        except Exception as e:
            logger.warning(f"Failed to check fruit color: {e}")
            return None

    def store_fruit(self, disable_normal_camera=False):
        """Store fruit using configured mode (Drop / Store / Inventory)

        Args:
            disable_normal_camera: If True, skip camera zoom during screenshot

        Returns:
            True if successful, False if interrupted
        """
        # 1. Click fruit point to select
        if self.fruit_point:
            logger.info(
                f"[Fruit] Storing fruit - mode: {'keybind' if self.use_store_keybind else 'inventory' if self.store_in_inventory else 'drop'}"
            )
            print(f"\rPre-cast: Clicking fruit point to store...", end="", flush=True)
            self.mouse.click(
                self.fruit_point["x"], self.fruit_point["y"], hold_delay=0.1
            )
            if not self.interruptible_sleep(self.store_click_delay):
                return False

        # 2. Handle fruit storage based on mode
        if self.use_store_keybind:
            # Mode 1: Use keybind (e.g., 'f')
            print(
                f"\rPre-cast: Pressing '{self.store_keybind}' to store...",
                end="",
                flush=True,
            )
            self.keyboard.press(self.store_keybind)
            self.keyboard.release(self.store_keybind)
            if not self.interruptible_sleep(self.backspace_delay):
                return False

        elif self.store_in_inventory and self.inventory_fruit_point:
            # Mode 2: Drag to inventory
            print(f"\rPre-cast: Storing in inventory...", end="", flush=True)

            # Open inventory with `
            self.keyboard.press("`")
            self.keyboard.release("`")
            if not self.interruptible_sleep(0.5):
                return False

            # Click and drag fruit to inventory center
            inv_x = self.inventory_fruit_point["x"]
            inv_y = self.inventory_fruit_point["y"]

            if self.inventory_center_point:
                center_x = self.inventory_center_point["x"]
                center_y = self.inventory_center_point["y"]
            else:
                center_x = self.screen_width // 2
                center_y = self.screen_height // 2

            print(
                f"\rPre-cast: Dragging from ({inv_x},{inv_y}) to ({center_x},{center_y})...",
                end="",
                flush=True,
            )
            self.mouse.drag(inv_x, inv_y, center_x, center_y)

            if not self.interruptible_sleep(0.2):
                return False
            if not self.interruptible_sleep(0.2):
                return False

            # Close inventory
            self.keyboard.press("`")
            self.keyboard.release("`")
            if not self.interruptible_sleep(0.5):
                return False

        else:
            # Mode 3: Drop with backspace (default)
            if self.store_in_inventory and not self.inventory_fruit_point:
                print(
                    f"\rPre-cast: WARNING - Inventory store enabled but no point set! Dropping instead.",
                    end="",
                    flush=True,
                )

            print(f"\rPre-cast: Pressing backspace to drop...", end="", flush=True)
            from pynput.keyboard import Key

            self.keyboard.press(Key.backspace)
            self.keyboard.release(Key.backspace)
            if not self.interruptible_sleep(self.backspace_delay):
                return False

        return True

    def take_fruit_screenshot(self, disable_normal_camera=False):
        """Take screenshot of fruit with camera zoom

        Only executed if webhook_only_legendary is enabled AND pity is 0/40

        Args:
            disable_normal_camera: If True, skip camera zoom

        Returns:
            (screenshot_path, is_legendary) tuple
            screenshot_path is None if screenshot was skipped
        """
        # Conditional screenshot: only if filter enabled AND 0/40 pity
        if self.webhook_only_legendary:
            logger.info(
                "[Fruit Webhook] Legendary filter ON - checking pity counter..."
            )
            print(
                f"\r[Webhook] Checking if fruit is Legendary/Mythical...",
                end="",
                flush=True,
            )
            is_legendary = (
                self.check_legendary_pity_callback()
                if self.check_legendary_pity_callback
                else False
            )

            if not is_legendary:
                logger.info(
                    "[Fruit Webhook] Not legendary/mythical (pity not 0/40) - skipping screenshot"
                )
                print(
                    f"\r[Webhook] Not a Legendary/Mythical fruit (pity not 0/40) - skipping screenshot",
                    end="",
                    flush=True,
                )
                return (None, False)
            else:
                logger.info("[Fruit Webhook] ✅ LEGENDARY/MYTHICAL FRUIT DETECTED!")
                print(
                    f"\r[Webhook] ✅ LEGENDARY/MYTHICAL FRUIT DETECTED!",
                    end="",
                    flush=True,
                )
        else:
            is_legendary = False

        # Execute screenshot with camera zoom
        screenshot_path = None

        try:
            # Zoom in 6 ticks (only if camera enabled)
            if not disable_normal_camera:
                print(f"\rPre-cast: Zooming in 6 ticks...", end="", flush=True)
                for _ in range(6):
                    self.mouse.mouse_event(
                        0x0800, 0, 0, 120, 0
                    )  # MOUSEEVENTF_WHEEL, scroll up
                    if not self.interruptible_sleep(self.zoom_tick_delay):
                        return (None, is_legendary)
                if not self.interruptible_sleep(self.zoom_settle_delay):
                    return (None, is_legendary)

            # Small delay before screenshot
            if not self.interruptible_sleep(0.2):
                return (None, is_legendary)

            # Take screenshot
            print(f"\rPre-cast: Capturing screenshot...", end="", flush=True)
            screenshot_path = self.screen.capture_center()

            # Small delay after screenshot
            if not self.interruptible_sleep(0.2):
                return (screenshot_path, is_legendary)

        finally:
            # CRITICAL: Always zoom out to restore view (try/finally protection)
            if not disable_normal_camera:
                print(f"\rPre-cast: Zooming out 6 ticks...", end="", flush=True)
                for _ in range(6):
                    self.mouse.mouse_event(
                        0x0800, 0, 0, -120, 0
                    )  # MOUSEEVENTF_WHEEL, scroll down
                    if not self.interruptible_sleep(self.zoom_tick_delay):
                        break  # Don't return False in finally
                if not self.interruptible_sleep(self.zoom_settle_delay):
                    pass  # Don't return False in finally

        return (screenshot_path, is_legendary)

    def send_fruit_webhook(self, screenshot_path, is_legendary=False):
        """Send Discord webhook notification with fruit screenshot

        Delegates to the GUI's webhook service to avoid code duplication.

        Args:
            screenshot_path: Path to screenshot file
            is_legendary: True if legendary/mythical fruit detected
        """
        if not self._send_fruit_webhook_callback:
            logger.warning("[Webhook] Webhook callback not configured")
            return

        # Delegate to the GUI's webhook service
        self._send_fruit_webhook_callback(screenshot_path, is_legendary)

    def update_settings(self, settings):
        """Update settings (called when user changes settings in UI)"""
        self.fruit_point = settings.get("fruit_point", self.fruit_point)
        self.fruit_color = settings.get("fruit_color", self.fruit_color)
        self.store_in_inventory = settings.get(
            "store_in_inventory", self.store_in_inventory
        )
        self.inventory_fruit_point = settings.get(
            "inventory_fruit_point", self.inventory_fruit_point
        )
        self.inventory_center_point = settings.get(
            "inventory_center_point", self.inventory_center_point
        )
        self.use_store_keybind = settings.get(
            "use_store_keybind", self.use_store_keybind
        )
        self.store_keybind = settings.get("store_keybind", self.store_keybind)
        self.webhook_only_legendary = settings.get(
            "webhook_only_legendary", self.webhook_only_legendary
        )
        self.webhook_pity_zone = settings.get(
            "webhook_pity_zone", self.webhook_pity_zone
        )
        self.store_click_delay = settings.get(
            "store_click_delay", self.store_click_delay
        )
        self.backspace_delay = settings.get("backspace_delay", self.backspace_delay)
        self.zoom_tick_delay = settings.get("zoom_tick_delay", self.zoom_tick_delay)
        self.zoom_settle_delay = settings.get(
            "zoom_settle_delay", self.zoom_settle_delay
        )
