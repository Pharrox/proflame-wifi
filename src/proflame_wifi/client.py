"""
Low level functionality for interacting with Proflame fireplaces.
"""
import asyncio
from enum import StrEnum
import json
from json.decoder import JSONDecodeError
from logging import Logger, getLogger
from typing import Any, Callable, NoReturn, Self

from .connection import ConnectionManager
from .const import DEFAULT_PORT, ApiControl
from .strings import (
    CONNECTION_ACKNOWLEDGED,
    JSON_MSG_INVALID_SCHEMA,
    JSON_MSG_INVALID_TYPE,
    PING_ACKNOWLEDGED,
    UNKNOWN_CONTROL_MSG,
)

_LOGGER = getLogger(__name__)


class ClientStatus(StrEnum):
    """
    Enum that represents valid states of a Proflame connection.
    """

    ACTIVE = 'ACTIVE'
    CONNECTING = 'CONNECTING'
    CONNECTED = 'CONNECTED'
    DISCONNECTING = 'DISCONNECTING'
    DISCONNECTED = 'DISCONNECTED'

class ProflameClient:
    """
    Basic client used for interacting with Proflame fireplaces.
    """

    def __init__(self,
        host: str,
        port: int | None = None,
        logger: Logger | None = None,
        ping_interval: int | None = None,
        callbacks: list[Callable[[Self, str, int], NoReturn]] | None = None
    ) -> None:
        """
        Create a new instance of the ProflameClient class.

        :param host: The DNS name or IP address of the fireplace.
        :type host: str
        :param port: The port that the fireplace API listens on.
        :type port: int or None
        :param logger: A python logger to use for generated messages.
        :type: logger: Logger or None
        :param ping_interval: The frequency (in seconds) at which keepalive
            messages should be sent to the fireplace.
        :type ping_interval: int or None
        :param callbacks: A list of callback functions which should be invoked
            any time a new state update is received from the fireplace.
        :type callbacks: list[Callable[[ProflameClient, str, int], NoReturn]]
            or None
        """

        self._host: str = host
        self._port: int = port or DEFAULT_PORT
        self._logger: Logger = logger or _LOGGER
        self._ping_interval: int | None = ping_interval
        self._callbacks: list[Callable[[ProflameClient, str, int], NoReturn]] = callbacks or []

        self._connection = ConnectionManager(
            host=self._host,
            port=self._port,
            logger=self._logger,
            ping_interval=self._ping_interval,
            ping_message=ApiControl.PING,
            connect_handlers=[self._handle_connect],
            disconnect_handlers=[self._handle_disconnect],
            recv_handlers=[self._handle_recv],
        )

        self._active = False
        self._active_event = asyncio.Event()
        self._state_events: dict[str, asyncio.Event] = {}
        self._state_change_events: dict[str, list[asyncio.Event]] = {}
        self._state = {}

    @property
    def full_state(self) -> dict[str, int]:
        """
        Retrieve a full copy of all the attributes reported by the fireplace.

        The fields in the returned object will vary depending on what the
        fireplace has reported.

        :return: A snapshot of the current fireplace state.
        :rtype: dict[str, int]
        """
        return {**self._state}
    
    @property
    def status(self) -> ClientStatus:
        """
        Get the current status of the fireplace API connection.

        :return: The current statis of the fireplace client.
        :rtype: ClientStatus
        """
        if self._connection.connected and self._active:
            return ClientStatus.ACTIVE
        else:
            return self._connection.status

    @property
    def uri(self) -> str:
        """
        Get the formatted URI for the fireplace websocket.

        :return: The fireplace websocket URI.
        :rtype: str
        """
        return self._connection.uri
    
    def _handle_connect(self, client: ConnectionManager) -> None:
        """
        Handle a new connection event.

        :param client: The websocket connection manager that triggered the
        event.
        :type client: ConnectionManager
        """
        asyncio.create_task(client.send(ApiControl.CONN_SYN))
    
    def _handle_disconnect(self, client: ConnectionManager) -> None:
        """
        Handle the websocket connection being closed or dropped.
        """
        self._active = False
        self._active_event.clear()

    def _handle_control_message(self, message: str) -> None:
        """
        Process a system control/info message from the websocket.

        :param message: The message to be processed.
        :type message: str
        """
        if message == ApiControl.CONN_ACK:
            self._logger.debug(CONNECTION_ACKNOWLEDGED)
            self._active = True
            self._active_event.set()
        elif message == ApiControl.PONG:
            self._logger.debug(PING_ACKNOWLEDGED)
        else:
            self._logger.warning(UNKNOWN_CONTROL_MSG, message)

    def _handle_json_message(self, message: Any) -> None:
        """
        Process a system state message from the websocket.

        :param message: The message to be processed.
        :type message: Any
        """
        if not isinstance(message, dict):
            self._logger.warning(JSON_MSG_INVALID_TYPE, json.dumps(message))
        elif any(not isinstance(x, int) for x in message.values()):
            self._logger.warning(JSON_MSG_INVALID_SCHEMA, json.dumps(message))
        else:
            for k, v in message.items():
                self._state[k] = v
                if k not in self._state_events.keys():
                    self._state_events[k] = asyncio.Event()
                self._state_events[k].set()
                state_change_events = self._state_change_events.get(k, [])
                list(map(lambda x: x.set(), state_change_events))
                for callback in self._callbacks:
                    callback(self, k, v)

    def _handle_message(self, message: str) -> None:
        """
        Process a message from the websocket.

        :param message: The message to be processed.
        :type message: str
        """
        try:
            self._handle_json_message(json.loads(message))
        except JSONDecodeError:
            self._handle_control_message(message)
    
    def _handle_recv(self, client: ConnectionManager, message: str) -> None:
        """
        Handle receipt of a new message from the websocket.

        :param client: The websocket connection manager that triggered the
            event.
        :type client: ConnectionManager
        :param message: The new message that was received.
        :type message: str
        """
        self._handle_message(message)

    async def connect(self) -> None:
        """
        Open a connection to the fireplace.
        """
        await self._connection.connect(wait=True)

    async def disconnect(self) -> None:
        """
        Close the connection to the fireplace.
        """
        await self._connection.disconnect(wait=True)

    def get_state(self, attribute: str) -> int | None:
        """
        Get the state of a specific attribute by its name.

        :param attribute: The name of the fireplace attribute to retrieve.
        :type attribute: str
        :return: The value of the requested attribute or None if the requested
            attribute has not been reported by the fireplace.
        :rtype: int or None
        """
        return self._state.get(attribute, None)

    def register_callback(self, callback: Callable[[Self, str], NoReturn]) -> None:
        """
        Register a callback that will be invoked when a state change is
        reported by the fireplace.

        :param callback: The function to invoke whenever a state change is
            reported by the fireplace.
        :type callback: Callable[[ProflameClient, str, int], NoReturn]
        """
        self._callbacks.append(callback)

    async def set_state(self, attribute: str, value: int, wait: bool = False, wait_timeout: float = 3) -> int | bool | None:
        """
        Set the state of a specific attribute by its name.

        :param attribute: The name of the fireplace attribute to set.
        :type attribute: str
        :param value: The new value to set for the specifies attribute.
        :type value: int
        :return: The new state of the attribute as reported by the fireplace
            (if wait is set to True), False if a timeout was encountered while
            waiting for the fireplace to confirm the state update, or None if
            the update was made without waiting for confirmation from the
            fireplace.
        :rtype: int or bool or None
        """
        current = self.get_state(attribute)
        if wait and value != current:
            if attribute not in self._state_change_events.keys():
                self._state_change_events[attribute] = []

            event = asyncio.Event()
            await self._connection.send(json.dumps({attribute: value}))
            self._state_change_events[attribute].append(event)

            try:
                await asyncio.wait_for(event.wait(), timeout=wait_timeout)
                return self.get_state(attribute)
            except asyncio.TimeoutError:
                return False
            finally:
                self._state_change_events[attribute].remove(event)
        elif wait:
            await self._connection.send(json.dumps({attribute: value}))
            return value
        else:
            await self._connection.send(json.dumps({attribute: value}))
    
    async def wait_for_active(self) -> None:
        """
        Wait for the fireplace connection to become active.
        """
        await self._active_event.wait()
    
    async def wait_for_state_available(self, field: str) -> int:
        """
        Wait until a specified state key is available from the API.

        On connection the fireplace will send multiple messages after a
        connection becomes active to report the state of all supported
        functionality.

        :param field: The attribute that you want to wait to become available
            from the fireplace.
        :type wait: str
        """
        if field not in self._state_events.keys():
            self._state_events[field] = asyncio.Event()
        await self._state_events[field].wait()
        return self.get_state(field)
