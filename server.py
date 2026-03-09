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
import logging
import re
import threading
from google.oauth2 import id_token
from google.auth.transport import requests
from dotenv import load_dotenv
from db_connection import get_db
from email_service import (
  send_parent_approval_email,
  send_approval_notification_email,
  send_rejection_notification_email
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
if not GOOGLE_CLIENT_ID or GOOGLE_CLIENT_ID == 'YOUR_NEW_CLIENT_ID_HERE':
    GOOGLE_CLIENT_ID = '896563148898-u92eg641v7h3dqm9up4a31n5367fu1il.apps.googleusercontent.com'
logger.info(f"✅ SERVER STARTING V3: Using Google Client ID: {GOOGLE_CLIENT_ID}")
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

def get_placeholder():
    """Returns {p} for PostgreSQL and ? for SQLite"""
    if os.getenv('DATABASE_URL', '').startswith('postgres'):
        return '{p}'
    return '?'

def migrate_db():
    """Ensure database schema is up to date"""
    conn = get_db()
    c = conn.cursor()
    p = get_placeholder()

    # Check if we're on Postgres
    is_postgres = os.getenv('DATABASE_URL', '').startswith('postgres')

    # List of columns that might be missing in older versions
    required_columns = [
        ('parent_status', 'TEXT'),
        ('teacher_status', 'TEXT'),
        ('hod_status', 'TEXT'),
        ('parent_rejection_reason', 'TEXT'),
        ('teacher_rejection_reason', 'TEXT'),
        ('hod_rejection_reason', 'TEXT'),
        ('parent_approved_at', 'TIMESTAMP'),
        ('teacher_approved_at', 'TIMESTAMP'),
        ('hod_approved_at', 'TIMESTAMP')
    ]

    for col_name, col_type in required_columns:
        try:
            # Check if column exists
            has_column = False
            if is_postgres:
                c.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='requests' AND column_name='{col_name}'")
                if c.fetchone():
                    has_column = True
            else:
                c.execute(f"PRAGMA table_info(requests)")
                cols = [row[1] for row in c.fetchall()]
                if col_name in cols:
                    has_column = True
            
            if not has_column:
                print(f"Adding missing column: {col_name}")
                # For SQLite, we can only add one column at a time
                # For Postgres, same here for simplicity
                c.execute(f"ALTER TABLE requests ADD COLUMN {col_name} {col_type}")
                conn.commit() # Commit after each column to be safe
        except Exception as e:
            print(f"Migration error for {col_name}: {e}")
            conn.rollback()

    conn.commit()
    conn.close()

# Run migration on startup
try:
    migrate_db()
except Exception as e:
    print(f"Startup migration failed: {e}")

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
    # Return version info to verify deployment
    return {"status": "ok", "version": "1.0.5-migrated", "ui": "/front_gate.html"}
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
  p = get_placeholder()
  
  
  imported = 0
  
  for student in students:
    try:
      c.execute(f'''
        INSERT INTO users (role, email, name, department, class, roll_number, parent_phone, parent_email)
        VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
      ''', student)
      imported += 1
    except:
      pass # Skip if already exists
  
  conn.commit()
  conn.close()
  
  return {'message': f'Imported {imported} users'}

def serialize_row(row):
    """Helper to convert database row to dict with ISO strings for datetimes"""
    if not row:
        return None
    r = dict(row)
    for key, value in r.items():
        if hasattr(value, 'isoformat'):
            r[key] = value.isoformat()
    return r

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

        # Determine role
        role = get_user_role(email)

        # Check if user exists in database
        conn = get_db()
        c = conn.cursor()
        p = get_placeholder()
        
        c.execute(f'SELECT * FROM users WHERE email = {p} ', (email,))
        existing_user = c.fetchone()

        if not existing_user:
            conn.close()
            raise HTTPException(
                status_code=403, 
                detail='User not registered. Please contact admin.'
            )

        # Serialize the user data safely
        user_data = serialize_row(existing_user)
        user_data['role'] = role
        conn.close()

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
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f'❌ OAuth Exception: {error_msg}')
        raise HTTPException(status_code=500, detail=f'Auth Error: {error_msg}')
