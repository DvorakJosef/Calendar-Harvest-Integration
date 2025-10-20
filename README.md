# Calendar-Harvest Integration (Clean)

A standalone Calendar-Harvest Integration application that automatically syncs Google Calendar events to Harvest timesheets.

## 🎯 Features

- **Multi-user support** with Google Workspace authentication
- **Smart event grouping** - Combines events by project, task, and date
- **Pattern recognition** - Automatically suggests mappings
- **Real-time preview** - See exactly what entries will be created
- **Duplicate detection** - Prevents duplicate time entries

## ⚠️ Important: Harvest Project Permissions

**If projects are missing from the integration but visible in Harvest:**

Projects only appear in the Calendar-Harvest Integration if you have **Manager-level permissions** in Harvest. Regular user access is not sufficient for API visibility.

**Solution:** Contact your Harvest administrator to request Manager permissions for the projects you need to access.

## 📖 Documentation

- **[User Guide](USER_GUIDE.md)** - Complete guide for end users
- **[Harvest OAuth Setup](HARVEST_OAUTH_SETUP_GUIDE.md)** - OAuth 2.0 configuration
- **[Deployment Guide](DEPLOYMENT_GUIDE.md)** - Production deployment instructions

## 🚀 Quick Start

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your credentials

# Run locally (when main.py is available)
python3 main.py
# Access at: http://127.0.0.1:5001
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
