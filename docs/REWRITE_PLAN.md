# Rewrite Plan (v3)

Status: **Planned. Not started.** This document describes how the next version will be built. Nothing here is implemented yet.

Date: 2026-11-11

## 1. Why a rewrite

The v2 codebase works, but its structure blocks further work:

| Problem | Evidence in v2 |
| --- | --- |
| One god class owns everything | `FishingMacroGUI` in `bps_fishing_macro_v2.0.0.py` (10.7k lines, ~180 methods, ~430 `self.x =` assignments) mixes UI, Discord bot, OCR, stats, crafting and HUD. |
| Giant functions | `_try_ocr_counting_old` (~990 lines, likely dead), `__init__` (~590), `_handle_eta_command` (~560), `FishingCycle.pre_cast` (~540). |
| Half-finished extraction | `automation/fishing_cycle.py` is a literal copy-paste extraction that still calls back into the GUI for state (`get_pid_last_error`, `set_pid_last_time`, ...). |
| Errors are swallowed | ~100 `except Exception` blocks in the main file. |
| Sleep-driven flow | The fishing loop is a sequence of `time.sleep` calls instead of explicit states with timeouts. |
| Fragile coordinates | Absolute pixel coordinates with `SCREEN_WIDTH = 1920`, `SCREEN_HEIGHT = 1080` hard-coded. |
| Heavy distribution | PyInstaller bundle and an external Tesseract runtime. |
| Duplicated logic | Discord menu/ETA logic exists in both the bot service and the GUI. |
| Worked on one PC only | Fixed resolution, no DPI awareness, screen-absolute capture, exact color matching and fixed sleeps made it fail on other PCs. |
| Game knowledge buried in code | Every element position, color and click order was hand-written in code, so every change meant explaining the game piece by piece again. |

The stack was not the root cause. The architecture was. The plan below fixes the architecture first and picks a stack that makes the good architecture the easy path.

## 2. Goals and non-goals

### Goals

- Feature parity with v2 (see section 12), and nothing more until parity is reached.
- A small, fast, good-looking Windows app with a one-file installer and no extra runtimes.
- An engine that can be tested end to end **without Roblox running**.
- One source of truth for every action. The UI, the Discord bot and the HUD are all clients of the same engine API.
- **Works on any reasonable Windows PC**, not only the developer's: any resolution, any display scaling, windowed or fullscreen, any monitor (section 8).
- **Game knowledge is data**: elements and step order live in a game profile that can be built by recording and annotating gameplay, not by explaining the game in code (section 7).
- Every error is visible: in the UI, in the log, and optionally on Discord.

### Non-goals

- Cross-platform support. The app is Windows-only. Linux/macOS are out of scope.
- Porting the Python code line by line. v2 is a behavior reference, not source.
- New gameplay features before parity.
- Any kind of detection evasion beyond what v2 already does (black-screen anti-macro handling).

## 3. Stack decision

### Chosen

| Layer | Choice | Reason |
| --- | --- | --- |
| App shell | **Tauri 2** | Uses the WebView2 runtime already on Windows 10/11. Installer around 5-15 MB. Built-in installer (NSIS/MSI), updater, global shortcuts, multi-window. |
| Engine and system code | **Rust** (stable, edition 2021+) | Fast capture/detection loop, single native binary, compile-time error handling. |
| UI | **Svelte 5 + TypeScript + Tailwind CSS + shadcn-svelte** | Full visual control, small bundle, simple reactive state. |
| Screen capture | `windows-capture` (Windows Graphics Capture API) | GPU-backed, captures the Roblox window directly, works when partially covered. |
| Input | `windows` crate (`SendInput`, window focus APIs) | Replaces `pyautogui`, `pydirectinput` and `pynput` with one direct API. |
| OCR | Windows built-in OCR (`Windows.Media.Ocr` via the `windows` crate) | No Tesseract to install or bundle. |
| Discord bot | `serenity` | Mature, async, slash commands and buttons. |
| Webhooks | `reqwest` | |
| Rich Presence | `discord-rich-presence` | |
| Config | `serde` + TOML | Typed, human-readable, versioned. |
| Stats | SQLite via `rusqlite` | Same data model as v2 sessions, queryable history. |
| Secrets | Windows DPAPI (`CryptProtectData`) | Same approach as v2 `utils/token_encryption.py`, without the Fernet fallback. |
| Audio | `rodio` | Fruit notification sound. |
| Logging | `tracing` + `tracing-appender` | Structured logs, rolling files, live forwarding to the UI. |
| Errors | `thiserror` (libraries) + `anyhow` (app edges) | |
| Rust → TS types | `tauri-specta` | UI types are generated from Rust, so they never drift. |

