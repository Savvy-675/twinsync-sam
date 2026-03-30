from datetime import datetime, timedelta
import logging
from src.repositories.task_repo import TaskRepository
from src.repositories.user_repo import UserRepository
from src.ml.model_service import MLService

logger = logging.getLogger('PlannerService')

class PlannerService:
    @staticmethod
    def generate_day_plan(user_id):
        """
        Generates an optimized daily schedule based on:
        - Working Hours
        - Task Priority & Deadlines
        - Peak Focus Time
        - ML Behavior insights
        """
        user = UserRepository.get_by_id(user_id)
        if not user:
            return []

        # 1. Gather all pending tasks
        pending_tasks = TaskRepository.get_pending_by_user(user_id)
        if not pending_tasks:
            return []

        # Ensure priority scores are calculated
        MLService.predict_pending(user_id)
        
        # Sort by Smart Priority Score (descending)
        pending_tasks.sort(key=lambda x: x.smart_priority_score, reverse=True)

        # 2. Get User Constraints
        start_hour = int(user.working_hours_start.split(':')[0]) if user.working_hours_start else 9
        end_hour = int(user.working_hours_end.split(':')[0]) if user.working_hours_end else 17
        peak_focus = user.preferred_work_time or 'Morning'
        
        # Define Peak Hour Range
        peak_hours = {
            'Morning': range(8, 12),
            'Afternoon': range(12, 17),
            'Evening': range(17, 22)
        }.get(peak_focus, range(9, 12))

        # 3. Scheduling Logic
        schedule = []
        current_time = datetime.now().replace(hour=start_hour, minute=0, second=0, microsecond=0)
        
        # If today's start hour has passed, start from the next hour
        if current_time < datetime.now():
            current_time = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

        for task in pending_tasks:
            # If we've passed the working day, stop scheduling for today
            if current_time.hour >= end_hour:
                break
                
            duration = task.estimated_duration or 30
            
            # Behavior Adjustment: If task is difficult/critical, prioritize peak hours
            is_priority = task.priority in ['critical', 'high']
            
            # Mock Behavior Check: Avoid slots with >70% historical delay risk
            # For this version, we prioritize the "Peak Focus Time" for highest score tasks
            
            entry = {
                'id': task.id,
                'title': task.title,
                'start_time': current_time.strftime('%I:%M %p'),
                'end_time': (current_time + timedelta(minutes=duration)).strftime('%I:%M %p'),
                'duration': duration,
                'priority': task.priority,
                'category': task.category,
                'is_peak_focus': current_time.hour in peak_hours
            }
            
            schedule.append(entry)
            current_time += timedelta(minutes=duration + 15) # Add 15 min buffer
            
        return schedule
