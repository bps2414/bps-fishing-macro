# gui/tabs/logging_tab.py
# Logging Tab - Real-time log viewer in the GUI
import customtkinter as ctk
import tkinter as tk
import logging
from collections import deque
from queue import Queue


class GUILogHandler(logging.Handler):
    """
    Custom logging handler that pushes log records to a GUI text widget.

    CRITICAL FIX (Phase 7): emit() NO LONGER calls callback synchronously.
    Instead, logs are buffered to a queue and polled by GUI thread.
    This prevents deadlock when multiple threads log simultaneously.
    """

    def __init__(self, log_queue, max_lines=500):
        super().__init__()
        self.log_queue = log_queue  # Thread-safe queue instead of callback
        self.buffer = deque(maxlen=max_lines)
        self.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
            )
        )

    def emit(self, record):
        """
        Emit a log record (called from ANY thread).

        CRITICAL: This method MUST be non-blocking and MUST NOT call Tk operations.
        Simply format the message and push to queue. GUI thread polls the queue.
        """
        try:
            msg = self.format(record)
            self.buffer.append((msg, record.levelname))
            # Push to queue instead of calling callback (no Tk operations here!)
            self.log_queue.put_nowait((msg, record.levelname))
        except Exception:
            self.handleError(record)


def build(app, parent):
    """Build the Logging tab widgets.

    Args:
        app: FishingMacroGUI instance (self)
        parent: The tab frame to build into
    """
    # Controls frame
    controls_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
    controls_frame.pack(fill="x", pady=(10, 5))

    ctk.CTkLabel(
        controls_frame,
        text="📋 LIVE LOG VIEWER",
        font=("Arial", 14, "bold"),
        text_color=app.accent_color,
    ).pack(pady=(10, 5))

    # Control buttons row
    btn_row = ctk.CTkFrame(controls_frame, fg_color="transparent")
    btn_row.pack(fill="x", padx=15, pady=(5, 10))

    # Auto-scroll toggle
    app._log_auto_scroll = tk.BooleanVar(value=True)
    auto_scroll_check = ctk.CTkCheckBox(
        btn_row,
        text="Auto-scroll",
        variable=app._log_auto_scroll,
        fg_color=app.success_color,
        hover_color=app.hover_color,
        font=("Arial", 11),
    )
    auto_scroll_check.pack(side="left", padx=5)

    # Clear button
    ctk.CTkButton(
        btn_row,
        text="🗑️ Clear",
        command=lambda: _clear_log(app),
        width=80,
        fg_color=app.button_color,
        hover_color=app.hover_color,
        font=("Arial", 11),
    ).pack(side="left", padx=5)

    # Level filter
    ctk.CTkLabel(
        btn_row,
        text="Filter:",
        font=("Arial", 11),
    ).pack(side="left", padx=(15, 5))

    app._log_level_var = tk.StringVar(value="DEBUG")
    level_combo = ctk.CTkComboBox(
        btn_row,
        variable=app._log_level_var,
        values=["DEBUG", "INFO", "WARNING", "ERROR"],
        width=100,
        state="readonly",
        fg_color=app.button_color,
        button_color=app.accent_color,
        button_hover_color=app.hover_color,
        command=lambda e: _apply_filter(app),
    )
    level_combo.pack(side="left", padx=5)

    # Log text widget
    app._log_textbox = ctk.CTkTextbox(
        parent,
        fg_color="#0d0d0d",
        text_color="#cccccc",
        font=("Consolas", 10),
        corner_radius=8,
        border_width=1,
        border_color="#333333",
        wrap="word",
        state="disabled",
    )
    app._log_textbox.pack(fill="both", expand=True, pady=5, padx=5)

    # Configure text tags for log levels
    app._log_textbox.configure(state="normal")
    app._log_textbox._textbox.tag_configure("DEBUG", foreground="#888888")
    app._log_textbox._textbox.tag_configure("INFO", foreground="#00ccff")
    app._log_textbox._textbox.tag_configure("WARNING", foreground="#ffaa00")
    app._log_textbox._textbox.tag_configure("ERROR", foreground="#ff4444")
    app._log_textbox._textbox.tag_configure("CRITICAL", foreground="#ff0000")
    app._log_textbox.configure(state="disabled")

    # Status bar
    status_row = ctk.CTkFrame(parent, fg_color="transparent")
    status_row.pack(fill="x", pady=(0, 5), padx=5)
    app._log_count_label = ctk.CTkLabel(
        status_row,
        text="Lines: 0",
        font=("Arial", 9),
        text_color="#666666",
    )
    app._log_count_label.pack(side="left", padx=5)

    app._log_line_count = 0
    app._log_max_lines = 500

    # Create log queue BEFORE installing handler (handler needs it)
    app._log_queue = Queue()

    # Install the GUI log handler
    _install_handler(app)

    # Start polling the log queue on GUI thread (every 100ms)
    _poll_log_queue(app)


def _poll_log_queue(app):
    """Poll the log queue and append messages to the text widget (GUI thread only)."""
    try:
        # Process all pending log messages (non-blocking)
        while not app._log_queue.empty():
            try:
                msg, level = app._log_queue.get_nowait()
                _append_log(app, msg, level)
            except Exception:
                break
    except Exception:
        pass

    # Schedule next poll (every 100ms)
    try:
        app.root.after(100, lambda: _poll_log_queue(app))
    except Exception:
        pass  # GUI closed


def _install_handler(app):
    """Install the GUI logging handler into the root logger."""
    handler = GUILogHandler(app._log_queue, max_lines=500)
    handler.setLevel(logging.DEBUG)

    # Add to root logger so all module loggers are captured
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    # Store reference to prevent garbage collection
    app._gui_log_handler = handler


def _append_log(app, msg, level):
    """Append a log message to the text widget."""
    if not hasattr(app, "_log_textbox"):
        return

    # Check level filter
    level_order = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}
    min_level = level_order.get(app._log_level_var.get(), 0)
    msg_level = level_order.get(level, 0)
    if msg_level < min_level:
        return

    try:
        app._log_textbox.configure(state="normal")

        # Remove oldest lines if exceeding max
        app._log_line_count += 1
        if app._log_line_count > app._log_max_lines:
            app._log_textbox._textbox.delete("1.0", "2.0")
            app._log_line_count -= 1

        # Insert with color tag
        app._log_textbox._textbox.insert("end", msg + "\n", level)

        app._log_textbox.configure(state="disabled")

        # Auto-scroll to bottom
        if app._log_auto_scroll.get():
            app._log_textbox._textbox.see("end")

        # Update line count
        app._log_count_label.configure(text=f"Lines: {app._log_line_count}")
    except Exception:
        pass


def _clear_log(app):
    """Clear all log entries."""
    if not hasattr(app, "_log_textbox"):
        return
    app._log_textbox.configure(state="normal")
    app._log_textbox._textbox.delete("1.0", "end")
    app._log_textbox.configure(state="disabled")
    app._log_line_count = 0
    app._log_count_label.configure(text="Lines: 0")


def _apply_filter(app):
    """Re-apply filter (future log messages will be filtered)."""
    # Filter only applies to new messages; existing messages stay visible
    pass