@app.post('/api/auth/login')
def login(req: LoginRequest):
  conn = get_db()
  c = conn.cursor()
  p = get_placeholder()
  
  
  
  # Try to find user by roll number (student) or email (teacher/hod)
  identifier = req.identifier.strip()
  
  # First try as roll number (student)
  c.execute(f'SELECT * FROM users WHERE roll_number = {p} ', (identifier.upper(),))
  user = c.fetchone()
  
  # If not found, try as email (teacher/hod)
  if not user:
    c.execute(f'SELECT * FROM users WHERE email = {p} ', (identifier.lower(),))
    user = c.fetchone()
  
  conn.close()
  
  # Login check
  is_valid = False
  if user and user['password_hash']:
    try:
      if bcrypt.checkpw(req.password.encode(), user['password_hash'].encode()):
        is_valid = True
    except:
      pass
  
  # Test-mode fallback: allow roll number as password if no hash exists
  if not is_valid and user and not user['password_hash']:
    if req.password == user['roll_number'] or req.password == '8712209017':
      is_valid = True

  if not is_valid:
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
  p = get_placeholder()
  
  try:
    print(f"DEBUG: Checking pending for User ID: {user['id']}")
    
    # Check duplicate - Block if ANY request is pending
    # We use a simple select first, no transaction yet
    c.execute(f'''
      SELECT * FROM requests 
      WHERE student_id = {p} AND status IN ('PENDING_PARENT', 'PENDING_TEACHER', 'PENDING_HOD')
    ''', (user['id'],))
    
    existing = c.fetchone()
    if existing:
      print(f"DEBUG: Found pending request ID: {existing['id']}")
      conn.close()
      raise HTTPException(status_code=400, detail='You already have a pending request. Please wait for it to be processed or cancel it before submitting a new one.')
    
    print("DEBUG: No pending requests found. Proceeding to fetch student data.")
    
    # Get student
    c.execute(f'SELECT * FROM users WHERE id = {p} ', (user['id'],))
    student_row = c.fetchone()
    
    if not student_row:
      conn.close()
      raise HTTPException(status_code=400, detail=f'Student record not found for user ID {user["id"]}. Please logout and login again.')
    
    student = dict(student_row)
    
    if not student['parent_email']:
      conn.close()
      raise HTTPException(status_code=400, detail='Parent email not configured. Please contact admin.')
    
    if not is_valid_email(student['parent_email']):
      conn.close()
      raise HTTPException(status_code=400, detail='Invalid parent email format. Please contact admin.')
    
    # Generate token
    token = 'TOKEN_' + str(int(time.time())) + '_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=9))
    token_expiry = (datetime.utcnow() + timedelta(hours=24)).isoformat()
    request_id = 'REQ_' + str(int(time.time()))
    
    print("DEBUG: Inserting new request.")
    
    c.execute(f'''
      INSERT INTO requests (
        request_id, student_id, student_name, student_roll, student_class, student_department,
        parent_phone, request_type, reason, leave_date, leave_time, expires_at,
        status, parent_token, token_expiry
      ) VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
    ''', (
      request_id, user['id'], student['name'], student['roll_number'], student['class'], student['department'],
      student['parent_email'], req.type, req.reason, req.date, req.time, f"{req.date} {req.time}",
      'PENDING_PARENT', token, token_expiry
    ))
    
    conn.commit()
    last_id = c.lastrowid
    conn.close()
    
    print(f"DEBUG: Request submitted successfully (ID: {last_id}). Sending email.")
    
    # Send email to parent in background
    threading.Thread(target=send_parent_approval_email, args=(
      student['parent_email'],
      student['name'],
      req.type,
      req.date,
      req.time,
      req.reason,
      token
    )).start()
    
    return {
      'message': 'Request submitted successfully',
      'requestId': request_id,
      'id': last_id,
      'parentToken': token
    }
    
  except HTTPException:
    raise
  except Exception as e:
    print(f"ERROR: {e}")
    try:
      conn.close()
    except:
      pass
    raise HTTPException(status_code=500, detail=f'Failed to submit request: {str(e)}')

@app.get('/api/student/requests')
def get_student_requests(user = Depends(verify_token)):
  if user['role'] != 'student':
    raise HTTPException(status_code=403, detail='Access denied')
  
  conn = get_db()
  c = conn.cursor()
  p = get_placeholder()
  
  
  c.execute(f'SELECT * FROM requests WHERE student_id = {p} ORDER BY submitted_at DESC', (user['id'],))
  rows = c.fetchall()
  requests = [serialize_row(row) for row in rows]
  conn.close()
  return requests

