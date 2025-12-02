"""Request and response interceptors for the Alexa skill."""

import logging

from ask_sdk_core.dispatch_components import (
    AbstractExceptionHandler,
    AbstractRequestInterceptor,
    AbstractResponseInterceptor,
)

from alexa import data

logger = logging.getLogger(__name__)


class CacheResponseForRepeatInterceptor(AbstractResponseInterceptor):
    """
    Cache the response for repeat functionality.

    Stores the response in session attributes so it can be
    repeated if the user asks.
    """

    def process(self, handler_input, response):
        session_attr = handler_input.attributes_manager.session_attributes
        session_attr["recent_response"] = response


class RequestLogger(AbstractRequestInterceptor):
    """Log incoming requests."""

    def process(self, handler_input):
        logger.info(f"Request Envelope: {handler_input.request_envelope}")


class ResponseLogger(AbstractResponseInterceptor):
    """Log outgoing responses."""

    def process(self, handler_input, response):
        logger.info(f"Response: {response}")


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """
    Catch-all exception handler.

    Logs errors and provides a user-friendly error message in German.
    """

    def can_handle(self, handler_input, exception):
        return True

    def handle(self, handler_input, exception):
        logger.error(exception, exc_info=True)

        speech = data.ERROR_MESSAGE
        handler_input.response_builder.speak(speech).ask(speech)

        return handler_input.response_builder.response
