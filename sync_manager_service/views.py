import googleapiclient
from googleapiclient.discovery import build
import os

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from file_processor_service.models import DriveFile

from sync_manager_service.syncer import fetch_and_process_drive_changes
from sync_manager_service.models import DriveWatch
from auth_service.models import UserCredentials
from auth_service.helper import get_credentials_from_user_credentials


@csrf_exempt
def google_drive_webhook(request):
    """
    Handles Google Drive push notifications for file changes.
    Removes the file from local storage if it's deleted or if permissions change and the user loses access.
    """
    if request.method == 'POST':
        # Extract relevant headers from the webhook notification
        channel_id = request.headers.get('X-Goog-Channel-ID')
        resource_id = request.headers.get('X-Goog-Resource-ID')
        resource_state = request.headers.get('X-Goog-Resource-State')  # "sync", "update", "delete", etc.

        # Fetch the watch information (which user/file is associated with this notification)
        try:
            watch = DriveWatch.objects.get(resource_id=resource_id)
            file_id = watch.file_id
            user_credentials = UserCredentials.objects.get(user=watch.user)
            credentials = get_credentials_from_user_credentials(user_credentials)

            # Handle different resource states
            if resource_state == 'delete':
                # File was deleted; remove it from local storage
                print(f"File {file_id} was deleted. Removing from local storage...")
                handle_file_deletion(file_id)

            elif resource_state == 'update' or resource_state == 'sync':
                # Check if the file is still accessible (permissions may have changed)
                try:
                    file_metadata = fetch_file_metadata(file_id, credentials)

                    # If file is accessible, handle the update
                    if file_metadata:
                        print(f"File {file_id} was updated. Fetching details...")
                        fetch_and_process_drive_changes(file_id, credentials)

                except googleapiclient.errors.HttpError as e:
                    # Handle permission errors or inaccessible files
                    if e.resp.status == 403:
                        print(f"File {file_id} is no longer accessible (permissions may have changed). Removing from local storage.")
                        handle_file_deletion(file_id)

            return HttpResponse(status=200)

        except DriveWatch.DoesNotExist:
            return HttpResponse("Watch not found", status=404)
        except UserCredentials.DoesNotExist:
            return HttpResponse("User credentials not found", status=404)

    return HttpResponse(status=405)


def fetch_file_metadata(file_id, credentials):
    """
    Fetches file metadata from Google Drive to check if the file is still accessible.
    """
    service = build('drive', 'v3', credentials=credentials)

    try:
        # Fetch the file metadata (raises HttpError if the file is inaccessible)
        file_metadata = service.files().get(fileId=file_id, fields="id, name, mimeType, trashed").execute()

        # Check if the file is trashed (deleted)
        if file_metadata.get('trashed', False):
            print(f"File {file_metadata['name']} (ID: {file_id}) is in the trash.")
            return None

        return file_metadata  # Return the metadata if the file is accessible and not trashed

    except googleapiclient.errors.HttpError as e:
        if e.resp.status == 403:
            # Handle permission error (file is no longer accessible to the user)
            print(f"Permission denied for file {file_id}.")
        elif e.resp.status == 404:
            # Handle file not found (file may have been permanently deleted)
            print(f"File {file_id} not found.")

        return None

def handle_file_deletion(file_id):
    """
    Handles the deletion of a file from the local machine and backend using the file name.
    """
    try:
        # Fetch the file information from the database using the file_id
        drive_file = DriveFile.objects.get(file_id=file_id)
        file_name = drive_file.name  # Assuming 'name' stores the file name

        # Construct the file path using the file name
        file_path = f'/downloads/{file_name}'  # Replace with your actual storage path

        # Delete the file from the local system
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted file {file_name} from local storage")
        else:
            print(f"File {file_name} does not exist in local storage")

        # Remove the file record from the backend database
        drive_file.delete()
        print(f"Deleted file {file_id} ({file_name}) from the database")

    except DriveFile.DoesNotExist:
        print(f"File with ID {file_id} not found in the database")
