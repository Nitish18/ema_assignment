from django.db import models
from django.contrib.auth.models import User

class DriveWatch(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # The user who owns the file
    channel_id = models.CharField(max_length=255, unique=True)  # Channel ID
    resource_id = models.CharField(max_length=255, unique=True)  # Resource ID
    file_id = models.CharField(max_length=255)  # File ID being watched
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Watch for file {self.file_id} by user {self.user.username}"
