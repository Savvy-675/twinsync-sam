from src.config.db import db
from src.__init__ import create_app
from sqlalchemy import text

app = create_app()
with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE users ADD COLUMN active_usage_today INTEGER DEFAULT 0"))
        db.session.execute(text("ALTER TABLE users ADD COLUMN total_screen_time_today INTEGER DEFAULT 0"))
        db.session.commit()
        print("Database patched successfully.")
    except Exception as e:
        print(f"Database prefix error (might already exist): {e}")
