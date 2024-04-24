# chat/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<session_id>[a-f0-9-]+)/(?P<datasource_id>\d+)/$", consumers.ChatAIConsumer.as_asgi()),
]
