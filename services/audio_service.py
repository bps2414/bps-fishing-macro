# Copyright (C) 2026 BPS
# This file is part of BPS Fishing Macro.
#
# V5: Services Module - Audio Service
# Pure extraction from main file - NO behavior changes

import os
import logging

logger = logging.getLogger("FishingMacro")

# Try to import pygame (optional)
try:
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    import pygame

    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except (ImportError, pygame.error) as e:
    logger.debug(f"Pygame not available, using fallback sound: {e}")
    PYGAME_AVAILABLE = False

# Import winsound for fallback beep
import winsound


class AudioService:
    """Audio Notification Service - handles all sound playback"""

    def __init__(
        self,
        audio_file: str = None,
        sound_enabled: bool = True,
        sound_frequency: int = 1000,
        sound_duration: int = 500,
    ):
        """
        Initialize audio service

        EXACT COPY of logic from main file - NO behavior changes

        Args:
            audio_file: Path to custom audio file (mp3/wav)
            sound_enabled: Whether sound is enabled
            sound_frequency: Frequency for fallback beep (Hz)
            sound_duration: Duration for fallback beep (ms)
        """
        self.audio_file = audio_file
        self.sound_enabled = sound_enabled
        self.sound_frequency = sound_frequency
        self.sound_duration = sound_duration
        self.pygame_available = PYGAME_AVAILABLE

    def play_notification_sound(self):
        """
        Play notification sound (Custom or Beep)

        EXACT COPY from main file - NO behavior changes
        """
        if not self.sound_enabled:
            return

        try:
            # Try to play custom sound with pygame
            if (
                self.pygame_available
                and self.audio_file
                and os.path.exists(self.audio_file)
            ):
                try:
                    pygame.mixer.music.load(self.audio_file)
                    pygame.mixer.music.play()
                    return
                except Exception as e:
                    logger.error(f"Error playing custom sound: {e}")

            # Fallback to system beep
            winsound.Beep(self.sound_frequency, self.sound_duration)
        except Exception as e:
            logger.error(f"Error playing sound: {e}")

    def set_enabled(self, enabled: bool):
        """Enable or disable sound notifications"""
        self.sound_enabled = enabled
        logger.info(f"Sound notification {'enabled' if enabled else 'disabled'}")

    def update_settings(
        self,
        audio_file: str = None,
        sound_enabled: bool = None,
        sound_frequency: int = None,
        sound_duration: int = None,
    ):
        """Update audio settings"""
        if audio_file is not None:
            self.audio_file = audio_file
        if sound_enabled is not None:
            self.sound_enabled = sound_enabled
        if sound_frequency is not None:
            self.sound_frequency = sound_frequency
        if sound_duration is not None:
            self.sound_duration = sound_duration

    def is_pygame_available(self):
        """Check if pygame is available for custom audio"""
        return self.pygame_available

    def has_custom_audio_file(self):
        """Check if custom audio file exists"""
        return self.audio_file and os.path.exists(self.audio_file)
