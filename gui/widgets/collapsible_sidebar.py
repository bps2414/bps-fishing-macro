# Copyright (C) 2026 BPS
# This file is part of BPS Fishing Macro.
#
# Collapsible Sidebar Navigation Widget

"""
Collapsible Sidebar with expandable categories for tab navigation.

Features:
- Vertical category list with expand/collapse
- Sub-item support for nested navigation
- Visual feedback for active tab
- Smooth animations (optional)
"""

import customtkinter as ctk
import tkinter as tk


class CollapsibleSidebar(ctk.CTkFrame):
    """Collapsible sidebar navigation widget with expandable categories"""

    def __init__(self, parent, app, **kwargs):
        """Initialize sidebar

        Args:
            parent: Parent widget
            app: FishingMacroGUI instance
            **kwargs: Additional CTkFrame arguments
        """
        super().__init__(parent, **kwargs)

        self.app = app
        self.categories = {}  # Store category data
        self.expanded_categories = set()  # Track which categories are expanded
        self.active_item = None  # Currently active tab name

        # Configure sidebar appearance
        self.configure(
            fg_color="#1a1a1a",
            corner_radius=8,
            width=160,
        )

        # Container for category buttons
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=5, pady=5)

    def add_category(self, name, icon="", sub_items=None, callback=None):
        """Add a category to the sidebar

        Args:
            name: Category display name
            icon: Emoji or icon character
            sub_items: List of dicts with 'name' and 'callback' keys (for expandable categories)
            callback: Function to call when clicked (for direct navigation categories)
        """
        category_data = {
            "name": name,
            "icon": icon,
            "sub_items": sub_items or [],
            "callback": callback,
            "widgets": {},
        }

        # Create category button
        category_btn = self._create_category_button(name, icon, bool(sub_items))
        category_data["widgets"]["button"] = category_btn
        category_btn.pack(fill="x", pady=2)

        # Create sub-items frame (hidden by default)
        if sub_items:
            sub_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
            category_data["widgets"]["sub_frame"] = sub_frame

            for sub_item in sub_items:
                sub_btn = self._create_sub_item_button(
                    sub_item["name"], sub_item["callback"], sub_frame
                )
                sub_btn.pack(fill="x", pady=1, padx=(15, 0))

        self.categories[name] = category_data

    def _create_category_button(self, name, icon, has_children):
        """Create a category button widget

        Args:
            name: Category name
            icon: Icon character
            has_children: Whether category has sub-items

        Returns:
            CTkButton instance
        """
        # Determine text and command
        if has_children:
            text = f"{icon} {name} ▶"
            command = lambda: self.toggle_category(name)
        else:
            text = f"{icon} {name}"
            command = lambda: self._on_category_click(name)

        btn = ctk.CTkButton(
            self.content_frame,
            text=text,
            anchor="w",
            fg_color="#2a2a2a",
            hover_color="#3a3a3a",
            text_color="#ffffff",
            font=("Segoe UI", 11, "bold"),
            height=35,
            corner_radius=6,
            command=command,
        )

        return btn

    def _create_sub_item_button(self, name, callback, parent_frame):
        """Create a sub-item button widget

        Args:
            name: Sub-item name
            callback: Function to call when clicked
            parent_frame: Parent frame to add button to

        Returns:
            CTkButton instance
        """
        btn = ctk.CTkButton(
            parent_frame,
            text=f"  {name}",
            anchor="w",
            fg_color="#222222",
            hover_color="#333333",
            text_color="#cccccc",
            font=("Segoe UI", 10),
            height=30,
            corner_radius=4,
            command=lambda: self._on_sub_item_click(name, callback),
        )

        return btn

    def toggle_category(self, category_name):
        """Expand or collapse a category

        Args:
            category_name: Name of category to toggle
        """
        category = self.categories.get(category_name)
        if not category or not category["sub_items"]:
            return

        sub_frame = category["widgets"]["sub_frame"]
        button = category["widgets"]["button"]

        if category_name in self.expanded_categories:
            # Collapse
            sub_frame.pack_forget()
            self.expanded_categories.remove(category_name)
            button.configure(text=f"{category['icon']} {category_name} ▶")
        else:
            # Expand
            sub_frame.pack(fill="x", pady=(0, 5), after=button)
            self.expanded_categories.add(category_name)
            button.configure(text=f"{category['icon']} {category_name} ▼")

    def _on_category_click(self, category_name):
        """Handle click on category without children (direct navigation)

        Args:
            category_name: Name of category clicked
        """
        category = self.categories.get(category_name)
        if category and category["callback"]:
            # Convert category name to tab name (lowercase, no spaces)
            tab_name = category_name.lower().replace(" ", "_")
            self.select_item(tab_name)
            category["callback"]()

    def _on_sub_item_click(self, item_name, callback):
        """Handle click on sub-item

        Args:
            item_name: Name of sub-item clicked
            callback: Callback function to execute
        """
        # Convert item name to tab name
        tab_name = item_name.lower().replace(" ", "_")
        self.select_item(tab_name)
        callback()

    def select_item(self, item_name):
        """Highlight the selected item

        Args:
            item_name: Name of item to highlight (tab identifier)
        """
        self.active_item = item_name

        # Update all category buttons to default style
        for category_name, category in self.categories.items():
            button = category["widgets"]["button"]

            # Check if this category is the active one (for direct nav)
            category_id = category_name.lower().replace(" ", "_")
            if category_id == item_name and not category["sub_items"]:
                button.configure(
                    fg_color="#3a3a3a",
                    text_color="#ffffff",
                    border_width=2,
                    border_color="#5a9bcf",
                )
            else:
                button.configure(
                    fg_color="#2a2a2a",
                    text_color="#ffffff",
                    border_width=0,
                )

            # Update sub-items
            if category["sub_items"] and "sub_frame" in category["widgets"]:
                sub_frame = category["widgets"]["sub_frame"]
                for widget in sub_frame.winfo_children():
                    if isinstance(widget, ctk.CTkButton):
                        # Extract sub-item name from button text
                        sub_name = widget.cget("text").strip().lower().replace(" ", "_")
                        if sub_name == item_name:
                            widget.configure(
                                fg_color="#3a3a3a",
                                text_color="#ffffff",
                                border_width=2,
                                border_color="#5a9bcf",
                            )
                        else:
                            widget.configure(
                                fg_color="#222222",
                                text_color="#cccccc",
                                border_width=0,
                            )

    def get_active_item(self):
        """Get currently active tab name

        Returns:
            str: Active tab identifier
        """
        return self.active_item
