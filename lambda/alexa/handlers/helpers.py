"""Helper functions for Alexa skill handlers."""

import random
from typing import TypedDict

from alexa import data
from alexa.math_questions import MathQuestion
from alexa.persistence import get_persistence_manager
from alexa.srs import SpacedRepetition


class SerializedQuestion(TypedDict):
    """Type definition for a serialized MathQuestion stored in session."""

    question_id: str
    operand1: int
    operand2: int
    operation: str
    correct_answer: int
    question_text_german: str


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


def serialize_question(question: MathQuestion) -> SerializedQuestion:
    """Serialize a MathQuestion to a dictionary for session storage."""
    return {
        "question_id": question.question_id,
        "operand1": question.operand1,
        "operand2": question.operand2,
        "operation": question.operation.value,
        "correct_answer": question.correct_answer,
        "question_text_german": question.question_text_german,
    }
