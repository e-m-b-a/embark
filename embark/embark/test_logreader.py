from django.test import TestCase
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from channels.generic.websocket import WebsocketConsumer
import time
import logging
logger = logging.getLogger('web')


def set_stuff(arg):

    test_logreader.back_mes = arg
    logger.debug("AAAAAAAAAAAAAAAAAAAAAHH")


class test_logreader(TestCase):

    def setUp(self):
        self.back_mes = "Failure"
        self.room_group_name = 'updatesgroup'
        self.channel_layer = get_channel_layer()

    def test_redis_communication(self):
        msg = {"content": "Ping"}
        logger.debug(self.channel_layer)
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name, {
                "type": 'tes.message',
                "message": msg
            }
        )
        time.sleep(2)
        logger.debug("OOOOOOOOOOHHH")
        self.assertEqual(self.back_mes, "Pong")

