"""
Vision Module - V5 Fishing Macro
=================================
Centralized screen analysis for OCR, color detection, and screenshot capture.

This module provides a clean interface for all vision-related operations,
isolating screen capture, color detection, OCR, and anti-macro detection
from the rest of the codebase.

Modules:
    - screen_capture: Screenshot capture with mss (singleton, caching, scaling)
    - color_detector: Pixel color checking for fruit detection
    - ocr_service: RapidOCR wrapper for Smart Bait system
    - anti_macro_detector: Roblox anti-macro black screen detection

Usage:
    from vision import ScreenCapture, ColorDetector, OCRService, AntiMacroDetector
    
    capture = ScreenCapture(screen_width, screen_height)
    screenshot = capture.capture_area(x, y, width, height)
    
    detector = ColorDetector()
    is_match = detector.check_color_match(pixel_color, target_color, tolerance)
    
    ocr = OCRService()
    text = ocr.perform_ocr(image)
"""

from .screen_capture import ScreenCapture
from .color_detector import ColorDetector
from .ocr_service import OCRService
from .anti_macro_detector import AntiMacroDetector

__all__ = [
    'ScreenCapture',
    'ColorDetector',
    'OCRService',
    'AntiMacroDetector'
]
