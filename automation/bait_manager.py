"""
BaitManager - Smart Bait selection system for V5 fishing macro

Handles intelligent bait selection with OCR counting and color detection:
- OCR Mode: Counts exact bait numbers, auto-switches both directions
- Color-Only Mode: Visual HSV detection, optimized for performance
- Auto-cycle: Burning (use legendary) ↔ Stockpile (save legendary)

Developed by Murtaza. Extracted to module by BPS.
"""

import logging
import time
import os
import numpy as np
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

logger = logging.getLogger(__name__)

# Check dependencies
try:
    import cv2

    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class BaitManager:
    """Manages Smart Bait selection with OCR and color detection"""

    def __init__(self, vision, settings, callbacks):
        """
        Args:
            vision: Vision controller object with screen, ocr, color_detector
            settings: Dictionary with all smart bait settings
            callbacks: Dictionary with callback functions {
                'save_settings': function to save settings,
                'update_ui_hint': function(zone_type, text, color) to update UI labels,
                'update_mode_display': function(text, color) to update mode display,
                'update_decision_display': function(text, color) to update decision display
            }
        """
        self.screen = vision.screen
        self.ocr = vision.ocr
        self.color_detector = vision.color_detector

        # Settings (all from dict)
        self.enabled = settings.get("enabled", False)
        self.mode = settings.get("mode", "burning")  # 'burning' or 'stockpile'
        self.legendary_target = settings.get("legendary_target", 10)
        self.ocr_timeout = settings.get("ocr_timeout_ms", 800)
        self.ocr_confidence = settings.get("ocr_confidence_min", 0.3)
        self.fallback = settings.get("fallback_bait", "legendary")
        self.debug = settings.get("debug_screenshots", False)
        self.use_ocr = settings.get("use_ocr", True)

        # Zone configurations
        self.menu_zone = settings.get("menu_zone", None)
        self.top_zone = settings.get("top_bait_scan_zone", None)
        self.mid_zone = settings.get("mid_bait_scan_zone", None)

        # Debug: Log zone configuration status
        logger.info(f"BaitManager initialized - top_zone: {self.top_zone}")
        logger.info(f"BaitManager initialized - mid_zone: {self.mid_zone}")
        logger.info(f"BaitManager initialized - menu_zone: {self.menu_zone}")

        # Bait coordinates
        self.top_bait_point = settings.get("top_bait_point", None)
        self.smart_bait_2nd_coords = settings.get("smart_bait_2nd_coords", None)

        # Callbacks
        self.save_settings_callback = callbacks.get("save_settings")
        self.update_ui_hint_callback = callbacks.get("update_ui_hint")
        self.update_mode_display_callback = callbacks.get("update_mode_display")
        self.update_decision_display_callback = callbacks.get("update_decision_display")

        # Color cache (2000ms TTL for performance - bait doesn't change that fast)
        self._color_cache_result = None
        self._color_cache_time = 0
        self._color_cache_ttl = 2.0

    def update_coords(self, top_bait_point=None, smart_bait_2nd_coords=None):
        """Update bait coordinates after user changes them in UI

        Args:
            top_bait_point: New top bait coordinates dict {'x': x, 'y': y} or None to keep current
            smart_bait_2nd_coords: New 2nd bait coordinates dict {'x': x, 'y': y} or None to keep current
        """
        if top_bait_point is not None:
            self.top_bait_point = top_bait_point
            logger.info(f"BaitManager: Updated top_bait_point to {top_bait_point}")

        if smart_bait_2nd_coords is not None:
            self.smart_bait_2nd_coords = smart_bait_2nd_coords
            logger.info(
                f"BaitManager: Updated smart_bait_2nd_coords to {smart_bait_2nd_coords}"
            )

    def update_settings(self, settings):
        """Update BaitManager settings after user changes them in UI

        Args:
            settings: Dictionary with updated settings to apply
        """
        if "enabled" in settings:
            self.enabled = settings["enabled"]
        if "mode" in settings:
            self.mode = settings["mode"]
        if "legendary_target" in settings:
            self.legendary_target = settings["legendary_target"]
        if "ocr_timeout_ms" in settings:
            self.ocr_timeout = settings["ocr_timeout_ms"]
        if "ocr_confidence_min" in settings:
            self.ocr_confidence = settings["ocr_confidence_min"]
        if "fallback_bait" in settings:
            self.fallback = settings["fallback_bait"]
        if "debug_screenshots" in settings:
            self.debug = settings["debug_screenshots"]
        if "use_ocr" in settings:
            self.use_ocr = settings["use_ocr"]
        if "menu_zone" in settings:
            self.menu_zone = settings["menu_zone"]
        if "top_bait_scan_zone" in settings:
            self.top_zone = settings["top_bait_scan_zone"]
        if "mid_bait_scan_zone" in settings:
            self.mid_zone = settings["mid_bait_scan_zone"]

        logger.info(f"BaitManager: Settings updated")

    def select_bait(self):
        """Main entry point for Smart Bait selection

        Returns:
            dict {'x': x, 'y': y} of bait coordinates to click,
            or None if Smart Bait is disabled/failed (use default behavior)
        """
        # Gate 1: Feature enabled?
        if not self.enabled:
            logger.debug("[Smart Bait] Disabled, skipping")
            return None

        # Gate 2: Check if OCR mode or Color-Only mode
        if not self.use_ocr:
            logger.debug(f"[Smart Bait] Color-Only mode | Mode: {self.mode}")
            return self._select_bait_color_only()

        # OCR mode: Full OCR detection with decision logic
        logger.debug(f"[Smart Bait] OCR mode | Mode: {self.mode}")
        return self._select_bait_ocr_mode()

    def _select_bait_color_only(self):
        """Color-Only mode: Visual detection without counting

        Logic:
        - Burning: Check top slot color. If Legendary → use it. If RARE → AUTO-SWITCH to stockpile (NEVER go back)
        - Stockpile: Always use rare (2nd slot) until manually switched back
        """
        logger.debug(
            f"[Color-Only] Mode: {self.mode}, 2nd coords: {self.smart_bait_2nd_coords}, top coords: {self.top_bait_point}"
        )

        if self.mode == "burning":
            # Scan top slot to check if legendary is still there
            top_color = self.detect_top_bait_color()

            if top_color == "legendary":
                # Legendary still available - use top slot
                logger.info(
                    "[Color-Only Burning] Legendary detected on top - using TOP slot"
                )
                if self.top_bait_point:
                    return self.top_bait_point
                return self._get_fallback_coords()

            else:
                # NOT legendary (Rare/Common/N/A) - AUTO-SWITCH to STOCKPILE mode
                # This is ONE-WAY: once we switch, NEVER go back until user manually changes
                logger.info(
                    f"[Color-Only] {top_color.upper() if top_color else 'N/A'} detected on top - AUTO-SWITCHING to STOCKPILE mode"
                )
                self.mode = "stockpile"

                # Update UI to reflect mode change
                if self.update_mode_display_callback:
                    self.update_mode_display_callback("STOCKPILE", "#00ddff")

                # Save the mode change
                if self.save_settings_callback:
                    self.save_settings_callback()

                # Use 2nd coords now and forever (until manual switch)
                if self.smart_bait_2nd_coords:
                    return self.smart_bait_2nd_coords

                # Fallback if 2nd coords not configured
                logger.warning(
                    "[Color-Only Stockpile] No 2nd coords configured - using fallback"
                )
                return self._get_fallback_coords()

        elif self.mode == "stockpile":
            # Stockpiling: always use rare (2nd slot) to save legendary
            # IMPORTANT: Even if legendary returns to top slot, keep using 2nd coords
            # User must MANUALLY switch back to burning mode
            # PERFORMANCE: Skip color detection entirely in stockpile (always same choice)

            logger.debug(
                f"[Color-Only Stockpile] Using 2nd coords: {self.smart_bait_2nd_coords}"
            )
            if self.smart_bait_2nd_coords:
                logger.debug(
                    f"[Color-Only Stockpile] → Returning 2nd coords: ({self.smart_bait_2nd_coords['x']}, {self.smart_bait_2nd_coords['y']})"
                )
                return self.smart_bait_2nd_coords

            # Fallback: If no 2nd coords configured, use top as safety
            logger.warning("[Color-Only Stockpile] → No 2nd slot coords configured!")
            if self.top_bait_point:
                logger.warning(
                    f"[Color-Only Stockpile] → Using TOP as fallback: ({self.top_bait_point['x']}, {self.top_bait_point['y']})"
                )
                return self.top_bait_point

            return self._get_fallback_coords()

        return None

    def _select_bait_ocr_mode(self):
        """OCR mode: Full OCR detection with decision logic"""
        # Gate: RapidOCR available?
        ocr_instance = self.ocr.get_instance()
        if not ocr_instance:
            logger.debug("Smart Bait: RapidOCR not available, using fallback")
            return self._get_fallback_coords()

        # Gate: Critical zones configured?
        if not self.menu_zone:
            logger.warning("Smart Bait: Menu zone NOT configured!")
            return None
        if not self.top_zone:
            logger.warning("Smart Bait: Top Label zone NOT configured!")
            return None
        if not self.mid_zone:
            logger.warning("Smart Bait: Mid Label zone NOT configured!")
            return None

        # Execute OCR
        try:
            counts = self.get_counts()
        except Exception as e:
            logger.warning(f"Smart Bait: OCR scan failed: {e}")
            return self._get_fallback_coords()

        # Make decision
        selected_bait = self.decide(counts)

        if selected_bait is None:
            logger.info(f"Smart Bait: Using fallback bait ({self.fallback})")
            return self._get_fallback_coords()

        # Get coordinates for selected bait
        if selected_bait == "legendary":
            coords = self.top_bait_point
            logger.info(
                f"[Smart Bait Select] Decision: legendary → top_bait_point = {coords}"
            )
        elif selected_bait == "rare":
            coords = self.smart_bait_2nd_coords
            logger.info(
                f"[Smart Bait Select] Decision: rare → smart_bait_2nd_coords = {coords}"
            )
        else:
            coords = None
            logger.warning(f"[Smart Bait Select] Unknown bait type: {selected_bait}")

        if coords:
            logger.info(
                f"✅ Smart Bait: Selected {selected_bait} bait at ({coords['x']}, {coords['y']})"
            )
            return coords
        else:
            logger.error(f"❌ Smart Bait: No coords for {selected_bait}!")
            return self._get_fallback_coords()

    def _get_fallback_coords(self):
        """Get fallback bait coordinates"""
        if self.fallback == "legendary" and self.top_bait_point:
            return self.top_bait_point
        elif self.fallback == "rare" and self.smart_bait_2nd_coords:
            return self.smart_bait_2nd_coords
        elif self.top_bait_point:
            return self.top_bait_point
        return None

    def get_counts(self):
        """Get current bait counts from OCR

        Returns: dict with 'legendary', 'rare', 'common' counts (or None if failed)
        """
        counts = {"legendary": None, "rare": None, "common": None}

        if not self.menu_zone:
            return counts

        # Capture full bait menu area
        image = self.screen.capture_area(
            self.menu_zone["x"],
            self.menu_zone["y"],
            self.menu_zone["width"],
            self.menu_zone["height"],
            use_cache=False,
        )
        if image is None:
            logger.debug("Smart Bait: Failed to capture menu zone")
            return counts

        # Convert BGRA to RGB
        if image.shape[2] == 4:
            image = image[:, :, :3]
        image = image[:, :, [2, 1, 0]]  # BGR to RGB

        # Get OCR instance
        ocr_instance = self.ocr.get_instance()
        if not ocr_instance:
            logger.warning("Smart Bait: No OCR instance available")
            return counts

        # Call OCR extraction
        return self._try_ocr_counting(image, ocr_instance)

    def _try_ocr_counting(self, image, ocr_instance):
        """Try OCR counting with preprocessing fallback"""
        counts = {"legendary": None, "rare": None, "common": None}

        # Save debug screenshot if enabled
        if self.debug:
            try:
                from PIL import Image as PILImage

                debug_path = os.path.join(BASE_DIR, "smart_bait_debug_menu.png")
                PILImage.fromarray(image).save(debug_path)
                logger.info(f"Debug screenshot saved: {debug_path}")
            except (OSError, PermissionError, ImportError) as e:
                logger.warning(f"Failed to save debug screenshot: {e}")

        # Strategy 1: Try original image with RETRY LOGIC (up to 3 attempts)
        result = None
        for attempt in range(3):
            try:
                logger.info(f"Smart Bait OCR attempt {attempt + 1}/3")
                with ThreadPoolExecutor() as executor:
                    future = executor.submit(ocr_instance, image)
                    result = future.result(timeout=self.ocr_timeout / 1000.0)

                if result and result[0]:  # Success - text detected
                    logger.info(f"Smart Bait OCR successful on attempt {attempt + 1}")
                    logger.info(f"Smart Bait OCR raw result: boxes={len(result[0])}")
                    break
                else:
                    logger.info(
                        f"Smart Bait OCR attempt {attempt + 1} returned no text"
                    )

                # Small delay between retries
                if attempt < 2:  # Don't delay after last attempt
                    time.sleep(0.1)

            except FuturesTimeoutError:
                logger.warning(
                    f"Smart Bait: OCR timeout on attempt {attempt + 1} ({self.ocr_timeout}ms)"
                )
                if attempt < 2:
                    time.sleep(0.1)
            except Exception as e:
                logger.error(f"Smart Bait: OCR error on attempt {attempt + 1}: {e}")
                if attempt < 2:
                    time.sleep(0.1)

        # Strategy 2: Preprocessed image if all original attempts failed
        if not result or not result[0]:
            logger.info(
                "Smart Bait: All original OCR attempts failed, trying preprocessing..."
            )
            result = self._try_preprocessed_ocr(image, ocr_instance)

        if not result or not result[0]:
            logger.warning(
                "Smart Bait: OCR returned no text (both strategies + retries)"
            )
            return counts

        # Parse OCR result
        return self._parse_ocr_result(result, image, ocr_instance)

    def _try_preprocessed_ocr(self, image, ocr_instance):
        """Try OCR with preprocessing"""
        if not CV2_AVAILABLE:
            logger.debug("Smart Bait: cv2 not available for preprocessing")
            return None

        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            # Increase contrast using CLAHE
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            # Apply adaptive threshold
            thresh = cv2.adaptiveThreshold(
                enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            # Invert for white text on black background
            inverted = cv2.bitwise_not(thresh)

            # Save preprocessed debug if enabled
            if self.debug:
                try:
                    from PIL import Image as PILImage

                    debug_path2 = os.path.join(
                        BASE_DIR, "smart_bait_debug_preprocessed.png"
                    )
                    PILImage.fromarray(inverted).save(debug_path2)
                    logger.info(f"Preprocessed debug saved: {debug_path2}")
                except (OSError, PermissionError, ImportError) as e:
                    logger.warning(f"Failed to save preprocessed debug: {e}")

            # Try OCR on preprocessed image
            with ThreadPoolExecutor() as executor:
                future = executor.submit(ocr_instance, inverted)
                result = future.result(timeout=self.ocr_timeout / 1000.0)

            if result:
                logger.info(
                    f"Smart Bait preprocessed OCR: boxes={len(result[0]) if result[0] else 0}"
                )
                logger.info("Smart Bait: Preprocessed OCR succeeded!")

            return result
        except Exception as e:
            logger.warning(f"Smart Bait: Preprocessing failed: {e}", exc_info=True)
            return None

    def _parse_ocr_result(self, result, image, ocr_instance):
        """Parse OCR result to extract bait counts"""
        counts = {"legendary": None, "rare": None, "common": None}

        # Helper to choose best number from multiple OCR variants
        def _pick_best_number(nums):
            if not nums:
                return None
            try:
                from collections import Counter

                c = Counter(nums)
                # Special handling for 6 vs 9 ambiguity
                if len(c) == 2:
                    vals = list(c.keys())
                    if (
                        (6 in vals and 9 in vals)
                        or (60 in vals and 90 in vals)
                        or (16 in vals and 19 in vals)
                    ):
                        for v in vals:
                            if "9" in str(v):
                                logger.info(f"Smart Bait: Resolved 6vs9 → {v}")
                                return v
                best = sorted(c.items(), key=lambda kv: (-kv[1], -kv[0]))[0][0]
                return best
            except (IndexError, KeyError, ValueError) as e:
                logger.debug(f"Number picking fallback error: {e}")
                return nums[0]

        # Group OCR items by Y position (top to bottom)
        ocr_items = result[0]
        items_with_xy = []
        for itm in ocr_items:
            if len(itm) >= 2:
                box = itm[0]
                text = itm[1]
                y_center = sum(pt[1] for pt in box) / len(box) if box else 0
                x_center = sum(pt[0] for pt in box) / len(box) if box else 0
                y_min = min(pt[1] for pt in box) if box else y_center
                y_max = max(pt[1] for pt in box) if box else y_center
                items_with_xy.append((y_center, x_center, y_min, y_max, text))

        items_with_xy.sort(key=lambda t: t[0])  # Sort top-to-bottom

        # Group into lines by Y proximity
        grouped_lines = []
        line_tol = 10
        for y, x, y_min, y_max, text in items_with_xy:
            if not grouped_lines or abs(y - grouped_lines[-1]["y"]) > line_tol:
                grouped_lines.append(
                    {
                        "y": y,
                        "y_min": y_min,
                        "y_max": y_max,
                        "items": [(x, text)],
                        "boxes": [(y_min, y_max, text)],
                    }
                )
            else:
                g = grouped_lines[-1]
                g["items"].append((x, text))
                g["boxes"].append((y_min, y_max, text))
                g["y"] = ((g["y"] * (len(g["items"]) - 1)) + y) / len(g["items"])
                g["y_min"] = min(g["y_min"], y_min)
                g["y_max"] = max(g["y_max"], y_max)

        # Sort items within each line by X
        for g in grouped_lines:
            g["items"].sort(key=lambda t: t[0])
            g["texts"] = [t[1] for t in g["items"]]

        line_texts = [" ".join(g["texts"]) for g in grouped_lines]
        logger.info(f"Smart Bait line texts (top→bottom): {line_texts}")

        # Color-based validation for top line
        top_hint = None
        try:
            top_hint = self.detect_top_bait_color()
            if top_hint:
                logger.info(f"Smart Bait ColorScan hint (top): {top_hint}")
        except Exception as e:
            logger.debug(f"Smart Bait ColorScan hint failed: {e}")

        # Extract numbers from lines
        import re

        x_number_pattern = r"(?:[xX]\s*(\d+)|(\d+)\s*[xX])"

        def _num_from_match(m):
            return int(m.group(1) or m.group(2))

        def _extract_line_number(g):
            """Extract number from a line group with fallback strategies"""
            candidates = []
            line_text = " ".join(g["texts"])

            # Try x-number pattern first
            m = re.search(x_number_pattern, line_text)
            if m:
                candidates.append(_num_from_match(m))
            for _, _, t in g["boxes"]:
                m2 = re.search(x_number_pattern, t)
                if m2:
                    candidates.append(_num_from_match(m2))

            # Fallback: standalone numbers
            if not candidates:
                standalone_pattern = r"\b(\d{1,4})\b"
                for match in re.finditer(standalone_pattern, line_text):
                    num = int(match.group(1))
                    if 1 <= num <= 9999:
                        candidates.append(num)

            if candidates:
                return _pick_best_number(candidates), candidates

            # Last resort: Band OCR on this line
            try:
                band_pad = 2
                y0 = max(int(g["y_min"]) - band_pad, 0)
                y1 = min(int(g["y_max"]) + band_pad, image.shape[0])
                x0 = int(image.shape[1] * 0.65)  # Rightmost 35%
                x1 = image.shape[1]
                line_crop = image[y0:y1, x0:x1]

                band_variants = [line_crop]
                if CV2_AVAILABLE:
                    gray = cv2.cvtColor(line_crop, cv2.COLOR_RGB2GRAY)
                    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                    enhanced = clahe.apply(gray)
                    thresh1 = cv2.adaptiveThreshold(
                        enhanced,
                        255,
                        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                        cv2.THRESH_BINARY,
                        11,
                        2,
                    )
                    band_variants.append(cv2.bitwise_not(thresh1))
                    _, thresh2 = cv2.threshold(
                        gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
                    )
                    band_variants.append(cv2.bitwise_not(thresh2))
                    upscaled = cv2.resize(
                        gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC
                    )
                    band_variants.append(upscaled)

                band_candidates = []
                for variant in band_variants:
                    try:
                        with ThreadPoolExecutor() as executor:
                            future = executor.submit(ocr_instance, variant)
                            sub_result = future.result(
                                timeout=self.ocr_timeout / 1000.0
                            )
                        if sub_result and sub_result[0]:
                            sub_text = " ".join(
                                [itm[1] for itm in sub_result[0] if len(itm) >= 2]
                            )
                            m2 = re.search(x_number_pattern, sub_text)
                            if m2:
                                band_candidates.append(_num_from_match(m2))
                            for m in re.finditer(r"\b(\d{1,4})\b", sub_text):
                                num = int(m.group(1))
                                if 1 <= num <= 9999:
                                    band_candidates.append(num)
                    except (TimeoutError, Exception) as e:
                        logger.debug(f"Band OCR sub-extraction failed: {e}")

                if band_candidates:
                    logger.debug(f"Smart Bait: Band OCR candidates: {band_candidates}")
                    return _pick_best_number(band_candidates), band_candidates
            except Exception as sub_e:
                logger.debug(f"Smart Bait: line-band OCR failed: {sub_e}")

            return None, []

        def _has_kw(text, kw):
            return kw in text.lower()

        # Filter out header lines
        bait_lines = []
        for g in grouped_lines:
            line_text = " ".join(g["texts"])
            line_lower = line_text.lower()
            has_number = re.search(x_number_pattern, line_text)
            has_keyword = (
                "legendary" in line_lower
                or "rare" in line_lower
                or "common" in line_lower
            )
            if has_number or has_keyword:
                bait_lines.append(g)

        if bait_lines:
            logger.info(f"Smart Bait: Filtered {len(bait_lines)} bait lines")
        else:
            bait_lines = grouped_lines  # Fallback

        # Parse based on number of lines detected
        if len(bait_lines) >= 3:
            # Three lines: standard mapping
            bait_order = ["legendary", "rare", "common"]
            for idx, g in enumerate(bait_lines[:3]):
                if counts[bait_order[idx]] is not None:
                    continue
                val, cand = _extract_line_number(g)
                if val is not None:
                    counts[bait_order[idx]] = val
                    logger.info(f"Smart Bait: {bait_order[idx].capitalize()} = {val}")

        elif len(bait_lines) == 2:
            # Two lines: use keywords + color hint
            top, mid = bait_lines[0], bait_lines[1]
            top_text = " ".join(top["texts"])
            mid_text = " ".join(mid["texts"])
            top_leg = _has_kw(top_text, "legendary")
            top_rare = _has_kw(top_text, "rare")
            top_common = _has_kw(top_text, "common")
            mid_leg = _has_kw(mid_text, "legendary")
            mid_rare = _has_kw(mid_text, "rare")
            mid_common = _has_kw(mid_text, "common")

            # Apply color hint
            if top_hint == "legendary":
                top_leg = True
            elif top_hint == "rare":
                top_rare = True
            elif top_hint == "common":
                top_common = True

            # Get mid color hint if needed
            mid_hint = None
            if top_hint == "legendary" and self.mid_zone:
                try:
                    mid_hint = self.detect_mid_bait_color(self.mid_zone)
                except Exception as e:
                    logger.debug(f"Mid color scan failed: {e}")

            # Parse based on keywords
            if top_leg:
                if counts["legendary"] is None:
                    val, cand = _extract_line_number(top)
                    if val is not None:
                        counts["legendary"] = val
                        logger.info(f"Smart Bait: Legendary = {val} (2-line, top)")

                # Mid line is rare or common
                if mid_hint == "rare" or mid_rare:
                    if counts["rare"] is None:
                        val, cand = _extract_line_number(mid)
                        if val is not None:
                            counts["rare"] = val
                            logger.info(f"Smart Bait: Rare = {val} (2-line, mid)")
                elif mid_hint == "common" or mid_common:
                    if counts["common"] is None:
                        val, cand = _extract_line_number(mid)
                        if val is not None:
                            counts["common"] = val
                            logger.info(f"Smart Bait: Common = {val} (2-line, mid)")

            elif top_rare:
                if counts["rare"] is None:
                    val, cand = _extract_line_number(top)
                    if val is not None:
                        counts["rare"] = val
                        logger.info(f"Smart Bait: Rare = {val} (2-line, top)")
                if counts["common"] is None:
                    val, cand = _extract_line_number(mid)
                    if val is not None:
                        counts["common"] = val
                        logger.info(f"Smart Bait: Common = {val} (2-line, mid)")

        return counts

    def detect_top_bait_color(self, force_scan=False):
        """Detect which bait is on top using color analysis (no OCR)

        Args:
            force_scan: If True, bypass cache and always do fresh scan

        Returns: 'legendary', 'rare', 'common', or None
        """
        if not self.top_zone:
            logger.warning("Smart Bait TOP: top_zone not configured!")
            return None

        # Get current time for cache check and update
        now = time.time()

        # Performance: Use cached result if recent (2000ms), unless force_scan=True
        if not force_scan:
            if (
                self._color_cache_result is not None
                and (now - self._color_cache_time) < self._color_cache_ttl
            ):
                logger.debug(
                    f"Smart Bait TOP: Using cached result: {self._color_cache_result}"
                )
                return self._color_cache_result

        logger.debug(f"Smart Bait TOP: Capturing zone {self.top_zone}")
        image = self.screen.capture_area(
            self.top_zone["x"],
            self.top_zone["y"],
            self.top_zone["width"],
            self.top_zone["height"],
            use_cache=False,
        )
        if image is None:
            logger.warning(
                "Smart Bait TOP: First capture failed, retrying with delay..."
            )
            import time as time_retry

            time_retry.sleep(0.25)  # 250ms delay for UI/animation to settle
            image = self.screen.capture_area(
                self.top_zone["x"],
                self.top_zone["y"],
                self.top_zone["width"],
                self.top_zone["height"],
                use_cache=False,
            )
            if image is None:
                logger.warning(
                    "Smart Bait TOP: Second capture failed, third attempt..."
                )
                time_retry.sleep(0.25)  # Another 250ms delay
                image = self.screen.capture_area(
                    self.top_zone["x"],
                    self.top_zone["y"],
                    self.top_zone["width"],
                    self.top_zone["height"],
                    use_cache=False,
                )
                if image is None:
                    logger.warning("Smart Bait TOP: All retries failed - image is None")
                    return None

        # Convert BGRA->RGB
        if image.shape[2] == 4:
            image = image[:, :, :3]
        image = image[:, :, [2, 1, 0]]

        # DEBUG: Save screenshot ONLY if debug mode enabled
        if self.debug:
            import time as time_module

            debug_path = f"debug_top_{int(time_module.time()*1000)}.png"
            cv2.imwrite(debug_path, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
            logger.info(f"[DEBUG] Saved TOP capture to: {debug_path}")

        if not CV2_AVAILABLE:
            logger.debug("Smart Bait: cv2 not available for color scan")
            return None

        # ============================================================
        # DETECTION METHOD SWITCH - Easy to replace/remove
        # ============================================================
        # OPTIONS:
        # 1. _detect_multipoint(image)  - Multi-point gradient sampling (NEW)
        # 2. _detect_hsv_threshold(image) - Original HSV threshold method
        # ============================================================
        # bait_type = self._detect_multipoint(image)
        bait_type = self._detect_hsv_threshold(
            image, "TOP"
        )  # Using HSV (more reliable)

        # Update cache with fresh result
        self._color_cache_result = bait_type
        self._color_cache_time = now
        return bait_type

    def _detect_multipoint(self, image):
        """
        Multi-point vertical sampling detection method.
        Analyzes gradient patterns to differentiate bait types.

        Returns: 'legendary', 'rare', 'common', or None
        """
        h, w = image.shape[:2]

        # DEBUG: Save screenshot for analysis (uncomment to enable)
        # import cv2, time
        # cv2.imwrite(f"debug_top_{int(time.time())}.png", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))

        # Sample 3 vertical regions (avoid edges)
        top_region = image[int(h * 0.20) : int(h * 0.35), :]
        mid_region = image[int(h * 0.45) : int(h * 0.55), :]
        bot_region = image[int(h * 0.65) : int(h * 0.80), :]

        # Get average HSV for each region
        def get_region_stats(region):
            hsv = cv2.cvtColor(region, cv2.COLOR_RGB2HSV).astype(np.float32)
            hue = np.mean(hsv[:, :, 0])
            sat = np.mean(hsv[:, :, 1]) / 255.0
            val = np.mean(hsv[:, :, 2]) / 255.0
            return hue, sat, val

        top_h, top_s, top_v = get_region_stats(top_region)
        mid_h, mid_s, mid_v = get_region_stats(mid_region)
        bot_h, bot_s, bot_v = get_region_stats(bot_region)

        logger.info(
            f"[MultiPoint-TOP] Top(H={top_h:.1f}° S={top_s:.2f}) Mid(H={mid_h:.1f}° S={mid_s:.2f}) Bot(H={bot_h:.1f}° S={bot_s:.2f})"
        )

        # Calculate gradient intensity (hue difference top-to-bottom)
        # Handle circular hue (0-180 wraps)
        hue_diff = abs(top_h - bot_h)
        if hue_diff > 90:  # wrap-around
            hue_diff = 180 - hue_diff

        avg_sat = (top_s + mid_s + bot_s) / 3

        logger.info(f"  → Gradient: {hue_diff:.1f}°, AvgSat: {avg_sat:.2f}")

        # ======================================
        # CLASSIFICATION LOGIC
        # ======================================

        # 0. Empty/Dark slot: Extremely low saturation (<0.15) = treat as empty or Common
        if avg_sat < 0.15:
            logger.info(f"  → COMMON (extremely low sat {avg_sat:.2f} - empty or dark)")
            return "common"

        # 1. Common: Low saturation, uniform (white/gray)
        if avg_sat < 0.35 and hue_diff < 15:
            logger.info(f"  → COMMON (low sat + no gradient)")
            return "common"

        # 2. Rare: BLUE color check (PRIORITY - before gradient check)
        # If dominant hue is blue (85-155°), it's Rare regardless of gradient/saturation
        blues = [85 <= h <= 155 for h in [top_h, mid_h, bot_h]]
        if sum(blues) >= 2:  # At least 2/3 samples are blue
            logger.info(f"  → RARE (blue detected in {sum(blues)}/3 samples)")
            return "rare"

        # 3. Legendary: High variance gradient (rainbow)
        if hue_diff > 25:  # Significant gradient
            logger.info(f"  → LEGENDARY (rainbow gradient {hue_diff:.1f}°)")
            return "legendary"

        # 4. Legendary: High saturation uniform (gold) - only non-blue
        if avg_sat >= 0.50:
            logger.info(f"  → LEGENDARY (vibrant uniform, sat={avg_sat:.2f})")
            return "legendary"

        # 5. Fallback: Weak signal = Common
        logger.info(f"  → COMMON (fallback - weak signal)")
        return "common"

    def _detect_hsv_threshold(self, image, zone_name="UNKNOWN"):
        """
        Original HSV threshold detection method (backup/fallback).

        Args:
            image: RGB image array to analyze
            zone_name: Name of the zone being scanned (for logging)

        Returns: 'legendary', 'rare', 'common', or None
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV).astype(np.float32)
        hues = hsv[:, :, 0].flatten()
        sats = hsv[:, :, 1].flatten() / 255.0
        vals = hsv[:, :, 2].flatten() / 255.0

        # Ignore dark/low-sat background
        mask = (sats > 0.2) & (vals > 0.2)
        if np.count_nonzero(mask) > 0:
            hues_m = hues[mask]
            sats_m = sats[mask]
        else:
            hues_m = hues
            sats_m = sats

        # Circular hue variance
        angles = hues_m / 180.0 * 2 * np.pi
        mean_x = np.mean(np.cos(angles))
        mean_y = np.mean(np.sin(angles))
        r = np.sqrt(mean_x**2 + mean_y**2)
        hue_var = 1 - r

        sat_mean = float(np.mean(sats_m))

        # Dominant hue
        hist, bins = np.histogram(hues_m, bins=36, range=(0, 180))
        dom_idx = int(np.argmax(hist))
        dom_hue = (bins[dom_idx] + bins[dom_idx + 1]) / 2.0

        logger.debug(
            f"ColorScan ({zone_name}): hue_var={hue_var:.3f}, sat_mean={sat_mean:.3f}, dom_hue={dom_hue:.1f}°"
        )

        # Heuristic classification (color.txt reference)
        # CRITICAL ORDER: Check LEGENDARY FIRST (high variance rainbow), then specific colors
        bait_type = None

        # Priority 1: Legendary (rainbow - VERY high variance)
        # Check this FIRST to avoid false RARE detection (Legendary can have blue in the gradient)
        if hue_var >= 0.75:
            bait_type = "legendary"
            logger.info(
                f"  → LEGENDARY (hue_var {hue_var:.3f} >= 0.75 - rainbow/gradient)"
            )

        # Priority 2: Legendary (vibrant colors with high saturation, moderate variance)
        # Gold/Orange legendary with gradient
        elif sat_mean > 0.70 and hue_var >= 0.35:
            bait_type = "legendary"
            logger.info(
                f"  → LEGENDARY (sat_mean {sat_mean:.3f} > 0.70 AND hue_var {hue_var:.3f} >= 0.35)"
            )

        # Priority 3: Common - VERY LOW variance (solid color with border)
        # Check before RARE to avoid false positive on gray/white
        elif hue_var < 0.15:
            bait_type = "common"
            logger.info(f"  → COMMON (hue_var {hue_var:.3f} < 0.15 - solid color)")

        # Priority 4: Common (low variance, low saturation - solid white/gray)
        elif hue_var < 0.30 and sat_mean < 0.40:
            bait_type = "common"
            logger.info(
                f"  → COMMON (hue_var {hue_var:.3f} < 0.30 AND sat_mean {sat_mean:.3f} < 0.40)"
            )

        # Priority 5: Rare (blue dominant with moderate saturation)
        # Check LAST among colored baits to avoid false positive on Legendary gradient
        # Only accept if NOT high variance (to exclude Legendary rainbow)
        elif 85 <= dom_hue <= 155 and sat_mean >= 0.25 and hue_var < 0.70:
            bait_type = "rare"
            logger.info(
                f"  → RARE (dom_hue {dom_hue:.1f}° blue, sat_mean {sat_mean:.3f}, hue_var {hue_var:.3f})"
            )

        # Fallback: Unknown
        else:
            logger.warning(f"  → UNKNOWN (no rule matched) - defaulting to None")
            bait_type = None

        return bait_type

    def detect_mid_bait_color(self, mid_zone):
        """Detect mid bait color using same heuristics as top

        Args:
            mid_zone: dict with x, y, width, height

        Returns: 'legendary', 'rare', 'common', or None
        """
        if not mid_zone:
            logger.debug("Smart Bait mid: mid_zone not provided")
            return None

        image = self.screen.capture_area(
            mid_zone["x"],
            mid_zone["y"],
            mid_zone["width"],
            mid_zone["height"],
            use_cache=False,
        )
        if image is None:
            logger.debug("Smart Bait mid: failed to capture zone")
            return None

        if image.shape[2] == 4:
            image = image[:, :, :3]
        image = image[:, :, [2, 1, 0]]

        # DEBUG: Save screenshot to verify capture area (only when debug mode enabled)
        if self.debug:
            import time as time_module

            debug_path = f"debug_mid_{int(time_module.time()*1000)}.png"
            cv2.imwrite(debug_path, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
            logger.info(f"[DEBUG] Saved MID capture to: {debug_path}")

        if not CV2_AVAILABLE:
            logger.debug("Smart Bait mid: cv2 not available")
            return None

        # ============================================================
        # Use HSV threshold method (more reliable than multi-point)
        # ============================================================
        bait_type = self._detect_hsv_threshold_mid(image)

        logger.info(f"Smart Bait ColorScan (mid) result: {bait_type}")

        # Update UI mid label
        if self.update_ui_hint_callback:
            txt = bait_type if bait_type else "n/a"
            color = {
                "legendary": "#ff66ff",
                "rare": "#55ccff",
                "common": "#dddddd",
            }.get(bait_type, "#aaaaaa")
            self.update_ui_hint_callback("mid", txt, color)

        return bait_type

    def _detect_multipoint_mid(self, image):
        """Multi-point detection for MID slot (with separate logging)"""
        h, w = image.shape[:2]

        # Sample 3 vertical regions
        top_region = image[int(h * 0.20) : int(h * 0.35), :]
        mid_region = image[int(h * 0.45) : int(h * 0.55), :]
        bot_region = image[int(h * 0.65) : int(h * 0.80), :]

        def get_region_stats(region):
            hsv = cv2.cvtColor(region, cv2.COLOR_RGB2HSV).astype(np.float32)
            hue = np.mean(hsv[:, :, 0])
            sat = np.mean(hsv[:, :, 1]) / 255.0
            val = np.mean(hsv[:, :, 2]) / 255.0
            return hue, sat, val

        top_h, top_s, top_v = get_region_stats(top_region)
        mid_h, mid_s, mid_v = get_region_stats(mid_region)
        bot_h, bot_s, bot_v = get_region_stats(bot_region)

        logger.info(
            f"[MultiPoint-MID] Top(H={top_h:.1f}° S={top_s:.2f}) Mid(H={mid_h:.1f}° S={mid_s:.2f}) Bot(H={bot_h:.1f}° S={bot_s:.2f})"
        )

        # Calculate gradient
        hue_diff = abs(top_h - bot_h)
        if hue_diff > 90:
            hue_diff = 180 - hue_diff

        avg_sat = (top_s + mid_s + bot_s) / 3
        logger.info(f"  → Gradient: {hue_diff:.1f}°, AvgSat: {avg_sat:.2f}")

        # Same classification as top
        if avg_sat < 0.15:
            logger.info(f"  → COMMON (extremely low sat {avg_sat:.2f} - empty or dark)")
            return "common"

        if avg_sat < 0.35 and hue_diff < 15:
            logger.info(f"  → COMMON (low sat + no gradient)")
            return "common"

        blues = [85 <= h <= 155 for h in [top_h, mid_h, bot_h]]
        if sum(blues) >= 2:
            logger.info(f"  → RARE (blue detected in {sum(blues)}/3 samples)")
            return "rare"

        if hue_diff > 25:
            logger.info(f"  → LEGENDARY (rainbow gradient {hue_diff:.1f}°)")
            return "legendary"

        if avg_sat >= 0.50:
            logger.info(f"  → LEGENDARY (vibrant uniform, sat={avg_sat:.2f})")
            return "legendary"

        logger.info(f"  → COMMON (fallback - weak signal)")
        return "common"

    def _detect_hsv_threshold_mid(self, image):
        """Old HSV threshold method for mid slot (backup)"""
        hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV).astype(np.float32)
        hues = hsv[:, :, 0].flatten()
        sats = hsv[:, :, 1].flatten() / 255.0
        vals = hsv[:, :, 2].flatten() / 255.0

        mask = (sats > 0.2) & (vals > 0.2)
        if np.count_nonzero(mask) > 0:
            hues_m = hues[mask]
            sats_m = sats[mask]
        else:
            hues_m = hues
            sats_m = sats

        angles = hues_m / 180.0 * 2 * np.pi
        mean_x = np.mean(np.cos(angles))
        mean_y = np.mean(np.sin(angles))
        r = np.sqrt(mean_x**2 + mean_y**2)
        hue_var = 1 - r

        sat_mean = float(np.mean(sats_m))  # Calculate sat_mean

        hist, bins = np.histogram(hues_m, bins=36, range=(0, 180))
        dom_idx = int(np.argmax(hist))
        dom_hue = (bins[dom_idx] + bins[dom_idx + 1]) / 2.0

        logger.info(
            f"ColorScan (MID): hue_var={hue_var:.3f}, sat_mean={sat_mean:.3f}, dom_hue={dom_hue:.1f}°"
        )

        bait_type = None

        # Priority 1: Rare (blue dominant) - CHECK FIRST to avoid false Common/Legendary detection
        # Blue with high saturation = Rare (even with high variance)
        if 85 <= dom_hue <= 155 and sat_mean >= 0.25:
            bait_type = "rare"
            logger.info(
                f"  → RARE (dom_hue {dom_hue:.1f}° blue, sat_mean {sat_mean:.3f})"
            )

        # Priority 2A: Common - VERY LOW variance (solid color with border)
        # BUT only if NOT blue (to avoid Rare false positive)
        elif hue_var < 0.15 and not (85 <= dom_hue <= 155):
            bait_type = "common"
            logger.info(
                f"  → COMMON (hue_var {hue_var:.3f} < 0.15 - solid non-blue color)"
            )

        # Priority 2B: Common (low variance - solid white/gray)
        elif hue_var < 0.30 and sat_mean < 0.40:
            bait_type = "common"
            logger.info(
                f"  → COMMON (hue_var {hue_var:.3f} < 0.30 AND sat_mean {sat_mean:.3f} < 0.40)"
            )

        # Priority 3: Legendary (rainbow - VERY high variance)
        # Increased threshold to 0.85 to avoid Rare false positive
        elif hue_var >= 0.85:
            bait_type = "legendary"
            logger.info(f"  → LEGENDARY (hue_var {hue_var:.3f} >= 0.85 - rainbow)")

        # Priority 4: Legendary fallback (vibrant non-blue colors ONLY)
        elif sat_mean > 0.70 and not (85 <= dom_hue <= 155):
            bait_type = "legendary"
            logger.info(
                f"  → LEGENDARY (sat_mean {sat_mean:.3f} > 0.70 - vibrant non-blue)"
            )

        # Fallback
        else:
            logger.warning(f"  → UNKNOWN (no rule matched) - defaulting to None")
            bait_type = None

        return bait_type

    def decide(self, counts):
        """Decide which bait to use based on mode and counts

        Auto-switches between modes:
        - Burning: Use legendary until 1 left → switch to Stockpile
        - Stockpile: Use rare until target reached → switch to Burning

        Args:
            counts: dict with 'legendary' and 'rare' counts

        Returns:
            'legendary', 'rare', or None (use fallback)
        """
        legendary = counts.get("legendary")
        rare = counts.get("rare")

        logger.info(
            f"[Smart Bait Decision] Mode: {self.mode}, Legendary: {legendary}, Rare: {rare}, Target: {self.legendary_target}"
        )

        # Auto-switch logic
        if legendary is not None:
            if self.mode == "burning" and legendary <= 1:
                # Switch to stockpile
                self.mode = "stockpile"
                if self.update_mode_display_callback:
                    self.update_mode_display_callback("STOCKPILE", "#00ddff")
                if self.save_settings_callback:
                    self.save_settings_callback()
                logger.warning(
                    f"🔄 AUTO-SWITCH: Burning → Stockpile (legendary: {legendary}/1)"
                )
            elif self.mode == "stockpile" and legendary >= self.legendary_target:
                # Switch to burning
                self.mode = "burning"
                if self.update_mode_display_callback:
                    self.update_mode_display_callback("BURNING", "#ff8800")
                if self.save_settings_callback:
                    self.save_settings_callback()
                logger.warning(
                    f"🔄 AUTO-SWITCH: Stockpile → Burning (legendary: {legendary}/{self.legendary_target})"
                )

        # Make decision
        decision_text = ""

        if self.mode == "burning":
            # Use legendary until only 1 left
            if legendary is not None and legendary > 1:
                logger.info(f"[Burning] → Using legendary ({legendary} available)")
                decision_text = f"🔥 Use legendary ({legendary} → burning until 1)"
                if self.update_decision_display_callback:
                    self.update_decision_display_callback(decision_text, "#ffaa00")
                return "legendary"
            elif legendary == 1:
                logger.info("[Burning] → Last legendary, switching to stockpile")
                decision_text = "⚠️ Last legendary (switching to stockpile)"
                if self.update_decision_display_callback:
                    self.update_decision_display_callback(decision_text, "#ff8800")
                if rare is not None and rare > 0:
                    return "rare"
                return None
            elif legendary == 0 or legendary is None:
                if rare is not None and rare > 0:
                    logger.info("[Burning] → Using rare (no legendary)")
                    decision_text = f"Use rare ({rare} available, no legendary)"
                    if self.update_decision_display_callback:
                        self.update_decision_display_callback(decision_text, "#00aaff")
                    return "rare"
                logger.info("[Burning] → Fallback (no baits)")
                decision_text = "Fallback (no baits)"
                if self.update_decision_display_callback:
                    self.update_decision_display_callback(decision_text, "#888888")
                return None

        elif self.mode == "stockpile":
            # Use rare to accumulate legendary
            if legendary is None:
                logger.info("[Stockpile] → Fallback (legendary count unknown)")
                decision_text = "Fallback (can't read legendary)"
                if self.update_decision_display_callback:
                    self.update_decision_display_callback(decision_text, "#ff4444")
                return None

            if legendary >= self.legendary_target:
                logger.info(f"[Stockpile] → Target reached, switching to burning")
                decision_text = (
                    f"✓ Target reached ({legendary}/{self.legendary_target}) → burning"
                )
                if self.update_decision_display_callback:
                    self.update_decision_display_callback(decision_text, "#00ff00")
                if legendary > 1:
                    return "legendary"
                return None

            if rare is not None and rare > 0:
                logger.info(
                    f"[Stockpile] → Using rare (accumulating: {legendary}/{self.legendary_target})"
                )
                decision_text = (
                    f"💎 Use rare (accumulating {legendary}/{self.legendary_target})"
                )
                if self.update_decision_display_callback:
                    self.update_decision_display_callback(decision_text, "#00aaff")
                return "rare"

            if legendary > 0:
                logger.warning(
                    f"[Stockpile] → Forced legendary (no rare: {legendary}/{self.legendary_target})"
                )
                decision_text = (
                    f"⚠️ Forced legendary (no rare, {legendary}/{self.legendary_target})"
                )
                if self.update_decision_display_callback:
                    self.update_decision_display_callback(decision_text, "#ff8800")
                return "legendary"

            logger.info("[Stockpile] → Fallback (no baits)")
            decision_text = "Fallback (no baits, craft needed)"
            if self.update_decision_display_callback:
                self.update_decision_display_callback(decision_text, "#888888")
            return None

        # Unknown mode
        logger.warning(f"Smart Bait: Unknown mode '{self.mode}'")
        decision_text = f"Unknown mode: {self.mode}"
        if self.update_decision_display_callback:
            self.update_decision_display_callback(decision_text, "#ff4444")
        return None

    def update_settings(self, settings):
        """Update settings (called when user changes settings in UI)"""
        self.enabled = settings.get("enabled", self.enabled)
        self.mode = settings.get("mode", self.mode)
        self.legendary_target = settings.get("legendary_target", self.legendary_target)
        self.ocr_timeout = settings.get("ocr_timeout_ms", self.ocr_timeout)
        self.ocr_confidence = settings.get("ocr_confidence_min", self.ocr_confidence)
        self.fallback = settings.get("fallback_bait", self.fallback)
        self.debug = settings.get("debug_screenshots", self.debug)
        self.use_ocr = settings.get("use_ocr", self.use_ocr)
        self.menu_zone = settings.get("menu_zone", self.menu_zone)
        self.top_zone = settings.get("top_bait_scan_zone", self.top_zone)
        self.mid_zone = settings.get("mid_bait_scan_zone", self.mid_zone)
        self.top_bait_point = settings.get("top_bait_point", self.top_bait_point)
        self.smart_bait_2nd_coords = settings.get(
            "smart_bait_2nd_coords", self.smart_bait_2nd_coords
        )
