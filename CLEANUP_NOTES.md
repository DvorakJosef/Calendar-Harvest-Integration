# Environment Consolidation - Cleanup Notes

## ✅ Consolidated Environment Setup

We have successfully consolidated from 3 environments to 2:

### **Current Environments:**
1. **Development** - Local SQLite, localhost OAuth
2. **Production** - Europe (europe-central2), Cloud SQL PostgreSQL

### **Removed Environment:**
- ~~US Production~~ - ts-auto-465211.uc.r.appspot.com (us-central)

## 📁 File Changes Made

### **Updated Main Files:**
- `.env.production` ← Now points to Europe (was `.env.production.eu`)
- `app.yaml` ← Now points to Europe (was `app-eu.yaml`)
- `cloud-sql-config.txt` ← Now points to Europe (was `cloud-sql-config-eu.txt`)
- `deploy.sh` ← Now deploys to Europe
- `switch-env.sh` ← Simplified for 2 environments
- `setup-production.sh` ← Renamed from `setup-europe-project.sh`

### **Files That Can Be Removed:**
- `app-eu.yaml` (duplicated in app.yaml)
- `.env.production.eu` (duplicated in .env.production)
- `cloud-sql-config-eu.txt` (duplicated in cloud-sql-config.txt)
- `deploy-eu.sh` (functionality moved to deploy.sh)
- `setup-europe-project.sh` (renamed to setup-production.sh)

### **US Production Resources (Optional Cleanup):**
- Project: `ts-auto-465211`
- App Engine: https://ts-auto-465211.uc.r.appspot.com
- Cloud SQL: `calendar-harvest-db` in us-central1

## 🔧 Current Commands

### **Development:**
```bash
./switch-env.sh development
python3 app.py
# Access: http://127.0.0.1:5001
```

### **Production:**
```bash
./deploy.sh
# Access: https://calendar-harvest-eu.lm.r.appspot.com
```

### **Environment Switching:**
```bash
./switch-env.sh development  # Switch to dev
./switch-env.sh production   # Switch to prod
```

## 🌐 OAuth Configuration

Your OAuth should now include:
- `http://127.0.0.1:5001/auth/callback` (development)
- `http://localhost:5001/auth/callback` (development backup)
- `https://calendar-harvest-eu.lm.r.appspot.com/auth/callback` (production)

**Optional:** Remove the old US redirect URI:
- ~~`https://ts-auto-465211.uc.r.appspot.com/auth/callback`~~

## 💰 Cost Savings

By consolidating to one production environment:
- ✅ Reduced App Engine instances
- ✅ Reduced Cloud SQL instances
- ✅ Simplified monitoring and maintenance
- ✅ Lower overall GCP costs

## 📊 Monitoring

**Production (Europe):**
- Console: https://console.cloud.google.com/appengine?project=calendar-harvest-eu
- Logs: https://console.cloud.google.com/logs/query?project=calendar-harvest-eu
- Cloud SQL: https://console.cloud.google.com/sql?project=calendar-harvest-eu
