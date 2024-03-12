import asyncio
import json
import unittest

from websockets.server import serve

from proflame_wifi.client import ClientStatus, ProflameClient
from proflame_wifi.connection import ConnectionManager
from proflame_wifi.const import MAX_FAN_SPEED, ApiAttrs, ApiControl, OperatingMode
from proflame_wifi.strings import *

from .mock_fireplace import MockFireplace
from .util import fmt_log


class ClientTest(unittest.IsolatedAsyncioTestCase):

    async def test_create(self):
        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameClient('test', '127.0.0.1', 3838)
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
            self.assertEqual(client.device_id, 'test')
            self.assertEqual(client.uri, 'ws://127.0.0.1:3838')
            self.assertDictEqual(client.full_state, {})
    
    async def test_connection(self):
        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameClient('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertEqual(client.status, ClientStatus.CONNECTED)
            await client.wait_for_active()
            self.assertEqual(client.status, ClientStatus.ACTIVE)
            await client.disconnect()
            self.assertEqual(client.status, ClientStatus.DISCONNECTED)
    
    async def test_invalid_message(self):
        event = asyncio.Event()
        def handler(conn: ConnectionManager, message: str) -> None:
            if message == 'INVALID':
                event.set()

        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameClient('test', '127.0.0.1', 3838)
            client._connection.register_recv_handler(handler)
            msg = fmt_log(client._logger, 'WARNING', UNKNOWN_CONTROL_MSG, 'INVALID')
            with self.assertLogs(client._logger, 'WARNING') as cm:
                await client.connect()
                await client.wait_for_active()
                await client._connection.send('INVALID')
                await asyncio.wait_for(event.wait(), timeout=1)
                self.assertTrue(event.is_set())
                await client.disconnect()
                self.assertGreaterEqual(len(cm.output), 1)
                self.assertIn(msg, cm.output)
    
    async def test_invalid_json_type(self):
        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameClient('test', '127.0.0.1', 3838)
            payload = json.dumps([{'main_mode':0}])
            msg = fmt_log(client._logger, 'WARNING', JSON_MSG_INVALID_TYPE, payload)
            with self.assertLogs(client._logger, 'WARNING') as cm:
                await client.connect()
                await client.wait_for_active()
                await client._connection.send(payload)
                await asyncio.sleep(1)
                await client.disconnect()
                self.assertGreaterEqual(len(cm.output), 1)
                self.assertIn(msg, cm.output)
    
    async def test_invalid_json_schema(self):
        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameClient('test', '127.0.0.1', 3838)
            payload = json.dumps({'main_mode': 'off'})
            msg = fmt_log(client._logger, 'WARNING', JSON_MSG_INVALID_SCHEMA, payload)
            with self.assertLogs(client._logger, 'WARNING') as cm:
                await client.connect()
                await client.wait_for_active()
                await client._connection.send(payload)
                await asyncio.sleep(1)
                await client.disconnect()
                self.assertGreaterEqual(len(cm.output), 1)
                self.assertIn(msg, cm.output)
    
    async def test_callbacks(self):
        handled = asyncio.Event()
        def handler(client, field, value):
            if field == ApiAttrs.FAN_SPEED and value == 0:
                handled.set()

        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameClient('test', '127.0.0.1', 3838)
            client.register_callback(handler)
            await client.connect()
            await client.wait_for_state_available(ApiAttrs.FAN_SPEED)
            self.assertEqual(client.get_state(ApiAttrs.FAN_SPEED), 6)
            await client.set_state(ApiAttrs.FAN_SPEED, 0)
            await handled.wait()
            self.assertEqual(client.get_state(ApiAttrs.FAN_SPEED), 0)
            await client.disconnect()
    
    async def test_keepalive(self):
        event = asyncio.Event()
        invoked = 0
        def handler(conn: ConnectionManager, message: str) -> None:
            nonlocal invoked
            if message == ApiControl.PONG:
                invoked += 1
            if invoked >= 3:
                event.set()

        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameClient('test', '127.0.0.1', 3838, ping_interval=0.5)
            client._connection.register_recv_handler(handler)
            msg = fmt_log(client._logger, 'DEBUG', PING_ACKNOWLEDGED)
            with self.assertLogs(client._logger, 'DEBUG') as cm:
                await client.connect()
                await client.wait_for_active()
                await asyncio.wait_for(event.wait(), timeout=3)
                self.assertTrue(event.is_set())
                await client.disconnect()
                replies = [x for x in cm.output if x == msg]
                self.assertGreaterEqual(len(replies), 3)
    
    async def test_wait_for_state_available(self):
        server = MockFireplace(**{ApiAttrs.OPERATING_MODE: OperatingMode.THERMOSTAT})
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameClient('test', '127.0.0.1', 3838)
            await client.connect()
            self.assertIsNone(client.get_state(ApiAttrs.OPERATING_MODE))
            await client.wait_for_state_available(ApiAttrs.OPERATING_MODE)
            self.assertEqual(client.get_state(ApiAttrs.OPERATING_MODE), OperatingMode.THERMOSTAT)
            await client.disconnect()
    
    async def test_set_state_wait(self):
        server = MockFireplace(**{ApiAttrs.FAN_SPEED: MAX_FAN_SPEED})
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameClient('test', '127.0.0.1', 3838)
            await client.connect()
            await client.wait_for_state_available(ApiAttrs.FAN_SPEED)
            self.assertEqual(client.get_state(ApiAttrs.FAN_SPEED), MAX_FAN_SPEED)
            self.assertEqual(await client.set_state(ApiAttrs.FAN_SPEED, 3, True), 3)
            self.assertEqual(client.get_state(ApiAttrs.FAN_SPEED), 3)
            await client.disconnect()
    
    async def test_set_state_wait_timeout(self):
        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ProflameClient('test', '127.0.0.1', 3838)
            await client.connect()
            await client.wait_for_active()
            self.assertFalse(await client.set_state('ignore', 1, True, wait_timeout=0.5))
            await client.disconnect()
