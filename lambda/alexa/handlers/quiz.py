"""Quiz handlers for starting quizzes and processing answers."""

import logging

from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.utils import is_intent_name

from alexa import data
from alexa.handlers.helpers import (
    get_correct_feedback,
    get_incorrect_feedback,
    get_quiz_end_message,
    get_srs_from_session,
    save_srs_state,
    serialize_question,
)
from alexa.persistence import get_persistence_manager

logger = logging.getLogger(__name__)


class QuizHandler(AbstractRequestHandler):
    """
    Handler for starting a new quiz session.

    Initializes quiz state and asks the first question using SRS.
    """

    def can_handle(self, handler_input):
        return is_intent_name("QuizIntent")(handler_input) or is_intent_name(
            "AMAZON.StartOverIntent"
        )(handler_input)

    def handle(self, handler_input):
        session_attr = handler_input.attributes_manager.session_attributes
        old_questions_asked = session_attr.get("questions_asked", 0)
        old_state = session_attr.get("state", "NONE")
        logger.info(
            f"QuizHandler: STARTING NEW QUIZ - previous state={old_state}, "
            f"previous questions_asked={old_questions_asked}"
        )
        srs = get_srs_from_session(handler_input)

        # Reset SRS session tracking
        srs.reset_session()

        # Get first question
        question = srs.get_next_question()

        # Initialize session state
        session_attr["state"] = data.STATE_QUIZ
        session_attr["current_question"] = serialize_question(question)
        session_attr["questions_asked"] = 1
        session_attr["correct_count"] = 0
        session_attr["session_questions"] = [question.question_id]

        speech = data.START_QUIZ_MESSAGE + question.question_text_german
        reprompt = question.question_text_german

        handler_input.response_builder.speak(speech).ask(reprompt)
        return handler_input.response_builder.response


class AnswerIntentHandler(AbstractRequestHandler):
    """
    Handler for processing numeric answers during a quiz.

    Validates the answer, provides feedback, updates SRS,
    and serves the next question or ends the quiz.
    """

    def can_handle(self, handler_input):
        session_attr = handler_input.attributes_manager.session_attributes
        return (
            is_intent_name("AnswerIntent")(handler_input)
            and session_attr.get("state") == data.STATE_QUIZ
        )

    def handle(self, handler_input):
        session_attr = handler_input.attributes_manager.session_attributes
        questions_asked = session_attr.get("questions_asked", 0)
        correct_count = session_attr.get("correct_count", 0)
        logger.info(
            f"AnswerIntentHandler: questions_asked={questions_asked}, "
            f"correct_count={correct_count}, MAX_QUESTIONS={data.MAX_QUESTIONS}"
        )

        current_q = session_attr.get("current_question", {})

        # Get the user's answer
        slots = handler_input.request_envelope.request.intent.slots
        answer_slot = slots.get("number", {})
        user_answer = answer_slot.value if answer_slot else None

        # Validate answer
        try:
            user_answer_int = int(user_answer) if user_answer else None
        except ValueError:
            user_answer_int = None

        if user_answer_int is None:
            speech = data.NOT_UNDERSTOOD_DURING_QUIZ
            speech += " " + current_q.get("question_text_german", "")
            reprompt = current_q.get("question_text_german", data.REPROMPT_QUIZ)
            handler_input.response_builder.speak(speech).ask(reprompt)
            return handler_input.response_builder.response

        # Check answer correctness
        correct_answer = current_q.get("correct_answer")
        is_correct = user_answer_int == correct_answer

        # Update SRS
        srs = get_srs_from_session(handler_input)
        question_id = current_q.get("question_id")
        srs.record_answer(question_id, is_correct)
        save_srs_state(handler_input, srs)

        # Update persistence stats
        pm = get_persistence_manager(handler_input)
        pm.update_session_stats(
            questions_answered=1,
            correct_answers=1 if is_correct else 0,
            reset_streak=not is_correct,
        )
        pm.commit()

        # Generate feedback
        if is_correct:
            session_attr["correct_count"] = session_attr.get("correct_count", 0) + 1
            feedback = get_correct_feedback(correct_answer)
        else:
            operation = current_q.get("operation", "")
            feedback = get_incorrect_feedback(
                current_q.get("operand1", 0),
                current_q.get("operand2", 0),
                operation,
                correct_answer,
            )

        # Check if quiz is complete
        questions_asked = session_attr.get("questions_asked", 0)
        logger.info(
            f"Quiz progress check: questions_asked={questions_asked}, "
            f"MAX_QUESTIONS={data.MAX_QUESTIONS}, should_end={questions_asked >= data.MAX_QUESTIONS}"
        )

        if questions_asked >= data.MAX_QUESTIONS:
            # Quiz complete
            correct_count = session_attr.get("correct_count", 0)
            logger.info(f"QUIZ COMPLETE: correct={correct_count}, total={questions_asked}")
            end_message = get_quiz_end_message(correct_count, questions_asked)

            speech = feedback + " " + end_message + " " + data.EXIT_SKILL_MESSAGE
            session_attr["state"] = data.STATE_NONE

            handler_input.response_builder.speak(speech).set_should_end_session(True)
        else:
            # Get next question
            next_question = srs.get_next_question()

            # Avoid immediate repeats
            session_questions = session_attr.get("session_questions", [])
            max_attempts = 10
            attempts = 0
            while next_question.question_id in session_questions and attempts < max_attempts:
                next_question = srs.get_next_question()
                attempts += 1

            session_attr["current_question"] = serialize_question(next_question)
            session_attr["questions_asked"] = questions_asked + 1
            session_questions.append(next_question.question_id)
            session_attr["session_questions"] = session_questions
            logger.info(
                f"Next question: questions_asked now {questions_asked + 1}, "
                f"question_id={next_question.question_id}"
            )

            speech = feedback + " " + data.NEXT_QUESTION + next_question.question_text_german
            reprompt = next_question.question_text_german

            handler_input.response_builder.speak(speech).ask(reprompt)

        return handler_input.response_builder.response
