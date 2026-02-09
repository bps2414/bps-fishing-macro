# gui/tabs/discord_tab.py
# Discord Tab - Bot Remote Control + Rich Presence
# Phase 1: Skeleton only (UI structure, no backend integration)

import customtkinter as ctk
import tkinter as tk


def build(app, parent):
    """
    Build the Discord tab widgets (bot + RPC).

    Phase 1: Creates UI structure only, no backend calls.

    Args:
        app: FishingMacroGUI instance (self)
        parent: The tab frame to build into
    """
    # ========== Section 1: Discord Bot (Remote Control) ==========
    bot_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
    bot_frame.pack(fill="x", pady=10, padx=10)

    bot_title = ctk.CTkLabel(
        bot_frame,
        text="🤖 DISCORD BOT (Remote Control)",
        font=("Arial", 14, "bold"),
        text_color="#f5f5f5",
    )
    bot_title.pack(pady=(10, 5))

    bot_desc = ctk.CTkLabel(
        bot_frame,
        text="Control macro remotely via Discord commands: !start, !stop, !status, !screenshot",
        font=("Arial", 9),
        text_color="#aaaaaa",
    )
    bot_desc.pack(pady=(0, 10))

    # Enable bot checkbox
    app.discord_bot_enabled_var = tk.BooleanVar(value=False)
    bot_enable_check = ctk.CTkCheckBox(
        bot_frame,
        text="Enable Discord Bot",
        variable=app.discord_bot_enabled_var,
        command=lambda: _toggle_discord_bot(app),
        fg_color="#4a4a4a",
        hover_color="#5a5a5a",
        font=("Arial", 11, "bold"),
    )
    bot_enable_check.pack(pady=5, padx=15, anchor="w")

    # Bot token entry
    ctk.CTkLabel(
        bot_frame,
        text="Bot Token (from Discord Developer Portal):",
        font=("Arial", 11, "bold"),
        anchor="w",
    ).pack(fill="x", pady=(10, 5), padx=15)

    app.discord_bot_token_entry = ctk.CTkEntry(
        bot_frame,
        width=400,
        show="*",
        placeholder_text="Paste bot token here...",
        fg_color="#1a1a1a",
        border_color="#3a3a3a",
    )
    app.discord_bot_token_entry.pack(fill="x", pady=5, padx=15)

    # Allowed user IDs
    ctk.CTkLabel(
        bot_frame,
        text="Allowed User IDs (comma-separated):",
        font=("Arial", 11, "bold"),
        anchor="w",
    ).pack(fill="x", pady=(10, 5), padx=15)

    app.discord_allowed_users_entry = ctk.CTkEntry(
        bot_frame,
        width=400,
        placeholder_text="123456789,987654321",
        fg_color="#1a1a1a",
        border_color="#3a3a3a",
    )
    app.discord_allowed_users_entry.pack(fill="x", pady=5, padx=15)

    # Test connection button
    test_bot_btn = ctk.CTkButton(
        bot_frame,
        text="Test Bot Connection",
        command=lambda: _test_bot_connection(app),
        fg_color="#2a2a2a",
        hover_color="#3a3a3a",
        width=150,
    )
    test_bot_btn.pack(pady=10, padx=15)

    # Help text
    ctk.CTkLabel(
        bot_frame,
        text="Create bot at: https://discord.com/developers/applications",
        font=("Arial", 9),
        text_color="#666666",
    ).pack(pady=(0, 10), padx=15)

    # ========== Section 2: Discord Rich Presence ==========
    rpc_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
    rpc_frame.pack(fill="x", pady=10, padx=10)

    rpc_title = ctk.CTkLabel(
        rpc_frame,
        text="🎮 DISCORD RICH PRESENCE",
        font=("Arial", 14, "bold"),
        text_color="#f5f5f5",
    )
    rpc_title.pack(pady=(10, 5))

    rpc_desc = ctk.CTkLabel(
        rpc_frame,
        text="Display macro status in your Discord profile (visible to friends)",
        font=("Arial", 9),
        text_color="#aaaaaa",
    )
    rpc_desc.pack(pady=(0, 10))

    # Enable RPC checkbox
    app.discord_rpc_enabled_var = tk.BooleanVar(value=False)
    rpc_enable_check = ctk.CTkCheckBox(
        rpc_frame,
        text="Enable Rich Presence",
        variable=app.discord_rpc_enabled_var,
        command=lambda: _toggle_discord_rpc(app),
        fg_color="#4a4a4a",
        hover_color="#5a5a5a",
        font=("Arial", 11, "bold"),
    )
    rpc_enable_check.pack(pady=5, padx=15, anchor="w")

    # Application ID (optional)
    ctk.CTkLabel(
        rpc_frame,
        text="Application ID (leave empty for default):",
        font=("Arial", 11, "bold"),
        anchor="w",
    ).pack(fill="x", pady=(10, 5), padx=15)

    app.discord_rpc_app_id_entry = ctk.CTkEntry(
        rpc_frame,
        width=300,
        placeholder_text="Optional custom app ID",
        fg_color="#1a1a1a",
        border_color="#3a3a3a",
    )
    app.discord_rpc_app_id_entry.pack(fill="x", pady=5, padx=15)

    # Help text
    ctk.CTkLabel(
        rpc_frame,
        text="Create app at: https://discord.com/developers/applications (upload assets for custom images)",
        font=("Arial", 9),
        text_color="#666666",
    ).pack(pady=(5, 10), padx=15)


# ========== Placeholder Callbacks (Phase 1: No Implementation) ==========


def _toggle_discord_bot(app):
    """Toggle Discord bot on/off (placeholder)."""
    # TODO: Phase 5 - Implement bot start/stop
    print("[Discord Tab] Bot toggle - Not implemented yet")


def _toggle_discord_rpc(app):
    """Toggle Rich Presence on/off (placeholder)."""
    # TODO: Phase 4 - Implement RPC start/stop
    print("[Discord Tab] RPC toggle - Not implemented yet")


def _test_bot_connection(app):
    """Test bot connection (placeholder)."""
    # TODO: Phase 5 - Implement bot connection test
    print("[Discord Tab] Test connection - Not implemented yet")
