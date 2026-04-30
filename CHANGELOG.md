#+#+#+#+
# Changelog

All notable changes to this project are documented here.

## [2.0.1] - 2026-04-30

### Changed
- Reworked README for a portfolio/public GitHub presentation.
- Added repository audit documentation and explicit technical-debt notes.
- Added sanitized settings example and stronger ignore rules for local settings, generated tooling folders, logs, databases, and release runtimes.
- Documented that portable Tesseract files are local/release artifacts, not source files.

### Security
- Confirmed real `bpsfishmacrosettings.json` is ignored because it may contain Discord webhook URLs, bot tokens, private IDs, and local coordinates.

## [2.0.0] - 2026-02-10

### Changed
- **Version Migration:** Unified all version references to semantic version 2.0.0
- Renamed main entry point to `bps_fishing_macro_v2.0.0.py`
- Updated installer, build scripts, and all module headers
- Moved legacy binary artifacts to `artifacts_needs_manual_update/`

---

## [1.0.3] - 2026-02-10

### Added
- **`!shutdown` Command:** Remotely shut down the computer via Discord bot
  - Whitelist-protected (only authorized user IDs can execute)
  - Stops the macro before initiating shutdown
  - 10-second grace period before Windows shutdown
  - Confirmation message sent to Discord channel

---

## [5.3] - 2026-02-09

### Added
- **Discord Bot Auto-Menu:** Control panel auto-sent to the configured channel on connect
- **Guild/Channel Configuration:** UI fields for Server ID and Auto-Menu Channel ID
- **"List Channels" Button:** Lists all server text channels with IDs
- **Private Channel Support:** Works with restricted channels (e.g., #gpo-bot)
- **Optimized Defaults:** Pre-configured detection areas with tested coordinates

### Security
- Whitelist protection on all Discord menu buttons (Start/Stop/Pause/Resume/Restart/Refresh)
- Bot token encryption using Windows DPAPI
- Discord Bot disabled by default for new users

### Fixed
- Defaults applied correctly on first run
- Missing parameters when instantiating `DiscordBotService`
- Duplicated menu send logic refactored

### Quality
- 57 automated tests passing (100%)
- Build: 98.56 MB (exe) | 123.34 MB (installer)
- Full release documentation included

---

## [5.1] - 2026-02-08

### Added
- Discord Bot interactive commands (!menu, !start, !stop, !pause)
- Restart button in Discord menu
- Refresh button with screenshot + updated stats
- Screenshot support in Discord menu

### Fixed
- Discord bot event loop issues
- `command_queue` AttributeError
- Window icon loading issues

---

## [5.0] - Earlier

### Added
- Auto-craft system
- Smart bait OCR detection
- Megalodon audio detection
- Discord Rich Presence
- Webhook notifications
- Pause/resume system

### Improved
- Full architecture refactor
- Modular structure (automation/, config/, core/, etc)
- Thread-safe settings manager
- Expanded test coverage

---

For earlier versions, see the Git history.
