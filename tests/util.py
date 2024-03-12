from asyncio import Future, wait_for
from logging import Logger
from typing import Any


def fmt_log(logger: Logger, level: str, message: str, *args) -> str:
    return '{}:{}:{}'.format(level, logger.name, message % tuple(args))

async def run_async(future) -> Any:
    return await wait_for(future, timeout=3)
