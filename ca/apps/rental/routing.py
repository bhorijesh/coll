from django.urls import re_path
from .consumers import NotificationConsumer  # Ensure this import is correct

websocket_urlpatterns = [
    re_path(r'ws/notifications/$', NotificationConsumer.as_asgi()),
]
