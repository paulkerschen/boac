import logging
from logging.handlers import RotatingFileHandler

import ldap3.utils.log as ldap3_log


def initialize_logger(app):
    level = app.config['LOGGING_LEVEL']
    location = app.config['LOGGING_LOCATION']

    # Configure the app logger, root logger, and library loggers as desired.
    loggers = [
        app.logger,
        logging.getLogger(),
        logging.getLogger('ldap3'),
    ]

    # Capture runtime warnings so that we'll see them.
    logging.captureWarnings(True)

    # For more detail from the LDAP library, specify BASIC or NETWORK.
    ldap3_log.set_library_log_detail_level(ldap3_log.ERROR)

    # If location is configured as "STDOUT", don't create a new log file.
    if location == 'STDOUT':
        handlers = app.logger.handlers
    else:
        file_handler = RotatingFileHandler(location, mode='a', maxBytes=1024 * 1024 * 100, backupCount=20)
        handlers = [file_handler]

    for handler in handlers:
        handler.setLevel(level)
        formatter = logging.Formatter(app.config['LOGGING_FORMAT'])
        handler.setFormatter(formatter)

    for logger in loggers:
        for handler in handlers:
            logger.addHandler(handler)
            logger.setLevel(level)
