# 🧪 Development Testing Guide - Calendar-Harvest Integration

**Environment:** Development (localhost:5001)  
**User:** Josef Dvořák (josef.dvorak@directpeople.com)  
**Date:** 2025-01-25

---

## 🎯 Testing Objectives

1. ✅ Verify all security improvements work correctly
2. ✅ Test complete timesheet processing workflow
3. ✅ Validate user interface and error handling
4. ✅ Confirm OAuth connections are stable
5. ✅ Test edge cases and error scenarios

---

## 🚀 Pre-Testing Setup

### **1. Start the Application**
```bash
cd /Users/josefdvorak/Documents/augment-projects/Calendar-Harvest-Integration-Clean
source venv/bin/activate
python main.py
```

**Expected Output:**
```
✅ Configuration validation passed
🔐 Using Secret Manager: False
✅ User activity monitoring enabled
⚡ DIRECT MODE - Timesheet entries will be sent directly to Harvest
* Running on http://127.0.0.1:5001
```

### **2. Open Browser**
Navigate to: `http://127.0.0.1:5001`

---

## 📋 Test Plan

### **Phase 1: Authentication & Security Testing**

#### **Test 1.1: Login Flow**
1. **Visit:** `http://127.0.0.1:5001`
2. **Expected:** Login page appears
3. **Action:** Click "Login with Google"
4. **Expected:** Redirected to Google OAuth
5. **Action:** Complete Google login
6. **Expected:** Redirected back to dashboard
7. **Verify:** Your name appears in top-right corner

#### **Test 1.2: CSRF Protection**
1. **Action:** Open browser developer tools (F12)
2. **Navigate:** Any page with forms
3. **Verify:** CSRF token present in page source
4. **Check:** `<meta name="csrf-token" content="...">` exists
5. **Test:** Try submitting form without token (should fail)

#### **Test 1.3: Rate Limiting**
1. **Action:** Rapidly refresh any page 10+ times
2. **Expected:** No rate limit errors (normal browsing)
3. **Action:** Try rapid API calls (if possible)
4. **Expected:** Rate limiting kicks in after limits

#### **Test 1.4: Security Headers**
1. **Open:** Browser developer tools → Network tab
2. **Refresh:** Any page
3. **Check headers:** Look for:
   - `X-Frame-Options`
   - `X-Content-Type-Options`
   - `Content-Security-Policy`
   - `Strict-Transport-Security` (if HTTPS)

### **Phase 2: Setup & Configuration Testing**

#### **Test 2.1: Setup Page Access**
1. **Navigate:** `http://127.0.0.1:5001/setup`
2. **Expected:** Setup page loads
3. **Verify:** Google Calendar shows "Connected"
4. **Verify:** Harvest shows "Connected" with your details

#### **Test 2.2: Connection Status**
1. **Check:** Google Calendar section shows:
   - ✅ Connected badge
   - Your email address
   - Refresh button works
2. **Check:** Harvest section shows:
   - ✅ Connected badge
   - OAuth 2.0 badge
   - Your Harvest email
   - Account name: "Direct People"
   - Disconnect button present

#### **Test 2.3: Refresh Connections**
1. **Action:** Click "Refresh" on Google Calendar
2. **Expected:** Status updates, no errors
3. **Action:** Click "Refresh" on Harvest
4. **Expected:** Status updates, no errors

### **Phase 3: Project Mappings Testing**

#### **Test 3.1: View Existing Mappings**
1. **Navigate:** `http://127.0.0.1:5001/mappings`
2. **Expected:** Your 10 existing mappings display
3. **Verify:** Each mapping shows:
   - Calendar label
   - Harvest project name
   - Harvest task name
   - Edit/Delete buttons

#### **Test 3.2: Create New Mapping**
1. **Action:** Click "Add New Mapping"
2. **Fill:** Calendar label: "Test Mapping"
3. **Select:** Any Harvest project from dropdown
4. **Select:** Any task from dropdown
5. **Action:** Click "Save"
6. **Expected:** New mapping appears in list
7. **Cleanup:** Delete the test mapping

#### **Test 3.3: Edit Existing Mapping**
1. **Action:** Click "Edit" on any mapping
2. **Modify:** Change calendar label slightly
3. **Action:** Click "Save"
4. **Expected:** Mapping updates successfully
5. **Cleanup:** Revert the change

### **Phase 4: Calendar Events Testing**

