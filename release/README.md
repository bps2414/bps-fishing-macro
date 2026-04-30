# Release Assets

This folder contains packaging scripts and small release resources.

Large generated files are intentionally not tracked in Git:

- portable Tesseract runtime files
- installer outputs
- `.exe` builds
- zip archives
- local logs and databases

The historical Inno Setup script expects a local `release/tesseract-portable/`
folder when building the installer. Keep that folder local or attach the built
runtime through GitHub Releases instead of committing it to source control.
