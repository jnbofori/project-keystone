from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, Field


class ProjectDeliveryForecastResponse(BaseModel):
    project_id: uuid.UUID
    remaining: float = 0
    unit: str = "points"  # "points" | "items"
    samples_used: int = 0
    trials: int = 5000
    method: str = "monte_carlo_throughput"
    p50_date: date | None = None
    p85_date: date | None = None
    p95_date: date | None = None
    already_complete: bool = False
    unavailable_reason: str | None = None
    historical_rates: list[float] = Field(default_factory=list)
    average_velocity: float | None = None
    estimated_sprints: float | None = None
    likely_sprints: int | None = None
