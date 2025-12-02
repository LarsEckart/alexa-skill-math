"""Launch request handler."""

import logging

from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.utils import is_request_type

from alexa import data

logger = logging.getLogger(__name__)


class LaunchRequestHandler(AbstractRequestHandler):
    """
    Handler for skill launch.

    Always asks who is playing, then shows personalized welcome
    for returning players or starts setup for new players.
    """

    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        logger.info("In LaunchRequestHandler")

        session_attr = handler_input.attributes_manager.session_attributes

        # Always ask who's playing at launch
        session_attr["state"] = data.STATE_ASK_PLAYER
        speech = data.WELCOME_MESSAGE
        reprompt = data.ASK_PLAYER

        handler_input.response_builder.speak(speech).ask(reprompt)
        return handler_input.response_builder.response
