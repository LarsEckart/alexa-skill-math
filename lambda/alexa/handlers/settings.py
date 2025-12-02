"""Settings handlers for difficulty adjustment."""

import logging

from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.utils import is_intent_name

from alexa import data
from alexa.handlers.helpers import get_srs_from_session, serialize_question
from alexa.persistence import get_persistence_manager

logger = logging.getLogger(__name__)


class SetDifficultyHandler(AbstractRequestHandler):
    """
    Handler for adjusting difficulty level.

    Responds to requests like "Mach es leichter/schwerer" or
    "Ich bin in der zweiten Klasse".
    """

    def can_handle(self, handler_input):
        session_attr = handler_input.attributes_manager.session_attributes
        # Don't handle SetGradeIntent during quiz - it's likely an answer misrecognized
        if is_intent_name("SetGradeIntent")(handler_input):
            return session_attr.get("state") != data.STATE_QUIZ
        return is_intent_name("SetDifficultyIntent")(handler_input)

    def handle(self, handler_input):
        logger.info("In SetDifficultyHandler")

        session_attr = handler_input.attributes_manager.session_attributes
        pm = get_persistence_manager(handler_input)
        profile = pm.get_user_profile()
        current_grade = profile.grade

        # Check for explicit grade or difficulty direction
        slots = handler_input.request_envelope.request.intent.slots

        # Check for grade slot
        grade_slot = slots.get("grade", {}) if slots else {}
        grade_value = grade_slot.value if grade_slot else None

        # Check for difficulty direction slot
        direction_slot = slots.get("direction", {}) if slots else {}
        direction_value = direction_slot.value if direction_slot else None

        new_grade = current_grade

        if grade_value:
            try:
                new_grade = int(grade_value)
                if not 1 <= new_grade <= 4:
                    new_grade = current_grade
            except ValueError:
                pass
        elif direction_value:
            direction_lower = direction_value.lower()
            if direction_lower in ["leichter", "einfacher", "leicht"]:
                new_grade = max(1, current_grade - 1)
            elif direction_lower in ["schwerer", "schwieriger", "schwer"]:
                new_grade = min(4, current_grade + 1)

        if new_grade != current_grade:
            profile.grade = new_grade
            pm.save_user_profile(profile)
            pm.commit()

            grade_name = data.GRADE_NAMES.get(new_grade, str(new_grade))
            speech = data.DIFFICULTY_CHANGED.format(grade=grade_name)
        else:
            if direction_value and direction_value.lower() in ["leichter", "einfacher", "leicht"]:
                speech = data.DIFFICULTY_SAME.format(direction="einfachsten")
            elif direction_value and direction_value.lower() in [
                "schwerer",
                "schwieriger",
                "schwer",
            ]:
                speech = data.DIFFICULTY_SAME.format(direction="schwierigsten")
            else:
                grade_name = data.GRADE_NAMES.get(current_grade, str(current_grade))
                speech = data.DIFFICULTY_CHANGED.format(grade=grade_name)

        # If in quiz, continue with new difficulty
        if session_attr.get("state") == data.STATE_QUIZ:
            srs = get_srs_from_session(handler_input)
            srs.grade = new_grade
            next_question = srs.get_next_question()

            session_attr["current_question"] = serialize_question(next_question)
            speech += " " + data.NEXT_QUESTION + next_question.question_text_german
            reprompt = next_question.question_text_german
        else:
            speech += " " + data.REPROMPT_GENERAL
            reprompt = data.REPROMPT_GENERAL

        handler_input.response_builder.speak(speech).ask(reprompt)
        return handler_input.response_builder.response
