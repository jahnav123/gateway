import os
import bcrypt
from datetime import datetime
from db_connection import get_db

def init_database():
    """Initialize database - works with both SQLite and PostgreSQL"""
    conn = get_db()
    c = conn.cursor()
    
    is_postgres = os.getenv('DATABASE_URL', '').startswith('postgres')
    
    # Auto-increment syntax differs
    auto_increment = 'SERIAL PRIMARY KEY' if is_postgres else 'INTEGER PRIMARY KEY AUTOINCREMENT'
    timestamp_default = 'CURRENT_TIMESTAMP' if not is_postgres else 'CURRENT_TIMESTAMP'
    
    print("Creating tables...")
    
    # Create users table
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS users (
            id {auto_increment},
            role TEXT NOT NULL,
            email TEXT,
            password_hash TEXT,
            phone_number TEXT,
            name TEXT NOT NULL,
            department TEXT,
            class TEXT,
            roll_number TEXT UNIQUE,
            parent_phone TEXT,
            parent_email TEXT,
            parent_name TEXT,
            created_at TIMESTAMP DEFAULT {timestamp_default}
        )
    ''')
    
    # Create requests table
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS requests (
            id {auto_increment},
            request_id TEXT UNIQUE NOT NULL,
            student_id INTEGER NOT NULL,
            student_name TEXT NOT NULL,
            student_roll TEXT NOT NULL,
            student_class TEXT NOT NULL,
            student_department TEXT NOT NULL,
            parent_phone TEXT NOT NULL,
            request_type TEXT NOT NULL,
            reason TEXT NOT NULL,
            leave_date TEXT NOT NULL,
            leave_time TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            status TEXT NOT NULL,
            parent_token TEXT UNIQUE,
            token_expiry TEXT,
            token_used INTEGER DEFAULT 0,
            parent_status TEXT,
            teacher_status TEXT,
            hod_status TEXT,
            submitted_at TIMESTAMP DEFAULT {timestamp_default},
            parent_approved_at TIMESTAMP,
            teacher_approved_at TIMESTAMP,
            hod_approved_at TIMESTAMP,
            parent_rejection_reason TEXT,
            teacher_rejection_reason TEXT,
            hod_rejection_reason TEXT
        )
    ''')
    
    conn.commit()
    
    # Check if users exist
    c.execute('SELECT COUNT(*) as count FROM users')
    result = c.fetchone()
    user_count = result['count'] if is_postgres else result[0]
    
    if user_count == 0:
        print("Seeding initial users...")
        
        # Hash password for testing
        password = bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt())
        
        # Insert sample users
        users = [
            ('student', '25wh1a05d1@bvrithyderabad.edu.in', 'NAGA JAHNAVI BANDARUPALLI', 'CS-A', 'CSE', '25WH1A05D1', 'watermelon37453@gmail.com', 'Parent One', '9876543210'),
            ('student', '25wh1a05k1@bvrithyderabad.edu.in', 'Jahnavi Bandarupalli', 'CS-A', 'CSE', '25WH1A05K1', 'parent1@gmail.com', 'Parent One', '9876543210'),
            ('student', 'student2@bvrithyderabad.edu.in', 'Student Two', 'CS-A', 'CSE', 'CS002', 'parent2@gmail.com', 'Parent Two', '9876543211'),
            ('teacher', 'sundari.m@bvrithyderabad.edu.in', 'Sundari M', 'CS-B', 'CSE', None, None, None, None),
            ('hod', '25wh1a05l9@bvrithyderabad.edu.in', 'HOD CSE', None, 'CSE', None, None, None, None),
        ]
        
        for user in users:
            c.execute('''
                INSERT INTO users (role, email, name, class, department, roll_number, parent_email, parent_name, parent_phone)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''' if is_postgres else '''
                INSERT INTO users (role, email, name, class, department, roll_number, parent_email, parent_name, parent_phone)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', user)
        
        conn.commit()
        print(f"✅ Seeded {len(users)} users")
    else:
        print(f"✅ Database already has {user_count} users")
    
    conn.close()
    print("✅ Database initialization complete!")

if __name__ == '__main__':
    init_database()