### Alternatives considered

| Option | Why not chosen |
| --- | --- |
| Python + PySide6 / pywebview | Keeps most v2 code, but keeps the heavy bundle, Tesseract, and the GIL-bound vision loop. Good as a fallback if Rust turns out too costly (see section 14). |
| C# / .NET 8 + Avalonia or WPF | Excellent fit for a Windows macro and the strongest alternative. Lost on bundle size and UI flexibility compared to Tauri + Svelte. |
| Electron | Same UI flexibility as Tauri, but 100+ MB and higher memory. |

## 4. Repository and layout

The v3 code lives in a **new repository** (suggested name: `bps-fishing`). This repository stays as the legacy v2 reference and links to the new one.

```txt
bps-fishing/
├─ Cargo.toml                # workspace
├─ crates/
│  ├─ engine/                # state machine, tasks, FlowRunner, engine API. No Windows or Tauri deps.
│  ├─ vision/                # capture backends, detectors, coordinate/DPI math, calibration
│  ├─ profile/               # game profile types, loader, validation. Pure data, no platform deps.
│  ├─ input/                 # SendInput, window lookup/focus, hotkeys
│  ├─ storage/               # config + migrations, stats DB, secrets
│  ├─ integrations/          # discord bot, webhook, rich presence, audio
│  └─ cli/                   # headless runner for phase 1 and debugging
├─ app/
│  ├─ src-tauri/             # glue only: wires crates, exposes commands, forwards events
│  └─ ui/                    # Svelte app (main window + HUD window)
├─ profiles/
│  └─ roblox-fishing/        # game profile: elements, flows, anchors, fixtures (section 7)
├─ fixtures/                 # engine-level fixtures (recordings, compatibility matrix)
├─ docs/
│  ├─ adr/                   # architecture decision records
│  └─ ...
└─ .github/workflows/        # CI on windows-latest
```

Dependency rule (enforced in review and by crate boundaries):

```txt
app/src-tauri ──► integrations ──► engine ──► profile
      │                              ▲
      ├──────► storage ──────────────┤
      ├──────► vision  ──────────────┤  (implements engine traits)
      └──────► input   ──────────────┘  (implements engine traits)
```

`engine` and `profile` depend on nothing platform-specific. `vision` and `input` implement traits defined in `engine`. This is what makes the whole engine testable on fixtures.

## 5. Engine design

### 5.1 Engine API

The engine runs on its own thread. Everything else talks to it through two channels.

```rust
pub enum Command {
    Start,
    Stop,
    Pause,
    Resume,
    SetConfig(Config),
    TakeScreenshot,
    Shutdown,
}

pub enum Event {
    StateChanged { from: State, to: State },
    FishCaught { total: u64 },
    FruitDetected { kind: FruitKind, screenshot: Option<PathBuf> },
    BaitChanged { bait: BaitKind },
    CraftCompleted { count: u32 },
    StatsUpdated(SessionStats),
    Warning(String),
    Error(EngineError),
}

pub struct EngineHandle {
    pub commands: mpsc::Sender<Command>,
    pub events: broadcast::Receiver<Event>,
}
```

The Tauri shell, the Discord bot and the HUD each hold an `EngineHandle`. The Discord `!eta`/`/eta` command and the dashboard ETA card call the same `stats::eta()` function.

### 5.2 Platform traits

```rust
pub trait FrameSource {
    fn grab(&mut self, region: NormRect) -> Result<Frame, CaptureError>;
}

pub trait InputSink {
    fn click(&mut self, at: NormPoint, button: Button) -> Result<(), InputError>;
    fn press(&mut self, key: Key) -> Result<(), InputError>;
    fn release(&mut self, key: Key) -> Result<(), InputError>;
    fn focus_game(&mut self) -> Result<(), InputError>;
}

pub trait Clock {
    fn now(&self) -> Instant;
}
```

