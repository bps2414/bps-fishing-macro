# Copyright (C) 2026 BPS
# This file is part of BPS Fishing Macro.
#
# Timing and sleep utilities
# Extracted from V4 - ZERO behavior changes

import time


def interruptible_sleep(duration, running_flag_fn):
    """Sleep that can be interrupted by checking a running flag

    Args:
        duration: Sleep duration in seconds
        running_flag_fn: Callable that returns True if should continue, False to interrupt

    Returns:
        True if completed full duration, False if interrupted
    """
    start = time.time()
    while time.time() - start < duration:
        if not running_flag_fn():
            return False
        time.sleep(0.1)  # Check every 100ms (reduced CPU usage)
    return True


def interruptible_sleep_with_pause(duration, running_flag_fn, paused_flag_fn):
    """Sleep that can be interrupted by checking running/paused flags

    Args:
        duration: Sleep duration in seconds
        running_flag_fn: Callable that returns True if should continue, False to interrupt
        paused_flag_fn: Callable that returns True if paused, False if not paused

    Returns:
        True if completed full duration, False if interrupted by stop
    """
    start = time.time()
    while time.time() - start < duration:
        # Check if stopped
        if not running_flag_fn():
            return False

        # Wait while paused (don't consume duration time)
        while paused_flag_fn():
            if not running_flag_fn():  # Can stop during pause
                return False
            time.sleep(0.1)

        time.sleep(0.1)  # Check every 100ms (reduced CPU usage)
    return True
