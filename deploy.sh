#!/bin/bash

# Deployment script for Calendar-Harvest Integration
# Deploys to Google App Engine in Europe (europe-central2)

set -e

PROJECT_ID="calendar-harvest-eu"
SERVICE_NAME="default"

echo "🌍 Deploying Calendar-Harvest Integration to Production (Europe)"
echo "Project: $PROJECT_ID"
echo "Region: europe-central2"
echo ""

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed. Please install it first:"
    echo "https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Set the project
echo "📋 Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# Check if Cloud SQL configuration exists
if [ ! -f "cloud-sql-config.txt" ]; then
    echo "⚠️  Cloud SQL configuration not found!"
    echo "Please run ./setup-production.sh first to set up the database."
    read -p "Do you want to continue without Cloud SQL? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ Cloud SQL configuration found"
    
    # Read database URL from config
    DB_URL=$(grep "DATABASE_URL=" cloud-sql-config.txt | cut -d'=' -f2-)
    
    # Update app.yaml with database URL
    echo "�� Updating app.yaml with database configuration..."
    if grep -q "DATABASE_URL:" app.yaml; then
        sed -i.bak "s|DATABASE_URL:.*|DATABASE_URL: \"$DB_URL\"|" app.yaml
    else
        sed -i.bak "/GOOGLE_CLOUD_PROJECT:/a\\
  DATABASE_URL: \"$DB_URL\"" app.yaml
    fi
    
    echo "✅ Database configuration updated in app.yaml"
fi

# Switch to production environment
echo "🔄 Switching to production environment..."
./switch-env.sh production

# Install production dependencies
echo "📦 Installing production dependencies..."
pip install -r requirements.txt

# Deploy to App Engine
echo "🚀 Deploying to App Engine (europe-central2)..."
gcloud app deploy app.yaml --quiet --project=$PROJECT_ID

# Get the deployed URL
APP_URL="https://$PROJECT_ID.lm.r.appspot.com"

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "📋 Deployment Information:"
echo "  Project: $PROJECT_ID"
echo "  Region: europe-central2"
echo "  Service: $SERVICE_NAME"
echo "  URL: $APP_URL"
echo ""
echo "🔗 Access your application:"
echo "  $APP_URL"
echo ""
echo "📊 Monitor your application:"
echo "  Logs: https://console.cloud.google.com/logs/query?project=$PROJECT_ID"
echo "  Metrics: https://console.cloud.google.com/appengine?project=$PROJECT_ID"
echo ""
echo "⚠️  Remember to:"
echo "1. Test the production deployment"
echo "2. Monitor logs for any issues"

# Switch back to development environment
echo ""
echo "🔄 Switching back to development environment..."
./switch-env.sh development

echo "✅ Deployment script completed!"
