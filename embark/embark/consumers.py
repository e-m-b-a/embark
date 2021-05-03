import json

from channels.generic.websocket import WebsocketConsumer
from .process_log import input_processing


class WSConsumer(WebsocketConsumer):

    def connect(self):
        self.accept()
        # inotify_events()
        # a = input_processing()
        # self.send(json.dumps({'message': a}))

    def disconnect(self, close_code):
        pass
