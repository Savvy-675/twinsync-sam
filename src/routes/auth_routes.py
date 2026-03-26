from flask import Blueprint
from src.controllers.auth_controller import login, register

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

auth_bp.route('/login', methods=['POST'])(login)
auth_bp.route('/register', methods=['POST'])(register)
