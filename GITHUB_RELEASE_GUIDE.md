# GitHub Release Guide

This file documents the legacy manual release flow. The repository is already
connected to GitHub, so do not run `git init` again.

## Pre-Release Checklist

- [ ] Run tests from a clean environment.
- [ ] Confirm `bpsfishmacrosettings.json` is not staged.
- [ ] Confirm no webhook URLs, bot tokens, private server codes, or local IDs are staged.
- [ ] Rebuild the executable locally.
- [ ] Build the installer locally if publishing an installer.
- [ ] Attach generated binaries through GitHub Releases, not Git.

## Source Commit

```powershell
git status --short
git add README.md CHANGELOG.md requirements.txt docs/ release/ .gitignore
git add bps_fishing_macro_v2.0.0.py bps_fishing_macro_v2.0.0.spec
git add automation config core gui input services tests utils vision
git commit -m "chore: prepare repository for public portfolio"
git push origin main
```

Avoid `git add .` unless you have reviewed every untracked file.

## Build From Source

```powershell
py -m pip install -r requirements.txt
pyinstaller bps_fishing_macro_v2.0.0.spec
```

The installer script expects local release-only assets:

```txt
release/tesseract-portable/
release/audio/
```

The Tesseract folder is intentionally ignored by Git because it is a large
third-party runtime. Keep it local or attach built artifacts to Releases.

## Portable Zip

Example using relative paths from the repository root:

```powershell
New-Item -Path ".\portable-build" -ItemType Directory -Force
Copy-Item ".\release\bps_fishing_macro_v2.0.0.exe" ".\portable-build\"
Copy-Item ".\release\tesseract-portable" ".\portable-build\tesseract-portable" -Recurse
Copy-Item ".\release\audio" ".\portable-build\audio" -Recurse -ErrorAction SilentlyContinue

@"
BPS Fishing Macro v2.0.0 - Portable Edition

Usage:
1. Run bps_fishing_macro_v2.0.0.exe
2. Configure coordinates on first run
3. Optionally configure Discord features

Notes:
- Do not share your settings JSON.
- Use at your own risk.
"@ | Out-File ".\portable-build\README.txt" -Encoding UTF8

Compress-Archive -Path ".\portable-build\*" `
  -DestinationPath ".\release\BPSFishingMacro-v2.0.0-Portable.zip" `
  -Force

Remove-Item ".\portable-build" -Recurse -Force
```

## Tag And Release

```powershell
git tag -a v2.0.0 -m "BPS Fishing Macro v2.0.0"
git push origin v2.0.0
```

Then create a GitHub Release from the tag and attach generated binaries.

## Release Notes Template

```markdown
## BPS Fishing Macro v2.0.0

### Summary
- Semantic-version consolidation of the latest macro codebase.
- Windows desktop UI for fishing automation.
- Optional OCR/color-based bait detection.
- Optional Discord webhook, Rich Presence, and bot remote control.

### Downloads
| File | Description |
| --- | --- |
| `BPSFishingMacro-Setup-v2.0.0.exe` | Installer build |
| `BPSFishingMacro-v2.0.0-Portable.zip` | Portable build |

### Security
- Do not publish `bpsfishmacrosettings.json`.
- Do not publish Discord webhook URLs or bot tokens.
- Personal settings are local-only.

### Disclaimer
This tool automates gameplay input. Use at your own risk and follow the rules
of any game/platform where it is used.
```

## Never Commit

- `bpsfishmacrosettings.json`
- Discord bot tokens
- Discord webhook URLs
- private server codes
- local `.db` files
- logs/debug screenshots
- `build/`, `dist/`, generated installers, or generated executables
- portable third-party runtime folders such as `release/tesseract-portable/`
