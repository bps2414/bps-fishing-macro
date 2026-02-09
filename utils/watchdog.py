# Copyright (C) 2026 BPS
# This file is part of BPS Fishing Macro.
#
# Thread Watchdog & GUI Freeze Diagnostic Tool
# Monitors the GUI thread for hangs and dumps thread stacks to a log file.

import threading
import sys
import time
import os
import traceback
import logging

logger = logging.getLogger("FishingMacro")

# Log file for watchdog dumps
WATCHDOG_LOG = os.path.join(
    (
        os.path.dirname(os.path.abspath(__file__))
        if not getattr(sys, "frozen", False)
        else os.path.dirname(sys.executable)
    ),
    "..",
    "debug_watchdog.txt",
)
WATCHDOG_LOG = os.path.normpath(WATCHDOG_LOG)


class GUIWatchdog:
    """
    Monitors the GUI (main) thread for freezes.

    How it works:
    1. A heartbeat flag is set by the GUI thread every 500ms via root.after()
    2. A background watchdog thread checks the flag every 2 seconds
    3. If the GUI hasn't sent a heartbeat in >3 seconds, it's frozen
    4. On freeze detection: dumps ALL thread stack traces to debug_watchdog.txt

    Usage:
        watchdog = GUIWatchdog(root)
        watchdog.start()
    """

    def __init__(self, root, freeze_threshold=3.0, check_interval=2.0):
        self._root = root
        self._freeze_threshold = freeze_threshold
        self._check_interval = check_interval
        self._last_heartbeat = time.time()
        self._running = False
        self._thread = None
        self._main_thread_id = threading.main_thread().ident
        self._freeze_count = 0
        self._log_file = WATCHDOG_LOG

        # Write header
        try:
            with open(self._log_file, "w", encoding="utf-8") as f:
                f.write(f"=== BPS Fishing Macro — Thread Watchdog Log ===\n")
                f.write(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Main thread ID: {self._main_thread_id}\n")
                f.write(f"Freeze threshold: {self._freeze_threshold}s\n")
                f.write(f"Log file: {self._log_file}\n")
                f.write(f"{'='*60}\n\n")
            logger.info(f"[WATCHDOG] Log file: {self._log_file}")
        except Exception as e:
            logger.warning(f"[WATCHDOG] Cannot create log file: {e}")

    def start(self):
        """Start the watchdog monitoring"""
        if self._running:
            return
        self._running = True
        self._last_heartbeat = time.time()

        # Start heartbeat on GUI thread
        self._schedule_heartbeat()

        # Start watchdog monitor thread
        self._thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="GUIWatchdog"
        )
        self._thread.start()
        logger.info("[WATCHDOG] GUI watchdog started")

    def stop(self):
        """Stop the watchdog"""
        self._running = False
        logger.info("[WATCHDOG] GUI watchdog stopped")

    def _schedule_heartbeat(self):
        """Schedule heartbeat on GUI thread (proves GUI is responsive)"""
        if not self._running:
            return
        try:
            self._root.after(500, self._heartbeat)
        except Exception:
            pass  # Root destroyed

    def _heartbeat(self):
        """Called on GUI thread — proves it's alive"""
        self._last_heartbeat = time.time()
        self._schedule_heartbeat()

    def _monitor_loop(self):
        """Background thread — checks if GUI is frozen"""
        while self._running:
            time.sleep(self._check_interval)

            elapsed = time.time() - self._last_heartbeat

            if elapsed > self._freeze_threshold:
                self._freeze_count += 1
                self._dump_freeze(elapsed)
            elif self._freeze_count > 0:
                # GUI recovered from freeze
                self._log_recovery()

    def _dump_freeze(self, elapsed):
        """Dump all thread stack traces when GUI freeze detected"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        lines = []
        lines.append(f"\n{'!'*60}")
        lines.append(f"!!! GUI FREEZE DETECTED #{self._freeze_count} at {timestamp}")
        lines.append(
            f"!!! GUI unresponsive for {elapsed:.1f}s (threshold: {self._freeze_threshold}s)"
        )
        lines.append(f"{'!'*60}\n")

        # Dump all thread stacks
        frames = sys._current_frames()
        threads_by_id = {t.ident: t for t in threading.enumerate()}

        for thread_id, frame in sorted(frames.items()):
            thread = threads_by_id.get(thread_id)
            thread_name = thread.name if thread else "???"
            is_main = (
                " *** MAIN/GUI THREAD ***" if thread_id == self._main_thread_id else ""
            )
            is_daemon = " [daemon]" if (thread and thread.daemon) else ""

            lines.append(
                f"--- Thread: {thread_name} (id={thread_id}){is_daemon}{is_main} ---"
            )

            stack = traceback.format_stack(frame)
            for line in stack:
                lines.append(line.rstrip())
            lines.append("")

        # Active threads summary
        lines.append(f"--- Active threads ({len(threads_by_id)}): ---")
        for t in sorted(threads_by_id.values(), key=lambda x: x.name):
            status = "alive" if t.is_alive() else "dead"
            daemon = "daemon" if t.daemon else "non-daemon"
            lines.append(f"  {t.name:30s} id={t.ident}  {status}  {daemon}")
        lines.append("")

        dump_text = "\n".join(lines)

        # Write to file
        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(dump_text + "\n")
        except Exception:
            pass

        # Also log to console (abbreviated)
        logger.critical(
            f"[WATCHDOG] GUI FROZEN for {elapsed:.1f}s! "
            f"Freeze #{self._freeze_count}. "
            f"Stack dump saved to {self._log_file}"
        )

        # Print the main thread stack to console for immediate debugging
        main_frame = frames.get(self._main_thread_id)
        if main_frame:
            logger.critical("[WATCHDOG] Main thread stack:")
            for line in traceback.format_stack(main_frame):
                logger.critical(line.rstrip())

    def _log_recovery(self):
        """Log when GUI recovers from a freeze"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        msg = f"\n[RECOVERY] GUI thread recovered at {timestamp} after {self._freeze_count} freeze(s)\n"

        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(msg)
        except Exception:
            pass

        logger.warning(
            f"[WATCHDOG] GUI recovered after {self._freeze_count} freeze event(s)"
        )
        self._freeze_count = 0

    def log_event(self, event_name, details=""):
        """Manually log a diagnostic event (call from anywhere)"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S.") + f"{time.time() % 1:.3f}"[2:]
        thread = threading.current_thread()
        is_main = " [MAIN]" if thread.ident == self._main_thread_id else ""

        msg = f"[{timestamp}] {event_name}{is_main} thread={thread.name} | {details}"

        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass
