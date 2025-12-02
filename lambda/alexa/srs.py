"""
Spaced Repetition System (SRS) for the German Math Quiz.

This module implements a Leitner Box algorithm to prioritize questions
based on the learner's performance. Questions that are answered incorrectly
are asked more frequently, while mastered questions appear less often.

Leitner Box System:
- Box 1: Review every session (difficult/new)
- Box 2: Review every 2 sessions
- Box 3: Review every 4 sessions
- Box 4: Review every 8 sessions
- Box 5: Review every 16 sessions (mastered)

On correct answer: Move up one box (max 5)
On incorrect answer: Move back to box 1
"""

import random
from collections import defaultdict
from datetime import datetime

from alexa.math_questions import MathQuestion, Operation, generate_question
from alexa.models import QuestionStats

# Leitner box configuration
MAX_BOX = 5
MIN_BOX = 1

# Probability weights for selecting questions from each box
# Lower boxes (harder questions) have higher selection probability
BOX_WEIGHTS: dict[int, float] = {
    1: 1.0,  # Always eligible
    2: 0.5,  # 50% chance of being selected
    3: 0.25,  # 25% chance
    4: 0.125,  # 12.5% chance
    5: 0.0625,  # 6.25% chance
}

# Percentage of questions that should be new (not seen before)
NEW_QUESTION_RATIO = 0.3


