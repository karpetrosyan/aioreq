import logging

main_logger = logging.getLogger('aioreq')
main_logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)
main_logger.addHandler(handler)
