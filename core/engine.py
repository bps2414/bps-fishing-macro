"""
FishingEngine - Core Lifecycle Orchestrator

The FishingEngine is the "ignition key" of the fishing macro.
It manages application lifecycle, state, and thread control.

Responsibilities:
    - Control macro lifecycle (start/stop)
    - Own the running flag
    - Manage worker thread safely
    - Orchestrate FishingCycle.main_loop()
    - Ensure clean shutdown

What it does NOT do:
    - GUI logic (no tkinter/CustomTkinter)
    - Vision/detection (delegates to FishingCycle)
    - Input control (delegates to FishingCycle)
    - Fishing behavior (delegates to FishingCycle)
    - Settings I/O (receives settings via DI)

Design:
    - Pure dependency injection
    - Thread-safe state management
    - No zombie threads guaranteed
    - Future-proof for headless/remote control

Usage:
    engine = FishingEngine(fishing_cycle, settings, logger)
    engine.start()  # Starts background thread
    # ... macro runs ...
    engine.stop()   # Clean shutdown, waits for thread

Version: V5
Author: BPS
"""

import logging
import threading
import time
from typing import Optional, Callable

from core.state import MacroState
from core.exceptions import EngineStateError, EngineThreadError


class FishingEngine:
    """
    Core macro lifecycle orchestrator.

    The engine owns:
        - Macro state (STOPPED/RUNNING/etc)
        - Running flag (thread-safe)
        - Worker thread
        - Lifecycle callbacks

    The engine delegates all fishing logic to FishingCycle.
    """

    def __init__(
        self,
        fishing_cycle,
        settings_manager,
        logger: Optional[logging.Logger] = None,
        callbacks: Optional[dict] = None,
    ):
        """
        Initialize FishingEngine with dependencies.

        Args:
            fishing_cycle: FishingCycle instance (contains all fishing logic)
            settings_manager: SettingsManager instance (for configuration)
            logger: Optional logger for engine events
            callbacks: Optional dict of callbacks:
                - on_state_change: (old_state, new_state) -> None
                - on_start: () -> None
                - on_stop: () -> None
                - on_error: (exception) -> None
        """
        # Dependencies (injected, not created)
        self._fishing_cycle = fishing_cycle
        self._settings = settings_manager
        self._logger = logger or logging.getLogger(__name__)

        # Callbacks
        self._callbacks = callbacks or {}

        # State management (thread-safe)
        self._state = MacroState.STOPPED
        self._state_lock = threading.Lock()

        # Thread control
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False  # Atomic flag for quick checks
        self._running_lock = threading.Lock()

        # Lifecycle tracking
        self._start_time: Optional[float] = None
        self._stop_requested = False

        self._logger.info("FishingEngine initialized")

    # ========== PUBLIC API ==========

    def start(self) -> bool:
        """
        Start the fishing macro.

        Creates a background worker thread that runs FishingCycle.main_loop().
        Non-blocking - returns immediately after thread is started.

        Returns:
            True if started successfully, False if already running or error

        Raises:
            EngineStateError: If engine is in invalid state for starting
        """
        with self._state_lock:
            if not self._state.can_start:
                self._logger.warning(f"Cannot start: engine is {self._state}")
                return False

            # Transition to STARTING
            self._set_state(MacroState.STARTING)

        try:
            # Set running flag (thread-safe)
            with self._running_lock:
                self._running = True
                self._stop_requested = False

            # Create worker thread
            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                name="FishingEngine-Worker",
                daemon=True,  # Daemon to prevent hanging on exit
            )

            # Start thread
            self._start_time = time.time()
            self._worker_thread.start()

            # Transition to RUNNING
            with self._state_lock:
                self._set_state(MacroState.RUNNING)

            # Callback
            if "on_start" in self._callbacks:
                self._callbacks["on_start"]()

            self._logger.info("FishingEngine started successfully")
            return True

        except Exception as e:
            self._logger.error(f"Failed to start engine: {e}", exc_info=True)

            # Cleanup on failure
            with self._running_lock:
                self._running = False

            with self._state_lock:
                self._set_state(MacroState.ERROR)

            # Callback
            if "on_error" in self._callbacks:
                self._callbacks["on_error"](e)

            return False

    def stop(self, timeout: float = 5.0) -> bool:
        """
        Stop the fishing macro.

        Signals the worker thread to stop and waits for clean shutdown.
        Blocking - waits up to timeout seconds for thread to exit.

        Args:
            timeout: Maximum seconds to wait for thread shutdown (default 5.0)

        Returns:
            True if stopped cleanly, False if timeout or error
        """
        with self._state_lock:
            if not self._state.can_stop:
                self._logger.warning(f"Cannot stop: engine is {self._state}")
                return True  # Already stopped

            # Transition to STOPPING
            self._set_state(MacroState.STOPPING)

        try:
            # Signal stop (thread-safe)
            with self._running_lock:
                self._running = False
                self._stop_requested = True

            self._logger.info("Stop signal sent, waiting for worker thread...")

            # Wait for worker thread to exit
            timed_out = False
            if self._worker_thread and self._worker_thread.is_alive():
                self._worker_thread.join(timeout=timeout)

                if self._worker_thread.is_alive():
                    self._logger.warning(
                        f"Worker thread did not stop within {timeout}s (daemon, will die on exit)"
                    )
                    timed_out = True

            # Cleanup — ALWAYS transition to STOPPED regardless of timeout
            # Daemon thread will die when process exits, so it's safe to reset state
            self._worker_thread = None
            self._start_time = None

            # ALWAYS transition to STOPPED (even on timeout) so engine can start again
            with self._state_lock:
                self._set_state(MacroState.STOPPED)

            # Callback
            if "on_stop" in self._callbacks:
                self._callbacks["on_stop"]()

            if timed_out:
                self._logger.warning(
                    "FishingEngine force-stopped (thread may still be running)"
                )
            else:
                self._logger.info("FishingEngine stopped cleanly")
            return not timed_out

        except Exception as e:
            self._logger.error(f"Error during stop: {e}", exc_info=True)

            with self._state_lock:
                self._set_state(MacroState.ERROR)

            if "on_error" in self._callbacks:
                self._callbacks["on_error"](e)

            return False

    def is_running(self) -> bool:
        """
        Check if macro is currently running.

        Thread-safe, fast check suitable for tight loops.

        Returns:
            True if macro is running, False otherwise
        """
        with self._running_lock:
            return self._running

    def get_state(self) -> MacroState:
        """
        Get current macro state.

        Returns:
            Current MacroState
        """
        with self._state_lock:
            return self._state

    def get_uptime(self) -> Optional[float]:
        """
        Get macro uptime in seconds.

        Returns:
            Uptime in seconds if running, None if stopped
        """
        if self._start_time and self.is_running():
            return time.time() - self._start_time
        return None

    # ========== INTERNAL ==========

    def _worker_loop(self):
        """
        Worker thread main loop.

        Runs FishingCycle.main_loop() and handles exceptions.
        This is the ONLY code that runs in the background thread.
        """
        self._logger.info("Worker thread started")

        try:
            # Delegate to FishingCycle - all fishing logic lives there
            self._fishing_cycle.main_loop()

        except Exception as e:
            # Catch any unhandled exceptions from FishingCycle
            self._logger.error(f"Worker thread exception: {e}", exc_info=True)

            # Transition to ERROR state
            with self._state_lock:
                self._set_state(MacroState.ERROR)

            # Callback
            if "on_error" in self._callbacks:
                self._callbacks["on_error"](e)

        finally:
            # Always mark as stopped when thread exits
            with self._running_lock:
                self._running = False

            self._logger.info("Worker thread exited")

    def _set_state(self, new_state: MacroState):
        """
        Internal state transition with callback.

        Must be called while holding _state_lock.

        Args:
            new_state: New MacroState to transition to
        """
        old_state = self._state
        self._state = new_state

        self._logger.debug(f"State transition: {old_state} -> {new_state}")

        # Callback
        if "on_state_change" in self._callbacks:
            try:
                self._callbacks["on_state_change"](old_state, new_state)
            except Exception as e:
                self._logger.error(f"State change callback error: {e}")

    # ========== FUTURE: PAUSE SUPPORT ==========

    def pause(self) -> bool:
        """
        Pause the macro (future feature).

        Not implemented yet - reserved for V6.
        """
        self._logger.warning("Pause not implemented yet")
        return False

    def resume(self) -> bool:
        """
        Resume from paused state (future feature).

        Not implemented yet - reserved for V6.
        """
        self._logger.warning("Resume not implemented yet")
        return False