class SpacedRepetition:
    """
    Spaced Repetition System using the Leitner Box algorithm.

    This class manages question selection and tracks learning progress
    for a single user session.
    """

    def __init__(
        self,
        question_stats: dict[str, QuestionStats] | None = None,
        grade: int = 1,
    ):
        """
        Initialize the SRS system.

        Args:
            question_stats: Dictionary mapping question_id to QuestionStats.
                           If None, starts fresh.
            grade: The grade level to generate questions for.
        """
        self._stats: dict[str, QuestionStats] = question_stats or {}
        self._grade = grade
        self._session_asked: set[str] = set()  # Questions asked this session
        self._recent_questions: list[str] = []  # Last N questions to avoid immediate repeats
        self._max_recent = 5  # Don't repeat last 5 questions

    @property
    def grade(self) -> int:
        """Current grade level."""
        return self._grade

    @grade.setter
    def grade(self, value: int) -> None:
        """Set the grade level."""
        self._grade = value

    @property
    def question_stats(self) -> dict[str, QuestionStats]:
        """Get all question statistics (for persistence)."""
        return self._stats.copy()

    def get_next_question(self) -> MathQuestion:
        """
        Select the next question based on SRS algorithm.

        Selection strategy:
        1. Prioritize questions from lower boxes (more difficult)
        2. Mix in new questions periodically
        3. Avoid repeating recent questions

        Returns:
            A MathQuestion selected according to SRS priorities.
        """
        # Decide whether to generate a new question or review
        if self._should_generate_new():
            return self._generate_new_question()

        # Try to select from existing questions using SRS
        selected = self._select_from_srs()
        if selected:
            return selected

        # Fallback: generate a new question
        return self._generate_new_question()

    def _should_generate_new(self) -> bool:
        """Determine if we should generate a new question vs review."""
        if not self._stats:
            return True

        # Count questions available for review (not recently asked)
        available = [q_id for q_id in self._stats if q_id not in self._recent_questions]

        if not available:
            return True

        # Use new question ratio with some randomness
        return random.random() < NEW_QUESTION_RATIO

    def _select_from_srs(self) -> MathQuestion | None:
        """
        Select a question from existing stats using weighted box selection.

        Returns:
            A MathQuestion or None if no suitable question found.
        """
        # Filter out recently asked questions
        available_stats = [
            stats for q_id, stats in self._stats.items() if q_id not in self._recent_questions
        ]

        if not available_stats:
            return None

        # Group by box
        by_box: dict[int, list[QuestionStats]] = defaultdict(list)
        for stats in available_stats:
            by_box[stats.box].append(stats)

        # Select box based on weights (lower boxes preferred)
        selected_stats = self._weighted_box_selection(by_box)

        if not selected_stats:
            return None

        # Reconstruct the question from the ID
        return self._reconstruct_question(selected_stats.question_id)

    def _weighted_box_selection(
        self, by_box: dict[int, list[QuestionStats]]
    ) -> QuestionStats | None:
        """
        Select a question using weighted random selection across boxes.

        Lower boxes have higher probability of being selected.
        """
        candidates: list[tuple[QuestionStats, float]] = []

        for box_num, stats_list in by_box.items():
            weight = BOX_WEIGHTS.get(box_num, 0.1)
            for stats in stats_list:
                # Apply weight and add some time-based priority
                final_weight = weight * self._time_factor(stats)
                candidates.append((stats, final_weight))

        if not candidates:
            return None

        # Weighted random selection
        total_weight = sum(w for _, w in candidates)
        if total_weight == 0:
            return random.choice([s for s, _ in candidates])

        r = random.random() * total_weight
        cumulative = 0.0
        for stats, weight in candidates:
            cumulative += weight
            if r <= cumulative:
                return stats

        return candidates[-1][0]  # Fallback

    def _time_factor(self, stats: QuestionStats) -> float:
        """
        Calculate a time-based priority factor.

        Questions not asked recently get a slight boost.
        """
        if stats.last_asked is None:
            return 1.5  # Boost never-asked questions

        hours_since = (datetime.now() - stats.last_asked).total_seconds() / 3600

        # Logarithmic boost based on hours since last asked
        if hours_since < 1:
            return 0.5  # Recently asked, lower priority
        elif hours_since < 24:
            return 1.0
        else:
            return min(2.0, 1.0 + (hours_since / 168))  # Up to 2x after a week

    def _generate_new_question(self) -> MathQuestion:
        """Generate a new question that hasn't been seen or was seen long ago."""
        max_attempts = 20

        for _ in range(max_attempts):
            question = generate_question(grade=self._grade)

            # Skip if recently asked
            if question.question_id in self._recent_questions:
                continue

            # Prefer truly new questions
            if question.question_id not in self._stats:
                return question

            # Accept questions in higher boxes (well-learned) for review
            stats = self._stats[question.question_id]
            if stats.box >= 3:
                return question

        # Fallback: just return a random question
        return generate_question(grade=self._grade)

    def _reconstruct_question(self, question_id: str) -> MathQuestion | None:
        """
        Reconstruct a MathQuestion from its ID.

        Question ID format: "{operation}_{operand1}_{operand2}"
        e.g., "add_7_5", "mul_6_8"
        """
        try:
            parts = question_id.split("_")
            if len(parts) != 3:
                return None

            op_str, op1_str, op2_str = parts
            operand1 = int(op1_str)
            operand2 = int(op2_str)

            # Map operation string to enum
            op_map = {
                "add": Operation.ADDITION,
                "sub": Operation.SUBTRACTION,
                "mul": Operation.MULTIPLICATION,
                "div": Operation.DIVISION,
            }
            operation = op_map.get(op_str)
            if operation is None:
                return None

            # Calculate the correct answer
            if operation == Operation.ADDITION:
                answer = operand1 + operand2
            elif operation == Operation.SUBTRACTION:
                answer = operand1 - operand2
            elif operation == Operation.MULTIPLICATION:
                answer = operand1 * operand2
            elif operation == Operation.DIVISION:
                answer = operand1 // operand2 if operand2 != 0 else 0
            else:
                return None

            # German operation words
            op_words = {
                Operation.ADDITION: "plus",
                Operation.SUBTRACTION: "minus",
                Operation.MULTIPLICATION: "mal",
                Operation.DIVISION: "geteilt durch",
            }

            question_text = f"Was ist {operand1} {op_words[operation]} {operand2}?"

            return MathQuestion(
                question_id=question_id,
                operand1=operand1,
                operand2=operand2,
                operation=operation,
                correct_answer=answer,
                question_text_german=question_text,
            )
        except (ValueError, IndexError):
            return None

    def record_answer(self, question_id: str, correct: bool) -> None:
        """
        Update SRS data after an answer is given.

        Args:
            question_id: The ID of the question answered.
            correct: Whether the answer was correct.
        """
        # Get or create stats for this question
        if question_id not in self._stats:
            self._stats[question_id] = QuestionStats(question_id=question_id)

        stats = self._stats[question_id]

        # Update counts
        if correct:
            stats.correct_count += 1
            # Move up one box (max 5)
            stats.box = min(MAX_BOX, stats.box + 1)
        else:
            stats.incorrect_count += 1
            # Move back to box 1
            stats.box = MIN_BOX

        stats.last_asked = datetime.now()

        # Track in session and recent questions
        self._session_asked.add(question_id)
        self._recent_questions.append(question_id)
        if len(self._recent_questions) > self._max_recent:
            self._recent_questions.pop(0)

    def get_weak_areas(self) -> list[str]:
        """
        Return operation types the learner struggles with.

        Returns:
            List of operation names (e.g., ["subtraction", "division"])
            sorted by difficulty (most challenging first).
        """
        # Group stats by operation type
        op_stats: dict[str, list[QuestionStats]] = defaultdict(list)

        for question_id, stats in self._stats.items():
            if stats.total_attempts == 0:
                continue

            # Extract operation from question_id
            parts = question_id.split("_")
            if parts:
                op_type = parts[0]
                op_stats[op_type].append(stats)

        # Calculate average accuracy per operation
        op_accuracy: dict[str, float] = {}
        for op_type, stats_list in op_stats.items():
            total_correct = sum(s.correct_count for s in stats_list)
            total_attempts = sum(s.total_attempts for s in stats_list)
            if total_attempts > 0:
                op_accuracy[op_type] = total_correct / total_attempts

        # Map to readable names and filter weak areas (< 70% accuracy)
        op_names = {
            "add": "Addition",
            "sub": "Subtraktion",
            "mul": "Multiplikation",
            "div": "Division",
        }

        weak_areas = [
            op_names.get(op, op)
            for op, accuracy in sorted(op_accuracy.items(), key=lambda x: x[1])
            if accuracy < 0.7
        ]

        return weak_areas

    def get_strong_areas(self) -> list[str]:
        """
        Return operation types the learner is doing well with.

        Returns:
            List of operation names with >= 80% accuracy.
        """
        op_stats: dict[str, list[QuestionStats]] = defaultdict(list)

        for question_id, stats in self._stats.items():
            if stats.total_attempts < 3:  # Need at least 3 attempts
                continue

            parts = question_id.split("_")
            if parts:
                op_type = parts[0]
                op_stats[op_type].append(stats)

        op_accuracy: dict[str, float] = {}
        for op_type, stats_list in op_stats.items():
            total_correct = sum(s.correct_count for s in stats_list)
            total_attempts = sum(s.total_attempts for s in stats_list)
            if total_attempts > 0:
                op_accuracy[op_type] = total_correct / total_attempts

        op_names = {
            "add": "Plus-Aufgaben",
            "sub": "Minus-Aufgaben",
            "mul": "Mal-Aufgaben",
            "div": "Geteilt-Aufgaben",
        }

        strong_areas = [
            op_names.get(op, op)
            for op, accuracy in sorted(op_accuracy.items(), key=lambda x: -x[1])
            if accuracy >= 0.8
        ]

        return strong_areas

    def get_session_stats(self) -> dict:
        """
        Get statistics for the current session.

        Returns:
            Dictionary with session statistics.
        """
        return {
            "questions_asked": len(self._session_asked),
            "unique_questions": len(self._session_asked),
        }

    def reset_session(self) -> None:
        """Reset session-specific tracking (for new session)."""
        self._session_asked.clear()
        self._recent_questions.clear()

    def load_stats(self, stats_data: list[dict]) -> None:
        """
        Load question statistics from persistence.

        Args:
            stats_data: List of QuestionStats dictionaries.
        """
        self._stats.clear()
        for data in stats_data:
            stats = QuestionStats.from_dict(data)
            self._stats[stats.question_id] = stats

    def export_stats(self) -> list[dict]:
        """
        Export question statistics for persistence.

        Returns:
            List of QuestionStats dictionaries.
        """
        return [stats.to_dict() for stats in self._stats.values()]
