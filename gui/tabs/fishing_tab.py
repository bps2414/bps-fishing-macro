# gui/tabs/fishing_tab.py
# Fishing Tab - Fishing End Delay, PD Controller
import customtkinter as ctk
import tkinter as tk


def build(app, parent):
    """Build the Fishing tab widgets.

    Args:
        app: FishingMacroGUI instance (self)
        parent: The tab frame to build into
    """
    # Fishing End Delay section
    fishing_delay_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
    fishing_delay_frame.pack(fill="x", pady=10)

    fishing_delay_title = ctk.CTkLabel(
        fishing_delay_frame,
        text="⏱️ FISHING END DELAY",
        font=("Arial", 14, "bold"),
        text_color=app.accent_color,
    )
    fishing_delay_title.pack(pady=(10, 10))

    delay_row = ctk.CTkFrame(fishing_delay_frame, fg_color="transparent")
    delay_row.pack(fill="x", pady=5, padx=15)
    ctk.CTkLabel(
        delay_row, text="End delay (s):", font=("Arial", 11), width=150, anchor="w"
    ).pack(side="left")
    delay_container, app.fishing_end_delay_entry = app.create_spinbox_entry(
        delay_row,
        app.fishing_end_delay,
        min_val=0.0,
        max_val=5.0,
        step=0.1,
        width=120,
    )
    delay_container.pack(side="left", padx=5)

    ctk.CTkLabel(
        fishing_delay_frame,
        text="Delay before ending fishing phase",
        font=("Arial", 9),
        text_color="#aaaaaa",
    ).pack(pady=(5, 5))

    # V3: Save button for fishing end delay
    save_fishing_delay_btn = ctk.CTkButton(
        fishing_delay_frame,
        text="Save End Delay",
        command=app.save_fishing_end_delay_from_ui,
        width=150,
        fg_color=app.accent_color,
        hover_color=app.hover_color,
        font=("Arial", 11, "bold"),
    )
    save_fishing_delay_btn.pack(pady=(5, 15))

    # PID Controller section
    pid_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
    pid_frame.pack(fill="x", pady=10)

    pid_title = ctk.CTkLabel(
        pid_frame,
        text="🎮 PD CONTROLLER",
        font=("Arial", 14, "bold"),
        text_color=app.accent_color,
    )
    pid_title.pack(pady=(10, 10))

    # Kp (Proportional gain)
    kp_row = ctk.CTkFrame(pid_frame, fg_color="transparent")
    kp_row.pack(fill="x", pady=5, padx=15)
    ctk.CTkLabel(
        kp_row, text="Kp (Proportional):", font=("Arial", 11), width=150, anchor="w"
    ).pack(side="left")
    kp_container, app.kp_entry = app.create_spinbox_entry(
        kp_row, app.pid_kp, min_val=0.0, max_val=10.0, step=0.1, width=120
    )
    kp_container.pack(side="left", padx=5)

    # Kd (Derivative gain)
    kd_row = ctk.CTkFrame(pid_frame, fg_color="transparent")
    kd_row.pack(fill="x", pady=5, padx=15)
    ctk.CTkLabel(
        kd_row, text="Kd (Derivative):", font=("Arial", 11), width=150, anchor="w"
    ).pack(side="left")
    kd_container, app.kd_entry = app.create_spinbox_entry(
        kd_row, app.pid_kd, min_val=0.0, max_val=5.0, step=0.05, width=120
    )
    kd_container.pack(side="left", padx=5)

    # Clamp (Output limit)
    clamp_row = ctk.CTkFrame(pid_frame, fg_color="transparent")
    clamp_row.pack(fill="x", pady=5, padx=15)
    ctk.CTkLabel(
        clamp_row,
        text="PD Clamp (Limit):",
        font=("Arial", 11),
        width=150,
        anchor="w",
    ).pack(side="left")
    clamp_container, app.clamp_entry = app.create_spinbox_entry(
        clamp_row,
        app.pid_clamp,
        min_val=1,
        max_val=100,
        step=5,
        is_float=False,
        width=120,
    )
    clamp_container.pack(side="left", padx=5)

    # Save button
    save_btn_row = ctk.CTkFrame(pid_frame, fg_color="transparent")
    save_btn_row.pack(fill="x", pady=10, padx=15)
    ctk.CTkButton(
        save_btn_row,
        text="💾 Save PD Settings",
        command=app.save_pid_from_ui,
        width=200,
        fg_color=app.accent_color,
        hover_color=app.hover_color,
        font=("Arial", 12, "bold"),
    ).pack()

    # Info label for PID
    ctk.CTkLabel(
        pid_frame,
        text="Default: Kp=1.0, Kd=0.3, Clamp=1.0",
        font=("Arial", 9),
        text_color="#aaaaaa",
    ).pack(pady=(5, 15))
