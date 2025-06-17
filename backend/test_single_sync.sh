#!/bin/bash

# Test a single sync run to verify everything works

# Set environment variables
export ALIBABA_USERNAME=daniel_allen@fastmail.com
export ALIBABA_PASSWORD=P123okemon1.
export EMAIL_PASSWORD=${EMAIL_PASSWORD:-placeholder}  
export SECRET_KEY=your-secret-key-change-this-in-production
export REDIS_URL=redis://localhost:6379/0
export DATABASE_URL=postgresql://grandcentral:password@localhost:5432/grand_central
export BROWSER_HEADLESS=false  
export EMAIL_2FA_FOLDER=2FA

echo "🧪 Testing Single Alibaba Sync..."
echo "📧 Using email: $ALIBABA_USERNAME"
echo ""

# Activate virtual environment
source venv/bin/activate

echo "📊 Current stats:"
python tools/alibaba_sync_manager.py stats
echo ""

echo "🔄 Running incremental sync..."
python tools/alibaba_sync_manager.py incremental

echo ""
echo "📊 Updated stats:"
python tools/alibaba_sync_manager.py stats