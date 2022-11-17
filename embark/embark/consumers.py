# import difflib
import json
# import re

import logging

# import rx
# import rx.operators as ops
from asgiref.sync import async_to_sync

from channels.generic.websocket import WebsocketConsumer
from channels.layers import get_channel_layer

# from inotify_simple import flags
from django.conf import settings
# from uploader.models import Firmware

logger = logging.getLogger(__name__)


# consumer class for synchronous/asynchronous websocket communication
class WSConsumer(WebsocketConsumer):

    # constructor
    def __init__(self):
        super().__init__()
        self.channel_layer = get_channel_layer()
        self.room_group_name = 'updatesgroup'

    # this method is executed when the connection to the frontend is established
    def connect(self):
        logger.info("WS - connect")
        # create room group for channels communication
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )
        # accept socket connection
        self.accept()
        logger.info("WS - connect - accept")

        # called when received data from frontend
        # implement this for processing client input at backend
        # send current state
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name, {
                'type': 'send.message',
                'message': settings.PROCESS_MAP
            }
        )

    def receive(self, text_data=None, bytes_data=None):
        logger.info("WS - receive")
        # pass

    # called when websocket connection is closed
    def disconnect(self, code):
        logger.info("WS - disconnected: %s", code)
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    # send data to frontend
    def send_message(self, event):
        # Receive message and extract data from room group
        message = event['message']
        # logger.info(f"WS - send message: " + str(message))
        logger.info("WS - send message")
        # Send message to WebSocket
        self.send(json.dumps(message, sort_keys=False))
