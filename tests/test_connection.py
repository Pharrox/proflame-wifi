import asyncio
import unittest

from websockets.server import serve

from proflame_wifi.connection import ConnectionManager
from proflame_wifi.const import ApiControl

from .mock_fireplace import MockFireplace


class ConnectionTest(unittest.IsolatedAsyncioTestCase):

    async def test_create(self):
        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ConnectionManager('127.0.0.1', 3838)
            self.assertFalse(client.connected)
    
    async def test_connection(self):
        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ConnectionManager('127.0.0.1', 3838)
            await client.connect()
            await client.wait_for_connect()
            self.assertTrue(client.connected)
            await client.disconnect()
            await client.wait_for_disconnect()
            self.assertFalse(client.connected)
    
    async def test_connection_wait(self):
        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ConnectionManager('127.0.0.1', 3838)
            await client.connect(wait=True)
            self.assertTrue(client.connected)
            await client.disconnect(wait=True)
            self.assertFalse(client.connected)
    
    async def test_communication(self):
        responses = []
        def handler(source: ConnectionManager, message: str) -> None:
            responses.append(message)
            asyncio.create_task(source.disconnect())

        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ConnectionManager(
                '127.0.0.1', 3838,
                recv_handlers=[handler]
            )
            await client.connect(wait=True)
            self.assertTrue(client.connected)
            await client.send(ApiControl.CONN_SYN)
            await client.wait_for_disconnect()
            self.assertFalse(client.connected)
            self.assertGreater(len(responses), 1)
            self.assertEqual(responses[0], ApiControl.CONN_ACK)
    
    async def test_connect_handler(self):
        called = 0
        def handler(source: ConnectionManager) -> None:
            nonlocal called
            called += 1

        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ConnectionManager(
                '127.0.0.1', 3838,
                connect_handlers=[handler]
            )
            await client.connect(wait=True)
            self.assertTrue(client.connected)
            self.assertEqual(called, 1)
            await client.disconnect(wait=True)
            self.assertFalse(client.connected)
            self.assertEqual(called, 1)
    
    async def test_connect_handler_err(self):
        called = 0
        def handler(source: ConnectionManager) -> None:
            nonlocal called
            called += 1

        def broken_handler(source: ConnectionManager) -> None:
            raise RuntimeError('Test error')

        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ConnectionManager(
                '127.0.0.1', 3838,
                connect_handlers=[broken_handler, handler]
            )
            await client.connect(wait=True)
            self.assertTrue(client.connected)
            self.assertEqual(called, 1)
            await client.disconnect(wait=True)
            self.assertFalse(client.connected)
            self.assertEqual(called, 1)
    
    async def test_disconnect_handler(self):
        called = 0
        def handler(source: ConnectionManager) -> None:
            nonlocal called
            called += 1

        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ConnectionManager(
                '127.0.0.1', 3838,
                disconnect_handlers=[handler]
            )
            await client.connect(wait=True)
            self.assertTrue(client.connected)
            self.assertEqual(called, 0)
            await client.disconnect(wait=True)
            self.assertFalse(client.connected)
            self.assertEqual(called, 1)
    
    async def test_disconnect_handler_err(self):
        called = 0
        def handler(source: ConnectionManager) -> None:
            nonlocal called
            called += 1

        def broken_handler(source: ConnectionManager) -> None:
            raise RuntimeError('Test error')

        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ConnectionManager(
                '127.0.0.1', 3838,
                disconnect_handlers=[broken_handler, handler]
            )
            await client.connect(wait=True)
            self.assertTrue(client.connected)
            self.assertEqual(called, 0)
            await client.disconnect(wait=True)
            self.assertFalse(client.connected)
            self.assertEqual(called, 1)
    
    async def test_recv_handler(self):
        called = asyncio.Event()
        def handler(source: ConnectionManager, message: str) -> None:
            called.set()

        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ConnectionManager(
                '127.0.0.1', 3838,
                recv_handlers=[handler]
            )
            await client.connect(wait=True)
            self.assertTrue(client.connected)
            await client.send(ApiControl.CONN_SYN)
            await asyncio.wait_for(called.wait(), timeout=1)
            self.assertTrue(called.is_set())
            await client.disconnect()
            self.assertFalse(client.connected)
    
    async def test_recv_handler_err(self):
        called = asyncio.Event()
        def handler(source: ConnectionManager, message: str) -> None:
            called.set()
        def broken_handler(source: ConnectionManager, message: str) -> None:
            raise RuntimeError('Test error')

        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            client = ConnectionManager(
                '127.0.0.1', 3838,
                recv_handlers=[broken_handler, handler]
            )
            await client.connect(wait=True)
            self.assertTrue(client.connected)
            await client.send(ApiControl.CONN_SYN)
            await asyncio.wait_for(called.wait(), timeout=1)
            self.assertTrue(called.is_set())
            await client.disconnect()
            await client.wait_for_disconnect()
            self.assertFalse(client.connected)
    
    async def test_interrupt(self):
        client = ConnectionManager('127.0.0.1', 3838, ping_interval=1)
        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            await client.connect(wait=True)
            self.assertTrue(client.connected)
        
        await client.wait_for_disconnect()
        self.assertFalse(client.connected)

        async with serve(server.serve, '127.0.0.1', 3838):
            await client.wait_for_connect()
            self.assertTrue(client.connected)
            await client.disconnect(wait=True)
            self.assertFalse(client.connected)
    
    async def test_connect_idepotency(self):
        client = ConnectionManager('127.0.0.1', 3838)
        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            await client.connect(wait=True)
            self.assertTrue(client.connected)
            await client.connect(wait=True)
            self.assertTrue(client.connected)
            await client.disconnect(wait=False)
            self.assertFalse(client.connected)
    
    async def test_message_queue(self):
        called = 0
        def handler(source: ConnectionManager, message: str) -> None:
            nonlocal called
            if message.startswith('TEST'):
                called += 1
            if message == 'TEST3':
                asyncio.create_task(source.disconnect())

        client = ConnectionManager('127.0.0.1', 3838,
            ping_interval=1,
            recv_handlers=[handler],
        )

        server = MockFireplace()
        async with serve(server.serve, '127.0.0.1', 3838):
            await client.connect(wait=True)
            self.assertTrue(client.connected)
            self.assertEqual(called, 0)
        
        await client.wait_for_disconnect()
        self.assertFalse(client.connected)
        await client.send('TEST1')
        await client.send('TEST2')
        await client.send('TEST3')

        async with serve(server.serve, '127.0.0.1', 3838):
            await client.wait_for_connect()
            self.assertTrue(client.connected)
            await client.wait_for_disconnect()
            self.assertFalse(client.connected)
            self.assertEqual(called, 3)


if __name__ == '__main__':
    unittest.main()
