# gui/tabs/craft_tab.py
# Auto Craft Tab - Auto Craft, Smart Bait OCR, Coordinates, 2nd Bait Selection
import customtkinter as ctk
import tkinter as tk


def build(app, parent, ensure_ocr_dependencies):
    """Build the Auto Craft tab widgets.

    Args:
        app: FishingMacroGUI instance (self)
        parent: The tab frame to build into
        ensure_ocr_dependencies: Function to check/install OCR dependencies
    """
    # Auto Craft Enable Checkbox
    auto_craft_enable_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
    auto_craft_enable_frame.pack(fill="x", pady=10)

    auto_craft_title = ctk.CTkLabel(
        auto_craft_enable_frame,
        text="⚒️ AUTO CRAFT SETTINGS",
        font=("Arial", 14, "bold"),
        text_color=app.accent_color,
    )
    auto_craft_title.pack(pady=(10, 10))

    app.auto_craft_enabled_var = tk.BooleanVar(value=app.auto_craft_enabled)
    app.auto_craft_checkbox = ctk.CTkCheckBox(
        auto_craft_enable_frame,
        text="Enable Auto Craft",
        variable=app.auto_craft_enabled_var,
        command=app.toggle_auto_craft,
        font=("Arial", 12, "bold"),
        fg_color=app.accent_color,
        hover_color=app.hover_color,
    )
    app.auto_craft_checkbox.pack(pady=15, padx=15)

    # Warning about mutual exclusion
    ctk.CTkLabel(
        auto_craft_enable_frame,
        text="⚠️ Note: Auto Craft and Auto Buy Bait cannot be enabled together!",
        font=("Arial", 10, "bold"),
        text_color="#ff9900",
    ).pack(pady=(0, 15), padx=15)

    # Auto Craft Area Selector
    auto_craft_area_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
    auto_craft_area_frame.pack(fill="x", pady=10)

    auto_craft_area_title = ctk.CTkLabel(
        auto_craft_area_frame,
        text="🎯 MINIGAME AREA SELECTOR",
        font=("Arial", 14, "bold"),
        text_color=app.accent_color,
    )
    auto_craft_area_title.pack(pady=(10, 10))

    auto_craft_area_row = ctk.CTkFrame(auto_craft_area_frame, fg_color="transparent")
    auto_craft_area_row.pack(fill="x", pady=10, padx=15)

    ctk.CTkLabel(
        auto_craft_area_row,
        text="⚒️ Auto Craft Area",
        font=("Arial", 11, "bold"),
        width=150,
        anchor="w",
    ).pack(side="left")
    app.auto_craft_area_button = ctk.CTkButton(
        auto_craft_area_row,
        text="OFF",
        command=app.toggle_auto_craft_area,
        width=100,
        fg_color="#666666",
        hover_color="#888888",
        font=("Arial", 12, "bold"),
    )
    app.auto_craft_area_button.pack(side="left", padx=8)

    # Auto Craft Water Point row
    auto_craft_water_point_row = ctk.CTkFrame(
        auto_craft_area_frame, fg_color="transparent"
    )
    auto_craft_water_point_row.pack(fill="x", pady=10, padx=15)

    ctk.CTkLabel(
        auto_craft_water_point_row,
        text="🌊 Water Point",
        font=("Arial", 11, "bold"),
        width=150,
        anchor="w",
    ).pack(side="left")
    app.auto_craft_water_point_button = ctk.CTkButton(
        auto_craft_water_point_row,
        text="Select",
        command=app.start_auto_craft_water_point_selection,
        width=120,
        fg_color=app.button_color,
        hover_color=app.hover_color,
    )
    app.auto_craft_water_point_button.pack(side="left", padx=5)
    app.auto_craft_water_point_label = ctk.CTkLabel(
        auto_craft_water_point_row,
        text="None",
        font=("Arial", 10),
        text_color="#ffaa00",
    )
    app.auto_craft_water_point_label.pack(side="left", padx=5)

    # Update label if water point exists
    if app.auto_craft_water_point:
        app.auto_craft_water_point_label.configure(
            text=f"({app.auto_craft_water_point['x']}, {app.auto_craft_water_point['y']})",
            text_color="#00dd00",
        )

    ctk.CTkLabel(
        auto_craft_area_frame,
        text="Note: Configure the minigame area and water point for auto craft.",
        font=("Arial", 10),
        text_color="#aaaaaa",
    ).pack(pady=(5, 15), padx=15)

    # Craft Settings Frame
    craft_settings_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
    craft_settings_frame.pack(fill="x", pady=10)

    craft_settings_title = ctk.CTkLabel(
        craft_settings_frame,
        text="⚙️ CRAFT CONFIGURATION",
        font=("Arial", 14, "bold"),
        text_color=app.accent_color,
    )
    craft_settings_title.pack(pady=(10, 10))

    # Craft Every N Fish
    craft_every_row = ctk.CTkFrame(craft_settings_frame, fg_color="transparent")
    craft_every_row.pack(fill="x", pady=5, padx=15)
    ctk.CTkLabel(
        craft_every_row,
        text="Craft Every X Fish:",
        font=("Arial", 11),
        width=180,
        anchor="w",
    ).pack(side="left")
    craft_every_container, app.craft_every_n_fish_entry = app.create_spinbox_entry(
        craft_every_row,
        app.craft_every_n_fish,
        min_val=1,
        max_val=100,
        step=1,
        is_float=False,
        width=120,
    )
    craft_every_container.pack(side="left", padx=5)

    # Menu Delay
    menu_delay_row = ctk.CTkFrame(craft_settings_frame, fg_color="transparent")
    menu_delay_row.pack(fill="x", pady=5, padx=15)
    ctk.CTkLabel(
        menu_delay_row,
        text="Menu Delay (s):",
        font=("Arial", 11),
        width=180,
        anchor="w",
    ).pack(side="left")
    menu_delay_container, app.craft_menu_delay_entry = app.create_spinbox_entry(
        menu_delay_row,
        app.craft_menu_delay,
        min_val=0.1,
        max_val=5.0,
        step=0.1,
        width=120,
    )
    menu_delay_container.pack(side="left", padx=5)

    # Click Speed
    click_speed_row = ctk.CTkFrame(craft_settings_frame, fg_color="transparent")
    click_speed_row.pack(fill="x", pady=5, padx=15)
    ctk.CTkLabel(
        click_speed_row,
        text="Click Speed (s):",
        font=("Arial", 11),
        width=180,
        anchor="w",
    ).pack(side="left")
    click_speed_container, app.craft_click_speed_entry = app.create_spinbox_entry(
        click_speed_row,
        app.craft_click_speed,
        min_val=0.01,
        max_val=2.0,
        step=0.01,
        width=120,
    )
    click_speed_container.pack(side="left", padx=5)

    # Legendary Quantity
    legendary_qty_row = ctk.CTkFrame(craft_settings_frame, fg_color="transparent")
    legendary_qty_row.pack(fill="x", pady=5, padx=15)
    ctk.CTkLabel(
        legendary_qty_row,
        text="🟡 Legendary Quantity:",
        font=("Arial", 11, "bold"),
        width=180,
        anchor="w",
    ).pack(side="left")
    legendary_container, app.craft_legendary_quantity_entry = app.create_spinbox_entry(
        legendary_qty_row,
        app.craft_legendary_quantity,
        min_val=0,
        max_val=200,
        step=5,
        is_float=False,
        width=120,
    )
    legendary_container.pack(side="left", padx=5)

    # Rare Quantity
    rare_qty_row = ctk.CTkFrame(craft_settings_frame, fg_color="transparent")
    rare_qty_row.pack(fill="x", pady=5, padx=15)
    ctk.CTkLabel(
        rare_qty_row,
        text="🔵 Rare Quantity:",
        font=("Arial", 11, "bold"),
        width=180,
        anchor="w",
    ).pack(side="left")
    rare_container, app.craft_rare_quantity_entry = app.create_spinbox_entry(
        rare_qty_row,
        app.craft_rare_quantity,
        min_val=0,
        max_val=200,
        step=5,
        is_float=False,
        width=120,
    )
    rare_container.pack(side="left", padx=5)

    # Common Quantity
    common_qty_row = ctk.CTkFrame(craft_settings_frame, fg_color="transparent")
    common_qty_row.pack(fill="x", pady=5, padx=15)
    ctk.CTkLabel(
        common_qty_row,
        text="⚪ Common Quantity:",
        font=("Arial", 11, "bold"),
        width=180,
        anchor="w",
    ).pack(side="left")
    common_container, app.craft_common_quantity_entry = app.create_spinbox_entry(
        common_qty_row,
        app.craft_common_quantity,
        min_val=0,
        max_val=200,
        step=5,
        is_float=False,
        width=120,
    )
    common_container.pack(side="left", padx=5)

    # Save Button
    save_craft_settings_btn = ctk.CTkButton(
        craft_settings_frame,
        text="💾 Save Craft Settings",
        command=app.save_craft_settings_from_ui,
        fg_color=app.accent_color,
        hover_color=app.hover_color,
        font=("Arial", 12, "bold"),
    )
    save_craft_settings_btn.pack(pady=15)

    # Coordinates Frame
    craft_coords_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
    craft_coords_frame.pack(fill="x", pady=10)

    craft_coords_title = ctk.CTkLabel(
        craft_coords_frame,
        text="📍 CRAFT COORDINATES",
        font=("Arial", 14, "bold"),
        text_color=app.accent_color,
    )
    craft_coords_title.pack(pady=(10, 10))

    # Helper function to create coordinate rows
    def create_coord_row(coord_parent, label_text, coord_name):
        row = ctk.CTkFrame(coord_parent, fg_color="transparent")
        row.pack(fill="x", pady=5, padx=15)

        ctk.CTkLabel(
            row, text=label_text, font=("Arial", 11), width=180, anchor="w"
        ).pack(side="left")

        btn = ctk.CTkButton(
            row,
            text="Set Position",
            command=lambda: app.start_auto_craft_coord_selection(coord_name),
            width=120,
            fg_color=app.button_color,
            hover_color=app.hover_color,
        )
        btn.pack(side="left", padx=5)

        # Get current coordinate value
        coord_value = getattr(app, coord_name, None)
        if coord_value:
            label_text_val = f"X: {coord_value['x']}, Y: {coord_value['y']}"
            label_color = "#00dd00"
        else:
            label_text_val = "Not Set"
            label_color = "#ff4444"

        label = ctk.CTkLabel(
            row, text=label_text_val, font=("Arial", 10), text_color=label_color
        )
        label.pack(side="left", padx=5)

        return btn, label

    # Create all coordinate rows for CRAFTING (clicking slots in craft menu)
    app.craft_button_btn, app.craft_button_label = create_coord_row(
        craft_coords_frame, "🎯 Craft Button:", "craft_button_coords"
    )
    app.plus_button_btn, app.plus_button_label = create_coord_row(
        craft_coords_frame, "➕ Plus Button:", "plus_button_coords"
    )
    app.fish_icon_btn, app.fish_icon_label = create_coord_row(
        craft_coords_frame, "🐟 Fish Icon:", "fish_icon_coords"
    )
    app.legendary_bait_btn, app.legendary_bait_label = create_coord_row(
        craft_coords_frame, "🟡 Legendary Bait:", "legendary_bait_coords"
    )
    app.rare_bait_btn, app.rare_bait_label = create_coord_row(
        craft_coords_frame, "🔵 Rare Bait:", "rare_bait_coords"
    )
    app.common_bait_btn, app.common_bait_label = create_coord_row(
        craft_coords_frame, "⚪ Common Bait:", "common_bait_coords"
    )

    ctk.CTkLabel(
        craft_coords_frame,
        text="Click 'Set Position' then right-click on the target location in-game.",
        font=("Arial", 10),
        text_color="#aaaaaa",
    ).pack(pady=(5, 10), padx=15)

    # ========== 2ND BAIT SELECTION (FOR SMART BAIT FISHING) ==========
    bait_selection_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
    bait_selection_frame.pack(fill="x", pady=10)

    ctk.CTkLabel(
        bait_selection_frame,
        text="🎣 2ND BAIT SELECTION (SMART BAIT)",
        font=("Arial", 14, "bold"),
        text_color=app.accent_color,
    ).pack(pady=(10, 5))

    ctk.CTkLabel(
        bait_selection_frame,
        text="This coordinate is used by Smart Bait when selecting 2nd bait (Rare) during fishing.",
        font=("Arial", 9),
        text_color="#aaaaaa",
    ).pack(pady=(0, 5), padx=15)

    ctk.CTkLabel(
        bait_selection_frame,
        text="ℹ️ 1st Bait (Legendary) uses 'Top Bait Point' from Pre-Cast Settings tab.",
        font=("Arial", 9, "bold"),
        text_color="#00aaff",
    ).pack(pady=(0, 10), padx=15)

    smart_bait_2nd_row = ctk.CTkFrame(bait_selection_frame, fg_color="transparent")
    smart_bait_2nd_row.pack(fill="x", pady=5, padx=15)
    ctk.CTkLabel(
        smart_bait_2nd_row,
        text="🔵 2nd Bait (Rare):",
        font=("Arial", 11, "bold"),
        width=140,
        anchor="w",
    ).pack(side="left", padx=5)
    app.smart_bait_2nd_btn = ctk.CTkButton(
        smart_bait_2nd_row,
        text="Set Position",
        command=lambda: app.start_auto_craft_coord_selection("smart_bait_2nd_coords"),
        width=100,
        fg_color=app.button_color,
        hover_color=app.hover_color,
    )
    app.smart_bait_2nd_btn.pack(side="left", padx=5)
    smart_bait_2nd_text = "Not Set"
    smart_bait_2nd_color = "#ff4444"
    if app.smart_bait_2nd_coords:
        smart_bait_2nd_text = (
            f"X: {app.smart_bait_2nd_coords['x']}, Y: {app.smart_bait_2nd_coords['y']}"
        )
        smart_bait_2nd_color = "#00dd00"
    app.smart_bait_2nd_label = ctk.CTkLabel(
        smart_bait_2nd_row,
        text=smart_bait_2nd_text,
        font=("Arial", 10),
        text_color=smart_bait_2nd_color,
    )
    app.smart_bait_2nd_label.pack(side="left", padx=5)

    ctk.CTkLabel(bait_selection_frame, text="", font=("Arial", 1)).pack(pady=(0, 8))

    # ========== V4: SMART BAIT SECTION ==========
    _build_smart_bait_section(app, parent, ensure_ocr_dependencies)


