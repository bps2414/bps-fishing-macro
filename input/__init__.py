"""
Input Module - V5 Fishing Macro
================================
Centralized input abstraction layer for mouse, keyboard, and window management.

This module provides a clean interface for all low-level input operations,
isolating win32api, pyautogui, pynput, and other input libraries from the rest of the codebase.

Modules:
    - mouse_controller: Mouse movement, clicking, and dragging with Anti-Roblox workarounds
    - keyboard_controller: Keyboard input simulation
    - window_manager: Window focus and detection for Roblox

Usage:
    from input import MouseController, KeyboardController, WindowManager
    
    mouse = MouseController()
    keyboard = KeyboardController()
    window = WindowManager()
    
    mouse.move_to(100, 200)
    mouse.click(100, 200)
    keyboard.tap('5')
    window.focus_roblox_window()
"""

from .mouse_controller import MouseController
from .keyboard_controller import KeyboardController
from .window_manager import WindowManager

__all__ = [
    'MouseController',
    'KeyboardController',
    'WindowManager'
]
