import os
import joblib
from datetime import datetime
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score
from src.repositories.task_repo import TaskRepository
from src.repositories.user_repo import UserRepository
from src.config.db import db
from src.models.all_models import Task

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ml_models')
if not os.path.exists(MODELS_DIR):
    os.makedirs(MODELS_DIR)

class MLService:
    PRIO_MAP = {'low':0, 'medium':1, 'high':2}
    CAT_MAP = {'personal':0, 'study':1, 'work':2}

    @classmethod
    def extract_features(cls, task):
        p = cls.PRIO_MAP.get(task.priority.lower() if task.priority else 'medium', 1)
        c = cls.CAT_MAP.get(task.category.lower() if task.category else 'work', 2)
        h = task.deadline.hour if task.deadline else 12
        dur = task.estimated_duration or 30
        return [p, c, h, dur]

    @classmethod
    def train_model(cls, user_id):
        tasks = TaskRepository.get_completed_history(user_id)
        X, y = [], []
        for t in tasks:
            X.append(cls.extract_features(t))
            y.append(1 if t.status == 'delayed' else 0)

        # Cold Start Logic
        if len(y) < 20:
            for _ in range(30):
                X.append([1, 0, 21, 60]); y.append(1)
                X.append([2, 0, 22, 30]); y.append(1)
                X.append([2, 2, 10, 45]); y.append(0)
                X.append([0, 1, 14, 120]); y.append(0)
                X.append([2, 2, 23, 90]); y.append(1)

        clf = DecisionTreeClassifier(max_depth=5, random_state=42)
        clf.fit(X, y)
        preds = clf.predict(X)
        acc = accuracy_score(y, preds)
        
        # Persist model locally
        model_path = os.path.join(MODELS_DIR, f'user_{user_id}.joblib')
        joblib.dump({'model': clf, 'importances': clf.feature_importances_}, model_path)

        # Update User Metrics
        UserRepository.update_stats(user_id, {
            'ml_accuracy': acc * 100,
            'ml_samples': len(y),
            'ml_last_trained': datetime.now().strftime('%I:%M %p')
        })
        print(f"[ML Service] Retrained user {user_id} - Acc: {acc*100}%")
        return acc

    @classmethod
    def calculate_priority_score(cls, task, delay_prob):
        base_importance = cls.PRIO_MAP.get(task.priority.lower() if task.priority else 'medium', 1) * 20
        delay_risk_score = delay_prob * 30
        
        deadline_urgency = 0
        from datetime import datetime
        if task.deadline:
            days_left = (task.deadline - datetime.now()).days
            if days_left <= 0:
                deadline_urgency = 30
            elif days_left <= 3:
                deadline_urgency = 20
            elif days_left <= 7:
                deadline_urgency = 10
                
        return min(base_importance + delay_risk_score + deadline_urgency, 100)

    @classmethod
    def predict_pending(cls, user_id):
        # Load Model
        model_path = os.path.join(MODELS_DIR, f'user_{user_id}.joblib')
        if not os.path.exists(model_path):
            cls.train_model(user_id)
            
        data = joblib.load(model_path)
        clf = data['model']
        imps = data['importances']
        
        feature_names = ["Priority", "Category", "Time of Day", "Duration"]
        imps_dict = dict(zip(feature_names, imps))
        top_feature = max(imps_dict, key=imps_dict.get)
        top_feature_pct = int(imps_dict[top_feature] * 100)
        
        pending_tasks = TaskRepository.get_pending_by_user(user_id)
        for pt in pending_tasks:
            X_test = [cls.extract_features(pt)]
            probs = clf.predict_proba(X_test)[0]
            delay_prob = 0.0
            if len(clf.classes_) > 1 and 1 in clf.classes_:
                delay_prob = probs[list(clf.classes_).index(1)]
            elif len(clf.classes_) == 1 and clf.classes_[0] == 1:
                delay_prob = probs[0]
                
            pt.risk_score = f"{int(delay_prob * 100)}%"
            pt.risk_reason = f"Driven by `{top_feature}` (dictates {top_feature_pct}% variance)."
            pt.smart_priority_score = cls.calculate_priority_score(pt, delay_prob)
            
        db.session.commit()
        return top_feature, top_feature_pct
