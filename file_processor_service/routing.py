from django.urls import path
from .consumers import FileDownloadConsumer

websocket_urlpatterns = [
    path('ws/file-downloads/', FileDownloadConsumer.as_asgi()),
]
