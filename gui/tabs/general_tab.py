# gui/tabs/general_tab.py
# General Tab - Always on Top, Status, Hotkeys, Item Hotkeys, HUD Settings
import customtkinter as ctk
import tkinter as tk


def build(app, parent):
    """Build the General tab widgets.

    Args:
        app: FishingMacroGUI instance (self)
        parent: The tab frame to build into
    """
    # Settings toggles
    settings_frame = ctk.CTkFrame(parent, fg_color="transparent")
    settings_frame.pack(fill="x", pady=10)

    app.always_on_top_var = tk.BooleanVar(value=app.always_on_top)
    always_on_top_check = ctk.CTkCheckBox(
        settings_frame,
        text="Always on Top",
        variable=app.always_on_top_var,
        command=app.toggle_always_on_top,
        fg_color=app.success_color,
        hover_color=app.hover_color,
        font=("Segoe UI", 11),
    )
    always_on_top_check.pack(side="left", padx=10)

    # Status frame
    status_frame = ctk.CTkFrame(parent, fg_color=app.button_color, corner_radius=8)
    status_frame.pack(fill="x", pady=8)

    status_title = ctk.CTkLabel(
        status_frame,
        text="Status",
        font=("Segoe UI", 12, "bold"),
        text_color=app.fg_color,
    )
    status_title.pack(pady=(8, 4))

    app.status_label = ctk.CTkLabel(
        status_frame,
        text="Status: STOPPED",
        font=("Arial", 13, "bold"),
        text_color="#ff4444",
    )
    app.status_label.pack(pady=5)

    app.activity_label = ctk.CTkLabel(
        status_frame,
        text="Activity: Idle",
        font=("Arial", 11),
        text_color="#00ccff",
    )
    app.activity_label.pack(pady=(5, 10))

    # Controls frame
    controls_frame = ctk.CTkFrame(parent, fg_color=app.button_color, corner_radius=8)
    controls_frame.pack(fill="both", expand=True, pady=8)

    controls_title = ctk.CTkLabel(
        controls_frame,
        text="Hotkeys",
        font=("Segoe UI", 12, "bold"),
        text_color=app.fg_color,
    )
    controls_title.pack(pady=(8, 10))

    # Start/Stop row
    start_row = ctk.CTkFrame(controls_frame, fg_color="transparent")
    start_row.pack(fill="x", padx=15, pady=8)

    ctk.CTkLabel(
        start_row,
        text="▶ Start/Stop",
        font=("Arial", 12, "bold"),
        width=120,
        anchor="w",
    ).pack(side="left", padx=5)
    app.start_button = ctk.CTkButton(
        start_row,
        text="START",
        command=app.toggle_start,
        width=100,
        fg_color="#00aa00",
        hover_color="#00dd00",
        font=("Arial", 12, "bold"),
    )
    app.start_button.pack(side="left", padx=8)
    app.start_hotkey_label = ctk.CTkLabel(
        start_row,
        text="[F1]",
        font=("Arial", 11, "bold"),
        text_color=app.accent_color,
        width=60,
    )
    app.start_hotkey_label.pack(side="left", padx=5)
    ctk.CTkButton(
        start_row,
        text="🔧 Rebind",
        command=lambda: app.start_rebind("start"),
        width=90,
        fg_color=app.button_color,
        hover_color=app.hover_color,
    ).pack(side="left")

    # Change Area row
    area_row = ctk.CTkFrame(controls_frame, fg_color="transparent")
    area_row.pack(fill="x", padx=15, pady=8)

    ctk.CTkLabel(
        area_row,
        text="🎯 Change Area",
        font=("Arial", 12, "bold"),
        width=120,
        anchor="w",
    ).pack(side="left", padx=5)
    app.area_button = ctk.CTkButton(
        area_row,
        text="OFF",
        command=app.toggle_area,
        width=100,
        fg_color="#666666",
        hover_color="#888888",
        font=("Arial", 12, "bold"),
    )
    app.area_button.pack(side="left", padx=8)
    app.area_hotkey_label = ctk.CTkLabel(
        area_row,
        text="[F2]",
        font=("Arial", 11, "bold"),
        text_color=app.accent_color,
        width=60,
    )
    app.area_hotkey_label.pack(side="left", padx=5)
    ctk.CTkButton(
        area_row,
        text="🔧 Rebind",
        command=lambda: app.start_rebind("area"),
        width=90,
        fg_color=app.button_color,
        hover_color=app.hover_color,
    ).pack(side="left")

    # Exit row
    exit_row = ctk.CTkFrame(controls_frame, fg_color="transparent")
    exit_row.pack(fill="x", padx=15, pady=8)

    ctk.CTkLabel(
        exit_row, text="❌ Exit", font=("Arial", 12, "bold"), width=120, anchor="w"
    ).pack(side="left", padx=5)
    app.exit_button = ctk.CTkButton(
        exit_row,
        text="EXIT",
        command=app.force_exit,
        width=100,
        fg_color="#cc0000",
        hover_color="#ff4444",
        font=("Arial", 12, "bold"),
    )
    app.exit_button.pack(side="left", padx=8)
    app.exit_hotkey_label = ctk.CTkLabel(
        exit_row,
        text="[F3]",
        font=("Arial", 11, "bold"),
        text_color=app.accent_color,
        width=60,
    )
    app.exit_hotkey_label.pack(side="left", padx=5)
    ctk.CTkButton(
        exit_row,
        text="🔧 Rebind",
        command=lambda: app.start_rebind("exit"),
        width=90,
        fg_color=app.button_color,
        hover_color=app.hover_color,
    ).pack(side="left")

    # Pause row
    pause_row = ctk.CTkFrame(controls_frame, fg_color="transparent")
    pause_row.pack(fill="x", padx=15, pady=(8, 15))

    ctk.CTkLabel(
        pause_row, text="⏸ Pause", font=("Arial", 12, "bold"), width=120, anchor="w"
    ).pack(side="left", padx=5)
    app.pause_label = ctk.CTkLabel(
        pause_row,
        text="(F4 during run)",
        font=("Arial", 11),
        width=100,
        text_color="#888888",
    )
    app.pause_label.pack(side="left", padx=8)
    app.pause_hotkey_label = ctk.CTkLabel(
        pause_row,
        text="[F4]",
        font=("Arial", 11, "bold"),
        text_color=app.accent_color,
        width=60,
    )
    app.pause_hotkey_label.pack(side="left", padx=5)
    ctk.CTkButton(
        pause_row,
        text="🔧 Rebind",
        command=lambda: app.start_rebind("pause"),
        width=90,
        fg_color=app.button_color,
        hover_color=app.hover_color,
    ).pack(side="left")

    # Item Hotkeys section
    item_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
    item_frame.pack(fill="x", pady=10)

    item_title = ctk.CTkLabel(
        item_frame,
        text="🎣 ITEM HOTKEYS (1-10)",
        font=("Arial", 14, "bold"),
        text_color=app.accent_color,
    )
    item_title.pack(pady=(10, 15))

    # Rod hotkey row
    rod_row = ctk.CTkFrame(item_frame, fg_color="transparent")
    rod_row.pack(fill="x", padx=15, pady=5)
    ctk.CTkLabel(
        rod_row, text="🎣 Rod", font=("Arial", 12, "bold"), width=150, anchor="w"
    ).pack(side="left")
    app.rod_hotkey_var = tk.StringVar(value=app.rod_hotkey)
    rod_combo = ctk.CTkComboBox(
        rod_row,
        variable=app.rod_hotkey_var,
        values=[str(i) for i in range(1, 11)],
        width=80,
        state="readonly",
        fg_color=app.button_color,
        button_color=app.accent_color,
        button_hover_color=app.hover_color,
        command=lambda e: app.save_item_hotkeys(),
    )
    rod_combo.pack(side="left", padx=8)

    # Everything else hotkey row
    everything_row = ctk.CTkFrame(item_frame, fg_color="transparent")
    everything_row.pack(fill="x", padx=15, pady=5)
    ctk.CTkLabel(
        everything_row,
        text="📦 Everything Else",
        font=("Arial", 12, "bold"),
        width=150,
        anchor="w",
    ).pack(side="left")
    app.everything_else_hotkey_var = tk.StringVar(value=app.everything_else_hotkey)
    everything_combo = ctk.CTkComboBox(
        everything_row,
        variable=app.everything_else_hotkey_var,
        values=[str(i) for i in range(1, 11)],
        width=80,
        state="readonly",
        fg_color=app.button_color,
        button_color=app.accent_color,
        button_hover_color=app.hover_color,
        command=lambda e: app.save_item_hotkeys(),
    )
    everything_combo.pack(side="left", padx=8)

    # HUD Position selector
    hud_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
    hud_frame.pack(fill="x", pady=10)

    hud_title = ctk.CTkLabel(
        hud_frame,
        text="📊 HUD SETTINGS",
        font=("Arial", 14, "bold"),
        text_color=app.accent_color,
    )
    hud_title.pack(pady=(10, 15))

    hud_pos_row = ctk.CTkFrame(hud_frame, fg_color="transparent")
    hud_pos_row.pack(fill="x", padx=15, pady=(5, 15))
    ctk.CTkLabel(
        hud_pos_row,
        text="HUD Position:",
        font=("Arial", 12, "bold"),
        width=150,
        anchor="w",
    ).pack(side="left")
    app.hud_position_var = tk.StringVar(
        value=app.hud_position.title().replace("-", " ")
    )
    hud_combo = ctk.CTkComboBox(
        hud_pos_row,
        variable=app.hud_position_var,
        values=["Top", "Bottom Left", "Bottom Right"],
        width=150,
        state="readonly",
        fg_color=app.button_color,
        button_color=app.accent_color,
        button_hover_color=app.hover_color,
        command=lambda e: app.save_hud_position(),
    )
    hud_combo.pack(side="left", padx=5)

    # Info label
    app.info_label = ctk.CTkLabel(
        parent,
        text="✓ Ready to fish!",
        font=("Arial", 11, "bold"),
        text_color="#00dd00",
    )
    app.info_label.pack(pady=10)
