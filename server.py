from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import bcrypt
import jwt
from datetime import datetime, timedelta
import os
import time
import random
import string
import re
from google.oauth2 import id_token
from google.auth.transport import requests
from dotenv import load_dotenv
from db_connection import get_db
from email_service import (
  send_parent_approval_email,
  send_approval_notification_email,
  send_rejection_notification_email
)

# Load environment variables
load_dotenv()

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
ALLOWED_EMAIL_DOMAIN = 'bvrithyderabad.edu.in'
ENFORCE_DOMAIN_RESTRICTION = os.getenv('ENFORCE_DOMAIN_RESTRICTION', 'false').lower() == 'true'

# Role mapping - HODs and Teachers by email
HOD_EMAILS = ['25wh1a05l9@bvrithyderabad.edu.in'] # Temporary testing HOD
TEACHER_EMAILS = ['sundari.m@bvrithyderabad.edu.in']

# Teacher class assignments
TEACHER_CLASSES = {
  'sundari.m@bvrithyderabad.edu.in': 'CS-B'
}

def is_valid_email(email):
  """Validate email format"""
  pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
  return re.match(pattern, email) is not None

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

# Serve static HTML files
@app.get("/front_gate.html")
async def serve_front_gate():
  return FileResponse("front_gate.html")

@app.get("/parent-approve.html")
async def serve_parent_approve():
  return FileResponse("parent-approve.html")

@app.get("/")
async def root():
  return FileResponse("front_gate.html")

JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'

# Security check for production
if JWT_SECRET == 'your-secret-key-change-in-production':
  print('⚠️ WARNING: Using default JWT_SECRET. Set JWT_SECRET in .env for production!')

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