Test implementations: `FixtureFrames` (replays screenshots), `RecordingInput` (records actions for assertions), `FakeClock`.

### 5.3 Fishing state machine

```txt
Idle ─Start─► Preparing ─► Casting ─► WaitingBite ─► Reeling ─► Collecting ─┐
                 ▲                                                         │
                 └─────────────────────────────────────────────────────────┘

any state ──timeout / error / black screen──► Recovering ──► Preparing | Idle
any state ──Pause──► Paused ──Resume──► previous state
```

| State | Responsibility | Exit condition | Timeout (default, configurable) |
| --- | --- | --- | --- |
| `Preparing` | Run enabled pre-cast tasks (bait, craft, fruit storage) | All tasks done | 60 s |
| `Casting` | Focus game, hold/release cast | Cast animation detected | 5 s |
| `WaitingBite` | Watch the bite region for the trigger colors (v2 `esperar`) | Bite detected | 60 s |
| `Reeling` | Minigame control loop with the PD controller (v2 `pesca`, `pid_kp`, `pid_kd`, `pid_clamp`) | Minigame UI gone | 30 s |
| `Collecting` | Count catch, check fruit, emit events | Done | 5 s |
| `Recovering` | Handle black screen / anti-macro, refocus, reset input | Game visible again | 30 s, then `Idle` with error |

Each state implements:

```rust
pub trait StateBehavior {
    fn on_enter(&mut self, ctx: &mut Ctx) -> Result<()>;
    fn tick(&mut self, ctx: &mut Ctx, frame: &Frame) -> Result<Transition>;
    fn timeout(&self) -> Duration;
}
```

The loop runs at a fixed tick rate (default 60 Hz in `Reeling`, 20 Hz elsewhere): grab only the regions the current state needs, tick, apply the transition, emit events. No `sleep`-based sequencing. Delays inside a state are expressed as "wait until `ctx.clock.now() >= deadline`".

Per-state timeouts replace the v2 `utils/watchdog.py`.

### 5.4 Tasks (optional features)

Optional features plug into `Preparing` and `Collecting` instead of branching inside the main loop:

```rust
pub trait Task {
    fn name(&self) -> &'static str;
    fn enabled(&self, cfg: &Config) -> bool;
    fn should_run(&self, ctx: &Ctx) -> bool;        // e.g. every N catches
    fn step(&mut self, ctx: &mut Ctx, frame: &Frame) -> Result<TaskStatus>;
}
```

Tasks decide *when* something runs. *What* happens (the clicks and waits) is a flow from the game profile (section 7).

Planned tasks: `BaitSelect`, `BaitBuy`, `AutoCraft`, `FruitStore`, `FruitAlert`. v2 had a separate "auto craft mode" with its own copies of pre-cast, wait and minigame (`auto_craft_pre_cast`, `auto_craft_esperar`, `auto_craft_pesca`). In v3 that is the same state machine with the `AutoCraft` task enabled.

## 6. Vision

- Every region is stored as a **normalized rectangle** relative to the Roblox client area (`0.0..1.0`). Pixel coordinates are computed at capture time from the current window size and DPI (section 8).
- Colors are matched in **HSV with per-element tolerances**, never as exact RGB values.
- Detectors are generic (`color`, `template`, `bar`, `ocr_number`, `black_ratio`). Which element uses which detector, and with what parameters, comes from the game profile (section 7).
- Detectors are pure functions over a `Frame` so they can be tested on fixtures:
  - `color::matches(frame, target, tolerance)` (v2 `check_color_match`, `is_color_in_range`)
  - `color::dominant(frame)` (v2 `get_dominant_color`)
  - `bar::locate(frame)` (v2 `find_biggest_black_group`, minigame bar position)
  - `bait::classify(frame)` (v2 `detect_top_bait_color`, `detect_mid_bait_color`)
  - `screen::black_ratio(frame)` (v2 anti-macro `get_black_percentage`)
  - `ocr::read_number(frame)` (v2 `perform_ocr_and_parse_number`)
