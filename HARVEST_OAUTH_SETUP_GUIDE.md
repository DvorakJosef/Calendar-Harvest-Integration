# 🔐 Harvest OAuth 2.0 Setup Guide

**Date:** July 16, 2025  
**Status:** Ready for Implementation  
**Environment:** Development  

---

## 🎯 OBJECTIVE

**Register OAuth 2.0 application with Harvest to enable secure individual user authentication.**

---

## 📋 STEP-BY-STEP SETUP

### **Step 1: Access Harvest Developer Portal**

1. **Go to Harvest Developer Portal**
   - Visit: https://id.getharvest.com/developers
   - Log in with your Harvest account

2. **Navigate to OAuth Applications**
   - Click on "OAuth2 Applications" in the left sidebar
   - Click "Create New Application"

### **Step 2: Register OAuth Application**

**Fill out the application form:**

#### **Application Details:**
- **Application Name:** `Calendar-Harvest Integration`
- **Description:** `Automated timesheet creation from Google Calendar events with secure individual user authentication`
- **Website URL:** `https://github.com/your-username/calendar-harvest-integration` (or your repository URL)

#### **OAuth Configuration:**
- **Redirect URI (Development):** `http://127.0.0.1:5001/auth/harvest/callback`
- **Redirect URI (Production):** `https://calendar-harvest-eu.lm.r.appspot.com/auth/harvest/callback`

#### **Application Type:**
- Select: **Web Application**

#### **Permissions:**
- **Time Tracking:** Read and Write (to create time entries)
- **Projects:** Read (to fetch project and task lists)
- **Users:** Read (to get user information)

### **Step 3: Obtain OAuth Credentials**

After creating the application, you'll receive:

1. **Client ID** - Public identifier for your application
2. **Client Secret** - Private secret for your application (keep secure!)

**Example format:**
```
Client ID: 1234567890abcdef1234567890abcdef
Client Secret: abcdef1234567890abcdef1234567890abcdef12
```

### **Step 4: Update Environment Configuration**

#### **For Development (.env file):**
```bash
# Harvest OAuth 2.0 Configuration
HARVEST_CLIENT_ID=your_actual_client_id_here
HARVEST_CLIENT_SECRET=your_actual_client_secret_here
HARVEST_REDIRECT_URI=http://127.0.0.1:5001/auth/harvest/callback
```

#### **For Production (Google Cloud):**
```bash
# Set environment variables in Google Cloud
gcloud config set project calendar-harvest-eu
gcloud app deploy --set-env-vars HARVEST_CLIENT_ID=your_client_id,HARVEST_CLIENT_SECRET=your_client_secret,HARVEST_REDIRECT_URI=https://calendar-harvest-eu.lm.r.appspot.com/auth/harvest/callback
```

---

## 🧪 TESTING THE OAUTH FLOW

### **Step 1: Start Development Server**
```bash
python3 main.py
```

### **Step 2: Test OAuth Configuration**
```bash
python3 harvest_oauth.py
```

**Expected output:**
```
✅ Harvest OAuth is properly configured
   Client ID: 1234567890...
   Redirect URI: http://127.0.0.1:5001/auth/harvest/callback
```

### **Step 3: Test OAuth Flow in Browser**

1. **Visit Setup Page**
   - Go to: http://127.0.0.1:5001/setup
   - You should see the new OAuth option

2. **Click "Connect with Harvest OAuth"**
   - Should redirect to Harvest authorization page
   - Log in with your Harvest account
   - Grant permissions to the application

3. **Verify Successful Connection**
   - Should redirect back to setup page
   - Should show "OAuth 2.0" badge with your Harvest user info

---

## 🔒 SECURITY VERIFICATION

### **Test User Isolation:**

1. **Create Test User Account**
   - Register a new user in the application
   - Connect with different Harvest account

2. **Verify Separate Authentication**
   - Each user should authenticate individually
   - No shared credentials between users
   - Each user sees only their own data

3. **Test Cross-User Access Prevention**
   - User A cannot access User B's timesheet entries
   - User A cannot see User B's project mappings
   - User A cannot process events into User B's account

