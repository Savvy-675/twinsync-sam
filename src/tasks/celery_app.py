from celery import Celery
from src.config.config import Config
import os

def make_celery(app):
    # FALLBACK: If Redis/Broker URL is not found, force "Eager" (Synchronous) mode 
    # to ensure the app continues to function natively without Docker.
    broker_url = Config.broker_url
    backend_url = Config.result_backend
    
    # If using default localhost without a real Redis server, we force Eager mode.
    # Note: In a real Cloud/Docker environment, CELERY_BROKER_URL will be set via .env.
    is_native = not os.getenv('CELERY_BROKER_URL')

    celery = Celery(
        app.import_name,
        broker=broker_url if not is_native else None,
        backend=backend_url if not is_native else None
    )
    
    celery.conf.update(app.config)
    if is_native:
        celery.conf.task_always_eager = True
        print("[CELERY] Native Mode Active: Background tasks will run Synchronously (No Redis found).")

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

celery_app = None

def init_celery_task_broker(app):
    global celery_app
    celery_app = make_celery(app)
    return celery_app
