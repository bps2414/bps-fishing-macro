# gui/tabs/webhook_tab.py
# Webhooks Tab - Discord Webhook, User ID, Legendary Filter, Pity Zone
import customtkinter as ctk
import tkinter as tk


def build(app, parent):
    """Build the Webhooks tab widgets.

    Args:
        app: FishingMacroGUI instance (self)
        parent: The tab frame to build into
    """
    # Load webhook settings
    webhook_settings = app.settings.load_webhook_settings()

    # Discord Webhook URL row
    webhook_url_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
    webhook_url_frame.pack(fill="x", pady=10)

    webhook_title = ctk.CTkLabel(
        webhook_url_frame,
        text="🔔 DISCORD WEBHOOK",
        font=("Arial", 14, "bold"),
        text_color=app.accent_color,
    )
    webhook_title.pack(pady=(10, 10))

    ctk.CTkLabel(
        webhook_url_frame, text="Webhook URL:", font=("Arial", 11, "bold")
    ).pack(fill="x", pady=5, padx=15)
    app.webhook_url_entry = ctk.CTkEntry(
        webhook_url_frame,
        width=500,
        fg_color=app.button_color,
        border_color=app.accent_color,
        placeholder_text="https://discord.com/api/webhooks/...",
    )
    webhook_url = webhook_settings.get("webhook_url", "")
    if webhook_url:
        app.webhook_url_entry.insert(0, webhook_url)
    app.webhook_url_entry.pack(fill="x", pady=(5, 15), padx=15)

    # User ID row
    user_id_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
    user_id_frame.pack(fill="x", pady=10)

    user_id_title = ctk.CTkLabel(
        user_id_frame,
        text="👤 USER ID",
        font=("Arial", 14, "bold"),
        text_color=app.accent_color,
    )
    user_id_title.pack(pady=(10, 10))

    ctk.CTkLabel(
        user_id_frame, text="Discord User ID:", font=("Arial", 11, "bold")
    ).pack(fill="x", pady=5, padx=15)
    app.user_id_entry = ctk.CTkEntry(
        user_id_frame,
        width=300,
        fg_color=app.button_color,
        border_color=app.accent_color,
    )
    app.user_id_entry.insert(0, webhook_settings.get("user_id", ""))
    app.user_id_entry.pack(fill="x", pady=(5, 15), padx=15)

    # Legendary/Mythical fruit filter section
    legendary_filter_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
    legendary_filter_frame.pack(fill="x", pady=10)

    legendary_filter_title = ctk.CTkLabel(
        legendary_filter_frame,
        text="⭐ LEGENDARY/MYTHICAL FILTER",
        font=("Arial", 14, "bold"),
        text_color=app.accent_color,
    )
    legendary_filter_title.pack(pady=(10, 10))

    # Only notify legendary checkbox
    app.webhook_only_legendary_var = tk.BooleanVar(value=app.webhook_only_legendary)
    legendary_checkbox = ctk.CTkCheckBox(
        legendary_filter_frame,
        text="Only notify for Legendary/Mythical fruits",
        variable=app.webhook_only_legendary_var,
        command=app.toggle_webhook_legendary_filter,
        fg_color=app.accent_color,
        hover_color=app.hover_color,
        font=("Arial", 11, "bold"),
    )
    legendary_checkbox.pack(pady=5, padx=15)

    ctk.CTkLabel(
        legendary_filter_frame,
        text="When enabled, scans pity counter to detect LEGENDARY PITY 0/40",
        font=("Arial", 9),
        text_color="#aaaaaa",
    ).pack(pady=(0, 5), padx=15)

    # Pity zone configuration (shown only when filter enabled)
    app.pity_zone_section = ctk.CTkFrame(legendary_filter_frame, fg_color="transparent")
    if app.webhook_only_legendary:
        app.pity_zone_section.pack(fill="x", pady=5, padx=15)

    pity_zone_row = ctk.CTkFrame(app.pity_zone_section, fg_color="transparent")
    pity_zone_row.pack(fill="x", pady=5)
    ctk.CTkLabel(
        pity_zone_row,
        text="📋 Pity Counter Zone:",
        font=("Arial", 11, "bold"),
        width=150,
        anchor="w",
    ).pack(side="left")
    app.pity_zone_btn = ctk.CTkButton(
        pity_zone_row,
        text="Select Zone",
        command=app.start_pity_zone_selection,
        width=100,
        fg_color=app.button_color,
        hover_color=app.hover_color,
    )
    app.pity_zone_btn.pack(side="left", padx=5)

    zone_text = "Not Set"
    zone_color = "#ff4444"
    if app.webhook_pity_zone:
        z = app.webhook_pity_zone
        zone_text = f"({z['x']}, {z['y']}) {z['width']}x{z['height']}"
        zone_color = "#00dd00"
    app.pity_zone_label = ctk.CTkLabel(
        pity_zone_row, text=zone_text, font=("Arial", 10), text_color=zone_color
    )
    app.pity_zone_label.pack(side="left", padx=5)

    # Result label for test
    pity_test_result_row = ctk.CTkFrame(app.pity_zone_section, fg_color="transparent")
    pity_test_result_row.pack(fill="x", pady=5)
    app.pity_test_result_label = ctk.CTkLabel(
        pity_test_result_row,
        text="",
        font=("Arial", 10),
        wraplength=600,
        justify="left",
        anchor="w",
    )
    app.pity_test_result_label.pack(side="left", padx=15, fill="x", expand=True)

    # Botão de teste do filtro pity fish
    pity_test_button_row = ctk.CTkFrame(app.pity_zone_section, fg_color="transparent")
    pity_test_button_row.pack(fill="x", pady=2)
    ctk.CTkButton(
        pity_test_button_row,
        text="🧪 Testar Filtro Pity Fish (Discord)",
        command=app.test_pity_fish_webhook,
        width=260,
        fg_color="#00aaff",
        hover_color="#0088cc",
        font=("Arial", 11, "bold"),
    ).pack(side="left", padx=5)

    ctk.CTkLabel(
        app.pity_zone_section,
        text="Draw rectangle around pity counter text area (e.g., 'LEGENDARY PITY 0/40')",
        font=("Arial", 9),
        text_color="#00ccff",
    ).pack(pady=(5, 10), padx=15)

    # Buttons frame
    buttons_frame = ctk.CTkFrame(parent, fg_color="transparent")
    buttons_frame.pack(fill="x", pady=15)

    ctk.CTkButton(
        buttons_frame,
        text="🧪 Test Webhook",
        command=app.test_webhook,
        width=180,
        fg_color="#00aaff",
        hover_color="#0088cc",
        font=("Arial", 12, "bold"),
    ).pack(side="left", padx=5)
    ctk.CTkButton(
        buttons_frame,
        text="💾 Save Webhook Settings",
        command=app.save_webhook_settings_ui,
        width=200,
        fg_color=app.accent_color,
        hover_color=app.hover_color,
        font=("Arial", 12, "bold"),
    ).pack(side="left", padx=5)
