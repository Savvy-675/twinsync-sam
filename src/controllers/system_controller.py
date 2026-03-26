from flask import jsonify, request
from src.config.db import db
from redis import Redis
from src.config.config import Config
from src.models.all_models import User
from flask_jwt_extended import jwt_required, get_jwt_identity
import time

def update_usage():
    user_id = get_jwt_identity()
    data = request.get_json()
    active_inc = data.get('active_seconds', 0)
    screen_val = data.get('screen_seconds', data.get('total_seconds', 0))
    is_absolute = data.get('is_absolute', False)
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404
        
    user.active_usage_today = (user.active_usage_today or 0) + active_inc
    
    if is_absolute:
        user.total_screen_time_today = screen_val
    else:
        user.total_screen_time_today = (user.total_screen_time_today or 0) + screen_val
    
    if 'daily_screen_time_goal' in data:
        user.daily_screen_time_goal = data['daily_screen_time_goal']
        
    db.session.commit()
    
    # Check for urgency (e.g. if we are close to working_hours_end)
    # This logic can be expanded here or in the analytics service
    
    return jsonify({
        "success": True, 
        "data": {
            "active_usage": user.active_usage_today,
            "total_screen_time": user.total_screen_time_today
        }
    })

def health_check():
    health = {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {
            "database": "unknown",
            "redis": "unknown"
        }
    }
    
    # 1. DB Check
    try:
        db.session.execute('SELECT 1')
        health["services"]["database"] = "connected"
    except Exception as e:
        health["status"] = "degraded"
        health["services"]["database"] = f"error: {str(e)}"
        
    # 2. Redis Check
    try:
        r = Redis.from_url(Config.REDIS_URL, socket_timeout=2)
        r.ping()
        health["services"]["redis"] = "connected"
    except Exception as e:
        health["status"] = "degraded"
        health["services"]["redis"] = f"error: {str(e)}"
        
    code = 200 if health["status"] == "healthy" else 503
    return jsonify(health), code
