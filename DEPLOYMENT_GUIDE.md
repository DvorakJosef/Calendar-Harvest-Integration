# Calendar-Harvest Integration - Deployment Guide

This guide explains how to set up and deploy the Calendar-Harvest Integration app with a simplified two-environment setup.

## 🏗️ Architecture Overview

- **Development**: Local SQLite database, localhost OAuth
- **Production**: Google Cloud SQL PostgreSQL, App Engine hosting in Europe (europe-central2)

## 📋 Prerequisites

1. **Google Cloud SDK** installed and authenticated
2. **Python 3.9+** with pip
3. **Git** for version control
4. **Google Cloud Project** with billing enabled (`calendar-harvest-eu`)

## 🔧 Environment Setup

### 1. Development Environment

```bash
# Switch to development environment
./switch-env.sh development

# Install dependencies
pip install -r requirements.txt

# Run locally
python3 app.py
```

Access at: http://127.0.0.1:5001

### 2. Production Environment Setup

#### Step 1: Set up Production Infrastructure
```bash
# Run the production setup script (one-time setup)
./setup-production.sh
```

This will:
- Create the `calendar-harvest-eu` project
- Create App Engine application in europe-central2
- Create PostgreSQL instance in europe-central2
- Generate secure credentials
- Save configuration to `cloud-sql-config.txt`

#### Step 2: Update Google OAuth Configuration

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to "APIs & Services" > "Credentials"
3. Edit your OAuth 2.0 Client ID
4. Add these redirect URIs:
   ```
   http://127.0.0.1:5001/auth/callback
   http://localhost:5001/auth/callback
   https://calendar-harvest-eu.lm.r.appspot.com/auth/callback
   ```

#### Step 3: Deploy to Production
```bash
# Deploy to Europe production
./deploy.sh
```

This will:
- Switch to production environment
- Update app.yaml with database configuration
- Deploy to App Engine in europe-central2
- Switch back to development environment

## 📁 File Structure

```
calendar-harvest-integration/
├── .env                    # Current environment (symlink)
├── .env.development        # Development configuration
├── .env.production         # Production configuration (Europe)
├── app.yaml               # App Engine configuration (Europe)
├── config.py              # Environment configuration manager
├── health_check.py        # Health check endpoints
├── switch-env.sh          # Environment switching script
├── setup-production.sh    # Production setup script
├── deploy.sh              # Deployment script (Europe)
├── DEPLOYMENT_GUIDE.md    # This file
├── CLEANUP_NOTES.md       # Environment consolidation notes
└── us-cleanup-guide.sh    # Optional US cleanup script
```

## 🔄 Environment Management

### Switch to Development
```bash
./switch-env.sh development
```

### Switch to Production
```bash
./switch-env.sh production
```

### View Environment Status
```bash
./switch-env.sh
```

## 🗄️ Database Management

### Development Database
- **Type**: SQLite
- **Location**: `calendar_harvest_dev.db`
- **Backup**: File-based, easy to copy

### Production Database
- **Type**: PostgreSQL on Cloud SQL
- **Instance**: `calendar-harvest-db-eu`
- **Region**: europe-central2
- **Automatic backups**: Enabled (daily at 3 AM UTC)

## 🔐 Security Considerations

### Environment Variables
- **Development**: Uses `.env.development`
- **Production**: Uses App Engine environment variables

### Secrets Management
- Database passwords generated automatically
- OAuth secrets stored in environment variables
- Production secret key should be changed from default

## 📊 Monitoring and Logging

### Health Checks
- `/health` - Basic health check
- `/health/detailed` - Detailed health with database check
- `/readiness` - Readiness probe
- `/liveness` - Liveness probe

### Logging
- **Development**: Console output with DEBUG level
- **Production**: Google Cloud Logging with INFO level

### Monitoring URLs
- **App Engine Console**: https://console.cloud.google.com/appengine?project=calendar-harvest-eu
- **Cloud SQL Console**: https://console.cloud.google.com/sql?project=calendar-harvest-eu
- **Logs**: https://console.cloud.google.com/logs/query?project=calendar-harvest-eu

## 🚀 Deployment Commands

### Quick Development Setup
```bash
git clone <repository>
cd calendar-harvest-integration
./switch-env.sh development
pip install -r requirements.txt
python3 app.py
```

### Full Production Deployment
```bash
# 1. Set up production infrastructure (one-time)
./setup-production.sh

# 2. Update OAuth configuration (manual step)
# Add redirect URIs in Google Cloud Console

# 3. Deploy
./deploy.sh
```

## 🌍 Production Environment

### URLs
- **Production**: https://calendar-harvest-eu.lm.r.appspot.com
- **Development**: http://127.0.0.1:5001

### Region
- **Location**: europe-central2 (Warsaw, Poland)
- **Benefits**: Lower latency for European users, data locality compliance

## 🔧 Troubleshooting

### Common Issues

1. **OAuth Redirect URI Mismatch**
   - Check Google Cloud Console OAuth configuration
   - Ensure all redirect URIs are added

2. **Database Connection Issues**
   - Verify Cloud SQL instance is running
   - Check database credentials in `cloud-sql-config.txt`

3. **App Engine Deployment Fails**
   - Check `gcloud auth list` for authentication
   - Verify project ID is correct
   - Check app.yaml configuration

### Debug Commands
```bash
# Check current environment
cat .env

# Test database connection
python3 -c "from health_check import detailed_health_check; print(detailed_health_check())"

# View App Engine logs
gcloud app logs tail -s default --project=calendar-harvest-eu

# Check environment status
./switch-env.sh
```

## 📝 Maintenance

### Regular Tasks
1. **Monitor database usage** (Cloud SQL)
2. **Review application logs** (Cloud Logging)
3. **Update dependencies** (`pip list --outdated`)
4. **Backup development database** (copy SQLite file)

### Updates and Rollbacks
```bash
# Deploy new version
./deploy.sh

# Rollback if needed
gcloud app versions list --project=calendar-harvest-eu
gcloud app services set-traffic default --splits=<previous-version>=1 --project=calendar-harvest-eu
```

## 💰 Cost Optimization

### Current Setup
- **App Engine**: Auto-scales to 0, minimal cost when not in use
- **Cloud SQL**: db-f1-micro instance, ~$7-15/month
- **Storage**: Minimal costs for static files and logs

### Optional Cleanup
- Run `./us-cleanup-guide.sh` to clean up old US production resources
- This can save additional Cloud SQL costs from the old environment

## 🎯 Next Steps

After successful deployment:

1. ✅ Test both development and production environments
2. ✅ Verify OAuth flow works in both environments
3. ✅ Test database connectivity and data persistence
4. ✅ Set up monitoring and alerting
5. ✅ Document any custom configuration for your team
6. ✅ Consider running `./us-cleanup-guide.sh` to clean up old resources

## 📞 Support

For issues with this deployment setup:
1. Check the troubleshooting section above
2. Review Google Cloud Console for error messages
3. Check application logs for detailed error information
4. Review `CLEANUP_NOTES.md` for environment consolidation details