- Each detector ships with at least one fixture and a test. A detector bug becomes a new fixture.
- Debug **recording mode** saves frames plus engine decisions into a session folder, so a bad run can be replayed as a test.

## 7. Game profile: describe the game as data, not code

### The problem in v2

Every game element and every step order lived in code: pixel positions, colors, click sequences, waits. Adding or fixing anything meant explaining each piece of the game (where the shop button is, what color the bite indicator is, what happens after which click) again, in code or to whoever was helping. This was the slowest and most frustrating part of development.

### The fix

All knowledge about the game lives in one **game profile**: a set of versioned data files the engine reads. Code knows *how* to detect and act. The profile says *what* the game looks like and *in what order* things happen.

```txt
profiles/roblox-fishing/
├─ profile.toml          # name, version, reference resolution, game window title
├─ elements.toml         # every UI element: where, how to recognize it
├─ flows.toml            # step sequences (buy bait, craft, store fruit, ...)
├─ anchors/              # small reference images used to locate elements
└─ fixtures/             # labeled screenshots proving each element is detected
```

**Elements** are named and described once:

```toml
[elements.bite_indicator]
region   = { x = 0.48, y = 0.40, w = 0.04, h = 0.06 }   # normalized
detect   = { kind = "color", hsv = [12, 200, 230], tolerance = [8, 50, 50], min_ratio = 0.15 }

[elements.shop_button]
anchor   = "anchors/shop_icon.png"                       # found by template matching
offset   = { x = 0.0, y = 0.0 }
detect   = { kind = "template", threshold = 0.85 }

[elements.bait_counter]
region   = { x = 0.81, y = 0.12, w = 0.06, h = 0.03 }
detect   = { kind = "ocr_number" }
```

**Flows** describe order declaratively. Every step waits on a condition instead of a fixed sleep:

```toml
[flows.buy_common_bait]
steps = [
  { click = "shop_button" },
  { wait_until = "shop_panel", visible = true, timeout_ms = 3000 },
  { click = "bait_common" },
  { click = "buy_confirm" },
  { wait_until = "shop_panel", visible = false, timeout_ms = 3000 },
]
on_timeout = "recover"
```

Engine side:

- A `FlowRunner` executes steps inside a state or task. Supported steps: `click`, `press`, `hold`, `wait_until`, `wait_ms` (discouraged, needs a comment), `read` (store an OCR value), `branch` (if an element is visible, run another flow).
- Tasks from section 5.4 become thin: they decide *when* to run and call a flow. `BaitBuy` is "every N catches, run `buy_common_bait`".
- The reeling controller and the state machine stay in code, because they are real-time logic, not sequences.
- Profiles are validated at load time: unknown element names, missing anchors and invalid regions are errors with a clear message, not crashes in the middle of a run.
- When the game updates its UI, the fix is usually a profile change plus a new fixture, not a code change.

### Dev tooling: show the game instead of explaining it

A **Studio** mode (developer page in the app, hidden behind a setting) replaces the "explain every piece" loop:

1. **Record**: play the game normally. Studio records frames (only the game window) and your inputs with timestamps.
2. **Annotate**: scrub through the recording. Drag a box over an element, name it, and Studio samples its color or cuts an anchor image automatically. Mark the frames where it should and should not be detected.
3. **Generate**: Studio writes the element to `elements.toml`, saves the annotated frames to `fixtures/`, and proposes a flow from your recorded clicks (click on `shop_button`, then wait until `shop_panel` appeared, ...). You review and save.
4. **Test**: every element runs against its fixtures right there, showing detected/not detected per frame. The same check runs in CI.

The profile files plus the recordings also become the context for AI assistants: instead of describing the game in prose, point the assistant at `elements.toml`, `flows.toml` and the fixtures. A short `profiles/roblox-fishing/README.md` explains the game loop in plain words once.

## 8. Portability: it must work on every PC

### The problem in v2

The macro worked on the developer's PC and failed on friends' PCs. Likely causes, from the v2 code and how screen macros usually fail:

