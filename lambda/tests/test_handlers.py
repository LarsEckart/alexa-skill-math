"""
Tests for the Alexa skill handlers.

These tests verify the behavior of all intent handlers for the
German Math Quiz skill.
"""

from unittest.mock import MagicMock, patch

import pytest

from alexa import data
from alexa.handlers import (
    AnswerIntentHandler,
    ExitIntentHandler,
    FallbackIntentHandler,
    HelpIntentHandler,
    LaunchRequestHandler,
    ProgressHandler,
    QuizHandler,
    RepeatHandler,
    SetDifficultyHandler,
)
from alexa.handlers.helpers import (
    get_correct_feedback,
    get_incorrect_feedback,
    get_quiz_end_message,
    serialize_question,
)
from alexa.math_questions import MathQuestion, Operation
from alexa.models import UserProfile

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_handler_input():
    """Create a mock handler input with all required attributes."""
    handler_input = MagicMock()

    # Session attributes (mutable dict)
    session_attrs = {}
    handler_input.attributes_manager.session_attributes = session_attrs

    # Response builder
    response_builder = MagicMock()
    response_builder.speak.return_value = response_builder
    response_builder.ask.return_value = response_builder
    response_builder.set_should_end_session.return_value = response_builder
    response_builder.response = MagicMock()
    handler_input.response_builder = response_builder

    # Request envelope
    handler_input.request_envelope = MagicMock()
    handler_input.request_envelope.request = MagicMock()
    handler_input.request_envelope.context.system.user.user_id = "test-user-123"

    return handler_input


@pytest.fixture
def mock_persistence_manager():
    """Create a mock persistence manager."""
    pm = MagicMock()
    pm.is_first_time_user.return_value = False
    pm.get_user_profile.return_value = UserProfile(
        user_id="test-user-123",
        name="Max",
        grade=2,
    )
    pm.get_session_stats.return_value = {
        "total_questions": 50,
        "total_correct": 40,
        "streak_current": 5,
        "streak_best": 10,
        "sessions_count": 5,
    }
    pm.get_question_stats.return_value = {}
    return pm


@pytest.fixture
def sample_question():
    """Create a sample math question."""
    return MathQuestion(
        question_id="add_7_5",
        operand1=7,
        operand2=5,
        operation=Operation.ADDITION,
        correct_answer=12,
        question_text_german="Was ist 7 plus 5?",
    )


# ============================================================================
# Test Helper Functions
# ============================================================================


class TestHelperFunctions:
    """Tests for helper functions in alexa.handlers.helpers."""

    def test_get_correct_feedback(self):
        """Test that correct feedback contains the answer or is a positive affirmation."""
        feedback = get_correct_feedback(42)
        feedback_lower = feedback.lower()
        # Should either contain the answer or be a positive affirmation
        positive_words = [
            "42",
            "richtig",
            "super",
            "prima",
            "toll",
            "klasse",
            "spitze",
            "genau",
            "gut",
            "korrekt",
        ]
        assert any(word in feedback_lower for word in positive_words), (
            f"Feedback should contain positive words: {feedback}"
        )

    def test_get_incorrect_feedback(self):
        """Test that incorrect feedback contains the correct answer."""
        feedback = get_incorrect_feedback(7, 5, "add", 12)
        assert "12" in feedback

    def test_get_quiz_end_message_perfect(self):
        """Test quiz end message for perfect score."""
        message = get_quiz_end_message(10, 10)
        assert "perfekt" in message.lower() or "champion" in message.lower()

    def test_get_quiz_end_message_great(self):
        """Test quiz end message for great score (80%+)."""
        message = get_quiz_end_message(8, 10)
        assert "super" in message.lower() or "toll" in message.lower()

    def test_get_quiz_end_message_good(self):
        """Test quiz end message for good score (50%+)."""
        message = get_quiz_end_message(6, 10)
        assert "gut" in message.lower()

    def test_get_quiz_end_message_needs_practice(self):
        """Test quiz end message for low score (<50%)."""
        message = get_quiz_end_message(3, 10)
        assert "übung" in message.lower()

    def test_serialize_question(self, sample_question):
        """Test question serialization for session storage."""
        serialized = serialize_question(sample_question)

        assert serialized["question_id"] == "add_7_5"
        assert serialized["operand1"] == 7
        assert serialized["operand2"] == 5
        assert serialized["operation"] == "add"
        assert serialized["correct_answer"] == 12
        assert serialized["question_text_german"] == "Was ist 7 plus 5?"


