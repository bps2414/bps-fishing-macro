"""
Macro State Definitions

Defines the possible states of the fishing macro engine.
"""

from enum import Enum, auto


class MacroState(Enum):
    """Macro execution states"""
    
    STOPPED = auto()    # Macro is stopped, no threads running
    STARTING = auto()   # Macro is initializing (transitional)
    RUNNING = auto()    # Macro is actively fishing
    STOPPING = auto()   # Macro is shutting down (transitional)
    PAUSED = auto()     # Reserved for future pause functionality
    ERROR = auto()      # Macro encountered fatal error
    
    def __str__(self):
        return self.name.title()
    
    @property
    def is_active(self):
        """Returns True if macro is running or transitioning"""
        return self in (MacroState.STARTING, MacroState.RUNNING, MacroState.STOPPING)
    
    @property
    def can_start(self):
        """Returns True if macro can be started from this state"""
        return self in (MacroState.STOPPED, MacroState.ERROR)
    
    @property
    def can_stop(self):
        """Returns True if macro can be stopped from this state"""
        return self in (MacroState.STARTING, MacroState.RUNNING, MacroState.PAUSED)
