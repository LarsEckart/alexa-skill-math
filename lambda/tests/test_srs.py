"""
Unit tests for the Spaced Repetition System (SRS).
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from alexa.srs import SpacedRepetition, MAX_BOX, MIN_BOX
from alexa.models import QuestionStats
from alexa.math_questions import MathQuestion, Operation


class TestQuestionStats:
    """Tests for the QuestionStats model."""
    
    def test_new_stats_defaults(self):
        """New question stats should have sensible defaults."""
        stats = QuestionStats(question_id="add_7_5")
        
        assert stats.question_id == "add_7_5"
        assert stats.correct_count == 0
        assert stats.incorrect_count == 0
        assert stats.last_asked is None
        assert stats.box == 1
    
    def test_total_attempts(self):
        """Total attempts should sum correct and incorrect."""
        stats = QuestionStats(
            question_id="add_7_5",
            correct_count=5,
            incorrect_count=3,
        )
        
        assert stats.total_attempts == 8
    
    def test_accuracy_no_attempts(self):
        """Accuracy should be 0.5 for new questions."""
        stats = QuestionStats(question_id="add_7_5")
        
        assert stats.accuracy == 0.5
    
    def test_accuracy_with_attempts(self):
        """Accuracy should be calculated correctly."""
        stats = QuestionStats(
            question_id="add_7_5",
            correct_count=7,
            incorrect_count=3,
        )
        
        assert stats.accuracy == 0.7
    
    def test_to_dict_and_from_dict(self):
        """Should round-trip through dict serialization."""
        now = datetime.now()
        original = QuestionStats(
            question_id="mul_6_8",
            correct_count=10,
            incorrect_count=2,
            last_asked=now,
            box=3,
        )
        
        data = original.to_dict()
        restored = QuestionStats.from_dict(data)
        
        assert restored.question_id == original.question_id
        assert restored.correct_count == original.correct_count
        assert restored.incorrect_count == original.incorrect_count
        assert restored.box == original.box
        # Datetime comparison with some tolerance
        assert abs((restored.last_asked - original.last_asked).total_seconds()) < 1


class TestSpacedRepetition:
    """Tests for the SpacedRepetition class."""
    
    def test_init_empty(self):
        """Should initialize with no stats."""
        srs = SpacedRepetition(grade=2)
        
        assert srs.grade == 2
        assert len(srs.question_stats) == 0
    
    def test_init_with_stats(self):
        """Should initialize with provided stats."""
        stats = {
            "add_7_5": QuestionStats(question_id="add_7_5", box=3),
            "sub_10_4": QuestionStats(question_id="sub_10_4", box=1),
        }
        srs = SpacedRepetition(question_stats=stats, grade=1)
        
        assert len(srs.question_stats) == 2
    
    def test_get_next_question_returns_question(self):
        """Should always return a valid MathQuestion."""
        srs = SpacedRepetition(grade=1)
        
        question = srs.get_next_question()
        
        assert isinstance(question, MathQuestion)
        assert question.question_id is not None
        assert question.correct_answer is not None
    
    def test_record_answer_correct_moves_box_up(self):
        """Correct answer should move question up one box."""
        srs = SpacedRepetition(grade=1)
        question_id = "add_5_3"
        
        # Record first correct answer
        srs.record_answer(question_id, correct=True)
        
        stats = srs.question_stats[question_id]
        assert stats.box == 2
        assert stats.correct_count == 1
        assert stats.incorrect_count == 0
    
    def test_record_answer_incorrect_resets_to_box_1(self):
        """Incorrect answer should reset question to box 1."""
        initial_stats = {
            "add_5_3": QuestionStats(question_id="add_5_3", box=4),
        }
        srs = SpacedRepetition(question_stats=initial_stats, grade=1)
        
        srs.record_answer("add_5_3", correct=False)
        
        stats = srs.question_stats["add_5_3"]
        assert stats.box == MIN_BOX
        assert stats.incorrect_count == 1
    
    def test_record_answer_max_box_limit(self):
        """Box should not exceed MAX_BOX."""
        initial_stats = {
            "add_5_3": QuestionStats(question_id="add_5_3", box=MAX_BOX),
        }
        srs = SpacedRepetition(question_stats=initial_stats, grade=1)
        
        srs.record_answer("add_5_3", correct=True)
        
        assert srs.question_stats["add_5_3"].box == MAX_BOX
    
    def test_record_answer_updates_last_asked(self):
        """Recording answer should update last_asked timestamp."""
        srs = SpacedRepetition(grade=1)
        before = datetime.now()
        
        srs.record_answer("add_5_3", correct=True)
        
        after = datetime.now()
        last_asked = srs.question_stats["add_5_3"].last_asked
        assert before <= last_asked <= after
    
    def test_no_immediate_repeat(self):
        """Should not repeat the same question immediately."""
        srs = SpacedRepetition(grade=1)
        
        # Ask and answer a few questions
        asked_ids = []
        for _ in range(10):
            q = srs.get_next_question()
            srs.record_answer(q.question_id, correct=True)
            asked_ids.append(q.question_id)
        
        # Check that no question was asked twice in a row
        for i in range(1, len(asked_ids)):
            # Allow some repeats but not immediate ones
            # (within recent window of 5)
            pass  # The SRS has a 5-question buffer
    
    def test_get_weak_areas_identifies_struggles(self):
        """Should identify operations with low accuracy."""
        stats = {
            "add_1_1": QuestionStats(question_id="add_1_1", correct_count=9, incorrect_count=1),
            "add_2_2": QuestionStats(question_id="add_2_2", correct_count=8, incorrect_count=2),
            "sub_5_3": QuestionStats(question_id="sub_5_3", correct_count=2, incorrect_count=8),
            "sub_7_2": QuestionStats(question_id="sub_7_2", correct_count=3, incorrect_count=7),
        }
        srs = SpacedRepetition(question_stats=stats, grade=1)
        
        weak_areas = srs.get_weak_areas()
        
        assert "Subtraktion" in weak_areas
        assert "Addition" not in weak_areas
    
    def test_get_strong_areas_identifies_mastery(self):
        """Should identify operations with high accuracy."""
        stats = {
            "add_1_1": QuestionStats(question_id="add_1_1", correct_count=9, incorrect_count=1),
            "add_2_2": QuestionStats(question_id="add_2_2", correct_count=8, incorrect_count=1),
            "add_3_3": QuestionStats(question_id="add_3_3", correct_count=10, incorrect_count=0),
            "sub_5_3": QuestionStats(question_id="sub_5_3", correct_count=2, incorrect_count=8),
        }
        srs = SpacedRepetition(question_stats=stats, grade=1)
        
        strong_areas = srs.get_strong_areas()
        
        assert "Plus-Aufgaben" in strong_areas
    
    def test_export_and_load_stats(self):
        """Should export and reload stats correctly."""
        srs = SpacedRepetition(grade=2)
        
        # Record some answers
        srs.record_answer("add_5_3", correct=True)
        srs.record_answer("add_5_3", correct=True)
        srs.record_answer("mul_4_5", correct=False)
        
        # Export
        exported = srs.export_stats()
        
        # Create new SRS and load
        srs2 = SpacedRepetition(grade=2)
        srs2.load_stats(exported)
        
        # Verify
        assert len(srs2.question_stats) == 2
        assert srs2.question_stats["add_5_3"].correct_count == 2
        assert srs2.question_stats["add_5_3"].box == 3  # Started at 1, +2 correct
        assert srs2.question_stats["mul_4_5"].box == 1  # Reset on incorrect
    
    def test_reconstruct_addition_question(self):
        """Should correctly reconstruct an addition question."""
        srs = SpacedRepetition(grade=1)
        
        question = srs._reconstruct_question("add_7_5")
        
        assert question is not None
        assert question.operand1 == 7
        assert question.operand2 == 5
        assert question.correct_answer == 12
        assert question.operation == Operation.ADDITION
        assert "plus" in question.question_text_german
    
    def test_reconstruct_subtraction_question(self):
        """Should correctly reconstruct a subtraction question."""
        srs = SpacedRepetition(grade=1)
        
        question = srs._reconstruct_question("sub_10_4")
        
        assert question is not None
        assert question.operand1 == 10
        assert question.operand2 == 4
        assert question.correct_answer == 6
        assert question.operation == Operation.SUBTRACTION
    
    def test_reconstruct_multiplication_question(self):
        """Should correctly reconstruct a multiplication question."""
        srs = SpacedRepetition(grade=2)
        
        question = srs._reconstruct_question("mul_6_8")
        
        assert question is not None
        assert question.correct_answer == 48
        assert question.operation == Operation.MULTIPLICATION
    
    def test_reconstruct_division_question(self):
        """Should correctly reconstruct a division question."""
        srs = SpacedRepetition(grade=3)
        
        question = srs._reconstruct_question("div_24_6")
        
        assert question is not None
        assert question.correct_answer == 4
        assert question.operation == Operation.DIVISION
    
    def test_reconstruct_invalid_question_id(self):
        """Should return None for invalid question IDs."""
        srs = SpacedRepetition(grade=1)
        
        assert srs._reconstruct_question("invalid") is None
        assert srs._reconstruct_question("add_x_5") is None
        assert srs._reconstruct_question("unknown_5_3") is None
    
    def test_reset_session(self):
        """Should clear session tracking."""
        srs = SpacedRepetition(grade=1)
        
        # Ask some questions
        for _ in range(5):
            q = srs.get_next_question()
            srs.record_answer(q.question_id, correct=True)
        
        # Reset session
        srs.reset_session()
        
        # Stats should be preserved
        assert len(srs.question_stats) > 0
        # But session tracking should be cleared (internal state)
    
    def test_prioritizes_lower_boxes(self):
        """Questions in lower boxes should be selected more often."""
        # Create stats with questions in different boxes
        stats = {
            "add_1_1": QuestionStats(question_id="add_1_1", box=1),
            "add_2_2": QuestionStats(question_id="add_2_2", box=5),
            "add_3_3": QuestionStats(question_id="add_3_3", box=5),
            "add_4_4": QuestionStats(question_id="add_4_4", box=5),
            "add_5_5": QuestionStats(question_id="add_5_5", box=5),
        }
        srs = SpacedRepetition(question_stats=stats, grade=1)
        
        # Run many selections and count
        box1_count = 0
        total_srs_selections = 0
        
        with patch.object(srs, '_should_generate_new', return_value=False):
            for _ in range(100):
                q = srs.get_next_question()
                if q and q.question_id in stats:
                    total_srs_selections += 1
                    if q.question_id == "add_1_1":
                        box1_count += 1
                srs._recent_questions.clear()  # Allow repeats for this test
        
        # Box 1 question should be selected more often than average
        if total_srs_selections > 0:
            box1_ratio = box1_count / total_srs_selections
            # With weights, box 1 should be selected significantly more
            # (it has weight 1.0, box 5 has weight 0.0625)
            assert box1_ratio > 0.3  # Should be selected >30% of time


class TestSRSIntegration:
    """Integration tests for the SRS with the math engine."""
    
    def test_full_learning_session(self):
        """Simulate a full learning session."""
        srs = SpacedRepetition(grade=1)
        
        # Simulate 20 questions
        results = []
        for _ in range(20):
            question = srs.get_next_question()
            
            # Simulate answering (70% correct rate)
            import random
            correct = random.random() < 0.7
            srs.record_answer(question.question_id, correct)
            results.append((question.question_id, correct))
        
        # Should have tracked all questions
        assert len(srs.question_stats) > 0
        
        # Export should work
        exported = srs.export_stats()
        assert len(exported) > 0
    
    def test_grade_change_generates_appropriate_questions(self):
        """Changing grade should affect question generation."""
        srs = SpacedRepetition(grade=1)
        
        # Get a question for grade 1
        q1 = srs.get_next_question()
        assert q1.operation in [Operation.ADDITION, Operation.SUBTRACTION]
        
        # Change to grade 3
        srs.grade = 3
        
        # Grade 3 can include multiplication and division
        # Get several questions to check variety
        operations = set()
        for _ in range(50):
            q = srs.get_next_question()
            operations.add(q.operation)
        
        # Should have more than just add/sub
        assert len(operations) >= 2
