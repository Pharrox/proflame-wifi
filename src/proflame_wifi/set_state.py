"""
Helper script for requesting state updates to a fireplace.
"""
import argparse
import asyncio
import json
import sys

from .manager import ProflameManager
from .const import DEFAULT_PORT


async def set_state(host: str, port: int, field: str, value: int):
    """
    Request a change to the state of a fireplace.

    :param host: The DNS name or IP address of the fireplace.
    :type host: str
    :param port: The port that the fireplace is listening on.
    :type port: int
    :param field: The API attribute to request an update for.
    :type field: str
    :param value: The new value to set for the specified attribute.
    :type value: int
    """
    client = ProflameManager(
        device_id='temp',
        host=host,
        port=port,
    )

    await client.connect()
    initial = await client.wait_for_state_available(field)
    result = await client.set_state(field, value, True)
    await client.disconnect()

    print(json.dumps({
        'field': field,
        'result': result,
        'initial': initial,
        'requested': value,
    }))

def main():
    """
    Entrypoint of the script.
    """
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description='Updates the state of a Proflame fireplace'
    )

    parser.add_argument('host', action='store', metavar='HOST')
    parser.add_argument('field', action='store', metavar='FIELD')
    parser.add_argument('value', action='store', metavar='VALUE', type=int)
    args = parser.parse_args()

    host = args.host.split(':')[0] if ':' in args.host else args.host
    port = int(args.host.split(':')[1] if ':' in args.host else DEFAULT_PORT)

    asyncio.run(set_state(host, port, args.field, args.value))
