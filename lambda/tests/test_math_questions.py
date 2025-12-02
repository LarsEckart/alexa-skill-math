"""Unit tests for the math question engine."""

import pytest

from alexa.math_questions import (
    GRADE_CONFIGS,
    DifficultyConfig,
    MathQuestion,
    Operation,
    generate_question,
    generate_question_id,
    generate_question_set,
    get_available_operations,
    get_grade_config,
)


class TestOperation:
    """Tests for Operation enum."""

    def test_operation_values(self):
        """Verify operation enum values for ID generation."""
        assert Operation.ADDITION.value == "add"
        assert Operation.SUBTRACTION.value == "sub"
        assert Operation.MULTIPLICATION.value == "mul"
        assert Operation.DIVISION.value == "div"


class TestQuestionId:
    """Tests for question ID generation."""

    def test_generate_question_id_addition(self):
        """Test question ID format for addition."""
        qid = generate_question_id(Operation.ADDITION, 7, 5)
        assert qid == "add_7_5"

    def test_generate_question_id_subtraction(self):
        """Test question ID format for subtraction."""
        qid = generate_question_id(Operation.SUBTRACTION, 15, 8)
        assert qid == "sub_15_8"

    def test_generate_question_id_multiplication(self):
        """Test question ID format for multiplication."""
        qid = generate_question_id(Operation.MULTIPLICATION, 6, 7)
        assert qid == "mul_6_7"

    def test_generate_question_id_division(self):
        """Test question ID format for division."""
        qid = generate_question_id(Operation.DIVISION, 42, 6)
        assert qid == "div_42_6"


class TestMathQuestion:
    """Tests for MathQuestion dataclass."""

    def test_check_answer_correct(self):
        """Test that correct answers are validated properly."""
        question = MathQuestion(
            question_id="add_5_3",
            operand1=5,
            operand2=3,
            operation=Operation.ADDITION,
            correct_answer=8,
            question_text_german="Was ist 5 plus 3?",
        )
        assert question.check_answer(8) is True

    def test_check_answer_incorrect(self):
        """Test that incorrect answers are rejected."""
        question = MathQuestion(
            question_id="add_5_3",
            operand1=5,
            operand2=3,
            operation=Operation.ADDITION,
            correct_answer=8,
            question_text_german="Was ist 5 plus 3?",
        )
        assert question.check_answer(7) is False
        assert question.check_answer(9) is False


class TestGradeConfigs:
    """Tests for grade level configurations."""

    def test_grade_1_config(self):
        """Test grade 1 configuration."""
        config = GRADE_CONFIGS[1]
        assert config.grade == 1
        assert Operation.ADDITION in config.operations
        assert Operation.SUBTRACTION in config.operations
        assert Operation.MULTIPLICATION not in config.operations
        assert Operation.DIVISION not in config.operations
        assert config.number_range == (0, 20)

    def test_grade_2_config(self):
        """Test grade 2 configuration."""
        config = GRADE_CONFIGS[2]
        assert config.grade == 2
        assert Operation.MULTIPLICATION in config.operations
        assert config.multiplication_tables == [2, 5, 10]
        assert config.number_range == (0, 100)

    def test_grade_3_config(self):
        """Test grade 3 configuration."""
        config = GRADE_CONFIGS[3]
        assert Operation.DIVISION in config.operations
        assert config.multiplication_tables == list(range(1, 11))

    def test_grade_4_config(self):
        """Test grade 4 configuration."""
        config = GRADE_CONFIGS[4]
        assert config.number_range == (0, 1000)
        assert config.multiplication_tables == list(range(1, 13))


class TestGenerateQuestionAddition:
    """Tests for addition question generation."""

    def test_addition_grade_1_in_range(self):
        """Test that grade 1 addition stays within 0-20."""
        for _ in range(100):  # Run multiple times for randomness
            question = generate_question(grade=1, operation=Operation.ADDITION)
            assert 0 <= question.operand1 <= 20
            assert 0 <= question.operand2 <= 20
            assert 0 <= question.correct_answer <= 20
            assert question.operation == Operation.ADDITION

    def test_addition_answer_correct(self):
        """Test that addition answer is computed correctly."""
        for _ in range(50):
            question = generate_question(grade=1, operation=Operation.ADDITION)
            assert question.correct_answer == question.operand1 + question.operand2

    def test_addition_question_text_german(self):
        """Test German question text format."""
        question = generate_question(grade=1, operation=Operation.ADDITION)
        assert "plus" in question.question_text_german
        assert "Was ist" in question.question_text_german
        assert "?" in question.question_text_german


