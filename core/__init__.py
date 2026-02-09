"""
Core Module - Fishing Macro Lifecycle Orchestration

This module provides the core application lifecycle management layer.
It owns macro state, thread control, and orchestration WITHOUT any:
- GUI logic
- Vision/detection logic
- Input/control logic
- Automation/fishing logic

The Core layer acts as the "ignition key" - it starts, stops, and manages
the engine (FishingCycle) but does not implement any fishing behavior.

Components:
    - engine: FishingEngine (main orchestrator)
    - state: MacroState enum
    - exceptions: Custom exceptions for lifecycle control

Usage:
    from core import FishingEngine, MacroState
    
    engine = FishingEngine(fishing_cycle, settings, logger)
    engine.start()
    # ... macro runs in background thread ...
    engine.stop()

Design Principles:
    - Dependency injection only
    - No direct imports of vision/input/automation
    - Thread-safe state management
    - Clean shutdown guarantees
    - Future-proof for headless/remote control

Version: V5
Author: BPS
"""

from core.state import MacroState
from core.exceptions import MacroStoppedException, EngineException
from core.engine import FishingEngine

__all__ = [
    'FishingEngine',
    'MacroState',
    'MacroStoppedException',
    'EngineException',
]
