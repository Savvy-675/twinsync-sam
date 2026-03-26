import eventlet
eventlet.monkey_patch()

from src import create_app
from src.socket_instance import socketio

app = create_app()

if __name__ == '__main__':
    # Moved to Port 5001 because Port 5000 was stubborn on the host machine.
    # Relative API URLs in the frontend will automatically follow this change.
    print("Launching TwinSync Cloud Platform in Native Fallback mode (Port 5001)...")
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, use_reloader=False)
