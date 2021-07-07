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

    # this method is executed when the connection to the frontend is established
    def connect(self):
        # create room group for channels communication
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )
        # accept socket connection
        self.accept()

        # called when received data from frontend
        # TODO: implement this for processing client input at backend -> page refresh should be here

    def receive(self, text_data=None, bytes_data=None):
        pass

    # called when websocket connection is closed
    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    # send data to frontend
    def send_message(self, event):
        # Receive message and extract data from room group
        message = event['message']
        # Send message to WebSocket
        self.send(json.dumps(message, sort_keys=False))
