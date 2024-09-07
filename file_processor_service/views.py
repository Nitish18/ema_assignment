import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .tasks import download_file_task, download_files_in_folder  # Celery task import

from django.http import JsonResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required  # Import @login_required
from googleapiclient.discovery import build

from auth_service.views import check_credentials  # Import the check_credentials function
from sync_manager_service.syncer import create_watch  # Import the create_watch function


@csrf_exempt
def file_upload(request):
    """
    API endpoint to initiate file download tasks.
    Accepts a list of Google Drive file IDs, and starts an async task for each.
    """

    # Ensure the user's OAuth credentials are valid or refresh them
    credentials = check_credentials(request)

    # If credentials are invalid or missing, redirect to the OAuth flow
    if isinstance(credentials, HttpResponseRedirect):
        return credentials

    if request.method == 'POST':
        try:
            # Get the list of file IDs from the POST request
            data = json.loads(request.body)
            # Extract the file_list from the JSON data
            file_id_list = data.get('file_ids', [])

            # Start a Celery async task for each file ID
            task_ids = []
            service = build('drive', 'v3', credentials=credentials)

            for file_id in file_id_list:
                # Get file metadata to check if it's a folder
                file_metadata = service.files().get(fileId=file_id, fields="mimeType").execute()
                user_id = request.user.id

                if file_metadata['mimeType'] == 'application/vnd.google-apps.folder':
                    # If the ID belongs to a folder, download all files within the folder
                    print(f"Folder detected: {file_id}. Initiating folder download...")
                    download_files_in_folder(file_id, credentials, user_id)
                else:
                    # If it's a regular file, download the file
                    print(f"File detected: {file_id}. Initiating file download...")
                    task = download_file_task.delay(file_id, user_id)
                    task_ids.append(task.id)
                    create_watch(credentials, file_id, user_id)

            # Return a response with the initiated task IDs
            return JsonResponse({"message": "Download tasks started", "task_ids": task_ids})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=400)