# ============================================================================
# Test Launch Request Handler
# ============================================================================


class TestLaunchRequestHandler:
    """Tests for the LaunchRequestHandler."""

    def test_can_handle_launch_request(self, mock_handler_input):
        """Test that handler can handle LaunchRequest."""
        mock_handler_input.request_envelope.request.object_type = "LaunchRequest"

        with patch("alexa.handlers.launch.is_request_type") as mock_is_request:
            mock_is_request.return_value = lambda x: True
            handler = LaunchRequestHandler()
            assert handler.can_handle(mock_handler_input)

    @patch("alexa.handlers.launch.get_persistence_manager")
    def test_handle_first_time_user(self, mock_get_pm, mock_handler_input):
        """Test launch for first-time user starts setup flow."""
        pm = MagicMock()
        pm.is_first_time_user.return_value = True
        mock_get_pm.return_value = pm

        handler = LaunchRequestHandler()
        handler.handle(mock_handler_input)

        # Should ask for name
        speak_call = mock_handler_input.response_builder.speak.call_args
        speech = speak_call[0][0]
        assert "name" in speech.lower() or "heißt" in speech.lower()

        # Session state should be SETUP_NAME
        assert (
            mock_handler_input.attributes_manager.session_attributes["state"]
            == data.STATE_SETUP_NAME
        )

    @patch("alexa.handlers.launch.get_persistence_manager")
    def test_handle_returning_user_with_name(
        self, mock_get_pm, mock_handler_input, mock_persistence_manager
    ):
        """Test launch for returning user with name shows personalized welcome."""
        mock_get_pm.return_value = mock_persistence_manager

        handler = LaunchRequestHandler()
        handler.handle(mock_handler_input)

        speak_call = mock_handler_input.response_builder.speak.call_args
        speech = speak_call[0][0]

        # Should include the user's name
        assert "Max" in speech
        # Should mention stats
        assert "40" in speech and "50" in speech


# ============================================================================
# Test Quiz Handler
# ============================================================================


class TestQuizHandler:
    """Tests for the QuizHandler."""

    def test_can_handle_quiz_intent(self, mock_handler_input):
        """Test that handler can handle QuizIntent."""
        with patch("alexa.handlers.quiz.is_intent_name") as mock_is_intent:
            mock_is_intent.return_value = lambda x: True
            handler = QuizHandler()
            assert handler.can_handle(mock_handler_input)

    @patch("alexa.handlers.quiz.get_srs_from_session")
    @patch("alexa.handlers.quiz.get_persistence_manager")
    def test_handle_starts_quiz(
        self, mock_get_pm, mock_get_srs, mock_handler_input, sample_question
    ):
        """Test that quiz handler initializes quiz state correctly."""
        srs = MagicMock()
        srs.get_next_question.return_value = sample_question
        mock_get_srs.return_value = srs

        handler = QuizHandler()
        handler.handle(mock_handler_input)

        session_attr = mock_handler_input.attributes_manager.session_attributes

        # Check session state
        assert session_attr["state"] == data.STATE_QUIZ
        assert session_attr["questions_asked"] == 1
        assert session_attr["correct_count"] == 0
        assert "current_question" in session_attr

        # Check speech includes question
        speak_call = mock_handler_input.response_builder.speak.call_args
        speech = speak_call[0][0]
        assert "7 plus 5" in speech


# ============================================================================
# Test Answer Intent Handler
# ============================================================================