| Cause | Why it broke v2 |
| --- | --- |
| Different resolution | Hard-coded 1920x1080 and absolute pixel coordinates. |
| Windows display scaling (125%, 150%) | Process not DPI-aware, so coordinates and captures were scaled differently from what was clicked. |
| Window mode and position | Fullscreen vs windowed, window not at the screen origin, multiple monitors. Screen-absolute capture misses the game. |
| Color differences | Roblox graphics quality, HDR, Night Light, monitor color profiles and GPU settings change pixel values. Exact RGB matching fails. |
| Performance differences | Fixed `sleep` timings tuned for one PC are too short or too long on a slower or faster PC. |
| Missing runtimes | Tesseract path, Python libraries, PyInstaller antivirus false positives. |
| Keyboard layout and input method | Virtual-key based input can map differently. |

### The fix, by design

- **Capture the game window, not the screen.** Windows Graphics Capture targets the Roblox window directly, so window position, monitor and other windows do not matter.
- **Per-monitor DPI awareness v2** declared in the app manifest. All coordinates go through one conversion function: normalized element coordinates → client-area pixels → screen pixels for input. This function has unit tests for 100%, 125%, 150% and 175% scaling.
- **Normalized coordinates and anchors.** Elements are relative to the game client area (section 6). Elements that move with layout are located by anchor images (template matching) instead of fixed positions.
- **Tolerant color matching in HSV**, with tolerances per element in the profile, plus **per-machine color calibration**: on first run the user opens the game at a known screen, the app samples the reference elements and stores a small per-machine color offset. Detection uses the profile color corrected by that offset.
- **Condition-based timing.** Flows wait for game state (`wait_until`), never for fixed durations, so slow and fast PCs both work.
- **Scan-code input** (`SendInput` with `KEYEVENTF_SCANCODE`) so keyboard layout does not matter.
- **No external runtimes.** Windows OCR is built in, the app is one native installer, binaries are signed to reduce antivirus false positives.

### Preflight check

Before every Start, and on demand from the Dashboard, the app runs a **preflight** and shows a checklist with a fix hint for each failure:

- Roblox window found, visible, not minimized
- Client area size within the supported range
- DPI scaling detected and handled
- HDR / Night Light state (warning only)
- Calibration present and still matching (reference elements detected now)
- Every element required by the enabled tasks detected on the current frame, or explicitly not expected on this screen
- Input test: a harmless key round-trip the game reacts to (optional)

Start is blocked on errors and allowed with a confirmation on warnings.

### Diagnostics export

One button ("Export diagnostics") creates a zip with: app version, Windows version, DPI and resolution info, monitor layout, profile version, config without secrets, the last log file and the last N captured frames per element. A friend sends the zip, and the problem can be reproduced by loading those frames as fixtures. No automatic telemetry.

### Compatibility matrix

Fixtures are collected from at least these setups, and CI runs every detector against all of them:

| Setup | Resolution | Scaling | Window |
| --- | --- | --- | --- |
| A | 1920x1080 | 100% | fullscreen |
| B | 1366x768 | 100% | windowed |
| C | 2560x1440 | 125% | windowed |
| D | 3840x2160 | 150% | fullscreen |
| E | 1920x1080 | 100% | low graphics quality |

New setups are added from diagnostics exports whenever a user reports a failure.

## 9. Storage

### Config

- One `Config` struct, serialized as TOML in `%APPDATA%/bps-fishing/config.toml`. It holds user choices only (enabled tasks, timings, controller gains, hotkeys, integrations). Game knowledge lives in the profile (section 7), not here.
- Per-machine data (color calibration offset, detected DPI and resolution at calibration time, optional per-element region overrides) lives in `machine.toml`, next to the config. It is never shared between PCs and is regenerated by calibration.
- `schema_version` field and explicit migrations (`migrate_v1_to_v2`, ...). Unknown versions refuse to load and keep a backup instead of overwriting.
- Secrets (bot token, webhook URL) are **not** in the TOML. They are stored DPAPI-encrypted in a separate file and referenced by key.
- A one-time importer reads a v2 `bpsfishmacrosettings.json` and converts what it can. Absolute coordinates are converted to normalized ones using the 1920x1080 reference v2 assumed, then the user is asked to re-check calibration.

