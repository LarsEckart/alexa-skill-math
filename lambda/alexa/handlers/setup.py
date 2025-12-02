"""Setup flow handlers for name and grade collection."""

import logging

from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.utils import is_intent_name

from alexa import data
from alexa.persistence import get_persistence_manager

logger = logging.getLogger(__name__)


class SetupNameHandler(AbstractRequestHandler):
    """
    Handler for capturing user's name during setup.

    Triggered when user provides their name in the setup flow.
    """

    def can_handle(self, handler_input):
        session_attr = handler_input.attributes_manager.session_attributes
        return (
            is_intent_name("SetNameIntent")(handler_input)
            and session_attr.get("state") == data.STATE_SETUP_NAME
        )

    def handle(self, handler_input):
        logger.info("In SetupNameHandler")

        slots = handler_input.request_envelope.request.intent.slots
        name = slots.get("name", {})
        name_value = name.value if name else None

        session_attr = handler_input.attributes_manager.session_attributes

        if name_value:
            # Save name to profile
            pm = get_persistence_manager(handler_input)
            profile = pm.get_user_profile()
            profile.name = name_value
            pm.save_user_profile(profile)
            pm.increment_session_count()
            pm.commit()

            # Move to grade setup
            session_attr["state"] = data.STATE_SETUP_GRADE
            speech = data.ASK_GRADE.format(name=name_value)
            reprompt = data.INVALID_GRADE
        else:
            speech = data.ASK_NAME
            reprompt = data.ASK_NAME

        handler_input.response_builder.speak(speech).ask(reprompt)
        return handler_input.response_builder.response


class SetupGradeHandler(AbstractRequestHandler):
    """
    Handler for capturing user's grade level during setup.

    Triggered when user provides their grade in the setup flow.
    """

    def can_handle(self, handler_input):
        session_attr = handler_input.attributes_manager.session_attributes
        return (
            is_intent_name("SetGradeIntent")(handler_input)
            and session_attr.get("state") == data.STATE_SETUP_GRADE
        )

    def handle(self, handler_input):
        logger.info("In SetupGradeHandler")

        slots = handler_input.request_envelope.request.intent.slots
        grade_slot = slots.get("grade", {})
        grade_value = grade_slot.value if grade_slot else None

        session_attr = handler_input.attributes_manager.session_attributes

        try:
            grade = int(grade_value) if grade_value else None
            if grade and 1 <= grade <= 4:
                # Save grade to profile
                pm = get_persistence_manager(handler_input)
                profile = pm.get_user_profile()
                profile.grade = grade
                pm.save_user_profile(profile)
                pm.commit()

                grade_name = data.GRADE_NAMES.get(grade, str(grade))
                session_attr["state"] = data.STATE_NONE

                speech = data.CONFIRM_GRADE.format(grade=grade_name)
                speech += " " + data.REPROMPT_GENERAL
                reprompt = data.REPROMPT_GENERAL
            else:
                speech = data.INVALID_GRADE
                reprompt = data.INVALID_GRADE
        except (ValueError, TypeError):
            speech = data.INVALID_GRADE
            reprompt = data.INVALID_GRADE

        handler_input.response_builder.speak(speech).ask(reprompt)
        return handler_input.response_builder.response
