from flask_socketio import SocketIO

# Global SocketIO instance
# Using Redis message queue for scaling across multiple workers
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')
