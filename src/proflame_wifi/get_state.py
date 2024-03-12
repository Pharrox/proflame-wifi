"""
Helper script for retrieving information about a fireplace.
"""
import argparse
import asyncio
import json
import sys

from .client import ProflameClient
from .const import DEFAULT_PORT


async def get_state(host: str, port: int) -> None:
    """
    Get the full state of a fireplace and print it to the console.

    :param host: The DNS name or IP address of the fireplace.
    :type host: str
    :param port: The port that the fireplace is listening on.
    :type port: int
    """
    client = ProflameClient(
        device_id='temp',
        host=host,
        port=port
    )
    await client.connect()
    await client.wait_for_active()
    await asyncio.sleep(0.5)
    print(json.dumps(client.full_state, indent=2))
    await client.disconnect()

def main():
    """
    Entrypoint of the script.
    """
    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description='Dumps the state of a Proflame fireplace'
    )

    parser.add_argument('host', action='store', metavar='HOST')
    args = parser.parse_args()

    host = args.host.split(':')[0] if ':' in args.host else args.host
    port = int(args.host.split(':')[1] if ':' in args.host else DEFAULT_PORT)

    asyncio.run(get_state(host, port))
