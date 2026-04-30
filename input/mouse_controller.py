"""
Mouse Controller - V5 Fishing Macro
====================================
Handles all mouse input operations with Anti-Roblox workarounds.

This module centralizes mouse movement, clicking, and dragging logic,
using the proven Anti-Roblox method (SetCursorPos + mouse_event(MOVE) + pyautogui).

All timing delays are preserved exactly as they were in V4 to maintain behavior.
"""

import ctypes
import time
import win32api
import pyautogui


class MouseController:
    """
    Centralized mouse control with Anti-Roblox workarounds.

    Uses ctypes.windll.user32 for cursor positioning and movement events,
    combined with pyautogui for click actions. This approach bypasses
    Roblox's input detection mechanisms.
    """

    def __init__(self):
        """Initialize mouse controller."""
        pass

    def move_to(self, x, y):
        """
        Move cursor to absolute screen coordinates.

        Uses win32api.SetCursorPos for compatibility with V4 behavior.

        Args:
            x (int): Screen X coordinate
            y (int): Screen Y coordinate
        """
        x, y = int(x), int(y)
        win32api.SetCursorPos((x, y))

    def click(self, x, y, hold_delay=0.05):
        """
        Simulate a mouse click using the Anti-Roblox method.

        This method uses SetCursorPos + mouse_event(MOVE) + pyautogui clicks
        to bypass Roblox's input detection. All delays are preserved from V4.

        Args:
            x (int): Screen X coordinate
            y (int): Screen Y coordinate
            hold_delay (float): Delay after click in seconds (default: 0.05)
        """
        try:
            x, y = int(x), int(y)
            win32api.SetCursorPos((x, y))
            time.sleep(0.05)  # Increased from 0.01 for robustness
            win32api.mouse_event(0x0001, 0, 1, 0, 0)
            time.sleep(0.05)  # Increased from 0.01 for robustness
            pyautogui.mouseDown()
            pyautogui.mouseUp()
            time.sleep(hold_delay)
        except Exception as e:
            print(f"Click Error: {e}")

    def drag(self, start_x, start_y, end_x, end_y):
        """
        Simulate a robust drag operation using Anti-Roblox method.

        This is the proven drag method that works reliably with Roblox.
        All timing values are preserved exactly from V4 for stability.

        Args:
            start_x (int): Start X coordinate
            start_y (int): Start Y coordinate
            end_x (int): End X coordinate
            end_y (int): End Y coordinate
        """
        try:
            start_x, start_y = int(start_x), int(start_y)
            end_x, end_y = int(end_x), int(end_y)

            # Move to start
            win32api.SetCursorPos((start_x, start_y))
            time.sleep(0.08)  # Increased from 0.03 for robustness
            win32api.mouse_event(0x0001, 0, 1, 0, 0)  # Move 1px to register
            time.sleep(0.12)  # Increased from 0.08 for robustness

            # Click down
            pyautogui.mouseDown()
            time.sleep(0.20)  # Increased from 0.15 for robustness

            # Drag to end
            win32api.SetCursorPos((end_x, end_y))
            time.sleep(0.08)  # Increased from 0.03 for robustness
            win32api.mouse_event(0x0001, 0, 1, 0, 0)  # Move 1px to register
            time.sleep(0.30)  # Increased from 0.25 for robustness

            # Release
            pyautogui.mouseUp()
            time.sleep(0.12)  # Increased from 0.08 for robustness
        except Exception as e:
            print(f"Drag Error: {e}")

    def left_down(self):
        """
        Press and hold left mouse button at current cursor position.
        Uses pyautogui for compatibility with Anti-Roblox method.
        """
        pyautogui.mouseDown()

    def left_up(self):
        """
        Release left mouse button at current cursor position.
        Uses pyautogui for compatibility with Anti-Roblox method.
        """
        pyautogui.mouseUp()

    def mouse_event(self, flags, dx=0, dy=0, data=0, extra_info=0):
        """
        Direct wrapper for win32api.mouse_event for special operations.

        This allows the main code to use special mouse events (wheel scroll,
        relative movement) while still going through the controller.

        Args:
            flags (int): Mouse event flags (MOUSEEVENTF_* constants)
            dx (int): Relative X movement (default: 0)
            dy (int): Relative Y movement (default: 0)
            data (int): Event-specific data (e.g., wheel delta) (default: 0)
            extra_info (int): Extra information (default: 0)

        Common flags:
            0x0001: MOUSEEVENTF_MOVE (relative movement)
            0x0002: MOUSEEVENTF_LEFTDOWN
            0x0004: MOUSEEVENTF_LEFTUP
            0x0008: MOUSEEVENTF_RIGHTDOWN
            0x0010: MOUSEEVENTF_RIGHTUP
            0x0800: MOUSEEVENTF_WHEEL
        """
        win32api.mouse_event(flags, dx, dy, data, extra_info)

    def drag_right(self, delta_x, delta_y, steps=10, step_delay=0.05, hold_delay=0.2):
        """
        Simulate a right-button drag using relative mouse movement events.

        Uses the same method as the fishing cycle camera rotation:
        RIGHTDOWN → multiple MOUSEEVENTF_MOVE (relative) → RIGHTUP.

        Args:
            delta_x (int): Total horizontal movement (negative = left, positive = right)
            delta_y (int): Total vertical movement (negative = up, positive = down)
            steps (int): Number of movement steps (smoother = more steps)
            step_delay (float): Delay between each step in seconds
            hold_delay (float): Delay after pressing right button before moving
        """
        try:
            step_dx = int(delta_x / steps)
            step_dy = int(delta_y / steps)

            # Hold right button
            win32api.mouse_event(0x0008, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTDOWN
            time.sleep(hold_delay)

            # Move in relative steps
            for _ in range(steps):
                win32api.mouse_event(0x0001, step_dx, step_dy, 0, 0)  # MOUSEEVENTF_MOVE
                time.sleep(step_delay)

            time.sleep(0.1)
            # Release right button
            win32api.mouse_event(0x0010, 0, 0, 0, 0)  # MOUSEEVENTF_RIGHTUP
            time.sleep(0.5)
        except Exception as e:
            print(f"DragRight Error: {e}")
            try:
                win32api.mouse_event(0x0010, 0, 0, 0, 0)  # safety release
            except Exception:
                pass
