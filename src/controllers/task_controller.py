from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.utils.response import success_response, error_response
from src.repositories.task_repo import TaskRepository
from src.services.task_service import TaskService
from src.services.socket_service import SocketService
from src.tasks.all_tasks import train_model_async

@jwt_required()
def get_tasks():
    user_id = get_jwt_identity()
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 50))
    
    # ML triggering: Managed via TaskService logic
    TaskService.trigger_ai_engine(user_id)
    
    tasks = TaskRepository.get_all_by_user(user_id)
    
    # Sort tasks conceptually by smart_priority_score descending
    tasks.sort(key=lambda x: getattr(x, 'smart_priority_score', 0) or 0, reverse=True)
    
    start = (page - 1) * limit
    end = start + limit
    paginated_tasks = tasks[start:end]
    
    task_data = [{
        'id': t.id,
        'title': t.title,
        'category': t.category,
        'priority': t.priority,
        'status': t.status,
        'deadline': t.deadline.isoformat() if t.deadline else None,
        'estimated_duration': t.estimated_duration,
        'risk_score': t.risk_score,
        'risk_reason': t.risk_reason,
        'smart_priority_score': getattr(t, 'smart_priority_score', 0)
    } for t in paginated_tasks]
    
    return success_response(data={
        'tasks': task_data,
        'page': page,
        'limit': limit,
        'total': len(tasks)
    }, message="Cloud-synchronized tasks retrieved.")

@jwt_required()
def create_task():
    user_id = get_jwt_identity()
    data = request.json
    try:
        task = TaskRepository.create({
            'user_id': user_id,
            'title': data['title'],
            'category': data['category'],
            'priority': data['priority'],
            'estimated_duration': data.get('estimated_duration', 30),
            'deadline': data['deadline']
        })
        
        # Real-time synchronization: Broadcast new task to user's devices
        SocketService.emit_task_update(user_id, f"New Task '{task.title}' synchronized.", task.id)
        
        return success_response(data={'id': task.id}, message="Task synchronized to Cloud.", status_code=201)
    except Exception as e:
        return error_response(message=str(e))

@jwt_required()
def update_task(task_id):
    user_id = get_jwt_identity()
    new_status = request.json.get('status')
    try:
        task = TaskRepository.update_status(task_id, new_status, user_id=user_id)
        if not task:
            return error_response(message="Task not found or access denied.", status_code=403)
            
        # Real-time synchronization
        SocketService.emit_task_update(user_id, f"Task '{task.title}' status updated to {new_status}.", task.id)
        
        if new_status in ['completed', 'delayed']:
            # ASYNC Offloading: Retrain model in the background worker
            train_model_async.delay(user_id)
            
        return success_response(message="Task status updated. Syncing behavioral loop...")
    except Exception as e:
        return error_response(message=str(e))

@jwt_required()
def delete_task(task_id):
    user_id = get_jwt_identity()
    try:
        TaskRepository.delete(task_id, user_id=user_id)
        
        # Real-time synchronization
        SocketService.emit_task_update(user_id, "Task deleted from Cloud Store.", task_id)
        
        return success_response(message="Task purged from Cloud.")
    except Exception as e:
        return error_response(message=str(e))
