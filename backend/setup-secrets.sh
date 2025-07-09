#!/bin/bash

# Setup Google Cloud Secret Manager secrets for AI Error Translator
# Run this script after setting up your Google Cloud project

set -e

PROJECT_ID=${GOOGLE_CLOUD_PROJECT_ID:-"ai-error-translator"}
echo "Setting up secrets for project: $PROJECT_ID"

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install Google Cloud SDK first."
    exit 1
fi

# Check if logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Not authenticated with gcloud. Please run 'gcloud auth login' first."
    exit 1
fi

# Set the project
gcloud config set project $PROJECT_ID

# Enable Secret Manager API
echo "📋 Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com

# Function to create or update secret
create_or_update_secret() {
    local secret_name=$1
    local description=$2
    
    echo "🔐 Setting up secret: $secret_name"
    
    # Check if secret exists
    if gcloud secrets describe $secret_name --quiet 2>/dev/null; then
        echo "   Secret $secret_name already exists"
    else
        # Create secret
        gcloud secrets create $secret_name --replication-policy="automatic" --data-file="-" <<< "PLACEHOLDER_VALUE"
        echo "   Created secret: $secret_name"
    fi
    
    echo "   📝 To set the actual value, run:"
    echo "   echo 'YOUR_ACTUAL_SECRET_VALUE' | gcloud secrets versions add $secret_name --data-file=-"
    echo ""
}

# Create all required secrets
echo "🚀 Creating secrets..."
echo ""

create_or_update_secret "gemini-api-key" "Gemini API key for AI services"
create_or_update_secret "jwt-secret-key" "JWT secret key for authentication"
create_or_update_secret "api-secret-key" "API secret key for general authentication"
create_or_update_secret "stripe-secret-key" "Stripe secret key for billing"
create_or_update_secret "stripe-webhook-secret" "Stripe webhook secret for payment processing"

echo "✅ Secret setup complete!"
echo ""
echo "📌 Next steps:"
echo "1. Update each secret with your actual values using the commands above"
echo "2. Grant Cloud Run service account access to secrets:"
echo "   gcloud projects add-iam-policy-binding $PROJECT_ID --member=serviceAccount:$PROJECT_ID-compute@developer.gserviceaccount.com --role=roles/secretmanager.secretAccessor"
echo "3. Deploy your application using: gcloud builds submit --config cloudbuild.yaml"
echo ""
echo "🔍 To verify secrets are set:"
echo "gcloud secrets list"
echo ""
echo "🔧 To test secret access:"
echo "gcloud secrets versions access latest --secret=gemini-api-key"