---

## 🚨 TROUBLESHOOTING

### **Common Issues:**

#### **1. "OAuth not configured" Error**
```
❌ Harvest OAuth is not configured
```
**Solution:** Check environment variables are set correctly

#### **2. "Invalid redirect URI" Error**
**Solution:** Ensure redirect URI in Harvest matches exactly:
- Development: `http://127.0.0.1:5001/auth/harvest/callback`
- Production: `https://calendar-harvest-eu.lm.r.appspot.com/auth/harvest/callback`

#### **3. "Invalid client credentials" Error**
**Solution:** Verify Client ID and Client Secret are correct

#### **4. "State mismatch" Error**
**Solution:** Clear browser cookies and try again

### **Debug Commands:**

```bash
# Test OAuth configuration
python3 harvest_oauth.py

# Check environment variables
echo $HARVEST_CLIENT_ID
echo $HARVEST_CLIENT_SECRET
echo $HARVEST_REDIRECT_URI

# Test OAuth endpoints
curl http://127.0.0.1:5001/api/harvest/oauth/status
```

---

## 📊 OAUTH FLOW DIAGRAM

```
User Browser          Application Server          Harvest OAuth Server
     |                        |                           |
     |-- Click "Connect" ---->|                           |
     |                        |-- Generate Auth URL ----->|
     |<-- Redirect to Harvest |                           |
     |                        |                           |
     |-- Login & Authorize ---|-------------------------->|
     |                        |                           |
     |<-- Redirect with code --|<-- Authorization Code ---|
     |                        |                           |
     |                        |-- Exchange code for token->|
     |                        |<-- Access Token ----------|
     |                        |                           |
     |<-- Success page -------|                           |
     |                        |                           |
```

---

## ✅ VERIFICATION CHECKLIST

### **OAuth Application Registration:**
- [ ] Application created in Harvest Developer Portal
- [ ] Correct redirect URIs configured
- [ ] Appropriate permissions granted
- [ ] Client ID and Secret obtained

### **Environment Configuration:**
- [ ] HARVEST_CLIENT_ID set in .env
- [ ] HARVEST_CLIENT_SECRET set in .env  
- [ ] HARVEST_REDIRECT_URI set in .env
- [ ] OAuth configuration test passes

### **Application Testing:**
- [ ] Setup page shows OAuth option
- [ ] OAuth flow redirects to Harvest correctly
- [ ] User can authorize application
- [ ] Callback handles authorization code
- [ ] User info displayed correctly
- [ ] API calls work with OAuth token

### **Security Testing:**
- [ ] Multiple users can authenticate separately
- [ ] No credential sharing possible
- [ ] User isolation verified
- [ ] Cross-user access prevented

---

## 🎯 NEXT STEPS AFTER SETUP

### **1. User Migration Strategy**
- Deploy OAuth alongside existing personal tokens
- Encourage users to switch to OAuth
- Gradually phase out personal tokens

### **2. Production Deployment**
- Update production environment variables
- Test OAuth flow in production
- Monitor authentication success rates

### **3. User Communication**
```
Subject: Upgrade to Secure Harvest Authentication

We're upgrading to more secure OAuth 2.0 authentication!

BENEFITS:
✅ Individual authentication (no shared credentials)
✅ Enhanced security and user isolation  
✅ Revocable access from your Harvest account
✅ Complete audit trail

ACTION: Visit the setup page and click "Connect with Harvest OAuth"
```

---

## 🔐 SECURITY GUARANTEE

**After OAuth 2.0 implementation:**

✅ **Individual Authentication** - Each user authenticates with their own Harvest account  
✅ **No Credential Sharing** - OAuth tokens cannot be shared between users  
✅ **Built-in User Isolation** - Automatic and foolproof  
✅ **Complete Audit Trail** - All actions tracked to specific users  
✅ **Revocable Access** - Users can revoke app access anytime  

**This makes the security incident from June 16 - July 13 technically impossible to repeat.**
