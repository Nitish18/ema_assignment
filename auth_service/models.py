from django.db import models
from django.contrib.auth.models import User


class UserCredentials(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # Link credentials to a Django user
    token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255, null=True, blank=True)
    token_uri = models.CharField(max_length=255)
    client_id = models.CharField(max_length=255)
    client_secret = models.CharField(max_length=255)
    scopes = models.TextField()  # Storing scopes as a text field

    def __str__(self):
        return f'Credentials for {self.user.username}'
