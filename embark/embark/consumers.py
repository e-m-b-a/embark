import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer

from uploader.models import FirmwareAnalysis

logger = logging.getLogger(__name__)


# consumer class for synchronous/asynchronous websocket communication
class WSConsumer(AsyncWebsocketConsumer):

    @database_sync_to_async
    def get_message(self):
        logger.info("Getting status for user %s", self.user)
        analysis_list = FirmwareAnalysis.objects.filter(user=self.user, failed=False, finished=False)
        logger.debug("Found the following list of analysis for user %s : %s", self.user, analysis_list)
        logger.debug("User has %d analysis running", analysis_list.count())
        if analysis_list.count() > 0:
            message = {{str(analysis_.id): analysis_.status} for analysis_ in analysis_list }
            return message
        return "Please Wait"

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
    async def receive(self, text_data=None, bytes_data=None):
        logger.info("WS - receive")
        if text_data == "Reload":
            # Send message to room group
            await self.channel_layer.group_send(self.room_group_name, {"type": 'send.message', "message": await self.get_message()})

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