### Stats

SQLite tables: `sessions`, `catches`, `fruits`, `crafts`. Covers v2 `stats_manager` features: session duration, today summary, history, CSV export.

## 10. UI

### Main window (sidebar layout, dark theme by default)

| Page | Content |
| --- | --- |
| Dashboard | Big start/stop, preflight checklist (section 8), current state with animation, fish/hour, ETA, session chart, live thumbnail of the active detection region |
| Fishing | Cycle timings, minigame controller gains, tick rates |
| Bait & Craft | One card per task with enable toggle and settings |
| Calibration | Guided first-run calibration (color sampling, region check), overlay to adjust regions over the game, live detector output per element |
| Integrations | Webhook, Discord bot (allowed users, prefix), Rich Presence, test buttons |
| Stats | History, filters, CSV export |
| Logs | Live, filterable by level and module, "Export diagnostics" button |
| Settings | Hotkeys, theme, updates, config import/export, developer mode toggle |
| Studio (developer mode) | Record, annotate, generate and test profile elements and flows (section 7) |

### HUD window

Second Tauri window: transparent, always on top, click-through. Shows state, catches, session time. Toggle with a global hotkey.

### UI rules

- The UI never computes engine logic. It renders events and sends commands.
- Forms are generated from the typed config, with validation on the Rust side.
- Every long action shows progress or state; every failure shows a readable message with a suggested fix.

## 11. Engineering rules

- Git from the first commit. Conventional Commits. Versions only as tags (`v3.0.0-alpha.1`, ...). Changelog generated from commits.
- No version numbers in file or folder names.
- CI on `windows-latest` for every push: `cargo fmt --check`, `cargo clippy -D warnings`, `cargo test`, profile validation, every element against every fixture setup (section 8), `pnpm svelte-check`, `pnpm build`.
- Size limits: about 400 lines per file and about 60 lines per function. Over that, split.
- No swallowed errors. Errors propagate with `?`, become an `Event::Error` at the engine edge, and are logged.
- No `unwrap()` outside tests.
- No hard-coded game coordinates, colors or click sequences in Rust code. They belong in the profile.
- No fixed sleeps for game state. Use `wait_until` with a timeout. A `wait_ms` step needs a comment explaining why.
- Every new element or detector needs fixtures (positive and negative). Every engine bug fix needs a regression test.
- Profile changes are reviewed like code and bump the profile version.
- Significant decisions get a short ADR in `docs/adr/`.

## 12. Feature parity map

| v2 feature | v2 location | v3 location |
| --- | --- | --- |
| Main fishing loop | `automation/fishing_cycle.py` (`main_loop`, `pre_cast`, `esperar`, `pesca`) | `engine` state machine (`Preparing`, `Casting`, `WaitingBite`, `Reeling`, `Collecting`) |
| Minigame PD control | `fishing_cycle.py` (`pid_kp`, `pid_kd`, `pid_clamp`) | `engine::reeling` + `vision::bar` |
| Auto craft mode | `automation/craft_automation.py`, `auto_craft_*` methods | `AutoCraft` task + `craft` flow |
| Bait select / buy / smart decide | `automation/bait_manager.py`, `smart_bait_decide` | `BaitSelect`, `BaitBuy` tasks + `buy_*` flows + `vision::bait` |
| Fruit detect / store / screenshot | `automation/fruit_handler.py` | `FruitStore`, `FruitAlert` tasks + `store_fruit` flow |
| Auto setup | `automation/auto_setup.py` | Calibration page + overlay + preflight |
| Hard-coded coordinates and colors | spread across `automation/*`, main file | Game profile `elements.toml` (section 7) |
| Anti-macro black screen | `vision/anti_macro_detector.py` | `Recovering` state + `vision::screen::black_ratio` |
| OCR (Tesseract) | `vision/ocr_service.py` | `vision::ocr` (Windows OCR) |
| Screen capture (`mss`) | `vision/screen_capture.py` | `vision::capture` (Windows Graphics Capture) |
| Mouse / keyboard / window | `input/*` | `input` crate |
| Watchdog | `utils/watchdog.py` | Per-state timeouts |
| Settings + validation | `config/settings_manager.py`, `utils/validators.py` | `storage::config` + migrations |
| Token encryption | `utils/token_encryption.py` | `storage::secrets` (DPAPI) |
| Stats + CSV | `services/stats_manager.py` | `storage::stats` (SQLite) |
| Logging | `services/logging_service.py` | `tracing` + Logs page |
| Audio alert | `services/audio_service.py` | `integrations::audio` |
| Fruit webhook, legendary filter, pity counter | `services/webhook_service.py` | `integrations::webhook` |
| Rich Presence | `services/rich_presence_service.py` | `integrations::presence` |
| Discord bot (start, stop, pause, resume, status, stats, eta, screenshot, menu, restart, shutdown, help; allowed users; cooldown) | `services/discord_bot_service.py` + GUI handlers | `integrations::discord` using `EngineHandle` only |
| HUD | `update_hud` in main file | HUD window |
| GUI tabs | `gui/tabs/*` | Svelte pages (section 10) |

