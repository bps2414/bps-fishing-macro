"""
OCR Service - V5 Fishing Macro
===============================
Tesseract OCR wrapper for Smart Bait text recognition.

This module provides a fail-safe OCR service using external Tesseract for detecting
bait counts in the Smart Bait system. All exceptions are caught and return None,
allowing the caller to decide fallback behavior.
"""

import logging
import subprocess
import os
import tempfile
from pathlib import Path

logger = logging.getLogger("FishingMacro")

# Tesseract paths to check (in priority order)
TESSERACT_PATHS = [
    # 1. Bundled with macro installer (installed via Inno Setup)
    r"C:\Program Files\BPS Fishing Macro\tesseract\tesseract.exe",
    # 2. Standard Tesseract installation
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    # 3. Relative to exe location (for portable mode)
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "tesseract", "tesseract.exe"
    ),
]


class OCRService:
    """
    Fail-safe OCR service using external Tesseract.

    All methods return None on failure, allowing the caller to decide
    fallback behavior. Uses PSM 7 (single line) for bait number detection.
    """

    def __init__(self, text_score=0.4, default_timeout_ms=1000):
        """
        Initialize OCR service.

        Args:
            text_score (float): Minimum confidence score (deprecated, kept for compatibility)
            default_timeout_ms (int): Default OCR timeout in milliseconds (default: 1000)
        """
        self.text_score = text_score
        self.default_timeout_ms = default_timeout_ms
        self.tesseract_path = self._find_tesseract()
        self.available = self.tesseract_path is not None

        if self.available:
            logger.info(f"✅ Tesseract found: {self.tesseract_path}")
        else:
            logger.error(
                "❌ Tesseract not found! Install from: https://github.com/UB-Mannheim/tesseract/wiki"
            )

    def _find_tesseract(self):
        """Find Tesseract executable."""
        for path in TESSERACT_PATHS:
            if os.path.exists(path):
                return path
        return None

    def is_available(self):
        """
        Check if OCR is available.

        Returns:
            bool: True if Tesseract is installed, False otherwise
        """
        return self.available

    def get_instance(self):
        """
        Get Tesseract path (compatibility method).

        Returns:
            str: Path to tesseract.exe or None if unavailable
        """
        return self.tesseract_path if self.available else None

    def _preprocess_image_for_ocr(self, image):
        """
        Preprocess image for better OCR accuracy.

        Applies:
        - Grayscale conversion
        - Resize (2x upscale)
        - Adaptive thresholding (binarization)
        - Noise reduction

        Args:
            image (numpy.ndarray): BGR image

        Returns:
            numpy.ndarray: Preprocessed grayscale image
        """
        import cv2
        import numpy as np

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Upscale 2x for better OCR (Tesseract works better on larger text)
        height, width = gray.shape
        gray = cv2.resize(gray, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)

        # Apply adaptive threshold (binarization) - white text on black background
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

        # Denoise
        denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)

        return denoised

    def perform_ocr(
        self, image, timeout_ms=None, psm_mode=6, preprocess=False, char_whitelist=None
    ):
        """
        Perform OCR on an image with timeout protection.

        Args:
            image (numpy.ndarray): Image to analyze (BGR format)
            timeout_ms (int): Timeout in milliseconds (default: uses default_timeout_ms)
            psm_mode (int): Tesseract PSM mode (6=block, 7=single line, default: 6)
            preprocess (bool): Apply image preprocessing for better accuracy (default: False)
            char_whitelist (str): Optional whitelist of characters to recognize (e.g., "0123456789/")

        Returns:
            tuple: (detected_text: str, confidence: float) or (None, 0.0) on failure
        """
        if image is None:
            logger.debug("[OCR] perform_ocr called with None image")
            return None, 0.0

        if not self.available:
            logger.debug("[OCR] Tesseract not available")
            return None, 0.0

        try:
            import cv2

            # Preprocess if enabled
            processed_image = (
                self._preprocess_image_for_ocr(image) if preprocess else image
            )

            # Save image to temporary file
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
                cv2.imwrite(tmp_path, processed_image)

            timeout_sec = (timeout_ms or self.default_timeout_ms) / 1000.0
            logger.debug(f"[OCR] Running Tesseract with timeout={timeout_sec}s")

            # Hide console window on Windows
            startupinfo = None
            creationflags = 0
            if os.name == "nt":  # Windows
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                creationflags = subprocess.CREATE_NO_WINDOW

            # Build Tesseract command with optional whitelist
            cmd = [
                self.tesseract_path,
                tmp_path,
                "stdout",
                "--psm",
                str(psm_mode),  # Use specified PSM mode (6=block, 7=single line)
            ]

            # Add character whitelist if specified
            if char_whitelist:
                cmd.extend(["-c", f"tessedit_char_whitelist={char_whitelist}"])

            # Run Tesseract
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                encoding="utf-8",
                startupinfo=startupinfo,
                creationflags=creationflags,
            )

            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

            if result.returncode == 0:
                text = result.stdout.strip()

                # Clean common OCR misreads
                text = text.replace("@", " ")  # @ is often misread space
                text = text.replace("|", " ")  # | is often misread space
                text = text.replace("~", " ")  # ~ is often misread space

                # Tesseract doesn't provide confidence in stdout mode, use 0.8 as default
                confidence = 0.8 if text else 0.0
                logger.debug(f"[OCR] Result: '{text}' (confidence: {confidence:.2f})")
                return text, confidence
            else:
                logger.warning(f"[OCR] Tesseract error: {result.stderr}")
                return None, 0.0

        except subprocess.TimeoutExpired:
            logger.warning(f"[OCR] ⏰ Timeout exceeded ({timeout_sec}s)")
            try:
                if "tmp_path" in locals():
                    os.unlink(tmp_path)
            except Exception:
                pass
            return None, 0.0

        except Exception as e:
            logger.warning(f"[OCR] Execution error: {e}")
            return None, 0.0

    def parse_number(self, ocr_text, min_value=0, max_value=9999):
        """
        Parse OCR text to extract a number (used for bait counts).

        Handles common OCR misreads (O→0, l→1, I→1).

        Args:
            ocr_text (str): Raw text from OCR
            min_value (int): Minimum valid value (default: 0)
            max_value (int): Maximum valid value (default: 9999)

        Returns:
            int: Parsed number, or None if unparseable or out of range
        """
        if not ocr_text or ocr_text.strip() == "":
            return None

        # Clean the text
        cleaned = ocr_text.strip()

        # Common OCR misreads
        cleaned = cleaned.replace("O", "0").replace("o", "0")
        cleaned = cleaned.replace("l", "1").replace("I", "1")
        cleaned = cleaned.replace(",", "").replace(".", "")
        cleaned = cleaned.replace(" ", "")

        # Extract only digits
        digits_only = "".join(c for c in cleaned if c.isdigit())

        if digits_only == "":
            return None

        try:
            number = int(digits_only)

            # Range check
            if number < min_value or number > max_value:
                return None

            return number
        except ValueError:
            return None

    def perform_ocr_and_parse_number(
        self, image, timeout_ms=None, min_value=0, max_value=9999
    ):
        """
        Perform OCR and parse the result as a number.

        Convenience method that combines perform_ocr and parse_number.

        Args:
            image (numpy.ndarray): Image to analyze
            timeout_ms (int): Timeout in milliseconds
            min_value (int): Minimum valid value
            max_value (int): Maximum valid value

        Returns:
            tuple: (number: int or None, confidence: float)
        """
        text, confidence = self.perform_ocr(image, timeout_ms)
        number = self.parse_number(text, min_value, max_value)
        return number, confidence
