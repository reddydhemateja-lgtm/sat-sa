from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.review import ReviewDecisionEnum


class ReviewDecisionCreate(BaseModel):
    decision: ReviewDecisionEnum
    comment: str | None = Field(default=None, max_length=4000)


class ReviewDecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    finding_id: int
    reviewer_id: int
    decision: ReviewDecisionEnum
    comment: str | None
    previous_decision: str | None
    decided_at: datetime
    created_at: datetime