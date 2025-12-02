"""Launch request handler."""

import logging

from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.utils import is_request_type

from alexa import data
from alexa.persistence import get_persistence_manager

logger = logging.getLogger(__name__)


class LaunchRequestHandler(AbstractRequestHandler):
    """
    Handler for skill launch.

    Handles welcome message based on whether user is new or returning.
    For first-time users, initiates setup flow to get name and grade.
    For returning users, shows personalized welcome with last session stats.
    """

    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        logger.info("In LaunchRequestHandler")

        pm = get_persistence_manager(handler_input)
        session_attr = handler_input.attributes_manager.session_attributes

        if pm.is_first_time_user():
            # First-time user: start setup flow
            session_attr["state"] = data.STATE_SETUP_NAME
            speech = data.WELCOME_MESSAGE_FIRST_TIME
            reprompt = data.ASK_NAME
        else:
            # Returning user
            profile = pm.get_user_profile()
            session_stats = pm.get_session_stats()

            # Increment session count
            pm.increment_session_count()
            pm.commit()

            if profile.name:
                total = session_stats.get("total_questions", 0)
                correct = session_stats.get("total_correct", 0)

                if total > 0:
                    speech = data.WELCOME_MESSAGE_RETURNING.format(
                        name=profile.name,
                        correct=correct,
                        total=total,
                    )
                else:
                    speech = data.WELCOME_MESSAGE_RETURNING_NO_STATS.format(name=profile.name)
            else:
                speech = data.WELCOME_MESSAGE_UNNAMED

            reprompt = data.REPROMPT_GENERAL
            session_attr["state"] = data.STATE_NONE

        handler_input.response_builder.speak(speech).ask(reprompt)
        return handler_input.response_builder.response
