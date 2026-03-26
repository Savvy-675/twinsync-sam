import os
import logging
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from src.config.config import Config
from src.config.db import db
from src.socket_instance import socketio
from src.jobs.scheduler import init_scheduler
from src.tasks.celery_app import init_celery_task_broker
from flasgger import Swagger
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from src.utils.errors import handle_exception

# Global extensions
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])
cache = Cache()
jwt = JWTManager()

def create_app():
    # Provide explicitly static_folder mapping since factory lives inside /src
    app = Flask(__name__, static_url_path='', static_folder='../static')
    app.config.from_object(Config)
    
    # 1. Initialize Database
    db.init_app(app)
    
    # 2. Initialize JWT for Cloud Auth
    jwt.init_app(app)
    
    # 3. Initialize WebSocket Support
    # Only using a message queue if Redis is explicitly available (Non-Native)
    socketio.init_app(app, message_queue=app.config.get('SOCKETIO_REDIS_URL'))
    
    # 4. Initialize Celery Task Broker
    init_celery_task_broker(app)
    
    # 5. Initialize Swagger (OpenAPI docs)
    # Access at http://localhost:5000/apidocs
    Swagger(app)
    
    # 6. Initialize Rate Limiting & Caching
    limiter.init_app(app)
    cache.init_app(app)

    # 7. Global Error Handling
    app.register_error_handler(Exception, handle_exception)
    
    # Register Route Blueprints (Controllers Layer)
    from src.routes.api import api_bp
    from src.routes.auth_routes import auth_bp
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    
    # Frontend Main Entry
    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    # Boot procedures (Database Tables & Jobs)
    with app.app_context():
        # DB Auto-Creation in Production is handled via Migrations usually,
        # but for this demo, we'll ensure the table structure is active.
        db.create_all()
        
        # Cold start mock user creation if DB is entirely empty
        from src.models.all_models import User, Task
        if User.query.count() == 0:
            from src.repositories.user_repo import UserRepository
            from datetime import datetime, timedelta
            
            # Create user with initial 'wowed' metrics
            u = UserRepository.create({
                'name': 'Enterprise Demo', 
                'email': 'demo@twin.local', 
                'password': 'password',
                'productivity_score': 74,
                'ml_accuracy': 85,
                'ml_samples': 5,
                'personality_type': 'High-Efficiency Architect'
            })
            
            now = datetime.utcnow()
            # Pre-populate with completed sync history
            for i in range(5):
                t = Task(
                    user_id=u.id, 
                    title=f'Synchronize Cloud Node {i+1}', 
                    category='work', 
                    priority='high', 
                    estimated_duration=45, 
                    deadline=now - timedelta(days=1),
                    status='completed'
                )
                db.session.add(t)
            
            db.session.commit()
            
            # Offload heavy initial training
            from src.tasks.all_tasks import train_model_async
            try:
                train_model_async.delay(u.id)
            except:
                pass # Fallback for local native non-celery environments

    # Initialize APScheduler for automated system cron
    init_scheduler(app)
    
    # Configure Structured Logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
    
    return app
