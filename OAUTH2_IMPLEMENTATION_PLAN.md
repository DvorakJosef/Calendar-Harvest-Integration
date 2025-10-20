# 🔐 OAuth 2.0 Implementation Plan for Harvest Authentication

**Date:** July 16, 2025  
**Priority:** HIGH - Critical for preventing credential sharing  
**Timeline:** 2 weeks  

---

## 🎯 OBJECTIVE

**Replace personal access tokens with OAuth 2.0 authentication to eliminate credential sharing and ensure individual user authentication with Harvest.**

---

## 🚨 CURRENT PROBLEM

### **Security Issues with Personal Access Tokens:**
1. **Shared Credentials** - Users share personal access tokens
2. **No User Isolation** - One token can access any user's data
3. **No Revocation Control** - Users can't revoke app access easily
4. **No Audit Trail** - Can't track which user performed which action
5. **Manual Token Management** - Users must manually create and share tokens

---

## ✅ OAUTH 2.0 BENEFITS

### **1. Individual User Authentication**
- Each user authenticates with their own Harvest account
- No shared credentials possible
- Automatic user identification

### **2. Built-in User Isolation**
- OAuth tokens are tied to specific Harvest users
- Impossible to access wrong user's data
- Automatic credential ownership verification

### **3. Enhanced Security**
- Revocable access from Harvest account
- Time-limited tokens with refresh capability
- Complete audit trail in Harvest logs

### **4. Better User Experience**
- One-click authentication
- No manual token creation
- Automatic token refresh

---

## 🔧 IMPLEMENTATION PLAN

### **Phase 1: Harvest OAuth App Registration (Week 1)**

#### **Step 1.1: Register OAuth Application**
1. **Go to Harvest Developer Portal**
   - Visit: https://id.getharvest.com/developers
   - Log in with Harvest account

2. **Create New OAuth Application**
   - Application Name: "Calendar-Harvest Integration"
   - Description: "Automated timesheet creation from Google Calendar"
   - Website: https://calendar-harvest-eu.lm.r.appspot.com
   - Redirect URI: https://calendar-harvest-eu.lm.r.appspot.com/auth/harvest/callback

3. **Obtain OAuth Credentials**
   - Client ID
   - Client Secret
   - Store securely in environment variables

#### **Step 1.2: Update Environment Configuration**
```bash
# Add to .env and production environment
HARVEST_CLIENT_ID=your_client_id_here
HARVEST_CLIENT_SECRET=your_client_secret_here
HARVEST_REDIRECT_URI=https://calendar-harvest-eu.lm.r.appspot.com/auth/harvest/callback
```

### **Phase 2: OAuth Flow Implementation (Week 1-2)**

#### **Step 2.1: Add OAuth Dependencies**
```python
# Add to requirements.txt
requests-oauthlib==1.3.1
```

#### **Step 2.2: Create OAuth Service**
```python
# harvest_oauth.py
class HarvestOAuth:
    def __init__(self):
        self.client_id = os.getenv('HARVEST_CLIENT_ID')
        self.client_secret = os.getenv('HARVEST_CLIENT_SECRET')
        self.redirect_uri = os.getenv('HARVEST_REDIRECT_URI')
        self.authorization_base_url = 'https://id.getharvest.com/oauth2/authorize'
        self.token_url = 'https://id.getharvest.com/api/v2/oauth2/token'
    
    def get_authorization_url(self, state):
        """Get OAuth authorization URL"""
        
    def exchange_code_for_token(self, code, state):
        """Exchange authorization code for access token"""
        
    def refresh_token(self, refresh_token):
        """Refresh expired access token"""
        
    def get_user_info(self, access_token):
        """Get Harvest user information"""
```

#### **Step 2.3: Update User Model**
```python
# Add to UserConfig model
harvest_oauth_token = db.Column(db.Text)  # JSON string
harvest_refresh_token = db.Column(db.String(255))
harvest_token_expires_at = db.Column(db.DateTime)
harvest_user_id = db.Column(db.Integer)  # Harvest user ID
harvest_user_email = db.Column(db.String(255))  # Harvest user email

def set_harvest_oauth_token(self, token_data):
    """Store OAuth token data"""
    
def get_harvest_oauth_token(self):
    """Get OAuth token data"""
    
def is_harvest_token_valid(self):
    """Check if OAuth token is still valid"""
```

#### **Step 2.4: Add OAuth Endpoints**
```python
@app.route('/auth/harvest')
@login_required
def harvest_oauth_start():
    """Start Harvest OAuth flow"""
    
@app.route('/auth/harvest/callback')
@login_required
def harvest_oauth_callback():
    """Handle Harvest OAuth callback"""
    
@app.route('/api/harvest/oauth/disconnect', methods=['POST'])
@login_required
def harvest_oauth_disconnect():
    """Disconnect Harvest OAuth"""
```

### **Phase 3: Service Integration (Week 2)**

#### **Step 3.1: Update Harvest Service**
```python
# Update HarvestService to use OAuth tokens
def _get_oauth_headers(self, user_id):
    """Get headers with OAuth token"""
    user_config = UserConfig.query.filter_by(user_id=user_id).first()
    
    if not user_config:
        raise ValueError("No user configuration found")
    
    # Check if token is expired and refresh if needed
    if not user_config.is_harvest_token_valid():
        self._refresh_user_token(user_config)
    
    token_data = user_config.get_harvest_oauth_token()
    return {
        'Authorization': f'Bearer {token_data["access_token"]}',
        'Harvest-Account-Id': token_data['account_id'],
        'User-Agent': 'Calendar-Harvest Integration'
    }

def _refresh_user_token(self, user_config):
    """Refresh expired OAuth token"""
```

