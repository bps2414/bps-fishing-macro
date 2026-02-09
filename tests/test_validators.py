"""
Test suite for utils/validators.py
===================================
Tests for coordinate, webhook, and user ID validation.
"""

import pytest
from utils.validators import (
    validate_webhook_url,
    validate_user_id,
    validate_coordinates,
    validate_area_coords,
)


class TestWebhookValidation:
    """Tests for Discord webhook URL validation"""

    def test_valid_discord_webhook(self):
        url = "https://discord.com/api/webhooks/123456789/abcdefg"
        assert validate_webhook_url(url) == True

    def test_valid_discordapp_webhook(self):
        url = "https://discordapp.com/api/webhooks/987654321/xyz"
        assert validate_webhook_url(url) == True

    def test_invalid_protocol(self):
        url = "http://discord.com/api/webhooks/123/abc"
        assert validate_webhook_url(url) == False

    def test_invalid_domain(self):
        url = "https://example.com/webhooks/123/abc"
        assert validate_webhook_url(url) == False

    def test_empty_url(self):
        # Empty URL returns False (not valid format)
        assert validate_webhook_url("") == False

    def test_none_url(self):
        # None returns False (not a string)
        assert validate_webhook_url(None) == False

    def test_malformed_url(self):
        url = "not_a_url_at_all"
        assert validate_webhook_url(url) == False


class TestUserIDValidation:
    """Tests for Discord user ID validation"""

    def test_valid_18_digit_id(self):
        assert validate_user_id("123456789012345678") == True

    def test_valid_17_digit_id(self):
        # Discord IDs can be 17-20 digits
        assert validate_user_id("12345678901234567") == True

    def test_valid_19_digit_id(self):
        assert validate_user_id("1234567890123456789") == True

    def test_valid_20_digit_id(self):
        # 20 digits is still valid (upper bound)
        assert validate_user_id("12345678901234567890") == True

    def test_invalid_too_short(self):
        assert validate_user_id("12345") == False

    def test_invalid_too_long(self):
        # 21 digits exceeds Discord limit
        assert validate_user_id("123456789012345678901") == False

    def test_invalid_non_numeric(self):
        assert validate_user_id("12345678901234567a") == False

    def test_empty_id(self):
        # Empty ID returns True (allowed by design - ping disabled)
        assert validate_user_id("") == True

    def test_none_id(self):
        # None returns True (allowed by design - ping not configured)
        assert validate_user_id(None) == True


class TestCoordinateValidation:
    """Tests for coordinate validation"""

    def test_valid_coords(self):
        coords = {"x": 100, "y": 200}
        assert validate_coordinates(coords, "test_point", 1920, 1080) == True

    def test_coords_at_origin(self):
        coords = {"x": 0, "y": 0}
        assert validate_coordinates(coords, "origin", 1920, 1080) == True

    def test_coords_at_max_bounds(self):
        coords = {"x": 1919, "y": 1079}
        assert validate_coordinates(coords, "max_bounds", 1920, 1080) == True

    def test_x_out_of_bounds(self):
        coords = {"x": 2000, "y": 200}
        assert validate_coordinates(coords, "test_point", 1920, 1080) == False

    def test_y_out_of_bounds(self):
        coords = {"x": 100, "y": 1100}
        assert validate_coordinates(coords, "test_point", 1920, 1080) == False

    def test_negative_x(self):
        coords = {"x": -10, "y": 200}
        assert validate_coordinates(coords, "test_point", 1920, 1080) == False

    def test_negative_y(self):
        coords = {"x": 100, "y": -10}
        assert validate_coordinates(coords, "test_point", 1920, 1080) == False

    def test_missing_x_key(self):
        coords = {"y": 200}
        assert validate_coordinates(coords, "test_point", 1920, 1080) == False

    def test_missing_y_key(self):
        coords = {"x": 100}
        assert validate_coordinates(coords, "test_point", 1920, 1080) == False

    def test_none_coords(self):
        # None is allowed for optional coordinates
        assert validate_coordinates(None, "test_point", 1920, 1080) == True

    def test_empty_dict(self):
        coords = {}
        assert validate_coordinates(coords, "test_point", 1920, 1080) == False


class TestAreaCoordinateValidation:
    """Tests for area coordinate validation (with width/height)"""

    def test_valid_area(self):
        coords = {"x": 100, "y": 200, "width": 500, "height": 300}
        assert validate_area_coords(coords, 1920, 1080) == True

    def test_area_at_origin(self):
        coords = {"x": 0, "y": 0, "width": 500, "height": 300}
        assert validate_area_coords(coords, 1920, 1080) == True

    def test_area_extends_past_screen(self):
        coords = {"x": 1800, "y": 900, "width": 500, "height": 300}
        # x + width = 2300 > 1920, should fail
        assert validate_area_coords(coords, 1920, 1080) == False

    def test_negative_width(self):
        coords = {"x": 100, "y": 200, "width": -500, "height": 300}
        assert validate_area_coords(coords, 1920, 1080) == False

    def test_zero_height(self):
        coords = {"x": 100, "y": 200, "width": 500, "height": 0}
        assert validate_area_coords(coords, 1920, 1080) == False

    def test_missing_width(self):
        coords = {"x": 100, "y": 200, "height": 300}
        assert validate_area_coords(coords, 1920, 1080) == False

    def test_none_area(self):
        # None is NOT allowed for area coords
        assert validate_area_coords(None, 1920, 1080) == False

    def test_negative_coords(self):
        coords = {"x": -10, "y": -20, "width": 500, "height": 300}
        assert validate_area_coords(coords, 1920, 1080) == False
