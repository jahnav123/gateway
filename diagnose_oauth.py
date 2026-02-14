#!/usr/bin/env python3
"""
Google OAuth Diagnostic Tool
Helps identify issues with Google OAuth configuration
"""

import os
from dotenv import load_dotenv

load_dotenv()

def check_google_oauth_config():
    """Check Google OAuth configuration"""
    print("=" * 60)
    print("Google OAuth Configuration Diagnostic")
    print("=" * 60)
    print()
    
    # Check environment variables
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    
    print("1. Environment Variables Check:")
    print(f"   GOOGLE_CLIENT_ID: {'✅ Set' if client_id else '❌ Missing'}")
    if client_id:
        print(f"   Value: {client_id}")
        if not client_id.endswith('.apps.googleusercontent.com'):
            print("   ⚠️  Warning: Client ID should end with .apps.googleusercontent.com")
    
    print(f"   GOOGLE_CLIENT_SECRET: {'✅ Set' if client_secret else '❌ Missing'}")
    if client_secret:
        print(f"   Value: {client_secret[:10]}... (hidden)")
    print()
    
    # Check HTML file
    print("2. HTML Configuration Check:")
    try:
        with open('front_gate.html', 'r') as f:
            content = f.read()
            if 'data-client_id' in content:
                import re
                match = re.search(r'data-client_id="([^"]+)"', content)
                if match:
                    html_client_id = match.group(1)
                    print(f"   Client ID in HTML: {html_client_id}")
                    if client_id and html_client_id == client_id:
                        print("   ✅ Matches .env file")
                    else:
                        print("   ❌ Does NOT match .env file")
                        print("   This is likely causing the issue!")
            else:
                print("   ❌ data-client_id not found in HTML")
    except FileNotFoundError:
        print("   ❌ front_gate.html not found")
    print()
    
    # Check server.py
    print("3. Server Configuration Check:")
    try:
        with open('server.py', 'r') as f:
            content = f.read()
            if 'GOOGLE_CLIENT_ID' in content:
                print("   ✅ Server configured to use GOOGLE_CLIENT_ID")
            if 'ALLOWED_EMAIL_DOMAIN' in content:
                import re
                match = re.search(r"ALLOWED_EMAIL_DOMAIN = '([^']+)'", content)
                if match:
                    domain = match.group(1)
                    print(f"   Allowed email domain: @{domain}")
            if 'verify_oauth2_token' in content:
                print("   ✅ OAuth token verification configured")
    except FileNotFoundError:
        print("   ❌ server.py not found")
    print()
    
    # Recommendations
    print("4. Recommendations:")
    print()
    print("   To fix 'pattern did not match' error:")
    print("   a. Verify Google Cloud Console settings:")
    print("      - Go to: https://console.cloud.google.com/")
    print("      - Navigate to: APIs & Services → Credentials")
    print("      - Check Authorized JavaScript origins")
    print("      - Check Authorized redirect URIs")
    print()
    print("   b. Required Authorized JavaScript origins:")
    print("      - http://localhost:8000")
    print("      - http://127.0.0.1:8000")
    print("      - Your production domain (if deployed)")
    print()
    print("   c. Clear browser cache and try again")
    print()
    print("   d. Try in incognito/private browsing mode")
    print()
    print("   e. Check browser console for detailed errors")
    print()
    print("=" * 60)

if __name__ == '__main__':
    check_google_oauth_config()
