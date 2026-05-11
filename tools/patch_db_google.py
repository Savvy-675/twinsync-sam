import os
import sqlite3
from src.config.config import Config

def patch():
    # Detect if we are using SQLite or PostgreSQL
    db_url = Config.SQLALCHEMY_DATABASE_URI
    
    if db_url.startswith('sqlite'):
        db_path = db_url.replace('sqlite:///', '')
        # If relative path, join with instance folder or base dir
        if not os.path.isabs(db_path):
            # Try to find the file
            potential_paths = [
                os.path.join(os.getcwd(), db_path),
                os.path.join(os.getcwd(), 'instance', db_path),
                db_path
            ]
            for p in potential_paths:
                if os.path.exists(p):
                    db_path = p
                    break
        
        print(f"Patching SQLite database at: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN google_token TEXT")
            print("Added google_token")
        except Exception as e:
            print(f"Skipping google_token: {e}")
            
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN google_refresh_token TEXT")
            print("Added google_refresh_token")
        except Exception as e:
            print(f"Skipping google_refresh_token: {e}")
            
        conn.commit()
        conn.close()
        print("SQLite patch complete.")
        
    else:
        # For PostgreSQL, we still need sqlalchemy but we use a raw connection
        from sqlalchemy import create_engine, text
        engine = create_engine(db_url)
        with engine.connect() as conn:
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN google_token TEXT"))
                conn.commit()
                print("Added google_token")
            except Exception as e:
                print(f"Skipping google_token: {e}")
                
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN google_refresh_token TEXT"))
                conn.commit()
                print("Added google_refresh_token")
            except Exception as e:
                print(f"Skipping google_refresh_token: {e}")
        print("PostgreSQL patch complete.")

if __name__ == "__main__":
    patch()
