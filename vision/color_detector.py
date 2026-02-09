"""
Color Detector - V5 Fishing Macro
==================================
Pixel color detection and matching for fruit detection.

This module handles color-based detection logic with tolerance checking.
Used primarily for Devil Fruit detection in the fishing macro.
"""


class ColorDetector:
    """
    Color detection and matching utilities.
    
    Provides methods for checking if colors match within a tolerance.
    All colors are in RGB format (not BGR).
    """
    
    def __init__(self):
        """Initialize color detector."""
        pass
    
    def check_color_match(self, color1, color2, tolerance=10):
        """
        Check if two colors match within a tolerance.
        
        Args:
            color1 (tuple): (R, G, B) first color
            color2 (tuple): (R, G, B) second color
            tolerance (int): Maximum difference per channel (default: 10)
            
        Returns:
            bool: True if colors match within tolerance, False otherwise
        """
        if color1 is None or color2 is None:
            return False
        
        try:
            # Check each channel
            r_match = abs(color1[0] - color2[0]) <= tolerance
            g_match = abs(color1[1] - color2[1]) <= tolerance
            b_match = abs(color1[2] - color2[2]) <= tolerance
            
            return r_match and g_match and b_match
        except (IndexError, TypeError):
            return False
    
    def is_color_in_range(self, color, min_color, max_color):
        """
        Check if a color is within a range.
        
        Args:
            color (tuple): (R, G, B) color to check
            min_color (tuple): (R, G, B) minimum bounds
            max_color (tuple): (R, G, B) maximum bounds
            
        Returns:
            bool: True if color is within range, False otherwise
        """
        if color is None or min_color is None or max_color is None:
            return False
        
        try:
            return (min_color[0] <= color[0] <= max_color[0] and
                    min_color[1] <= color[1] <= max_color[1] and
                    min_color[2] <= color[2] <= max_color[2])
        except (IndexError, TypeError):
            return False
    
    def get_dominant_color(self, image, region=None):
        """
        Get the dominant color in an image or region.
        
        Args:
            image (numpy.ndarray): Image in BGR format
            region (tuple): Optional (x, y, width, height) region to analyze
            
        Returns:
            tuple: (R, G, B) dominant color, or None on failure
        """
        try:
            if image is None:
                return None
            
            # Extract region if specified
            if region:
                x, y, w, h = region
                image = image[y:y+h, x:x+w]
            
            # Convert BGR to RGB
            import numpy as np
            b, g, r = image[:, :, 0], image[:, :, 1], image[:, :, 2]
            
            # Calculate average color
            avg_r = int(np.mean(r))
            avg_g = int(np.mean(g))
            avg_b = int(np.mean(b))
            
            return (avg_r, avg_g, avg_b)
        except Exception:
            return None
    
    def check_specific_color_label(self, color, label):
        """
        Check if a color matches a specific label (legendary, rare, common).
        
        Used for Smart Bait color-only detection mode.
        
        Args:
            color (tuple): (R, G, B) color to check
            label (str): 'legendary', 'rare', or 'common'
            
        Returns:
            bool: True if color matches the label, False otherwise
        """
        if color is None:
            return False
        
        try:
            r, g, b = color
            
            # Legendary: Gold-ish color (high R, moderate-high G, low B)
            if label == 'legendary':
                return r > 180 and g > 120 and b < 100
            
            # Rare: Purple-ish color (moderate-high R, low-moderate G, high B)
            elif label == 'rare':
                return r > 100 and g < 100 and b > 150
            
            # Common: Gray-ish/white color (balanced RGB, all relatively high)
            elif label == 'common':
                return r > 150 and g > 150 and b > 150 and abs(r - g) < 30 and abs(g - b) < 30
            
            return False
        except (IndexError, TypeError):
            return False
