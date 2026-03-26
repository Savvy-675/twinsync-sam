from src.socket_instance import socketio
from flask import request
import logging

logger = logging.getLogger('SocketService')

class SocketService:
    @staticmethod
    def emit_task_update(user_id, message, task_id=None):
        """
        Broadcasting task updates to a specific user's room.
        This ensures users only receive sync events for their own data.
        """
        payload = {'message': message, 'task_id': task_id}
        socketio.emit('task_updated', payload, room=f"user_{user_id}")
        logger.info(f"[SOCKET] Task update emitted to user_{user_id}")

    @staticmethod
    def emit_analytics_refresh(user_id):
        socketio.emit('analytics_refreshed', {}, room=f"user_{user_id}")
        logger.info(f"[SOCKET] Analytics refresh emitted to user_{user_id}")

# --- WebSocket Event Handlers ---

@socketio.on('connect')
def handle_connect():
    # In a real cloud environment, we'd verify the JWT token here
    # For now, we'll allow joining a room based on an 'identity' event or similar
    logger.info(f"Client connected: {request.sid}")

@socketio.on('join')
def on_join(data):
    # Standard multi-user room isolation
    user_id = data.get('user_id')
    if user_id:
        from flask_socketio import join_room
        join_room(f"user_{user_id}")
        logger.info(f"User {user_id} joined room user_{user_id}")
