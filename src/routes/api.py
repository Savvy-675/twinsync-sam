from flask import Blueprint
from src.controllers.task_controller import get_tasks, create_task, update_task, delete_task
from src.controllers.ai_controller import chat, analytics, email_sync
from src.controllers.system_controller import health_check, update_usage

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Task API
api_bp.route('/tasks', methods=['GET'])(get_tasks)
api_bp.route('/tasks', methods=['POST'])(create_task)
api_bp.route('/tasks/<int:task_id>', methods=['PUT'])(update_task)
api_bp.route('/tasks/<int:task_id>', methods=['DELETE'])(delete_task)

# AI & Analytics API
api_bp.route('/chat', methods=['POST'])(chat)
api_bp.route('/analytics', methods=['GET'])(analytics)
api_bp.route('/email-sync', methods=['POST'])(email_sync)
from src.controllers.ai_controller import onboard_profile
api_bp.route('/profile/onboard', methods=['POST'])(onboard_profile)

# System & Tracking API
api_bp.route('/health', methods=['GET'])(health_check)
from flask_jwt_extended import jwt_required
api_bp.route('/screentime', methods=['POST'])(jwt_required()(update_usage))
