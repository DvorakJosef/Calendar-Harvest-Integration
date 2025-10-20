#!/bin/bash

# Environment switching script for calendar-harvest integration
# Simplified for two environments: development and production

if [ "$1" = "development" ] || [ "$1" = "dev" ]; then
    echo "🔄 Switching to DEVELOPMENT environment..."
    cp .env.development .env
    export FLASK_ENV=development
    echo "✅ Development environment activated"
    echo "📍 Database: SQLite (local)"
    echo "🔗 OAuth Redirect: http://127.0.0.1:5001/auth/callback"
    echo "🌐 URL: http://127.0.0.1:5001"
    
elif [ "$1" = "production" ] || [ "$1" = "prod" ]; then
    echo "🔄 Switching to PRODUCTION environment..."
    cp .env.production .env
    export FLASK_ENV=production
    echo "✅ Production environment activated"
    echo "📍 Database: Cloud SQL PostgreSQL (europe-central2)"
    echo "🔗 OAuth Redirect: https://calendar-harvest-eu.lm.r.appspot.com/auth/callback"
    echo "🌐 URL: https://calendar-harvest-eu.lm.r.appspot.com"
    
else
    echo "📋 Calendar-Harvest Integration - Environment Manager"
    echo ""
    echo "Usage: ./switch-env.sh [development|production]"
    echo "       ./switch-env.sh [dev|prod]"
    echo ""
    echo "🏗️  Available environments:"
    echo "  development  - Local SQLite database, localhost OAuth"
    echo "  production   - Cloud SQL PostgreSQL, Europe (europe-central2)"
    echo ""
    echo "📁 Current environment files:"
    ls -la .env*
    echo ""
    echo "🌐 Production URL: https://calendar-harvest-eu.lm.r.appspot.com"
fi
