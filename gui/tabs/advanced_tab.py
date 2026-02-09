# gui/tabs/advanced_tab.py
# Advanced Tab - Camera, Zoom, Pre-Cast Delays, Detection Delays
import customtkinter as ctk
import tkinter as tk


def build(app, parent):
    """Build the Advanced Settings tab widgets.

    Args:
        app: FishingMacroGUI instance (self)
        parent: The tab frame to build into
    """
    # Warning label
    warning_frame = ctk.CTkFrame(parent, fg_color="transparent")
    warning_frame.pack(fill="x", pady=10)
    ctk.CTkLabel(
        warning_frame,
        text="⚠️ WARNING: Advanced Settings ⚠️",
        font=("Arial", 12, "bold"),
        text_color="#ff4444",
    ).pack()
    ctk.CTkLabel(
        warning_frame,
        text="Only modify if you know what you're doing! Incorrect values may cause malfunction.",
        font=("Arial", 9),
        text_color="#ffaa00",
    ).pack(pady=5)

    # Checkbox to disable rotation/zoom/camera in normal mode
    disable_camera_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
    disable_camera_frame.pack(fill="x", pady=8)

    disable_camera_title = ctk.CTkLabel(
        disable_camera_frame,
        text="🎮 NORMAL MODE - CAMERA",
        font=("Arial", 13, "bold"),
        text_color=app.accent_color,
    )
    disable_camera_title.pack(pady=(10, 5))

    disable_normal_camera_row = ctk.CTkFrame(
        disable_camera_frame, fg_color="transparent"
    )
    disable_normal_camera_row.pack(fill="x", pady=(5, 10), padx=15)
    app.disable_normal_camera_var = ctk.BooleanVar(value=app.disable_normal_camera)
    disable_normal_camera_checkbox = ctk.CTkCheckBox(
        disable_normal_camera_row,
        text="Disable rotation/zoom/camera in normal mode",
        variable=app.disable_normal_camera_var,
        command=app.save_disable_normal_camera,
        fg_color=app.accent_color,
        hover_color=app.hover_color,
        font=("Arial", 11),
    )
    disable_normal_camera_checkbox.pack(side="left")
    ctk.CTkLabel(
        disable_normal_camera_row,
        text="(Does not affect Auto Craft)",
        font=("Arial", 9),
        text_color="#00ccff",
    ).pack(side="left", padx=8)

    ctk.CTkLabel(
        disable_camera_frame,
        text="When enabled: Disables 180° rotation, zoom in/out and camera initialization in normal mode.",
        font=("Arial", 9),
        text_color="#aaaaaa",
    ).pack(pady=(0, 10), padx=15)

    # Camera Rotation Settings
    camera_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
    camera_frame.pack(fill="x", pady=8)

    camera_title = ctk.CTkLabel(
        camera_frame,
        text="📷 CAMERA ROTATION DELAYS",
        font=("Arial", 13, "bold"),
        text_color=app.accent_color,
    )
    camera_title.pack(pady=(10, 10))

    # Camera rotation delay
    cam_delay_row = ctk.CTkFrame(camera_frame, fg_color="transparent")
    cam_delay_row.pack(fill="x", pady=4, padx=15)
    ctk.CTkLabel(
        cam_delay_row,
        text="Initial delay before rotation (s):",
        font=("Arial", 10),
        width=280,
        anchor="w",
    ).pack(side="left")
    cam_delay_container, app.camera_rotation_delay_entry = app.create_spinbox_entry(
        cam_delay_row,
        app.camera_rotation_delay,
        min_val=0.0,
        max_val=2.0,
        step=0.05,
        width=80,
    )
    cam_delay_container.pack(side="left", padx=5)
    ctk.CTkLabel(
        cam_delay_row, text="Default: 0.05", font=("Arial", 9), text_color="#00ccff"
    ).pack(side="left", padx=5)

    # Camera rotation steps
    cam_steps_row = ctk.CTkFrame(camera_frame, fg_color="transparent")
    cam_steps_row.pack(fill="x", pady=4, padx=15)
    ctk.CTkLabel(
        cam_steps_row,
        text="Number of rotation steps:",
        font=("Arial", 10),
        width=280,
        anchor="w",
    ).pack(side="left")
    cam_steps_container, app.camera_rotation_steps_entry = app.create_spinbox_entry(
        cam_steps_row,
        app.camera_rotation_steps,
        min_val=1,
        max_val=20,
        step=1,
        is_float=False,
        width=80,
    )
    cam_steps_container.pack(side="left", padx=5)
    ctk.CTkLabel(
        cam_steps_row,
        text="Default: 8 (8x100px = 800px total)",
        font=("Arial", 9),
        text_color="#00ccff",
    ).pack(side="left", padx=5)

    # Camera rotation step delay
    cam_step_delay_row = ctk.CTkFrame(camera_frame, fg_color="transparent")
    cam_step_delay_row.pack(fill="x", pady=4, padx=15)
    ctk.CTkLabel(
        cam_step_delay_row,
        text="Delay between each step (s):",
        font=("Arial", 10),
        width=280,
        anchor="w",
    ).pack(side="left")
    cam_step_delay_container, app.camera_rotation_step_delay_entry = (
        app.create_spinbox_entry(
            cam_step_delay_row,
            app.camera_rotation_step_delay,
            min_val=0.0,
            max_val=1.0,
            step=0.01,
            width=80,
        )
    )
    cam_step_delay_container.pack(side="left", padx=5)
    ctk.CTkLabel(
        cam_step_delay_row,
        text="Default: 0.05",
        font=("Arial", 9),
        text_color="#00ccff",
    ).pack(side="left", padx=5)

    # Camera rotation settle delay
    cam_settle_row = ctk.CTkFrame(camera_frame, fg_color="transparent")
    cam_settle_row.pack(fill="x", pady=(4, 15), padx=15)
    ctk.CTkLabel(
        cam_settle_row,
        text="Delay after completing rotation (s):",
        font=("Arial", 10),
        width=280,
        anchor="w",
    ).pack(side="left")
    cam_settle_container, app.camera_rotation_settle_delay_entry = (
        app.create_spinbox_entry(
            cam_settle_row,
            app.camera_rotation_settle_delay,
            min_val=0.0,
            max_val=2.0,
            step=0.05,
            width=80,
        )
    )
    cam_settle_container.pack(side="left", padx=5)
    ctk.CTkLabel(
        cam_settle_row, text="Default: 0.3", font=("Arial", 9), text_color="#00ccff"
    ).pack(side="left", padx=5)

    # Zoom Settings
    zoom_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
    zoom_frame.pack(fill="x", pady=8)

    zoom_title = ctk.CTkLabel(
        zoom_frame,
        text="🔍 ZOOM DELAYS",
        font=("Arial", 13, "bold"),
        text_color=app.accent_color,
    )
    zoom_title.pack(pady=(10, 10))

    # Zoom ticks
    zoom_ticks_row = ctk.CTkFrame(zoom_frame, fg_color="transparent")
    zoom_ticks_row.pack(fill="x", pady=4, padx=15)
    ctk.CTkLabel(
        zoom_ticks_row,
        text="Number of zoom ticks:",
        font=("Arial", 10),
        width=280,
        anchor="w",
    ).pack(side="left")
    zoom_ticks_container, app.zoom_ticks_entry = app.create_spinbox_entry(
        zoom_ticks_row,
        app.zoom_ticks,
        min_val=1,
        max_val=20,
        step=1,
        is_float=False,
        width=80,
    )
    zoom_ticks_container.pack(side="left", padx=5)
    ctk.CTkLabel(
        zoom_ticks_row, text="Default: 3", font=("Arial", 9), text_color="#00ccff"
    ).pack(side="left", padx=5)

    # Zoom tick delay
    zoom_tick_delay_row = ctk.CTkFrame(zoom_frame, fg_color="transparent")
    zoom_tick_delay_row.pack(fill="x", pady=4, padx=15)
    ctk.CTkLabel(
        zoom_tick_delay_row,
        text="Delay between each zoom tick (s):",
        font=("Arial", 10),
        width=280,
        anchor="w",
    ).pack(side="left")
    zoom_tick_delay_container, app.zoom_tick_delay_entry = app.create_spinbox_entry(
        zoom_tick_delay_row,
        app.zoom_tick_delay,
        min_val=0.0,
        max_val=0.5,
        step=0.01,
        width=80,
    )
    zoom_tick_delay_container.pack(side="left", padx=5)
    ctk.CTkLabel(
        zoom_tick_delay_row,
        text="Default: 0.05",
        font=("Arial", 9),
        text_color="#00ccff",
    ).pack(side="left", padx=5)

    # Zoom settle delay
    zoom_settle_row = ctk.CTkFrame(zoom_frame, fg_color="transparent")
    zoom_settle_row.pack(fill="x", pady=(4, 15), padx=15)
    ctk.CTkLabel(
        zoom_settle_row,
        text="Delay after completing zoom (s):",
        font=("Arial", 10),
        width=280,
        anchor="w",
    ).pack(side="left")
    app.zoom_settle_delay_entry = ctk.CTkEntry(
        zoom_settle_row,
        width=80,
        fg_color=app.button_color,
        border_color=app.accent_color,
    )
    app.zoom_settle_delay_entry.insert(0, str(app.zoom_settle_delay))
    app.zoom_settle_delay_entry.pack(side="left", padx=5)
    ctk.CTkLabel(
        zoom_settle_row,
        text="Default: 0.3",
        font=("Arial", 9),
        text_color="#00ccff",
    ).pack(side="left", padx=5)

    # Pre-Cast Delays
    precast_delays_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
    precast_delays_frame.pack(fill="x", pady=8)

    precast_title = ctk.CTkLabel(
        precast_delays_frame,
        text="🎣 PRE-CAST ACTION DELAYS",
        font=("Arial", 13, "bold"),
        text_color=app.accent_color,
    )
    precast_title.pack(pady=(10, 10))

    # Minigame wait
    minigame_wait_row = ctk.CTkFrame(precast_delays_frame, fg_color="transparent")
    minigame_wait_row.pack(fill="x", pady=4, padx=15)
    ctk.CTkLabel(
        minigame_wait_row,
        text="Wait for minigame to appear (s):",
        font=("Arial", 10),
        width=280,
        anchor="w",
    ).pack(side="left")
    app.pre_cast_minigame_wait_entry = ctk.CTkEntry(
        minigame_wait_row,
        width=80,
        fg_color=app.button_color,
        border_color=app.accent_color,
    )
    app.pre_cast_minigame_wait_entry.insert(0, str(app.pre_cast_minigame_wait))
    app.pre_cast_minigame_wait_entry.pack(side="left", padx=5)
    ctk.CTkLabel(
        minigame_wait_row,
        text="Default: 2.5 (prevents premature detection)",
        font=("Arial", 9),
        text_color="#00ccff",
    ).pack(side="left", padx=5)

    # Store click delay
    store_delay_row = ctk.CTkFrame(precast_delays_frame, fg_color="transparent")
    store_delay_row.pack(fill="x", pady=4, padx=15)
    ctk.CTkLabel(
        store_delay_row,
        text="Delay after clicking store (s):",
        font=("Arial", 10),
        width=280,
        anchor="w",
    ).pack(side="left")
    app.store_click_delay_entry = ctk.CTkEntry(
        store_delay_row,
        width=80,
        fg_color=app.button_color,
        border_color=app.accent_color,
    )
    app.store_click_delay_entry.insert(0, str(app.store_click_delay))
    app.store_click_delay_entry.pack(side="left", padx=5)
    ctk.CTkLabel(
        store_delay_row,
        text="Default: 1.0",
        font=("Arial", 9),
        text_color="#00ccff",
    ).pack(side="left", padx=5)

    # Backspace delay
    backspace_delay_row = ctk.CTkFrame(precast_delays_frame, fg_color="transparent")
    backspace_delay_row.pack(fill="x", pady=4, padx=15)
    ctk.CTkLabel(
        backspace_delay_row,
        text="Delay after pressing backspace (s):",
        font=("Arial", 10),
        width=280,
        anchor="w",
    ).pack(side="left")
    app.backspace_delay_entry = ctk.CTkEntry(
        backspace_delay_row,
        width=80,
        fg_color=app.button_color,
        border_color=app.accent_color,
    )
    app.backspace_delay_entry.insert(0, str(app.backspace_delay))
    app.backspace_delay_entry.pack(side="left", padx=5)
    ctk.CTkLabel(
        backspace_delay_row,
        text="Default: 0.3",
        font=("Arial", 9),
        text_color="#00ccff",
    ).pack(side="left", padx=5)

    # Rod deselect delay
    rod_deselect_row = ctk.CTkFrame(precast_delays_frame, fg_color="transparent")
    rod_deselect_row.pack(fill="x", pady=4, padx=15)
    ctk.CTkLabel(
        rod_deselect_row,
        text="Delay after deselecting rod (s):",
        font=("Arial", 10),
        width=280,
        anchor="w",
    ).pack(side="left")
    app.rod_deselect_delay_entry = ctk.CTkEntry(
        rod_deselect_row,
        width=80,
        fg_color=app.button_color,
        border_color=app.accent_color,
    )
    app.rod_deselect_delay_entry.insert(0, str(app.rod_deselect_delay))
    app.rod_deselect_delay_entry.pack(side="left", padx=5)
    ctk.CTkLabel(
        rod_deselect_row,
        text="Default: 0.5",
        font=("Arial", 9),
        text_color="#00ccff",
    ).pack(side="left", padx=5)

    # Rod select delay
    rod_select_row = ctk.CTkFrame(precast_delays_frame, fg_color="transparent")
    rod_select_row.pack(fill="x", pady=4, padx=15)
    ctk.CTkLabel(
        rod_select_row,
        text="Delay after selecting rod (s):",
        font=("Arial", 10),
        width=280,
        anchor="w",
    ).pack(side="left")
    app.rod_select_delay_entry = ctk.CTkEntry(
        rod_select_row,
        width=80,
        fg_color=app.button_color,
        border_color=app.accent_color,
    )
    app.rod_select_delay_entry.insert(0, str(app.rod_select_delay))
    app.rod_select_delay_entry.pack(side="left", padx=5)
    ctk.CTkLabel(
        rod_select_row, text="Default: 0.5", font=("Arial", 9), text_color="#00ccff"
    ).pack(side="left", padx=5)

    # Bait click delay
    bait_delay_row = ctk.CTkFrame(precast_delays_frame, fg_color="transparent")
    bait_delay_row.pack(fill="x", pady=(4, 15), padx=15)
    ctk.CTkLabel(
        bait_delay_row,
        text="Delay after clicking bait (s):",
        font=("Arial", 10),
        width=280,
        anchor="w",
    ).pack(side="left")
    app.bait_click_delay_entry = ctk.CTkEntry(
        bait_delay_row,
        width=80,
        fg_color=app.button_color,
        border_color=app.accent_color,
    )
    app.bait_click_delay_entry.insert(0, str(app.bait_click_delay))
    app.bait_click_delay_entry.pack(side="left", padx=5)
    ctk.CTkLabel(
        bait_delay_row, text="Default: 0.3", font=("Arial", 9), text_color="#00ccff"
    ).pack(side="left", padx=5)

    # Detection & General Delays
    detection_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
    detection_frame.pack(fill="x", pady=8)

    detection_title = ctk.CTkLabel(
        detection_frame,
        text="🔎 DETECTION & GENERAL DELAYS",
        font=("Arial", 13, "bold"),
        text_color=app.accent_color,
    )
    detection_title.pack(pady=(10, 10))

    # Fruit detection delay
    fruit_det_delay_row = ctk.CTkFrame(detection_frame, fg_color="transparent")
    fruit_det_delay_row.pack(fill="x", pady=4, padx=15)
    ctk.CTkLabel(
        fruit_det_delay_row,
        text="Delay during fruit detection (s):",
        font=("Arial", 10),
        width=280,
        anchor="w",
    ).pack(side="left")
    app.fruit_detection_delay_entry = ctk.CTkEntry(
        fruit_det_delay_row,
        width=80,
        fg_color=app.button_color,
        border_color=app.accent_color,
    )
    app.fruit_detection_delay_entry.insert(0, str(app.fruit_detection_delay))
    app.fruit_detection_delay_entry.pack(side="left", padx=5)
    ctk.CTkLabel(
        fruit_det_delay_row,
        text="Default: 0.02",
        font=("Arial", 9),
        text_color="#00ccff",
    ).pack(side="left", padx=5)

    # Fruit detection settle
    fruit_settle_row = ctk.CTkFrame(detection_frame, fg_color="transparent")
    fruit_settle_row.pack(fill="x", pady=4, padx=15)
    ctk.CTkLabel(
        fruit_settle_row,
        text="Delay after fruit detection (s):",
        font=("Arial", 10),
        width=280,
        anchor="w",
    ).pack(side="left")
    app.fruit_detection_settle_entry = ctk.CTkEntry(
        fruit_settle_row,
        width=80,
        fg_color=app.button_color,
        border_color=app.accent_color,
    )
    app.fruit_detection_settle_entry.insert(0, str(app.fruit_detection_settle))
    app.fruit_detection_settle_entry.pack(side="left", padx=5)
    ctk.CTkLabel(
        fruit_settle_row,
        text="Default: 0.3",
        font=("Arial", 9),
        text_color="#00ccff",
    ).pack(side="left", padx=5)

    # General action delay
    general_delay_row = ctk.CTkFrame(detection_frame, fg_color="transparent")
    general_delay_row.pack(fill="x", pady=4, padx=15)
    ctk.CTkLabel(
        general_delay_row,
        text="General delay between actions (s):",
        font=("Arial", 10),
        width=280,
        anchor="w",
    ).pack(side="left")
    app.general_action_delay_entry = ctk.CTkEntry(
        general_delay_row,
        width=80,
        fg_color=app.button_color,
        border_color=app.accent_color,
    )
    app.general_action_delay_entry.insert(0, str(app.general_action_delay))
    app.general_action_delay_entry.pack(side="left", padx=5)
    ctk.CTkLabel(
        general_delay_row,
        text="Default: 0.05",
        font=("Arial", 9),
        text_color="#00ccff",
    ).pack(side="left", padx=5)

    # Mouse move settle
    mouse_settle_row = ctk.CTkFrame(detection_frame, fg_color="transparent")
    mouse_settle_row.pack(fill="x", pady=4, padx=15)
    ctk.CTkLabel(
        mouse_settle_row,
        text="Delay after moving mouse (s):",
        font=("Arial", 10),
        width=280,
        anchor="w",
    ).pack(side="left")
    app.mouse_move_settle_entry = ctk.CTkEntry(
        mouse_settle_row,
        width=80,
        fg_color=app.button_color,
        border_color=app.accent_color,
    )
    app.mouse_move_settle_entry.insert(0, str(app.mouse_move_settle))
    app.mouse_move_settle_entry.pack(side="left", padx=5)
    ctk.CTkLabel(
        mouse_settle_row,
        text="Default: 0.05",
        font=("Arial", 9),
        text_color="#00ccff",
    ).pack(side="left", padx=5)

    # Focus settle delay after focusing Roblox
    focus_settle_row = ctk.CTkFrame(detection_frame, fg_color="transparent")
    focus_settle_row.pack(fill="x", pady=(4, 15), padx=15)
    ctk.CTkLabel(
        focus_settle_row,
        text="Delay after focusing Roblox (s):",
        font=("Arial", 10),
        width=280,
        anchor="w",
    ).pack(side="left")
    app.focus_settle_delay_entry = ctk.CTkEntry(
        focus_settle_row,
        width=80,
        fg_color=app.button_color,
        border_color=app.accent_color,
    )
    app.focus_settle_delay_entry.insert(0, str(app.focus_settle_delay))
    app.focus_settle_delay_entry.pack(side="left", padx=5)
    ctk.CTkLabel(
        focus_settle_row,
        text="Default: 1.0",
        font=("Arial", 9),
        text_color="#00ccff",
    ).pack(side="left", padx=5)

    # Save button for advanced settings
    save_advanced_row = ctk.CTkFrame(parent, fg_color="transparent")
    save_advanced_row.pack(fill="x", pady=15)
    ctk.CTkButton(
        save_advanced_row,
        text="💾 Save Advanced Settings",
        command=app.save_advanced_settings,
        width=250,
        fg_color=app.accent_color,
        hover_color=app.hover_color,
        font=("Arial", 12, "bold"),
    ).pack()
    ctk.CTkButton(
        save_advanced_row,
        text="🔄 Reset to Default",
        command=app.reset_advanced_settings,
        width=250,
        fg_color="#ff8800",
        hover_color="#ffaa00",
        font=("Arial", 12, "bold"),
    ).pack(pady=5)
