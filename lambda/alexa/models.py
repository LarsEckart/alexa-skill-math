"""
Data models for the German Math Quiz Alexa Skill.

This module defines the data structures used for tracking user progress
and spaced repetition learning.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class QuestionStats:
    """
    Statistics tracked for each question for spaced repetition.
    
    Uses a Leitner Box system (boxes 1-5):
    - Box 1: New/difficult questions (asked frequently)
    - Box 5: Well-learned questions (asked rarely)
    """
    question_id: str  # Matches MathQuestion.question_id, e.g., "add_7_5"
    correct_count: int = 0
    incorrect_count: int = 0
    last_asked: datetime | None = None
    box: int = 1  # Leitner box (1-5), starts at 1
    
    @property
    def total_attempts(self) -> int:
        """Total number of times this question was asked."""
        return self.correct_count + self.incorrect_count
    
    @property
    def accuracy(self) -> float:
        """Accuracy rate as a value between 0 and 1."""
        if self.total_attempts == 0:
            return 0.5  # Neutral for new questions
        return self.correct_count / self.total_attempts
    
    def to_dict(self) -> dict:
        """Convert to dictionary for persistence."""
        return {
            "question_id": self.question_id,
            "correct_count": self.correct_count,
            "incorrect_count": self.incorrect_count,
            "last_asked": self.last_asked.isoformat() if self.last_asked else None,
            "box": self.box,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "QuestionStats":
        """Create from dictionary (from persistence)."""
        last_asked = None
        if data.get("last_asked"):
            last_asked = datetime.fromisoformat(data["last_asked"])
        
        return cls(
            question_id=data["question_id"],
            correct_count=data.get("correct_count", 0),
            incorrect_count=data.get("incorrect_count", 0),
            last_asked=last_asked,
            box=data.get("box", 1),
        )


@dataclass
class UserProfile:
    """
    User profile containing learning preferences and overall statistics.
    """
    user_id: str
    name: str | None = None
    grade: int = 1  # Grade level (1-4)
    total_questions_answered: int = 0
    total_correct: int = 0
    current_streak: int = 0  # Consecutive correct answers
    best_streak: int = 0
    last_session: datetime | None = None
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def overall_accuracy(self) -> float:
        """Overall accuracy across all questions."""
        if self.total_questions_answered == 0:
            return 0.0
        return self.total_correct / self.total_questions_answered
    
    def to_dict(self) -> dict:
        """Convert to dictionary for persistence."""
        return {
            "user_id": self.user_id,
            "name": self.name,
            "grade": self.grade,
            "total_questions_answered": self.total_questions_answered,
            "total_correct": self.total_correct,
            "current_streak": self.current_streak,
            "best_streak": self.best_streak,
            "last_session": self.last_session.isoformat() if self.last_session else None,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserProfile":
        """Create from dictionary (from persistence)."""
        last_session = None
        if data.get("last_session"):
            last_session = datetime.fromisoformat(data["last_session"])
        
        created_at = datetime.now()
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        
        return cls(
            user_id=data["user_id"],
            name=data.get("name"),
            grade=data.get("grade", 1),
            total_questions_answered=data.get("total_questions_answered", 0),
            total_correct=data.get("total_correct", 0),
            current_streak=data.get("current_streak", 0),
            best_streak=data.get("best_streak", 0),
            last_session=last_session,
            created_at=created_at,
        )
