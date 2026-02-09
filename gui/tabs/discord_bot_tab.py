"""
Discord Settings Tab (V5.2)

Unified Discord settings tab for:
- Rich Presence (status display)
- Bot Remote Control (commands via Discord)

Author: GitHub Copilot
Date: February 9, 2026
"""

import customtkinter as ctk
import logging

logger = logging.getLogger(__name__)


def create_discord_bot_tab(parent: ctk.CTkFrame, app):
    """Create unified Discord settings tab"""

    # Main container with padding
    container = ctk.CTkFrame(parent, fg_color="transparent")
    container.pack(fill="both", expand=True, padx=20, pady=20)

    # ============================================================================
    # RICH PRESENCE SECTION
    # ============================================================================
    rpc_frame = ctk.CTkFrame(container)
    rpc_frame.pack(fill="x", pady=(0, 20))

    rpc_header = ctk.CTkLabel(
        rpc_frame,
        text="📊 Rich Presence (Status Display)",
        font=("Segoe UI", 16, "bold"),
        text_color=app.accent_color,
    )
    rpc_header.pack(fill="x", padx=15, pady=(15, 5))

    rpc_info = ctk.CTkLabel(
        rpc_frame,
        text="Display macro status on your Discord profile (fish count, runtime, hourly rate)",
        font=("Segoe UI", 11),
        text_color="#888888",
    )
    rpc_info.pack(fill="x", padx=15, pady=(0, 15))

    # RPC Enable switch
    rpc_switch_frame = ctk.CTkFrame(rpc_frame, fg_color="transparent")
    rpc_switch_frame.pack(fill="x", padx=15, pady=(0, 15))

    app.discord_rpc_enabled_var = ctk.BooleanVar(value=app.discord_rpc_enabled)

    rpc_switch = ctk.CTkSwitch(
        rpc_switch_frame,
        text="Enable Rich Presence",
        variable=app.discord_rpc_enabled_var,
        command=lambda: app.toggle_discord_rpc(),
        font=("Segoe UI", 13),
    )
    rpc_switch.pack(side="left")

    app.rpc_status_label = ctk.CTkLabel(
        rpc_switch_frame,
        text="⚪ Not Running",
        font=("Segoe UI", 11),
        text_color="#888888",
    )
    app.rpc_status_label.pack(side="right", padx=10)

    # ============================================================================
    # DISCORD BOT SECTION
    # ============================================================================
    bot_frame = ctk.CTkFrame(container)
    bot_frame.pack(fill="x", pady=(0, 20))

    bot_header = ctk.CTkLabel(
        bot_frame,
        text="🤖 Discord Bot (Remote Control)",
        font=("Segoe UI", 16, "bold"),
        text_color=app.accent_color,
    )
    bot_header.pack(fill="x", padx=15, pady=(15, 5))

    bot_info = ctk.CTkLabel(
        bot_frame,
        text="Control macro remotely via Discord commands: !start, !stop, !status, !screenshot",
        font=("Segoe UI", 11),
        text_color="#888888",
    )
    bot_info.pack(fill="x", padx=15, pady=(0, 15))

    # Bot Enable switch
    bot_switch_frame = ctk.CTkFrame(bot_frame, fg_color="transparent")
    bot_switch_frame.pack(fill="x", padx=15, pady=(0, 15))

    app.discord_bot_enabled_var = ctk.BooleanVar(value=app.discord_bot_enabled)

    bot_switch = ctk.CTkSwitch(
        bot_switch_frame,
        text="Enable Discord Bot",
        variable=app.discord_bot_enabled_var,
        command=lambda: app.toggle_discord_bot(),
        font=("Segoe UI", 13),
    )
    bot_switch.pack(side="left")

    app.bot_status_label = ctk.CTkLabel(
        bot_switch_frame,
        text="🔴 Offline",
        font=("Segoe UI", 11),
        text_color="#ff4444",
    )
    app.bot_status_label.pack(side="right", padx=10)

    # Application ID
    app_id_label = ctk.CTkLabel(
        bot_frame, text="Application ID:", font=("Segoe UI", 12), anchor="w"
    )
    app_id_label.pack(fill="x", padx=15, pady=(10, 5))

    app.bot_app_id_entry = ctk.CTkEntry(
        bot_frame,
        placeholder_text="1234567890123456789 (from Discord Developer Portal)",
        font=("Consolas", 11),
    )
    app.bot_app_id_entry.pack(fill="x", padx=15, pady=(0, 10))
    if app.discord_bot_app_id:
        app.bot_app_id_entry.insert(0, app.discord_bot_app_id)

    # Bot Token
    token_label = ctk.CTkLabel(
        bot_frame, text="Bot Token:", font=("Segoe UI", 12), anchor="w"
    )
    token_label.pack(fill="x", padx=15, pady=(0, 5))

    token_entry_frame = ctk.CTkFrame(bot_frame, fg_color="transparent")
    token_entry_frame.pack(fill="x", padx=15, pady=(0, 10))

    app.bot_token_entry = ctk.CTkEntry(
        token_entry_frame,
        placeholder_text="MTxxxxxxxxxx.xxxxxx.xxxxxxxxxx",
        show="•",
        font=("Consolas", 11),
    )
    app.bot_token_entry.pack(side="left", fill="x", expand=True)

    show_token_btn = ctk.CTkButton(
        token_entry_frame,
        text="👁️",
        width=40,
        command=lambda: app.toggle_bot_token_visibility(),
    )
    show_token_btn.pack(side="left", padx=(5, 0))

    # Allowed Users
    users_label = ctk.CTkLabel(
        bot_frame,
        text="Allowed User IDs (one per line):",
        font=("Segoe UI", 12),
        anchor="w",
    )
    users_label.pack(fill="x", padx=15, pady=(10, 5))

    app.bot_allowed_users_text = ctk.CTkTextbox(
        bot_frame, height=80, font=("Consolas", 11)
    )
    app.bot_allowed_users_text.pack(fill="x", padx=15, pady=(0, 10))
    if app.discord_bot_allowed_users:
        app.bot_allowed_users_text.insert(
            "1.0", "\n".join(map(str, app.discord_bot_allowed_users))
        )

    # ============================================================================
    # AUTO-MENU CONFIGURATION
    # ============================================================================
    auto_menu_label = ctk.CTkLabel(
        bot_frame,
        text="🎯 Auto-Menu Configuration (Optional):",
        font=("Segoe UI", 13, "bold"),
        anchor="w",
        text_color=app.accent_color,
    )
    auto_menu_label.pack(fill="x", padx=15, pady=(15, 5))

    auto_menu_info = ctk.CTkLabel(
        bot_frame,
        text="Configure to automatically send the control menu when bot connects",
        font=("Segoe UI", 10),
        text_color="#888888",
    )
    auto_menu_info.pack(fill="x", padx=15, pady=(0, 10))

    # Guild ID
    guild_label = ctk.CTkLabel(
        bot_frame, text="Server (Guild) ID:", font=("Segoe UI", 11), anchor="w"
    )
    guild_label.pack(fill="x", padx=15, pady=(5, 3))

    guild_entry_frame = ctk.CTkFrame(bot_frame, fg_color="transparent")
    guild_entry_frame.pack(fill="x", padx=15, pady=(0, 10))

    app.bot_guild_id_entry = ctk.CTkEntry(
        guild_entry_frame,
        placeholder_text="Right-click server icon → Copy Server ID",
        font=("Consolas", 11),
    )
    app.bot_guild_id_entry.pack(side="left", fill="x", expand=True)
    if hasattr(app, "discord_bot_guild_id") and app.discord_bot_guild_id:
        app.bot_guild_id_entry.insert(0, app.discord_bot_guild_id)

    list_channels_btn = ctk.CTkButton(
        guild_entry_frame,
        text="📋 List Channels",
        width=120,
        command=lambda: app.list_discord_channels(),
        fg_color="#4a5568",
        hover_color="#2d3748",
    )
    list_channels_btn.pack(side="left", padx=(5, 0))

    # Auto-Menu Channel ID
    channel_label = ctk.CTkLabel(
        bot_frame, text="Auto-Menu Channel ID:", font=("Segoe UI", 11), anchor="w"
    )
    channel_label.pack(fill="x", padx=15, pady=(5, 3))

    app.bot_auto_menu_channel_entry = ctk.CTkEntry(
        bot_frame,
        placeholder_text="Right-click #channel → Copy Channel ID (e.g., #gpo-bot)",
        font=("Consolas", 11),
    )
    app.bot_auto_menu_channel_entry.pack(fill="x", padx=15, pady=(0, 10))
    if (
        hasattr(app, "discord_bot_auto_menu_channel")
        and app.discord_bot_auto_menu_channel
    ):
        app.bot_auto_menu_channel_entry.insert(0, app.discord_bot_auto_menu_channel)

    # Action buttons
    btn_frame = ctk.CTkFrame(bot_frame, fg_color="transparent")
    btn_frame.pack(fill="x", padx=15, pady=(10, 15))

    save_btn = ctk.CTkButton(
        btn_frame,
        text="💾 Save Settings",
        command=lambda: app.save_discord_bot_settings(),
        height=35,
        font=("Segoe UI", 12, "bold"),
    )
    save_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))

    test_btn = ctk.CTkButton(
        btn_frame,
        text="🔌 Test Connection",
        command=lambda: app.test_discord_bot_connection(),
        height=35,
        font=("Segoe UI", 12),
        fg_color="#4a5568",
        hover_color="#2d3748",
    )
    test_btn.pack(side="left", expand=True, fill="x", padx=(5, 0))

    # ============================================================================
    # INFO SECTION
    # ============================================================================
    info_frame = ctk.CTkFrame(container, fg_color="#1a1a2e")
    info_frame.pack(fill="x")

    info_header = ctk.CTkLabel(
        info_frame, text="ℹ️ Bot Setup Instructions", font=("Segoe UI", 13, "bold")
    )
    info_header.pack(fill="x", padx=15, pady=(15, 10))

    setup_text = """⚠️ IMPORTANT: Enable Message Content Intent in Discord Developer Portal
1. Go to https://discord.com/developers/applications/
2. Select your application → Bot tab
3. Scroll to "Privileged Gateway Intents"
4. Enable "MESSAGE CONTENT INTENT" (required for commands)
5. Save changes

Bot Commands:
• !start - Start the fishing macro
• !stop - Stop the fishing macro
• !status - Get current status and statistics
• !screenshot - Capture game window screenshot

Security: Only whitelisted user IDs can send commands (3s rate limit)"""

    commands_label = ctk.CTkLabel(
        info_frame,
        text=setup_text,
        font=("Segoe UI", 10),
        justify="left",
        anchor="w",
    )
    commands_label.pack(fill="x", padx=15, pady=(0, 15))

    # Load saved token if exists
    _load_bot_token(app)


def _load_bot_token(app):
    """Load and decrypt saved bot token into entry field"""
    try:
        from utils.token_encryption import decrypt_token

        bot_settings = app.settings.load_discord_bot_settings()

        # Load saved values if they exist
        if bot_settings.get("bot_token"):
            decrypted_token = decrypt_token(bot_settings["bot_token"])
            app.bot_token_entry.delete(0, "end")
            app.bot_token_entry.insert(0, decrypted_token)

    except Exception as e:
        logger.warning(f"[Discord] Could not load saved token: {e}")
