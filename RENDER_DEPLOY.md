# Render Deployment Guide

## Deploy to Render (Free - 5 minutes)

### Step 1: Sign Up
1. Go to **https://render.com**
2. Click "Get Started" → Sign up with GitHub/GitLab
3. Authorize Render

### Step 2: Create Web Service
1. Click **"New +"** → **"Web Service"**
2. Connect your repository:
   - If using GitLab: Enter `https://repo.we4shakthi.in/wingsai/gateway.git`
   - Or connect via GitHub if you mirror it
3. Configure:
   - **Name:** `gateway-app` (or any name)
   - **Region:** Choose closest to you
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `bash start_server.sh`
   - **Plan:** `Free`

### Step 3: Add Environment Variables
Click **"Environment"** tab and add these:

```
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
GOOGLE_CLIENT_ID=896563148898-u92eg641v7h3dqm9up4a31n5367fu1il.apps.googleusercontent.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=watermelon37453@gmail.com
SMTP_PASSWORD=fhfbvpbcawkgocid
COLLEGE_NAME=BVRIT Hyderabad
COLLEGE_EMAIL=watermelon37453@gmail.com
ENFORCE_DOMAIN_RESTRICTION=false
BASE_URL=https://gateway-app.onrender.com
```

**Important:** Replace `BASE_URL` with your actual Render URL after deployment!

### Step 4: Deploy
1. Click **"Create Web Service"**
2. Wait 3-5 minutes for build and deployment
3. You'll get a URL like: `https://gateway-app.onrender.com`

### Step 5: Update Google OAuth (CRITICAL)
1. Go to **Google Cloud Console**: https://console.cloud.google.com
2. Navigate to **APIs & Services** → **Credentials**
3. Click on your OAuth 2.0 Client ID
4. Add to **Authorized JavaScript origins:**
   ```
   https://gateway-app.onrender.com
   ```
5. Add to **Authorized redirect URIs:**
   ```
   https://gateway-app.onrender.com
   ```
6. Click **Save**

### Step 6: Update BASE_URL
1. Go back to Render dashboard
2. Click your service → **Environment**
3. Update `BASE_URL` to your actual Render URL
4. Save (will auto-redeploy)

### Step 7: Test
1. Open your Render URL: `https://gateway-app.onrender.com/front_gate.html`
2. Try logging in with Google
3. Submit a test request

## Troubleshooting

### Database Issues
The SQLite database resets on each deployment. For production:
- Use Render PostgreSQL (free tier available)
- Or keep SQLite and re-import students after each deploy

### Logs
View logs in Render dashboard → Your service → **Logs** tab

### Cold Starts
Free tier sleeps after 15 min of inactivity. First request takes ~30 seconds.

## Your Live URL
After deployment, share this with everyone:
**https://gateway-app.onrender.com/front_gate.html**

🎉 No localhost, no ngrok, accessible worldwide!
