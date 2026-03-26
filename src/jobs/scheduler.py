from apscheduler.schedulers.background import BackgroundScheduler
from src.ml.model_service import MLService
from src.services.email_service import EmailService
from src.models.all_models import User, Task
import logging
from datetime import datetime

logger = logging.getLogger('APScheduler')

def run_ml_retraining_job(app):
    with app.app_context():
        users = User.query.all()
        for u in users:
            try:
                MLService.train_model(u.id)
            except Exception as e:
                logger.error(f"[CRON] Failed retraining user {u.id}: {e}")

def run_daily_summary_job(app):
    with app.app_context():
        users = User.query.all()
        for u in users:
            EmailService.send_daily_report(u.email, u.productivity_score, u.ml_samples)

def run_high_risk_smtp_sweeper(app):
    with app.app_context():
        logger.info("[CRON] Sweeping Database for extreme High-Risk variables to trigger Automated SMTP Pipeline.")
        users = User.query.all()
        for u in users:
            pending_tasks = Task.query.filter_by(user_id=u.id, status='pending').all()
            for t in pending_tasks:
                if t.risk_score and t.deadline and t.deadline > datetime.utcnow():
                    try:
                        risk_val = int(t.risk_score.replace('%', ''))
                        # Only automate extreme conditions (e.g. users actively spiraling toward delay)
                        if risk_val > 75:
                            logger.info(f"[CRON SMTP ALERT] User {u.id} - Task {t.title} critical risk threshold breached ({risk_val}%). Queueing network alert email.")
                            EmailService.send_task_alert(user_email=u.email, task_title=t.title, risk_pct=f"{risk_val}%")
                    except Exception as e:
                        logger.error(f"Failed parsing risk for email automation scheduler: {e}")

def init_scheduler(app):
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=lambda: run_ml_retraining_job(app), trigger="cron", hour=0, minute=0, id="ml_retrain")
    scheduler.add_job(func=lambda: run_daily_summary_job(app), trigger="cron", hour=18, minute=0, id="daily_summary")
    
    # Execute extreme risk scanner routinely (e.g., every 4 hours checking for newly predicted catastrophes)
    scheduler.add_job(func=lambda: run_high_risk_smtp_sweeper(app), trigger="interval", hours=4, id="high_risk_sweeper")
    
    scheduler.start()