class TestAnswerIntentHandler:
    """Tests for the AnswerIntentHandler."""

    def test_can_handle_answer_during_quiz(self, mock_handler_input):
        """Test that handler only handles answers during quiz state."""
        mock_handler_input.attributes_manager.session_attributes["state"] = data.STATE_QUIZ

        with patch("alexa.handlers.quiz.is_intent_name") as mock_is_intent:
            mock_is_intent.return_value = lambda x: True
            handler = AnswerIntentHandler()
            assert handler.can_handle(mock_handler_input)

    def test_cannot_handle_answer_outside_quiz(self, mock_handler_input):
        """Test that handler doesn't handle answers outside quiz."""
        mock_handler_input.attributes_manager.session_attributes["state"] = data.STATE_NONE

        with patch("alexa.handlers.quiz.is_intent_name") as mock_is_intent:
            mock_is_intent.return_value = lambda x: True
            handler = AnswerIntentHandler()
            assert not handler.can_handle(mock_handler_input)

    @patch("alexa.handlers.quiz.save_srs_state")
    @patch("alexa.handlers.quiz.get_srs_from_session")
    @patch("alexa.handlers.quiz.get_persistence_manager")
    def test_handle_correct_answer(
        self,
        mock_get_pm,
        mock_get_srs,
        mock_save_srs,
        mock_handler_input,
        mock_persistence_manager,
        sample_question,
    ):
        """Test handling a correct answer."""
        mock_get_pm.return_value = mock_persistence_manager

        srs = MagicMock()
        srs.get_next_question.return_value = sample_question
        srs.question_stats = {}
        mock_get_srs.return_value = srs

        # Setup session state
        session_attr = mock_handler_input.attributes_manager.session_attributes
        session_attr["state"] = data.STATE_QUIZ
        session_attr["current_question"] = {
            "question_id": "add_7_5",
            "operand1": 7,
            "operand2": 5,
            "operation": "add",
            "correct_answer": 12,
            "question_text_german": "Was ist 7 plus 5?",
        }
        session_attr["questions_asked"] = 1
        session_attr["correct_count"] = 0
        session_attr["session_questions"] = ["add_7_5"]

        # Setup slots with correct answer
        mock_handler_input.request_envelope.request.intent.slots = {"number": MagicMock(value="12")}

        handler = AnswerIntentHandler()
        handler.handle(mock_handler_input)

        # Check SRS was updated
        srs.record_answer.assert_called_once_with("add_7_5", True)

        # Check correct count increased
        assert session_attr["correct_count"] == 1

        # Check positive feedback in speech
        speak_call = mock_handler_input.response_builder.speak.call_args
        speech = speak_call[0][0].lower()
        positive_words = ["richtig", "super", "prima", "toll", "genau", "klasse", "spitze", "gut"]
        assert any(word in speech for word in positive_words), (
            f"Expected positive feedback in: {speech}"
        )

    @patch("alexa.handlers.quiz.save_srs_state")
    @patch("alexa.handlers.quiz.get_srs_from_session")
    @patch("alexa.handlers.quiz.get_persistence_manager")
    def test_handle_incorrect_answer(
        self,
        mock_get_pm,
        mock_get_srs,
        mock_save_srs,
        mock_handler_input,
        mock_persistence_manager,
        sample_question,
    ):
        """Test handling an incorrect answer."""
        mock_get_pm.return_value = mock_persistence_manager

        srs = MagicMock()
        srs.get_next_question.return_value = sample_question
        srs.question_stats = {}
        mock_get_srs.return_value = srs

        # Setup session state
        session_attr = mock_handler_input.attributes_manager.session_attributes
        session_attr["state"] = data.STATE_QUIZ
        session_attr["current_question"] = {
            "question_id": "add_7_5",
            "operand1": 7,
            "operand2": 5,
            "operation": "add",
            "correct_answer": 12,
            "question_text_german": "Was ist 7 plus 5?",
        }
        session_attr["questions_asked"] = 1
        session_attr["correct_count"] = 0
        session_attr["session_questions"] = ["add_7_5"]

        # Setup slots with incorrect answer
        mock_handler_input.request_envelope.request.intent.slots = {"number": MagicMock(value="15")}

        handler = AnswerIntentHandler()
        handler.handle(mock_handler_input)

        # Check SRS was updated with incorrect
        srs.record_answer.assert_called_once_with("add_7_5", False)

        # Check correct count did NOT increase
        assert session_attr["correct_count"] == 0

        # Check speech contains the correct answer
        speak_call = mock_handler_input.response_builder.speak.call_args
        speech = speak_call[0][0]
        assert "12" in speech

    @patch("alexa.handlers.quiz.save_srs_state")
    @patch("alexa.handlers.quiz.get_srs_from_session")
    @patch("alexa.handlers.quiz.get_persistence_manager")
    def test_handle_invalid_answer(
        self, mock_get_pm, mock_get_srs, mock_save_srs, mock_handler_input, mock_persistence_manager
    ):
        """Test handling an invalid (non-numeric) answer."""
        mock_get_pm.return_value = mock_persistence_manager

        # Setup session state
        session_attr = mock_handler_input.attributes_manager.session_attributes
        session_attr["state"] = data.STATE_QUIZ
        session_attr["current_question"] = {
            "question_id": "add_7_5",
            "operand1": 7,
            "operand2": 5,
            "operation": "add",
            "correct_answer": 12,
            "question_text_german": "Was ist 7 plus 5?",
        }

        # Setup slots with invalid answer
        mock_handler_input.request_envelope.request.intent.slots = {
            "number": MagicMock(value="banana")
        }

        handler = AnswerIntentHandler()
        handler.handle(mock_handler_input)

        # Check speech asks for valid number
        speak_call = mock_handler_input.response_builder.speak.call_args
        speech = speak_call[0][0].lower()
        assert "zahl" in speech or "verstanden" in speech


