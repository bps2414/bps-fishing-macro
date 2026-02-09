"""
Anti-Macro Detector - V5 Fishing Macro
=======================================
Detects Roblox anti-macro black screen feature.

Roblox sometimes displays a black screen to detect macros.
This module checks if the screen is at least 50% pure black (#000000).
"""

import numpy as np


class AntiMacroDetector:
    """
    Detector for Roblox anti-macro black screen.
    
    Checks if an image contains at least 50% pure black pixels,
    which indicates Roblox's anti-macro detection is active.
    """
    
    def __init__(self, black_threshold=0.5):
        """
        Initialize anti-macro detector.
        
        Args:
            black_threshold (float): Percentage of black pixels to trigger detection (default: 0.5 = 50%)
        """
        self.black_threshold = black_threshold
    
    def is_black_screen(self, image):
        """
        Check if image is at least 50% pure black (#000000).
        
        This is Roblox's anti-macro feature - they display a black screen
        to detect if the user is using automation.
        
        Args:
            image (numpy.ndarray): Screenshot in BGR format
            
        Returns:
            bool: True if black screen detected, False otherwise
        """
        if image is None:
            return False
        
        try:
            # Extract RGB channels (ignore alpha if present)
            b, g, r = image[:, :, 0], image[:, :, 1], image[:, :, 2]
            
            # Check for pure black pixels (0, 0, 0)
            black_pixels = (r == 0) & (g == 0) & (b == 0)
            
            # Count black pixels
            total_pixels = image.shape[0] * image.shape[1]
            black_count = np.sum(black_pixels)
            
            # Check if at least threshold of pixels are black
            black_percentage = black_count / total_pixels
            
            return black_percentage >= self.black_threshold
        except Exception:
            return False
    
    def get_black_percentage(self, image):
        """
        Get the percentage of pure black pixels in an image.
        
        Args:
            image (numpy.ndarray): Screenshot in BGR format
            
        Returns:
            float: Percentage of black pixels (0.0 to 1.0), or 0.0 on error
        """
        if image is None:
            return 0.0
        
        try:
            # Extract RGB channels (ignore alpha if present)
            b, g, r = image[:, :, 0], image[:, :, 1], image[:, :, 2]
            
            # Check for pure black pixels (0, 0, 0)
            black_pixels = (r == 0) & (g == 0) & (b == 0)
            
            # Count black pixels
            total_pixels = image.shape[0] * image.shape[1]
            black_count = np.sum(black_pixels)
            
            return black_count / total_pixels
        except Exception:
            return 0.0
