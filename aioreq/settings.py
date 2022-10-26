import logging

from pathlib import Path
from configparser import ConfigParser

ini_file_path_posix = Path(__file__).parent / 'settings.ini'
ini_file_path = str(ini_file_path_posix.absolute())

parser = ConfigParser()
parser.read(ini_file_path)

log_level_mapper = {
        'notset': logging.NOTSET,
        'debug' : logging.DEBUG,
        'info'  : logging.INFO,
        'warning' : logging.WARNING,
        'error' : logging.ERROR,
        'critical' : logging.CRITICAL
        }

log_format_mapper = {
        '$name': '%(name)s',
        '$levelno' : '%(levelno)s',
        '$levelname' : '%(levelname)s',
        '$pathname' : '%(pathname)s',
        '$filename' : '%(filename)s',
        '$module' : '%(module)s',
        '$lineno' : '%(lineno)d',
        '$funcName' : '%(funcName)s',
        '$created' : '%(created)f',
        '$asctime' : '%(asctime)s',
        '$msecs' : '%(msecs)d',
        '$relativeCreated' : '%(relativeCreated)d',
        '$thread' : "%(thread)d",
        '$threadName' : '%(threadName)s',
        '$process' : '%(process)d',
        '$message' : '%(message)s'
        }

LOGGER_NAME = parser.get('Logging', 'logger_name')

MAIN_LOGGER_LEVEL = parser.get('Logging', 'logger_level')
STREAM_HANDLER_LEVEL = parser.get('Logging', 'stream_handler_level')


if any(
        (
        (MAIN_LOGGER_LEVEL not in log_level_mapper),
        (STREAM_HANDLER_LEVEL not in log_level_mapper)
        )
    ):
    print(type(MAIN_LOGGER_LEVEL), type(STREAM_HANDLER_LEVEL), repr(MAIN_LOGGER_LEVEL), repr('debug'))
    raise ValueError('Setting.ini contains invalid value '
                     f'for one of the logger levels ({MAIN_LOGGER_LEVEL} or {STREAM_HANDLER_LEVEL})')

MAIN_LOGGER_LEVEL = log_level_mapper.get(MAIN_LOGGER_LEVEL) # type: ignore
STREAM_HANDLER_LEVEL = log_level_mapper.get(STREAM_HANDLER_LEVEL) # type: ignore

FORMAT = parser.get('Logging', 'stream_handler_format')

for key, value in log_format_mapper.items():
    FORMAT = FORMAT.replace(key, value)

BUFFER_SIZE = 4048 #deprecated

DEFAULT_CONNECTION_TIMEOUT = int(parser.getfloat ('Connection', 'default_connection_timeout'))
DEFAULT_DNS_SERVER = parser['Connection']['default_dns_server']


main_logger = logging.getLogger(LOGGER_NAME)
main_logger.setLevel(MAIN_LOGGER_LEVEL)

handler = logging.StreamHandler()
handler.setLevel(STREAM_HANDLER_LEVEL)

formatter = logging.Formatter(FORMAT)

handler.setFormatter(formatter)
main_logger.addHandler(handler)
