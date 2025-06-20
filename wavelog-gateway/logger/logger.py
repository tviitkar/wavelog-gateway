import logging


def logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    console_format = logging.Formatter(
        "%(asctime)s %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(console_format)

    logger.addHandler(console_handler)
    logger.setLevel(logging.DEBUG)

    return logger
