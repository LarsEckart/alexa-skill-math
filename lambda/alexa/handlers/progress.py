"""Progress reporting handler."""

import logging

from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.utils import is_intent_name

from alexa import data
from alexa.handlers.helpers import get_srs_from_session
from alexa.persistence import get_persistence_manager

logger = logging.getLogger(__name__)


class ProgressHandler(AbstractRequestHandler):
    """
    Handler for reporting user's learning progress.

    Responds to "Wie gut bin ich?" with statistics about
    performance, streaks, and strong/weak areas.
    """

    def can_handle(self, handler_input):
        return is_intent_name("ProgressIntent")(handler_input)

    def handle(self, handler_input):
        logger.info("In ProgressHandler")

        pm = get_persistence_manager(handler_input)
        session_stats = pm.get_session_stats()

        total = session_stats.get("total_questions", 0)
        correct = session_stats.get("total_correct", 0)
        best_streak = session_stats.get("streak_best", 0)

        if total == 0:
            speech = data.PROGRESS_NO_DATA
        else:
            percentage = round((correct / total) * 100) if total > 0 else 0

            speech = data.PROGRESS_REPORT.format(
                total=total,
                correct=correct,
                percentage=percentage,
            )

            if best_streak > 0:
                speech += data.PROGRESS_STREAK.format(streak=best_streak)

            # Get strong/weak areas from SRS
            srs = get_srs_from_session(handler_input)

            strong_areas = srs.get_strong_areas()
            if strong_areas:
                areas_text = " und ".join(strong_areas[:2])
                speech += data.PROGRESS_STRONG_AREAS.format(areas=areas_text)

            weak_areas = srs.get_weak_areas()
            if weak_areas:
                areas_text = " und ".join(weak_areas[:2])
                speech += data.PROGRESS_WEAK_AREAS.format(areas=areas_text)

        speech += " " + data.REPROMPT_GENERAL
        handler_input.response_builder.speak(speech).ask(data.REPROMPT_GENERAL)
        return handler_input.response_builder.response
