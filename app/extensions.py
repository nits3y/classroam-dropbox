from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],  # No global default limit
    storage_uri="memory://"
)

socketio = SocketIO(async_mode="eventlet")
