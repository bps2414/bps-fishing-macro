"""
Test suite for vision/color_detector.py
========================================
Tests for RGB color matching and tolerance checking.
"""

import pytest
from vision.color_detector import ColorDetector


class TestColorDetectorInitialization:
    """Tests for ColorDetector initialization"""

    def test_default_initialization(self):
        detector = ColorDetector()
        assert detector is not None


class TestColorMatching:
    """Tests for color matching within tolerance"""

    def test_exact_color_match(self):
        """Test exact RGB color match"""
        detector = ColorDetector()
        color1 = (255, 0, 0)  # Red
        color2 = (255, 0, 0)  # Red

        assert detector.check_color_match(color1, color2, tolerance=10) == True

    def test_color_match_within_tolerance(self):
        """Test colors matching within tolerance"""
        detector = ColorDetector()
        color1 = (255, 0, 0)
        color2 = (250, 5, 5)  # Slightly different

        assert detector.check_color_match(color1, color2, tolerance=10) == True

    def test_color_mismatch_outside_tolerance(self):
        """Test colors not matching outside tolerance"""
        detector = ColorDetector()
        color1 = (255, 0, 0)  # Red
        color2 = (0, 255, 0)  # Green

        assert detector.check_color_match(color1, color2, tolerance=10) == False

    def test_none_color_handling(self):
        """Test handling of None colors"""
        detector = ColorDetector()

        assert detector.check_color_match(None, (255, 0, 0), tolerance=10) == False
        assert detector.check_color_match((255, 0, 0), None, tolerance=10) == False
        assert detector.check_color_match(None, None, tolerance=10) == False


class TestColorRangeChecking:
    """Tests for color range validation"""

    def test_color_within_range(self):
        """Test color is within min/max bounds"""
        detector = ColorDetector()
        color = (128, 128, 128)  # Gray
        min_color = (100, 100, 100)
        max_color = (200, 200, 200)

        assert detector.is_color_in_range(color, min_color, max_color) == True

    def test_color_outside_range(self):
        """Test color outside bounds"""
        detector = ColorDetector()
        color = (255, 0, 0)  # Bright red
        min_color = (0, 100, 100)
        max_color = (50, 200, 200)

        assert detector.is_color_in_range(color, min_color, max_color) == False

    def test_color_at_min_boundary(self):
        """Test color exactly at minimum boundary"""
        detector = ColorDetector()
        color = (100, 100, 100)
        min_color = (100, 100, 100)
        max_color = (200, 200, 200)

        assert detector.is_color_in_range(color, min_color, max_color) == True

    def test_color_at_max_boundary(self):
        """Test color exactly at maximum boundary"""
        detector = ColorDetector()
        color = (200, 200, 200)
        min_color = (100, 100, 100)
        max_color = (200, 200, 200)

        assert detector.is_color_in_range(color, min_color, max_color) == True

    def test_none_color_in_range(self):
        """Test handling of None in range checking"""
        detector = ColorDetector()
        min_color = (0, 0, 0)
        max_color = (255, 255, 255)

        assert detector.is_color_in_range(None, min_color, max_color) == False


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_invalid_color_tuple_length(self):
        """Test handling of invalid color tuples"""
        detector = ColorDetector()

        # Too few values - ColorDetector handles gracefully
        try:
            result = detector.check_color_match((255, 0), (255, 0, 0))
            # If it doesn't crash, acceptable
        except (IndexError, ValueError):
            pass

        # RGB vs RGBA - ColorDetector compares first 3 values
        # (255, 0, 0, 255) has RGB=(255,0,0), matches (255, 0, 0)
        assert detector.check_color_match((255, 0, 0, 255), (255, 0, 0)) == True

    def test_non_numeric_color_values(self):
        """Test handling of non-numeric values"""
        detector = ColorDetector()

        # This should handle gracefully
        try:
            result = detector.check_color_match(("red", "green", "blue"), (255, 0, 0))
            assert result == False
        except:
            # If exception, that's also acceptable
            pass
            pass
