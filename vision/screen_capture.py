"""
Screen Capture - V5 Fishing Macro
==================================
Centralized screenshot capture using mss with singleton pattern and caching.

This module handles all screenshot operations with performance optimizations:
- Singleton mss instance (reused across captures)
- Screenshot caching (16ms cache to reduce CPU usage)
- DPI-aware scaling for different resolutions
- Configurable capture regions
"""

import time
import tempfile
import os
import threading
import logging
import mss
import mss.tools
import numpy as np

logger = logging.getLogger("FishingMacro")


class ScreenCapture:
    """
    Centralized screen capture with performance optimizations.

    Uses mss for fast screenshot capture with singleton pattern and caching.
    All coordinates are absolute screen coordinates.
    """

    def __init__(self, screen_width, screen_height, ref_width=1920, ref_height=1080):
        """
        Initialize screen capture.

        Args:
            screen_width (int): Current screen width
            screen_height (int): Current screen height
            ref_width (int): Reference width for scaling (default: 1920)
            ref_height (int): Reference height for scaling (default: 1080)
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.ref_width = ref_width
        self.ref_height = ref_height

        # Coordinate storage for default capture areas
        self.scan_area_coords = None
        self.auto_craft_area_coords = None

        # Thread-safe mss instance creation
        self._mss_instance = None
        self._mss_lock = threading.Lock()

        # Screenshot caching (16ms = ~60 FPS max)
        self._screenshot_cache = None
        self._screenshot_cache_time = 0
        self._screenshot_cache_duration = 0.016  # 16ms cache

    def set_scan_area(self, coords):
        """Set the default scan area coordinates.

        Args:
            coords (dict): Dictionary with 'x', 'y', 'width', 'height' keys
        """
        self.scan_area_coords = coords

    def set_auto_craft_area(self, coords):
        """Set the auto craft area coordinates.

        Args:
            coords (dict): Dictionary with 'x', 'y', 'width', 'height' keys
        """
        self.auto_craft_area_coords = coords

    def _get_mss_instance(self):
        """Get or create mss instance (thread-safe)."""
        with self._mss_lock:
            if self._mss_instance is None:
                self._mss_instance = mss.mss()
            return self._mss_instance

    def _reset_mss_instance(self):
        """Reset mss instance (thread-safe)."""
        with self._mss_lock:
            if self._mss_instance is not None:
                try:
                    self._mss_instance.close()
                except Exception:
                    pass
                self._mss_instance = None

    def capture_area(self, x=None, y=None, width=None, height=None, use_cache=True):
        """
        Capture a screenshot of a specific screen area.

        Args:
            x (int): Left coordinate (default: use scan_area_coords)
            y (int): Top coordinate (default: use scan_area_coords)
            width (int): Width of capture area (default: use scan_area_coords)
            height (int): Height of capture area (default: use scan_area_coords)
            use_cache (bool): Use cached screenshot if recent enough (default: True)

        Returns:
            numpy.ndarray: Screenshot as BGR numpy array, or None on failure
        """
        # Use default scan area coordinates if not provided
        if x is None or y is None or width is None or height is None:
            if not self.scan_area_coords:
                return None
            x = self.scan_area_coords["x"]
            y = self.scan_area_coords["y"]
            width = self.scan_area_coords["width"]
            height = self.scan_area_coords["height"]
        # Check cache first
        if use_cache:
            current_time = time.time()
            if (
                self._screenshot_cache is not None
                and current_time - self._screenshot_cache_time
                < self._screenshot_cache_duration
            ):
                return self._screenshot_cache

        # Retry logic for thread-local DC errors
        max_retries = 2
        for attempt in range(max_retries):
            try:
                # Get mss instance (thread-safe)
                mss_instance = self._get_mss_instance()

                monitor = {"left": x, "top": y, "width": width, "height": height}

                screenshot = mss_instance.grab(monitor)
                result = np.array(screenshot)

                # Update cache
                if use_cache:
                    self._screenshot_cache = result
                    self._screenshot_cache_time = time.time()

                return result
            except AttributeError as e:
                # '_thread._local' object has no attribute 'srcdc' - reset and retry
                if "srcdc" in str(e) or "_local" in str(e):
                    import logging

                    logging.getLogger("FishingMacro").debug(
                        f"[ScreenCapture] Thread-local DC error (attempt {attempt+1}/{max_retries}), resetting mss..."
                    )
                    self._reset_mss_instance()
                    if attempt == max_retries - 1:
                        # Last retry failed, log warning
                        logging.getLogger("FishingMacro").warning(
                            f"[ScreenCapture] capture_area failed at ({x},{y},{width},{height}): {e}"
                        )
                        return None
                    continue  # Retry
                else:
                    raise  # Different AttributeError, re-raise
            except Exception as e:
                # Other errors - reset instance and fail
                import logging

                logging.getLogger("FishingMacro").warning(
                    f"[ScreenCapture] capture_area failed at ({x},{y},{width},{height}): {e}"
                )
                self._reset_mss_instance()
                return None

        return None

    def capture_center(self, auto_craft_mode=False):
        """
        Capture a screenshot centered on the screen and save to a temp file.

        This method provides the screenshot path needed for webhook notifications.

        Args:
            auto_craft_mode (bool): If True, use smaller capture area (400x320) with
                                   brightness/contrast enhancement. If False, use
                                   normal area (800x500) with vertical offset.

        Returns:
            str: Path to saved PNG screenshot, or None on failure
        """
        try:
            # Get mss instance (thread-safe)
            mss_instance = self._get_mss_instance()

            # Calculate center area based on mode
            if auto_craft_mode:
                # Focused screenshot for auto craft with zoom (400x320 at 1920x1080)
                screenshot_width = int(400 * self.screen_width / self.ref_width)
                screenshot_height = int(320 * self.screen_height / self.ref_height)
                offset_y = 0
            else:
                # Normal screenshot (800x500 at 1920x1080) with vertical offset
                screenshot_width = int(800 * self.screen_width / self.ref_width)
                screenshot_height = int(500 * self.screen_height / self.ref_height)
                offset_y = int(100 * self.screen_height / self.ref_height)

            center_x = self.screen_width // 2
            center_y = self.screen_height // 2

            monitor = {
                "left": center_x - screenshot_width // 2,
                "top": center_y - screenshot_height // 2 - offset_y,
                "width": screenshot_width,
                "height": screenshot_height,
            }

            screenshot = mss_instance.grab(monitor)

            # Create temp file
            fd, screenshot_path = tempfile.mkstemp(prefix="fruit_", suffix=".png")
            os.close(fd)

            # Apply brightness/contrast enhancement for auto craft mode
            if auto_craft_mode:
                try:
                    from PIL import Image, ImageEnhance

                    img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                    enhancer = ImageEnhance.Brightness(img)
                    img = enhancer.enhance(1.25)
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(1.15)
                    img.save(screenshot_path, "PNG")
                except ImportError:
                    # Fallback if PIL not available
                    mss.tools.to_png(
                        screenshot.rgb, screenshot.size, output=screenshot_path
                    )
            else:
                mss.tools.to_png(
                    screenshot.rgb, screenshot.size, output=screenshot_path
                )

            return screenshot_path

        except Exception as e:
            logger.warning(f"[ScreenCapture] capture_center failed: {e}")
            # If mss fails, reset instance
            self._reset_mss_instance()
            return None

    def capture_window(self, hwnd):
        """
        Capture a screenshot of a specific window by handle.

        Args:
            hwnd: Window handle (from win32gui.FindWindow)

        Returns:
            numpy.ndarray: Screenshot as BGR numpy array, or None on failure
        """
        try:
            import win32gui

            # Get window rectangle
            rect = win32gui.GetWindowRect(hwnd)
            x, y, right, bottom = rect
            width = right - x
            height = bottom - y

            if width <= 0 or height <= 0:
                return None

            return self.capture_area(
                x=x, y=y, width=width, height=height, use_cache=False
            )
        except Exception as e:
            import logging

            logging.getLogger("FishingMacro").warning(
                f"[ScreenCapture] capture_window failed: {e}"
            )
            return None

    def capture_pixel(self, x, y):
        """
        Capture a single pixel color.

        Args:
            x (int): Screen X coordinate
            y (int): Screen Y coordinate

        Returns:
            tuple: (R, G, B) color values, or None on failure
        """
        try:
            # Get mss instance (thread-safe)
            mss_instance = self._get_mss_instance()

            monitor = {"left": x, "top": y, "width": 1, "height": 1}

            screenshot = mss_instance.grab(monitor)
            # Get pixel color (BGRA format from mss)
            pixel = screenshot.pixel(0, 0)
            # Convert BGRA to RGB
            return (pixel[2], pixel[1], pixel[0])
        except Exception:
            # If mss fails, reset instance
            self._reset_mss_instance()
            return None

    def cleanup(self):
        """Close the mss instance if it exists."""
        self._reset_mss_instance()

    def clear_cache(self):
        """Clear the screenshot cache."""
        self._screenshot_cache = None
        self._screenshot_cache_time = 0
