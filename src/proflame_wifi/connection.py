"""
Basic functionality for interacting with websockets.
"""
import asyncio
from enum import StrEnum
from logging import Logger, getLogger
from typing import Callable, NoReturn, Self

from websockets.client import WebSocketClientProtocol, connect

from .const import DEFAULT_PORT

_LOGGER = getLogger(__name__)


class ConnectionStatus(StrEnum):
    """
    Enum that represents valid states of a websocket connection.
    """

    CONNECTING = 'CONNECTING'
    CONNECTED = 'CONNECTED'
    DISCONNECTING = 'DISCONNECTING'
    DISCONNECTED = 'DISCONNECTED'

class ConnectionManager:
    """
    Object for establishing and interacting with websockets.
    """

    PING_INTERVAL = 5
    PING_MESSAGE = 'PING'

    def __init__(self,
        host: str,
        port: int = DEFAULT_PORT,
        logger: Logger | None = None,
        ping_interval: int | None = None,
        ping_message: str | None = None,
        connect_handlers: list[Callable[[Self], NoReturn]] | None = None,
        disconnect_handlers: list[Callable[[Self], NoReturn]] | None = None,
        recv_handlers: list[Callable[[Self, str], NoReturn]] | None = None
    ):
        """
        Create a new instance of the ConnectionManager class.

        :param host: The DNS name or IP address to connect to.
        :type host: str
        :param port: The port to connect to.
        :type port: int or None
        :param logger: A python logger to use for generated messages.
        :type: logger: Logger or None
        :param ping_interval: The frequency (in seconds) at which keepalive
            messages should be sent.
        :type ping_interval: int or None
        :param ping_message: The message that should be sent periodically to
            keep the connection active.
        :type ping_message: str or None
        :param connect_handlers: A list of callback functions that should be
            invoked any time a new connection is established.
        :type connect_handlers: list[Callable[[ConnectionManager], NoReturn]]
            or None
        :param disconnect_handlers: A list of callback functions that should be
            invoked any time a connection is lost or closed.
        :type disconnect_handlers: list[Callable[[ConnectionManager],
            NoReturn]] or None
        :param recv_handlers: A list of callback functions that should be
            invoked any time a new message is received.
        :type recv_handlers: list[Callable[[ConnectionManager, str], NoReturn]]
            or None
        """
        self._host: str = host
        self._port: int = port
        self._logger: Logger = logger or _LOGGER
        self._ping_interval: int = ping_interval or ConnectionManager.PING_INTERVAL
        self._ping_message: str = ping_message or ConnectionManager.PING_MESSAGE

        self._connect_event = asyncio.Event()
        self._disconnect_event = asyncio.Event()
        self._send_item = None

        self._connect_handlers: list[Callable[[ConnectionManager], NoReturn]] = []
        self._disconnect_handlers: list[Callable[[ConnectionManager], NoReturn]] = []
        self._recv_handlers: list[Callable[[ConnectionManager, str], NoReturn]] = []

        self._current_status: ConnectionStatus = ConnectionStatus.DISCONNECTED
        self._desired_status: ConnectionStatus = ConnectionStatus.DISCONNECTED
        self._queue: asyncio.Queue = asyncio.Queue()
        self._tasks: list[asyncio.Task] = []
        self._ws: WebSocketClientProtocol = None

        list(map(self.register_connect_handler, connect_handlers or []))
        list(map(self.register_disconnect_handler, disconnect_handlers or []))
        list(map(self.register_recv_handler, recv_handlers or []))

    @property
    def connected(self) -> bool:
        """
        Return true if the connection status is currently connected.

        :return: A boolean value that indicates if the connection is currently
            established.
        :rtype: bool
        """
        return self.status == ConnectionStatus.CONNECTED
    
    @property
    def status(self) -> ConnectionStatus:
        """
        Get the current status of the connection.

        :return: The current status of the connection.
        :rtype: ConnectionStatus
        """
        return self._current_status

    @property
    def uri(self) -> str:
        """
        Get the formatted URI for the websocket.

        :return: The websocket URI.
        :rtype: str
        """
        return f"ws://{self._host}:{self._port}"
    
    async def connect(self, wait=False) -> None:
        """
        Open a websocket connection and start workers.
        
        :param wait: Whather to wait for the connection to be opened before
            returning.
        :type wait: bool
        """
        self._desired_status = ConnectionStatus.CONNECTED
        asyncio.create_task(self._maintain_connection())
        if wait:
            await self.wait_for_connect()

    async def disconnect(self, wait=False):
        """
        Close a websocket connection and stop workers.

        :param wait: Whether to wait for the connection to be closed before
            returning.
        :type wait: bool
        """
        self._desired_status = ConnectionStatus.DISCONNECTED
        await self._cleanup()
        if wait:
            await self.wait_for_disconnect()
    
    def register_connect_handler(self, handler: Callable[[Self], NoReturn]) -> None:
        """
        Add a new callback function to be invoked any time a new connection is
        established.

        :param handler: The function to call on new connections.
        :type handler: Callable[[ConnectionManager], NoReturn]
        """
        self._connect_handlers.append(handler)
    
    def register_disconnect_handler(self, handler: Callable[[Self], NoReturn]) -> None:
        """
        Add a new callback function to be invoked any time an established
        connection is closed or dropped.

        :param handler: The function to call on closed connections.
        :type handler: Callable[[ConnectionManager], NoReturn]
        """
        self._disconnect_handlers.append(handler)
    
    def register_recv_handler(self, handler: Callable[[Self, str], NoReturn]) -> None:
        """
        Add a new callback function to be invoked any time a new message is
        received from the websocket.

        :param handler: The function to call on received messages.
        :type handler: Callable[[ConnectionManager, str], NoReturn]
        """
        self._recv_handlers.append(handler)

    async def send(self, message) -> None:
        """
        Send a raw message to the websocket.

        :param message: The message to send to the websocket.
        :type message: str
        """
        self._queue.put_nowait(message)

    async def wait_for_connect(self) -> None:
        """
        Wait for the websocket connection to become available.
        """
        return await self._connect_event.wait()

    async def wait_for_disconnect(self) -> None:
        """
        Wait for the websocket connection to close.
        """
        return await self._disconnect_event.wait()

    def _callback(self, future: asyncio.Task) -> None:
        """
        Handle housekeeping when a worker ends.

        :param future: The task object that ended and caused this methos to be
            invoked.
        :type future: Task
        """
        exception = future.exception()
        if exception and not isinstance(exception, asyncio.CancelledError):
            self._logger.error(
                'Unexpected error in worker',
                exc_info=exception
            )
        asyncio.create_task(self._cleanup())

    async def _cleanup(self) -> None:
        """
        Handle cleanup of all resources for a connection that is being torn
        down.
        """
        if self._current_status == ConnectionStatus.DISCONNECTING:
            return

        self._current_status = ConnectionStatus.DISCONNECTING
        active = [x for x in self._tasks if not x.done()]
        list(map(lambda x: x.cancel(), active))
        await asyncio.gather(*active)
        self._tasks = []
        await self._ws.close()
        self._current_status = ConnectionStatus.DISCONNECTED
        await self._on_disconnect()

    async def _dispatcher(self) -> None:
        """
        Worker the handles the processesing of messages to be sent to the
        websocket.
        """
        while True:
            try:
                if self._send_item is None:
                    self._send_item = await self._queue.get()
                self._logger.debug("SEND: %s", self._send_item)
                await self._ws.send(str(self._send_item))
                self._queue.task_done()
                self._send_item = None
            except asyncio.CancelledError:
                break
    
    async def _keep_alive(self) -> None:
        """
        Worker that sends periodic messages to maintain the websocket
        connection.
        """
        while True:
            try:
                await asyncio.sleep(self._ping_interval)
                await self.send(self._ping_message)
            except asyncio.CancelledError:
                break
    
    async def _listener(self) -> None:
        """
        Worker that handles processing of messages received from the websocket.
        """
        while True:
            try:
                async for message in self._ws:
                    self._logger.debug('RECV: %s', message)
                    await self._on_recv(message)
            except asyncio.CancelledError:
                break

    async def _maintain_connection(self) -> None:
        """
        Worker that maintains an open connection to the websocket for as long
        as an active connection is desired.

        Detects disconnects and automatically tries to reestablish the
        connection.
        """
        if self._ws or self._tasks:
            return

        self._current_status = ConnectionStatus.CONNECTING
        async for websocket in connect(self.uri, ping_interval=None):
            self._ws = websocket
            self._tasks.append(asyncio.create_task(self._dispatcher()))
            self._tasks.append(asyncio.create_task(self._listener()))
            self._tasks.append(asyncio.create_task(self._keep_alive()))
            list(map(lambda x: x.add_done_callback(self._callback), self._tasks))
            self._current_status = ConnectionStatus.CONNECTED
            await self._on_connect()
            await self.wait_for_disconnect()
            if self._desired_status == ConnectionStatus.DISCONNECTED:
                break

    async def _on_connect(self) -> None:
        """
        Call event handlers tied to client connection.
        """
        for handler in self._connect_handlers:
            try:
                handler(self)
            except Exception as e:
                self._logger.exception(['Unhandled error in connect handler'])
        self._connect_event.set()
        self._disconnect_event.clear()

    async def _on_disconnect(self) -> None:
        """
        Call event handlers tied to client disconnection.
        """
        for handler in self._disconnect_handlers:
            try:
                handler(self)
            except Exception:
                self._logger.exception(['Unhandled error in disconnect handler'])
        self._connect_event.clear()
        self._disconnect_event.set()

    async def _on_recv(self, message: str) -> None:
        """
        Call event handlers tied the the receipt of new messages.

        :param message: The message that was received.
        :type message: str
        """
        for handler in self._recv_handlers:
            try:
                handler(self, message)
            except Exception:
                self._logger.exception(['Unhandled error in recv handler'])