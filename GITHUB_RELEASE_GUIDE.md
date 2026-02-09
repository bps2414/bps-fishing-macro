# 🚀 GitHub Release Guide

## 📋 Pre-Release Checklist

- [x] All tests passing (57/57)
- [x] Executable build complete (98.56 MB)
- [x] Installer compiled (123.34 MB)
- [x] Temp files cleaned
- [x] Defaults updated (optimized areas)
- [x] README updated with new features
- [ ] Git repository initialized
- [ ] Files committed
- [ ] Version tag created
- [ ] GitHub release published

---

## 🔧 Step 1: Set Up Git Repository

```powershell
cd F:\VSCode\fishing\V5.2
git init
git config user.name "Your Name"
git config user.email "you@example.com"
git add .
git commit -m "Release V5.2 - Auto-Menu Discord Bot

- Discord Bot auto-menu on connect
- Guild ID + Auto-Menu Channel ID configuration
- \"List Channels\" button to discover channel IDs
- Whitelist protection on all buttons
- Optimized default areas
- 57 tests passing (100%)
- Build: 98.56 MB exe, 123.34 MB installer"
```

---

## 🌐 Step 2: Create GitHub Repository

1. Go to https://github.com/new
2. **Name:** `bps-fishing-macro`
3. **Description:** "Automated fishing macro with Discord integration"
4. **Visibility:** Private (recommended) or Public
5. **Do NOT** initialize with README/.gitignore/license
6. Click **Create repository**

```powershell
git remote add origin https://github.com/YOUR_USERNAME/bps-fishing-macro.git
git remote -v
git branch -M main
git push -u origin main
```

---

## 📦 Step 3: Create Portable.zip (Optional)

```powershell
New-Item -Path "F:\VSCode\fishing\V5.2\portable-build" -ItemType Directory -Force
Copy-Item "F:\VSCode\fishing\V5.2\release\bps_fishing_macroV5.2.exe" `
          "F:\VSCode\fishing\V5.2\portable-build\"
Copy-Item "F:\VSCode\fishing\V5.2\release\tesseract-portable" `
          "F:\VSCode\fishing\V5.2\portable-build\tesseract-portable" `
          -Recurse
Copy-Item "F:\VSCode\fishing\V5.2\release\audio" `
          "F:\VSCode\fishing\V5.2\portable-build\audio" `
          -Recurse -ErrorAction SilentlyContinue

@"
BPS Fishing Macro V5.2 - Portable Edition
=========================================

Usage:
1. Run bps_fishing_macroV5.2.exe
2. Configure coordinates on first run
3. (Optional) Configure Discord Bot for remote control

Requirements:
- Windows 10/11 x64
- .NET Framework 4.8+ (usually preinstalled)

Support:
- GitHub: https://github.com/YOUR_USERNAME/bps-fishing-macro
"@ | Out-File "F:\VSCode\fishing\V5.2\portable-build\README.txt" -Encoding UTF8

Compress-Archive -Path "F:\VSCode\fishing\V5.2\portable-build\*" `
                 -DestinationPath "F:\VSCode\fishing\V5.2\release\BPSFishingMacro-v5.2-Portable.zip" `
                 -Force
Remove-Item "F:\VSCode\fishing\V5.2\portable-build" -Recurse -Force
```

---

## 🏷️ Step 4: Create Version Tag

```powershell


New Features:
- Auto-Menu: menu auto-sent on bot connect
- Guild & Channel config via UI
- List Channels for channel IDs
- Whitelist protection on menu buttons
- Optimized default areas

Build Info:
- Executable: 98.56 MB
- Installer: 123.34 MB
- Tests: 57/57 passing
- Python: 3.11.9
- PyInstaller: 6.17.0"

git push origin v5.2
```

---

## 🎉 Step 5: Publish GitHub Release

1. Go to `https://github.com/YOUR_USERNAME/bps-fishing-macro/releases`
2. Click **Draft a new release**
3. **Tag:** `v5.2`
4. **Title:** `V5.2 - Auto-Menu Discord Bot`
5. **Description:** Use the template below
6. **Attach binaries:**
   - `BPSFishingMacro-Setup-v5.2.exe`
   - `BPSFishingMacro-v5.2-Portable.zip` (if created)
7. Mark as **latest release**
8. Click **Publish release**

### Release Notes Template

```markdown
## 🎯 What’s New

### Discord Bot Auto-Menu
- **Auto-Menu:** Control panel sent automatically on bot connect
- **Channel Discovery:** “List Channels” shows all server channels with IDs
- **Simple Config:** Guild ID + Auto-Menu Channel ID in UI
- **Private Channel Support:** Works with restricted channels (e.g., #gpo-bot)
- **Security:** Whitelist on all menu buttons

## 📥 Downloads

| File | Size | Description |
|------|------|-------------|
| `BPSFishingMacro-Setup-v5.2.exe` | 123.34 MB | Full installer (recommended) |
| `BPSFishingMacro-v5.2-Portable.zip` | ~180 MB | Portable version |

## 🚀 Quick Install

### Installer (Recommended)
1. Download `BPSFishingMacro-Setup-v5.2.exe`
2. Run installer
3. Follow setup wizard
4. Launch from Desktop/Start Menu

### Portable
1. Download `BPSFishingMacro-v5.2-Portable.zip`
2. Extract to any folder
3. Run `bps_fishing_macroV5.2.exe`

## 🎮 Discord Bot Setup (Optional)

1. Create a bot in the Discord Developer Portal
2. Copy Application ID + Bot Token
3. Enable **Message Content Intent**
4. Configure in the macro under **Discord Bot** tab
5. Set Guild ID + Auto-Menu Channel ID
6. Save settings and restart the macro

## 📊 Technical
- Windows 10/11 x64
- Python 3.11.9
- PyInstaller 6.17.0
- Tests: 57/57 passing
```

---

## 🔐 Security Notes

### Do NOT commit:
- `bpsfishmacrosettings.json` (personal tokens/IDs)
- Discord bot tokens
- Personal webhook URLs
- Private user IDs

### Safe to commit:
- Source code
- Optimized defaults (no personal data)
- Public Discord Application ID
- Documentation
- Build scripts

---

## ✅ Final Checklist

- [ ] Commit code
- [ ] Push to GitHub
- [ ] Create tag v5.2
- [ ] Build installer
- [ ] Create portable zip (optional)
- [ ] Publish GitHub release

---

## 🎊 Done!

Your latest release will be available at:
```
https://github.com/YOUR_USERNAME/bps-fishing-macro/releases/latest
```

