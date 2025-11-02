#!/bin/bash
# StartupEval AI - Deployment Script
# Deploys backend to Cloud Run and frontend to Firebase Hosting

set -e  # Exit on error

echo "========================================="
echo "  StartupEval AI Deployment Script"
echo "========================================="

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-startologer}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="startologer-backend"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Helper functions
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Check prerequisites
info "Checking prerequisites..."

if ! command -v gcloud &> /dev/null; then
    error "gcloud CLI not found. Install from: https://cloud.google.com/sdk/docs/install"
fi

if ! command -v docker &> /dev/null; then
    error "Docker not found. Install from: https://docs.docker.com/get-docker/"
fi

# Authenticate with GCP
info "Authenticating with Google Cloud..."
gcloud auth login || warn "Already authenticated"
gcloud config set project "$PROJECT_ID"

# Enable required APIs
info "Enabling required GCP APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    firestore.googleapis.com \
    documentai.googleapis.com \
    secretmanager.googleapis.com \
    --project="$PROJECT_ID"

# Create secrets in Secret Manager (if they don't exist)
info "Setting up secrets..."

if ! gcloud secrets describe gemini-api-key --project="$PROJECT_ID" &> /dev/null; then
    warn "GEMINI_API_KEY not found in Secret Manager. Please create it:"
    echo "  gcloud secrets create gemini-api-key --data-file=- --project=$PROJECT_ID"
    echo "  (Then paste your API key and press Ctrl+D)"
fi

# Build and deploy backend to Cloud Run
info "Building backend Docker image..."
cd project-root/backend
gcloud builds submit \
    --tag "gcr.io/$PROJECT_ID/$SERVICE_NAME" \
    --project="$PROJECT_ID"

info "Deploying backend to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
    --image "gcr.io/$PROJECT_ID/$SERVICE_NAME" \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID,GCP_REGION=$REGION" \
    --set-secrets "GEMINI_API_KEY=gemini-api-key:latest" \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --project="$PROJECT_ID"

# Get the backend URL
BACKEND_URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format 'value(status.url)' --project="$PROJECT_ID")
info "Backend deployed at: $BACKEND_URL"

# Build frontend
info "Building Angular frontend..."
cd ../frontend
npm install
npm run build

# Deploy frontend to Firebase Hosting
info "Deploying frontend to Firebase Hosting..."
cd ..
firebase deploy --only hosting --project "$PROJECT_ID"

# Update firebase.json with backend URL
info "Updating Firebase Hosting config..."
cat > firebase.json <<EOF
{
  "hosting": {
    "public": "frontend/dist/frontend/browser",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [
      {
        "source": "/api/**",
        "run": {
          "serviceId": "$SERVICE_NAME",
          "region": "$REGION"
        }
      },
      {
        "source": "**",
        "destination": "/index.html"
      }
    ]
  }
}
EOF

firebase deploy --only hosting --project "$PROJECT_ID"

# Get frontend URL
FRONTEND_URL=$(firebase hosting:channel:list --project "$PROJECT_ID" | grep "live" | awk '{print $2}')

echo ""
echo "========================================="
info "Deployment completed successfully!"
echo "========================================="
echo ""
echo "Backend URL:  $BACKEND_URL"
echo "Frontend URL: https://$PROJECT_ID.web.app"
echo ""
echo "Next steps:"
echo "1. Update ALLOWED_ORIGINS in Cloud Run to include your frontend domain"
echo "2. Test the application"
echo "3. Set up monitoring and alerts"
echo ""
