"""
Automation Module - V5 Fishing Macro
=====================================
High-level fishing automation orchestration.

This module contains all gameplay automation logic:
- Smart Bait management (OCR + color fallback)
- Fruit handling (detection, storage, webhooks)
- Craft automation (bait crafting sequences)
- Fishing cycle orchestration (main loop, normal/auto craft modes)

All automation components use dependency injection and do not directly
access GUI, settings files, or low-level I/O. They receive pre-configured
dependencies (vision, input, settings) from the main orchestrator.

Modules:
    - bait_manager: Smart Bait selection (OCR + color fallback)
    - fruit_handler: Fruit detection, storage, webhook notifications
    - craft_automation: Auto craft bait sequences
    - fishing_cycle: Main fishing loop orchestration (Phase 6)

Usage:
    from automation import BaitManager, FruitHandler, CraftAutomation, FishingCycle
    
    bait_mgr = BaitManager(vision, settings, callbacks)
    fruit_hdl = FruitHandler(vision, input, settings, callbacks)
    craft_auto = CraftAutomation(input, settings, callbacks)
    fishing_cyc = FishingCycle(vision, input, bait_mgr, fruit_hdl, craft_auto, settings, callbacks, logger, stats_mgr)
"""

from .bait_manager import BaitManager
from .fruit_handler import FruitHandler
from .craft_automation import CraftAutomation
from .fishing_cycle import FishingCycle

__all__ = [
    'BaitManager',
    'FruitHandler',
    'CraftAutomation',
    'FishingCycle'
]

