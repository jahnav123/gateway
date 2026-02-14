# Google OAuth Setup Guide

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter project name (e.g., "Gateway Permission System")
4. Click "Create"

## Step 2: Enable Google+ API

1. In the left sidebar, go to "APIs & Services" → "Library"
2. Search for "Google+ API"
3. Click on it and press "Enable"

## Step 3: Configure OAuth Consent Screen

1. Go to "APIs & Services" → "OAuth consent screen"
2. Select "External" (or "Internal" if using Google Workspace)
3. Click "Create"
4. Fill in required fields:
   - App name: Gateway Permission System
   - User support email: Your email
   - Developer contact: Your email
5. Click "Save and Continue"
6. Skip "Scopes" (click "Save and Continue")
7. Add test users if using External (add your email addresses)
8. Click "Save and Continue"

## Step 4: Create OAuth Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Select "Web application"
4. Name: Gateway Web Client
5. Add Authorized JavaScript origins:
   - `http://localhost:8080`
   - `http://192.168.18.104:8080`
   - Add your production domain when ready
6. Add Authorized redirect URIs:
   - `http://localhost:8080`
   - `http://192.168.18.104:8080`
7. Click "Create"
8. Copy the **Client ID** and **Client Secret**

## Step 5: Update Configuration Files

### Update `.env` file:
```bash
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret-here
```

### Update `front_gate.html`:
Find this line:
```html
data-client_id="YOUR_GOOGLE_CLIENT_ID"
```

Replace with your actual Client ID:
```html
data-client_id="123456789-abc123.apps.googleusercontent.com"
```

## Step 6: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 7: Restart Server

```bash
python server.py
```

## Testing

1. Open `http://192.168.18.104:8080/front_gate.html`
2. Click "Sign in with Google"
3. Select your Google account
4. Grant permissions
5. You should be logged in automatically

## Role Assignment

Users are assigned roles based on their email in `server.py`:

```python
HOD_EMAILS = ['bhaktitakey@gmail.com']
TEACHER_EMAILS = ['kruthikab21@gmail.com']
# All other emails are assigned 'student' role
```

Update these lists with your actual email addresses.

## Troubleshooting

### "Invalid Client ID" error
- Make sure you copied the full Client ID from Google Cloud Console
- Check that the Client ID in `front_gate.html` matches the one in `.env`

### "Redirect URI mismatch" error
- Add your current URL to Authorized JavaScript origins in Google Cloud Console
- Wait a few minutes for changes to propagate

### "Access blocked" error
- Add your email as a test user in OAuth consent screen
- Or publish your app (if ready for production)

## Security Notes

- Never commit `.env` file to version control
- Keep your Client Secret private
- Use HTTPS in production
- Restrict authorized domains in production
