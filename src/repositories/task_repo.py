from src.models.all_models import Task, User
from src.config.db import db
import datetime

class TaskRepository:
    @staticmethod
    def get_all_by_user(user_id):
        # Multi-user cloud isolation
        return Task.query.filter_by(user_id=user_id).order_by(Task.deadline.asc()).all()

    @staticmethod
    def get_pending_by_user(user_id):
        return Task.query.filter_by(user_id=user_id, status='pending').all()

    @staticmethod
    def get_completed_history(user_id, limit=50):
        # Persistent storage retrieval
        return Task.query.filter_by(user_id=user_id, status='completed').order_by(Task.completed_at.desc()).limit(limit).all()

    @staticmethod
    def calculate_priority_from_deadline(deadline):
        """Auto-assign priority based on days remaining until deadline."""
        if not deadline:
            return 'medium'
        now = datetime.datetime.utcnow()
        if isinstance(deadline, str):
            deadline = datetime.datetime.fromisoformat(deadline)
        days_left = (deadline - now).total_seconds() / 86400
        if days_left < 1:
            return 'critical'
        elif days_left <= 3:
            return 'high'
        elif days_left <= 7:
            return 'medium'
        else:
            return 'low'

    @staticmethod
    def create(data):
        deadline = data.get('deadline')
        if isinstance(deadline, str) and deadline:
            try:
                # JS 'Z' format is not supported in all python versions, swap with explicit +00:00
                deadline = deadline.replace('Z', '+00:00')
                deadline = datetime.datetime.fromisoformat(deadline)
            except ValueError:
                # If AI returns something non-ISO, fallback safely
                deadline = datetime.datetime.utcnow() + datetime.timedelta(days=7)
        elif not deadline:
            deadline = datetime.datetime.utcnow() + datetime.timedelta(days=7)

        # Auto-assign priority from deadline if not specified
        priority = data.get('priority') or TaskRepository.calculate_priority_from_deadline(deadline)

        task = Task(
            user_id=data['user_id'],
            title=data['title'],
            category=data.get('category', 'general'),
            priority=priority,
            estimated_duration=data.get('estimated_duration', 30),
            deadline=deadline,
            email_hash=data.get('email_hash')  # None for manual/chat tasks
        )
        db.session.add(task)
        db.session.commit()
        return task


    @staticmethod
    def update_status(task_id, status, user_id=None):
        # Secure update: Ensure the task belongs to the user
        query = Task.query.filter_by(id=task_id)
        if user_id: query = query.filter_by(user_id=user_id)
        
        task = query.first()
        if task:
            task.status = status
            if status == 'completed':
                task.completed_at = datetime.datetime.utcnow()
            db.session.commit()
        return task

    @staticmethod
    def delete(task_id, user_id=None):
        query = Task.query.filter_by(id=task_id)
        if user_id: query = query.filter_by(user_id=user_id)
        
        task = query.first()
        if task:
            db.session.delete(task)
            db.session.commit()
        return True
