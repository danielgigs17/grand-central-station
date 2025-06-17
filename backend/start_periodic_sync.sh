#!/bin/bash

# Alibaba Periodic Sync Script
# This script starts the long-running periodic scraper outside of Docker

# Set environment variables
export ALIBABA_USERNAME=daniel_allen@fastmail.com
export ALIBABA_PASSWORD=P123okemon1.
export EMAIL_PASSWORD=${EMAIL_PASSWORD:-placeholder}  # You'll need to set this
export SECRET_KEY=your-secret-key-change-this-in-production
export REDIS_URL=redis://localhost:6379/0
export DATABASE_URL=postgresql://grandcentral:password@localhost:5432/grand_central
export BROWSER_HEADLESS=true  # Set to false for debugging, true for production
export EMAIL_2FA_FOLDER=2FA

echo "🚀 Starting Alibaba Periodic Sync..."
echo "📧 Using email: $ALIBABA_USERNAME"
echo "🖥️  Browser headless: $BROWSER_HEADLESS"
echo "📁 2FA folder: $EMAIL_2FA_FOLDER"
echo ""

# Activate virtual environment
source venv/bin/activate

echo "📋 Checking current sync status..."
python tools/alibaba_sync_manager.py stats
echo ""

echo "🔄 Starting periodic scheduler (every 5 minutes)..."
echo "Press Ctrl+C to stop"
echo ""

# Start the scheduler
python tools/alibaba_sync_manager.py scheduler --interval 5