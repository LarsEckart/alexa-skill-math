"""
Unit tests for the data models.
"""

from datetime import datetime

from alexa.models import QuestionStats, UserProfile


class TestUserProfile:
    """Tests for the UserProfile model."""

    def test_new_profile_defaults(self):
        """New profile should have sensible defaults."""
        profile = UserProfile(user_id="user123")

        assert profile.user_id == "user123"
        assert profile.name is None
        assert profile.grade == 1
        assert profile.total_questions_answered == 0
        assert profile.total_correct == 0
        assert profile.current_streak == 0
        assert profile.best_streak == 0
        assert profile.last_session is None
        assert profile.created_at is not None

    def test_profile_with_all_fields(self):
        """Should accept all fields."""
        now = datetime.now()
        profile = UserProfile(
            user_id="user123",
            name="Max",
            grade=3,
            total_questions_answered=100,
            total_correct=85,
            current_streak=5,
            best_streak=12,
            last_session=now,
            created_at=now,
        )

        assert profile.name == "Max"
        assert profile.grade == 3
        assert profile.total_correct == 85
        assert profile.best_streak == 12

    def test_overall_accuracy_no_questions(self):
        """Accuracy should be 0 with no questions."""
        profile = UserProfile(user_id="user123")

        assert profile.overall_accuracy == 0.0

    def test_overall_accuracy_with_questions(self):
        """Accuracy should be calculated correctly."""
        profile = UserProfile(
            user_id="user123",
            total_questions_answered=100,
            total_correct=75,
        )

        assert profile.overall_accuracy == 0.75

    def test_to_dict(self):
        """Should convert to dictionary correctly."""
        now = datetime.now()
        profile = UserProfile(
            user_id="user123",
            name="Max",
            grade=2,
            total_questions_answered=50,
            total_correct=40,
            current_streak=3,
            best_streak=7,
            last_session=now,
            created_at=now,
        )

        data = profile.to_dict()

        assert data["user_id"] == "user123"
        assert data["name"] == "Max"
        assert data["grade"] == 2
        assert data["total_questions_answered"] == 50
        assert data["total_correct"] == 40
        assert data["current_streak"] == 3
        assert data["best_streak"] == 7
        assert data["last_session"] is not None
        assert data["created_at"] is not None

    def test_from_dict(self):
        """Should create from dictionary correctly."""
        now = datetime.now()
        data = {
            "user_id": "user456",
            "name": "Anna",
            "grade": 4,
            "total_questions_answered": 200,
            "total_correct": 180,
            "current_streak": 10,
            "best_streak": 15,
            "last_session": now.isoformat(),
            "created_at": now.isoformat(),
        }

        profile = UserProfile.from_dict(data)

        assert profile.user_id == "user456"
        assert profile.name == "Anna"
        assert profile.grade == 4
        assert profile.total_questions_answered == 200
        assert profile.best_streak == 15

    def test_from_dict_minimal(self):
        """Should handle minimal dictionary with defaults."""
        data = {"user_id": "user789"}

        profile = UserProfile.from_dict(data)

        assert profile.user_id == "user789"
        assert profile.name is None
        assert profile.grade == 1
        assert profile.total_questions_answered == 0

    def test_round_trip_serialization(self):
        """Should round-trip through dict serialization."""
        now = datetime.now()
        original = UserProfile(
            user_id="user123",
            name="Test",
            grade=3,
            total_questions_answered=50,
            total_correct=45,
            current_streak=8,
            best_streak=12,
            last_session=now,
            created_at=now,
        )

        data = original.to_dict()
        restored = UserProfile.from_dict(data)

        assert restored.user_id == original.user_id
        assert restored.name == original.name
        assert restored.grade == original.grade
        assert restored.total_questions_answered == original.total_questions_answered
        assert restored.total_correct == original.total_correct
        assert restored.current_streak == original.current_streak
        assert restored.best_streak == original.best_streak


class TestQuestionStatsEdgeCases:
    """Additional edge case tests for QuestionStats."""

    def test_from_dict_with_null_last_asked(self):
        """Should handle null last_asked."""
        data = {
            "question_id": "add_5_3",
            "correct_count": 5,
            "incorrect_count": 2,
            "last_asked": None,
            "box": 2,
        }

        stats = QuestionStats.from_dict(data)

        assert stats.last_asked is None

    def test_from_dict_missing_optional_fields(self):
        """Should handle missing optional fields."""
        data = {"question_id": "sub_10_5"}

        stats = QuestionStats.from_dict(data)

        assert stats.question_id == "sub_10_5"
        assert stats.correct_count == 0
        assert stats.incorrect_count == 0
        assert stats.box == 1

    def test_accuracy_perfect_score(self):
        """Should handle 100% accuracy."""
        stats = QuestionStats(
            question_id="add_1_1",
            correct_count=100,
            incorrect_count=0,
        )

        assert stats.accuracy == 1.0

    def test_accuracy_zero_score(self):
        """Should handle 0% accuracy."""
        stats = QuestionStats(
            question_id="div_81_9",
            correct_count=0,
            incorrect_count=10,
        )

        assert stats.accuracy == 0.0
