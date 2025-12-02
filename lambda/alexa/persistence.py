"""
Persistence layer for the German Math Quiz Alexa Skill.

This module provides an abstraction over DynamoDB storage using the
ASK SDK persistence adapter. It handles:
- User profiles (name, grade, preferences)
- SRS question statistics (per-question learning data)
- Session statistics (streaks, totals)

Uses a single-table design with the user_id as partition key.
All data for a user is stored in a single DynamoDB item.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from alexa.models import QuestionStats, UserProfile

if TYPE_CHECKING:
    from ask_sdk_core.handler_input import HandlerInput


# Attribute keys in the persistent store
ATTR_USER_PROFILE = "user_profile"
ATTR_QUESTION_STATS = "question_stats"
ATTR_SESSION_STATS = "session_stats"


class PersistenceManager:
    """
    Manages persistence of user data for the Math Quiz skill.

    This class provides a clean interface for loading and saving
    user data, abstracting away the DynamoDB details.
    """

    def __init__(self, handler_input: HandlerInput):
        """
        Initialize the persistence manager.

        Args:
            handler_input: The ASK SDK handler input containing
                          the attributes manager.
        """
        self._handler_input = handler_input
        self._attributes_manager = handler_input.attributes_manager
        self._persistent_attrs: dict | None = None
        self._dirty = False  # Track if we have unsaved changes

    def _get_user_id(self) -> str:
        """Get the unique user ID from the request."""
        return self._handler_input.request_envelope.context.system.user.user_id

    def _load_persistent_attributes(self) -> dict:
        """
        Lazy-load persistent attributes from DynamoDB.

        Returns:
            Dictionary of persistent attributes.
        """
        if self._persistent_attrs is None:
            self._persistent_attrs = self._attributes_manager.persistent_attributes
        return self._persistent_attrs

    def get_user_profile(self) -> UserProfile:
        """
        Load or create the user profile.

        Returns:
            UserProfile for the current user.
        """
        attrs = self._load_persistent_attributes()

        if ATTR_USER_PROFILE in attrs:
            return UserProfile.from_dict(attrs[ATTR_USER_PROFILE])

        # First-time user - create a new profile
        user_id = self._get_user_id()
        return UserProfile(
            user_id=user_id,
            created_at=datetime.now(),
        )

    def save_user_profile(self, profile: UserProfile) -> None:
        """
        Save the user profile to persistent storage.

        Args:
            profile: The UserProfile to save.
        """
        attrs = self._load_persistent_attributes()
        attrs[ATTR_USER_PROFILE] = profile.to_dict()
        self._dirty = True

    def get_question_stats(self) -> dict[str, QuestionStats]:
        """
        Load question statistics for SRS.

        Returns:
            Dictionary mapping question_id to QuestionStats.
        """
        attrs = self._load_persistent_attributes()
        stats_data = attrs.get(ATTR_QUESTION_STATS, {})

        result = {}
        for question_id, data in stats_data.items():
            # Add question_id to data if not present (for backwards compatibility)
            if "question_id" not in data:
                data["question_id"] = question_id
            result[question_id] = QuestionStats.from_dict(data)

        return result

    def save_question_stats(self, stats: dict[str, QuestionStats]) -> None:
        """
        Save question statistics to persistent storage.

        Args:
            stats: Dictionary mapping question_id to QuestionStats.
        """
        attrs = self._load_persistent_attributes()

        # Store as a dictionary keyed by question_id for efficient lookups
        stats_data = {}
        for question_id, question_stats in stats.items():
            stats_data[question_id] = question_stats.to_dict()

        attrs[ATTR_QUESTION_STATS] = stats_data
        self._dirty = True

    def get_session_stats(self) -> dict:
        """
        Load session statistics (totals, streaks).

        Returns:
            Dictionary with session statistics.
        """
        attrs = self._load_persistent_attributes()
        return attrs.get(
            ATTR_SESSION_STATS,
            {
                "total_questions": 0,
                "total_correct": 0,
                "streak_current": 0,
                "streak_best": 0,
                "sessions_count": 0,
                "last_session": None,
            },
        )

    def save_session_stats(self, stats: dict) -> None:
        """
        Save session statistics to persistent storage.

        Args:
            stats: Dictionary with session statistics.
        """
        attrs = self._load_persistent_attributes()
        attrs[ATTR_SESSION_STATS] = stats
        self._dirty = True

    def update_session_stats(
        self,
        questions_answered: int = 0,
        correct_answers: int = 0,
        reset_streak: bool = False,
    ) -> dict:
        """
        Update session statistics with new answers.

        Args:
            questions_answered: Number of questions answered in this update.
            correct_answers: Number of correct answers in this update.
            reset_streak: Whether to reset the current streak (wrong answer).

        Returns:
            Updated session statistics.
        """
        stats = self.get_session_stats()

        stats["total_questions"] = stats.get("total_questions", 0) + questions_answered
        stats["total_correct"] = stats.get("total_correct", 0) + correct_answers

        if reset_streak:
            stats["streak_current"] = 0
        else:
            stats["streak_current"] = stats.get("streak_current", 0) + correct_answers

        # Update best streak if current is higher
        if stats["streak_current"] > stats.get("streak_best", 0):
            stats["streak_best"] = stats["streak_current"]

        stats["last_session"] = datetime.now().isoformat()

        self.save_session_stats(stats)
        return stats

    def increment_session_count(self) -> None:
        """Increment the session count (call at session start)."""
        stats = self.get_session_stats()
        stats["sessions_count"] = stats.get("sessions_count", 0) + 1
        stats["last_session"] = datetime.now().isoformat()
        self.save_session_stats(stats)

    def commit(self) -> None:
        """
        Commit all pending changes to DynamoDB.

        Should be called at the end of request handling to
        persist any changes made during the request.
        """
        if self._dirty and self._persistent_attrs is not None:
            self._attributes_manager.persistent_attributes = self._persistent_attrs
            self._attributes_manager.save_persistent_attributes()
            self._dirty = False

    def is_first_time_user(self) -> bool:
        """
        Check if this is a first-time user.

        Returns:
            True if the user has no stored data.
        """
        attrs = self._load_persistent_attributes()
        return ATTR_USER_PROFILE not in attrs


def get_persistence_manager(handler_input: HandlerInput) -> PersistenceManager:
    """
    Factory function to get a PersistenceManager.

    Args:
        handler_input: The ASK SDK handler input.

    Returns:
        A PersistenceManager instance.
    """
    return PersistenceManager(handler_input)


# Helper functions for common operations


def load_srs_data(handler_input: HandlerInput) -> tuple[dict[str, QuestionStats], int]:
    """
    Load SRS data and grade level for initializing SpacedRepetition.

    Args:
        handler_input: The ASK SDK handler input.

    Returns:
        Tuple of (question_stats dict, grade level).
    """
    pm = get_persistence_manager(handler_input)
    profile = pm.get_user_profile()
    question_stats = pm.get_question_stats()
    return question_stats, profile.grade


def save_srs_data(
    handler_input: HandlerInput,
    question_stats: dict[str, QuestionStats],
    questions_answered: int = 0,
    correct_answers: int = 0,
    had_wrong_answer: bool = False,
) -> None:
    """
    Save SRS data and update session statistics.

    Args:
        handler_input: The ASK SDK handler input.
        question_stats: Updated question statistics from SRS.
        questions_answered: Number of questions answered.
        correct_answers: Number of correct answers.
        had_wrong_answer: Whether any answer was wrong (resets streak).
    """
    pm = get_persistence_manager(handler_input)
    pm.save_question_stats(question_stats)

    if questions_answered > 0:
        pm.update_session_stats(
            questions_answered=questions_answered,
            correct_answers=correct_answers,
            reset_streak=had_wrong_answer,
        )

    pm.commit()