## 13. Roadmap

Each phase ends with a tagged pre-release and a short note in the changelog. A phase is not started until the previous one meets its exit criteria.

### Phase 0: Foundation

- [ ] Create the new repository with the layout from section 4
- [ ] Cargo workspace with empty crates, Tauri 2 app, Svelte + Tailwind + shadcn-svelte
- [ ] App manifest with per-monitor DPI awareness v2
- [ ] CI pipeline from section 11
- [ ] ADR 0001: stack choice (section 3). ADR 0002: engine API and state machine (section 5). ADR 0003: game profile format (section 7)
- [ ] Link the new repository from this README

Exit: CI green on an empty app that opens a window.

### Phase 1: Technical spike (highest risk, do first)

- [ ] `vision::capture` grabbing the Roblox window via Windows Graphics Capture
- [ ] Coordinate conversion (normalized → client → screen) with tests for 100/125/150/175% scaling
- [ ] `input` sending clicks and scan-code keys with `SendInput` that Roblox accepts
- [ ] One element (bite indicator) detected in HSV with tolerance, on fixtures
- [ ] `cli` binary: detect bite, then click, with timing output
- [ ] Measure capture-to-input latency
- [ ] Verify Windows OCR reads the bait counter and pity counter fixtures
- [ ] **Run the CLI on at least one other PC** (a friend's) with a different resolution or scaling

Exit: capture-to-click latency under 30 ms at the 95th percentile, and the CLI triggers on a real bite **on two different PCs**. If this fails, stop and revisit section 14 before writing more code.

### Phase 2: Engine and game profile

- [ ] `Command` / `Event` / `EngineHandle`
- [ ] State machine with `Idle`, `Preparing` (no tasks yet), `Casting`, `WaitingBite`, `Reeling`, `Collecting`, `Recovering`, `Paused`
- [ ] Profile loader with validation (`profile.toml`, `elements.toml`, `flows.toml`, anchors)
- [ ] `FlowRunner` with `click`, `press`, `hold`, `wait_until`, `wait_ms`, `read`, `branch`
- [ ] Template matching for anchored elements
- [ ] Reeling controller ported from v2 behavior, with gains in config
- [ ] Fixture-driven tests for every transition, every timeout and every flow
- [ ] Recording mode

Exit: tests green, and a 1-hour CLI run with no stuck state. No game coordinates or colors in Rust code.

### Phase 3: App shell and config

- [ ] `storage::config` and `machine.toml` with `schema_version`, plus the v2 settings importer
- [ ] Tauri commands and event forwarding, `tauri-specta` types
- [ ] Dashboard, Fishing, Logs and Settings pages
- [ ] Global start/stop hotkey

Exit: full fishing cycle usable from the app without a terminal.

### Phase 4: Works on every PC

- [ ] Guided first-run calibration with per-machine color offset
- [ ] Overlay window for adjusting regions over the game, live detector preview per element
- [ ] Preflight checklist blocking Start on errors
- [ ] Diagnostics export zip
- [ ] Fixtures for every setup in the compatibility matrix (section 8), all green in CI
- [ ] HUD window
- [ ] Beta test with 2-3 friends on their own PCs, fixing every failure through a diagnostics zip

Exit: a new user on a PC the developer never touched goes from install to fishing in under 2 minutes, without help.

### Phase 5: Studio

- [ ] Record game window frames and inputs
- [ ] Annotate: drag a box, name the element, auto-sample color or cut anchor
- [ ] Generate elements, fixtures and a draft flow from recorded clicks
- [ ] Live test of every element against its fixtures
- [ ] `profiles/roblox-fishing/README.md` describing the game loop once, in plain words

Exit: adding a new element and a short flow takes minutes in Studio and needs no Rust change.

### Phase 6: Tasks

One task at a time, built with Studio, each with fixtures and tests, each behind its own toggle:

- [ ] `BaitSelect` and `BaitBuy`
- [ ] `FruitStore` and `FruitAlert` (with screenshot)
- [ ] `AutoCraft`

Exit: every v2 automation feature in section 12 works and can be disabled independently.

### Phase 7: Stats and integrations

- [ ] `storage::stats` (SQLite), Stats page, CSV export
- [ ] Webhook (fruit alerts, legendary-only filter, pity counter)
- [ ] Rich Presence
- [ ] Discord bot through `EngineHandle` only, with allowed-user list and cooldown
- [ ] Audio alert

Exit: bot, UI and HUD show identical numbers for the same session.

### Phase 8: Distribution

- [ ] NSIS installer from Tauri, app icon, version metadata, code signing
- [ ] `tauri-plugin-updater` with signed update manifests on GitHub Releases
- [ ] Profile updates shipped separately from app updates when only the game UI changed
- [ ] Release workflow triggered by tags
- [ ] Mark this repository as archived/legacy in its README

Exit: a clean Windows machine installs and runs the app with no other downloads, and receives both an app update and a profile-only update.

## 14. Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Roblox ignores `SendInput` in some cases | Blocks the whole project | Phase 1 tests this first. v2 already worked with `pydirectinput` (scan codes), so use scan-code `SendInput` the same way. |
| Works on the developer's PC only | Friends cannot use it (main v2 pain) | Section 8: window capture, DPI awareness, normalized coordinates, HSV tolerance, per-machine calibration, condition-based timing, preflight, diagnostics, compatibility matrix. Phase 1 and Phase 4 exits require other PCs. |
| Describing the game is slow and error-prone | Development stalls (main v2 pain) | Section 7: game profile as data, Studio record/annotate/generate, fixtures as the shared description. |
| Windows Graphics Capture shows a yellow border or needs permissions | Cosmetic / setup friction | Disable the border where the OS allows it. Keep a DXGI Desktop Duplication fallback behind the `FrameSource` trait. |
| Windows OCR is less accurate than tuned Tesseract on game fonts | Bait and pity counters misread | Preprocess (scale, threshold) before OCR. Fixtures for every counter. Keep color-based counting as fallback, as v2 did. |
| Template matching too slow for real-time states | Missed bites | Use anchors only to locate elements once per screen change, then track fixed regions. Keep `Reeling` on plain region color/bar detection. |
| Profile format grows into a programming language | Complexity moves from code into TOML | Flows stay linear with `branch` only. Anything needing math or real-time control stays in Rust (state machine, reeling controller). |
| Rust learning curve slows progress | Schedule | Phases are small and independently useful. If Phase 1 or 2 take far too long, fall back to C# + Avalonia using the same architecture. Sections 4-13 do not depend on the language. |
| Game UI changes | Detectors break | Profile-only update, fixture tests, recording mode and Studio to collect new fixtures quickly. |
| Automation violates game rules | Account risk for users | Keep the same clear warning as v2 in the README and in the first-run screen. |

## 15. Open questions

- Repository name and whether to keep the "BPS Fishing Macro" branding.
- Whether Discord commands move to slash commands only or keep the `!` prefix for compatibility.
- Default tick rates, to be decided from Phase 1 measurements.
- Whether v2 bait "smart decide" logic should be simplified once real stats exist in SQLite.
- Supported client-area size range (smallest window that still detects reliably), to be decided from Phase 4 fixtures.
- Whether profiles should support more than one game later. The format allows it, but it is not a goal before parity.
