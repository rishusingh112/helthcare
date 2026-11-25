import os
import socketio
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'curalync_backend.settings')

django_asgi_app = get_asgi_application()

from curalync_backend.socketio_app import sio  # noqa: E402

application = socketio.ASGIApp(sio, other_asgi_app=django_asgi_app)
