# Copyright (C) 2026 BPS
# This file is part of BPS Fishing Macro.
#
# V5: GUI Module - Tabs Package

"""
GUI Tab Components
Each tab module exports a build(app, parent) function.
"""

from gui.tabs import (
    general_tab,
    settings_tab,
    fishing_tab,
    craft_tab,
    webhook_tab,
    advanced_tab,
    stats_tab,
    logging_tab,
    discord_bot_tab,  # V5.2: Discord Bot Remote Control
)

__all__ = [
    "general_tab",
    "settings_tab",
    "fishing_tab",
    "craft_tab",
    "webhook_tab",
    "advanced_tab",
    "stats_tab",
    "logging_tab",
    "discord_bot_tab",
]
