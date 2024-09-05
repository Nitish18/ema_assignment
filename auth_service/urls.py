from django.urls import path
from auth_service import views


urlpatterns = [
    path('auth/', views.drive_auth, name='drive_auth'),  # Initiate OAuth flow
    path('callback/', views.drive_callback, name='drive_callback'),  # Handle callback
    path('logout/', views.logout, name='logout'),  # Log out
]
