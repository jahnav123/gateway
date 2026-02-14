# OTP-Based Email Authentication

## Overview
The system now uses **email-based OTP (One-Time Password)** authentication instead of storing passwords. This provides better security and eliminates the need to manage password storage.

## How It Works

### 1. User Enters Identifier
- Students: Enter roll number (e.g., `L9`)
- Teachers/HODs: Enter email (e.g., `jahnavi@gmail.com`)

### 2. System Sends OTP
- 6-digit verification code generated
- Sent to user's registered email
- Valid for 5 minutes

### 3. User Verifies OTP
- Enter the 6-digit code from email
- System validates and logs in
- JWT token issued for 24-hour session

## Security Features

✅ **No Password Storage** - Passwords removed from database  
✅ **Time-Limited OTP** - Expires in 5 minutes  
✅ **One-Time Use** - OTP deleted after verification  
✅ **Email Verification** - Confirms user has access to registered email  

## User Experience

**Login Flow:**
1. Enter email or roll number
2. Click "Send Verification Code"
3. Check email for 6-digit code
4. Enter code and click "Verify & Login"
5. Redirected to dashboard

## Technical Details

- **OTP Storage:** In-memory (use Redis for production)
- **OTP Length:** 6 digits
- **OTP Expiry:** 5 minutes
- **Session Duration:** 24 hours (JWT)
- **Email Service:** Gmail SMTP

## Migration Notes

- Old password-based login still available at `/api/auth/login` (for backward compatibility)
- New OTP endpoints: `/api/auth/send-otp` and `/api/auth/verify-otp`
- Frontend updated to use OTP flow by default

## Production Recommendations

1. **Use Redis** for OTP storage (instead of in-memory)
2. **Rate Limiting** on OTP requests (prevent spam)
3. **IP Tracking** for suspicious activity
4. **Backup Authentication** method (SMS, authenticator app)
5. **Audit Logging** for all login attempts
