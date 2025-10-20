# Calendar Harvest Integration - Desktop App Guide

## Installation

### macOS

1. **Download the installer**
   - Go to [GitHub Releases](https://github.com/DvorakJosef/Calendar-Harvest-Integration/releases)
   - Download the latest `.dmg` file (e.g., `Calendar-Harvest-Integration-1.0.0.dmg`)

2. **Install the application**
   - Double-click the `.dmg` file to open it
   - Drag the "Calendar Harvest Integration" app to the Applications folder
   - Wait for the copy process to complete

3. **Launch the application**
   - Open Applications folder
   - Double-click "Calendar Harvest Integration"
   - The app will start automatically

4. **First launch**
   - The app will open in a window
   - You'll be prompted to set up your Google Calendar and Harvest connections
   - Follow the on-screen setup wizard

## System Requirements

- **macOS 10.13 or later** (High Sierra or newer)
- **Internet connection** (for OAuth authentication)
- **Google account** with Calendar access
- **Harvest account** with API access

## Features

### 1. Calendar Events
- View your Google Calendar events for the selected week
- Automatically filters out:
  - Cancelled meetings
  - Meetings you've declined
- Shows event details (time, duration, attendees)

### 2. Timesheet Processing
- Map calendar events to Harvest projects and tasks
- Create timesheet entries with a single click
- Review entries before submission
- Automatic time calculation

### 3. Project Mappings
- Save custom mappings between calendar events and Harvest projects
- Reuse mappings for recurring events
- Bulk import/export mappings

### 4. Auto-Updates
- The app checks for updates automatically on startup
- You'll be notified if a new version is available
- Download and install updates directly from the app

## Usage

### Setting Up Connections

1. **Google Calendar**
   - Click "Connect Google Calendar" on the Setup page
   - Sign in with your Google account
   - Grant calendar access permissions
   - The app will remember your credentials

2. **Harvest**
   - Click "Connect Harvest" on the Setup page
   - Sign in with your Harvest account
   - Grant API access permissions
   - The app will remember your credentials

### Processing Timesheet Entries

1. **Select a week**
   - Use the date picker to select the week you want to process
   - Calendar events will load automatically

2. **Review events**
   - Check the "Calendar Events" section
   - Cancelled and declined meetings are automatically excluded
   - Click "Show More" to see all events

3. **Create mappings**
   - For each event, select the corresponding Harvest project and task
   - The app suggests mappings based on event titles
   - Save mappings for future use

4. **Generate timesheet**
   - Click "Generate Timesheet Preview"
   - Review the proposed entries
   - Adjust hours if needed

5. **Submit to Harvest**
   - Click "Submit to Harvest"
   - Entries will be created in your Harvest account
   - You'll see a confirmation with the results

## Data Storage

### Local Database
- All your mappings and settings are stored locally on your computer
- No data is sent to external servers (except Google and Harvest APIs)
- Database location: `~/.calendar_harvest_integration/calendar_harvest.db`

### Credentials
- OAuth tokens are stored securely in your local database
- Credentials are never shared or transmitted to third parties
- You can revoke access at any time through Google/Harvest settings

## Troubleshooting

### App won't start
1. Check that you have macOS 10.13 or later
2. Try restarting your computer
3. Delete the app and reinstall from the latest .dmg

### Connection issues
1. Check your internet connection
2. Verify your Google/Harvest credentials are still valid
3. Try disconnecting and reconnecting your accounts

### Missing events
1. Check that events are not marked as "Declined" in Google Calendar
2. Verify the date range is correct
3. Check that events are in your primary calendar

### Timesheet entries not appearing in Harvest
1. Verify your Harvest account has permission to create entries
2. Check that the project and task IDs are correct
3. Review the error message in the app for details

## Updating the Application

### Automatic Updates
1. The app checks for updates on startup
2. If an update is available, you'll see a notification
3. Click "Download Update" to get the latest version
4. The app will guide you through the installation

### Manual Updates
1. Visit [GitHub Releases](https://github.com/DvorakJosef/Calendar-Harvest-Integration/releases)
2. Download the latest `.dmg` file
3. Follow the installation steps above

## Privacy & Security

- **No cloud storage** - All data stays on your computer
- **No tracking** - The app doesn't collect usage data
- **Secure authentication** - Uses OAuth 2.0 for all connections
- **Local encryption** - Credentials are stored securely
- **Open source** - Code is publicly available for review

## Support

For issues or questions:
1. Check the [GitHub Issues](https://github.com/DvorakJosef/Calendar-Harvest-Integration/issues)
2. Create a new issue with details about your problem
3. Include error messages and steps to reproduce

## Uninstalling

1. Open Applications folder
2. Drag "Calendar Harvest Integration" to Trash
3. Empty Trash
4. (Optional) Delete local data: `rm -rf ~/.calendar_harvest_integration`

## Advanced

### Command Line Launch
```bash
open /Applications/Calendar\ Harvest\ Integration.app
```

### View Logs
```bash
# Logs are stored in:
~/.calendar_harvest_integration/logs/
```

### Reset Application
```bash
# Delete all local data and start fresh:
rm -rf ~/.calendar_harvest_integration
```


