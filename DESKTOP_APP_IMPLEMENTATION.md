# Desktop App Implementation Guide

## Overview

This guide explains the desktop app implementation using PyWebView. The app wraps your existing Flask application in a native macOS window, providing a seamless desktop experience without code changes.

## Architecture

```
┌─────────────────────────────────────────┐
│   Calendar Harvest Integration.app      │
│  (Native macOS Application Bundle)      │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────────────────┐   │
│  │   PyWebView Window              │   │
│  │  (Native WKWebView)             │   │
│  │                                 │   │
│  │  ┌───────────────────────────┐  │   │
│  │  │  HTML/CSS/JS Frontend     │  │   │
│  │  │  (Your existing templates)│  │   │
│  │  └───────────────────────────┘  │   │
│  └─────────────────────────────────┘   │
│                 ↓ HTTP                  │
│  ┌─────────────────────────────────┐   │
│  │   Flask Backend (localhost)     │   │
│  │  - Google Calendar API          │   │
│  │  - Harvest API                  │   │
│  │  - SQLite Database              │   │
│  └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

## Files Created

### 1. `desktop_app.py` - Main Application Wrapper
- Manages Flask server in background thread
- Creates PyWebView window
- Handles app lifecycle
- Waits for server to be ready before showing window

### 2. `desktop_app.spec` - PyInstaller Configuration
- Defines how to package the app
- Includes all dependencies and data files
- Creates macOS app bundle with icon
- Configures bundle metadata

### 3. `build_desktop_app.sh` - Build Script
- Automates the entire build process
- Creates .dmg installer
- Generates checksums
- Provides build instructions

### 4. `desktop_updater.py` - Auto-Update Checker
- Checks GitHub releases for new versions
- Caches results (24-hour TTL)
- Provides download URLs
- Integrates with Flask API

### 5. `DESKTOP_APP_GUIDE.md` - User Documentation
- Installation instructions
- Feature overview
- Troubleshooting guide
- Privacy & security info

## Installation & Setup

### Prerequisites

```bash
# Install Python 3.9+
python3 --version

# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required tools
brew install create-dmg
```

### Install Python Dependencies

```bash
# Install all requirements including PyWebView
pip install -r requirements.txt

# Or install PyInstaller separately
pip install pyinstaller
```

## Building the App

### Quick Build

```bash
# Make build script executable
chmod +x build_desktop_app.sh

# Run the build
./build_desktop_app.sh
```

### Manual Build Steps

```bash
# Step 1: Clean previous builds
rm -rf build dist *.dmg

# Step 2: Build with PyInstaller
pyinstaller desktop_app.spec --clean

# Step 3: Test the app
open dist/Calendar\ Harvest\ Integration.app

# Step 4: Create .dmg installer
create-dmg \
    --volname "Calendar Harvest Integration" \
    --window-pos 200 120 \
    --window-size 800 400 \
    --icon-size 100 \
    --icon "Calendar Harvest Integration.app" 200 190 \
    --hide-extension "Calendar Harvest Integration.app" \
    --app-drop-link 600 190 \
    Calendar-Harvest-Integration-1.0.0.dmg \
    dist/
```

## Testing

### Local Testing

```bash
# Test the desktop app directly
python3 desktop_app.py

# Or run the built app
open dist/Calendar\ Harvest\ Integration.app
```

### Testing Checklist

- [ ] App launches without errors
- [ ] Flask server starts in background
- [ ] Web interface loads in window
- [ ] All features work (calendar, harvest, mappings)
- [ ] OAuth flows work correctly
- [ ] Database operations work
- [ ] App closes cleanly
- [ ] .dmg installer works
- [ ] App can be dragged to Applications
- [ ] App launches from Applications folder

## Distribution

### Creating a Release

```bash
# Create a new git tag
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# Create GitHub release with gh CLI
gh release create v1.0.0 \
    Calendar-Harvest-Integration-1.0.0.dmg \
    Calendar-Harvest-Integration-1.0.0.dmg.sha256 \
    --title "Calendar Harvest Integration v1.0.0" \
    --notes "Release notes here"
```

### Sharing with Colleagues

1. **Via GitHub Releases**
   - Share the release URL
   - Colleagues download .dmg directly

2. **Via Email**
   - Attach the .dmg file
   - Include installation instructions

3. **Via Shared Drive**
   - Upload to Google Drive or Dropbox
   - Share the link

## Updating the App

### For Users

The app checks for updates automatically on startup. Users will see a notification if an update is available.

### For Developers

To release a new version:

1. Update version in `desktop_updater.py`:
   ```python
   APP_VERSION = "1.1.0"
   ```

2. Update version in `desktop_app.spec`:
   ```python
   'CFBundleVersion': '1.1.0',
   'CFBundleShortVersionString': '1.1.0',
   ```

3. Rebuild the app:
   ```bash
   ./build_desktop_app.sh
   ```

4. Create a GitHub release with the new .dmg

## Troubleshooting Build Issues

### PyInstaller not found
```bash
pip install pyinstaller
```

### create-dmg not found
```bash
brew install create-dmg
```

### App won't start
1. Check Flask server logs
2. Verify all dependencies are installed
3. Check for port conflicts (5001)

### Missing files in bundle
1. Update `datas` in `desktop_app.spec`
2. Rebuild with `--clean` flag

## Performance Considerations

- **App Size**: ~150-200MB (includes Python runtime)
- **Memory Usage**: ~200-300MB at runtime
- **Startup Time**: ~3-5 seconds
- **Performance**: Native speed (no network overhead)

## Security Considerations

- Credentials stored locally in SQLite database
- OAuth tokens encrypted at rest
- No data sent to external servers (except Google/Harvest APIs)
- Code is open source for security review

## Future Enhancements

- [ ] Code signing for distribution
- [ ] Notarization for macOS Gatekeeper
- [ ] Sparkle framework for auto-updates
- [ ] System tray integration
- [ ] Keyboard shortcuts
- [ ] Dark mode support
- [ ] Windows/Linux support

## Reverting to Web App

If you need to revert to web app deployment:

1. Remove `desktop_app.py`, `desktop_app.spec`, `build_desktop_app.sh`
2. Remove PyWebView from `requirements.txt`
3. Deploy Flask app to cloud platform (Heroku, Google Cloud, etc.)
4. Update documentation


