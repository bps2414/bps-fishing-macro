# gui/tabs/stats_tab.py
# Stats Tab - Today Stats, 7-Day History, Export/Import
import customtkinter as ctk
import tkinter as tk


def build(app, parent):
    """Build the Stats tab widgets.

    Args:
        app: FishingMacroGUI instance (self)
        parent: The tab frame to build into
    """
    # Today section
    today_frame = ctk.CTkFrame(parent, fg_color=app.button_color, corner_radius=8)
    today_frame.pack(fill="x", pady=8, padx=5)

    ctk.CTkLabel(
        today_frame,
        text="Today",
        font=("Segoe UI", 12, "bold"),
        text_color=app.fg_color,
    ).pack(anchor="w", padx=12, pady=(10, 6))

    # Today stats grid
    today_stats = ctk.CTkFrame(today_frame, fg_color="transparent")
    today_stats.pack(fill="x", padx=12, pady=(0, 12))

    for i in range(4):
        today_stats.grid_columnconfigure(i, weight=1)

    # Labels for today stats
    app.today_sessions_label = ctk.CTkLabel(
        today_stats, text="0", font=("Segoe UI", 16, "bold")
    )
    app.today_sessions_label.grid(row=0, column=0, padx=5)
    ctk.CTkLabel(
        today_stats, text="Sessions", font=("Segoe UI", 9), text_color=app.fg_color
    ).grid(row=1, column=0)

    app.today_fish_label = ctk.CTkLabel(
        today_stats, text="0", font=("Segoe UI", 16, "bold")
    )
    app.today_fish_label.grid(row=0, column=1, padx=5)
    ctk.CTkLabel(
        today_stats, text="Fish", font=("Segoe UI", 9), text_color=app.fg_color
    ).grid(row=1, column=1)

    app.today_fruits_label = ctk.CTkLabel(
        today_stats, text="0", font=("Segoe UI", 16, "bold")
    )
    app.today_fruits_label.grid(row=0, column=2, padx=5)
    ctk.CTkLabel(
        today_stats, text="Fruits", font=("Segoe UI", 9), text_color=app.fg_color
    ).grid(row=1, column=2)

    app.today_rate_label = ctk.CTkLabel(
        today_stats, text="0/h", font=("Segoe UI", 16, "bold")
    )
    app.today_rate_label.grid(row=0, column=3, padx=5)
    ctk.CTkLabel(
        today_stats, text="Rate", font=("Segoe UI", 9), text_color=app.fg_color
    ).grid(row=1, column=3)

    # History section
    history_frame = ctk.CTkFrame(parent, fg_color=app.button_color, corner_radius=8)
    history_frame.pack(fill="both", expand=True, pady=8, padx=5)

    ctk.CTkLabel(
        history_frame,
        text="Last 7 Days",
        font=("Segoe UI", 12, "bold"),
        text_color=app.fg_color,
    ).pack(anchor="w", padx=12, pady=(10, 6))

    # History table header
    history_header = ctk.CTkFrame(history_frame, fg_color="transparent")
    history_header.pack(fill="x", padx=12)
    ctk.CTkLabel(
        history_header,
        text="Date",
        width=100,
        anchor="w",
        font=("Segoe UI", 10, "bold"),
    ).pack(side="left")
    ctk.CTkLabel(
        history_header, text="Fish", width=60, font=("Segoe UI", 10, "bold")
    ).pack(side="left")
    ctk.CTkLabel(
        history_header, text="Fruits", width=60, font=("Segoe UI", 10, "bold")
    ).pack(side="left")

    # History rows container
    app.history_container = ctk.CTkFrame(history_frame, fg_color="transparent")
    app.history_container.pack(fill="both", expand=True, padx=12, pady=(4, 12))

    # Export button
    export_frame = ctk.CTkFrame(parent, fg_color="transparent")
    export_frame.pack(fill="x", pady=8, padx=5)

    ctk.CTkButton(
        export_frame,
        text="Export CSV",
        command=app.export_stats_csv,
        width=100,
        fg_color=app.button_color,
        hover_color=app.hover_color,
    ).pack(side="left", padx=5)

    ctk.CTkButton(
        export_frame,
        text="Refresh",
        command=app.refresh_stats_display,
        width=80,
        fg_color=app.button_color,
        hover_color=app.hover_color,
    ).pack(side="left", padx=5)

    # V3.1: Export/Import Config buttons
    config_frame = ctk.CTkFrame(parent, fg_color="transparent")
    config_frame.pack(fill="x", pady=8, padx=5)

    ctk.CTkLabel(
        config_frame,
        text="⚙️ Configuration:",
        font=("Segoe UI", 10, "bold"),
        text_color=app.fg_color,
    ).pack(side="left", padx=5)

    ctk.CTkButton(
        config_frame,
        text="📤 Export Config",
        command=app.export_config,
        width=120,
        fg_color="#00aa88",
        hover_color="#00cc99",
    ).pack(side="left", padx=5)

    ctk.CTkButton(
        config_frame,
        text="📥 Import Config",
        command=app.import_config,
        width=120,
        fg_color="#aa8800",
        hover_color="#cc9900",
    ).pack(side="left", padx=5)

    # Initial load of stats
    app.refresh_stats_display()
