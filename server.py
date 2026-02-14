from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sqlite3
import bcrypt
import jwt
from datetime import datetime, timedelta
import os
import time
import random
import string
from google.oauth2 import id_token
from google.auth.transport import requests
from email_service import (
    send_parent_approval_email,
    send_approval_notification_email,
    send_rejection_notification_email,
    send_cancellation_notification_email
)

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
ALLOWED_EMAIL_DOMAIN = 'bvrithyderabad.edu.in'

# Role mapping - HODs and Teachers by email
HOD_EMAILS = ['25wh1a05l9@bvrithyderabad.edu.in']  # Temporary testing HOD
TEACHER_EMAILS = ['sundari.m@bvrithyderabad.edu.in', '25wh1a05k1@bvrithyderabad.edu.in']

def get_user_role(email):
    """Determine user role based on email"""
    email_lower = email.lower().strip()
    if email_lower in HOD_EMAILS:
        return 'hod'
    elif email_lower in TEACHER_EMAILS:
        return 'teacher'
    else:
        return 'student'

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'

def get_db():
    conn = sqlite3.connect('gateway.db')
    conn.row_factory = sqlite3.Row
    return conn

def verify_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='No token provided')
    token = authorization.split(' ')[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except:
        raise HTTPException(status_code=401, detail='Invalid token')

# Models
class LoginRequest(BaseModel):
    identifier: str
    password: str

class GoogleAuthRequest(BaseModel):
    token: str

class RequestSubmit(BaseModel):
    type: str
    reason: str
    date: str
    time: str

class RejectRequest(BaseModel):
    reason: Optional[str] = None

# AUTH
@app.post('/api/auth/google')
def google_auth(req: GoogleAuthRequest):
    """Authenticate user with Google OAuth token"""
    try:
        # Verify the Google token
        idinfo = id_token.verify_oauth2_token(
            req.token, 
            requests.Request(), 
            GOOGLE_CLIENT_ID
        )
        
        # Extract user info
        email = idinfo['email']
        name = idinfo.get('name', email.split('@')[0])
        
        # Check if email is from allowed domain
        email_domain = email.split('@')[1] if '@' in email else ''
        if email_domain != ALLOWED_EMAIL_DOMAIN:
            raise HTTPException(
                status_code=403, 
                detail=f'Access denied. Only @{ALLOWED_EMAIL_DOMAIN} emails are allowed.'
            )
        
        # Determine role
        role = get_user_role(email)
        
        # Check if user exists in database
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE email = ?', (email,))
        existing_user = c.fetchone()
        
        if existing_user:
            user_id = existing_user['id']
        else:
            # Create new user in database
            # Note: parent_phone column in requests table actually stores parent_email
            parent_email = f"parent.{email.split('@')[0]}@gmail.com"  # Generate parent email
            c.execute('''
                INSERT INTO users (role, email, name, department, class, roll_number, parent_phone, parent_email)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (role, email, name, 'CSE', 'CS-A' if role == 'student' else '', '', '0000000000', parent_email))
            conn.commit()
            user_id = c.lastrowid
        
        conn.close()
        
        # Generate user data
        user_data = {
            'id': user_id,
            'email': email,
            'role': role,
            'name': name,
            'class': 'CS-A' if role == 'student' else '',
            'department': 'CSE',
            'roll_number': ''
        }
        
        # Generate JWT token
        token = jwt.encode({
            'id': user_data['id'],
            'role': role,
            'email': email,
            'name': user_data['name'],
            'class': user_data['class'],
            'department': user_data['department'],
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        return {
            'token': token,
            'user': user_data
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail='Invalid Google token')

@app.post('/api/auth/login')
def login(req: LoginRequest):
    conn = get_db()
    c = conn.cursor()
    
    # Try to find user by roll number (student) or email (teacher/hod)
    identifier = req.identifier.strip()
    
    # First try as roll number (student)
    c.execute('SELECT * FROM users WHERE roll_number = ?', (identifier.upper(),))
    user = c.fetchone()
    
    # If not found, try as email (teacher/hod)
    if not user:
        c.execute('SELECT * FROM users WHERE email = ?', (identifier.lower(),))
        user = c.fetchone()
    
    conn.close()
    
    if not user or not bcrypt.checkpw(req.password.encode(), user['password_hash'].encode()):
        raise HTTPException(status_code=401, detail='Invalid credentials')
    
    token = jwt.encode({
        'id': user['id'],
        'role': user['role'],
        'name': user['name'],
        'class': user['class'],
        'department': user['department'],
        'roll_number': user['roll_number'],
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    return {
        'token': token,
        'user': {
            'id': user['id'],
            'name': user['name'],
            'role': user['role'],
            'class': user['class'],
            'department': user['department'],
            'roll_number': user['roll_number']
        }
    }

# STUDENT
@app.post('/api/student/request')
def submit_request(req: RequestSubmit, user = Depends(verify_token)):
    if user['role'] != 'student':
        raise HTTPException(status_code=403, detail='Access denied')
    
    conn = get_db()
    c = conn.cursor()
    
    # Check duplicate
    c.execute('''
        SELECT * FROM requests 
        WHERE student_id = ? AND leave_date = ? AND status IN ('PENDING_PARENT', 'PENDING_TEACHER', 'PENDING_HOD')
    ''', (user['id'], req.date))
    
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail='You already have a pending request for this date')
    
    # Get student
    c.execute('SELECT * FROM users WHERE id = ?', (user['id'],))
    student = c.fetchone()
    
    if not student['parent_email']:
        conn.close()
        raise HTTPException(status_code=400, detail='Parent email not configured. Please contact admin.')
    
    # Generate token
    token = 'TOKEN_' + str(int(time.time())) + '_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=9))
    token_expiry = (datetime.utcnow() + timedelta(hours=24)).isoformat()
    request_id = 'REQ_' + str(int(time.time()))
    
    c.execute('''
        INSERT INTO requests (
            request_id, student_id, student_name, student_roll, student_class, student_department,
            parent_phone, request_type, reason, leave_date, leave_time, expires_at,
            status, parent_token, token_expiry
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        request_id, user['id'], student['name'], student['roll_number'], student['class'], student['department'],
        student['parent_email'], req.type, req.reason, req.date, req.time, f"{req.date} {req.time}",
        'PENDING_PARENT', token, token_expiry
    ))
    
    conn.commit()
    last_id = c.lastrowid
    conn.close()
    
    # Send email to parent
    send_parent_approval_email(
        student['parent_email'],
        student['name'],
        req.type,
        req.date,
        req.time,
        req.reason,
        token
    )
    
    return {
        'message': 'Request submitted successfully',
        'requestId': request_id,
        'id': last_id,
        'parentToken': token
    }

@app.get('/api/student/requests')
def get_student_requests(user = Depends(verify_token)):
    if user['role'] != 'student':
        raise HTTPException(status_code=403, detail='Access denied')
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM requests WHERE student_id = ? ORDER BY submitted_at DESC', (user['id'],))
    requests = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return requests

@app.post('/api/student/cancel/{id}')
def cancel_request(id: int, user = Depends(verify_token)):
    if user['role'] != 'student':
        raise HTTPException(status_code=403, detail='Access denied')
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM requests WHERE id = ? AND student_id = ?', (id, user['id']))
    request = c.fetchone()
    
    if not request:
        conn.close()
        raise HTTPException(status_code=404, detail='Request not found')
    
    if request['status'] not in ['PENDING_PARENT', 'PENDING_TEACHER', 'PENDING_HOD']:
        conn.close()
        raise HTTPException(status_code=400, detail='Cannot cancel this request')
    
    c.execute('UPDATE requests SET status = ?, cancelled_at = CURRENT_TIMESTAMP WHERE id = ?', ('CANCELLED_BY_STUDENT', id))
    conn.commit()
    
    # Send cancellation notification to parent email
    if request['parent_phone']:  # Will update to parent_email
        c.execute('SELECT parent_email FROM users WHERE id = ?', (request['student_id'],))
        parent = c.fetchone()
        if parent and parent['parent_email']:
            send_cancellation_notification_email(parent['parent_email'], request['student_name'])
    
    conn.close()
    
    return {'message': 'Request cancelled successfully'}

# PARENT
@app.get('/api/parent/request/{token}')
def get_parent_request(token: str):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM requests WHERE parent_token = ?', (token,))
    request = c.fetchone()
    conn.close()
    
    if not request:
        raise HTTPException(status_code=404, detail='Invalid or expired token')
    
    if datetime.fromisoformat(request['token_expiry']) < datetime.utcnow():
        raise HTTPException(status_code=400, detail='This approval link has expired')
    
    if request['token_used']:
        raise HTTPException(status_code=400, detail='This approval link has already been used')
    
    return dict(request)

@app.post('/api/parent/approve/{token}')
def approve_parent(token: str):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM requests WHERE parent_token = ?', (token,))
    request = c.fetchone()
    
    if not request:
        conn.close()
        raise HTTPException(status_code=404, detail='Invalid token')
    
    if datetime.fromisoformat(request['token_expiry']) < datetime.utcnow():
        conn.close()
        raise HTTPException(status_code=400, detail='Token expired')
    
    if request['token_used']:
        conn.close()
        raise HTTPException(status_code=400, detail='Token already used')
    
    c.execute('''
        UPDATE requests 
        SET status = 'PENDING_TEACHER', parent_status = 'approved', token_used = 1, parent_approved_at = CURRENT_TIMESTAMP
        WHERE parent_token = ?
    ''', (token,))
    conn.commit()
    conn.close()
    
    return {'message': 'Request approved successfully'}

@app.post('/api/parent/reject/{token}')
def reject_parent(token: str, req: RejectRequest):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM requests WHERE parent_token = ?', (token,))
    request = c.fetchone()
    
    if not request:
        conn.close()
        raise HTTPException(status_code=404, detail='Invalid token')
    
    if datetime.fromisoformat(request['token_expiry']) < datetime.utcnow():
        conn.close()
        raise HTTPException(status_code=400, detail='Token expired')
    
    if request['token_used']:
        conn.close()
        raise HTTPException(status_code=400, detail='Token already used')
    
    c.execute('''
        UPDATE requests 
        SET status = 'REJECTED_BY_PARENT', parent_status = 'rejected', token_used = 1, 
            parent_approved_at = CURRENT_TIMESTAMP, parent_rejection_reason = ?
        WHERE parent_token = ?
    ''', (req.reason, token))
    conn.commit()
    
    # Get student email to send notification
    c.execute('SELECT u.email, r.student_name FROM requests r JOIN users u ON r.student_id = u.id WHERE r.parent_token = ?', (token,))
    student_data = c.fetchone()
    
    conn.close()
    
    # Send rejection notification to student
    if student_data and student_data['email']:
        send_rejection_notification_email(student_data['email'], student_data['student_name'], 'Parent', req.reason)
    
    return {'message': 'Request rejected successfully'}

# TEACHER
@app.get('/api/teacher/requests/pending')
def get_teacher_requests(user = Depends(verify_token)):
    if user['role'] != 'teacher':
        raise HTTPException(status_code=403, detail='Access denied')
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT * FROM requests 
        WHERE status = 'PENDING_TEACHER' AND student_class = ?
        ORDER BY submitted_at ASC
    ''', (user['class'],))
    requests = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return requests

@app.post('/api/teacher/approve/{id}')
def approve_teacher(id: int, user = Depends(verify_token)):
    if user['role'] != 'teacher':
        raise HTTPException(status_code=403, detail='Access denied')
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM requests WHERE id = ?', (id,))
    request = c.fetchone()
    
    if not request or request['status'] != 'PENDING_TEACHER':
        conn.close()
        raise HTTPException(status_code=400, detail='Invalid request')
    
    c.execute('''
        UPDATE requests 
        SET status = 'PENDING_HOD', teacher_status = 'approved', teacher_approved_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (id,))
    conn.commit()
    conn.close()
    
    return {'message': 'Request approved successfully'}

