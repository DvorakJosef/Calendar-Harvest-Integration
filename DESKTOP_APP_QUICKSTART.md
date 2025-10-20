# Desktop App - Quick Start Guide

## For Developers

### 1. Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Install build tools
pip install pyinstaller
brew install create-dmg
```

### 2. Test Desktop App Locally

```bash
# Run the desktop app directly
python3 desktop_app.py
```

This will:
- Start Flask server on localhost:5001
- Open a native macOS window
- Load your app in the window
- Allow you to test all features

### 3. Build for Distribution

```bash
# Make build script executable
chmod +x build_desktop_app.sh

# Run the build
./build_desktop_app.sh
```

This will:
- Clean previous builds
- Install dependencies
- Build with PyInstaller
- Create .dmg installer
- Generate checksums

### 4. Test the Built App

```bash
# Test the app bundle
open dist/Calendar\ Harvest\ Integration.app

# Test the installer
open Calendar-Harvest-Integration-1.0.0.dmg
```

### 5. Create a Release

```bash
# Tag the release
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0

# Create GitHub release
gh release create v1.0.0 \
    Calendar-Harvest-Integration-1.0.0.dmg \
    Calendar-Harvest-Integration-1.0.0.dmg.sha256
```

## For End Users

### Installation

1. Download `Calendar-Harvest-Integration-1.0.0.dmg` from [Releases](https://github.com/DvorakJosef/Calendar-Harvest-Integration/releases)
2. Double-click to open the installer
3. Drag app to Applications folder
4. Launch from Applications

### First Run

1. Open the app
2. Click "Setup" to configure connections
3. Connect Google Calendar
4. Connect Harvest
5. Start processing timesheet entries

## File Structure

```
.
├── desktop_app.py                 # Main desktop app wrapper
├── desktop_app.spec               # PyInstaller configuration
├── desktop_updater.py             # Auto-update checker
├── build_desktop_app.sh           # Build script
├── DESKTOP_APP_GUIDE.md           # User guide
├── DESKTOP_APP_IMPLEMENTATION.md  # Developer guide
├── DESKTOP_APP_QUICKSTART.md      # This file
├── .github/workflows/
│   └── build-desktop-app.yml      # GitHub Actions CI/CD
├── main.py                        # Flask app (unchanged)
├── requirements.txt               # Python dependencies
├── templates/                     # HTML templates (unchanged)
├── static/                        # CSS/JS/images (unchanged)
└── ...other files...
```

## Key Components

### desktop_app.py
- Starts Flask server in background thread
- Creates PyWebView window
- Manages app lifecycle
- Waits for server to be ready

### desktop_updater.py
- Checks GitHub releases for updates
- Caches results (24-hour TTL)
- Provides download URLs
- Integrates with Flask API

### build_desktop_app.sh
- Automates entire build process
- Creates .dmg installer
- Generates checksums
- Provides build instructions

## Common Tasks

### Update App Version

1. Edit `desktop_updater.py`:
   ```python
   APP_VERSION = "1.1.0"
   ```

2. Edit `desktop_app.spec`:
   ```python
   'CFBundleVersion': '1.1.0',
   'CFBundleShortVersionString': '1.1.0',
   ```

3. Rebuild and release

### Add New Dependencies

1. Add to `requirements.txt`
2. Update `desktop_app.spec` `hiddenimports` if needed
3. Rebuild

### Customize App Icon

1. Create 512x512 PNG image
2. Convert to ICNS:
   ```bash
   iconutil -c icns icon.png -o static/icon.icns
   ```
3. Rebuild

### Debug Build Issues

```bash
# Verbose PyInstaller output
pyinstaller desktop_app.spec --clean -v

# Check app contents
ls -la dist/Calendar\ Harvest\ Integration.app/Contents/

# Run app with debug output
python3 desktop_app.py --debug
```

## Troubleshooting

### App won't start
- Check Flask server logs
- Verify port 5001 is available
- Check all dependencies installed

### Missing files in bundle
- Update `datas` in `desktop_app.spec`
- Rebuild with `--clean`

### Build fails
- Update PyInstaller: `pip install --upgrade pyinstaller`
- Check macOS version (10.13+)
- Verify all tools installed

## Next Steps

1. ✅ Test desktop app locally
2. ✅ Build and test .dmg installer
3. ✅ Create GitHub release
4. ✅ Share with colleagues
5. ✅ Gather feedback
6. ✅ Iterate and improve

## Resources

- [PyWebView Documentation](https://pywebview.kivy.org/)
- [PyInstaller Documentation](https://pyinstaller.org/)
- [GitHub Releases API](https://docs.github.com/en/rest/releases)
- [macOS App Distribution](https://developer.apple.com/macos/distribution/)


