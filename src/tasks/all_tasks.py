from src.tasks.celery_app import celery_app
from src.ml.model_service import MLService
from src.services.email_service import EmailService
from src.models.all_models import User
import logging

logger = logging.getLogger('CeleryTasks')

@celery_app.task(bind=True, max_retries=3)
def train_model_async(self, user_id):
    try:
        logger.info(f"[CELERY] Retraining model for user {user_id}")
        return MLService.train_model(user_id)
    except Exception as exc:
        logger.error(f"[CELERY] Retraining failed for user {user_id}, retrying...")
        raise self.retry(exc=exc, countdown=60)

@celery_app.task(bind=True, max_retries=5)
def send_email_async(self, email_func_name, **kwargs):
    # Mapping to actual EmailService functions for flexible dispatch
    try:
        func = getattr(EmailService, email_func_name)
        return func(**kwargs)
    except Exception as exc:
        logger.error(f"[CELERY] Email dispatch failed ({email_func_name}), retrying...")
        raise self.retry(exc=exc, countdown=300)

@celery_app.task
def global_daily_maintenance():
    # To be called by a scheduler or cron
    users = User.query.all()
    for u in users:
        train_model_async.delay(u.id)
        send_email_async.delay('send_daily_report', user_email=u.email, score=u.productivity_score, completed=u.ml_samples)
