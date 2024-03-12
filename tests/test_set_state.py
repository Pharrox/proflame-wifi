import asyncio
import contextlib
import io
import json
import unittest
from unittest.mock import patch
import sys

from websockets.server import serve

from proflame_wifi.const import ApiAttrs, OperatingMode
from proflame_wifi.set_state import main

from .mock_fireplace import MockFireplace


class GetStateTest(unittest.IsolatedAsyncioTestCase):

    async def test_get_state(self):
        args = ['set-state', '127.0.0.1:3838', ApiAttrs.FLAME_HEIGHT, '6']
        stdout = io.StringIO()

        future: asyncio.Future = None
        def mock_run(coroutine: asyncio.Future) -> None:
            nonlocal future
            future = coroutine

        server = MockFireplace(**{
            ApiAttrs.OPERATING_MODE: OperatingMode.MANUAL,
            ApiAttrs.FLAME_HEIGHT: 3,
            ApiAttrs.CURRENT_TEMPERATURE: 700,
            ApiAttrs.TARGET_TEMPERATURE: 750
        })

        with patch.object(sys, 'argv', args):
            with patch.object(asyncio, 'run', mock_run):
                with contextlib.redirect_stdout(stdout):
                    async with serve(server.serve, '127.0.0.1', 3838):
                        main()
                        await future
        
        stdout.seek(0)
        result = json.loads(stdout.read())
        self.assertDictEqual(result, {
            'field': ApiAttrs.FLAME_HEIGHT,
            'initial': 3,
            'requested': 6,
            'result': 6,
        })


if __name__ == '__main__':
    unittest.main()