def _build_smart_bait_section(app, parent, ensure_ocr_dependencies):
    """Build the Smart Bait (OCR) section within the Auto Craft tab."""
    smart_bait_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
    smart_bait_frame.pack(fill="x", pady=10)

    smart_bait_title = ctk.CTkLabel(
        smart_bait_frame,
        text="🧠 SMART BAIT (OCR)",
        font=("Arial", 14, "bold"),
        text_color=app.accent_color,
    )
    smart_bait_title.pack(pady=(10, 5))

    # RapidOCR status indicator
    available, err = ensure_ocr_dependencies()
    ocr_status_text = (
        "✅ RapidOCR Available" if available else "❌ RapidOCR Not Installed"
    )
    ocr_status_color = "#00dd00" if available else "#ff4444"
    ctk.CTkLabel(
        smart_bait_frame,
        text=ocr_status_text,
        font=("Arial", 10),
        text_color=ocr_status_color,
    ).pack(pady=(0, 5))
    if not available:
        ctk.CTkLabel(
            smart_bait_frame,
            text="Clique para instalar dependências OCR",
            font=("Arial", 9),
            text_color="#ffaa00",
        ).pack(pady=(0, 5))

        # Botão para instalar dependências
        def install_ocr():
            ok, err = ensure_ocr_dependencies()
            if ok:
                tk.messagebox.showinfo(
                    "OCR",
                    "Dependências OCR instaladas! Reinicie o macro para ativar o OCR.",
                )
            else:
                tk.messagebox.showerror("OCR", f"Erro ao instalar dependências: {err}")

        ctk.CTkButton(smart_bait_frame, text="Instalar OCR", command=install_ocr).pack(
            pady=(0, 5)
        )

    # Enable Smart Bait checkbox
    app.smart_bait_enabled_var = tk.BooleanVar(value=app.smart_bait_enabled)
    smart_bait_check = ctk.CTkCheckBox(
        smart_bait_frame,
        text="Enable Smart Bait (Murtaza)",
        variable=app.smart_bait_enabled_var,
        command=app.toggle_smart_bait,
        fg_color=app.success_color,
        hover_color=app.hover_color,
        font=("Segoe UI", 11, "bold"),
    )
    smart_bait_check.pack(pady=5, padx=15)

    # Current mode display (read-only, set by popup)
    mode_display_row = ctk.CTkFrame(smart_bait_frame, fg_color="transparent")
    mode_display_row.pack(fill="x", pady=5, padx=15)
    ctk.CTkLabel(
        mode_display_row,
        text="Current Mode:",
        font=("Arial", 11),
        width=120,
        anchor="w",
    ).pack(side="left")
    app.smart_bait_mode_display_label = ctk.CTkLabel(
        mode_display_row,
        text=app.smart_bait_mode.upper(),
        font=("Arial", 12, "bold"),
        text_color="#ff8800" if app.smart_bait_mode == "burning" else "#00ddff",
    )
    app.smart_bait_mode_display_label.pack(side="left", padx=5)

    # Mode descriptions
    ctk.CTkLabel(
        smart_bait_frame,
        text="⚡ OCR Mode: Auto-cycle between modes based on counts",
        font=("Arial", 9, "bold"),
        text_color="#00ff88",
    ).pack(pady=(0, 2), padx=15)
    ctk.CTkLabel(
        smart_bait_frame,
        text="• Burning→Stockpile at 1 leg (OCR) OR when Rare detected (Color-Only)\n"
        "• Stockpile→Burning at target (OCR) OR manual switch (Color-Only)",
        font=("Arial", 8),
        text_color="#aaaaaa",
        justify="left",
    ).pack(pady=(0, 5), padx=15)

    # Legendary target (OCR mode only - for auto-switch back to Burning)
    app.smart_bait_target_row = ctk.CTkFrame(smart_bait_frame, fg_color="transparent")
    if app.smart_bait_use_ocr:
        app.smart_bait_target_row.pack(fill="x", pady=5, padx=15)
    ctk.CTkLabel(
        app.smart_bait_target_row,
        text="Legendary Target:",
        font=("Arial", 11),
        width=120,
        anchor="w",
    ).pack(side="left")
    target_container, app.smart_bait_target_entry = app.create_spinbox_entry(
        app.smart_bait_target_row,
        app.smart_bait_legendary_target,
        min_val=1,
        max_val=500,
        step=10,
        is_float=False,
        width=100,
    )
    target_container.pack(side="left", padx=5)
    app.smart_bait_target_entry.bind(
        "<FocusOut>", lambda e: app.save_smart_bait_from_ui()
    )
    app.smart_bait_target_entry.bind(
        "<Return>", lambda e: app.save_smart_bait_from_ui()
    )
    ctk.CTkLabel(
        app.smart_bait_target_row,
        text="(OCR only: auto-switch Stockpile→Burning)",
        font=("Arial", 9),
        text_color="#aaaaaa",
    ).pack(side="left", padx=5)

    # Fallback bait (OCR mode only - used when OCR fails)
    app.smart_bait_fallback_row = ctk.CTkFrame(smart_bait_frame, fg_color="transparent")
    if app.smart_bait_use_ocr:
        app.smart_bait_fallback_row.pack(fill="x", pady=5, padx=15)
    ctk.CTkLabel(
        app.smart_bait_fallback_row,
        text="Fallback Bait:",
        font=("Arial", 11),
        width=120,
        anchor="w",
    ).pack(side="left")
    app.smart_bait_fallback_var = tk.StringVar(
        value=app.smart_bait_fallback.capitalize()
    )
    fallback_combo = ctk.CTkComboBox(
        app.smart_bait_fallback_row,
        variable=app.smart_bait_fallback_var,
        values=["Legendary", "Rare"],
        width=120,
        state="readonly",
        fg_color=app.button_color,
        button_color=app.accent_color,
        button_hover_color=app.hover_color,
        command=lambda e: app.save_smart_bait_from_ui(),
    )
    fallback_combo.pack(side="left", padx=5)
    ctk.CTkLabel(
        app.smart_bait_fallback_row,
        text="(OCR only: used when OCR fails)",
        font=("Arial", 9),
        text_color="#aaaaaa",
    ).pack(side="left", padx=5)

    # OCR Zones section
    zones_label = ctk.CTkLabel(
        smart_bait_frame,
        text="📐 OCR Scan Zones",
        font=("Arial", 12, "bold"),
        text_color=app.fg_color,
    )
    zones_label.pack(pady=(10, 5), padx=15, anchor="w")

    # INSTRUCTION FRAME
    instruction_frame = ctk.CTkFrame(
        smart_bait_frame,
        fg_color="#1a3d1a",
        corner_radius=5,
        border_width=2,
        border_color="#44ff44",
    )
    instruction_frame.pack(fill="x", pady=(0, 8), padx=15)

    ctk.CTkLabel(
        instruction_frame,
        text="✅ OCR scans bait menu - position-independent",
        font=("Arial", 10, "bold"),
        text_color="#44ff44",
    ).pack(pady=(8, 8), padx=10)

    ctk.CTkLabel(
        smart_bait_frame,
        text="📍 Menu Zone: Draw rectangle around entire bait list (all 3 types + numbers)",
        font=("Arial", 9, "bold"),
        text_color="#00ccff",
    ).pack(pady=(0, 5), padx=15, anchor="w")

    # Single menu zone
    menu_zone_row = ctk.CTkFrame(smart_bait_frame, fg_color="transparent")
    menu_zone_row.pack(fill="x", pady=5, padx=15)
    ctk.CTkLabel(
        menu_zone_row,
        text="📋 Bait Menu Zone:",
        font=("Arial", 11),
        width=140,
        anchor="w",
    ).pack(side="left")
    app.smart_bait_menu_zone_btn = ctk.CTkButton(
        menu_zone_row,
        text="Select Zone",
        command=lambda: app.start_smart_bait_zone_selection("menu"),
        width=100,
        fg_color=app.button_color,
        hover_color=app.hover_color,
    )
    app.smart_bait_menu_zone_btn.pack(side="left", padx=5)
    zone_text = "Not Set"
    zone_color = "#ff4444"
    if app.smart_bait_menu_zone:
        z = app.smart_bait_menu_zone
        zone_text = f"({z['x']}, {z['y']}) {z['width']}x{z['height']}"
        zone_color = "#00dd00"
    app.smart_bait_menu_zone_label = ctk.CTkLabel(
        menu_zone_row, text=zone_text, font=("Arial", 10), text_color=zone_color
    )
    app.smart_bait_menu_zone_label.pack(side="left", padx=5)

    # Top bait color-scan zone (label only, no numbers)
    ctk.CTkLabel(
        smart_bait_frame,
        text="🎯 Top Label Zone (color scan only, no numbers):",
        font=("Arial", 9, "bold"),
        text_color="#00ccff",
    ).pack(pady=(8, 2), padx=15, anchor="w")
    ctk.CTkLabel(
        smart_bait_frame,
        text="Select only the bait name at the top (exclude the xN numbers).",
        font=("Arial", 9),
        text_color="#aaaaaa",
    ).pack(pady=(0, 5), padx=15, anchor="w")

    top_zone_row = ctk.CTkFrame(smart_bait_frame, fg_color="transparent")
    top_zone_row.pack(fill="x", pady=5, padx=15)
    ctk.CTkLabel(
        top_zone_row,
        text="📍 Top Label Zone:",
        font=("Arial", 11),
        width=140,
        anchor="w",
    ).pack(side="left")
    app.smart_bait_top_zone_btn = ctk.CTkButton(
        top_zone_row,
        text="Select Zone",
        command=lambda: app.start_smart_bait_zone_selection("top"),
        width=120,
        fg_color=app.button_color,
        hover_color=app.hover_color,
    )
    app.smart_bait_top_zone_btn.pack(side="left", padx=5)
    top_zone_text = "Not Set"
    top_zone_color = "#ff4444"
    if app.smart_bait_top_zone:
        zt = app.smart_bait_top_zone
        top_zone_text = f"({zt['x']}, {zt['y']}) {zt['width']}x{zt['height']}"
        top_zone_color = "#00dd00"
    app.smart_bait_top_zone_label = ctk.CTkLabel(
        top_zone_row,
        text=top_zone_text,
        font=("Arial", 10),
        text_color=top_zone_color,
    )
    app.smart_bait_top_zone_label.pack(side="left", padx=5)

    mid_zone_row = ctk.CTkFrame(smart_bait_frame, fg_color="transparent")
    mid_zone_row.pack(fill="x", pady=5, padx=15)
    ctk.CTkLabel(
        mid_zone_row,
        text="📍 Mid Label Zone:",
        font=("Arial", 11),
        width=140,
        anchor="w",
    ).pack(side="left")
    app.smart_bait_mid_zone_btn = ctk.CTkButton(
        mid_zone_row,
        text="Select Zone",
        command=lambda: app.start_smart_bait_zone_selection("mid"),
        width=120,
        fg_color=app.button_color,
        hover_color=app.hover_color,
    )
    app.smart_bait_mid_zone_btn.pack(side="left", padx=5)
    mid_zone_text = "Not Set"
    mid_zone_color = "#ff4444"
    if hasattr(app, "smart_bait_mid_zone") and app.smart_bait_mid_zone:
        zm = app.smart_bait_mid_zone
        mid_zone_text = f"({zm['x']}, {zm['y']}) {zm['width']}x{zm['height']}"
        mid_zone_color = "#00dd00"
    app.smart_bait_mid_zone_label = ctk.CTkLabel(
        mid_zone_row,
        text=mid_zone_text,
        font=("Arial", 10),
        text_color=mid_zone_color,
    )
    app.smart_bait_mid_zone_label.pack(side="left", padx=5)

    # Status text for color detection results
    app.smart_bait_top_hint_label = ctk.CTkLabel(
        smart_bait_frame,
        text="Last detected (top): n/a",
        font=("Arial", 9),
        text_color="#aaaaaa",
    )
    app.smart_bait_top_hint_label.pack(pady=(0, 3), padx=15, anchor="w")

    app.smart_bait_mid_hint_label = ctk.CTkLabel(
        smart_bait_frame,
        text="Last detected (mid): n/a",
        font=("Arial", 9),
        text_color="#aaaaaa",
    )
    app.smart_bait_mid_hint_label.pack(pady=(0, 6), padx=15, anchor="w")

    # Debug checkbox
    app.smart_bait_debug_var = tk.BooleanVar(value=app.smart_bait_debug)
    debug_check = ctk.CTkCheckBox(
        smart_bait_frame,
        text="📸 Save debug screenshots",
        variable=app.smart_bait_debug_var,
        command=app.save_smart_bait_from_ui,
        fg_color=app.accent_color,
        hover_color=app.hover_color,
        font=("Segoe UI", 10),
    )
    debug_check.pack(pady=5, padx=15, anchor="w")

    # Color-Only Mode toggle (disable OCR for performance)
    app.smart_bait_use_ocr_var = tk.BooleanVar(value=app.smart_bait_use_ocr)
    ocr_mode_check = ctk.CTkCheckBox(
        smart_bait_frame,
        text="🤖 Use OCR (uncheck for Color-Only mode - better FPS)",
        variable=app.smart_bait_use_ocr_var,
        command=app.save_smart_bait_from_ui,
        fg_color=app.accent_color,
        hover_color=app.hover_color,
        font=("Segoe UI", 10),
    )
    ocr_mode_check.pack(pady=5, padx=15, anchor="w")

    ctk.CTkLabel(
        smart_bait_frame,
        text="ℹ️ Color-Only Mode Behavior:",
        font=("Arial", 9, "bold"),
        text_color="#00ddff",
    ).pack(pady=(2, 0), padx=15, anchor="w")

    ctk.CTkLabel(
        smart_bait_frame,
        text="• Burning: Scans top slot color. If Legendary→use it. If Rare→auto-switch to Stockpile.\n"
        "• Stockpile: Always uses rare (2nd slot). Manually switch back to Burning when ready.\n"
        "• No counting, only color detection (better FPS, no AI load).",
        font=("Arial", 8),
        text_color="#aaaaaa",
        wraplength=450,
        justify="left",
    ).pack(pady=(0, 8), padx=15, anchor="w")

    # V4: Live Counter Frame (ALWAYS visible - shows preview in both modes)
    app.live_counter_frame = ctk.CTkFrame(
        smart_bait_frame, fg_color="#1a1a1a", corner_radius=8
    )
    app.live_counter_frame.pack(fill="x", pady=10, padx=15)

    # Title changes based on mode
    title_text = (
        "📊 Live OCR Counter & Color Preview"
        if app.smart_bait_use_ocr
        else "🎨 Live Color Detection"
    )
    app.smart_bait_frame_title = ctk.CTkLabel(
        app.live_counter_frame,
        text=title_text,
        font=("Arial", 12, "bold"),
        text_color=app.fg_color,
    )
    app.smart_bait_frame_title.pack(pady=(8, 5))

    # ===== LIVE DETECTION PREVIEW (always visible) =====
    preview_frame = ctk.CTkFrame(
        app.live_counter_frame,
        fg_color="#0d0d0d",
        corner_radius=5,
        border_width=2,
        border_color="#00aa00",
    )
    preview_frame.pack(fill="x", padx=10, pady=(5, 10))

    ctk.CTkLabel(
        preview_frame,
        text="🔴 LIVE DETECTION (auto-updates)",
        font=("Arial", 10, "bold"),
        text_color="#00ff88",
    ).pack(pady=(5, 2))

    # Top slot preview
    top_preview_row = ctk.CTkFrame(preview_frame, fg_color="transparent")
    top_preview_row.pack(fill="x", pady=2, padx=10)
    ctk.CTkLabel(
        top_preview_row,
        text="TOP:",
        font=("Arial", 10, "bold"),
        width=50,
        anchor="w",
    ).pack(side="left")
    app.smart_bait_top_preview = ctk.CTkLabel(
        top_preview_row,
        text="---",
        font=("Arial", 11, "bold"),
        text_color="#aaaaaa",
        width=100,
        anchor="w",
    )
    app.smart_bait_top_preview.pack(side="left", padx=5)

    # Mid slot preview
    mid_preview_row = ctk.CTkFrame(preview_frame, fg_color="transparent")
    mid_preview_row.pack(fill="x", pady=2, padx=10)
    ctk.CTkLabel(
        mid_preview_row,
        text="MID:",
        font=("Arial", 10, "bold"),
        width=50,
        anchor="w",
    ).pack(side="left")
    app.smart_bait_mid_preview = ctk.CTkLabel(
        mid_preview_row,
        text="---",
        font=("Arial", 11, "bold"),
        text_color="#aaaaaa",
        width=100,
        anchor="w",
    )
    app.smart_bait_mid_preview.pack(side="left", padx=5)

    # Detection method indicator
    method_row = ctk.CTkFrame(preview_frame, fg_color="transparent")
    method_row.pack(fill="x", pady=(0, 5), padx=10)
    ctk.CTkLabel(
        method_row,
        text="Method:",
        font=("Arial", 8),
        width=50,
        anchor="w",
        text_color="#666666",
    ).pack(side="left")
    app.smart_bait_method_preview = ctk.CTkLabel(
        method_row, text="---", font=("Arial", 8), text_color="#666666", anchor="w"
    )
    app.smart_bait_method_preview.pack(side="left", padx=5)

    # ===== OCR-ONLY ELEMENTS (hidden in Color-Only mode) =====
    # Counter display grid
    app.smart_bait_counter_grid = ctk.CTkFrame(
        app.live_counter_frame, fg_color="transparent"
    )
    if app.smart_bait_use_ocr:
        app.smart_bait_counter_grid.pack(fill="x", padx=10, pady=5)

    # Legendary counter
    legendary_counter_row = ctk.CTkFrame(
        app.smart_bait_counter_grid, fg_color="transparent"
    )
    legendary_counter_row.pack(fill="x", pady=3)
    ctk.CTkLabel(
        legendary_counter_row,
        text="🟡 Legendary:",
        font=("Arial", 11, "bold"),
        width=100,
        anchor="w",
    ).pack(side="left")
    app.smart_bait_legendary_count_label = ctk.CTkLabel(
        legendary_counter_row,
        text="---",
        font=("Arial", 14, "bold"),
        text_color="#ffaa00",
        width=60,
    )
    app.smart_bait_legendary_count_label.pack(side="left", padx=5)
    app.smart_bait_legendary_conf_label = ctk.CTkLabel(
        legendary_counter_row, text="", font=("Arial", 9), text_color="#aaaaaa"
    )
    app.smart_bait_legendary_conf_label.pack(side="left", padx=5)

    # Rare counter
    rare_counter_row = ctk.CTkFrame(app.smart_bait_counter_grid, fg_color="transparent")
    rare_counter_row.pack(fill="x", pady=3)
    ctk.CTkLabel(
        rare_counter_row,
        text="🔵 Rare:",
        font=("Arial", 11, "bold"),
        width=100,
        anchor="w",
    ).pack(side="left")
    app.smart_bait_rare_count_label = ctk.CTkLabel(
        rare_counter_row,
        text="---",
        font=("Arial", 14, "bold"),
        text_color="#ffaa00",
        width=60,
    )
    app.smart_bait_rare_count_label.pack(side="left", padx=5)
    app.smart_bait_rare_conf_label = ctk.CTkLabel(
        rare_counter_row, text="", font=("Arial", 9), text_color="#aaaaaa"
    )
    app.smart_bait_rare_conf_label.pack(side="left", padx=5)

    # Decision info (mode + last decision) - OCR only
    app.smart_bait_decision_frame = ctk.CTkFrame(
        app.live_counter_frame, fg_color="#0d0d0d", corner_radius=5
    )
    if app.smart_bait_use_ocr:
        app.smart_bait_decision_frame.pack(fill="x", pady=(5, 5), padx=10)

    # Mode display
    mode_row = ctk.CTkFrame(app.smart_bait_decision_frame, fg_color="transparent")
    mode_row.pack(fill="x", pady=2, padx=5)
    ctk.CTkLabel(
        mode_row, text="Mode:", font=("Arial", 10, "bold"), width=60, anchor="w"
    ).pack(side="left")
    app.smart_bait_mode_display = ctk.CTkLabel(
        mode_row, text="---", font=("Arial", 10, "bold"), text_color="#00ff88"
    )
    app.smart_bait_mode_display.pack(side="left", padx=3)

    # Decision display
    decision_row = ctk.CTkFrame(app.smart_bait_decision_frame, fg_color="transparent")
    decision_row.pack(fill="x", pady=2, padx=5)
    ctk.CTkLabel(
        decision_row,
        text="Decision:",
        font=("Arial", 9),
        width=60,
        anchor="w",
        text_color="#999999",
    ).pack(side="left")
    app.smart_bait_decision_display = ctk.CTkLabel(
        decision_row,
        text="---",
        font=("Arial", 9),
        text_color="#aaaaaa",
        wraplength=200,
        anchor="w",
    )
    app.smart_bait_decision_display.pack(side="left", padx=3, fill="x", expand=True)

    # Auto-refresh controls
    auto_refresh_frame = ctk.CTkFrame(app.live_counter_frame, fg_color="transparent")
    auto_refresh_frame.pack(fill="x", pady=(8, 5), padx=10)

    # Auto-refresh toggle (DISABLED BY DEFAULT)
    app._smart_bait_auto_refresh_enabled = False
    app._smart_bait_refresh_timer = None
    app._smart_bait_refresh_interval = 2000  # 2 seconds

    app.smart_bait_auto_refresh_var = tk.BooleanVar(value=False)
    auto_refresh_check = ctk.CTkCheckBox(
        auto_refresh_frame,
        text="🔄 Auto-Refresh (live updates)",
        variable=app.smart_bait_auto_refresh_var,
        command=app.toggle_smart_bait_auto_refresh,
        fg_color=app.success_color,
        hover_color=app.hover_color,
        font=("Arial", 11, "bold"),
    )
    auto_refresh_check.pack(side="left", padx=5)

    # Refresh interval label
    app.smart_bait_refresh_status = ctk.CTkLabel(
        auto_refresh_frame,
        text="(updates every 2s)",
        font=("Arial", 9),
        text_color="#aaaaaa",
    )
    app.smart_bait_refresh_status.pack(side="left", padx=5)

    # Test buttons (different for OCR vs Color-Only mode)
    app.smart_bait_test_ocr_btn = ctk.CTkButton(
        app.live_counter_frame,
        text="🔍 Test OCR Now",
        command=app.test_smart_bait_ocr,
        width=200,
        fg_color="#0088ff",
        hover_color="#0066cc",
        font=("Arial", 11, "bold"),
    )

    app.smart_bait_test_color_btn = ctk.CTkButton(
        app.live_counter_frame,
        text="🎨 Test Color Detection",
        command=app.test_smart_bait_color,
        width=200,
        fg_color="#ff8800",
        hover_color="#cc6600",
        font=("Arial", 11, "bold"),
    )

    # Show appropriate button based on mode
    if app.smart_bait_use_ocr:
        app.smart_bait_test_ocr_btn.pack(pady=(5, 10))
    else:
        app.smart_bait_test_color_btn.pack(pady=(5, 10))

    app.smart_bait_test_instructions = ctk.CTkLabel(
        app.live_counter_frame,
        text="Open crafting menu, then click test button",
        font=("Arial", 9),
        text_color="#aaaaaa",
    )
    app.smart_bait_test_instructions.pack(pady=(0, 8))
