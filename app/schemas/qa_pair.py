"""Schema for question-answer pairs with user feedback"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from uuid import uuid4
from pydantic import BaseModel, Field


class Source(BaseModel):
    """Source reference for an answer"""
    document_id: str
    source: str = ""
    type: str = ""
    relevance: str = "cited"  # "cited" or "relevant"


class FeedbackItem(BaseModel):
    """User feedback on an answer"""
    timestamp: datetime = Field(default_factory=datetime.now)
    is_accurate: bool
    feedback_text: Optional[str] = None


class QAPair(BaseModel):
    """Question-answer pair with feedback and sources"""
    qa_id: str = Field(default_factory=lambda: str(uuid4()))
    question: str
    answer: str
    sources: List[Source] = Field(default_factory=list)
    feedback: List[FeedbackItem] = Field(default_factory=list)
    is_validated: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
    
    @property
    def is_accurate(self) -> bool:
        """Check if the answer is marked as accurate based on feedback"""
        if not self.feedback:
            return False
        return self.feedback[-1].is_accurate
        
    def add_feedback(self, is_accurate: bool, feedback_text: Optional[str] = None) -> None:
        """Add user feedback to the Q&A pair"""
        self.feedback.append(
            FeedbackItem(
                timestamp=datetime.now(),
                is_accurate=is_accurate,
                feedback_text=feedback_text
            )
        )
        self.updated_at = datetime.now()
        
        # If marked as accurate and not already validated, update validation status
        if is_accurate and not self.is_validated:
            self.is_validated = True 