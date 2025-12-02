"""
German Math Quiz Alexa Skill - Lambda Function.

This module implements the Alexa skill handlers for a German primary school
math quiz using spaced repetition for adaptive learning.

Handlers:
- LaunchRequestHandler: Welcome and setup flow
- QuizHandler: Start a new quiz session
- AnswerIntentHandler: Process numeric answers
- SetDifficultyHandler: Adjust difficulty/grade level
- ProgressHandler: Report learning progress
- RepeatHandler: Repeat current question
- HelpHandler: Provide help text
- Exit/Stop/Cancel Handlers: End session gracefully
"""

import json
import logging
import os
import random

from ask_sdk_core.dispatch_components import (
    AbstractExceptionHandler,
    AbstractRequestHandler,
    AbstractRequestInterceptor,
    AbstractResponseInterceptor,
)
from ask_sdk_core.serialize import DefaultSerializer
from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.utils import is_intent_name, is_request_type
from ask_sdk_dynamodb.adapter import DynamoDbAdapter
from ask_sdk_model import Response

from alexa import data
from alexa.persistence import get_persistence_manager
from alexa.srs import SpacedRepetition

# DynamoDB table name for persistence (configurable via environment variable)
DYNAMODB_TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "MathQuizUserData")

# Persistence adapter for storing user data in DynamoDB
persistence_adapter = DynamoDbAdapter(
    table_name=DYNAMODB_TABLE_NAME,
    partition_key_name="id",
    attribute_name="attributes",
    create_table=False,  # Table should be created via infrastructure (WP6)
)

# Skill Builder with persistence adapter
sb = CustomSkillBuilder(persistence_adapter=persistence_adapter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ============================================================================
# Helper Functions
# ============================================================================


def get_srs_from_session(handler_input) -> SpacedRepetition:
    """
    Get or create an SRS instance from session attributes.

    The SRS is stored in session for the duration of the session,
    with question_stats loaded from persistent storage.
    """
    pm = get_persistence_manager(handler_input)
    profile = pm.get_user_profile()

    # Create SRS instance with current question stats
    question_stats = pm.get_question_stats()
    srs = SpacedRepetition(question_stats=question_stats, grade=profile.grade)

    return srs


def save_srs_state(handler_input, srs: SpacedRepetition) -> None:
    """Save SRS question stats to persistent storage."""
    pm = get_persistence_manager(handler_input)
    pm.save_question_stats(srs.question_stats)
    pm.commit()


def get_correct_feedback(answer: int) -> str:
    """Generate positive feedback for a correct answer."""
    template = random.choice(data.CORRECT_ANSWER_TEMPLATES)
    return template.format(answer=answer)


def get_incorrect_feedback(
    operand1: int, operand2: int, operation: str, correct_answer: int
) -> str:
    """Generate feedback for an incorrect answer with the correct solution."""
    template = random.choice(data.WRONG_ANSWER_TEMPLATES)
    operation_word = data.OPERATION_WORDS.get(operation, operation)
    return template.format(
        operand1=operand1,
        operand2=operand2,
        operation=operation_word,
        answer=correct_answer,
    )


def get_quiz_end_message(correct: int, total: int) -> str:
    """Get appropriate end-of-quiz message based on performance."""
    if correct == total:
        return data.QUIZ_END_PERFECT.format(total=total)
    elif correct >= total * 0.8:
        return data.QUIZ_END_GREAT.format(correct=correct, total=total)
    elif correct >= total * 0.5:
        return data.QUIZ_END_GOOD.format(correct=correct, total=total)
    else:
        return data.QUIZ_END_KEEP_PRACTICING.format(correct=correct, total=total)


def serialize_question(question) -> dict:
    """Serialize a MathQuestion to a dictionary for session storage."""
    return {
        "question_id": question.question_id,
        "operand1": question.operand1,
        "operand2": question.operand2,
        "operation": question.operation.value,
        "correct_answer": question.correct_answer,
        "question_text_german": question.question_text_german,
    }


# ============================================================================
# Request Handlers
# ============================================================================


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


class SetDifficultyHandler(AbstractRequestHandler):
    """
    Handler for adjusting difficulty level.

    Responds to requests like "Mach es leichter/schwerer" or
    "Ich bin in der zweiten Klasse".
    """

    def can_handle(self, handler_input):
        return is_intent_name("SetDifficultyIntent")(handler_input) or is_intent_name(
            "SetGradeIntent"
        )(handler_input)

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


# ============================================================================
# Interceptors
# ============================================================================


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


# ============================================================================
# Exception Handler
# ============================================================================


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


# ============================================================================
# Skill Builder Configuration
# ============================================================================

# Add all request handlers to the skill
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(SetupNameHandler())
sb.add_request_handler(SetupGradeHandler())
sb.add_request_handler(QuizHandler())
sb.add_request_handler(AnswerIntentHandler())
sb.add_request_handler(SetDifficultyHandler())
sb.add_request_handler(ProgressHandler())
sb.add_request_handler(RepeatHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(ExitIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(FallbackIntentHandler())

# Add exception handler
sb.add_exception_handler(CatchAllExceptionHandler())

# Add interceptors
sb.add_global_response_interceptor(CacheResponseForRepeatInterceptor())
sb.add_global_request_interceptor(RequestLogger())
sb.add_global_response_interceptor(ResponseLogger())

# Expose the lambda handler
lambda_handler = sb.lambda_handler()