# ============================================================================
# Test Progress Handler
# ============================================================================


class TestProgressHandler:
    """Tests for the ProgressHandler."""

    @patch("alexa.handlers.progress.get_srs_from_session")
    @patch("alexa.handlers.progress.get_persistence_manager")
    def test_handle_with_stats(
        self, mock_get_pm, mock_get_srs, mock_handler_input, mock_persistence_manager
    ):
        """Test progress report with existing stats."""
        mock_get_pm.return_value = mock_persistence_manager

        srs = MagicMock()
        srs.get_strong_areas.return_value = ["Plus-Aufgaben"]
        srs.get_weak_areas.return_value = ["Division"]
        mock_get_srs.return_value = srs

        handler = ProgressHandler()
        handler.handle(mock_handler_input)

        speak_call = mock_handler_input.response_builder.speak.call_args
        speech = speak_call[0][0]

        # Should mention total questions
        assert "50" in speech
        # Should mention correct answers
        assert "40" in speech
        # Should mention percentage (80%)
        assert "80" in speech

    @patch("alexa.handlers.progress.get_srs_from_session")
    @patch("alexa.handlers.progress.get_persistence_manager")
    def test_handle_no_data(self, mock_get_pm, mock_get_srs, mock_handler_input):
        """Test progress report with no data."""
        pm = MagicMock()
        pm.get_session_stats.return_value = {
            "total_questions": 0,
            "total_correct": 0,
        }
        mock_get_pm.return_value = pm

        srs = MagicMock()
        srs.get_strong_areas.return_value = []
        srs.get_weak_areas.return_value = []
        mock_get_srs.return_value = srs

        handler = ProgressHandler()
        handler.handle(mock_handler_input)

        speak_call = mock_handler_input.response_builder.speak.call_args
        speech = speak_call[0][0].lower()

        # Should indicate no data
        assert "noch keine" in speech or "quiz starten" in speech.lower()


# ============================================================================
# Test Set Difficulty Handler
# ============================================================================


