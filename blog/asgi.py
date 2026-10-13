# blog/asgi.py
import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blog.settings")
django.setup()

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
})
