from src.repositories.task_repo import TaskRepository
from src.repositories.user_repo import UserRepository
from src.ml.model_service import MLService
from src.services.socket_service import SocketService
import datetime
import logging

logger = logging.getLogger('TaskService')

class TaskService:
    @staticmethod
    def trigger_ai_engine(user_id):
        """
        Calculates real-time risk scores for all pending tasks 
        whenever the task list is retrieved or modified.
        """
        try:
            factor, importance = MLService.predict_pending(user_id)
            
            # Real-time sync: Notify clients that analytics and risk profiling are ready
            SocketService.emit_analytics_refresh(user_id)
            return True
        except Exception as e:
            logger.error(f"AI Engine failure for user {user_id}: {e}")
            return False

    @staticmethod
    def update_task_status(task_id, new_status, user_id):
        task = TaskRepository.update_status(task_id, new_status, user_id=user_id)
        if task:
            # Re-calculating global user productivity metrics synchronously
            # so the frontend instantly reflects the updated score/delay rate
            all_tasks = TaskRepository.get_all_by_user(user_id)
            
            total_tasks = len(all_tasks)
            completed_tasks = len([t for t in all_tasks if t.status == 'completed'])
            delayed_tasks = len([t for t in all_tasks if t.status == 'delayed'])
            
            # Simple productivity heuristic
            new_score = (completed_tasks / total_tasks) * 100 if total_tasks else 0
            
            # Delay rate calculation
            total_past = completed_tasks + delayed_tasks
            delay_rt = (delayed_tasks / total_past) * 100 if total_past > 0 else 0
            
            UserRepository.update_stats(user_id, {
                'productivity_score': new_score,
                'delay_rate': round(delay_rt, 2)
            })
            
            # Real-time broadcast
            msg = f"Task '{task.title}' marked as {new_status}."
            SocketService.emit_task_update(user_id, msg, task.id)
            # Emit analytics strictly so dashboard gauges refresh instantly
            SocketService.emit_analytics_refresh(user_id)
            
            return task
        return None
