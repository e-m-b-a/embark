import asyncio
import os
import base64
import logging
import json

from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from uploader.models import FirmwareAnalysis

logger = logging.getLogger(__name__)


class LogConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.analysis_id = None
        self.line_cache = None
        self.file_view = None
        self.observer = None

    def load_file_content(self):
        logger.info(
            'Getting file content for analysis id "%s"; view: %s',
            self.analysis_id,
            self.file_view,
        )

        num_lines = self.line_cache.num_lines()
        limit = min(num_lines, self.file_view.limit)

        # Ensure you can't read negative lines
        offset = max(self.file_view.offset, 0)
        # Ensure you can't read lines bigger than the last line
        offset = min(num_lines - limit, offset)

        # Fix the offset, in case the user tried to read invalid lines
        self.file_view.offset = offset

        content = self.line_cache.read_lines(offset, offset + limit - 1)
        self.file_view.content = base64.b64encode(content).decode("ascii")
        self.file_view.num_lines = num_lines

    @database_sync_to_async
    def get_firmware(self, analysis_id: str) -> FirmwareAnalysis:
        return FirmwareAnalysis.objects.get(id=analysis_id, user=self.scope["user"])

    async def connect(self):
        logger.info("WS - connect")
        await self.accept()
        logger.info("WS - connect - accept")

        self.analysis_id = self.scope["url_route"]["kwargs"]["analysis_id"]

        firmware = await self.get_firmware(self.analysis_id)

        log_file_path_ = f"{Path(firmware.path_to_logs).parent}/emba_run.log"

        if not os.path.isfile(log_file_path_):
            await self.send_message({"error": "The log file does not exist, yet."})
            await self.close()

        self.line_cache = LineCache(log_file_path_)

        self.file_view = FileView()

        this = self

        class ModifyEventHandler(FileSystemEventHandler):
            def on_modified(self, _event):
                asyncio.run(this.update_lines())

        event_handler = ModifyEventHandler()

        self.observer = Observer()
        self.observer.schedule(event_handler, log_file_path_)
        self.observer.start()

        await self.update_lines()

    async def send_file_content(self) -> None:
        self.load_file_content()
        await self.send_message({"file_view": self.file_view.__dict__})

    async def update_lines(self) -> None:
        self.line_cache.refresh()
        await self.send_file_content()

    async def receive(self, text_data: str = "", bytes_data=None) -> None:
        logger.info("WS - receive")
        try:
            data = json.loads(text_data)
            if data["action"] == "change_view":
                logger.info("WS - action: change view")
                logger.info(data["file_view"])
                self.file_view = FileView(**data["file_view"])
                await self.send_file_content()
            else:
                raise NotImplementedError("Unknown action")
        except Exception as exception:
            logger.error(exception)
            await self.send_message({"error": "Unknown error"})

    async def disconnect(self, code):
        logger.info("WS - disconnected: %s", code)
        if self.line_cache:
            self.line_cache.close()

        if self.observer:
            self.observer.stop()

    # send data to frontend
    async def send_message(self, message: dict) -> None:
        # logger.info(f"WS - send message: " + str(message))
        logger.info("WS - send message")
        # Send message to WebSocket
        await self.send(json.dumps(message, sort_keys=False))


class FileView:
    def __init__(self, offset=0, limit=30, content="", num_lines=0) -> None:
        self.offset = offset
        self.limit = limit
        self.content = content
        self.num_lines = num_lines


REFRESH_LINES = 10  # This will define how many of the last lines will be refreshed


class LineCache:
    def __init__(self, filepath: str) -> None:
        self.line_beginnings = [0]
        self.line_endings = [0]
        # Intentionally not using with to save resources
        # because we don't have to open the file as often
        # pylint: disable-next=consider-using-with
        self.filehandle = open(filepath, "rb")
        self.refresh()

    def refresh(self) -> None:
        # Make sure to not go out of bounds
        refresh_from_line = min(len(self.line_beginnings), REFRESH_LINES)
        refresh_from_byte = self.line_beginnings[-refresh_from_line]

        # Remove the line beginnings and endings to be refreshed
        self.line_beginnings = self.line_beginnings[:-refresh_from_line]
        self.line_endings = self.line_endings[:-refresh_from_line]

        logger.debug(
            "Start refreshing line cache from line %s (start counting from end of the file)", refresh_from_line
        )
        logger.debug("Start refreshing line cache from byte %s", refresh_from_byte)

        self.filehandle.seek(refresh_from_byte)

        while True:
            line_beginning = self.filehandle.tell()
            line = self.filehandle.readline()

            line_ending = self.filehandle.tell()

            if len(line) > 0 and line[-1:] == b'\n':
                line_ending = line_ending - 1

            self.line_beginnings.append(line_beginning)
            self.line_endings.append(line_ending)

            if len(line) == 0 or line[-1:] != b'\n':
                break

    def num_lines(self) -> int:
        return len(self.line_beginnings)

    def read_lines(self, first_line: int, last_line: int) -> bytes:
        num_lines = self.num_lines()

        if first_line > last_line:
            raise IndexError("The first line cannot be bigger than the last line")

        if first_line < 0:
            raise IndexError("The first line cannot be below 0")

        if last_line >= num_lines:
            raise IndexError("The first line cannot be equal or above the number of lines")

        first_byte = self.line_beginnings[num_lines - last_line - 1]
        last_byte = self.line_endings[num_lines - first_line - 1]
        self.filehandle.seek(first_byte)
        output = self.filehandle.read(last_byte - first_byte)

        return output

    def close(self) -> None:
        self.filehandle.close()
