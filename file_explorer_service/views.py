from django.http import JsonResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required  # Import @login_required
from googleapiclient.discovery import build

from auth_service.models import UserCredentials
from auth_service.views import check_credentials  # Import the check_credentials function


@login_required
def get_drive_files(request):
    """
    Fetches all files and folders from Google Drive using OAuth tokens.
    This view is protected by login_required to ensure only authenticated users can access it.
    """
    # Ensure the user's OAuth credentials are valid or refresh them
    credentials = check_credentials(request)

    # If credentials are invalid or missing, redirect to the OAuth flow
    if isinstance(credentials, HttpResponseRedirect):
        return credentials

    try:
        # Create the Google Drive API service using valid OAuth credentials
        service = build('drive', 'v3', credentials=credentials)

        # Fetch all files and folders from Google Drive
        results = service.files().list(
            pageSize=1000,  # Fetches up to 1000 items per page
            fields="nextPageToken, files(id, name, mimeType, parents)"
        ).execute()

        items = results.get('files', [])

        # Prepare the data for response
        file_data = []
        for item in items:
            file_data.append({
                'id': item['id'],
                'name': item['name'],
                'mimeType': item['mimeType'],
                'parents': item.get('parents', [])
            })

        # Return the list of files and folders as JSON
        return JsonResponse({'files': file_data})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