class TestSetDifficultyHandler:
    """Tests for the SetDifficultyHandler."""

    @patch("alexa.handlers.settings.get_srs_from_session")
    @patch("alexa.handlers.settings.get_persistence_manager")
    def test_set_grade_explicitly(
        self, mock_get_pm, mock_get_srs, mock_handler_input, sample_question
    ):
        """Test setting grade explicitly."""
        pm = MagicMock()
        profile = UserProfile(user_id="test", grade=2)
        pm.get_user_profile.return_value = profile
        mock_get_pm.return_value = pm

        srs = MagicMock()
        srs.get_next_question.return_value = sample_question
        mock_get_srs.return_value = srs

        # Setup slots with grade 3
        mock_handler_input.request_envelope.request.intent.slots = {
            "grade": MagicMock(value="3"),
            "direction": MagicMock(value=None),
        }

        handler = SetDifficultyHandler()
        handler.handle(mock_handler_input)

        # Check grade was updated
        assert profile.grade == 3
        pm.save_user_profile.assert_called()

    @patch("alexa.handlers.settings.get_srs_from_session")
    @patch("alexa.handlers.settings.get_persistence_manager")
    def test_make_easier(self, mock_get_pm, mock_get_srs, mock_handler_input, sample_question):
        """Test making difficulty easier."""
        pm = MagicMock()
        profile = UserProfile(user_id="test", grade=3)
        pm.get_user_profile.return_value = profile
        mock_get_pm.return_value = pm

        srs = MagicMock()
        srs.get_next_question.return_value = sample_question
        mock_get_srs.return_value = srs

        # Setup slots with "leichter"
        mock_handler_input.request_envelope.request.intent.slots = {
            "grade": MagicMock(value=None),
            "direction": MagicMock(value="leichter"),
        }

        handler = SetDifficultyHandler()
        handler.handle(mock_handler_input)

        # Grade should decrease by 1
        assert profile.grade == 2

    @patch("alexa.handlers.settings.get_srs_from_session")
    @patch("alexa.handlers.settings.get_persistence_manager")
    def test_make_harder(self, mock_get_pm, mock_get_srs, mock_handler_input, sample_question):
        """Test making difficulty harder."""
        pm = MagicMock()
        profile = UserProfile(user_id="test", grade=2)
        pm.get_user_profile.return_value = profile
        mock_get_pm.return_value = pm

        srs = MagicMock()
        srs.get_next_question.return_value = sample_question
        mock_get_srs.return_value = srs

        # Setup slots with "schwerer"
        mock_handler_input.request_envelope.request.intent.slots = {
            "grade": MagicMock(value=None),
            "direction": MagicMock(value="schwerer"),
        }

        handler = SetDifficultyHandler()
        handler.handle(mock_handler_input)

        # Grade should increase by 1
        assert profile.grade == 3


# ============================================================================
# Test Help Handler
# ============================================================================


class TestHelpIntentHandler:
    """Tests for the HelpIntentHandler."""

    def test_help_during_quiz(self, mock_handler_input):
        """Test help message during quiz includes question."""
        session_attr = mock_handler_input.attributes_manager.session_attributes
        session_attr["state"] = data.STATE_QUIZ
        session_attr["current_question"] = {
            "question_text_german": "Was ist 7 plus 5?",
        }

        handler = HelpIntentHandler()
        handler.handle(mock_handler_input)

        speak_call = mock_handler_input.response_builder.speak.call_args
        speech = speak_call[0][0]

        # Should include help text
        assert "antwort" in speech.lower() or "zahl" in speech.lower()
        # Should repeat the question
        assert "7 plus 5" in speech

    def test_help_outside_quiz(self, mock_handler_input):
        """Test general help message outside quiz."""
        session_attr = mock_handler_input.attributes_manager.session_attributes
        session_attr["state"] = data.STATE_NONE

        handler = HelpIntentHandler()
        handler.handle(mock_handler_input)

        speak_call = mock_handler_input.response_builder.speak.call_args
        speech = speak_call[0][0].lower()

        # Should mention starting quiz
        assert "quiz" in speech


# ============================================================================
# Test Exit Handler
# ============================================================================


class TestExitIntentHandler:
    """Tests for the ExitIntentHandler."""

    def test_exit_during_quiz_shows_summary(self, mock_handler_input):
        """Test exit during quiz shows progress summary."""
        session_attr = mock_handler_input.attributes_manager.session_attributes
        session_attr["state"] = data.STATE_QUIZ
        session_attr["correct_count"] = 3
        session_attr["questions_asked"] = 5

        handler = ExitIntentHandler()
        handler.handle(mock_handler_input)

        speak_call = mock_handler_input.response_builder.speak.call_args
        speech = speak_call[0][0]

        # Should show correct/total
        assert "3" in speech and "5" in speech

        # Should end session
        mock_handler_input.response_builder.set_should_end_session.assert_called_with(True)

    def test_exit_outside_quiz(self, mock_handler_input):
        """Test normal exit message outside quiz."""
        session_attr = mock_handler_input.attributes_manager.session_attributes
        session_attr["state"] = data.STATE_NONE

        handler = ExitIntentHandler()
        handler.handle(mock_handler_input)

        speak_call = mock_handler_input.response_builder.speak.call_args
        speech = speak_call[0][0].lower()

        # Should say goodbye
        assert "tschüss" in speech or "bis" in speech


