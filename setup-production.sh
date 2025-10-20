#!/bin/bash

# Setup script for new GCP project in europe-central2
# For Calendar-Harvest Integration

set -e

# Configuration
NEW_PROJECT_ID="calendar-harvest-eu"
REGION="europe-central2"
ZONE="europe-central2-a"
BILLING_ACCOUNT_ID=""  # Will be detected automatically

echo "🌍 Setting up new GCP project for europe-central2 deployment"
echo "New Project ID: $NEW_PROJECT_ID"
echo "Region: $REGION"
echo ""

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI is not installed. Please install it first:"
    echo "https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get billing account
echo "📋 Getting billing account information..."
BILLING_ACCOUNTS=$(gcloud billing accounts list --format="value(name)" --filter="open=true")
if [ -z "$BILLING_ACCOUNTS" ]; then
    echo "❌ No active billing accounts found. Please set up billing first."
    exit 1
fi

BILLING_ACCOUNT_ID=$(echo "$BILLING_ACCOUNTS" | head -n1)
echo "✅ Using billing account: $BILLING_ACCOUNT_ID"

# Create new project
echo "🏗️  Creating new project: $NEW_PROJECT_ID..."
if gcloud projects describe $NEW_PROJECT_ID &>/dev/null; then
    echo "✅ Project $NEW_PROJECT_ID already exists"
else
    gcloud projects create $NEW_PROJECT_ID --name="Calendar Harvest EU"
    echo "✅ Project created successfully"
fi

# Link billing account
echo "💳 Linking billing account..."
gcloud billing projects link $NEW_PROJECT_ID --billing-account=$BILLING_ACCOUNT_ID

# Set the project
echo "📋 Setting project to $NEW_PROJECT_ID..."
gcloud config set project $NEW_PROJECT_ID

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable appengine.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable sql-component.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# Create App Engine application
echo "🚀 Creating App Engine application in $REGION..."
gcloud app create --region=$REGION

# Create Cloud SQL instance
echo "🗄️  Creating Cloud SQL instance in $REGION..."
INSTANCE_NAME="calendar-harvest-db-eu"
DATABASE_NAME="calendar_harvest_prod"
DB_USER="calendar_harvest_user"

if gcloud sql instances describe $INSTANCE_NAME --project=$NEW_PROJECT_ID &>/dev/null; then
    echo "✅ Instance $INSTANCE_NAME already exists"
else
    gcloud sql instances create $INSTANCE_NAME \
        --database-version=POSTGRES_14 \
        --tier=db-f1-micro \
        --region=$REGION \
        --storage-type=SSD \
        --storage-size=10GB \
        --storage-auto-increase \
        --backup-start-time=03:00 \
        --maintenance-window-day=SUN \
        --maintenance-window-hour=04 \
        --project=$NEW_PROJECT_ID
    
    echo "✅ Cloud SQL instance created successfully"
fi

# Create database
echo "📊 Creating database $DATABASE_NAME..."
if gcloud sql databases describe $DATABASE_NAME --instance=$INSTANCE_NAME --project=$NEW_PROJECT_ID &>/dev/null; then
    echo "✅ Database $DATABASE_NAME already exists"
else
    gcloud sql databases create $DATABASE_NAME \
        --instance=$INSTANCE_NAME \
        --project=$NEW_PROJECT_ID
    
    echo "✅ Database created successfully"
fi

# Generate a random password
DB_PASSWORD=$(openssl rand -base64 32)

# Create database user
echo "👤 Creating database user $DB_USER..."
if gcloud sql users describe $DB_USER --instance=$INSTANCE_NAME --project=$NEW_PROJECT_ID &>/dev/null; then
    echo "⚠️  User $DB_USER already exists. Updating password..."
    gcloud sql users set-password $DB_USER \
        --instance=$INSTANCE_NAME \
        --password="$DB_PASSWORD" \
        --project=$NEW_PROJECT_ID
else
    gcloud sql users create $DB_USER \
        --instance=$INSTANCE_NAME \
        --password="$DB_PASSWORD" \
        --project=$NEW_PROJECT_ID
fi

echo "✅ Database user created/updated successfully"

# Get connection name
CONNECTION_NAME=$(gcloud sql instances describe $INSTANCE_NAME --project=$NEW_PROJECT_ID --format="value(connectionName)")

echo ""
echo "🎉 Europe-central2 project setup completed!"
echo ""
echo "📋 New Project Configuration:"
echo "  Project ID: $NEW_PROJECT_ID"
echo "  Region: $REGION"
echo "  App Engine URL: https://$NEW_PROJECT_ID.ew.r.appspot.com"
echo "  Instance: $INSTANCE_NAME"
echo "  Database: $DATABASE_NAME"
echo "  User: $DB_USER"
echo "  Password: $DB_PASSWORD"
echo "  Connection Name: $CONNECTION_NAME"
echo ""

# Save configuration to file
cat > cloud-sql-config-eu.txt << EOL
# Cloud SQL Configuration for Calendar-Harvest Integration (Europe)
# Generated on: $(date)

PROJECT_ID=$NEW_PROJECT_ID
REGION=$REGION
INSTANCE_NAME=$INSTANCE_NAME
DATABASE_NAME=$DATABASE_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
CONNECTION_NAME=$CONNECTION_NAME

# Database URL for .env.production.eu:
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@/$DATABASE_NAME?host=/cloudsql/$CONNECTION_NAME

# App Engine URL:
APP_URL=https://$NEW_PROJECT_ID.ew.r.appspot.com
EOL

echo "💾 Configuration saved to cloud-sql-config-eu.txt"
echo ""
echo "🔧 Next steps:"
echo "1. Update OAuth redirect URIs in Google Console"
echo "2. Create .env.production.eu file"
echo "3. Update app-eu.yaml configuration"
echo "4. Deploy to europe-central2"
echo ""
echo "📝 OAuth Redirect URI to add:"
echo "https://$NEW_PROJECT_ID.ew.r.appspot.com/auth/callback"
