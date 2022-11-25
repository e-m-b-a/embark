import signal
import sys
import logging

from django.dispatch import Signal

logger = logging.getLogger(__name__)

finish_execution = Signal()

def _stop_handler(signal, frame):  
    print('Shutting down all operations!')
    logger.info("sending shutdown signal to boundedexec")
    finish_execution.send(sender='system')
    sys.exit(0) 

signal.signal(signal.SIGINT, _stop_handler)