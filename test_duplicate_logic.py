
import sqlite3
import os

def get_db():
    conn = sqlite3.connect('gateway.db')
    conn.row_factory = sqlite3.Row
    return conn

def test_check():
    print("--- Testing Pending Request Block Logic ---")
    conn = get_db()
    c = conn.cursor()
    
    # 1. Verify User ID 1 exists
    student_id = 1
    c.execute("SELECT * FROM users WHERE id = ?", (student_id,))
    user = c.fetchone()
    if not user:
        print("CRITICAL: User ID 1 not found!")
        return
    print(f"User found: {user['name']} (ID: {user['id']})")

    # 2. Check for ANY pending requests for this user
    print(f"Checking for pending requests for Student ID {student_id}...")
    c.execute('''
      SELECT id, status, request_type FROM requests 
      WHERE student_id = ? AND status IN ('PENDING_PARENT', 'PENDING_TEACHER', 'PENDING_HOD')
    ''', (student_id,))
    
    pending = c.fetchall()
    if pending:
        print(f"✅ FOUND {len(pending)} pending requests:")
        for r in pending:
            print(f" - ID: {r['id']}, Status: {r['status']}, Type: {r['request_type']}")
        print("Result: The BLOCK logic SHOULD trigger.")
    else:
        print("❌ NO pending requests found.")
        print("Result: The BLOCK logic will NOT trigger (Submission allowed).")
        
        # Debug: Show ALL requests for this user to see why
        print("DEBUG: All requests for this user:")
        c.execute("SELECT id, status FROM requests WHERE student_id = ?", (student_id,))
        all_reqs = c.fetchall()
        for r in all_reqs:
            print(f" - ID: {r['id']}, Status: '{r['status']}'")

    conn.close()

if __name__ == "__main__":
    test_check()
