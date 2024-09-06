from celery import shared_task
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
from .models import DriveFile
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


@shared_task
def download_file_task(file_id, credentials):
    """
    Asynchronous task to download a file from Google Drive using the file_id, with support for resumable downloads.
    """
    try:
        service = build('drive', 'v3', credentials=credentials)

        # Fetch the file metadata to get the file name, mimeType, and size
        file_metadata = service.files().get(fileId=file_id, fields="name, mimeType, size").execute()
        file_name = file_metadata.get('name')
        mime_type = file_metadata.get('mimeType')
        file_size = int(file_metadata.get('size', 0))

        # Fetch or create a DriveFile entry in the database, and update the metadata
        drive_file, created = DriveFile.objects.update_or_create(
            file_id=file_id,
            defaults={
                'name': file_name,
                'status': 'downloading',
                'mime_type': mime_type,
                'file_size': file_size,
            }
        )

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
            drive_file.progress += int(status.resumable_progress)
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
