# Quick Start - Google OAuth

## 🚀 Fast Setup (5 minutes)

### 1. Get Google Credentials
Visit: https://console.cloud.google.com/
- Create new project
- Enable Google+ API
- Create OAuth Client ID (Web application)
- Copy Client ID and Client Secret

### 2. Run Setup Script
```bash
./setup_oauth.sh
```
Paste your Client ID and Client Secret when prompted.

### 3. Start Server
```bash
python server.py
```

### 4. Test
Open: http://192.168.18.104:8080/front_gate.html

---

## 📝 Manual Setup

### Update .env:
```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

### Update front_gate.html (line ~53):
```html
data-client_id="your-client-id.apps.googleusercontent.com"
```

### Install dependencies:
```bash
pip install -r requirements.txt
```

---

## 🔧 Configure User Roles

Edit `server.py` (lines 20-21):
```python
HOD_EMAILS = ['hod@example.com']
TEACHER_EMAILS = ['teacher@example.com']
```

---

## ❓ Troubleshooting

**"Invalid Client ID"**
→ Check Client ID matches in both `.env` and `front_gate.html`

**"Redirect URI mismatch"**
→ Add your URL to Authorized JavaScript origins in Google Console

**"Access blocked"**
→ Add test users in OAuth consent screen

---

## 📚 Full Documentation
- `GOOGLE_OAUTH_SETUP.md` - Detailed setup guide
- `OAUTH_MIGRATION.md` - Technical details
