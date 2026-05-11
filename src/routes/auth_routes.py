from flask import Blueprint
from src.controllers.auth_controller import login, register

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

auth_bp.route('/login', methods=['POST'])(login)
auth_bp.route('/register', methods=['POST'])(register)

# Google OAuth2
from src.controllers.google_auth_controller import google_authorize, google_callback
auth_bp.route('/google', methods=['GET'])(google_authorize)
auth_bp.route('/google/callback', methods=['GET'])(google_callback)
