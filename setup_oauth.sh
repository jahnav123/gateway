#!/bin/bash

echo "🔧 Gateway Google OAuth Setup"
echo "=============================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    exit 1
fi

# Prompt for Google Client ID
echo "📝 Enter your Google Client ID:"
read -r CLIENT_ID

if [ -z "$CLIENT_ID" ]; then
    echo "❌ Client ID cannot be empty"
    exit 1
fi

# Prompt for Google Client Secret
echo "📝 Enter your Google Client Secret:"
read -r CLIENT_SECRET

if [ -z "$CLIENT_SECRET" ]; then
    echo "❌ Client Secret cannot be empty"
    exit 1
fi

# Update .env file
if grep -q "GOOGLE_CLIENT_ID=" .env; then
    sed -i.bak "s|GOOGLE_CLIENT_ID=.*|GOOGLE_CLIENT_ID=$CLIENT_ID|" .env
else
    echo "GOOGLE_CLIENT_ID=$CLIENT_ID" >> .env
fi

if grep -q "GOOGLE_CLIENT_SECRET=" .env; then
    sed -i.bak "s|GOOGLE_CLIENT_SECRET=.*|GOOGLE_CLIENT_SECRET=$CLIENT_SECRET|" .env
else
    echo "GOOGLE_CLIENT_SECRET=$CLIENT_SECRET" >> .env
fi

# Update front_gate.html
sed -i.bak "s|data-client_id=\"YOUR_GOOGLE_CLIENT_ID\"|data-client_id=\"$CLIENT_ID\"|" front_gate.html

echo ""
echo "✅ Configuration updated successfully!"
echo ""
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 To start the server, run:"
echo "   python server.py"
echo ""
echo "📖 For detailed setup instructions, see GOOGLE_OAUTH_SETUP.md"