# ADMIN - Import students (temporary endpoint)
@app.post('/api/admin/import-students')
def import_students():
  """Import initial students - remove after use"""
  students = [
    ('student', '25wh1a05d1@bvrithyderabad.edu.in', 'NAGA JAHNAVI BANDARUPALLI', 'CSE', 'CS-A', '25WH1A05D1', '0000000000', 'watermelon37453@gmail.com'),
    ('student', 'student2@bvrithyderabad.edu.in', 'Sample Student 2', 'CSE', 'CS-A', '25WH1A05D2', '0000000000', 'parent2@gmail.com'),
    ('student', 'student3@bvrithyderabad.edu.in', 'Sample Student 3', 'CSE', 'CS-B', '25WH1A05D3', '0000000000', 'parent3@gmail.com'),
    ('teacher', '25wh1a05k1@bvrithyderabad.edu.in', 'KODURI KRITHI', 'CSE', 'CS-A', None, None, None),
    ('hod', '25wh1a05l9@bvrithyderabad.edu.in', 'BHAKTI BALU TAKEY', 'CSE', '', None, None, None),
    ('student', '25wh1a05g5@bvrithyderabad.edu.in', 'Student G5', 'CSE', 'CS-A', '25WH1A05G5', '0000000000', 'kruthikab21@gmail.com'),
  ]
  
  conn = get_db()
  c = conn.cursor()
  imported = 0
  
  for student in students:
    try:
      c.execute('''
        INSERT INTO users (role, email, name, department, class, roll_number, parent_phone, parent_email)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
      ''', student)
      imported += 1
    except:
      pass # Skip if already exists
  
  conn.commit()
  conn.close()
  
  return {'message': f'Imported {imported} users'}

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
    email = idinfo.get('email', '')
    name = idinfo.get('name', email.split('@')[0] if email else 'User')
    
    # Validate email exists
    if not email:
      raise HTTPException(status_code=400, detail='Email not found in token')
    
    # Domain restriction (configurable)
    if ENFORCE_DOMAIN_RESTRICTION:
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
    c.execute('SELECT * FROM users WHERE email = %s ', (email,))
    existing_user = c.fetchone()
    
    if existing_user:
      user_id = existing_user['id']
      user_name = existing_user['name']
      user_class = existing_user['class']
      user_dept = existing_user['department']
      user_roll = existing_user['roll_number']
    else:
      conn.close()
      raise HTTPException(
        status_code=403, 
        detail='User not registered. Please contact admin.'
      )
    
    conn.close()
    
    # Generate user data
    user_data = {
      'id': user_id,
      'email': email,
      'role': role,
      'name': user_name,
      'class': user_class,
      'department': user_dept,
      'roll_number': user_roll
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
  except HTTPException:
    raise
  except ValueError as e:
    error_msg = str(e)
    print(f'❌ OAuth ValueError: {error_msg}')
    raise HTTPException(status_code=401, detail=f'Invalid token: {error_msg}')
  except Exception as e:
    error_msg = f"{type(e).__name__}: {str(e)}"
    print(f'❌ OAuth Exception: {error_msg}')
    # Include the error in the detail for debugging
    raise HTTPException(status_code=500, detail=f'Auth Error: {error_msg}')

@app.post('/api/auth/login')
def login(req: LoginRequest):
  conn = get_db()
  c = conn.cursor()
  
  # Try to find user by roll number (student) or email (teacher/hod)
  identifier = req.identifier.strip()
  
  # First try as roll number (student)
  c.execute('SELECT * FROM users WHERE roll_number = %s ', (identifier.upper(),))
  user = c.fetchone()
  
  # If not found, try as email (teacher/hod)
  if not user:
    c.execute('SELECT * FROM users WHERE email = %s ', (identifier.lower(),))
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
  
  # Validate date and time
  try:
    leave_datetime = datetime.strptime(f"{req.date} {req.time}", "%Y-%m-%d %H:%M")
    if leave_datetime <= datetime.now():
      raise HTTPException(status_code=400, detail='Leave date and time must be in the future')
  except ValueError:
    raise HTTPException(status_code=400, detail='Invalid date or time format')
  
  conn = get_db()
  c = conn.cursor()
  
  # Check duplicate with transaction
  c.execute('BEGIN IMMEDIATE')
  try:
    c.execute('''
      SELECT * FROM requests 
      WHERE student_id = %s AND leave_date = %s AND status IN ('PENDING_PARENT', 'PENDING_TEACHER', 'PENDING_HOD')
    ''', (user['id'], req.date))
    
    if c.fetchone():
      conn.rollback()
      conn.close()
      raise HTTPException(status_code=400, detail='You already have a pending request for this date')
    
    # Get student
    c.execute('SELECT * FROM users WHERE id = %s ', (user['id'],))
    student = c.fetchone()
    
    if not student:
      conn.rollback()
      conn.close()
      raise HTTPException(status_code=400, detail=f'Student record not found for user ID {user["id"]}. Please logout and login again.')
    
    if not student['parent_email']:
      conn.rollback()
      conn.close()
      raise HTTPException(status_code=400, detail='Parent email not configured. Please contact admin.')
    
    # Validate parent email format
    if not is_valid_email(student['parent_email']):
      conn.rollback()
      conn.close()
      raise HTTPException(status_code=400, detail='Invalid parent email format. Please contact admin.')
    
    # Generate token
    token = 'TOKEN_' + str(int(time.time())) + '_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=9))
    token_expiry = (datetime.utcnow() + timedelta(hours=24)).isoformat()
    request_id = 'REQ_' + str(int(time.time()))
    
    c.execute('''
      INSERT INTO requests (
        request_id, student_id, student_name, student_roll, student_class, student_department,
        parent_phone, request_type, reason, leave_date, leave_time, expires_at,
        status, parent_token, token_expiry
      ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (
      request_id, user['id'], student['name'], student['roll_number'], student['class'], student['department'],
      student['parent_email'], req.type, req.reason, req.date, req.time, f"{req.date} {req.time}",
      'PENDING_PARENT', token, token_expiry
    ))
    
    conn.commit()
    last_id = c.lastrowid
  except HTTPException:
    conn.rollback()
    raise
  except Exception as e:
    conn.rollback()
    conn.close()
    raise HTTPException(status_code=500, detail=f'Failed to submit request: {str(e)}')
  
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
  c.execute('SELECT * FROM requests WHERE student_id = %s ORDER BY submitted_at DESC', (user['id'],))
  requests = [dict(row) for row in c.fetchall()]
  conn.close()
  
  return requests

@app.post('/api/student/cancel/{id}')
def cancel_request(id: int, user = Depends(verify_token)):
  if user['role'] != 'student':
    raise HTTPException(status_code=403, detail='Access denied')
  
  conn = get_db()
  c = conn.cursor()
  c.execute('SELECT * FROM requests WHERE id = %s AND student_id = %s ', (id, user['id']))
  request = c.fetchone()
  
  if not request:
    conn.close()
    raise HTTPException(status_code=404, detail='Request not found')
  
  if request['status'] not in ['PENDING_PARENT', 'PENDING_TEACHER', 'PENDING_HOD']:
    conn.close()
    raise HTTPException(status_code=400, detail='Cannot cancel this request')
  
  c.execute('UPDATE requests SET status = %s , cancelled_at = CURRENT_TIMESTAMP WHERE id = %s ', ('CANCELLED_BY_STUDENT', id))
  conn.commit()
  
  # No email sent to parent on cancellation
  
  conn.close()
  
  return {'message': 'Request cancelled successfully'}

# PARENT
@app.get('/api/parent/request/{token}')
def get_parent_request(token: str):
  conn = get_db()
  c = conn.cursor()
  c.execute('SELECT * FROM requests WHERE parent_token = %s ', (token,))
  request = c.fetchone()
  conn.close()
  
  if not request:
    raise HTTPException(status_code=404, detail='Invalid or expired token')
  
  try:
    token_expiry = datetime.fromisoformat(request['token_expiry'])
    if token_expiry < datetime.utcnow():
      raise HTTPException(status_code=400, detail='This approval link has expired')
  except (ValueError, TypeError):
    raise HTTPException(status_code=400, detail='Invalid token expiry format')
  
  if request['token_used']:
    raise HTTPException(status_code=400, detail='This approval link has already been used')
  
  return dict(request)

@app.post('/api/parent/approve/{token}')
def approve_parent(token: str):
  conn = get_db()
  c = conn.cursor()
  c.execute('SELECT * FROM requests WHERE parent_token = %s ', (token,))
  request = c.fetchone()
  
  if not request:
    conn.close()
    raise HTTPException(status_code=404, detail='Invalid token')
  
  try:
    token_expiry = datetime.fromisoformat(request['token_expiry'])
    if token_expiry < datetime.utcnow():
      conn.close()
      raise HTTPException(status_code=400, detail='Token expired')
  except (ValueError, TypeError):
    conn.close()
    raise HTTPException(status_code=400, detail='Invalid token expiry format')
  
  if request['token_used']:
    conn.close()
    raise HTTPException(status_code=400, detail='Token already used')
  
  # Emergency requests auto-approve, casual requests go to teacher
  if request['request_type'].lower() == 'emergency':
    c.execute('''
      UPDATE requests 
      SET status = 'APPROVED', parent_status = 'approved', token_used = 1, 
        parent_approved_at = CURRENT_TIMESTAMP,
        teacher_status = 'auto_approved', teacher_approved_at = CURRENT_TIMESTAMP,
        hod_status = 'auto_approved', hod_approved_at = CURRENT_TIMESTAMP
      WHERE parent_token = %s 
    ''', (token,))
    conn.commit()
    
    # Send approval notification
    c.execute('SELECT u.email, u.parent_email, r.student_name, r.leave_date, r.leave_time FROM requests r JOIN users u ON r.student_id = u.id WHERE r.parent_token = %s ', (token,))
    data = c.fetchone()
    conn.close()
    
    if data:
      if data['email']:
        send_approval_notification_email(data['email'], data['student_name'], data['leave_date'], data['leave_time'])
      if data['parent_email']:
        send_approval_notification_email(data['parent_email'], data['student_name'], data['leave_date'], data['leave_time'])
    
    return {'message': 'Emergency request approved successfully (auto-approved)'}
  else:
    c.execute('''
      UPDATE requests 
      SET status = 'PENDING_TEACHER', parent_status = 'approved', token_used = 1, parent_approved_at = CURRENT_TIMESTAMP
      WHERE parent_token = %s 
    ''', (token,))
    conn.commit()
    conn.close()
    
    return {'message': 'Request approved successfully'}

@app.post('/api/parent/reject/{token}')
def reject_parent(token: str, req: RejectRequest):
  conn = get_db()
  c = conn.cursor()
  c.execute('SELECT * FROM requests WHERE parent_token = %s ', (token,))
  request = c.fetchone()
  
  if not request:
    conn.close()
    raise HTTPException(status_code=404, detail='Invalid token')
  
  try:
    token_expiry = datetime.fromisoformat(request['token_expiry'])
    if token_expiry < datetime.utcnow():
      conn.close()
      raise HTTPException(status_code=400, detail='Token expired')
  except (ValueError, TypeError):
    conn.close()
    raise HTTPException(status_code=400, detail='Invalid token expiry format')
  
  if request['token_used']:
    conn.close()
    raise HTTPException(status_code=400, detail='Token already used')
  
  c.execute('''
    UPDATE requests 
    SET status = 'REJECTED_BY_PARENT', parent_status = 'rejected', token_used = 1, 
      parent_approved_at = CURRENT_TIMESTAMP, parent_rejection_reason = %s 
    WHERE parent_token = %s 
  ''', (req.reason, token))
  conn.commit()
  
  # Get student email to send notification
  c.execute('SELECT u.email, r.student_name FROM requests r JOIN users u ON r.student_id = u.id WHERE r.parent_token = %s ', (token,))
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
  # Show pending casual requests + approved emergency requests for visibility
  c.execute('''
    SELECT * FROM requests 
    WHERE student_class = %s AND (
      status = 'PENDING_TEACHER' OR 
      (status = 'APPROVED' AND request_type = 'Emergency')
    )
    ORDER BY submitted_at DESC
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
  c.execute('SELECT * FROM requests WHERE id = %s ', (id,))
  request = c.fetchone()
  
  if not request or request['status'] != 'PENDING_TEACHER':
    conn.close()
    raise HTTPException(status_code=400, detail='Invalid request')
  
  c.execute('''
    UPDATE requests 
    SET status = 'PENDING_HOD', teacher_status = 'approved', teacher_approved_at = CURRENT_TIMESTAMP
    WHERE id = %s 
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
  c.execute('SELECT * FROM requests WHERE id = %s ', (id,))
  request = c.fetchone()
  
  if not request or request['status'] != 'PENDING_TEACHER':
    conn.close()
    raise HTTPException(status_code=400, detail='Invalid request')
  
  c.execute('''
    UPDATE requests 
    SET status = 'REJECTED_BY_TEACHER', teacher_status = 'rejected', 
      teacher_approved_at = CURRENT_TIMESTAMP, teacher_rejection_reason = %s 
    WHERE id = %s 
  ''', (req.reason, id))
  conn.commit()
  
  # Get student and parent emails
  c.execute('SELECT u.email, u.parent_email, r.student_name FROM requests r JOIN users u ON r.student_id = u.id WHERE r.id = %s ', (id,))
  data = c.fetchone()
  conn.close()
  
  # Send rejection notification to student and parent
  if data:
    if data['email']:
      send_rejection_notification_email(data['email'], data['student_name'], 'Teacher', req.reason)
    if data['parent_email'] and is_valid_email(data['parent_email']):
      send_rejection_notification_email(data['parent_email'], data['student_name'], 'Teacher', req.reason)
  
  return {'message': 'Request rejected successfully'}

# HOD
@app.get('/api/hod/requests/pending')
def get_hod_requests(user = Depends(verify_token)):
  if user['role'] != 'hod':
    raise HTTPException(status_code=403, detail='Access denied')
  
  conn = get_db()
  c = conn.cursor()
  # Show pending casual requests + approved emergency requests for visibility
  c.execute('''
    SELECT * FROM requests 
    WHERE student_department = %s AND (
      status = 'PENDING_HOD' OR 
      (status = 'APPROVED' AND request_type = 'Emergency')
    )
    ORDER BY submitted_at DESC
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
  c.execute('SELECT * FROM requests WHERE id = %s ', (id,))
  request = c.fetchone()
  
  if not request or request['status'] != 'PENDING_HOD':
    conn.close()
    raise HTTPException(status_code=400, detail='Invalid request')
  
  c.execute('''
    UPDATE requests 
    SET status = 'APPROVED', hod_status = 'approved', hod_approved_at = CURRENT_TIMESTAMP
    WHERE id = %s 
  ''', (id,))
  conn.commit()
  
  # Get student and parent emails
  c.execute('SELECT u.email, u.parent_email, r.student_name, r.leave_date, r.leave_time FROM requests r JOIN users u ON r.student_id = u.id WHERE r.id = %s ', (id,))
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
  c.execute('SELECT * FROM requests WHERE id = %s ', (id,))
  request = c.fetchone()
  
  if not request or request['status'] != 'PENDING_HOD':
    conn.close()
    raise HTTPException(status_code=400, detail='Invalid request')
  
  c.execute('''
    UPDATE requests 
    SET status = 'REJECTED_BY_HOD', hod_status = 'rejected', 
      hod_approved_at = CURRENT_TIMESTAMP, hod_rejection_reason = %s 
    WHERE id = %s 
  ''', (req.reason, id))
  conn.commit()
  
  # Get student and parent emails
  c.execute('SELECT u.email, u.parent_email, r.student_name FROM requests r JOIN users u ON r.student_id = u.id WHERE r.id = %s ', (id,))
  data = c.fetchone()
  conn.close()
  
  # Send rejection notification to student and parent
  if data:
    if data['email']:
      send_rejection_notification_email(data['email'], data['student_name'], 'HOD', req.reason)
    if data['parent_email'] and is_valid_email(data['parent_email']):
      send_rejection_notification_email(data['parent_email'], data['student_name'], 'HOD', req.reason)
  
  return {'message': 'Request rejected successfully'}

if __name__ == '__main__':
  import uvicorn
  uvicorn.run(app, host='0.0.0.0', port=3000)
# Deployment timestamp: Sun Mar 8 14:02:29 IST 2026
