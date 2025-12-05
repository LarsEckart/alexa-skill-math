"""
Core Math Question Engine for German Primary School Math Quiz.

This module generates dynamic math questions for different grade levels,
with support for addition, subtraction, multiplication, and division.
"""

import random
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum


class Operation(Enum):
    """Supported math operations."""

    ADDITION = "add"
    SUBTRACTION = "sub"
    MULTIPLICATION = "mul"
    DIVISION = "div"


@dataclass
class DifficultyConfig:
    """Configuration for a specific grade level."""

    grade: int
    operations: list[Operation]
    number_range: tuple[int, int]  # (min, max)
    multiplication_tables: list[int] | None = None  # For grades that learn specific tables


# Difficulty configurations per grade level
GRADE_CONFIGS: dict[int, DifficultyConfig] = {
    1: DifficultyConfig(
        grade=1,
        operations=[Operation.ADDITION],
        number_range=(1, 10),
    ),
    2: DifficultyConfig(
        grade=2,
        operations=[Operation.ADDITION, Operation.SUBTRACTION, Operation.MULTIPLICATION],
        number_range=(0, 100),
        multiplication_tables=[2, 5, 10],  # Intro to multiplication
    ),
    3: DifficultyConfig(
        grade=3,
        operations=[
            Operation.ADDITION,
            Operation.SUBTRACTION,
            Operation.MULTIPLICATION,
            Operation.DIVISION,
        ],
        number_range=(0, 100),
        multiplication_tables=list(range(1, 11)),  # Full times tables 1-10
    ),
    4: DifficultyConfig(
        grade=4,
        operations=[
            Operation.ADDITION,
            Operation.SUBTRACTION,
            Operation.MULTIPLICATION,
            Operation.DIVISION,
        ],
        number_range=(0, 1000),
        multiplication_tables=list(range(1, 13)),  # Extended tables 1-12
    ),
}


@dataclass
class MathQuestion:
    """Represents a single math question."""

    question_id: str  # Unique ID for SRS tracking, e.g., "add_7_5"
    operand1: int
    operand2: int
    operation: Operation
    correct_answer: int
    question_text_german: str  # Speech-friendly German text

    def check_answer(self, answer: int) -> bool:
        """Check if the provided answer is correct."""
        return answer == self.correct_answer


# German words for operations (speech-friendly)
OPERATION_WORDS_GERMAN: dict[Operation, str] = {
    Operation.ADDITION: "plus",
    Operation.SUBTRACTION: "minus",
    Operation.MULTIPLICATION: "mal",
    Operation.DIVISION: "geteilt durch",
}


def _number_to_german_speech(num: int) -> str:
    """
    Convert a number to German speech-friendly format.

    For basic numbers, we just return the digit string.
    Alexa handles German number pronunciation well with SSML.
    """
    return str(num)


def generate_question_id(operation: Operation, operand1: int, operand2: int) -> str:
    """Generate a unique question ID for SRS tracking."""
    return f"{operation.value}_{operand1}_{operand2}"


def _generate_addition(config: DifficultyConfig) -> MathQuestion:
    """Generate an addition question within the configured range."""
    min_num = config.number_range[0]
    max_num = config.number_range[1]

    # Generate operands within range, ensuring sum doesn't exceed max
    operand1 = random.randint(min_num, max_num)
    # Ensure operand2 is at least min_num but sum doesn't exceed max
    max_operand2 = max(min_num, max_num - operand1)
    operand2 = random.randint(min_num, max_operand2)

    answer = operand1 + operand2
    operation = Operation.ADDITION

    question_text = (
        f"Was ist {_number_to_german_speech(operand1)} "
        f"{OPERATION_WORDS_GERMAN[operation]} "
        f"{_number_to_german_speech(operand2)}?"
    )

    return MathQuestion(
        question_id=generate_question_id(operation, operand1, operand2),
        operand1=operand1,
        operand2=operand2,
        operation=operation,
        correct_answer=answer,
        question_text_german=question_text,
    )


def _generate_subtraction(config: DifficultyConfig) -> MathQuestion:
    """Generate a subtraction question ensuring no negative results."""
    min_num = config.number_range[0]
    max_num = config.number_range[1]

    # Generate operands such that result is non-negative and both are in range
    operand1 = random.randint(min_num, max_num)
    operand2 = random.randint(min_num, operand1)  # operand2 <= operand1

    answer = operand1 - operand2
    operation = Operation.SUBTRACTION

    question_text = (
        f"Was ist {_number_to_german_speech(operand1)} "
        f"{OPERATION_WORDS_GERMAN[operation]} "
        f"{_number_to_german_speech(operand2)}?"
    )

    return MathQuestion(
        question_id=generate_question_id(operation, operand1, operand2),
        operand1=operand1,
        operand2=operand2,
        operation=operation,
        correct_answer=answer,
        question_text_german=question_text,
    )


