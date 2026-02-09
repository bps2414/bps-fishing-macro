# gui/tabs/settings_tab.py
# Settings Tab - Notifications, Pre-Cast, Auto Buy Bait, Auto Store Fruit, Casting
import customtkinter as ctk
import tkinter as tk


def build(app, parent):
    """Build the Settings tab widgets.

    Args:
        app: FishingMacroGUI instance (self)
        parent: The tab frame to build into
    """
    # V3: Sound Notification section
    sound_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
    sound_frame.pack(fill="x", pady=10)

    sound_title = ctk.CTkLabel(
        sound_frame,
        text="🔔 NOTIFICATIONS",
        font=("Arial", 14, "bold"),
        text_color=app.accent_color,
    )
    sound_title.pack(pady=(10, 10))

    # Sound notification checkbox
    app.sound_enabled_var = tk.BooleanVar(value=app.sound_enabled)
    sound_check = ctk.CTkCheckBox(
        sound_frame,
        text="🔊 Play sound when fruit detected",
        variable=app.sound_enabled_var,
        command=app.toggle_sound_notification,
        fg_color=app.accent_color,
        hover_color=app.hover_color,
        font=("Arial", 12, "bold"),
    )
    sound_check.pack(fill="x", pady=(5, 15), padx=15)

    # Pre-Cast section
    precast_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
    precast_frame.pack(fill="x", pady=10)

    precast_title = ctk.CTkLabel(
        precast_frame,
        text="🎣 PRE-CAST SETTINGS",
        font=("Arial", 14, "bold"),
        text_color=app.accent_color,
    )
    precast_title.pack(pady=(10, 5))

    # Auto Buy Bait checkbox
    app.auto_buy_bait_var = tk.BooleanVar(value=app.auto_buy_bait)
    app.auto_bait_checkbox = ctk.CTkCheckBox(
        precast_frame,
        text="Auto Buy Bait",
        variable=app.auto_buy_bait_var,
        command=app.toggle_auto_buy_bait,
        fg_color=app.success_color,
        hover_color=app.hover_color,
        font=("Segoe UI", 11),
    )
    app.auto_bait_checkbox.pack(fill="x", pady=5, padx=15)

    # Warning about mutual exclusion with Auto Craft
    app.auto_bait_warning = ctk.CTkLabel(
        precast_frame,
        text="Cannot be used with Auto Craft mode",
        font=("Segoe UI", 9),
        text_color=app.warning_color,
    )
    app.auto_bait_warning.pack(fill="x", pady=(0, 5), padx=15)

    # Auto Buy Bait section (shown/hidden based on checkbox)
    app.auto_bait_section = ctk.CTkFrame(precast_frame, fg_color="transparent")
    if app.auto_buy_bait:
        app.auto_bait_section.pack(fill="x", pady=5, padx=12)

    # Yes Button row
    yes_button_row = ctk.CTkFrame(app.auto_bait_section, fg_color="transparent")
    yes_button_row.pack(fill="x", pady=5)
    ctk.CTkLabel(
        yes_button_row,
        text="✅ Yes Button",
        font=("Arial", 11, "bold"),
        width=140,
        anchor="w",
    ).pack(side="left", padx=(0, 6))
    app.yes_button_btn = ctk.CTkButton(
        yes_button_row,
        text="Select",
        command=lambda: app.start_button_selection("yes"),
        width=90,
        fg_color=app.button_color,
        hover_color=app.hover_color,
    )
    app.yes_button_btn.pack(side="left", padx=6)
    app.yes_button_label = ctk.CTkLabel(
        yes_button_row, text="None", font=("Arial", 10), text_color="#ffaa00"
    )
    app.yes_button_label.pack(side="left", padx=6)
    if app.yes_button:
        app.yes_button_label.configure(
            text=f"({app.yes_button['x']}, {app.yes_button['y']})",
            text_color="#00dd00",
        )

    # Middle Button row
    middle_button_row = ctk.CTkFrame(app.auto_bait_section, fg_color="transparent")
    middle_button_row.pack(fill="x", pady=5)
    ctk.CTkLabel(
        middle_button_row,
        text="⏸️ Middle Button",
        font=("Arial", 11, "bold"),
        width=140,
        anchor="w",
    ).pack(side="left", padx=(0, 6))
    app.middle_button_btn = ctk.CTkButton(
        middle_button_row,
        text="Select",
        command=lambda: app.start_button_selection("middle"),
        width=90,
        fg_color=app.button_color,
        hover_color=app.hover_color,
    )
    app.middle_button_btn.pack(side="left", padx=6)
    app.middle_button_label = ctk.CTkLabel(
        middle_button_row, text="None", font=("Arial", 10), text_color="#ffaa00"
    )
    app.middle_button_label.pack(side="left", padx=6)
    if app.middle_button:
        app.middle_button_label.configure(
            text=f"({app.middle_button['x']}, {app.middle_button['y']})",
            text_color="#00dd00",
        )

    # No Button row
    no_button_row = ctk.CTkFrame(app.auto_bait_section, fg_color="transparent")
    no_button_row.pack(fill="x", pady=5)
    ctk.CTkLabel(
        no_button_row,
        text="❌ No Button",
        font=("Arial", 11, "bold"),
        width=140,
        anchor="w",
    ).pack(side="left", padx=(0, 6))
    app.no_button_btn = ctk.CTkButton(
        no_button_row,
        text="Select",
        command=lambda: app.start_button_selection("no"),
        width=90,
        fg_color=app.button_color,
        hover_color=app.hover_color,
    )
    app.no_button_btn.pack(side="left", padx=6)
    app.no_button_label = ctk.CTkLabel(
        no_button_row, text="None", font=("Arial", 10), text_color="#ffaa00"
    )
    app.no_button_label.pack(side="left", padx=6)
    if app.no_button:
        app.no_button_label.configure(
            text=f"({app.no_button['x']}, {app.no_button['y']})",
            text_color="#00dd00",
        )

    # Loops per purchase row
    loops_row = ctk.CTkFrame(app.auto_bait_section, fg_color="transparent")
    loops_row.pack(fill="x", pady=8)
    ctk.CTkLabel(
        loops_row,
        text="🔄 Loops per purchase:",
        font=("Arial", 11, "bold"),
        width=170,
        anchor="w",
    ).pack(side="left", padx=(0, 6))
    loops_container, app.loops_entry = app.create_spinbox_entry(
        loops_row,
        app.loops_per_purchase,
        min_val=1,
        max_val=100,
        step=1,
        width=90,
        is_float=False,
    )
    loops_container.pack(side="left", padx=5)
    app.loops_entry.bind("<FocusOut>", lambda e: app.save_loops_setting())
    app.loops_entry.bind("<Return>", lambda e: app.save_loops_setting())

    # Auto Store Devil Fruit checkbox
    app.auto_store_fruit_var = tk.BooleanVar(value=app.auto_store_fruit)
    app.auto_fruit_checkbox = ctk.CTkCheckBox(
        precast_frame,
        text="Auto Store Devil Fruit",
        variable=app.auto_store_fruit_var,
        command=app.toggle_auto_store_fruit,
        fg_color=app.success_color,
        hover_color=app.hover_color,
        font=("Segoe UI", 11),
    )
    app.auto_fruit_checkbox.pack(fill="x", pady=5, padx=15)

    # Auto Store Fruit section (shown/hidden based on checkbox)
    app.auto_fruit_section = ctk.CTkFrame(precast_frame, fg_color="transparent")
    if app.auto_store_fruit:
        app.auto_fruit_section.pack(fill="x", pady=5, padx=20)

    # Fruit hotkey row
    fruit_hotkey_row = ctk.CTkFrame(app.auto_fruit_section, fg_color="transparent")
    fruit_hotkey_row.pack(fill="x", pady=5)
    ctk.CTkLabel(
        fruit_hotkey_row,
        text="🍎 Fruit Hotkey",
        font=("Arial", 11, "bold"),
        width=120,
        anchor="w",
    ).pack(side="left")
    app.fruit_hotkey_var = tk.StringVar(value=app.fruit_hotkey)
    fruit_hotkey_combo = ctk.CTkComboBox(
        fruit_hotkey_row,
        variable=app.fruit_hotkey_var,
        values=[str(i) for i in range(1, 11)],
        width=80,
        state="readonly",
        fg_color=app.button_color,
        button_color=app.accent_color,
        button_hover_color=app.hover_color,
        command=lambda e: app.save_item_hotkeys(),
    )
    fruit_hotkey_combo.pack(side="left", padx=8)

    # Fruit Point row
    fruit_point_row = ctk.CTkFrame(app.auto_fruit_section, fg_color="transparent")
    fruit_point_row.pack(fill="x", pady=5)
    ctk.CTkLabel(
        fruit_point_row,
        text="🍎 Fruit Point",
        font=("Arial", 11, "bold"),
        width=120,
        anchor="w",
    ).pack(side="left")
    app.fruit_point_btn = ctk.CTkButton(
        fruit_point_row,
        text="Select",
        command=app.start_fruit_point_selection,
        width=100,
        fg_color=app.button_color,
        hover_color=app.hover_color,
    )
    app.fruit_point_btn.pack(side="left", padx=5)
    app.fruit_point_label = ctk.CTkLabel(
        fruit_point_row, text="None", font=("Arial", 10), text_color="#ffaa00"
    )
    app.fruit_point_label.pack(side="left", padx=5)
    if app.fruit_point and app.fruit_color:
        color_hex = (
            f"#{app.fruit_color[2]:02x}{app.fruit_color[1]:02x}{app.fruit_color[0]:02x}"
        )
        app.fruit_point_label.configure(
            text=f"({app.fruit_point['x']}, {app.fruit_point['y']}) {color_hex}",
            text_color="#00dd00",
        )

    # New: Checkbox "Não dropar, guardar no inventário"
    app.store_in_inventory_var = tk.BooleanVar(value=app.store_in_inventory)
    app.store_in_inventory_checkbox = ctk.CTkCheckBox(
        app.auto_fruit_section,
        text="Don't drop, save in inventory",
        variable=app.store_in_inventory_var,
        command=app.toggle_store_in_inventory,
        fg_color=app.success_color,
        hover_color=app.hover_color,
        font=("Segoe UI", 11),
    )
    app.store_in_inventory_checkbox.pack(fill="x", pady=5, padx=5)

    # Inventory Fruit Point section (shown/hidden based on checkbox)
    app.inventory_fruit_section = ctk.CTkFrame(
        app.auto_fruit_section, fg_color="transparent"
    )
    if app.store_in_inventory:
        app.inventory_fruit_section.pack(fill="x", pady=5, padx=10)

    # Merged Row: Inventory Fruit Point & Center Point
    inventory_points_row = ctk.CTkFrame(
        app.inventory_fruit_section, fg_color="transparent"
    )
    inventory_points_row.pack(fill="x", pady=5)

    # Left side: Inventory Fruit Point
    left_frame = ctk.CTkFrame(inventory_points_row, fg_color="transparent")
    left_frame.pack(side="left", fill="both", expand=True)

    ctk.CTkLabel(
        left_frame,
        text="📦 Inv. Slot",
        font=("Arial", 11, "bold"),
        width=80,
        anchor="w",
    ).pack(side="left")
    app.inventory_fruit_point_btn = ctk.CTkButton(
        left_frame,
        text="Select",
        command=app.start_inventory_fruit_point_selection,
        width=60,
        fg_color=app.button_color,
        hover_color=app.hover_color,
    )
    app.inventory_fruit_point_btn.pack(side="left", padx=5)
    app.inventory_fruit_point_label = ctk.CTkLabel(
        left_frame, text="None", font=("Arial", 10), text_color="#ffaa00"
    )
    app.inventory_fruit_point_label.pack(side="left", padx=5)

    # Right side: Center Point
    right_frame = ctk.CTkFrame(inventory_points_row, fg_color="transparent")
    right_frame.pack(side="left", fill="both", expand=True)

    ctk.CTkLabel(
        right_frame,
        text="🎯 Center",
        font=("Arial", 11, "bold"),
        width=80,
        anchor="w",
    ).pack(side="left")
    app.inventory_center_point_btn = ctk.CTkButton(
        right_frame,
        text="Select",
        command=app.start_inventory_center_point_selection,
        width=60,
        fg_color=app.button_color,
        hover_color=app.hover_color,
    )
    app.inventory_center_point_btn.pack(side="left", padx=5)
    app.inventory_center_point_label = ctk.CTkLabel(
        right_frame, text="Default", font=("Arial", 10), text_color="#ffaa00"
    )
    app.inventory_center_point_label.pack(side="left", padx=5)

    # Update labels if points exist
    if app.inventory_fruit_point:
        app.inventory_fruit_point_label.configure(
            text=f"({app.inventory_fruit_point['x']}, {app.inventory_fruit_point['y']})",
            text_color="#00dd00",
        )
    if app.inventory_center_point:
        app.inventory_center_point_label.configure(
            text=f"({app.inventory_center_point['x']}, {app.inventory_center_point['y']})",
            text_color="#00dd00",
        )

    # Auto Select Top Bait checkbox
    app.auto_select_top_bait_var = tk.BooleanVar(value=app.auto_select_top_bait)
    app.auto_top_bait_checkbox = ctk.CTkCheckBox(
        precast_frame,
        text="Auto Select Top Bait",
        variable=app.auto_select_top_bait_var,
        command=app.toggle_auto_select_top_bait,
        fg_color=app.success_color,
        hover_color=app.hover_color,
        font=("Segoe UI", 11),
    )
    app.auto_top_bait_checkbox.pack(fill="x", pady=5, padx=15)

    # Auto Select Top Bait section (shown/hidden based on checkbox)
    app.auto_top_bait_section = ctk.CTkFrame(precast_frame, fg_color="transparent")
    if app.auto_select_top_bait:
        app.auto_top_bait_section.pack(fill="x", pady=5, padx=20)

    # Top Bait Point row
    top_bait_point_row = ctk.CTkFrame(app.auto_top_bait_section, fg_color="transparent")
    top_bait_point_row.pack(fill="x", pady=5)
    ctk.CTkLabel(
        top_bait_point_row,
        text="🎯 Bait Point",
        font=("Arial", 11, "bold"),
        width=120,
        anchor="w",
    ).pack(side="left")
    app.top_bait_point_btn = ctk.CTkButton(
        top_bait_point_row,
        text="Select",
        command=app.start_top_bait_point_selection,
        width=100,
        fg_color=app.button_color,
        hover_color=app.hover_color,
    )
    app.top_bait_point_btn.pack(side="left", padx=5)
    app.top_bait_point_label = ctk.CTkLabel(
        top_bait_point_row, text="None", font=("Arial", 10), text_color="#ffaa00"
    )
    app.top_bait_point_label.pack(side="left", padx=5)
    if app.top_bait_point:
        app.top_bait_point_label.configure(
            text=f"({app.top_bait_point['x']}, {app.top_bait_point['y']})",
            text_color="#00dd00",
        )

    # Casting section
    casting_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
    casting_frame.pack(fill="x", pady=10)

    casting_title = ctk.CTkLabel(
        casting_frame,
        text="🎯 CASTING SETTINGS",
        font=("Arial", 14, "bold"),
        text_color=app.accent_color,
    )
    casting_title.pack(pady=(10, 15))

    # Water point row
    water_point_row = ctk.CTkFrame(casting_frame, fg_color="transparent")
    water_point_row.pack(fill="x", pady=10, padx=15)

    ctk.CTkLabel(
        water_point_row,
        text="🌊 Water Point",
        font=("Arial", 11, "bold"),
        width=150,
        anchor="w",
    ).pack(side="left")
    app.water_point_button = ctk.CTkButton(
        water_point_row,
        text="Select",
        command=app.start_water_point_selection,
        width=120,
        fg_color=app.button_color,
        hover_color=app.hover_color,
    )
    app.water_point_button.pack(side="left", padx=5)
    app.water_point_label = ctk.CTkLabel(
        water_point_row, text="None", font=("Arial", 10), text_color="#ffaa00"
    )
    app.water_point_label.pack(side="left", padx=5)

    # Update label if water point exists
    if app.water_point:
        app.water_point_label.configure(
            text=f"({app.water_point['x']}, {app.water_point['y']})",
            text_color="#00dd00",
        )

    # Cast hold duration row
    cast_hold_row = ctk.CTkFrame(casting_frame, fg_color="transparent")
    cast_hold_row.pack(fill="x", pady=5, padx=15)
    ctk.CTkLabel(
        cast_hold_row,
        text="Cast hold duration (s):",
        font=("Arial", 11),
        width=150,
        anchor="w",
    ).pack(side="left")
    cast_hold_container, app.cast_hold_entry = app.create_spinbox_entry(
        cast_hold_row,
        app.cast_hold_duration,
        min_val=0.1,
        max_val=5.0,
        step=0.1,
        width=120,
    )
    cast_hold_container.pack(side="left", padx=5)

    # Recast timeout row
    recast_timeout_row = ctk.CTkFrame(casting_frame, fg_color="transparent")
    recast_timeout_row.pack(fill="x", pady=5, padx=15)
    ctk.CTkLabel(
        recast_timeout_row,
        text="Recast timeout (s):",
        font=("Arial", 11),
        width=150,
        anchor="w",
    ).pack(side="left")
    recast_timeout_container, app.recast_timeout_entry = app.create_spinbox_entry(
        recast_timeout_row,
        app.recast_timeout,
        min_val=1.0,
        max_val=30.0,
        step=0.5,
        width=120,
    )
    recast_timeout_container.pack(side="left", padx=5)

    # Save button for casting settings
    save_casting_btn_row = ctk.CTkFrame(casting_frame, fg_color="transparent")
    save_casting_btn_row.pack(fill="x", pady=(10, 15), padx=15)
    ctk.CTkButton(
        save_casting_btn_row,
        text="💾 Save Casting Settings",
        command=app.save_casting_from_ui,
        width=200,
        fg_color=app.accent_color,
        hover_color=app.hover_color,
        font=("Arial", 12, "bold"),
    ).pack()
