from django.urls import path
from . import views

urlpatterns = [
    path('file-sync-webhook/', views.google_drive_webhook, name='file_sync_handler'),
]
