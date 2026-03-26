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
    def complete_task(task_id, user_id):
        task = TaskRepository.update_status(task_id, 'completed', user_id=user_id)
        if task:
            # Re-calculating global user productivity score
            user = UserRepository.get_by_id(user_id)
            all_tasks = TaskRepository.get_all_by_user(user_id)
            completed = [t for t in all_tasks if t.status == 'completed']
            
            # Simple productivity heuristic
            new_score = (len(completed) / len(all_tasks)) * 100 if all_tasks else 0
            UserRepository.update_stats(user_id, {'productivity_score': new_score})
            
            # Real-time broadcast
            SocketService.emit_task_update(user_id, f"Sync Successful: '{task.title}' recorded.", task.id)
            SocketService.emit_analytics_refresh(user_id)
            
            return task
        return None
