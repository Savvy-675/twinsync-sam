import sqlite3
import os

db_path = "instance/digital-twins.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN active_usage_today INTEGER DEFAULT 0")
        print("Added active_usage_today")
    except Exception as e:
        print(f"Error active_usage_today: {e}")
        
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN total_screen_time_today INTEGER DEFAULT 0")
        print("Added total_screen_time_today")
    except Exception as e:
        print(f"Error total_screen_time_today: {e}")
        
    conn.commit()
    conn.close()
    print("Direct SQLite migration complete.")
else:
    print(f"Database not found at {db_path}")
