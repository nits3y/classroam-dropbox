import os

from app import create_app
from app.admin import lan_ip
from app.extensions import socketio

app = create_app()

if __name__ == "__main__":
    host = "0.0.0.0"
    port = 5000
    debug = os.environ.get("CLASSROOM_DEBUG") == "1"
    print("Classroom Dropbox is running.")
    print(f"Teacher admin: http://localhost:{port}/admin")
    print(f"Student address for this LAN: http://{lan_ip()}:{port}/")
    print("Set CLASSROOM_DEBUG=1 only while developing; keep it off during class.")
    socketio.run(app, host=host, port=port, debug=debug)