#### **Step 3.2: Update All API Calls**
- Replace `_get_headers()` with `_get_oauth_headers(user_id)`
- Add automatic token refresh logic
- Add OAuth-specific error handling

### **Phase 4: Migration Strategy (Week 2)**

#### **Step 4.1: Dual Authentication Support**
```python
# Support both personal tokens and OAuth during transition
def _get_headers(self, user_id=None):
    user_config = UserConfig.query.filter_by(user_id=user_id).first()
    
    # Prefer OAuth if available
    if user_config and user_config.harvest_oauth_token:
        return self._get_oauth_headers(user_id)
    
    # Fall back to personal access token
    elif user_config and user_config.harvest_access_token:
        return self._get_legacy_headers(user_id)
    
    else:
        raise ValueError("No Harvest authentication configured")
```

#### **Step 4.2: Migration UI**
- Add OAuth setup to setup wizard
- Show migration prompt for existing users
- Provide clear instructions for switching

#### **Step 4.3: Gradual Migration**
1. **Week 1:** Deploy OAuth support alongside existing tokens
2. **Week 2:** Encourage users to switch to OAuth
3. **Week 3:** Make OAuth mandatory for new users
4. **Week 4:** Deprecate personal access tokens

---

## 🧪 TESTING STRATEGY

### **Unit Tests**
- OAuth flow components
- Token refresh logic
- Error handling
- User isolation validation

### **Integration Tests**
- Complete OAuth flow
- Multi-user scenarios
- Token expiration handling
- API call authentication

### **Manual Testing**
- Multiple users with different Harvest accounts
- Token refresh scenarios
- Error conditions
- User experience flow

---

## 🛡️ SECURITY IMPROVEMENTS

### **Before OAuth (Current Issues):**
❌ Shared personal access tokens  
❌ No user identity verification  
❌ Manual credential management  
❌ No access revocation control  
❌ Limited audit trail  

### **After OAuth (Security Benefits):**
✅ Individual user authentication  
✅ Automatic user identity verification  
✅ Built-in access revocation  
✅ Complete audit trail  
✅ Time-limited tokens  
✅ Automatic token refresh  
✅ Impossible to share credentials  

---

## 📋 IMPLEMENTATION CHECKLIST

### **Week 1:**
- [ ] Register OAuth application with Harvest
- [ ] Set up OAuth credentials in environment
- [ ] Create HarvestOAuth service class
- [ ] Update UserConfig model for OAuth tokens
- [ ] Implement OAuth authorization flow
- [ ] Add OAuth callback handling
- [ ] Create OAuth endpoints

### **Week 2:**
- [ ] Update HarvestService to use OAuth tokens
- [ ] Implement token refresh logic
- [ ] Add OAuth error handling
- [ ] Create migration UI components
- [ ] Implement dual authentication support
- [ ] Write comprehensive tests
- [ ] Deploy to staging for testing

### **Week 3:**
- [ ] User acceptance testing
- [ ] Performance testing
- [ ] Security testing
- [ ] Deploy to production
- [ ] Begin user migration
- [ ] Monitor for issues

### **Week 4:**
- [ ] Complete user migration
- [ ] Remove personal token support
- [ ] Final security audit
- [ ] Documentation updates

---

## 🚀 DEPLOYMENT PLAN

### **Staging Deployment:**
1. Deploy OAuth implementation to staging
2. Test with multiple Harvest accounts
3. Verify user isolation works correctly
4. Test token refresh scenarios

### **Production Deployment:**
1. Deploy with feature flag (OAuth optional)
2. Gradual rollout to users
3. Monitor authentication success rates
4. Collect user feedback

### **Migration Communication:**
```
Subject: Important: Upgrade to Secure Harvest Authentication

Hi [User],

We're upgrading the Calendar-Harvest integration to use more secure authentication.

WHAT'S CHANGING:
- No more sharing personal access tokens
- Each user authenticates with their own Harvest account
- More secure and easier to use

ACTION REQUIRED:
1. Visit the setup page
2. Click "Connect with Harvest OAuth"
3. Authorize the application with your Harvest account

This ensures your timesheet entries are always created in YOUR account only.

Deadline: [Date]
```

---

## 🎯 SUCCESS METRICS

### **Security Metrics:**
- Zero shared credential incidents
- 100% user isolation verification
- Complete audit trail coverage

### **User Experience Metrics:**
- Reduced setup time
- Fewer authentication errors
- Higher user satisfaction

### **Technical Metrics:**
- Successful OAuth flow completion rate
- Token refresh success rate
- API authentication error rate

---

## 🔒 FINAL SECURITY GUARANTEE

**After OAuth 2.0 implementation:**

✅ **Individual Authentication:** Each user must authenticate with their own Harvest account  
✅ **Impossible Credential Sharing:** OAuth tokens cannot be shared between users  
✅ **Automatic User Isolation:** Built into OAuth protocol  
✅ **Complete Audit Trail:** All actions tracked to specific Harvest users  
✅ **Revocable Access:** Users can revoke app access anytime  

**This will make the security incident that occurred (June 16 - July 13) IMPOSSIBLE to repeat.**
