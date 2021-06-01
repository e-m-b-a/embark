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
        # self.dummy_map = [{"firmware_id": 1, "module": "module1", "phase": "phase1", "percentage": 0.3}, {"firmware_id": 2, "module": "module2", "phase": "phase2", "percentage": 0.4}]

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
        #logger.debug(process_map)
        #self.send(json.dumps(process_map, sort_keys=False))
        print(" MESSAGE RECEIVED")
        # THIS WORKS BUT ONLY SENDS THE DATA RECEIVED FROM THE FRONTEND BACK TO THE FRONTEND
        # data = json.loads(text_data)
        # message = data['message']
        # async_to_sync(self.channel_layer.group_send)(
        #     self.room_group_name, {
        #         "type": 'send_message_to_frontend',
        #         "message": message
        #     }
        # )

    # called when websocket connection is closed TODO: implement connection close if necessary
    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    # THIS METHOD IS NOT CALLED FROM THE LOGREADER BUT IT SHOULD
    # send data to frontend
    def send_message_to_frontend(self, event):
        logger.debug("EVENT TRIGERED")
        # Receive message from room group
        message = event['message']
        # Send message to WebSocket
        self.send(text_data=json.dumps({
            'message': message
        }))


