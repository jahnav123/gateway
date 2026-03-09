
import requests
import json
import sys
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8080/api"

# Test data
STUDENT_ROLL = "25WH1A05D1"
STUDENT_PASS = "25WH1A05D1" # Falling back to roll number
TEACHER_EMAIL = "25wh1a05k1@bvrithyderabad.edu.in"
TEACHER_PASS = "8712209017" # Test-mode fallback password
HOD_EMAIL = "25wh1a05l9@bvrithyderabad.edu.in"
HOD_PASS = "8712209017" # Test-mode fallback password

def log(msg):
    print(f"\n[TEST] {msg}")

def test_full_flow():
    session = requests.Session()
    
    # 1. Login as Student
    log("Logging in as Student...")
    resp = session.post(f"{BASE_URL}/auth/login", json={
        "identifier": STUDENT_ROLL,
        "password": STUDENT_PASS
    })
    if resp.status_code != 200:
        print(f"FAILED LOGIN: {resp.text}")
        return
    student_token = resp.json()['token']
    headers = {"Authorization": f"Bearer {student_token}"}
    log("Student Login Successful.")

    # 2. Cleanup existing pending requests for this student to start fresh
    import sqlite3
    conn = sqlite3.connect('gateway.db')
    c = conn.cursor()
    c.execute("DELETE FROM requests WHERE student_id = 1")
    conn.commit()
    conn.close()
    log("Cleaned up old requests for student ID 1.")

    # 3. Submit first Casual Request
    log("Submitting Casual Request...")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    req_data = {
        "type": "casual",
        "reason": "Family function",
        "date": tomorrow,
        "time": "10:00"
    }
    resp = session.post(f"{BASE_URL}/student/request", json=req_data, headers=headers)
    if resp.status_code != 200:
        print(f"FAILED SUBMIT: {resp.text}")
        return
    parent_token = resp.json()['parentToken']
    request_id_db = resp.json()['id']
    log(f"Casual Request Submitted (ID: {request_id_db}). Parent Token: {parent_token}")

    log("Attempting DUPLICATE submission (should be blocked)...")
    resp = session.post(f"{BASE_URL}/student/request", json=req_data, headers=headers)
    if resp.status_code == 400:
        log(f"SUCCESS: Blocked correctly. Message: {resp.json()['detail']}")
    else:
        log(f"FAILED: Duplicate was NOT blocked. Status: {resp.status_code}")

    # 4.5 Test Cancellation
    log("Attempting to CANCEL the request...")
    resp = session.post(f"{BASE_URL}/student/cancel/{request_id_db}", headers=headers)
    if resp.status_code == 200:
        log("Cancellation Successful.")
        # Re-submit to continue the rest of the flow
        log("Re-submitting for flow testing...")
        resp = session.post(f"{BASE_URL}/student/request", json=req_data, headers=headers)
        parent_token = resp.json()['parentToken']
        request_id_db = resp.json()['id']
    else:
        log(f"FAILED Cancellation: {resp.text}")
        return

    # 5. Parent Approval
    log("Simulating Parent Approval...")
    resp = requests.post(f"{BASE_URL}/parent/approve/{parent_token}")
    if resp.status_code == 200:
        log("Parent Approval Successful.")
    else:
        log(f"Parent Approval Failed: {resp.text}")

    # 6. Teacher Login & Approval
    log("Logging in as Teacher...")
    resp = session.post(f"{BASE_URL}/auth/login", json={
        "identifier": TEACHER_EMAIL,
        "password": TEACHER_PASS
    })
    teacher_token = resp.json()['token']
    t_headers = {"Authorization": f"Bearer {teacher_token}"}
    
    log("Teacher Approving...")
    resp = session.post(f"{BASE_URL}/teacher/approve/{request_id_db}", headers=t_headers)
    if resp.status_code == 200:
        log("Teacher Approval Successful.")
    else:
        log(f"Teacher Approval Failed: {resp.text}")

    # 7. HOD Login & Approval
    log("Logging in as HOD...")
    resp = session.post(f"{BASE_URL}/auth/login", json={
        "identifier": HOD_EMAIL,
        "password": HOD_PASS
    })
    hod_token = resp.json()['token']
    h_headers = {"Authorization": f"Bearer {hod_token}"}
    
    log("HOD Approving...")
    resp = session.post(f"{BASE_URL}/hod/approve/{request_id_db}", headers=h_headers)
    if resp.status_code == 200:
        log("HOD Approval Successful.")
    else:
        log(f"HOD Approval Failed: {resp.text}")

    # 8. Verify Final Status
    log("Verifying final status as Student...")
    resp = session.get(f"{BASE_URL}/student/requests", headers=headers)
    final_req = [r for r in resp.json() if r['id'] == request_id_db][0]
    log(f"Final Request Status: {final_req['status']}")
    if final_req['status'] == 'APPROVED':
        log("✅ CASUAL FLOW TEST PASSED!")
    else:
        log("❌ CASUAL FLOW TEST FAILED!")

    # 9. Emergency Flow (Auto-approves Teacher/HOD)
    log("\n--- Testing Emergency Flow ---")
    # First, cancel or delete previous to allow new one
    conn = sqlite3.connect('gateway.db')
    c = conn.cursor()
    c.execute("DELETE FROM requests WHERE student_id = 1")
    conn.commit()
    conn.close()
    
    log("Submitting Emergency Request...")
    req_data['type'] = 'emergency'
    resp = session.post(f"{BASE_URL}/student/request", json=req_data, headers=headers)
    e_parent_token = resp.json()['parentToken']
    e_req_id = resp.json()['id']
    
    log("Parent Approving Emergency...")
    resp = requests.post(f"{BASE_URL}/parent/approve/{e_parent_token}")
    log(f"Parent Status: {resp.status_code}")
    
    log("Verifying Auto-Approval Status...")
    resp = session.get(f"{BASE_URL}/student/requests", headers=headers)
    e_req = [r for r in resp.json() if r['id'] == e_req_id][0]
    log(f"Emergency Status: {e_req['status']}")
    if e_req['status'] == 'APPROVED':
        log("✅ EMERGENCY FLOW TEST PASSED!")
    else:
        log("❌ EMERGENCY FLOW TEST FAILED!")

if __name__ == "__main__":
    try:
        test_full_flow()
    except Exception as e:
        print(f"Test crashed: {e}")
