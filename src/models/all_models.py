import datetime
from src.config.db import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')
    preferences = db.Column(db.String(255))
    
    # ML & Core Stats
    productivity_score = db.Column(db.Float, default=0.0)
    delay_rate = db.Column(db.Float, default=0.0)
    peak_focus_time = db.Column(db.String(50), default='Morning')
    avg_duration_mins = db.Column(db.Float, default=45.0)
    personality_type = db.Column(db.String(100), default='Learning...')
    learning_multiplier = db.Column(db.Float, default=1.0)
    daily_goal = db.Column(db.Integer, default=5)
    
    # Scheduling Preferences
    user_type = db.Column(db.String(50), default='Student')
    working_hours_start = db.Column(db.String(10), default='09:00')
    working_hours_end = db.Column(db.String(10), default='17:00')
    preferred_work_time = db.Column(db.String(50), default='Morning')
    
    # ML Tracking
    ml_accuracy = db.Column(db.Float, default=0.0)
    ml_samples = db.Column(db.Integer, default=0)
    ml_last_trained = db.Column(db.String(100), default='Never')
    
    # Screen Time & Usage
    active_usage_today = db.Column(db.Integer, default=0)
    total_screen_time_today = db.Column(db.Integer, default=0)
    daily_screen_time_goal = db.Column(db.Integer, default=120) # in minutes

    # Personalized Email Sync
    imap_server = db.Column(db.String(100))
    smtp_server = db.Column(db.String(100))
    email_user = db.Column(db.String(120))
    email_pass_encrypted = db.Column(db.String(255))

    tasks = db.relationship('Task', backref='user', lazy=True)
    logs = db.relationship('ActivityLog', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    priority = db.Column(db.String(50))
    category = db.Column(db.String(50), index=True)
    deadline = db.Column(db.DateTime, index=True)
    status = db.Column(db.String(50), default='pending', index=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    estimated_duration = db.Column(db.Integer, default=30)
    scheduled_for = db.Column(db.DateTime)
    
    # Prediction fields
    risk_score = db.Column(db.String(100), default='Low')
    risk_reason = db.Column(db.Text, default='')
    smart_priority_score = db.Column(db.Float, default=0.0)
    
    # Email deduplication: SHA1 hash of (user_id + email subject + sender)
    email_hash = db.Column(db.String(64), index=True, nullable=True)

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Insight(db.Model):
    __tablename__ = 'insights'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recommendation = db.Column(db.Text, nullable=False)
    reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Goal(db.Model):
    __tablename__ = 'goals'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(50))
    target = db.Column(db.Integer)
    progress = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class ChatLog(db.Model):
    __tablename__ = 'chat_logs'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(50))
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
