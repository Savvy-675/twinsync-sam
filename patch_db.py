import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'instance', 'digital-twins.db')
if not os.path.exists(db_path):
    print("Database not found, new deployment will create it.")
    exit(0)

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Try adding User columns
    try:
        cur.execute("ALTER TABLE users ADD COLUMN user_type VARCHAR(50) DEFAULT 'Student'")
        cur.execute("ALTER TABLE users ADD COLUMN working_hours_start VARCHAR(10) DEFAULT '09:00'")
        cur.execute("ALTER TABLE users ADD COLUMN working_hours_end VARCHAR(10) DEFAULT '17:00'")
        cur.execute("ALTER TABLE users ADD COLUMN preferred_work_time VARCHAR(50) DEFAULT 'Morning'")
        print("Added new columns to users table.")
    except Exception as e:
        print(f"Users table might already have columns: {e}")

    # Try adding Task columns
    try:
        cur.execute("ALTER TABLE tasks ADD COLUMN smart_priority_score FLOAT DEFAULT 0.0")
        print("Added new column to tasks table.")
    except Exception as e:
        print(f"Tasks table might already have column: {e}")

    conn.commit()
    conn.close()
    print("DB patch complete.")
except Exception as e:
    print(f"Could not patch DB: {e}")