class TestGenerateQuestionSubtraction:
    """Tests for subtraction question generation."""

    def test_subtraction_no_negative_results(self):
        """Test that subtraction never produces negative results."""
        for _ in range(100):
            question = generate_question(grade=1, operation=Operation.SUBTRACTION)
            assert question.correct_answer >= 0
            assert question.operand1 >= question.operand2

    def test_subtraction_answer_correct(self):
        """Test that subtraction answer is computed correctly."""
        for _ in range(50):
            question = generate_question(grade=1, operation=Operation.SUBTRACTION)
            assert question.correct_answer == question.operand1 - question.operand2

    def test_subtraction_question_text_german(self):
        """Test German question text for subtraction."""
        question = generate_question(grade=1, operation=Operation.SUBTRACTION)
        assert "minus" in question.question_text_german


class TestGenerateQuestionMultiplication:
    """Tests for multiplication question generation."""

    def test_multiplication_uses_times_tables(self):
        """Test that multiplication uses configured times tables."""
        for _ in range(50):
            question = generate_question(grade=2, operation=Operation.MULTIPLICATION)
            # At least one operand should be from [2, 5, 10]
            tables = [2, 5, 10]
            assert question.operand1 in tables or question.operand2 in tables

    def test_multiplication_answer_correct(self):
        """Test that multiplication answer is computed correctly."""
        for _ in range(50):
            question = generate_question(grade=3, operation=Operation.MULTIPLICATION)
            assert question.correct_answer == question.operand1 * question.operand2

    def test_multiplication_question_text_german(self):
        """Test German question text for multiplication."""
        question = generate_question(grade=2, operation=Operation.MULTIPLICATION)
        assert "mal" in question.question_text_german


class TestGenerateQuestionDivision:
    """Tests for division question generation."""

    def test_division_whole_number_results(self):
        """Test that division always produces whole numbers."""
        for _ in range(50):
            question = generate_question(grade=3, operation=Operation.DIVISION)
            assert question.correct_answer == question.operand1 // question.operand2
            assert question.operand1 % question.operand2 == 0  # Clean division

    def test_division_no_divide_by_zero(self):
        """Test that division never divides by zero."""
        for _ in range(100):
            question = generate_question(grade=3, operation=Operation.DIVISION)
            assert question.operand2 != 0

    def test_division_question_text_german(self):
        """Test German question text for division."""
        question = generate_question(grade=3, operation=Operation.DIVISION)
        assert "geteilt durch" in question.question_text_german


class TestGenerateQuestionValidation:
    """Tests for input validation."""

    def test_invalid_grade_raises_error(self):
        """Test that invalid grade raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported grade"):
            generate_question(grade=5)

    def test_invalid_operation_for_grade_raises_error(self):
        """Test that operation not available for grade raises error."""
        with pytest.raises(ValueError, match="not available for grade"):
            generate_question(grade=1, operation=Operation.MULTIPLICATION)

    def test_random_operation_selection(self):
        """Test that random operation selection works."""
        operations_seen = set()
        for _ in range(50):
            question = generate_question(grade=3)  # Has all 4 operations
            operations_seen.add(question.operation)
        
        # Should see multiple different operations
        assert len(operations_seen) >= 2


class TestGenerateQuestionSet:
    """Tests for question set generation."""

    def test_generate_correct_count(self):
        """Test that correct number of questions are generated."""
        questions = generate_question_set(count=10, grade=1)
        assert len(questions) == 10

    def test_generate_with_specific_operation(self):
        """Test generation with specific operation."""
        questions = generate_question_set(count=5, grade=1, operation=Operation.ADDITION)
        for q in questions:
            assert q.operation == Operation.ADDITION

    def test_default_count(self):
        """Test default count is 10."""
        questions = generate_question_set(grade=1)
        assert len(questions) == 10


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_available_operations(self):
        """Test getting available operations for grade."""
        ops = get_available_operations(1)
        assert ops == [Operation.ADDITION, Operation.SUBTRACTION]

    def test_get_available_operations_invalid_grade(self):
        """Test error for invalid grade."""
        with pytest.raises(ValueError):
            get_available_operations(99)

    def test_get_grade_config(self):
        """Test getting grade configuration."""
        config = get_grade_config(2)
        assert isinstance(config, DifficultyConfig)
        assert config.grade == 2

    def test_get_grade_config_invalid_grade(self):
        """Test error for invalid grade."""
        with pytest.raises(ValueError):
            get_grade_config(99)


class TestQuestionUniqueIds:
    """Tests for question ID uniqueness and format."""

    def test_question_id_format(self):
        """Test that question IDs follow the expected format."""
        question = generate_question(grade=1)
        parts = question.question_id.split("_")
        assert len(parts) == 3
        assert parts[0] in ["add", "sub", "mul", "div"]
        assert parts[1].isdigit()
        assert parts[2].isdigit()

    def test_question_id_matches_operands(self):
        """Test that question ID contains the actual operands."""
        for _ in range(20):
            question = generate_question(grade=1)
            expected_id = f"{question.operation.value}_{question.operand1}_{question.operand2}"
            assert question.question_id == expected_id
