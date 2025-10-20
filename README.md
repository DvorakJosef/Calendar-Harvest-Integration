# Calendar-Harvest Integration

A native macOS desktop application that automatically syncs Google Calendar events to Harvest timesheets. **Zero cloud costs, simple distribution, native experience.**

## 🎯 Features

- **Native macOS App** - Desktop application with zero cloud costs
- **Multi-user support** with Google Workspace authentication
- **Smart event grouping** - Combines events by project, task, and date
- **Pattern recognition** - Automatically suggests mappings
- **Real-time preview** - See exactly what entries will be created
- **Duplicate detection** - Prevents duplicate time entries
- **Automatic updates** - Built-in update checker
- **Offline capable** - Works without internet (with caching)

## ⚠️ Important: Harvest Project Permissions

**If projects are missing from the integration but visible in Harvest:**

Projects only appear in the Calendar-Harvest Integration if you have **Manager-level permissions** in Harvest. Regular user access is not sufficient for API visibility.

**Solution:** Contact your Harvest administrator to request Manager permissions for the projects you need to access.

## 📖 Documentation

### For Users
- **[Desktop App Guide](DESKTOP_APP_GUIDE.md)** - Installation and usage
- **[User Guide](USER_GUIDE.md)** - Complete feature guide

### For Developers
- **[Desktop App Quick Start](DESKTOP_APP_QUICKSTART.md)** - Quick reference
- **[Desktop App Implementation](DESKTOP_APP_IMPLEMENTATION.md)** - Technical details
- **[Desktop App Evaluation](DESKTOP_APP_EVALUATION.md)** - Architecture decisions

### For Setup
- **[Harvest OAuth Setup](HARVEST_OAUTH_SETUP_GUIDE.md)** - OAuth 2.0 configuration

## 🚀 Quick Start

### For End Users (macOS)
```bash
# 1. Download the latest .dmg from GitHub Releases
# 2. Double-click to open the installer
# 3. Drag app to Applications folder
# 4. Launch from Applications
# Done! ✨
```

### For Developers (Local Testing)
```bash
# Install dependencies
pip install -r requirements.txt

# Run desktop app locally
python3 desktop_app.py
# Opens native macOS window at http://localhost:5001
```

### For Building Distribution
```bash
# Build .dmg installer
chmod +x build_desktop_app.sh
./build_desktop_app.sh
# Creates Calendar-Harvest-Integration-1.0.0.dmg
```

## 📁 Clean Project Structure

This is a clean, standalone version of the Calendar-Harvest Integration, completely separated from Finhealth and other projects for clarity and maintainability.

## 🔧 Current Status

This directory contains the Calendar Harvest Integration files that were separated from the Finhealth project:

- `debug_harvest.py` - Harvest API debugging script
- `test_time_entry.py` - Time entry testing script
- `create_clean_project.py` - Project separation script
- `fix_main.py` - Main application fixes

## 📊 Next Steps

To complete the separation, you'll need to:

1. **Locate the main Calendar Harvest Integration files** (main.py, models.py, etc.)
2. **Copy them to this clean directory**
3. **Remove Calendar Harvest Integration files from the Finhealth project**
4. **Test both projects independently**

## 🌍 Deployment

This application is designed to run on Google Cloud Platform:
- **App Engine** for hosting
- **Cloud SQL PostgreSQL** for database
- **europe-central2** region for European users

---

**Note**: This is a clean, standalone project separated from Finhealth and other applications.
