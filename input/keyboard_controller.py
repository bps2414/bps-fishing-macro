"""
Keyboard Controller - V5 Fishing Macro
=======================================
Handles all keyboard input operations.

This module centralizes keyboard input using pynput.keyboard.Controller,
providing a clean interface for pressing keys and hotkeys.
"""

import time
from pynput.keyboard import Controller, Key


class KeyboardController:
    """
    Centralized keyboard control using pynput.
    
    Provides methods for pressing, releasing, and tapping keys.
    Supports both character keys ('5', '`') and special keys (Key.backspace, Key.shift).
    """
    
    def __init__(self):
        """Initialize keyboard controller with pynput Controller."""
        self.kb = Controller()
    
    def press(self, key):
        """
        Press and hold a key.
        
        Args:
            key: Key to press (string like '5' or Key object like Key.backspace)
        """
        self.kb.press(key)
    
    def release(self, key):
        """
        Release a previously pressed key.
        
        Args:
            key: Key to release (string like '5' or Key object like Key.backspace)
        """
        self.kb.release(key)
    
    def tap(self, key, delay=0.05):
        """
        Press and release a key with a delay.
        
        This is a convenience method that combines press and release
        with a configurable delay between them.
        
        Args:
            key: Key to tap (string like '5' or Key object like Key.backspace)
            delay (float): Delay between press and release in seconds (default: 0.05)
        """
        self.kb.press(key)
        time.sleep(delay)
        self.kb.release(key)
