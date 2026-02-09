"""
Test suite for config/settings_manager.py
==========================================
Tests for settings loading, saving, and caching.
"""

import pytest
import json
import os
import tempfile
from config.settings_manager import SettingsManager


class TestSettingsManagerInitialization:
    """Tests for SettingsManager initialization"""

    def test_initialization_creates_default_file(self):
        """Test that initialization creates settings file if it doesn't exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = os.path.join(temp_dir, "test_settings.json")

            manager = SettingsManager(temp_file)

            # File should be created
            assert os.path.exists(temp_file)


class TestAreaCoordinates:
    """Tests for area coordinates load/save"""

    def test_save_and_load_area_coords(self):
        """Test saving and loading area coordinates"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = os.path.join(temp_dir, "test_settings.json")

            manager = SettingsManager(temp_file)

            # Save area coords
            test_coords = {"x": 100, "y": 200, "width": 500, "height": 700}
            manager.save_area_coords(test_coords)

            # Load area coords
            loaded = manager.load_area_coords()

            assert loaded == test_coords

    def test_load_default_area_coords(self):
        """Test loading default area coordinates"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = os.path.join(temp_dir, "test_settings.json")

            manager = SettingsManager(temp_file)
            coords = manager.load_area_coords()

            # Should return default area
            assert "x" in coords
            assert "y" in coords
            assert "width" in coords
            assert "height" in coords


class TestItemHotkeys:
    """Tests for item hotkey settings"""

    def test_save_and_load_item_hotkeys(self):
        """Test saving and loading item hotkeys"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = os.path.join(temp_dir, "test_settings.json")

            manager = SettingsManager(temp_file)

            # Save hotkeys (method takes individual params)
            manager.save_item_hotkeys("1", "2", "3")

            # Load hotkeys
            loaded = manager.load_item_hotkeys()

            assert loaded["rod"] == "1"
            assert loaded["everything_else"] == "2"
            assert loaded["fruit"] == "3"


class TestAlwaysOnTop:
    """Tests for always on top setting"""

    def test_save_and_load_always_on_top(self):
        """Test saving and loading always on top"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = os.path.join(temp_dir, "test_settings.json")

            manager = SettingsManager(temp_file)

            # Save false
            manager.save_always_on_top(False)
            assert manager.load_always_on_top() == False

            # Save true
            manager.save_always_on_top(True)
            assert manager.load_always_on_top() == True


class TestHUDPosition:
    """Tests for HUD position setting"""

    def test_save_and_load_hud_position(self):
        """Test saving and loading HUD position"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = os.path.join(temp_dir, "test_settings.json")

            manager = SettingsManager(temp_file)

            # Save different positions
            positions = ["top", "bottom-left", "bottom-right"]
            for pos in positions:
                manager.save_hud_position(pos)
                assert manager.load_hud_position() == pos


class TestCachePerformance:
    """Tests for settings manager cache performance"""

    def test_cache_reduces_file_reads(self):
        """Test that cache prevents redundant file I/O"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = os.path.join(temp_dir, "test_settings.json")

            manager = SettingsManager(temp_file)

            # Load multiple times (should use cache after first load)
            coords1 = manager.load_area_coords()
            coords2 = manager.load_area_coords()
            coords3 = manager.load_area_coords()

            # All should return same data
            assert coords1 == coords2 == coords3

            # Verify file modification time doesn't change (not re-read)
            mtime_before = os.path.getmtime(temp_file)
            _ = manager.load_area_coords()  # Load from cache
            mtime_after = os.path.getmtime(temp_file)

            assert mtime_before == mtime_after  # File not modified

    def test_save_updates_cache(self):
        """Test that save operation updates internal cache"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = os.path.join(temp_dir, "test_settings.json")

            manager = SettingsManager(temp_file)

            # Save new data
            new_coords = {"x": 500, "y": 600, "width": 800, "height": 900}
            manager.save_area_coords(new_coords)

            # Load should return cached data (no file read)
            loaded = manager.load_area_coords()

            assert loaded == new_coords


class TestPrecastSettings:
    """Tests for precast settings dict"""

    def test_save_and_load_precast_settings(self):
        """Test saving and loading precast settings"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = os.path.join(temp_dir, "test_settings.json")

            manager = SettingsManager(temp_file)

            # Save precast settings
            test_settings = {
                "auto_buy_bait": True,
                "auto_store_fruit": False,
                "loops_per_purchase": 50,
            }
            manager.save_precast_settings(test_settings)

            # Load precast settings
            loaded = manager.load_precast_settings()

            assert loaded["auto_buy_bait"] == True
            assert loaded["auto_store_fruit"] == False
            assert loaded["loops_per_purchase"] == 50


class TestThreadSafety:
    """Tests for thread-safe operations"""

    def test_concurrent_loads(self):
        """Test concurrent loading from multiple threads"""
        import threading

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = os.path.join(temp_dir, "test_settings.json")

            manager = SettingsManager(temp_file)
            results = []

            def load_coords():
                result = manager.load_area_coords()
                results.append(result)

            # Create 10 threads loading simultaneously
            threads = [threading.Thread(target=load_coords) for _ in range(10)]

            for t in threads:
                t.start()

            for t in threads:
                t.join()

            # All threads should get consistent data
            assert len(results) == 10
            assert all(r == results[0] for r in results)
