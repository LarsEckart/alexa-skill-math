"""
German Math Quiz Alexa Skill - Lambda Function.

This module configures and exports the Alexa skill lambda handler.
All request handlers are defined in alexa.handlers.
"""

import logging
import os

from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_dynamodb.adapter import DynamoDbAdapter

from alexa.handlers import (
    AnswerIntentHandler,
    ExitIntentHandler,
    FallbackIntentHandler,
    HelpIntentHandler,
    IntentReflectorHandler,
    LaunchRequestHandler,
    NoIntentHandler,
    ProgressHandler,
    QuizHandler,
    RepeatHandler,
    SelectPlayerHandler,
    SessionEndedRequestHandler,
    SetDifficultyHandler,
    SetupGradeHandler,
    YesIntentHandler,
)
from alexa.interceptors import (
    CacheResponseForRepeatInterceptor,
    CatchAllExceptionHandler,
    RequestLogger,
    ResponseLogger,
)

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB table name for persistence (configurable via environment variable)
DYNAMODB_TABLE_NAME = os.environ.get("DYNAMODB_TABLE_NAME", "MathQuizUserData")

# Persistence adapter for storing user data in DynamoDB
persistence_adapter = DynamoDbAdapter(
    table_name=DYNAMODB_TABLE_NAME,
    partition_key_name="id",
    attribute_name="attributes",
    create_table=False,
)

# Skill Builder with persistence adapter
sb = CustomSkillBuilder(persistence_adapter=persistence_adapter)

# Add request handlers (order matters - more specific handlers first)
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(SelectPlayerHandler())
sb.add_request_handler(SetupGradeHandler())
sb.add_request_handler(QuizHandler())
sb.add_request_handler(AnswerIntentHandler())
sb.add_request_handler(SetDifficultyHandler())
sb.add_request_handler(ProgressHandler())
sb.add_request_handler(RepeatHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(YesIntentHandler())
sb.add_request_handler(NoIntentHandler())
sb.add_request_handler(ExitIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(IntentReflectorHandler())  # Must be last - catches any unhandled intents

# Add exception handler
sb.add_exception_handler(CatchAllExceptionHandler())

# Add interceptors
sb.add_global_response_interceptor(CacheResponseForRepeatInterceptor())
sb.add_global_request_interceptor(RequestLogger())
sb.add_global_response_interceptor(ResponseLogger())

# Expose the lambda handler
lambda_handler = sb.lambda_handler()
