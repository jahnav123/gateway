# Google Login Troubleshooting Guide

## Error: "Login failed: The string did not match the expected pattern"

This error occurs when Google OAuth token verification fails. Here are the steps to fix it:

### 1. Verify Google Cloud Console Configuration

Go to [Google Cloud Console](https://console.cloud.google.com/) and check:

#### a. OAuth 2.0 Client ID Settings
- Navigate to: **APIs & Services** → **Credentials**
- Click on your OAuth 2.0 Client ID
- Verify the following:

**Authorized JavaScript origins:**
```
http://localhost:8000
http://localhost:3000
http://127.0.0.1:8000
http://127.0.0.1:3000
https://your-production-domain.com
```

**Authorized redirect URIs:**
```
http://localhost:8000
http://localhost:3000
http://127.0.0.1:8000
http://127.0.0.1:3000
https://your-production-domain.com
```

#### b. Enable Required APIs
Make sure these APIs are enabled:
- Google+ API (or People API)
- Google Identity Services

### 2. Check Client ID Configuration

Verify your `.env` file has the correct Client ID:
```bash
GOOGLE_CLIENT_ID=896563148898-u92eg641v7h3dqm9up4a31n5367fu1il.apps.googleusercontent.com
```

And it matches the one in `front_gate.html`:
```html
data-client_id="896563148898-u92eg641v7h3dqm9up4a31n5367fu1il.apps.googleusercontent.com"
```

### 3. Domain Restrictions

The system only allows emails from: `@bvrithyderabad.edu.in`

Make sure you're logging in with a college email address.

### 4. Clear Browser Cache

Sometimes cached credentials cause issues:
1. Clear browser cache and cookies
2. Try in an incognito/private window
3. Try a different browser

### 5. Check Server Logs

Run the server and check for detailed error messages:
```bash
python server.py
```

Look for error messages in the console when attempting to log in.

### 6. Test with Updated Error Messages

The code has been updated to provide more detailed error messages. Try logging in again and note the exact error message.

### 7. Common Fixes

#### Fix 1: Restart the Server
```bash
# Stop the server (Ctrl+C)
# Start it again
python server.py
```

#### Fix 2: Verify Google Sign-In Library
Make sure the Google Sign-In library is loading correctly. Check browser console for errors.

#### Fix 3: Check Network Requests
Open browser DevTools → Network tab and check:
- Is the `/api/auth/google` request being made?
- What's the response status code?
- What's the error message in the response?

### 8. Alternative Login Method

If Google OAuth continues to fail, you can use the simple email login:
1. The system should show a simple login form
2. Enter your college email
3. This bypasses Google OAuth for testing

### 9. Contact Information

If the issue persists:
1. Check the server logs for detailed error messages
2. Verify your email is in the allowed domain
3. Ensure you're registered in the system (students must be pre-registered)

### 10. Quick Checklist

- [ ] Google Client ID matches in both `.env` and `front_gate.html`
- [ ] Authorized origins and redirect URIs are configured in Google Cloud Console
- [ ] Using a `@bvrithyderabad.edu.in` email address
- [ ] Server is running without errors
- [ ] Browser cache cleared
- [ ] Google Sign-In library loads without errors (check browser console)
- [ ] Student account is pre-registered in the database (for students only)
