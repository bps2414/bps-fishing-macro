# Copyright (C) 2026 BPS
# This file is part of BPS Fishing Macro.
#
# V5: Services Module - Webhook Service
# Pure extraction from main file - NO behavior changes

import json
import time
import os
from datetime import datetime
import logging

logger = logging.getLogger("FishingMacro")

# Constants extracted from main
MAX_WEBHOOK_RETRIES = 3
RETRY_DELAY_SECONDS = 1.0
WEBHOOK_TIMEOUT = 30.0


class WebhookService:
    """Discord Webhook Service - handles all webhook notifications"""

    def __init__(
        self,
        webhook_url: str = "",
        user_id: str = "",
        only_legendary: bool = False,
        pity_zone: dict = None,
        ocr_checker=None,
    ):
        """
        Initialize webhook service

        Args:
            webhook_url: Discord webhook URL
            user_id: Discord user ID for mentions
            only_legendary: If True, only send webhooks for legendary/mythical fruits
            pity_zone: Zone coordinates for pity counter OCR
            ocr_checker: Callback function to check legendary pity (signature: ocr_checker(pity_zone) -> bool)
        """
        self.webhook_url = webhook_url
        self.user_id = user_id
        self.only_legendary = only_legendary
        self.pity_zone = pity_zone
        self.ocr_checker = ocr_checker

    def send_fruit_webhook(
        self,
        screenshot_path,
        fish_caught: int,
        fruits_caught: int,
        start_time: float,
        override_is_legendary: bool = None,
    ):
        """
        Send Discord webhook notification with fruit screenshot and statistics

        EXACT COPY from main file - NO behavior changes

        Args:
            screenshot_path: Path to fruit screenshot
            fish_caught: Total fish caught
            fruits_caught: Total fruits caught
            start_time: Macro start time (for runtime calculation)
        """
        cleanup_path = screenshot_path
        try:
            import requests
            from datetime import datetime

            webhook_url = self.webhook_url.strip() if self.webhook_url else ""
            user_id = self.user_id.strip() if self.user_id else ""

            if not webhook_url or not user_id:
                print(
                    f"\rWebhook not configured, skipping notification...",
                    end="",
                    flush=True,
                )
                return

            # Check if legendary/mythical filter is enabled
            is_legendary = False
            if self.only_legendary:
                if override_is_legendary is not None:
                    # Use the override value if provided (avoids duplicate OCR check)
                    is_legendary = override_is_legendary
                    if is_legendary:
                        print(
                            f"\r[Webhook] ✅ LEGENDARY/MYTHICAL FRUIT DETECTED! (Pre-checked)",
                            end="",
                            flush=True,
                        )
                else:
                    print(
                        f"\r[Webhook] Checking if fruit is Legendary/Mythical...",
                        end="",
                        flush=True,
                    )
                    is_legendary = self.check_legendary_pity()

                if not is_legendary:
                    print(
                        f"\r[Webhook] Not a Legendary/Mythical fruit (pity not 0/40) - skipping notification",
                        end="",
                        flush=True,
                    )
                    return
                elif override_is_legendary is None:
                    print(
                        f"\r[Webhook] ✅ LEGENDARY/MYTHICAL FRUIT DETECTED!",
                        end="",
                        flush=True,
                    )
            elif override_is_legendary:
                # Even if filter is OFF, if we know it's legendary (e.g. from auto craft check), mark it
                is_legendary = True

            # Calculate runtime
            if start_time:
                runtime = time.time() - start_time
                hours = int(runtime // 3600)
                minutes = int((runtime % 3600) // 60)
                seconds = int(runtime % 60)
                runtime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                runtime_str = "00:00:00"

            # Create embed message
            if is_legendary:
                embed = {
                    "title": "⭐ LEGENDARY/MYTHICAL FRUIT CAUGHT! ⭐",
                    "description": f"<@{user_id}> **LEGENDARY PITY 0/40 DETECTED!** 🎉\nA Legendary or Mythical devil fruit has been caught!",
                    "color": 0xFFD700,
                    "fields": [
                        {
                            "name": "⭐ Rarity",
                            "value": "**Legendary/Mythical**",
                            "inline": True,
                        },
                        {"name": "⏱️ Runtime", "value": runtime_str, "inline": True},
                        {
                            "name": "🍎 Total Fruits",
                            "value": str(fruits_caught),
                            "inline": True,
                        },
                        {
                            "name": "🐟 Total Fish",
                            "value": str(fish_caught),
                            "inline": True,
                        },
                    ],
                    "timestamp": datetime.utcnow().isoformat(),
                    "footer": {"text": "BPS Fishing Macro - Legendary Filter Active"},
                }
            else:
                embed = {
                    "title": "🍎 DEVIL FRUIT CAUGHT! 🍎",
                    "description": f"<@{user_id}> A devil fruit has been detected!",
                    "color": 0xFF6B35,
                    "fields": [
                        {"name": "⏱️ Runtime", "value": runtime_str, "inline": True},
                        {
                            "name": "🍎 Fruits",
                            "value": str(fruits_caught),
                            "inline": True,
                        },
                        {"name": "🐟 Fish", "value": str(fish_caught), "inline": True},
                    ],
                    "timestamp": datetime.utcnow().isoformat(),
                    "footer": {"text": "BPS Fishing Macro"},
                }

            # Send webhook with retry logic
            retry_count = 0
            while retry_count < MAX_WEBHOOK_RETRIES:
                try:
                    with open(screenshot_path, "rb") as f:
                        files = {"file": ("fruit.png", f, "image/png")}
                        data = {
                            "payload_json": json.dumps(
                                {"content": f"<@{user_id}>", "embeds": [embed]}
                            )
                        }
                        response = requests.post(
                            webhook_url, files=files, data=data, timeout=WEBHOOK_TIMEOUT
                        )

                    if response.status_code in [200, 204]:
                        print(f"\r✅ Webhook notification sent!", end="", flush=True)
                        logger.info(f"Webhook sent successfully")
                        break
                    else:
                        print(
                            f"\r⚠️ Webhook error: {response.status_code}",
                            end="",
                            flush=True,
                        )
                        logger.error(f"Webhook failed: {response.status_code}")
                        if response.status_code >= 500:
                            retry_count += 1
                            if retry_count < MAX_WEBHOOK_RETRIES:
                                time.sleep(RETRY_DELAY_SECONDS)
                                continue
                        break
                except Exception as e:
                    retry_count += 1
                    if retry_count < MAX_WEBHOOK_RETRIES:
                        time.sleep(RETRY_DELAY_SECONDS)
                    else:
                        print(f"\r⚠️ Webhook error", end="", flush=True)
                        logger.error(f"Webhook error: {e}")
                    break
        except Exception as e:
            print(f"\rError sending webhook: {e}", end="", flush=True)
        finally:
            if cleanup_path and os.path.exists(cleanup_path):
                os.remove(cleanup_path)

    def check_legendary_pity(self):
        """
        Check if fruit is legendary/mythical by scanning pity counter

        EXACT COPY from main file - NO behavior changes

        Returns:
            bool: True if legendary/mythical, False otherwise
        """
        if not self.pity_zone:
            logger.warning("Pity zone not configured, assuming legendary fruit")
            return True

        # Use the OCR checker callback if provided
        if self.ocr_checker:
            try:
                return self.ocr_checker(self.pity_zone)
            except Exception as e:
                logger.error(f"Error checking legendary pity: {e}")
                return True

        # If no OCR checker provided, assume legendary
        logger.warning("No OCR checker provided, assuming legendary fruit")
        return True

    def send_test_message(self):
        """
        Send a test webhook message

        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            import requests

            webhook_url = self.webhook_url.strip() if self.webhook_url else ""
            user_id = self.user_id.strip() if self.user_id else ""

            if not webhook_url or not user_id:
                return False, "Please enter Webhook URL and User ID first!"

            # Send test message
            data = {"content": f"<@{user_id}> Test message from BPS Fishing Macro! ✅"}

            response = requests.post(webhook_url, json=data, timeout=10)

            if response.status_code == 204:
                return True, "Test message sent successfully!"
            else:
                return False, f"Webhook error: {response.status_code}"
        except ImportError:
            return False, "requests library not installed! Run: pip install requests"
        except Exception as e:
            return False, f"Error testing webhook: {e}"

    def update_settings(
        self,
        webhook_url: str = None,
        user_id: str = None,
        only_legendary: bool = None,
        pity_zone: dict = None,
    ):
        """Update webhook settings"""
        if webhook_url is not None:
            self.webhook_url = webhook_url
        if user_id is not None:
            self.user_id = user_id
        if only_legendary is not None:
            self.only_legendary = only_legendary
        if pity_zone is not None:
            self.pity_zone = pity_zone
