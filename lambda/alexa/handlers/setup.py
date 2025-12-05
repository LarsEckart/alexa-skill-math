"""Setup flow handlers for player selection and grade collection."""

import contextlib
import logging

from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.utils import is_intent_name

from alexa import data
from alexa.handlers.helpers import get_srs_from_session
from alexa.persistence import get_persistence_manager

logger = logging.getLogger(__name__)


class SelectPlayerHandler(AbstractRequestHandler):
    """
    Handler for selecting which player is playing.

    Triggered when user provides their name at the start of a session.
    Always asks for grade level so user can choose difficulty each session.
    """

    def can_handle(self, handler_input):
        session_attr = handler_input.attributes_manager.session_attributes
        return (
            is_intent_name("SetNameIntent")(handler_input)
            and session_attr.get("state") == data.STATE_ASK_PLAYER
        )

    def handle(self, handler_input):
        logger.info("In SelectPlayerHandler")

        slots = handler_input.request_envelope.request.intent.slots
        name_slot = slots.get("name", {})
        name_value = name_slot.value if name_slot else None

        session_attr = handler_input.attributes_manager.session_attributes

        if not name_value:
            speech = data.ASK_PLAYER
            reprompt = data.ASK_PLAYER
            handler_input.response_builder.speak(speech).ask(reprompt)
            return handler_input.response_builder.response

        # Set the current player
        pm = get_persistence_manager(handler_input)
        pm.set_current_player(name_value)

        # Store in session for display (preserve original casing)
        session_attr["current_player"] = name_value.lower().strip()
        session_attr["current_player_display"] = name_value

        # Always ask for grade - allows choosing difficulty each session
        session_attr["state"] = data.STATE_SETUP_GRADE

        if pm.is_new_player():
            speech = data.WELCOME_MESSAGE_NEW_PLAYER.format(name=name_value)
        else:
            # Returning player - welcome back and ask for grade
            session_stats = pm.get_session_stats()
            total = session_stats.get("total_questions", 0)
            correct = session_stats.get("total_correct", 0)

            if total > 0:
                speech = data.WELCOME_MESSAGE_RETURNING.format(
                    name=name_value,
                    correct=correct,
                    total=total,
                )
            else:
                speech = data.WELCOME_MESSAGE_RETURNING_NO_STATS.format(name=name_value)

        reprompt = data.ASK_GRADE.format(name=name_value)
        handler_input.response_builder.speak(speech).ask(reprompt)
        return handler_input.response_builder.response


class SetupGradeHandler(AbstractRequestHandler):
    """
    Handler for capturing player's grade level during setup.

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

        # Try to get the resolved value (id) from slot resolution
        grade = None
        if grade_slot:
            # First try to get the canonical ID from entity resolution
            resolutions = getattr(grade_slot, "resolutions", None)
            if resolutions and resolutions.resolutions_per_authority:
                for resolution in resolutions.resolutions_per_authority:
                    if resolution.status.code.value == "ER_SUCCESS_MATCH":
                        grade = int(resolution.values[0].value.id)
                        break

            # Fallback: try to parse the raw value as integer
            if grade is None and grade_slot.value:
                with contextlib.suppress(ValueError):
                    grade = int(grade_slot.value)

        session_attr = handler_input.attributes_manager.session_attributes

        if not (grade and 1 <= grade <= 4):
            player_name = session_attr.get("current_player_display", "")
            speech = data.INVALID_GRADE
            reprompt = data.ASK_GRADE.format(name=player_name)
            handler_input.response_builder.speak(speech).ask(reprompt)
            return handler_input.response_builder.response

        # Save grade to profile
        pm = get_persistence_manager(handler_input)
        profile = pm.get_user_profile()
        profile.grade = grade
        pm.save_user_profile(profile)
        pm.increment_session_count()
        pm.commit()

        grade_name = data.GRADE_NAMES.get(grade, str(grade))

        # Start quiz immediately
        srs = get_srs_from_session(handler_input)
        srs.reset_session()
        question = srs.get_next_question()

        session_attr["state"] = data.STATE_QUIZ
        session_attr["current_question"] = {
            "question_id": question.question_id,
            "question_text_german": question.question_text_german,
            "answer": question.answer,
            "operand1": question.operand1,
            "operand2": question.operand2,
            "operation": question.operation.value,
        }
        session_attr["correct_count"] = 0
        session_attr["questions_asked"] = 1

        speech = (
            data.CONFIRM_GRADE.format(grade=grade_name)
            + " Los geht's! "
            + question.question_text_german
        )
        reprompt = question.question_text_german

        handler_input.response_builder.speak(speech).ask(reprompt)
        return handler_input.response_builder.response
