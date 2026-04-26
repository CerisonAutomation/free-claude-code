#!/bin/bash
# One-command deployment to Render.com
# Usage: ./deploy-render.sh

set -e

echo "🚀 Deploying free-claude-code to Render.com..."

# Check if render CLI is installed
if ! command -v render &> /dev/null; then
    echo "📦 Installing Render CLI..."
    npm install -g render-cli
fi

# Check if logged in
if ! render whoami &> /dev/null; then
    echo "🔐 Please login to Render..."
    render login
fi

# Deploy from current directory
echo "📤 Deploying application..."
render deploy

echo "✅ Deployment complete!"
echo "🌐 Your app will be available at: https://your-app-name.onrender.com"
echo "📊 View logs: render logs"
