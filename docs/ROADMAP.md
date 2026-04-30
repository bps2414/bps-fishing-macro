# Roadmap

This is not a promise of future features. It is an honest technical-debt map for a first large personal project.

## Current State

- The app has grown from a single macro script into a modular Windows desktop tool.
- The main file is still too large and owns too many responsibilities.
- Some modules are extracted, but callbacks and UI state are still coupled to the main GUI object.
- Discord functionality exists in more than one place and should be consolidated.
- Automated tests cover a few helper/service areas, not the full macro workflow.

## Short-Term Cleanup

- Keep public documentation accurate and avoid overstating polish.
- Keep secrets and personal settings out of Git.
- Keep generated binaries, logs, local databases, caches, and third-party runtimes out of source control.
- Make install/run/test steps reproducible from source.

## Medium-Term Engineering Work

- Split the large `FishingMacroGUI` class into smaller UI/controller components.
- Consolidate Discord bot and Discord tab logic into one path.
- Remove duplicated Discord menu code.
- Move more behavior out of the main script into `automation/`, `services/`, and `core/`.
- Add tests around settings migration, validation, Discord command safety, and automation decision logic.

## Known Risks

- Windows-only behavior makes CI harder.
- Screen-coordinate automation is fragile across resolutions and game UI changes.
- OCR features depend on local Tesseract availability.
- Discord bot tokens and webhook URLs must never be committed.
- Macro use may violate game rules; the repository should remain clear about that.
