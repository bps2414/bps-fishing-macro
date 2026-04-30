# BPS Fishing Macro

> Legacy Windows automation project for a Roblox fishing loop. This was my first larger personal project, kept public as a record of learning, refactoring, and shipping a working tool from a messy codebase.

## Project Status

This repository is intentionally honest about its history:

- The current official codebase is `v2.0.0`, migrated from older manually copied folders such as `V3`, `V4`, `V5.x`, and `V6`.
- The macro works around screen coordinates, image/color detection, OCR, keyboard/mouse automation, and optional Discord integrations.
- The code still has technical debt, including a large main file and duplicated Discord/menu logic. See [docs/ROADMAP.md](docs/ROADMAP.md).
- Personal settings, Discord webhooks, bot tokens, local databases, logs, build outputs, and generated tooling folders are intentionally ignored.

## What It Does

BPS Fishing Macro automates a fishing cycle:

- cast, wait, catch, and repeat
- optional bait management with OCR/color detection
- optional fruit handling and alerts
- optional auto-craft flow
- optional Discord webhook, Rich Presence, and remote-control bot features
- local stats/logging for sessions

Use this at your own risk. Automation may violate game rules or platform policies. This project is shared for portfolio and learning purposes, not as a recommendation to use automation in live games.

## Tech Stack

- Python 3
- CustomTkinter/Tkinter desktop UI
- PyInstaller/Inno Setup packaging history
- `mss`, `numpy`, `Pillow`, `pyautogui`, `pynput`, `pydirectinput`
- Windows-only integrations through `pywin32`
- Discord integrations through webhooks, Rich Presence, and `discord.py`
- External Tesseract OCR for OCR-based features

## Repository Layout

```txt
.
├─ bps_fishing_macro_v2.0.0.py   # current main entry point
├─ automation/                   # fishing, bait, craft, fruit, setup flows
├─ config/                       # default settings and settings persistence
├─ core/                         # state/engine primitives
├─ gui/                          # CustomTkinter UI tabs and widgets
├─ input/                        # keyboard, mouse, window helpers
├─ services/                     # logging, stats, Discord, webhook, audio
├─ utils/                        # validation, paths, timing, token encryption
├─ vision/                       # screen capture, color detection, OCR wrappers
├─ tests/                        # focused unit tests
├─ release/                      # packaging scripts and release assets
├─ docs/                         # audit, roadmap, and portfolio notes
├─ bpsfishmacrosettings.example.json
├─ requirements.txt
└─ CHANGELOG.md
```

## Running From Source

This is a Windows desktop macro. The source run path assumes Python is installed and available on PATH or through the Python launcher.

```powershell
py -m pip install -r requirements.txt
py bps_fishing_macro_v2.0.0.py
```

On first run, the app creates `bpsfishmacrosettings.json`. That file is local-only and ignored by Git because it can contain screen coordinates, Discord webhook URLs, bot tokens, user IDs, and private server data.

Use `bpsfishmacrosettings.example.json` as a safe reference shape only. Do not commit your real settings file.

## Testing

```powershell
py -m pytest
```

Some features are hard to test automatically because they depend on Windows APIs, screen state, Roblox being open, OCR availability, and real mouse/keyboard automation.

## Packaging Notes

The repository keeps packaging scripts, but large generated binaries and local runtimes should not live in Git. Portable Tesseract files, installers, `.exe` files, logs, and local databases are ignored and should be distributed through GitHub Releases or rebuilt locally.

The historical installer script expects a local `release/tesseract-portable/` folder when building an installer.

## Documentation

- [docs/REPOSITORY_AUDIT.md](docs/REPOSITORY_AUDIT.md) - cleanup audit and version selection notes
- [docs/ROADMAP.md](docs/ROADMAP.md) - honest technical-debt roadmap
- [CHANGELOG.md](CHANGELOG.md) - release history
- [GITHUB_RELEASE_GUIDE.md](GITHUB_RELEASE_GUIDE.md) - legacy release process notes

## License

The source headers refer to GPL terms. See [LICENSE](LICENSE) for the project license statement.
