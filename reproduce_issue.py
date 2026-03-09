
import sqlite3
import os
import random
import string
import time
from datetime import datetime, timedelta

def get_db():
    conn = sqlite3.connect('gateway.db')
    conn.row_factory = sqlite3.Row
    return conn

def simulate_submit(student_id, date, time_val):
    print(f"\n--- Simulating submit for student {student_id} on {date} ---")
    conn = get_db()
    c = conn.cursor()
    
    try:
        # Check duplicate
        c.execute('''
          SELECT * FROM requests 
          WHERE student_id = ? AND leave_date = ? AND status IN ('PENDING_PARENT', 'PENDING_TEACHER', 'PENDING_HOD')
        ''', (student_id, date))
        
        existing = c.fetchone()
        if existing:
            print(f"FAILED: Already has a pending request for {date} (ID: {existing['id']})")
            conn.close()
            return False
            
        # Get student
        c.execute('SELECT * FROM users WHERE id = ?', (student_id,))
        student = c.fetchone()
        if not student:
            print("FAILED: Student not found")
            conn.close()
            return False
            
        # Insert
        token = 'TOKEN_' + str(int(time.time())) + '_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=9))
        request_id = 'REQ_' + str(int(time.time()))
        
        c.execute('''
          INSERT INTO requests (
            request_id, student_id, student_name, student_roll, student_class, student_department,
            parent_phone, request_type, reason, leave_date, leave_time, expires_at,
            status, parent_token, token_expiry
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
          request_id, student_id, student['name'], student['roll_number'], student['class'], student['department'],
          student['parent_email'], 'Casual', 'Testing reproduction', date, time_val, f"{date} {time_val}",
          'PENDING_PARENT', token, (datetime.utcnow() + timedelta(hours=24)).isoformat()
        ))
        
        conn.commit()
        print(f"SUCCESS: Request submitted (ID: {c.lastrowid})")
        conn.close()
        return True
    except Exception as e:
        print(f"CRASH: {e}")
        if conn: conn.close()
        return False

def test():
    # 1. Get a test student ID
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE role = 'student' LIMIT 1")
    row = c.fetchone()
    if not row:
        print("No student found in DB")
        return
    student_id = row['id']
    conn.close()
    
    # 2. Submit first request
    today = datetime.now().strftime("%Y-%m-%d")
    simulate_submit(student_id, today, "10:00")
    
    # 3. Submit duplicate request (should fail gracefully)
    simulate_submit(student_id, today, "11:00")
    
    # 4. Submit request for different date
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    simulate_submit(student_id, tomorrow, "10:00")

if __name__ == "__main__":
    test()
