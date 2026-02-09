"""
CraftAutomation - Crafting sequence automation for V5 fishing macro

Handles automated bait crafting sequences:
- Fixed order: Common → Rare → Legendary bait
- Click sequences: Bait Icon → Plus → Fish → Craft (quantity times)
- Overflow protection (280 bait limit)

Extracted to module by BPS.
"""

import logging
import time

logger = logging.getLogger(__name__)


class CraftAutomation:
    """Manages automated bait crafting sequences"""
    
    def __init__(self, input_ctrl, settings, callbacks):
        """
        Args:
            input_ctrl: Input controller object with mouse and keyboard
            settings: Dictionary with all craft settings
            callbacks: Dictionary with callback functions {
                'interruptible_sleep': function(duration) -> bool,
                'is_running': function() -> bool
            }
        """
        self.mouse = input_ctrl.mouse
        self.keyboard = input_ctrl.keyboard
        
        # Settings - craft quantities
        self.craft_common_quantity = settings.get('craft_common_quantity', 0)
        self.craft_rare_quantity = settings.get('craft_rare_quantity', 0)
        self.craft_legendary_quantity = settings.get('craft_legendary_quantity', 0)
        
        # Settings - coordinates
        self.common_bait_coords = settings.get('common_bait_coords', None)
        self.rare_bait_coords = settings.get('rare_bait_coords', None)
        self.legendary_bait_coords = settings.get('legendary_bait_coords', None)
        self.plus_button_coords = settings.get('plus_button_coords', None)
        self.fish_icon_coords = settings.get('fish_icon_coords', None)
        self.craft_button_coords = settings.get('craft_button_coords', None)
        
        # Settings - hotkeys and delays
        self.rod_hotkey = settings.get('rod_hotkey', '1')
        self.craft_menu_delay = settings.get('craft_menu_delay', 0.5)  # seconds
        self.craft_click_speed = settings.get('craft_click_speed', 0.1)  # seconds
        
        # Callbacks
        self.interruptible_sleep = callbacks.get('interruptible_sleep')
        self.is_running = callbacks.get('is_running')
    
    def update_coords(self, common_bait_coords=None, rare_bait_coords=None, legendary_bait_coords=None,
                     plus_button_coords=None, fish_icon_coords=None, craft_button_coords=None):
        """Update craft coordinates after user changes them in UI
        
        Args:
            common_bait_coords: New common bait coordinates or None to keep current
            rare_bait_coords: New rare bait coordinates or None to keep current
            legendary_bait_coords: New legendary bait coordinates or None to keep current
            plus_button_coords: New plus button coordinates or None to keep current
            fish_icon_coords: New fish icon coordinates or None to keep current
            craft_button_coords: New craft button coordinates or None to keep current
        """
        if common_bait_coords is not None:
            self.common_bait_coords = common_bait_coords
            logger.info(f"CraftAutomation: Updated common_bait_coords to {common_bait_coords}")
        
        if rare_bait_coords is not None:
            self.rare_bait_coords = rare_bait_coords
            logger.info(f"CraftAutomation: Updated rare_bait_coords to {rare_bait_coords}")
        
        if legendary_bait_coords is not None:
            self.legendary_bait_coords = legendary_bait_coords
            logger.info(f"CraftAutomation: Updated legendary_bait_coords to {legendary_bait_coords}")
        
        if plus_button_coords is not None:
            self.plus_button_coords = plus_button_coords
            logger.info(f"CraftAutomation: Updated plus_button_coords to {plus_button_coords}")
        
        if fish_icon_coords is not None:
            self.fish_icon_coords = fish_icon_coords
            logger.info(f"CraftAutomation: Updated fish_icon_coords to {fish_icon_coords}")
        
        if craft_button_coords is not None:
            self.craft_button_coords = craft_button_coords
            logger.info(f"CraftAutomation: Updated craft_button_coords to {craft_button_coords}")
    
    def run_craft_sequence(self):
        """Execute the complete crafting sequence for Auto Craft mode
        
        Crafting sequence (for each bait type with quantity > 0):
        1. Click Bait Icon - ONCE per bait type
        2. Click Plus Button - ONCE per bait type
        3. Click Fish Icon - ONCE per bait type
        4. Click Craft Button - QUANTITY times (5 clicks = 5 baits)
        
        Craft Order: FIXED - Common → Rare → Legendary (always in this order)
        
        Returns:
            True if successful, False if interrupted
        """
        try:
            print(f"\r[Auto Craft] ⚒️ Starting crafting sequence...", end='', flush=True)
            
            # DEBUG: Print all loaded coordinates
            print(f"\n[DEBUG] Common coords: {self.common_bait_coords}")
            print(f"[DEBUG] Rare coords: {self.rare_bait_coords}")
            print(f"[DEBUG] Legendary coords: {self.legendary_bait_coords}")
            print(f"[DEBUG] Plus button: {self.plus_button_coords}")
            print(f"[DEBUG] Fish icon: {self.fish_icon_coords}")
            print(f"[DEBUG] Craft button: {self.craft_button_coords}")
            print(f"[DEBUG] Quantities - Common: {self.craft_common_quantity}, Rare: {self.craft_rare_quantity}, Leg: {self.craft_legendary_quantity}\n")
            
            # Step 0: Deselect rod (press rod hotkey)
            print(f"\r[Auto Craft] Deselecting rod ({self.rod_hotkey})...", end='', flush=True)
            self.keyboard.press(self.rod_hotkey)
            self.keyboard.release(self.rod_hotkey)
            if not self.interruptible_sleep(0.3):
                return False
            
            # Wait for menu to open
            menu_delay = self.craft_menu_delay
            print(f"\r[Auto Craft] Waiting {menu_delay:.2f}s for menu to open...", end='', flush=True)
            if not self.interruptible_sleep(menu_delay):
                return False
            
            # Convert click speed to seconds
            click_delay = self.craft_click_speed
            
            # OCR removed from V2.7 - always 0
            ocr_leg = 0
            ocr_rare = 0
            ocr_common = 0
            
            # Define bait types to craft in FIXED order: Common → Rare → Legendary
            baits_to_craft = [
                ('Common', self.common_bait_coords, self.craft_common_quantity, ocr_common),
                ('Rare', self.rare_bait_coords, self.craft_rare_quantity, ocr_rare),
                ('Legendary', self.legendary_bait_coords, self.craft_legendary_quantity, ocr_leg)
            ]
            
            for bait_name, bait_coords, quantity, current_count in baits_to_craft:
                # Check if interrupted
                if not self.is_running():
                    break
                
                # Skip if quantity is 0
                if quantity <= 0:
                    continue
                
                # Skip if coordinates not set
                if not bait_coords:
                    print(f"\r[Auto Craft] ⚠️ {bait_name} bait coords not set, skipping...", end='', flush=True)
                    continue
                
                # Overflow protection: skip if already at 280+ baits
                if current_count >= 280:
                    print(f"\r[Auto Craft] ⚠️ {bait_name} at {current_count}/280 baits. Skipping to prevent overflow...", end='', flush=True)
                    continue
                
                print(f"\r[Auto Craft] Crafting {quantity}x {bait_name} bait (current: {current_count}/280)...", end='', flush=True)
                print(f"\n[DEBUG] Starting {bait_name} craft with coords: {bait_coords}")
                
                # Validate all required coords before starting
                if not self.plus_button_coords:
                    print(f"\r[Auto Craft] ⚠️ Plus button coords not set! Skipping {bait_name}...", end='', flush=True)
                    continue
                if not self.fish_icon_coords:
                    print(f"\r[Auto Craft] ⚠️ Fish icon coords not set! Skipping {bait_name}...", end='', flush=True)
                    continue
                if not self.craft_button_coords:
                    print(f"\r[Auto Craft] ⚠️ Craft button coords not set! Skipping {bait_name}...", end='', flush=True)
                    continue
                
                # Step 1: Click Bait Icon (ONCE - for the entire quantity)
                print(f"\r[AC] {bait_name}: Clicking bait icon at ({bait_coords['x']}, {bait_coords['y']})...", end='', flush=True)
                self.mouse.click(bait_coords['x'], bait_coords['y'], hold_delay=0.1)
                if not self.interruptible_sleep(click_delay):
                    return False
                
                # Step 2: Click Plus Button (ONCE - to add fish)
                print(f"\r[AC] {bait_name}: Clicking plus button at ({self.plus_button_coords['x']}, {self.plus_button_coords['y']})...", end='', flush=True)
                self.mouse.click(self.plus_button_coords['x'], self.plus_button_coords['y'], hold_delay=0.1)
                if not self.interruptible_sleep(click_delay):
                    return False
                
                # Step 3: Click Fish Icon (ONCE - to confirm fish selection)
                print(f"\r[AC] {bait_name}: Clicking fish icon at ({self.fish_icon_coords['x']}, {self.fish_icon_coords['y']})...", end='', flush=True)
                self.mouse.click(self.fish_icon_coords['x'], self.fish_icon_coords['y'], hold_delay=0.1)
                if not self.interruptible_sleep(click_delay):
                    return False
                
                # Step 4: Click Craft Button (QUANTITY times - once per bait to craft)
                for q in range(quantity):
                    if not self.is_running():
                        return False
                    print(f"\r[AC] {bait_name}: Clicking craft button {q+1}/{quantity}...", end='', flush=True)
                    self.mouse.click(self.craft_button_coords['x'], self.craft_button_coords['y'], hold_delay=0.1)
                    if not self.interruptible_sleep(click_delay):
                        return False
            
            print(f"\r[Auto Craft] ✅ Crafting sequence completed successfully!", end='', flush=True)
            return True
            
        except Exception as e:
            print(f"\r[Auto Craft] ❌ Error during crafting: {str(e)}", end='', flush=True)
            logger.error(f"Craft automation error: {e}", exc_info=True)
            return False
    
    def update_settings(self, settings):
        """Update settings (called when user changes settings in UI)"""
        self.craft_common_quantity = settings.get('craft_common_quantity', self.craft_common_quantity)
        self.craft_rare_quantity = settings.get('craft_rare_quantity', self.craft_rare_quantity)
        self.craft_legendary_quantity = settings.get('craft_legendary_quantity', self.craft_legendary_quantity)
        self.common_bait_coords = settings.get('common_bait_coords', self.common_bait_coords)
        self.rare_bait_coords = settings.get('rare_bait_coords', self.rare_bait_coords)
        self.legendary_bait_coords = settings.get('legendary_bait_coords', self.legendary_bait_coords)
        self.plus_button_coords = settings.get('plus_button_coords', self.plus_button_coords)
        self.fish_icon_coords = settings.get('fish_icon_coords', self.fish_icon_coords)
        self.craft_button_coords = settings.get('craft_button_coords', self.craft_button_coords)
        self.rod_hotkey = settings.get('rod_hotkey', self.rod_hotkey)
        self.craft_menu_delay = settings.get('craft_menu_delay', self.craft_menu_delay)
        self.craft_click_speed = settings.get('craft_click_speed', self.craft_click_speed)