#### **Test 4.1: Load Calendar Events**
1. **Navigate:** `http://127.0.0.1:5001/process`
2. **Expected:** Current week's events load
3. **Verify:** Events show:
   - Event titles
   - Date and time
   - Duration
   - Mapping status (mapped/unmapped)

#### **Test 4.2: Week Navigation**
1. **Action:** Click "Previous Week"
2. **Expected:** Previous week's events load
3. **Action:** Click "Next Week" twice
4. **Expected:** Returns to current week
5. **Verify:** Date range updates correctly

#### **Test 4.3: Event Details**
1. **Check:** Each event displays:
   - Clear title
   - Correct date/time
   - Duration in hours
   - Mapping indicator
   - Description (if any)

### **Phase 5: Timesheet Processing Testing**

#### **Test 5.1: Preview Mode (Safe Testing)**
1. **Navigate:** Process page
2. **Select:** A week with some events (not current week)
3. **Action:** Click "Generate Preview"
4. **Expected:** Preview shows:
   - Mapped events
   - Unmapped events
   - Timesheet entries to be created
   - Total hours calculation

#### **Test 5.2: Dry Run Processing**
1. **Action:** Check "Dry Run" option
2. **Action:** Click "Process Timesheets"
3. **Expected:** 
   - Processing modal appears
   - Shows what WOULD be created
   - No actual entries sent to Harvest
   - Success message with summary

#### **Test 5.3: Actual Processing (Use Old Week)**
⚠️ **IMPORTANT:** Use a week from 2024 to avoid affecting current timesheets

1. **Navigate:** To week October 14-20, 2024
2. **Verify:** Events are mapped correctly
3. **Action:** Uncheck "Dry Run"
4. **Action:** Click "Process Timesheets"
5. **Expected:**
   - Processing modal shows progress
   - Entries created successfully
   - Success summary displayed
6. **Verify:** Check Harvest web interface for created entries

### **Phase 6: Error Handling Testing**

#### **Test 6.1: Network Error Simulation**
1. **Action:** Disconnect internet briefly
2. **Action:** Try to load calendar events
3. **Expected:** Graceful error message
4. **Action:** Reconnect internet
5. **Expected:** Functionality resumes

#### **Test 6.2: Invalid Input Testing**
1. **Try:** Creating mapping with empty label
2. **Expected:** Validation error message
3. **Try:** Processing with no events selected
4. **Expected:** Appropriate warning

#### **Test 6.3: Session Timeout**
1. **Action:** Leave app idle for extended period
2. **Action:** Try to perform action
3. **Expected:** Redirected to login if session expired

### **Phase 7: User Interface Testing**

#### **Test 7.1: Responsive Design**
1. **Test:** Resize browser window
2. **Expected:** Layout adapts properly
3. **Test:** Mobile view (developer tools)
4. **Expected:** Mobile-friendly interface

#### **Test 7.2: Navigation**
1. **Test:** All navigation links work
2. **Verify:** Breadcrumbs are correct
3. **Check:** Back button functionality

#### **Test 7.3: Visual Feedback**
1. **Verify:** Loading spinners appear during operations
2. **Check:** Success/error messages display properly
3. **Confirm:** Button states change appropriately

---

## ✅ Success Criteria

### **Must Pass:**
- [ ] All authentication flows work
- [ ] Security features are active (CSRF, rate limiting, headers)
- [ ] Calendar events load correctly
- [ ] Project mappings function properly
- [ ] Timesheet processing works (dry run and actual)
- [ ] Error handling is graceful
- [ ] UI is responsive and intuitive

### **Performance Benchmarks:**
- [ ] Page load times < 3 seconds
- [ ] Calendar events load < 5 seconds
- [ ] Processing completes < 30 seconds for typical week

---

## 🐛 Issue Tracking

### **If You Find Issues:**
1. **Note:** Exact steps to reproduce
2. **Record:** Error messages (check browser console)
3. **Check:** Server logs in terminal
4. **Document:** Expected vs actual behavior

### **Common Areas to Watch:**
- OAuth token refresh
- Large calendar event loads
- Complex project mappings
- Network connectivity issues
- Browser compatibility

---

## 🎯 Final Validation

### **Before Declaring "Ready":**
1. ✅ Complete end-to-end workflow works
2. ✅ Security features are functioning
3. ✅ Error handling is robust
4. ✅ Performance is acceptable
5. ✅ UI/UX is polished
6. ✅ No critical bugs found

### **Ready for Team Distribution When:**
- All tests pass
- No critical issues found
- Performance meets benchmarks
- Documentation is complete

---

**Start testing and let me know if you encounter any issues! 🚀**
