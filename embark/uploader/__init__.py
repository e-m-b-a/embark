__copyright__ = 'Copyright 2021-2024 Siemens Energy AG, Copyright 2021 The AMOS Projects'
__author__ = 'Maximilian Wagner, Benedikt Kuehne, diegiesskanne'
__license__ = 'MIT'

import signal
import sys
import logging

from django.dispatch import Signal

logger = logging.getLogger(__name__)

finish_execution = Signal()


def _stop_handler(_signal, _frame):
    print('Shutting down all operations!')
    logger.info("sending shutdown signal to boundedexec")
    finish_execution.send(sender='system')
    sys.exit(0)


signal.signal(signal.SIGINT, _stop_handler)
