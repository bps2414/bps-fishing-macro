# Copyright (C) 2026 BPS
# This file is part of BPS Fishing Macro.
#
# Auto Setup Tab - Automated game entry and VIP server joining
# Phase 1: GUI only (automation logic in Phase 2)

import customtkinter as ctk
import tkinter as tk


def build(app, parent):
    """Build the Auto Setup tab widgets

    Args:
        app: FishingMacroGUI instance
        parent: Parent frame to build widgets in
    """

    # ── Info / Enable Section ──────────────────────────────────────
    info_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=8)
    info_frame.pack(fill="x", pady=(0, 10), padx=10)

    ctk.CTkLabel(
        info_frame,
        text="🚀 AUTO SETUP",
        font=("Arial", 14, "bold"),
        text_color=app.fg_color,
    ).pack(pady=(10, 5))

    ctk.CTkLabel(
        info_frame,
        text="Opens Roblox → joins VIP server → positions character → starts macro",
        font=("Arial", 10),
        text_color="#aaaaaa",
        wraplength=400,
    ).pack(pady=(0, 8), padx=15)

    app.auto_setup_enabled_var = tk.BooleanVar(value=app.auto_setup_enabled)
    ctk.CTkCheckBox(
        info_frame,
        text="Enable Auto Setup (runs before macro on F1)",
        variable=app.auto_setup_enabled_var,
        command=app.toggle_auto_setup,
        fg_color=app.success_color,
        hover_color=app.hover_color,
        font=("Arial", 11, "bold"),
    ).pack(pady=(2, 12), padx=15, anchor="w")

    # ── VIP Server Code ────────────────────────────────────────────
    vip_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=8)
    vip_frame.pack(fill="x", pady=(0, 10), padx=10)

    ctk.CTkLabel(
        vip_frame,
        text="🔑 VIP SERVER CODE",
        font=("Arial", 13, "bold"),
        text_color=app.fg_color,
    ).pack(pady=(10, 8))

    vip_row = ctk.CTkFrame(vip_frame, fg_color="transparent")
    vip_row.pack(fill="x", padx=15, pady=(0, 12))

    ctk.CTkLabel(
        vip_row, text="Server Code:", font=("Arial", 11), width=100, anchor="w"
    ).pack(side="left")

    app.auto_setup_vip_code_entry = ctk.CTkEntry(
        vip_row,
        width=300,
        fg_color=app.button_color,
        border_color=app.accent_color,
        placeholder_text="Paste your VIP server code here...",
    )
    app.auto_setup_vip_code_entry.pack(side="left", padx=5, fill="x", expand=True)
    if app.auto_setup_vip_code:
        app.auto_setup_vip_code_entry.insert(0, app.auto_setup_vip_code)

    # ── Coordinates Section ────────────────────────────────────────
    coords_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=8)
    coords_frame.pack(fill="x", pady=(0, 10), padx=10)

    ctk.CTkLabel(
        coords_frame,
        text="📍 COORDINATES",
        font=("Arial", 13, "bold"),
        text_color=app.fg_color,
    ).pack(pady=(10, 8))

    ctk.CTkLabel(
        coords_frame,
        text="Click 'Select' then RIGHT-CLICK on the target location",
        font=("Arial", 9),
        text_color="#888888",
    ).pack(pady=(0, 5), padx=15)

    # Coordinate rows
    coord_definitions = [
        ("🎮 Play Button (Website):", "auto_setup_play_button", "play"),
        ("🔐 Private Server 1:", "auto_setup_private_server_1", "ps1"),
        ("📝 VIP Code Input:", "auto_setup_vip_code_input", "input"),
        ("✅ Enter Regular:", "auto_setup_enter_regular", "enter"),
    ]

    for label_text, coord_attr, short_name in coord_definitions:
        row = ctk.CTkFrame(coords_frame, fg_color="transparent")
        row.pack(fill="x", pady=3, padx=15)

        ctk.CTkLabel(
            row, text=label_text, font=("Arial", 11), width=200, anchor="w"
        ).pack(side="left")

        btn = ctk.CTkButton(
            row,
            text="Select",
            command=lambda a=coord_attr: app.start_auto_setup_coord_selection(a),
            width=80,
            height=28,
            fg_color=app.button_color,
            hover_color=app.hover_color,
            font=("Arial", 10),
        )
        btn.pack(side="left", padx=5)

        coord_value = getattr(app, coord_attr, None)
        if coord_value:
            lbl_text = f"✓ X:{coord_value['x']}  Y:{coord_value['y']}"
            lbl_color = app.success_color
        else:
            lbl_text = "Not Set"
            lbl_color = app.error_color

        label = ctk.CTkLabel(
            row, text=lbl_text, font=("Arial", 10), text_color=lbl_color
        )
        label.pack(side="left", padx=8)

        # Store references for dynamic updates
        setattr(app, f"auto_setup_{short_name}_btn", btn)
        setattr(app, f"auto_setup_{short_name}_label", label)

    # Spacer after coords
    ctk.CTkFrame(coords_frame, fg_color="transparent", height=8).pack()

    # ── Color Detection Section ────────────────────────────────────
    colors_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=8)
    colors_frame.pack(fill="x", pady=(0, 10), padx=10)

    ctk.CTkLabel(
        colors_frame,
        text="🎨 COLOR DETECTION",
        font=("Arial", 13, "bold"),
        text_color=app.fg_color,
    ).pack(pady=(10, 8))

    ctk.CTkLabel(
        colors_frame,
        text="Click 'Select Color' then RIGHT-CLICK on pixel to detect",
        font=("Arial", 9),
        text_color="#888888",
    ).pack(pady=(0, 5), padx=15)

    # Menu Color Detection
    menu_color_row = ctk.CTkFrame(colors_frame, fg_color="transparent")
    menu_color_row.pack(fill="x", pady=5, padx=15)

    menu_label = ctk.CTkLabel(
        menu_color_row,
        text="🎮 Menu Color (initial load):",
        font=("Arial", 11),
        width=200,
        anchor="w",
    )
    menu_label.pack(side="left")

    menu_btn = ctk.CTkButton(
        menu_color_row,
        text="Select Color",
        command=lambda: app.start_auto_setup_color_selection("menu"),
        width=100,
        height=28,
        fg_color=app.button_color,
        hover_color=app.hover_color,
        font=("Arial", 10),
    )
    menu_btn.pack(side="left", padx=5)

    # Menu color status
    menu_color_check = app.auto_setup_menu_color_check
    if menu_color_check.get("coordinate") and menu_color_check.get("color_rgb"):
        coord = menu_color_check["coordinate"]
        color = menu_color_check["color_rgb"]
        menu_status_text = f"✓ X:{coord['x']} Y:{coord['y']} RGB{color}"
        menu_status_color = app.success_color
    else:
        menu_status_text = "Not Set"
        menu_status_color = app.error_color

    menu_status = ctk.CTkLabel(
        menu_color_row,
        text=menu_status_text,
        font=("Arial", 10),
        text_color=menu_status_color,
    )
    menu_status.pack(side="left", padx=8)

    # Color preview for menu
    menu_preview = ctk.CTkFrame(
        menu_color_row, width=40, height=20, corner_radius=4, fg_color="#333333"
    )
    menu_preview.pack(side="left", padx=5)
    if menu_color_check.get("color_rgb"):
        r, g, b = menu_color_check["color_rgb"]
        menu_preview.configure(fg_color=f"#{r:02x}{g:02x}{b:02x}")

    # Store references
    app.auto_setup_menu_color_btn = menu_btn
    app.auto_setup_menu_color_status = menu_status
    app.auto_setup_menu_color_preview = menu_preview

    # Game Loaded Color Detection
    game_color_row = ctk.CTkFrame(colors_frame, fg_color="transparent")
    game_color_row.pack(fill="x", pady=5, padx=15)

    game_label = ctk.CTkLabel(
        game_color_row,
        text="🎯 Game Loaded Color (health bar):",
        font=("Arial", 11),
        width=200,
        anchor="w",
    )
    game_label.pack(side="left")

    game_btn = ctk.CTkButton(
        game_color_row,
        text="Select Color",
        command=lambda: app.start_auto_setup_color_selection("game_loaded"),
        width=100,
        height=28,
        fg_color=app.button_color,
        hover_color=app.hover_color,
        font=("Arial", 10),
    )
    game_btn.pack(side="left", padx=5)

    # Game loaded color status
    game_color_check = app.auto_setup_game_loaded_color_check
    if game_color_check.get("coordinate") and game_color_check.get("color_rgb"):
        coord = game_color_check["coordinate"]
        color = game_color_check["color_rgb"]
        game_status_text = f"✓ X:{coord['x']} Y:{coord['y']} RGB{color}"
        game_status_color = app.success_color
    else:
        game_status_text = "Not Set"
        game_status_color = app.error_color

    game_status = ctk.CTkLabel(
        game_color_row,
        text=game_status_text,
        font=("Arial", 10),
        text_color=game_status_color,
    )
    game_status.pack(side="left", padx=8)

    # Color preview for game loaded
    game_preview = ctk.CTkFrame(
        game_color_row, width=40, height=20, corner_radius=4, fg_color="#333333"
    )
    game_preview.pack(side="left", padx=5)
    if game_color_check.get("color_rgb"):
        r, g, b = game_color_check["color_rgb"]
        game_preview.configure(fg_color=f"#{r:02x}{g:02x}{b:02x}")

    # Store references
    app.auto_setup_game_loaded_color_btn = game_btn
    app.auto_setup_game_loaded_color_status = game_status
    app.auto_setup_game_loaded_color_preview = game_preview

    # Tolerance settings
    tolerance_row = ctk.CTkFrame(colors_frame, fg_color="transparent")
    tolerance_row.pack(fill="x", pady=5, padx=15)

    ctk.CTkLabel(
        tolerance_row,
        text="Color Match Tolerance:",
        font=("Arial", 11),
        width=200,
        anchor="w",
    ).pack(side="left")

    tolerance_container, app.auto_setup_color_tolerance_entry = (
        app.create_spinbox_entry(
            tolerance_row,
            app.auto_setup_menu_color_check.get("tolerance", 20),
            5,
            100,
            5,
            width=100,
            is_float=False,
        )
    )
    tolerance_container.pack(side="left", padx=5)

    ctk.CTkLabel(
        tolerance_row,
        text="(Lower = stricter match)",
        font=("Arial", 9),
        text_color="#888888",
    ).pack(side="left", padx=5)

    # Test Detection Button (single button for both colors)
    test_row = ctk.CTkFrame(colors_frame, fg_color="transparent")
    test_row.pack(fill="x", pady=(10, 5), padx=15)

    test_btn = ctk.CTkButton(
        test_row,
        text="🔍 Test Detection (Where am I now?)",
        command=app.test_auto_setup_detection,
        width=280,
        height=35,
        fg_color="#3a7ebf",
        hover_color="#2d6aa3",
        font=("Arial", 11, "bold"),
    )
    test_btn.pack(pady=5)

    # Detection result label
    app.auto_setup_detection_result = ctk.CTkLabel(
        test_row,
        text="",
        font=("Arial", 11, "bold"),
        text_color="#888888",
    )
    app.auto_setup_detection_result.pack(pady=5)

    # Spacer after colors
    ctk.CTkFrame(colors_frame, fg_color="transparent", height=8).pack()

    # ── Advanced Settings ──────────────────────────────────────────
    adv_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=8)
    adv_frame.pack(fill="x", pady=(0, 10), padx=10)

    ctk.CTkLabel(
        adv_frame,
        text="⚙️ TIMEOUTS & RETRIES",
        font=("Arial", 13, "bold"),
        text_color=app.fg_color,
    ).pack(pady=(10, 8))

    # Max retries
    retries_row = ctk.CTkFrame(adv_frame, fg_color="transparent")
    retries_row.pack(fill="x", padx=15, pady=3)
    ctk.CTkLabel(
        retries_row, text="Max Retries:", font=("Arial", 11), width=160, anchor="w"
    ).pack(side="left")
    retries_container, app.auto_setup_max_retries_entry = app.create_spinbox_entry(
        retries_row, app.auto_setup_max_retries, 1, 10, 1, width=100, is_float=False
    )
    retries_container.pack(side="left", padx=5)

    # Game open timeout
    open_row = ctk.CTkFrame(adv_frame, fg_color="transparent")
    open_row.pack(fill="x", padx=15, pady=3)
    ctk.CTkLabel(
        open_row,
        text="Game Open Timeout (s):",
        font=("Arial", 11),
        width=160,
        anchor="w",
    ).pack(side="left")
    open_container, app.auto_setup_game_open_timeout_entry = app.create_spinbox_entry(
        open_row,
        app.auto_setup_game_open_timeout,
        10,
        120,
        5,
        width=100,
        is_float=False,
    )
    open_container.pack(side="left", padx=5)

    # Game load timeout
    load_row = ctk.CTkFrame(adv_frame, fg_color="transparent")
    load_row.pack(fill="x", padx=15, pady=3)
    ctk.CTkLabel(
        load_row,
        text="Game Load Timeout (s):",
        font=("Arial", 11),
        width=160,
        anchor="w",
    ).pack(side="left")
    load_container, app.auto_setup_game_load_timeout_entry = app.create_spinbox_entry(
        load_row,
        app.auto_setup_game_load_timeout,
        10,
        180,
        5,
        width=100,
        is_float=False,
    )
    load_container.pack(side="left", padx=5)

    # Save button
    save_row = ctk.CTkFrame(adv_frame, fg_color="transparent")
    save_row.pack(fill="x", padx=15, pady=(8, 12))

    ctk.CTkButton(
        save_row,
        text="💾 Save Auto Setup Settings",
        command=app.save_auto_setup_settings_from_ui,
        width=220,
        height=32,
        fg_color=app.success_color,
        hover_color="#2bb87a",
        font=("Arial", 11, "bold"),
    ).pack()

    # ── Status Info ────────────────────────────────────────────────
    status_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=8)
    status_frame.pack(fill="x", pady=(0, 10), padx=10)

    ctk.CTkLabel(
        status_frame,
        text="ℹ️ HOW IT WORKS",
        font=("Arial", 13, "bold"),
        text_color=app.fg_color,
    ).pack(pady=(10, 5))

    steps_text = (
        "1. Set all 4 coordinates above\n"
        "2. Set Menu Color (detects when game opens)\n"
        "3. Set Game Loaded Color (detects when in-game)\n"
        "4. Paste your VIP server code\n"
        "5. Enable Auto Setup checkbox\n"
        "6. Press F1 → Auto Setup runs first, then macro starts\n"
        "\n"
        "Auto Setup opens browser → Play → waits for Menu Color\n"
        "→ presses Ctrl → Private Server → VIP code → Enter\n"
        "→ waits for Game Loaded Color → positions character → starts fishing"
    )
    ctk.CTkLabel(
        status_frame,
        text=steps_text,
        font=("Arial", 10),
        text_color="#aaaaaa",
        justify="left",
        anchor="w",
        wraplength=400,
    ).pack(pady=(0, 12), padx=15, anchor="w")

    app.auto_setup_status_label = ctk.CTkLabel(
        status_frame,
        text="Status: Idle",
        font=("Arial", 11),
        text_color="#888888",
    )
    app.auto_setup_status_label.pack(pady=(0, 12))
