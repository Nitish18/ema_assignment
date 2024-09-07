from django.urls import re_path
from file_processor_service.consumers import FileDownloadConsumer


websocket_urlpatterns = [
    re_path(r'ws/file-downloads/$', FileDownloadConsumer.as_asgi()),
]