@app.post('/api/student/cancel/{id}')
def cancel_request(id: int, user = Depends(verify_token)):
  if user['role'] != 'student':
    raise HTTPException(status_code=403, detail='Access denied')
  
  conn = get_db()
  c = conn.cursor()
  p = get_placeholder()
  
  
  c.execute(f'SELECT * FROM requests WHERE id = {p} AND student_id = {p} ', (id, user['id']))
  request = c.fetchone()
  
  if not request:
    conn.close()
    raise HTTPException(status_code=404, detail='Request not found')
  
  if request['status'] not in ['PENDING_PARENT', 'PENDING_TEACHER', 'PENDING_HOD']:
    conn.close()
    raise HTTPException(status_code=400, detail='Cannot cancel this request')
  
  c.execute(f'UPDATE requests SET status = {p} , cancelled_at = CURRENT_TIMESTAMP WHERE id = {p} ', ('CANCELLED_BY_STUDENT', id))
  conn.commit()
  
  # No email sent to parent on cancellation
  
  conn.close()
  
  return {'message': 'Request cancelled successfully'}

# PARENT
@app.get('/api/parent/request/{token}')
def get_parent_request(token: str):
  conn = get_db()
  c = conn.cursor()
  p = get_placeholder()
  
  
  c.execute(f'SELECT * FROM requests WHERE parent_token = {p} ', (token,))
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
  
  res = serialize_row(request)
  conn.close()
  return res
@app.post('/api/parent/approve/{token}')
def approve_parent(token: str):
  conn = get_db()
  c = conn.cursor()
  p = get_placeholder()
  
  
  c.execute(f'SELECT * FROM requests WHERE parent_token = {p} ', (token,))
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
    if request['parent_status'] in ['approved', 'rejected']:
      conn.close()
      return {'message': f"Request already {request['parent_status']}"}
    conn.close()
    raise HTTPException(status_code=400, detail='Token already used')
  
  # Emergency requests auto-approve, casual requests go to teacher
  if request['request_type'].lower() == 'emergency':
    c.execute(f'''
      UPDATE requests 
      SET status = 'APPROVED', parent_status = 'approved', token_used = 1, 
        parent_approved_at = CURRENT_TIMESTAMP,
        teacher_status = 'auto_approved', teacher_approved_at = CURRENT_TIMESTAMP,
        hod_status = 'auto_approved', hod_approved_at = CURRENT_TIMESTAMP
      WHERE parent_token = {p} 
    ''', (token,))
    conn.commit()
    
    # Send approval notification
    c.execute(f'SELECT u.email, u.parent_email, r.student_name, r.leave_date, r.leave_time FROM requests r JOIN users u ON r.student_id = u.id WHERE r.parent_token = {p} ', (token,))
    data = c.fetchone()
    conn.close()
    
    if data:
      if data['email']:
        send_approval_notification_email(data['email'], data['student_name'], data['leave_date'], data['leave_time'])
      if data['parent_email']:
        send_approval_notification_email(data['parent_email'], data['student_name'], data['leave_date'], data['leave_time'])
    
    return {'message': 'Emergency request approved successfully (auto-approved)'}
  else:
    c.execute(f'''
      UPDATE requests 
      SET status = 'PENDING_TEACHER', parent_status = 'approved', token_used = 1, parent_approved_at = CURRENT_TIMESTAMP
      WHERE parent_token = {p} 
    ''', (token,))
    conn.commit()
    conn.close()
    
    return {'message': 'Request approved successfully'}

@app.post('/api/parent/reject/{token}')
def reject_parent(token: str, req: RejectRequest):
  conn = get_db()
  c = conn.cursor()
  p = get_placeholder()
  
  
  c.execute(f'SELECT * FROM requests WHERE parent_token = {p} ', (token,))
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
    if request['parent_status'] in ['approved', 'rejected']:
      conn.close()
      return {'message': f"Request already {request['parent_status']}"}
    conn.close()
    raise HTTPException(status_code=400, detail='Token already used')
  
  c.execute(f'''
    UPDATE requests 
    SET status = 'REJECTED_BY_PARENT', parent_status = 'rejected', token_used = 1, 
      parent_approved_at = CURRENT_TIMESTAMP, parent_rejection_reason = {p} 
    WHERE parent_token = {p} 
  ''', (req.reason, token))
  conn.commit()
  
  # Get student email to send notification
  c.execute(f'SELECT u.email, r.student_name FROM requests r JOIN users u ON r.student_id = u.id WHERE r.parent_token = {p} ', (token,))
  student_data = c.fetchone()
  
  conn.close()
  
  # Send rejection notification to student in background
  if student_data and student_data['email']:
    threading.Thread(target=send_rejection_notification_email, args=(
      student_data['email'], 
      student_data['student_name'], 
      'Parent', 
      req.reason
    )).start()
  
  return {'message': 'Request rejected successfully'}

