from src.config.db import db
from src.models.all_models import User

class UserRepository:
    @staticmethod
    def get_by_id(user_id):
        return User.query.get(user_id)

    @staticmethod
    def get_by_email(email):
        return User.query.filter_by(email=email).first()

    @staticmethod
    def create(user_data):
        user = User(
            name=user_data.get('name', 'New User'),
            email=user_data['email'],
            working_hours_start=user_data.get('working_hours_start', '09:00'),
            working_hours_end=user_data.get('working_hours_end', '17:00'),
            daily_screen_time_goal=user_data.get('daily_screen_time_goal', 120),
            preferences=user_data.get('preferences', 'morning')
        )
        user.set_password(user_data['password'])
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def update_stats(user_id, stats_dict):
        user = User.query.get(user_id)
        if user:
            for key, value in stats_dict.items():
                setattr(user, key, value)
            db.session.commit()
        return user
