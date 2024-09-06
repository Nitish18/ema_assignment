import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .tasks import download_file_task  # Celery task import

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
            for file_id in file_id_list:
                task = download_file_task(file_id, credentials)
                create_watch(credentials, file_id, request.user.id)
                task_ids.append(task.id)

            # Return a response with the initiated task IDs
            return JsonResponse({"message": "Download tasks started", "task_ids": task_ids})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=400)
