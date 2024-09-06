import json
from channels.generic.websocket import AsyncWebsocketConsumer

class FileDownloadConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Join a group for file download notifications
        await self.channel_layer.group_add("file_downloads", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Leave the group on WebSocket disconnect
        await self.channel_layer.group_discard("file_downloads", self.channel_name)

    async def receive(self, text_data):
        # Handle incoming WebSocket messages
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Send a response to the WebSocket client
        await self.send(text_data=json.dumps({
            'message': f"Received: {message}"
        }))

    async def file_download_complete(self, event):
        # Send a message to WebSocket client from the backend
        message = event['message']
        await self.send(text_data=json.dumps({
            'message': message
        }))
