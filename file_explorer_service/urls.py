from django.urls import path
from . import views

urlpatterns = [
    path('get-drive-files/', views.get_drive_files, name='get_drive_files'),
]
