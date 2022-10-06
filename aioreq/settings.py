import logging

LOGGER_NAME = 'aioreq'
MAIN_LOGGER_LEVEL = logging.INFO
# MAIN_LOGGER_LEVEL = 100
STREAM_HANDLER_LEVEL = logging.DEBUG
FORMAT = '%(name)s | %(levelname)s | %(message)s | %(asctime)s'

BUFFER_SIZE = 4048

DEFAULT_CONNECTION_TIMEOUT = 4
DEFAULT_DNS_SERVER = '8.8.8.8'

main_logger = logging.getLogger(LOGGER_NAME)
main_logger.setLevel(MAIN_LOGGER_LEVEL)

handler = logging.StreamHandler()
handler.setLevel(STREAM_HANDLER_LEVEL)

formatter = logging.Formatter(FORMAT)

handler.setFormatter(formatter)
main_logger.addHandler(handler)
