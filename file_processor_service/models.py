from django.db import models


class DriveFile(models.Model):
    """
    Model to store information about files from Google Drive.
    """
    file_id = models.CharField(max_length=255, unique=True)  # Google Drive file ID
    name = models.CharField(max_length=255)  # File name
    status = models.CharField(max_length=50, default='pending')  # Status of the file download (pending, downloading, completed, failed)
    access = models.CharField(max_length=50, default='private')  # Access level (private, public, shared)
    mime_type = models.CharField(max_length=255)  # File type (e.g., image/png, application/vnd.google-apps.folder)
    progress = models.BigIntegerField(default=0)  # Number of bytes downloaded so far (for resumable downloads)
    file_size = models.BigIntegerField(null=True, blank=True)  # Total file size
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp when the entry was created
    updated_at = models.DateTimeField(auto_now=True)  # Timestamp when the entry was last updated

    def __str__(self):
        return f"{self.name} ({self.file_id})"
