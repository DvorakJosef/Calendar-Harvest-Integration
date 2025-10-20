# 📖 Calendar-Harvest Integration User Guide

**Complete guide for using the Calendar-Harvest Integration application**

---

## 🎯 Overview

The Calendar-Harvest Integration automatically syncs your Google Calendar events to Harvest timesheets, saving you time and ensuring accurate time tracking.

### Key Features:
- **Multi-user support** with secure Google Workspace authentication
- **Smart event grouping** - Combines events by project, task, and date  
- **Pattern recognition** - Automatically suggests mappings based on your history
- **Real-time preview** - See exactly what entries will be created before submitting
- **Duplicate detection** - Prevents duplicate time entries

---

## 🚀 Getting Started

### Step 1: Access the Application
- **Development:** http://127.0.0.1:5001
- **Production:** https://calendar-harvest-eu.lm.r.appspot.com

### Step 2: Authenticate with Google
1. Click **"Sign in with Google"**
2. Use your **company Google Workspace account**
3. Grant calendar read permissions

### Step 3: Connect to Harvest
1. Go to the **Setup page**
2. Choose **"Connect with Harvest OAuth"** (recommended)
3. Log in with your **individual Harvest account**
4. Grant the necessary permissions

---

## ⚠️ IMPORTANT: Harvest Project Permissions

### 🔑 Critical Requirement for Project Visibility

**For a project to appear in the Calendar-Harvest Integration, you must have MANAGER-level permissions for that project in Harvest.**

#### Why Projects Might Be Missing:
- ✅ **Visible in Harvest web interface** - You can see and track time to the project
- ❌ **Missing from integration** - Project doesn't appear in the dropdown

#### Root Cause:
The Harvest API only returns projects where your user account has **Manager-level permissions**. Regular user access or timesheet permissions are **NOT sufficient** for API visibility.

#### Solution:
**Contact your Harvest administrator** and request:
1. **Manager permissions** for projects you need to access via the integration
2. **Verification** that you are properly assigned to the project
3. **Confirmation** that the project is active in Harvest

#### Example Scenario:
```
Project: "Režie (Direct People s.r.o.)"
- ✅ Visible in Harvest web interface
- ✅ Can track time manually in Harvest
- ❌ Missing from Calendar-Harvest Integration
- 🔧 Solution: Request Manager permissions from Harvest admin
```

### 🛡️ Security Note:
This is a **security feature** of Harvest - it prevents unauthorized API access to sensitive project data while still allowing timesheet functionality for regular users.

---

## 🗺️ Creating Mappings

### What are Mappings?
Mappings connect your calendar events to specific Harvest projects and tasks.

### Creating a New Mapping:
1. Go to the **Mappings page**
2. Click **"Add New Mapping"**
3. Fill in the details:
   - **Calendar Label:** Text that appears in your calendar events
   - **Harvest Project:** Select from your available projects
   - **Harvest Task:** Select from available tasks for that project
4. Click **"Save Mapping"**

### Smart Suggestions:
The system learns from your patterns and suggests mappings for frequently used combinations.

---

## ⚡ Processing Calendar Events

### Step 1: Preview Your Timesheet
1. Go to the **Process page**
2. Select the **week** you want to process
3. Click **"Preview Timesheet"**
4. Review the generated time entries

### Step 2: Review and Adjust
- **Check accuracy** of project/task assignments
- **Verify time calculations** (events are grouped by project/task/date)
- **Look for unmapped events** (highlighted in yellow)

### Step 3: Submit to Harvest
1. Click **"Submit to Harvest"**
2. Wait for confirmation
3. Check your Harvest account to verify entries

---

## 🔧 Troubleshooting

### Common Issues:

#### 1. "Project Not Found" Error
**Symptoms:** Project appears in Harvest but not in the integration
**Cause:** Insufficient Harvest permissions
**Solution:** Request Manager permissions from your Harvest administrator

#### 2. "No Events Found" Message
**Symptoms:** Calendar events don't appear in preview
**Possible Causes:**
- Events are outside the selected date range
- Events don't contain mapped keywords
- Google Calendar permissions not granted
**Solution:** Check date range and calendar permissions

#### 3. "Duplicate Entry" Warning
**Symptoms:** System prevents creating time entries
**Cause:** Time entries already exist for that project/task/date
**Solution:** This is normal - the system prevents duplicates automatically

#### 4. "Authentication Failed" Error
**Symptoms:** Cannot connect to Harvest or Google
**Solution:** 
- Re-authenticate in the Setup page
- Clear browser cookies and try again
- Contact administrator if using company accounts

---

## 📊 Best Practices

### Calendar Event Naming:
- **Use consistent keywords** that match your mappings
- **Include project identifiers** in event titles
- **Example:** "ČSAS Kalendář integration work" → Maps to "Public promise 2030"

### Mapping Strategy:
- **Create mappings for frequent projects** first
- **Use specific keywords** to avoid conflicts
- **Review and update mappings** regularly

### Time Tracking:
- **Process weekly** for best accuracy
- **Review previews carefully** before submitting
- **Check Harvest** after processing to confirm entries

---

## 🔒 Security & Privacy

### Data Protection:
- **Individual authentication** - Each user connects their own accounts
- **No shared credentials** - OAuth 2.0 ensures user isolation
- **Minimal data access** - Only reads calendar events and creates time entries
- **Revocable access** - You can disconnect anytime from your Google/Harvest accounts

### User Isolation:
- **Your data is private** - Other users cannot see your events or time entries
- **Separate authentication** - Each user must connect their own accounts
- **Independent processing** - Your actions don't affect other users

---

## 📞 Support

### Getting Help:
1. **Check this user guide** for common solutions
2. **Review error messages** carefully - they often contain specific guidance
3. **Contact your system administrator** for:
   - Harvest permission issues
   - Google Workspace authentication problems
   - Technical deployment issues

### Reporting Issues:
When reporting problems, please include:
- **Error message** (exact text)
- **Steps to reproduce** the issue
- **Browser and version** you're using
- **Screenshots** if helpful

---

## 🔄 Updates & Maintenance

### Regular Maintenance:
- **Review mappings** monthly to ensure they're still relevant
- **Clean up old mappings** for completed projects
- **Update project assignments** when your role changes

### System Updates:
- **New features** are deployed automatically
- **Security updates** are applied regularly
- **Downtime notifications** will be communicated in advance

---

*Last updated: July 30, 2025*
