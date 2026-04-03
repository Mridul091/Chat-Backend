import logging
import sys
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

def setup_logging():
    # Set the base logging config to ensure everything is caught
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    structlog.configure(
        processors=[
            # If log level is too low, ignore this log
            structlog.stdlib.filter_by_level,
            # Add context variables to the logs
            structlog.contextvars.merge_contextvars,
            # Add the log level to the event dict
            structlog.stdlib.add_log_level,
            # Add the name of the logger to event dict
            structlog.stdlib.add_logger_name,
            # Perform %-style formatting.
            structlog.stdlib.PositionalArgumentsFormatter(),
            # Add a timestamp in ISO 8601 format
            structlog.processors.TimeStamper(fmt="iso"),
            # If the "exc_info" key in the event dict is either true or a sys.exc_info() tuple, remove "exc_info" and render the exception with traceback into the "exception" key.
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            # Render logs in a beautiful console format for development
            structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

# Run the setup once
setup_logging()

# Create the global logger instance
logger = structlog.get_logger()

