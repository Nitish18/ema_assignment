from googleapiclient.discovery import build

import uuid

from googleapiclient.discovery import build
from file_processor_service.models import DriveFile
import os
from sync_manager_service.models import DriveWatch


def create_watch(credentials, file_id=None, user_id=None):
    """
    Creates a watch request for changes in Google Drive or for a specific file/folder.
    """
    service = build('drive', 'v3', credentials=credentials)

    channel_id = str(uuid.uuid4())  # Use UUID to generate a unique string

    # Define the webhook URL where Google will send notifications
    webhook_url = "https://a1a5-2405-201-5c08-d833-e0e2-83dc-a04b-e053.ngrok-free.app/sync-manager/file-sync-webhook/"

    # Request body to create a watch
    watch_request_body = {
        "id": channel_id,  # A unique ID for your webhook channel
        "type": "web_hook",
        "address": webhook_url,  # Your webhook endpoint
    }

    if file_id:
        # Watch a specific file or folder
        response = service.files().watch(fileId=file_id, body=watch_request_body).execute()
    else:
        # Watch the entire Google Drive
        response = service.changes().watch(body=watch_request_body).execute()

    # Store the channel ID, resource ID, and user ID in the database
    DriveWatch.objects.create(
        user_id=user_id,
        channel_id=channel_id,
        resource_id=response['resourceId'],  # The resource ID from the response
        file_id=file_id
    )

    return response


def fetch_and_process_drive_changes(file_id, credentials):
    """
    Fetches changes for a specific file (file_id) from Google Drive and processes them.
    """
    try:
        service = build('drive', 'v3', credentials=credentials)

        # Get the file metadata for the specific resource ID (file)
        file_metadata = service.files().get(fileId=file_id, fields="id, name, mimeType, trashed").execute()

        # Check if the file was trashed (deleted)
        if file_metadata.get('trashed', False):
            print(f"File {file_metadata['name']} (ID: {file_id}) was deleted.")
            # Handle file deletion locally and in the database
            handle_file_deletion(file_id)
        else:
            print(f"File {file_metadata['name']} (ID: {file_id}) was updated or modified.")
            # Handle file update locally and in the database
            handle_file_update(file_metadata)

    except Exception as e:
        print(f"Error fetching or processing changes for file {file_id}: {str(e)}")


def handle_file_deletion(file_id):
    """
    Handles the deletion of a file from the local machine and backend.
    """
    # Delete the file from the local system
    file_path = f'/path_to_local_storage/{file_id}'  # Customize this with the actual file storage path
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Deleted file {file_id} from local storage")

    # Remove the file record from the backend database
    DriveFile.objects.filter(file_id=file_id).delete()
    print(f"Deleted file {file_id} from the database")


def handle_file_update(file_metadata):
    """
    Handles the update of a file in the local machine and backend.
    """
    file_id = file_metadata['id']
    file_name = file_metadata['name']

    # Check if the file already exists in the local system or in the database
    drive_file, created = DriveFile.objects.update_or_create(
        file_id=file_id,
        defaults={'name': file_name, 'status': 'syncing'}
    )

    # Download or update the file if necessary (re-download the updated file)
    # download_file(file_id, file_name)