def _generate_multiplication(config: DifficultyConfig) -> MathQuestion:
    """Generate a multiplication question using configured times tables."""
    tables = config.multiplication_tables or [2, 5, 10]

    # One operand from the times tables, one from 1-10
    operand1 = random.choice(tables)
    operand2 = random.randint(1, 10)

    # Randomly swap order for variety
    if random.choice([True, False]):
        operand1, operand2 = operand2, operand1

    answer = operand1 * operand2
    operation = Operation.MULTIPLICATION

    question_text = (
        f"Was ist {_number_to_german_speech(operand1)} "
        f"{OPERATION_WORDS_GERMAN[operation]} "
        f"{_number_to_german_speech(operand2)}?"
    )

    return MathQuestion(
        question_id=generate_question_id(operation, operand1, operand2),
        operand1=operand1,
        operand2=operand2,
        operation=operation,
        correct_answer=answer,
        question_text_german=question_text,
    )


def _generate_division(config: DifficultyConfig) -> MathQuestion:
    """Generate a division question with whole number results."""
    tables = config.multiplication_tables or list(range(1, 11))

    # Generate from multiplication facts to ensure clean division
    divisor = random.choice(tables)
    quotient = random.randint(1, 10)
    dividend = divisor * quotient  # This ensures clean division

    operation = Operation.DIVISION

    question_text = (
        f"Was ist {_number_to_german_speech(dividend)} "
        f"{OPERATION_WORDS_GERMAN[operation]} "
        f"{_number_to_german_speech(divisor)}?"
    )

    return MathQuestion(
        question_id=generate_question_id(operation, dividend, divisor),
        operand1=dividend,
        operand2=divisor,
        operation=operation,
        correct_answer=quotient,
        question_text_german=question_text,
    )


# Map operations to their generator functions
_OPERATION_GENERATORS: dict[Operation, Callable[[DifficultyConfig], MathQuestion]] = {
    Operation.ADDITION: _generate_addition,
    Operation.SUBTRACTION: _generate_subtraction,
    Operation.MULTIPLICATION: _generate_multiplication,
    Operation.DIVISION: _generate_division,
}


def generate_question(
    grade: int = 1,
    operation: Operation | None = None,
) -> MathQuestion:
    """
    Generate a random math question for the specified grade level.

    Args:
        grade: The grade level (1-4). Defaults to 1.
        operation: Optional specific operation. If None, randomly selects
                   from operations available for the grade.

    Returns:
        A MathQuestion instance.

    Raises:
        ValueError: If grade is not supported or operation is not available for grade.
    """
    if grade not in GRADE_CONFIGS:
        raise ValueError(
            f"Unsupported grade: {grade}. Supported grades: {list(GRADE_CONFIGS.keys())}"
        )

    config = GRADE_CONFIGS[grade]

    if operation is None:
        operation = random.choice(config.operations)
    elif operation not in config.operations:
        raise ValueError(
            f"Operation {operation.value} is not available for grade {grade}. "
            f"Available operations: {[op.value for op in config.operations]}"
        )

    generator = _OPERATION_GENERATORS[operation]
    return generator(config)


def generate_question_set(
    count: int = 10,
    grade: int = 1,
    operation: Operation | None = None,
) -> list[MathQuestion]:
    """
    Generate a set of math questions.

    Args:
        count: Number of questions to generate.
        grade: The grade level (1-4).
        operation: Optional specific operation to focus on.

    Returns:
        A list of MathQuestion instances.
    """
    return [generate_question(grade=grade, operation=operation) for _ in range(count)]


def get_available_operations(grade: int) -> list[Operation]:
    """Get the list of available operations for a given grade."""
    if grade not in GRADE_CONFIGS:
        raise ValueError(f"Unsupported grade: {grade}")
    return GRADE_CONFIGS[grade].operations.copy()


def get_grade_config(grade: int) -> DifficultyConfig:
    """Get the difficulty configuration for a given grade."""
    if grade not in GRADE_CONFIGS:
        raise ValueError(f"Unsupported grade: {grade}")
    return GRADE_CONFIGS[grade]
