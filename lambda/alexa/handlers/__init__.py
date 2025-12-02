"""Alexa skill request handlers."""

from alexa.handlers.launch import LaunchRequestHandler
from alexa.handlers.progress import ProgressHandler
from alexa.handlers.quiz import AnswerIntentHandler, QuizHandler
from alexa.handlers.settings import SetDifficultyHandler
from alexa.handlers.setup import SetupGradeHandler, SetupNameHandler
from alexa.handlers.standard import (
    ExitIntentHandler,
    FallbackIntentHandler,
    HelpIntentHandler,
    RepeatHandler,
    SessionEndedRequestHandler,
)

__all__ = [
    "LaunchRequestHandler",
    "SetupNameHandler",
    "SetupGradeHandler",
    "QuizHandler",
    "AnswerIntentHandler",
    "SetDifficultyHandler",
    "ProgressHandler",
    "RepeatHandler",
    "HelpIntentHandler",
    "ExitIntentHandler",
    "SessionEndedRequestHandler",
    "FallbackIntentHandler",
]
