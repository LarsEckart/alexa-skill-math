"""Standard Alexa intent handlers (Help, Exit, Repeat, Fallback, etc.)."""

import json
import logging

from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.serialize import DefaultSerializer
from ask_sdk_core.utils import is_intent_name, is_request_type
from ask_sdk_model import Response

from alexa import data

logger = logging.getLogger(__name__)


class RepeatHandler(AbstractRequestHandler):
    """
    Handler for repeating the current question.

    During a quiz, repeats the current question.
    Outside a quiz, repeats the last response.
    """

    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.RepeatIntent")(handler_input)

    def handle(self, handler_input):
        logger.info("In RepeatHandler")

        session_attr = handler_input.attributes_manager.session_attributes

        if session_attr.get("state") == data.STATE_QUIZ:
            current_q = session_attr.get("current_question", {})
            question_text = current_q.get("question_text_german", "")

            if question_text:
                speech = data.REPEAT_QUESTION.format(question=question_text)
                reprompt = question_text
            else:
                speech = data.ERROR_MESSAGE
                reprompt = data.REPROMPT_GENERAL
        else:
            # Outside quiz, try to use cached response
            if "recent_response" in session_attr:
                cached_response_str = json.dumps(session_attr["recent_response"])
                cached_response = DefaultSerializer().deserialize(cached_response_str, Response)
                return cached_response
            else:
                speech = data.HELP_MESSAGE
                reprompt = data.REPROMPT_GENERAL

        handler_input.response_builder.speak(speech).ask(reprompt)
        return handler_input.response_builder.response


class HelpIntentHandler(AbstractRequestHandler):
    """
    Handler for help intent.

    Provides context-appropriate help messages.
    """

    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        logger.info("In HelpIntentHandler")

        session_attr = handler_input.attributes_manager.session_attributes

        if session_attr.get("state") == data.STATE_QUIZ:
            speech = data.HELP_DURING_QUIZ
            # Repeat current question after help
            current_q = session_attr.get("current_question", {})
            question_text = current_q.get("question_text_german", "")
            if question_text:
                speech += " " + question_text
            reprompt = question_text if question_text else data.REPROMPT_QUIZ
        else:
            speech = data.HELP_MESSAGE
            reprompt = data.REPROMPT_GENERAL

        handler_input.response_builder.speak(speech).ask(reprompt)
        return handler_input.response_builder.response


class ExitIntentHandler(AbstractRequestHandler):
    """
    Handler for Cancel, Stop, and Pause intents.

    Saves progress and provides a friendly goodbye.
    """

    def can_handle(self, handler_input):
        return (
            is_intent_name("AMAZON.CancelIntent")(handler_input)
            or is_intent_name("AMAZON.StopIntent")(handler_input)
            or is_intent_name("AMAZON.PauseIntent")(handler_input)
        )

    def handle(self, handler_input):
        logger.info("In ExitIntentHandler")

        session_attr = handler_input.attributes_manager.session_attributes

        if session_attr.get("state") == data.STATE_QUIZ:
            # Quiz in progress - provide summary
            correct = session_attr.get("correct_count", 0)
            answered = session_attr.get("questions_asked", 0)
            speech = data.EXIT_DURING_QUIZ.format(correct=correct, answered=answered)
        else:
            speech = data.EXIT_SKILL_MESSAGE

        handler_input.response_builder.speak(speech).set_should_end_session(True)
        return handler_input.response_builder.response


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for session end."""

    def can_handle(self, handler_input):
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        logger.info("In SessionEndedRequestHandler")
        logger.info(f"Session ended with reason: {handler_input.request_envelope}")
        return handler_input.response_builder.response


class FallbackIntentHandler(AbstractRequestHandler):
    """
    Handler for fallback intent.

    Triggered when Alexa doesn't understand the user's input.
    """

    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        logger.info("In FallbackIntentHandler")

        session_attr = handler_input.attributes_manager.session_attributes

        if session_attr.get("state") == data.STATE_QUIZ:
            current_q = session_attr.get("current_question", {})
            question_text = current_q.get("question_text_german", "")
            speech = data.FALLBACK_MESSAGE + " " + question_text
            reprompt = question_text if question_text else data.REPROMPT_QUIZ
        else:
            speech = data.FALLBACK_MESSAGE
            reprompt = data.REPROMPT_GENERAL

        handler_input.response_builder.speak(speech).ask(reprompt)
        return handler_input.response_builder.response
