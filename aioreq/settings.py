import logging

LOGGER_NAME = 'aioreq'


main_logger = logging.getLogger(LOGGER_NAME)
main_logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)
main_logger.addHandler(handler)