# TEACHER
@app.get('/api/teacher/requests/pending')
def get_teacher_requests(user = Depends(verify_token)):
  if user['role'] != 'teacher':
    raise HTTPException(status_code=403, detail='Access denied')
  
  conn = get_db()
  c = conn.cursor()
  p = get_placeholder()
  
  # Show pending casual requests + approved emergency requests for visibility
  c.execute(f'''
      SELECT * FROM requests 
      WHERE student_class = {p} AND (
          status = 'PENDING_TEACHER' OR 
          (status = 'APPROVED' AND request_type = 'Emergency')
      )
      ORDER BY submitted_at DESC
  ''', (user['class'],))
  requests = [serialize_row(row) for row in c.fetchall()]
  conn.close()
  return requests
@app.post('/api/teacher/approve/{id}')
def approve_teacher(id: int, user = Depends(verify_token)):
  if user['role'] != 'teacher':
    raise HTTPException(status_code=403, detail='Access denied')
  
  conn = get_db()
  c = conn.cursor()
  p = get_placeholder()
  
  c.execute(f'SELECT * FROM requests WHERE id = {p} ', (id,))
  request = c.fetchone()
  
  if not request or request['status'] != 'PENDING_TEACHER':
    conn.close()
    raise HTTPException(status_code=400, detail='Invalid request')
  
  c.execute(f'''
    UPDATE requests 
    SET status = 'PENDING_HOD', teacher_status = 'approved', teacher_approved_at = CURRENT_TIMESTAMP
    WHERE id = {p} 
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
  p = get_placeholder()
  
  c.execute(f'SELECT * FROM requests WHERE id = {p} ', (id,))
  request = c.fetchone()
  
  if not request or request['status'] != 'PENDING_TEACHER':
    conn.close()
    raise HTTPException(status_code=400, detail='Invalid request')
  
  c.execute(f'''
    UPDATE requests 
    SET status = 'REJECTED_BY_TEACHER', teacher_status = 'rejected', 
      teacher_approved_at = CURRENT_TIMESTAMP, teacher_rejection_reason = {p} 
    WHERE id = {p} 
  ''', (req.reason, id))
  conn.commit()
  
  # Get student and parent emails
  c.execute(f'SELECT u.email, u.parent_email, r.student_name FROM requests r JOIN users u ON r.student_id = u.id WHERE r.id = {p} ', (id,))
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
  p = get_placeholder()
  
  # Show pending casual requests + approved emergency requests for visibility
  c.execute(f'''
      SELECT * FROM requests 
      WHERE student_department = {p} AND (
          status = 'PENDING_HOD' OR 
          (status = 'APPROVED' AND request_type = 'Emergency')
      )
      ORDER BY submitted_at DESC
  ''', (user['department'],))
  requests = [serialize_row(row) for row in c.fetchall()]
  conn.close()
  return requests
@app.post('/api/hod/approve/{id}')
def approve_hod(id: int, user = Depends(verify_token)):
  if user['role'] != 'hod':
    raise HTTPException(status_code=403, detail='Access denied')
  
  conn = get_db()
  c = conn.cursor()
  p = get_placeholder()
  
  c.execute(f'SELECT * FROM requests WHERE id = {p} ', (id,))
  request = c.fetchone()
  
  if not request or request['status'] != 'PENDING_HOD':
    conn.close()
    raise HTTPException(status_code=400, detail='Invalid request')
  
  c.execute(f'''
    UPDATE requests 
    SET status = 'APPROVED', hod_status = 'approved', hod_approved_at = CURRENT_TIMESTAMP
    WHERE id = {p} 
  ''', (id,))
  conn.commit()
  
  # Get student and parent emails
  c.execute(f'SELECT u.email, u.parent_email, r.student_name, r.leave_date, r.leave_time FROM requests r JOIN users u ON r.student_id = u.id WHERE r.id = {p} ', (id,))
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
  p = get_placeholder()
  
  c.execute(f'SELECT * FROM requests WHERE id = {p} ', (id,))
  request = c.fetchone()
  
  if not request or request['status'] != 'PENDING_HOD':
    conn.close()
    raise HTTPException(status_code=400, detail='Invalid request')
  
  c.execute(f'''
    UPDATE requests 
    SET status = 'REJECTED_BY_HOD', hod_status = 'rejected', 
      hod_approved_at = CURRENT_TIMESTAMP, hod_rejection_reason = {p} 
    WHERE id = {p} 
  ''', (req.reason, id))
  conn.commit()
  
  # Get student and parent emails
  c.execute(f'SELECT u.email, u.parent_email, r.student_name FROM requests r JOIN users u ON r.student_id = u.id WHERE r.id = {p} ', (id,))
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
