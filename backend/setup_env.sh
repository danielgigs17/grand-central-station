#!/bin/bash
# Setup script for Alibaba Message Sync Environment

set -e

echo "🐍 Setting up Python environment for Alibaba Sync..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install basic requirements
echo "Installing basic requirements..."
pip install playwright asyncio python-dotenv

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install chromium

# Install additional requirements if file exists
if [ -f "requirements-alibaba.txt" ]; then
    echo "Installing additional requirements..."
    pip install -r requirements-alibaba.txt || echo "⚠️  Some packages failed to install - continuing anyway"
fi

echo "✅ Environment setup complete!"
echo ""
echo "To activate the environment in the future, run:"
echo "  source venv/bin/activate"
echo ""
echo "To test the Alibaba adapter, run:"
echo "  EMAIL_PASSWORD=your_email_password python test_adapter_only.py"
echo ""
echo "To run the production sync manager:"
echo "  EMAIL_PASSWORD=your_email_password python tools/alibaba_sync_manager.py accounts"