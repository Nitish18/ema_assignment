from celery import shared_task
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
from .models import DriveFile

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from sync_manager_service.syncer import create_watch  # Import the create_watch function
from auth_service.helper import get_credentials_from_user_id


@shared_task
def download_file_task(file_id, user_id):
    """
    Asynchronous task to download a file from Google Drive using the file_id, with support for resumable downloads.
    Skips downloading if the file is already completed.
    """
    try:
        credentials = get_credentials_from_user_id(user_id)
        service = build('drive', 'v3', credentials=credentials)

        # Fetch or create a DriveFile entry in the database
        drive_file, created = DriveFile.objects.get_or_create(
            file_id=file_id,
            defaults={'status': 'downloading'}
        )

        # If the file is already downloaded (status is 'completed'), skip the download
        if drive_file.status == 'completed':
            print(f"File {drive_file.name} already downloaded. Skipping re-download.")

            # Notify the front-end client via WebSocket that the file is already downloaded
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'file_downloads',
                {
                    'type': 'file_download_complete',
                    'message': f'File {drive_file.name} already downloaded. Skipping re-download.'
                }
            )
            return f"File {drive_file.name} already downloaded. Skipping re-download."

        # Fetch the file metadata to get the file name, mimeType, and size
        file_metadata = service.files().get(fileId=file_id, fields="name, mimeType, size").execute()
        file_name = file_metadata.get('name')
        mime_type = file_metadata.get('mimeType')
        file_size = int(file_metadata.get('size', 0))

        # Update the metadata if it has changed
        drive_file.name = file_name
        drive_file.mime_type = mime_type
        drive_file.file_size = file_size
        drive_file.status = 'downloading'
        drive_file.save()

        # Define the local path to store the downloaded file
        local_file_path = os.path.join('downloads', file_name)

        # Check if the file has been partially downloaded
        start_byte = drive_file.progress  # Start from where it left off

        # Open the local file in append mode if progress is > 0
        mode = 'ab' if start_byte > 0 else 'wb'
        fh = io.FileIO(local_file_path, mode)

        # Create a request to download the file with support for resuming
        request = service.files().get_media(fileId=file_id)
        downloader = MediaIoBaseDownload(fh, request, chunksize=1024 * 1024)  # Download in 1MB chunks

        if start_byte > 0:
            # Set the Range header to resume the download
            request.headers['Range'] = f"bytes={start_byte}-"

        done = False
        while not done:
            status, done = downloader.next_chunk()

            # Update the progress in the database after each chunk is downloaded
            drive_file.progress = int(status.resumable_progress)
            drive_file.save()

        # Once the download is complete, update the status
        drive_file.status = 'completed'
        drive_file.save()

        # Notify front-end (FE) client via WebSocket about task completion
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'file_downloads',  # WebSocket group name
            {
                'type': 'file_download_complete',
                'message': f'File {file_name} downloaded successfully'
            }
        )
        return f"File {file_name} downloaded successfully"

    except Exception as e:
        # If an error occurs, update the file status to 'failed'
        DriveFile.objects.filter(file_id=file_id).update(status='failed')
        return str(e)


def download_files_in_folder(folder_id, credentials, user_id=None):
    """
    Downloads all files inside a given Google Drive folder by folder_id, including files in subfolders.
    """
    service = build('drive', 'v3', credentials=credentials)

    # Fetch all files inside the folder (i.e., files where the folder_id is in their parents field)
    query = f"'{folder_id}' in parents and trashed = false"  # Fetch non-trashed files
    files_in_folder = service.files().list(q=query, fields="files(id, name, mimeType)").execute()

    # Iterate over each file and download it using download_file_task
    for file_metadata in files_in_folder.get('files', []):
        file_id = file_metadata['id']
        file_name = file_metadata['name']

        if file_metadata['mimeType'] == 'application/vnd.google-apps.folder':
            # Recursively download files from subfolders (optional)
            download_files_in_folder(file_id, credentials, user_id)
        else:
            # Download individual file
            task = download_file_task.delay(file_id, user_id)
            create_watch(credentials, file_id, user_id)

    return "All files downloaded successfully"
