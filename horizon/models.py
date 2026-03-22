from datetime import date
from pydantic import BaseModel, field_validator


class Task(BaseModel):
    id: str
    name: str
    story_points: int | float
    estimated_days: float
    actual_days: float
    calendar_days: int
    completed_date: date

    @field_validator("estimated_days", "actual_days")
    @classmethod
    def must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("must be positive")
        return v

    @field_validator("calendar_days")
    @classmethod
    def calendar_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("must be positive")
        return v


class TeamData(BaseModel):
    team: str
    tasks: list[Task]


class EstimationRequest(BaseModel):
    task_name: str
    story_points: int | float
    initial_estimate_days: float

    @field_validator("initial_estimate_days")
    @classmethod
    def must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("must be positive")
        return v


class PercentileEstimate(BaseModel):
    p10: float
    p50: float
    p90: float


class ReferenceCase(BaseModel):
    task: Task
    similarity_score: float  # 0.0 - 1.0


class EstimationResult(BaseModel):
    request: EstimationRequest
    team_name: str
    effort_days: PercentileEstimate
    calendar_days: PercentileEstimate
    simulation_samples: list[float]
    calendar_samples: list[float]
    reference_cases: list[ReferenceCase]
    dataset_size: int
    timestamp: str
