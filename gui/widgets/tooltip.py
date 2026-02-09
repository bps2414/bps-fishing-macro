# Copyright (C) 2026 BPS
# This file is part of BPS Fishing Macro.
#
# V5: GUI Module - Tooltip Widget
# Pure extraction from main file - NO behavior changes

"""
CustomTkinter Tooltip Widget
EXACT copy from main file - maintaining all functionality.
"""

import tkinter as tk
from ..styles import (
    TOOLTIP_DELAY,
    TOOLTIP_BG_COLOR,
    TOOLTIP_FG_COLOR,
    TOOLTIP_FONT,
    TOOLTIP_WRAP_LENGTH,
)


class CTkToolTip:
    """Tooltip widget for CustomTkinter - shows hint on hover"""

    def __init__(
        self,
        widget,
        text,
        delay=TOOLTIP_DELAY,
        bg_color=TOOLTIP_BG_COLOR,
        fg_color=TOOLTIP_FG_COLOR,
        font=TOOLTIP_FONT,
        wrap_length=TOOLTIP_WRAP_LENGTH,
    ):
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
        except (tk.TclError, AttributeError) as e:
            logger.debug(f"Failed to get tooltip position (widget destroyed?): {e}")
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

        # Add text label
        label = tk.Label(
            frame,
            text=self.text,
            bg=self.bg_color,
            fg=self.fg_color,
            font=self.font,
            justify=tk.LEFT,
            wraplength=self.wrap_length,
        )
        label.pack()

        # Position tooltip
        self.tooltip_window.geometry(f"+{x}+{y}")

    def _hide_tooltip(self):
        """Hide the tooltip window"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None
