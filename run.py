import eventlet
eventlet.monkey_patch()

import os

from app import create_app
from app.admin import lan_ip
from app.extensions import socketio

app = create_app()

if __name__ == "__main__":
    host = "0.0.0.0"
    debug = os.environ.get("CLASSROOM_DEBUG") == "1"

    # Allow overriding port via environment for flexibility
    env_port = os.environ.get("CLASSROOM_PORT")
    preferred_ports = [int(env_port)] if env_port else [5000]
    # add fallback range if preferred port unavailable
    preferred_ports += list(range(5001, 5011))

    import socket

    def _find_free_port(candidates):
        for p in candidates:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, p))
                s.close()
                return p
            except OSError:
                continue
        return None

    port = _find_free_port(preferred_ports)
    if port is None:
        raise RuntimeError("No available ports in range 5000-5010. Free a port or set CLASSROOM_PORT.")

    print("Classroom Dropbox is running.")
    print(f"Teacher admin: http://localhost:{port}/admin")
    print(f"Student address for this LAN: http://{lan_ip()}:{port}/")
    print("Set CLASSROOM_DEBUG=1 only while developing; keep it off during class.")
    socketio.run(app, host=host, port=port, debug=debug)
