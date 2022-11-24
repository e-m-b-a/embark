import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer

from uploader.models import FirmwareAnalysis

logger = logging.getLogger(__name__)


# consumer class for synchronous/asynchronous websocket communication
class WSConsumer(AsyncWebsocketConsumer):

    # this method is executed when the connection to the frontend is established
    async def connect(self):
        logger.info("WS - connect")
        self.user = self.scope["user"]
        self.room_group_name = "services_%s" % self.user
        # create room group for channels communication
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        # accept socket connection
        await self.accept()
        logger.info("WS - connect - accept")

    # called when received data from frontend
    # implement this for processing client input at backend
<<<<<<< HEAD
    # FIXME send user/group id to answer with 
    # all analysis-status messages for that group
    def receive(self, text_data=None, bytes_data=None):
=======
    # FIXME
    async def receive(self, text_data=None, bytes_data=None):
>>>>>>> 77cf71cb471469ffefe8e50ddda310e256bcfc57
        logger.info("WS - receive")
        if text_data == "Reload":
            # Send message to room group
            message = []
            analysis_list = FirmwareAnalysis.objects.filter(user=self.user, failed=False, finished=False)
            for analysis_ in analysis_list:
                message.append(analysis_.status)
            await self.channel_layer.group_send(self.room_group_name, {"type": 'send.message', "message": message})

    # called when websocket connection is closed
    async def disconnect(self, code):
        logger.info("WS - disconnected: %s", code)
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # send data to frontend
    async def send_message(self, event):
        # Receive message and extract data from room group
        message = event['message']
        # logger.info(f"WS - send message: " + str(message))
        logger.info("WS - send message")
        # Send message to WebSocket
        await self.send(json.dumps(message, sort_keys=False))
