"""
Discord Bot Service (v1.0.3)

Real Discord bot integration for remote control of the fishing macro.
Accepts commands (!start, !stop, !status, !screenshot, !shutdown) from authorized users
and enqueues them for safe GUI thread processing.

Security features:
- Allowed user ID whitelist (no unauthorized commands)
- Rate limiting per-author (prevents spam/abuse)
- Command queue architecture (all GUI operations on GUI thread)
- No inbound network ports (bot initiates all connections)
- Token encryption at rest (uses utils.token_encryption)

Author: GitHub Copilot
Date: February 9, 2026
"""

import discord
from discord.ext import commands
import threading
import time
from queue import Queue
from typing import Optional, List, Dict
import logging
from pathlib import Path


class DiscordBotService:
    """
    Discord bot service for remote macro control.

    Runs bot in separate daemon thread, enqueues commands to GUI command queue,
    implements rate limiting and authorization checks.
    """

    def __init__(
        self,
        bot_token: str,
        allowed_user_ids: List[int],
        command_queue: Queue,
        logger: logging.Logger,
        command_prefix: str = "!",
        auto_menu_channel_id: str = "",
        app_reference=None,
    ):
        """
        Initialize Discord bot service.

        Args:
            bot_token: Discord bot token (encrypted at rest)
            allowed_user_ids: List of authorized Discord user IDs
            command_queue: Queue for enqueuing commands to GUI thread
            logger: Logger instance for bot events
            command_prefix: Command prefix (default: "!")
            auto_menu_channel_id: Channel ID to auto-send menu on connect (optional)
            app_reference: Reference to main app for accessing menu methods
        """
        self.bot_token = bot_token
        self.allowed_user_ids = set(allowed_user_ids)  # Fast lookup
        self.command_queue = command_queue
        self.logger = logger
        self.command_prefix = command_prefix
        self.auto_menu_channel_id = auto_menu_channel_id
        self.app_reference = app_reference

        # Bot instance (created in thread)
        self.bot: Optional[commands.Bot] = None
        self._bot_thread: Optional[threading.Thread] = None
        self._running = False

        # Rate limiting (per-author cooldown)
        self._cooldowns: Dict[int, float] = {}  # {user_id: last_command_time}
        self._cooldown_seconds = 3.0  # Minimum 3 seconds between commands

        self.logger.info(
            f"[BOT] Initialized with {len(self.allowed_user_ids)} allowed users"
        )

    def start(self):
        """Start Discord bot in separate daemon thread"""
        if self._running:
            self.logger.warning("[BOT] Already running")
            return

        self._running = True
        self._bot_thread = threading.Thread(
            target=self._run_bot, daemon=True, name="DiscordBot"
        )
        self._bot_thread.start()
        self.logger.info("[BOT] Started in background thread")

    def stop(self):
        """Stop Discord bot cleanly (non-blocking safe)"""
        if not self._running:
            return

        self._running = False

        # Close bot connection
        if self.bot and not self.bot.is_closed():
            try:
                import asyncio

                loop = self.bot.loop
                if loop and not loop.is_closed():
                    if loop.is_running():
                         asyncio.run_coroutine_threadsafe(self.bot.close(), loop)
                    else:
                        # Loop exists but not running, just close it?
                        pass
            except Exception as e:
                print(f"[BOT] Warning during shutdown: {e}")

        # Wait for thread to finish (short timeout to avoid hanging)
        if self._bot_thread and self._bot_thread.is_alive():
            self._bot_thread.join(timeout=1.0)

        # Use print instead of logger to avoid deadlock
        print("[BOT] Stopped")

    def _run_bot(self):
        """Run Discord bot (executed in separate thread)"""
        import asyncio

        try:
            # Create bot with required intents
            intents = discord.Intents.default()
            intents.message_content = True  # Required to read message content

            # CRITICAL: Disable built-in help command to register our custom one
            self.bot = commands.Bot(
                command_prefix=self.command_prefix,
                intents=intents,
                help_command=None,  # Remove default !help to avoid conflict
            )

            # Register event handlers
            @self.bot.event
            async def on_ready():
                # Use print instead of self.logger to avoid deadlock with GUI thread
                print(f"[BOT] ✅ Connected as {self.bot.user} (ID: {self.bot.user.id})")
                print(f"[BOT] Serving {len(self.bot.guilds)} guilds")

                # Auto-send menu if channel is configured
                if self.auto_menu_channel_id and self.auto_menu_channel_id.isdigit():
                    try:
                        channel = self.bot.get_channel(int(self.auto_menu_channel_id))
                        if channel:
                            print(
                                f"[BOT] Auto-sending menu to #{channel.name} (ID: {channel.id})"
                            )

                            # Call the send_menu method from main app
                            if self.app_reference and hasattr(
                                self.app_reference, "_send_discord_menu"
                            ):
                                await self.app_reference._send_discord_menu(channel.id)
                                print(f"[BOT] ✅ Menu auto-sent to #{channel.name}")
                            else:
                                print(
                                    "[BOT] ⚠️ App reference not available for auto-menu"
                                )
                        else:
                            print(
                                f"[BOT] ⚠️ Auto-menu channel {self.auto_menu_channel_id} not found"
                            )
                    except Exception as e:
                        print(f"[BOT] ⚠️ Failed to auto-send menu: {e}")

            @self.bot.event
            async def on_disconnect():
                print("[BOT] ⚠️ Disconnected from Discord")

            @self.bot.event
            async def on_resumed():
                print("[BOT] ✅ Reconnected to Discord")

            @self.bot.event
            async def on_message(message):
                # Ignore bot's own messages
                if message.author.bot:
                    return

                # Check authorization
                if message.author.id not in self.allowed_user_ids:
                    # Silently ignore unauthorized users (don't reveal bot presence)
                    return

                # Check rate limit
                if not self._check_rate_limit(message.author.id):
                    msg = await message.channel.send(
                        f"⏳ {message.author.mention} Slow down! Wait {self._cooldown_seconds}s between commands."
                    )
                    # Auto-delete rate limit warning after 5 seconds
                    try:
                        await msg.delete(delay=5.0)
                    except Exception:
                        pass
                    return

                # Process commands
                await self.bot.process_commands(message)

            # Register commands
            # NOTE: No self.logger calls inside command handlers!
            # Logging from async event loop thread deadlocks with GUI thread logger.
            # All logging is done when the GUI thread processes the command queue.

            @self.bot.command(name="start", help="Start the fishing macro")
            async def cmd_start(ctx):
                if not await self._is_authorized(ctx):
                    return
                self.command_queue.put(
                    {
                        "command": "start",
                        "channel_id": ctx.channel.id,
                        "author_id": ctx.author.id,
                        "author_name": str(ctx.author),
                    }
                )
                try:
                    await ctx.message.delete()
                except Exception:
                    pass

            @self.bot.command(name="stop", help="Stop the fishing macro")
            async def cmd_stop(ctx):
                if not await self._is_authorized(ctx):
                    return
                self.command_queue.put(
                    {
                        "command": "stop",
                        "channel_id": ctx.channel.id,
                        "author_id": ctx.author.id,
                        "author_name": str(ctx.author),
                    }
                )
                try:
                    await ctx.message.delete()
                except Exception:
                    pass

            @self.bot.command(name="status", help="📊 Get detailed macro statistics")
            async def cmd_status(ctx):
                if not await self._is_authorized(ctx):
                    return
                self.command_queue.put(
                    {
                        "command": "status",
                        "channel_id": ctx.channel.id,
                        "author_id": ctx.author.id,
                        "author_name": str(ctx.author),
                    }
                )
                try:
                    await ctx.message.delete()
                except Exception:
                    pass

            @self.bot.command(name="help")
            async def cmd_help(ctx):
                """Show beautiful formatted help menu"""
                if not await self._is_authorized(ctx):
                    return

                help_msg = """```yaml
🎣 BPS FISHING MACRO — Remote Control Commands
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎮 MACRO CONTROL:
  !start       ▶️  Start the fishing macro
  !stop        ⏹️  Stop the fishing macro completely
  !pause       ⏸️  Pause (keeps engine running)
  !resume      ▶️  Resume from pause
  !restart     🔄  Restart macro (stop + start)
  !menu        🎮  Interactive control panel (buttons + live stats)

📊 INFORMATION:
  !status      📈  Detailed stats (session + today + all-time)
  !screenshot  📸  Capture game window screenshot (auto-deletes 60s)
  !eta         🍇  Estimated time until next fruit

🔧 TROUBLESHOOTING:
  !debug logs      📜  Send last 50 log lines
  !debug watchdog  🐕  Send freeze diagnostic file
  !debug on        ✅  Enable DEBUG logging
  !debug off       ❌  Disable DEBUG logging

⚠️ SYSTEM:
  !shutdown    🔌  Shutdown the computer remotely

❓ SUPPORT:
  !help        📖  Show this menu

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 TIP: All commands require authorization
🔗 GitHub: github.com/BPS-Softworks
```"""
                msg = await ctx.send(help_msg)
                # Auto-delete help after 30 seconds to keep chat clean
                try:
                    await msg.delete(delay=30.0)
                except Exception:
                    pass
                try:
                    await ctx.message.delete()
                except Exception:
                    pass

            @self.bot.command(
                name="screenshot", help="📸 Take a screenshot of the game window"
            )
            async def cmd_screenshot(ctx):
                if not await self._is_authorized(ctx):
                    return
                self.command_queue.put(
                    {
                        "command": "screenshot",
                        "channel_id": ctx.channel.id,
                        "author_id": ctx.author.id,
                        "author_name": str(ctx.author),
                    }
                )
                try:
                    await ctx.message.delete()
                except Exception:
                    pass

            @self.bot.command(name="pause", help="Pause the fishing macro")
            async def cmd_pause(ctx):
                if not await self._is_authorized(ctx):
                    return
                self.command_queue.put(
                    {
                        "command": "pause",
                        "channel_id": ctx.channel.id,
                        "author_id": ctx.author.id,
                        "author_name": str(ctx.author),
                    }
                )
                try:
                    await ctx.message.delete()
                except Exception:
                    pass

            @self.bot.command(name="resume", help="Resume the fishing macro")
            async def cmd_resume(ctx):
                if not await self._is_authorized(ctx):
                    return
                self.command_queue.put(
                    {
                        "command": "resume",
                        "channel_id": ctx.channel.id,
                        "author_id": ctx.author.id,
                        "author_name": str(ctx.author),
                    }
                )
                try:
                    await ctx.message.delete()
                except Exception:
                    pass

            @self.bot.command(
                name="restart", help="🔄 Restart the macro (stop + start)"
            )
            async def cmd_restart(ctx):
                if not await self._is_authorized(ctx):
                    return
                self.command_queue.put(
                    {
                        "command": "restart",
                        "channel_id": ctx.channel.id,
                        "author_id": ctx.author.id,
                        "author_name": str(ctx.author),
                    }
                )
                try:
                    await ctx.message.delete()
                except Exception:
                    pass

            @self.bot.command(name="debug", help="🔧 Debug tools (logs/watchdog)")
            async def cmd_debug(ctx, action: str = "help"):
                if not await self._is_authorized(ctx):
                    return
                self.command_queue.put(
                    {
                        "command": "debug",
                        "channel_id": ctx.channel.id,
                        "author_id": ctx.author.id,
                        "author_name": str(ctx.author),
                        "action": action.lower(),
                    }
                )
                try:
                    await ctx.message.delete()
                except Exception:
                    pass

            @self.bot.command(name="menu", help="🎮 Interactive control panel")
            async def cmd_menu(ctx):
                if not await self._is_authorized(ctx):
                    return
                self.command_queue.put(
                    {
                        "command": "menu",
                        "channel_id": ctx.channel.id,
                        "author_id": ctx.author.id,
                        "author_name": str(ctx.author),
                    }
                )
                try:
                    await ctx.message.delete()
                except Exception:
                    pass

            @self.bot.command(name="eta", help="🍇 Estimated time until next fruit")
            async def cmd_eta(ctx):
                if not await self._is_authorized(ctx):
                    return
                self.command_queue.put(
                    {
                        "command": "eta",
                        "channel_id": ctx.channel.id,
                        "author_id": ctx.author.id,
                        "author_name": str(ctx.author),
                    }
                )
                try:
                    await ctx.message.delete()
                except Exception:
                    pass

            @self.bot.command(name="shutdown", help="🔌 Shutdown the computer remotely")
            async def cmd_shutdown(ctx):
                if not await self._is_authorized(ctx):
                    return
                self.command_queue.put(
                    {
                        "command": "shutdown",
                        "channel_id": ctx.channel.id,
                        "author_id": ctx.author.id,
                        "author_name": str(ctx.author),
                    }
                )
                try:
                    await ctx.message.delete()
                except Exception:
                    pass

            # Run bot with auto-reconnect
            self.bot.run(self.bot_token, log_handler=None)  # discord.py handles reconnect internally

        except discord.PrivilegedIntentsRequired:
            print(
                "[BOT] ❌ Privileged intents not enabled! "
                "Go to Discord Developer Portal → Your App → Bot → Enable 'Message Content Intent'"
            )
        except discord.LoginFailure:
            print("[BOT] ❌ Invalid bot token - check Discord Developer Portal")
        except Exception as e:
            print(f"[BOT] ❌ Error: {e}")
        finally:
            self._running = False
            print("[BOT] Thread exited")

    async def _is_authorized(self, ctx) -> bool:
        """Check if command author is authorized"""
        if ctx.author.id not in self.allowed_user_ids:
            # Don't send message (silent reject for security)
            return False
        return True

    def _check_rate_limit(self, user_id: int) -> bool:
        """
        Check if user is rate limited.

        Args:
            user_id: Discord user ID

        Returns:
            True if allowed, False if rate limited
        """
        current_time = time.time()
        last_command_time = self._cooldowns.get(user_id, 0)

        if current_time - last_command_time < self._cooldown_seconds:
            return False  # Rate limited

        # Update cooldown timestamp
        self._cooldowns[user_id] = current_time
        return True

    async def send_message(self, channel_id: int, text: str, delete_after: float = None):
        """
        Send message to Discord channel.

        Args:
            channel_id: Discord channel ID
            text: Message text
            delete_after: Seconds after which to auto-delete the message (None = never)
        """
        if not self.bot or not self._running:
            return

        try:
            channel = self.bot.get_channel(channel_id)
            if channel:
                msg = await channel.send(text)
                if delete_after and msg:
                    await msg.delete(delay=delete_after)
        except Exception:
            pass

    async def send_file(self, channel_id: int, file_path: str, caption: str = "", delete_after: float = None):
        """
        Send file to Discord channel.

        Args:
            channel_id: Discord channel ID
            file_path: Path to file
            caption: Optional caption text
            delete_after: Seconds after which to auto-delete the message (None = never)
        """
        if not self.bot or not self._running:
            return

        try:
            channel = self.bot.get_channel(channel_id)
            if channel:
                file_obj = discord.File(file_path)
                msg = await channel.send(content=caption if caption else None, file=file_obj)
                if delete_after and msg:
                    await msg.delete(delay=delete_after)
        except Exception:
            pass

    async def purge_bot_messages(self, channel_id: int, limit: int = 50):
        """
        Purge bot's own messages from a channel.

        Args:
            channel_id: Discord channel ID
            limit: Max number of messages to scan
        """
        if not self.bot or not self._running:
            return

        try:
            channel = self.bot.get_channel(channel_id)
            if channel:
                def is_bot_msg(msg):
                    return msg.author == self.bot.user

                deleted = await channel.purge(limit=limit, check=is_bot_msg)
                print(f"[BOT] Purged {len(deleted)} bot messages from channel {channel_id}")
        except Exception as e:
            print(f"[BOT] Purge error: {e}")

    def add_allowed_user(self, user_id: int):
        """Add user to allowed list (runtime update)"""
        self.allowed_user_ids.add(user_id)

    def remove_allowed_user(self, user_id: int):
        """Remove user from allowed list (runtime update)"""
        self.allowed_user_ids.discard(user_id)

    def is_running(self) -> bool:
        """Check if bot is running"""
        return self._running and self._bot_thread and self._bot_thread.is_alive()
