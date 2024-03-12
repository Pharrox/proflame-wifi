from logging import Logger


def fmt_log(logger: Logger, level: str, message: str, *args) -> str:
    return '{}:{}:{}'.format(level, logger.name, message % tuple(args))
