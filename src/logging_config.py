import logging


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="{asctime} [{name}] [{levelname}] {message}",
        style='{',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("app.log")
        ]
    )

