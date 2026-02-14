# User Roles and Login Credentials

## Role Assignment

The system automatically assigns roles based on email addresses:

### 🔴 HOD (Head of Department)
- **Email:** bhaktitakey@gmail.com
- **Dashboard:** HOD Dashboard (approve/reject requests from all departments)

### 🔵 Teacher
- **Email:** kruthikab21@gmail.com
- **Dashboard:** Teacher Dashboard (approve/reject requests from their class)

### 🟢 Student (Default)
- **Email:** krithi9koduri@gmail.com (or any other email)
- **Dashboard:** Student Dashboard (submit and track requests)

---

## How to Login

1. **Go to:** http://192.168.18.104:8080/front_gate.html
2. **Enter your email address**
3. **Click:** "📧 Send Verification Code"
4. **Check your email** for 6-digit OTP
5. **Enter OTP** and click "✓ Verify & Login"
6. **Automatically redirected** to your role-specific dashboard

---

## Adding New Users

### To add a new HOD:
Edit `server.py` line ~22:
```python
HOD_EMAILS = ['bhaktitakey@gmail.com', 'newhod@gmail.com']
```

### To add a new Teacher:
Edit `server.py` line ~23:
```python
TEACHER_EMAILS = ['kruthikab21@gmail.com', 'newteacher@gmail.com']
```

### To add a new Student:
No changes needed - any email not in HOD or Teacher lists is automatically a student.

---

## System Features

✅ **No Database Required** - Role mapping in code  
✅ **No Password Storage** - OTP-based authentication  
✅ **Email Verification** - Secure 6-digit codes  
✅ **Auto Role Detection** - Based on email address  
✅ **24-Hour Sessions** - JWT tokens for convenience  

---

## Current Active Users

| Email | Role | Dashboard Access |
|-------|------|------------------|
| bhaktitakey@gmail.com | HOD | All department requests |
| kruthikab21@gmail.com | Teacher | Class-specific requests |
| krithi9koduri@gmail.com | Student | Submit & track own requests |
| (any other email) | Student | Submit & track own requests |
