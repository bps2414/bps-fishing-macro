# Repository Audit

Date: 2026-04-30

## Scope

The parent working folder contained many manually versioned folders. The real Git repository was nested in the `V2.0.0` folder, with `origin` pointing to `https://github.com/bps2414/bps-fishing-macro.git`.

This cleanup treats `V2.0.0` as the official public repository and uses the parent-folder versions only as historical evidence.

## Version Inventory

| Path | Read |
| --- | --- |
| `bps fishing macroV2.5.py` to `bps fishing macroV2.9.py` | Early single-file versions and PyInstaller spec at the parent folder. |
| `V3/` | Older Python macro with README/LICENSE and build output. |
| `V4/` | Larger OCR/color-detection iteration with build logs and packaged output. |
| `V5_Stable/` | Stable-looking V5 snapshot, but includes large generated PyInstaller output and runtime files. |
| `V5.1 - FECHADA/` | Closed V5.1 snapshot with docs, modular folders, build artifacts, and caches. |
| `V5.2/` | Later V5 line with tests, release notes, Tesseract portable runtime, and services. |
| `V5.3/` | Later V5 line with changelog, installer guide, auto-menu Discord work, and packaged/runtime files. |
| `V6/` | Experimental refactor/migration folder with docs around GUI/pywebview work. |
| `V2.0.0_backup_sidebar_20260210_233338/` | Backup made before sidebar/migration work. |
| `V2.0.0/` | Current Git repository, latest modified folder, semantic-version migration, tests, release notes, and remote Git history. |

## Final Version Decision

Chosen final version: `V2.0.0`.

Reasons:

- It is the only nested folder with an active Git repository and GitHub remote.
- It contains the latest semantic-version migration notes.
- It has the current entry point `bps_fishing_macro_v2.0.0.py`.
- It contains modular source folders, tests, requirements, changelog, and release guide.
- Its own migration report says it consolidated mixed versions from `1.0.3`, `V5.3`, `V5.2`, `V5.1`, and `V3.1`.

Uncertainty:

- `V6/` may contain experimental ideas, but it has less evidence of being the final public release.
- Parent-folder versions were not deleted. They are outside the Git repository and should be treated as local historical snapshots.

## Essential Files

- `bps_fishing_macro_v2.0.0.py`
- `automation/`
- `config/`
- `core/`
- `gui/`
- `input/`
- `services/`
- `utils/`
- `vision/`
- `requirements.txt`
- `pytest.ini`
- `tests/`
- `release/installer.iss`

## Duplicated, Dead, or Local-Only Material

Local/generated material found:

- `__pycache__/`
- `.pytest_cache/`
- `*.log`
- `*.db`
- `build/`
- `dist/`
- `release/tesseract-portable/`
- `.copilot-skills/`
- `.copilot-vault/`
- generated `.github/agents` and prompt/vault files

These are not appropriate as public source files. The ignore rules were tightened so they do not get accidentally committed.

## Sensitive Material

`bpsfishmacrosettings.json` was found locally and contains values that should not be public:

- Discord webhook URL
- encrypted Discord bot token
- Discord user/guild/channel IDs
- private server code
- local screen coordinates

The real settings file remains ignored. A sanitized `bpsfishmacrosettings.example.json` was added for documentation.

## How The Macro Appears To Work

At a high level, the app starts a CustomTkinter control UI, stores local settings, captures screen regions, reads color/OCR cues, and drives mouse/keyboard input for the fishing loop. Optional services handle stats, logging, audio alerts, Discord webhooks, Rich Presence, and Discord bot remote control.

## Cleanup Direction

This repository should present the latest working source, not every manual folder copy. Older versions remain useful as history, but they should not be pushed as source unless they are curated into documentation or Git tags.
