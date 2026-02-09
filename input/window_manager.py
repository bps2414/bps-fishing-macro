"""
Window Manager - V5 Fishing Macro
==================================
Handles window focus and detection for Roblox.

This module centralizes window management using win32gui,
providing methods to find and focus the Roblox window.
"""

import win32gui


class WindowManager:
    """
    Centralized window management for Roblox window detection and focus.

    Uses win32gui to find and activate the Roblox window.
    """

    def __init__(self):
        """Initialize window manager."""
        pass

    def find_window(self):
        """
        Find the Roblox window handle.

        Returns:
            int: Window handle (hwnd) if found, None otherwise
        """
        try:
            hwnd = win32gui.FindWindow(None, "Roblox")
            return hwnd if hwnd else None
        except Exception:
            return None

    def focus_roblox_window(self):
        """
        Focus the Roblox window.

        Finds the window with title "Roblox" and brings it to the foreground.

        Returns:
            bool: True if window found and focused successfully, False otherwise
        """
        try:
            # Find Roblox window
            hwnd = win32gui.FindWindow(None, "Roblox")
            if hwnd:
                win32gui.SetForegroundWindow(hwnd)
                return True
            else:
                return False
        except Exception:
            return False

    def is_roblox_focused(self):
        """
        Check if Roblox window is currently focused.

        Returns:
            bool: True if Roblox window exists and is foreground, False otherwise
        """
        try:
            hwnd = win32gui.FindWindow(None, "Roblox")
            if hwnd:
                foreground_hwnd = win32gui.GetForegroundWindow()
                return hwnd == foreground_hwnd
            return False
        except Exception:
            return False
