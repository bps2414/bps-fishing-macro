# Copyright (C) 2026 BPS
# This file is part of BPS Fishing Macro.
#
# V5.2: Discord Rich Presence Service
# Phase 4: Full Implementation

"""
Discord Rich Presence Service

Updates user's Discord profile with macro status:
- Running/Stopped state
- Fish caught count
- Fruits caught count
- Uptime

Uses pypresence library for local IPC to Discord client.

Thread-Safety:
- All RPC operations run in background thread to avoid blocking main loop
- Connection handled in separate thread
- Updates queued and executed non-blocking
"""

import logging
import threading
import time
from typing import Optional

# Try importing pypresence
try:
    from pypresence import Presence, DiscordNotFound, InvalidID, InvalidPipe

    PYPRESENCE_AVAILABLE = True
except ImportError:
    PYPRESENCE_AVAILABLE = False
    Presence = None
    DiscordNotFound = Exception
    InvalidID = Exception
    InvalidPipe = Exception


class RichPresenceService:
    """
    Discord Rich Presence service for status display.

    Non-blocking implementation with background connection thread.
    Gracefully handles Discord not running (logs warning, no crash).
    """

    # Fixed application ID for BPS Fishing Macro
    DEFAULT_APP_ID = "659816357587845140"  # Official BPS Fishing Macro app

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        application_id: Optional[str] = None,
    ):
        """
        Initialize Rich Presence service.

        Args:
            logger: Optional logger instance
            application_id: Optional Discord Application ID override
        """
        self.application_id = application_id or self.DEFAULT_APP_ID
        self.logger = logger or logging.getLogger(__name__)

        # RPC instance (created when connecting)
        self.rpc: Optional[Presence] = None
        self._connected = False
        self._connect_thread: Optional[threading.Thread] = None
        self._running = False  # Control flag for background thread

        # Check if pypresence is available
        if not PYPRESENCE_AVAILABLE:
            self.logger.warning(
                "⚠️ pypresence not installed - Rich Presence disabled. "
                "Install with: pip install pypresence"
            )

    def start(self) -> bool:
        """
        Connect to Discord client (non-blocking).

        Spawns background thread for connection to avoid blocking main loop.
        Discord not running = logs warning, returns False (no crash).

        Returns:
            True if connection initiated, False if pypresence unavailable
        """
        if not PYPRESENCE_AVAILABLE:
            self.logger.debug("Rich Presence start() - pypresence not available")
            return False

        if self._connected:
            self.logger.debug("Rich Presence already connected")
            return True

        # Start connection in background thread (non-blocking)
        self._running = True
        self._connect_thread = threading.Thread(
            target=self._connect_background, daemon=True, name="RPCConnect"
        )
        self._connect_thread.start()
        self.logger.info("🔗 Rich Presence connection initiated (background thread)")
        return True

    def _connect_background(self):
        """
        Background thread: connect to Discord client.

        Handles exceptions gracefully:
        - Discord not running -> logs warning
        - Invalid app ID -> logs error
        - Connection timeout -> logs warning
        """
        try:
            self.logger.debug(
                f"Connecting to Discord RPC (app_id={self.application_id})..."
            )
            self.rpc = Presence(self.application_id)
            self.rpc.connect()
            self._connected = True
            self.logger.info("✅ Rich Presence connected to Discord!")

        except DiscordNotFound:
            self.logger.warning(
                "⚠️ Discord not running - Rich Presence disabled. "
                "Start Discord to enable presence."
            )
            self._connected = False

        except InvalidID:
            self.logger.error(
                f"❌ Invalid Discord Application ID: {self.application_id}. "
                "Create app at https://discord.com/developers/applications"
            )
            self._connected = False

        except InvalidPipe:
            self.logger.warning(
                "⚠️ Discord IPC pipe unavailable - Rich Presence disabled. "
                "Discord may not be running or RPC is disabled."
            )
            self._connected = False

        except Exception as e:
            self.logger.warning(
                f"⚠️ Rich Presence connection failed: {type(e).__name__}: {e}"
            )
            self._connected = False

    def stop(self):
        """
        Disconnect from Discord client.

        Thread-safe: waits for connection thread to finish before closing.
        """
        self._running = False

        # Wait for connection thread to finish (max 2 seconds)
        if self._connect_thread and self._connect_thread.is_alive():
            self._connect_thread.join(timeout=2.0)

        # Close RPC connection
        if self._connected and self.rpc:
            try:
                self.rpc.close()
                self.logger.info("🔌 Rich Presence disconnected")
            except Exception as e:
                self.logger.warning(f"Error closing Rich Presence: {e}")
            finally:
                self._connected = False
                self.rpc = None

    def update_presence(
        self,
        state: str = "",
        details: str = "",
        large_image: str = "fishing_icon",
        small_image: str = "",
        start_timestamp: Optional[int] = None,
    ):
        """
        Update Rich Presence status (non-blocking).

        Thread-safe: runs in background thread if connection not ready.
        Fails gracefully if Discord disconnected (logs debug message).

        Args:
            state: State line (e.g., "Fishing in Progress")
            details: Details line (e.g., "Fish: 10 | Fruits: 2")
            large_image: Large image asset key (default: "fishing_icon")
            small_image: Small image asset key (optional)
            start_timestamp: Unix timestamp for elapsed time (optional)

        Example:
            rpc.update_presence(
                state="Fishing in Progress",
                details="Fish: 10 | Fruits: 2",
                start_timestamp=int(time.time())
            )

        Image Assets:
        - Must be uploaded to Discord app: https://discord.com/developers/applications
        - Navigate to: Your App > Rich Presence > Art Assets
        - Upload images and use asset name as key (e.g., "fishing_icon")
        """
        if not self._connected or not self.rpc:
            self.logger.debug("Rich Presence update skipped (not connected)")
            return

        # Update in background thread (non-blocking)
        threading.Thread(
            target=self._update_background,
            args=(state, details, large_image, small_image, start_timestamp),
            daemon=True,
            name="RPCUpdate",
        ).start()

    def _update_background(
        self,
        state: str,
        details: str,
        large_image: str,
        small_image: str,
        start_timestamp: Optional[int],
    ):
        """
        Background thread: update Rich Presence.

        Handles exceptions gracefully (Discord closed mid-session).
        """
        try:
            # Build update payload (only include non-empty fields)
            payload = {}
            if state:
                payload["state"] = state
            if details:
                payload["details"] = details
            if large_image:
                payload["large_image"] = large_image
            if small_image:
                payload["small_image"] = small_image
            if start_timestamp:
                payload["start"] = start_timestamp

            self.rpc.update(**payload)
            self.logger.debug(f"Rich Presence updated: {state} | {details}")

        except Exception as e:
            self.logger.warning(
                f"⚠️ Rich Presence update failed: {type(e).__name__}: {e}"
            )
            # Mark as disconnected so we don't spam errors
            self._connected = False

    def clear_presence(self):
        """
        Clear Rich Presence (show nothing).

        Thread-safe: closes connection cleanly.
        """
        if self._connected and self.rpc:
            try:
                self.rpc.clear()
                self.logger.debug("Rich Presence cleared")
            except Exception as e:
                self.logger.warning(f"Error clearing Rich Presence: {e}")

    def is_connected(self) -> bool:
        """
        Check if RPC is currently connected.

        Returns:
            True if connected to Discord, False otherwise
        """
        return self._connected
