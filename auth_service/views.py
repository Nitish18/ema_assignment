import os

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from googleapiclient.discovery import build

from django.shortcuts import redirect, render
from django.conf import settings
from django.http import HttpResponse
from google_auth_oauthlib.flow import Flow

from auth_service.models import UserCredentials
from django.contrib.auth.models import User

# Path to Google OAuth 2.0 client credentials JSON file
CREDENTIALS_FILE = os.path.join(settings.BASE_DIR, 'auth_creds.json')

# Allow HTTP for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # This allows HTTP for OAuth during local development

# Scopes define what level of access the app is requesting from Google Drive
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.metadata.readonly',
    'https://www.googleapis.com/auth/drive.appdata',
    'https://www.googleapis.com/auth/drive.photos.readonly',
]


def drive_auth(request):
    flow = Flow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)

    # Set the redirect URI explicitly based on the URL defined in Google Developer Console
    flow.redirect_uri = 'http://localhost:8000/auth-service/callback/'

    # Generate the authorization URL
    authorization_url, state = flow.authorization_url(
        access_type='offline',  # Request a refresh token
        include_granted_scopes='true'
    )

    # Store the state in the session to verify later in the callback
    request.session['state'] = state
    return redirect(authorization_url)


def drive_callback(request):
    # Retrieve the state from the session to validate the callback
    state = request.session['state']

    # Initialize the flow using the same credentials file and state
    flow = Flow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES, state=state)

    # Explicitly set the redirect URI to match the one registered in Google Developer Console
    flow.redirect_uri = 'http://localhost:8000/auth-service/callback/'

    # Fetch the token from the callback URL
    flow.fetch_token(authorization_response=request.build_absolute_uri())

    # Get credentials from the flow object
    credentials = flow.credentials

    # Save credentials to the database
    UserCredentials.objects.update_or_create(
        user=request.user,
        defaults={
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': ' '.join(credentials.scopes)
        }
    )

    return HttpResponse("OAuth completed and credentials saved!")


def logout(request):
    """
    Clears the session (logs out the user).
    """
    request.session.clear()
    return HttpResponse("Logged out!")


def check_credentials(request=None, user_id=None):
    """
    Checks if the user is authenticated and their credentials are valid.
    Fetches OAuth credentials from the database and refreshes them if expired.
    """
    if not request.user.is_authenticated:
        return redirect('admin:login')

    user_obj = None
    if not request and user_id:
        user_obj = User.objects.get(id=user_id)
        if not user_obj:
            return HttpResponse("User not found!", status=404)
        elif not user_obj.is_authenticated:
            return redirect('admin:login')

    try:
        user_creds = None

        if user_obj:
            user_creds = UserCredentials.objects.get(user=user_obj)
        else:
            # Retrieve the user's credentials from the MySQL database
            user_creds = UserCredentials.objects.get(user=request.user)

        # Reconstruct the credentials object from the database fields
        credentials = Credentials(
            token=user_creds.token,
            refresh_token=user_creds.refresh_token,
            token_uri=user_creds.token_uri,
            client_id=user_creds.client_id,
            client_secret=user_creds.client_secret,
            scopes=user_creds.scopes.split(' ')
        )

        # Refresh the token if it has expired
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(request)

            # Update the new token in the database after refreshing
            user_creds.token = credentials.token
            user_creds.save()

        # Return the valid credentials
        return credentials

    except UserCredentials.DoesNotExist:
        # If credentials do not exist in the database, redirect to OAuth flow
        return redirect('drive_auth')  # Redirect to initiate OAuth flow
