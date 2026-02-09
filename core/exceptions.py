"""
Core Exceptions

Custom exceptions for macro lifecycle control and error handling.
"""


class EngineException(Exception):
    """Base exception for FishingEngine errors"""
    pass


class MacroStoppedException(EngineException):
    """
    Raised when macro is stopped during operation.
    
    This is a NORMAL flow control exception, not an error.
    Used to cleanly exit loops when user stops the macro.
    """
    pass


class EngineStateError(EngineException):
    """Raised when engine operation is invalid for current state"""
    pass


class EngineThreadError(EngineException):
    """Raised when thread management fails"""
    pass