# ============================================================================
# Test Repeat Handler
# ============================================================================


class TestRepeatHandler:
    """Tests for the RepeatHandler."""

    def test_repeat_during_quiz(self, mock_handler_input):
        """Test repeat during quiz repeats the question."""
        session_attr = mock_handler_input.attributes_manager.session_attributes
        session_attr["state"] = data.STATE_QUIZ
        session_attr["current_question"] = {
            "question_text_german": "Was ist 7 plus 5?",
        }

        handler = RepeatHandler()
        handler.handle(mock_handler_input)

        speak_call = mock_handler_input.response_builder.speak.call_args
        speech = speak_call[0][0]

        # Should repeat the question
        assert "7 plus 5" in speech


# ============================================================================
# Test Fallback Handler
# ============================================================================


class TestFallbackIntentHandler:
    """Tests for the FallbackIntentHandler."""

    def test_fallback_during_quiz(self, mock_handler_input):
        """Test fallback during quiz repeats question."""
        session_attr = mock_handler_input.attributes_manager.session_attributes
        session_attr["state"] = data.STATE_QUIZ
        session_attr["current_question"] = {
            "question_text_german": "Was ist 7 plus 5?",
        }

        handler = FallbackIntentHandler()
        handler.handle(mock_handler_input)

        speak_call = mock_handler_input.response_builder.speak.call_args
        speech = speak_call[0][0]

        # Should include question
        assert "7 plus 5" in speech

    def test_fallback_outside_quiz(self, mock_handler_input):
        """Test fallback outside quiz gives help."""
        session_attr = mock_handler_input.attributes_manager.session_attributes
        session_attr["state"] = data.STATE_NONE

        handler = FallbackIntentHandler()
        handler.handle(mock_handler_input)

        speak_call = mock_handler_input.response_builder.speak.call_args
        speech = speak_call[0][0].lower()

        # Should mention not understood
        assert "verstanden" in speech or "hilfe" in speech


# ============================================================================
# Test Data Module
# ============================================================================


class TestDataModule:
    """Tests for the data module constants."""

    def test_german_messages_exist(self):
        """Test that all required German messages are defined."""
        assert data.WELCOME_MESSAGE_FIRST_TIME
        assert data.WELCOME_MESSAGE_RETURNING
        assert data.START_QUIZ_MESSAGE
        assert data.EXIT_SKILL_MESSAGE
        assert data.HELP_MESSAGE
        assert data.FALLBACK_MESSAGE

    def test_correct_speechcons_are_german(self):
        """Test that correct speechcons are appropriate German words."""
        german_words = ["Super", "Prima", "Toll", "Klasse", "Wunderbar"]
        for word in german_words:
            assert word in data.CORRECT_SPEECHCONS

    def test_operation_words_are_german(self):
        """Test that operation words are in German."""
        assert data.OPERATION_WORDS["add"] == "plus"
        assert data.OPERATION_WORDS["sub"] == "minus"
        assert data.OPERATION_WORDS["mul"] == "mal"
        assert data.OPERATION_WORDS["div"] == "geteilt durch"

    def test_grade_names_are_german(self):
        """Test that grade names are German ordinals."""
        assert data.GRADE_NAMES[1] == "erste"
        assert data.GRADE_NAMES[2] == "zweite"
        assert data.GRADE_NAMES[3] == "dritte"
        assert data.GRADE_NAMES[4] == "vierte"

    def test_states_are_defined(self):
        """Test that session states are defined."""
        assert data.STATE_NONE == "NONE"
        assert data.STATE_SETUP_NAME == "SETUP_NAME"
        assert data.STATE_SETUP_GRADE == "SETUP_GRADE"
        assert data.STATE_QUIZ == "QUIZ"
