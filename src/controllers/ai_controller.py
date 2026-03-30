from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.utils.response import success_response, error_response
from src.services.ai_service import AIService
from src.repositories.user_repo import UserRepository
from src.repositories.task_repo import TaskRepository
from src.models.all_models import Insight, Task
from src.config.db import db
import logging

logger = logging.getLogger('AIController')

@jwt_required(optional=True)
def chat():
    # 🕵️ Cloud Resilience Fallback
    try:
        user_id = get_jwt_identity()
    except:
        user_id = None

    if not user_id:
        user = UserRepository.get_by_email('demo@twin.local')
        user_id = str(user.id) if user else "1"

    data = request.json
    prompt = data.get('message', '').lower()

    # 🧠 Intelligent AI Cache
    from src import cache
    cache_key = f"chat_cache_{user_id}_{hash(prompt)}"
    cached_res = cache.get(cache_key)
    if cached_res:
        return success_response(data={'response': cached_res, 'task_created': False},
                                message="Gemini response retrieved from cache.")

    user = UserRepository.get_by_id(user_id)
    if not user:
        return error_response(message="User identity not found in Cloud.")

    # Inject pending task context for chat memory
    pending_tasks = TaskRepository.get_pending_by_user(user_id)
    task_context_str = ", ".join([f"'{t.title}' (due {t.deadline.strftime('%b %d') if t.deadline else 'N/A'}, {t.priority} priority)" for t in pending_tasks[:5]]) if pending_tasks else "No pending tasks"

    context = {
        'samps': user.ml_samples,
        'acc': user.ml_accuracy,
        'top_f': 'Time of Day',
        'pending_tasks': task_context_str
    }

    # 🤖 Task Intent Detection: Does the user want to add a task?
    task_created = False
    task_title = None
    task_intent = AIService.detect_task_intent(prompt)
    if task_intent:
        try:
            task_data = {
                'user_id': user_id,
                'title': task_intent.get('title', prompt[:60]),
                'category': task_intent.get('category', 'general'),
                'priority': task_intent.get('priority'),  # Will auto-calc from deadline
                'deadline': task_intent.get('deadline'),
            }
            new_task = TaskRepository.create(task_data)
            task_created = True
            task_title = new_task.title
            logger.info(f"Task created via chat: {task_title}")
            # Modify prompt so LLaMA confirms the task creation
            prompt = f"Confirm you just created the task '{task_title}' for the user. Be brief and encouraging."
        except Exception as e:
            logger.error(f"Failed to create task from chat: {e}")

    # Generate AI response
    response_text = AIService.generate_chat_response(prompt, context)

    if "Rate Limit" not in response_text and "error" not in response_text.lower():
        cache.set(cache_key, response_text, timeout=300)

    return success_response(
        data={'response': response_text, 'task_created': task_created, 'task_title': task_title},
        message="Response generated."
    )


@jwt_required(optional=True)
def email_sync():
    """Manually trigger a Gmail sync and create tasks from matching emails."""
    try:
        user_id = get_jwt_identity()
    except:
        user_id = None

    if not user_id:
        user = UserRepository.get_by_email('demo@twin.local')
        user_id = str(user.id) if user else "1"

    from src.services.email_service import EmailService
    extracted_tasks = EmailService.fetch_and_parse_emails(user_id)

    created = []
    for task_data in extracted_tasks:
        try:
            task = TaskRepository.create(task_data)
            created.append(task.title)
        except Exception as e:
            logger.error(f"Failed to save email-extracted task: {e}")

    return success_response(
        data={'tasks_created': created, 'count': len(created)},
        message=f"Email sync complete. {len(created)} new task(s) created."
    )


@jwt_required()
def analytics():
    user_id = get_jwt_identity()
    user = UserRepository.get_by_id(user_id)
    if not user:
        return error_response(message="User identity not found in Cloud.")

    insights = Insight.query.filter_by(user_id=user_id).order_by(Insight.created_at.desc()).limit(4).all()
    categories = db.session.query(Task.category, db.func.count(Task.id)).filter(
        Task.user_id == user_id, Task.status == 'completed'
    ).group_by(Task.category).all()

    # Build weekly task data for calendar
    from datetime import datetime, timedelta
    today = datetime.utcnow()
    weekly = []
    for i in range(7):
        day = today + timedelta(days=i)
        count = Task.query.filter(
            Task.user_id == user_id,
            Task.status == 'pending',
            db.func.date(Task.deadline) == day.date()
        ).count()
        weekly.append({'date': day.strftime('%Y-%m-%d'), 'label': day.strftime('%a'), 'count': count})

    # Build daily schedule preview (Planner Service)
    from src.services.planner_service import PlannerService
    daily_schedule = PlannerService.generate_day_plan(user_id)

    # Top 3 Important Tasks Today (Sorted by Smart Priority Score)
    pending_tasks = TaskRepository.get_pending_by_user(user_id)
    # Ensure they are refreshed
    from src.ml.model_service import MLService
    MLService.predict_pending(user_id)
    top_3 = sorted(pending_tasks, key=lambda x: x.smart_priority_score, reverse=True)[:3]

    # Check AI Health (Groq/Gemini)
    ai_configured = (Config.GROQ_API_KEY and len(Config.GROQ_API_KEY) > 5) or \
                    (Config.GEMINI_API_KEY and len(Config.GEMINI_API_KEY) > 5)

    data = {
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'productivity_score': user.productivity_score,
            'delay_rate': user.delay_rate,
            'learning_multiplier': user.learning_multiplier,
            'ml_accuracy': user.ml_accuracy,
            'ml_samples': user.ml_samples,
            'ml_last_trained': user.ml_last_trained,
            'personality_type': user.personality_type,
            'peak_focus_time': user.peak_focus_time,
            'avg_duration_mins': user.avg_duration_mins,
            'daily_goal': user.daily_goal,
            'user_type': getattr(user, 'user_type', 'Student'),
            'working_hours_start': getattr(user, 'working_hours_start', '09:00'),
            'working_hours_end': getattr(user, 'working_hours_end', '17:00'),
            'preferred_work_time': getattr(user, 'preferred_work_time', 'Morning')
        },
        'categories': [{'category': c[0], 'count': c[1]} for c in categories],
        'weekly': weekly,
        'daily_schedule': daily_schedule,
        'top_tasks': [{'id': t.id, 'title': t.title, 'priority': t.priority, 'score': t.smart_priority_score, 'deadline': t.deadline.strftime('%Y-%m-%d') if t.deadline else None} for t in top_3],
        'heatmap': {'Morning': 0, 'Afternoon': 0, 'Evening': 0},
        'recommendations': [{'recommendation': i.recommendation, 'reason': i.reason} for i in insights],
        'ai_health': ai_configured
    }

    if not ai_configured:
        return success_response(data=data, message="Cloud Sync Active (⚠️ AI Keys Missing)")
    
    return success_response(data=data, message="Real-time analytics synchronized.")

@jwt_required()
def onboard_profile():
    user_id = get_jwt_identity()
    user = UserRepository.get_by_id(user_id)
    if not user:
        return error_response(message="User identity not found in Cloud.")
        
    data = request.json
    user.user_type = data.get('user_type', 'Student')
    user.working_hours_start = data.get('working_hours_start', '09:00')
    user.working_hours_end = data.get('working_hours_end', '17:00')
    user.preferred_work_time = data.get('preferred_work_time', 'Morning')
    
    db.session.commit()
    return success_response(message="Smart planner profile configured successfully.")