@app.post('/api/teacher/reject/{id}')
def reject_teacher(id: int, req: RejectRequest, user = Depends(verify_token)):
    if user['role'] != 'teacher':
        raise HTTPException(status_code=403, detail='Access denied')
    
    if not req.reason:
        raise HTTPException(status_code=400, detail='Rejection reason required')
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM requests WHERE id = ?', (id,))
    request = c.fetchone()
    
    if not request or request['status'] != 'PENDING_TEACHER':
        conn.close()
        raise HTTPException(status_code=400, detail='Invalid request')
    
    c.execute('''
        UPDATE requests 
        SET status = 'REJECTED_BY_TEACHER', teacher_status = 'rejected', 
            teacher_approved_at = CURRENT_TIMESTAMP, teacher_rejection_reason = ?
        WHERE id = ?
    ''', (req.reason, id))
    conn.commit()
    conn.close()
    
    return {'message': 'Request rejected successfully'}

# HOD
@app.get('/api/hod/requests/pending')
def get_hod_requests(user = Depends(verify_token)):
    if user['role'] != 'hod':
        raise HTTPException(status_code=403, detail='Access denied')
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT * FROM requests 
        WHERE status = 'PENDING_HOD' AND student_department = ?
        ORDER BY submitted_at ASC
    ''', (user['department'],))
    requests = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return requests

@app.post('/api/hod/approve/{id}')
def approve_hod(id: int, user = Depends(verify_token)):
    if user['role'] != 'hod':
        raise HTTPException(status_code=403, detail='Access denied')
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM requests WHERE id = ?', (id,))
    request = c.fetchone()
    
    if not request or request['status'] != 'PENDING_HOD':
        conn.close()
        raise HTTPException(status_code=400, detail='Invalid request')
    
    c.execute('''
        UPDATE requests 
        SET status = 'APPROVED', hod_status = 'approved', hod_approved_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (id,))
    conn.commit()
    
    # Get student and parent emails
    c.execute('SELECT u.email, u.parent_email, r.student_name, r.leave_date, r.leave_time FROM requests r JOIN users u ON r.student_id = u.id WHERE r.id = ?', (id,))
    data = c.fetchone()
    
    conn.close()
    
    # Send approval email to student and parent
    if data:
        if data['email']:
            send_approval_notification_email(data['email'], data['student_name'], data['leave_date'], data['leave_time'])
        if data['parent_email']:
            send_approval_notification_email(data['parent_email'], data['student_name'], data['leave_date'], data['leave_time'])
    
    return {'message': 'Request approved successfully'}

@app.post('/api/hod/reject/{id}')
def reject_hod(id: int, req: RejectRequest, user = Depends(verify_token)):
    if user['role'] != 'hod':
        raise HTTPException(status_code=403, detail='Access denied')
    
    if not req.reason:
        raise HTTPException(status_code=400, detail='Rejection reason required')
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM requests WHERE id = ?', (id,))
    request = c.fetchone()
    
    if not request or request['status'] != 'PENDING_HOD':
        conn.close()
        raise HTTPException(status_code=400, detail='Invalid request')
    
    c.execute('''
        UPDATE requests 
        SET status = 'REJECTED_BY_HOD', hod_status = 'rejected', 
            hod_approved_at = CURRENT_TIMESTAMP, hod_rejection_reason = ?
        WHERE id = ?
    ''', (req.reason, id))
    conn.commit()
    conn.close()
    
    return {'message': 'Request rejected successfully'}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=3000)
