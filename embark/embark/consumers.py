import difflib
import json
import re

import rx
import rx.operators as ops
from asgiref.sync import async_to_sync

from channels.generic.websocket import WebsocketConsumer
from channels.layers import get_channel_layer

from inotify_simple import flags
from django.conf import settings
from uploader.models import Firmware

import logging

logger = logging.getLogger('web')


# consumer class for synchronous/asynchronous websocket communication
class WSConsumer(WebsocketConsumer):

    # constructor
    def __init__(self):
        super().__init__()
        self.channel_layer = get_channel_layer()
        self.room_group_name = 'updatesgroup'
        self.pm = {}

    # this method is executed when the connection to the frontend is established
    def connect(self):
        # accept socket connection
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )
        self.accept()

        # called when received data from frontend TODO: implement this for processing client input at backend
    def receive(self, text_data=None, bytes_data=None):
        pass

    # called when websocket connection is closed TODO: implement connection close if necessary
    def disconnect(self, close_code):
        logger.debug(self.pm)
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    # send data to frontend
    def send_message(self, event):
        # Receive message from room group
        message = event['message']
        self.pm = message
        # Send message to WebSocket
        self.send(json.dumps(message, sort_keys=False))
        # self.send(text_data=json.dumps({
        #     'message': message
        # }))

