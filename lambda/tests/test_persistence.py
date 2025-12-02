"""
Tests for the persistence module.

These tests use testcontainers with LocalStack to test against
a real DynamoDB instance running in a container.
"""

import boto3
import pytest
from testcontainers.localstack import LocalStackContainer

from alexa.models import QuestionStats, UserProfile
from alexa.persistence import (
    ATTR_QUESTION_STATS,
    ATTR_SESSION_STATS,
    ATTR_USER_PROFILE,
    PersistenceManager,
    get_persistence_manager,
    load_srs_data,
    save_srs_data,
)

# DynamoDB table configuration
TABLE_NAME = "MathQuizUserData"
PARTITION_KEY = "id"


@pytest.fixture(scope="module")
def localstack_container():
    """Start a LocalStack container for the test module."""
    with LocalStackContainer(image="localstack/localstack:3.0") as container:
        yield container


@pytest.fixture(scope="module")
def dynamodb_resource(localstack_container):
    """Create a DynamoDB resource connected to LocalStack."""
    endpoint_url = localstack_container.get_url()

    dynamodb = boto3.resource(
        "dynamodb",
        endpoint_url=endpoint_url,
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )

    # Create the table
    dynamodb.create_table(
        TableName=TABLE_NAME,
        KeySchema=[
            {"AttributeName": PARTITION_KEY, "KeyType": "HASH"},
        ],
        AttributeDefinitions=[
            {"AttributeName": PARTITION_KEY, "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # Wait for table to be active
    table = dynamodb.Table(TABLE_NAME)
    table.wait_until_exists()

    yield dynamodb


@pytest.fixture
def dynamodb_table(dynamodb_resource):
    """Get the DynamoDB table and clean it before each test."""
    table = dynamodb_resource.Table(TABLE_NAME)

    # Clean up all items before each test
    scan = table.scan()
    with table.batch_writer() as batch:
        for item in scan.get("Items", []):
            batch.delete_item(Key={PARTITION_KEY: item[PARTITION_KEY]})

    return table


class FakeAttributesManager:
    """
    A fake AttributesManager that uses real DynamoDB.

    This mimics the ASK SDK's AttributesManager interface but
    connects to our LocalStack DynamoDB.
    """

    def __init__(self, table, user_id: str):
        self._table = table
        self._user_id = user_id
        self._persistent_attributes: dict | None = None

    @property
    def persistent_attributes(self) -> dict:
        """Load persistent attributes from DynamoDB."""
        if self._persistent_attributes is None:
            response = self._table.get_item(Key={PARTITION_KEY: self._user_id})
            item = response.get("Item", {})
            # Remove the partition key from attributes
            self._persistent_attributes = {k: v for k, v in item.items() if k != PARTITION_KEY}
        return self._persistent_attributes

    @persistent_attributes.setter
    def persistent_attributes(self, value: dict) -> None:
        """Set persistent attributes (doesn't save until save is called)."""
        self._persistent_attributes = value

    def save_persistent_attributes(self) -> None:
        """Save persistent attributes to DynamoDB."""
        if self._persistent_attributes is not None:
            item = {PARTITION_KEY: self._user_id, **self._persistent_attributes}
            self._table.put_item(Item=item)


class FakeHandlerInput:
    """
    A fake HandlerInput that uses real DynamoDB.

    This mimics the ASK SDK's HandlerInput interface.
    """

    def __init__(self, table, user_id: str):
        self.attributes_manager = FakeAttributesManager(table, user_id)
        self.request_envelope = FakeRequestEnvelope(user_id)


class FakeRequestEnvelope:
    """Fake request envelope with user context."""

    def __init__(self, user_id: str):
        self.context = FakeContext(user_id)


class FakeContext:
    """Fake context with system info."""

    def __init__(self, user_id: str):
        self.system = FakeSystem(user_id)


class FakeSystem:
    """Fake system with user info."""

    def __init__(self, user_id: str):
        self.user = FakeUser(user_id)


class FakeUser:
    """Fake user with user_id."""

    def __init__(self, user_id: str):
        self.user_id = user_id


@pytest.fixture
def handler_input(dynamodb_table):
    """Create a fake handler input for a new user."""
    return FakeHandlerInput(dynamodb_table, "test-user-123")


@pytest.fixture
def handler_input_with_data(dynamodb_table):
    """Create a fake handler input with existing user data."""
    user_id = "test-user-456"

    # Pre-populate the table with user data
    dynamodb_table.put_item(
        Item={
            PARTITION_KEY: user_id,
            ATTR_USER_PROFILE: {
                "user_id": user_id,
                "name": "Emma",
                "grade": 2,
                "total_questions_answered": 50,
                "total_correct": 40,
                "current_streak": 5,
                "best_streak": 10,
                "last_session": "2025-12-01T10:00:00",
                "created_at": "2025-11-01T08:00:00",
            },
            ATTR_QUESTION_STATS: {
                "add_7_5": {
                    "question_id": "add_7_5",
                    "correct_count": 5,
                    "incorrect_count": 2,
                    "last_asked": "2025-12-01T10:00:00",
                    "box": 3,
                },
                "sub_10_4": {
                    "question_id": "sub_10_4",
                    "correct_count": 3,
                    "incorrect_count": 0,
                    "last_asked": "2025-12-01T09:30:00",
                    "box": 4,
                },
            },
            ATTR_SESSION_STATS: {
                "total_questions": 50,
                "total_correct": 40,
                "streak_current": 5,
                "streak_best": 10,
                "sessions_count": 15,
                "last_session": "2025-12-01T10:00:00",
            },
        }
    )

    return FakeHandlerInput(dynamodb_table, user_id)


class TestPersistenceManagerNewUser:
    """Tests for first-time users with no stored data."""

    def test_is_first_time_user_returns_true(self, handler_input):
        """First-time users should be detected correctly."""
        pm = PersistenceManager(handler_input)
        assert pm.is_first_time_user() is True

    def test_get_user_profile_creates_new_profile(self, handler_input):
        """Getting profile for new user creates a default profile."""
        pm = PersistenceManager(handler_input)
        profile = pm.get_user_profile()

        assert profile.user_id == "test-user-123"
        assert profile.name is None
        assert profile.grade == 1  # Default grade
        assert profile.total_questions_answered == 0
        assert profile.current_streak == 0

    def test_get_question_stats_returns_empty_dict(self, handler_input):
        """New users have no question statistics."""
        pm = PersistenceManager(handler_input)
        stats = pm.get_question_stats()

        assert stats == {}

    def test_get_session_stats_returns_defaults(self, handler_input):
        """New users get default session statistics."""
        pm = PersistenceManager(handler_input)
        stats = pm.get_session_stats()

        assert stats["total_questions"] == 0
        assert stats["total_correct"] == 0
        assert stats["streak_current"] == 0
        assert stats["streak_best"] == 0
        assert stats["sessions_count"] == 0


class TestPersistenceManagerExistingUser:
    """Tests for users with existing stored data."""

    def test_is_first_time_user_returns_false(self, handler_input_with_data):
        """Existing users should not be detected as first-time."""
        pm = PersistenceManager(handler_input_with_data)
        assert pm.is_first_time_user() is False

    def test_get_user_profile_loads_existing_data(self, handler_input_with_data):
        """Loading profile for existing user returns stored data."""
        pm = PersistenceManager(handler_input_with_data)
        profile = pm.get_user_profile()

        assert profile.user_id == "test-user-456"
        assert profile.name == "Emma"
        assert profile.grade == 2
        assert profile.total_questions_answered == 50
        assert profile.total_correct == 40
        assert profile.current_streak == 5
        assert profile.best_streak == 10

    def test_get_question_stats_loads_existing_data(self, handler_input_with_data):
        """Loading question stats returns stored data."""
        pm = PersistenceManager(handler_input_with_data)
        stats = pm.get_question_stats()

        assert len(stats) == 2
        assert "add_7_5" in stats
        assert "sub_10_4" in stats

        add_stats = stats["add_7_5"]
        assert add_stats.correct_count == 5
        assert add_stats.incorrect_count == 2
        assert add_stats.box == 3

    def test_get_session_stats_loads_existing_data(self, handler_input_with_data):
        """Loading session stats returns stored data."""
        pm = PersistenceManager(handler_input_with_data)
        stats = pm.get_session_stats()

        assert stats["total_questions"] == 50
        assert stats["total_correct"] == 40
        assert stats["streak_current"] == 5
        assert stats["streak_best"] == 10
        assert stats["sessions_count"] == 15


class TestPersistenceManagerSaving:
    """Tests for saving data."""

    def test_save_user_profile_persists_to_dynamodb(self, handler_input, dynamodb_table):
        """Saving a user profile stores it in DynamoDB."""
        pm = PersistenceManager(handler_input)

        profile = UserProfile(
            user_id="test-user-123",
            name="Max",
            grade=3,
        )
        pm.save_user_profile(profile)
        pm.commit()

        # Verify data is in DynamoDB
        response = dynamodb_table.get_item(Key={PARTITION_KEY: "test-user-123"})
        item = response.get("Item", {})

        assert ATTR_USER_PROFILE in item
        assert item[ATTR_USER_PROFILE]["name"] == "Max"
        assert item[ATTR_USER_PROFILE]["grade"] == 3

    def test_save_question_stats_persists_to_dynamodb(self, handler_input, dynamodb_table):
        """Saving question stats stores them in DynamoDB."""
        pm = PersistenceManager(handler_input)

        stats = {
            "add_3_2": QuestionStats(
                question_id="add_3_2",
                correct_count=10,
                incorrect_count=1,
                box=4,
            ),
        }
        pm.save_question_stats(stats)
        pm.commit()

        # Verify data is in DynamoDB
        response = dynamodb_table.get_item(Key={PARTITION_KEY: "test-user-123"})
        item = response.get("Item", {})

        assert ATTR_QUESTION_STATS in item
        assert "add_3_2" in item[ATTR_QUESTION_STATS]
        assert item[ATTR_QUESTION_STATS]["add_3_2"]["correct_count"] == 10

    def test_commit_not_called_if_no_changes(self, handler_input, dynamodb_table):
        """Commit without changes should not create an item."""
        pm = PersistenceManager(handler_input)
        pm.commit()

        # Should not have created an item
        response = dynamodb_table.get_item(Key={PARTITION_KEY: "test-user-123"})
        assert "Item" not in response

    def test_data_persists_across_sessions(self, dynamodb_table):
        """Data saved in one session should be available in another."""
        user_id = "test-user-persist"

        # Session 1: Save data
        handler1 = FakeHandlerInput(dynamodb_table, user_id)
        pm1 = PersistenceManager(handler1)

        profile = UserProfile(user_id=user_id, name="Lisa", grade=2)
        pm1.save_user_profile(profile)
        pm1.save_question_stats(
            {"mul_4_5": QuestionStats(question_id="mul_4_5", correct_count=3, box=2)}
        )
        pm1.commit()

        # Session 2: Load data (new handler, simulating new Lambda invocation)
        handler2 = FakeHandlerInput(dynamodb_table, user_id)
        pm2 = PersistenceManager(handler2)

        loaded_profile = pm2.get_user_profile()
        loaded_stats = pm2.get_question_stats()

        assert loaded_profile.name == "Lisa"
        assert loaded_profile.grade == 2
        assert "mul_4_5" in loaded_stats
        assert loaded_stats["mul_4_5"].correct_count == 3


class TestUpdateSessionStats:
    """Tests for updating session statistics."""

    def test_update_session_stats_increments_totals(self, handler_input):
        """Updating session stats increments question and correct totals."""
        pm = PersistenceManager(handler_input)

        stats = pm.update_session_stats(questions_answered=5, correct_answers=4)

        assert stats["total_questions"] == 5
        assert stats["total_correct"] == 4

    def test_update_session_stats_updates_streak(self, handler_input):
        """Correct answers should update the current streak."""
        pm = PersistenceManager(handler_input)

        # First batch of correct answers
        pm.update_session_stats(questions_answered=3, correct_answers=3)
        stats = pm.update_session_stats(questions_answered=2, correct_answers=2)

        assert stats["streak_current"] == 5
        assert stats["streak_best"] == 5

    def test_update_session_stats_resets_streak_on_wrong(self, handler_input):
        """Wrong answer should reset the current streak."""
        pm = PersistenceManager(handler_input)

        # Build up a streak
        pm.update_session_stats(questions_answered=5, correct_answers=5)

        # Wrong answer resets streak
        stats = pm.update_session_stats(questions_answered=1, correct_answers=0, reset_streak=True)

        assert stats["streak_current"] == 0
        assert stats["streak_best"] == 5  # Best streak preserved

    def test_update_session_stats_preserves_best_streak(self, handler_input):
        """Best streak should be preserved even after reset."""
        pm = PersistenceManager(handler_input)

        # Build up a streak
        pm.update_session_stats(questions_answered=10, correct_answers=10)

        # Reset and build new streak
        pm.update_session_stats(questions_answered=1, correct_answers=0, reset_streak=True)
        stats = pm.update_session_stats(questions_answered=3, correct_answers=3)

        assert stats["streak_current"] == 3
        assert stats["streak_best"] == 10

    def test_increment_session_count(self, handler_input):
        """Session count should increment."""
        pm = PersistenceManager(handler_input)

        pm.increment_session_count()
        pm.increment_session_count()
        stats = pm.get_session_stats()

        assert stats["sessions_count"] == 2

    def test_session_stats_persist_to_dynamodb(self, handler_input, dynamodb_table):
        """Session stats should be persisted to DynamoDB."""
        pm = PersistenceManager(handler_input)

        pm.update_session_stats(questions_answered=10, correct_answers=8)
        pm.commit()

        # Verify in DynamoDB
        response = dynamodb_table.get_item(Key={PARTITION_KEY: "test-user-123"})
        item = response.get("Item", {})

        assert ATTR_SESSION_STATS in item
        assert item[ATTR_SESSION_STATS]["total_questions"] == 10
        assert item[ATTR_SESSION_STATS]["total_correct"] == 8


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_persistence_manager(self, handler_input):
        """Factory function should return a PersistenceManager."""
        pm = get_persistence_manager(handler_input)
        assert isinstance(pm, PersistenceManager)

    def test_load_srs_data_new_user(self, handler_input):
        """Loading SRS data for new user returns empty stats and default grade."""
        question_stats, grade = load_srs_data(handler_input)

        assert question_stats == {}
        assert grade == 1  # Default grade

    def test_load_srs_data_existing_user(self, handler_input_with_data):
        """Loading SRS data for existing user returns stored data."""
        question_stats, grade = load_srs_data(handler_input_with_data)

        assert len(question_stats) == 2
        assert grade == 2

    def test_save_srs_data_persists(self, handler_input, dynamodb_table):
        """Saving SRS data should persist to DynamoDB."""
        stats = {
            "mul_6_7": QuestionStats(
                question_id="mul_6_7",
                correct_count=1,
                box=2,
            ),
        }

        save_srs_data(
            handler_input,
            question_stats=stats,
            questions_answered=1,
            correct_answers=1,
            had_wrong_answer=False,
        )

        # Verify in DynamoDB
        response = dynamodb_table.get_item(Key={PARTITION_KEY: "test-user-123"})
        item = response.get("Item", {})

        assert ATTR_QUESTION_STATS in item
        assert "mul_6_7" in item[ATTR_QUESTION_STATS]


class TestBackwardsCompatibility:
    """Tests for backwards compatibility with older data formats."""

    def test_question_stats_without_question_id_field(self, dynamodb_table):
        """Should handle older format where question_id wasn't stored in the dict."""
        user_id = "test-user-compat"

        # Insert data without question_id in the dict (older format)
        dynamodb_table.put_item(
            Item={
                PARTITION_KEY: user_id,
                ATTR_QUESTION_STATS: {
                    "add_5_3": {
                        "correct_count": 3,
                        "incorrect_count": 1,
                        "box": 2,
                        # Note: no "question_id" field
                    },
                },
            }
        )

        handler = FakeHandlerInput(dynamodb_table, user_id)
        pm = PersistenceManager(handler)
        stats = pm.get_question_stats()

        # Should still work and have the question_id
        assert "add_5_3" in stats
        assert stats["add_5_3"].question_id == "add_5_3"


class TestConcurrentUpdates:
    """Tests for handling multiple updates in a session."""

    def test_multiple_question_stats_updates(self, handler_input, dynamodb_table):
        """Multiple question stats can be updated and saved together."""
        pm = PersistenceManager(handler_input)

        # Update stats for multiple questions
        stats = {
            "add_1_1": QuestionStats(question_id="add_1_1", correct_count=1, box=2),
            "add_2_2": QuestionStats(question_id="add_2_2", correct_count=2, box=3),
            "sub_5_3": QuestionStats(
                question_id="sub_5_3", correct_count=0, incorrect_count=1, box=1
            ),
        }
        pm.save_question_stats(stats)
        pm.commit()

        # Verify all are saved
        response = dynamodb_table.get_item(Key={PARTITION_KEY: "test-user-123"})
        item = response.get("Item", {})

        saved_stats = item[ATTR_QUESTION_STATS]
        assert len(saved_stats) == 3
        assert saved_stats["add_1_1"]["box"] == 2
        assert saved_stats["add_2_2"]["box"] == 3
        assert saved_stats["sub_5_3"]["incorrect_count"] == 1

    def test_profile_and_stats_saved_together(self, handler_input, dynamodb_table):
        """Profile and question stats can be saved in one commit."""
        pm = PersistenceManager(handler_input)

        profile = UserProfile(user_id="test-user-123", name="Test", grade=2)
        pm.save_user_profile(profile)

        stats = {"add_1_2": QuestionStats(question_id="add_1_2", correct_count=5, box=4)}
        pm.save_question_stats(stats)

        pm.update_session_stats(questions_answered=5, correct_answers=5)
        pm.commit()

        # Verify all data is saved in one item
        response = dynamodb_table.get_item(Key={PARTITION_KEY: "test-user-123"})
        item = response.get("Item", {})

        assert item[ATTR_USER_PROFILE]["name"] == "Test"
        assert "add_1_2" in item[ATTR_QUESTION_STATS]
        assert item[ATTR_SESSION_STATS]["total_questions"] == 5
