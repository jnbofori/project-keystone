from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from llama_index.llms.openai import OpenAI
from sqlalchemy.orm import Session

from app.config import get_settings
from app.projects.dashboard import build_project_dashboard
from app.schemas.dashboard import ProjectDashboardResponse, SprintInsightsResponse

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a delivery coach for engineering project managers.
Given structured sprint metrics JSON, write 1–2 short paragraphs of plain prose.

Requirements:
- Analyze sprint health and identify delivery risks
- Explain the evidence using specific numbers from the data
- Prefer concrete observations (progress vs time, blockers, scope change, velocity/forecast, aging WIP, load imbalance) over generic advice
- Do not invent metrics that are missing or null
- Do not use bullet lists or markdown headings
- End with one clear implication or recommended focus if risk is elevated

Metric semantics (follow these exactly):
- velocity.forecast_current is a pace estimate (points done so far extrapolated over the full sprint, or else the 3-sprint average). It is NOT a target, goal, or commitment. Never say the team is "behind the forecast" or that the forecast is an ambitious target they must hit.
- pace_gap = progress percent minus elapsed percent. Positive pace_gap / pace_label "Ahead" means ahead of schedule; negative / "Behind" means behind. Do not compare pace_gap to forecast_current.
- When time.elapsed_percent is low (under about 20–25%), treat progress %, pace_gap, and especially forecast_current as unstable. Prefer soft language such as "too early to judge pace" or "extrapolation is noisy" instead of strong delivery-risk claims driven only by those numbers. Still report hard facts (blocked count, scope added, load imbalance).
- Compare velocity.forecast_current to progress.total_points (committed sprint scope). If forecast >= total_points, current pace may cover scope; if forecast < total_points, there is risk of unfinished work or carryover (align with risks.carryover_likely when present). When risks.scope_added_points is non-zero, mention it as added mid-sprint load already reflected in total_points.
- Treat risk_indicators.*.level and measurable fields (velocity_ratio, scope_growth_percent, dependency at_risk_count) as authoritative scored risk signals and cite them when elevated. Use Attention metrics (blocked_count, scope_added_points, reopened_count, pace_gap) as supporting evidence alongside those indicators.
"""

USER_ASK = (
    "Analyze the sprint health. Identify delivery risks and explain the evidence "
    "from the metrics below."
)

NO_SPRINT_INSIGHT = (
    "There is not enough sprint data to analyze yet. Link a Jira project and sync "
    "so Keystone can compute delivery metrics, then try again."
)


def _compact_dashboard(dashboard: ProjectDashboardResponse) -> dict:
    return dashboard.model_dump(mode="json", exclude_none=True)


def generate_sprint_insights(db: Session, project_id: UUID) -> SprintInsightsResponse:
    dashboard = build_project_dashboard(db, project_id)
    generated_at = datetime.now(UTC)
    sprint_name = dashboard.active_sprint.name if dashboard.active_sprint else None

    if dashboard.active_sprint is None:
        return SprintInsightsResponse(
            insight=NO_SPRINT_INSIGHT,
            sprint_name=None,
            generated_at=generated_at,
        )

    settings = get_settings()
    if not settings.openai_api_key.strip():
        return SprintInsightsResponse(
            insight="OpenAI is not configured so sprint intelligence is unavailable.",
            sprint_name=sprint_name,
            generated_at=generated_at,
        )

    payload = _compact_dashboard(dashboard)
    user_prompt = (
        f"{USER_ASK}\n\n"
        f"Sprint metrics JSON:\n{json.dumps(payload, indent=2, default=str)}"
    )
    prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt}\n\nInsight:"
    
    try:
        llm = OpenAI(
            model=settings.openai_llm_model,
            api_key=settings.openai_api_key,
            temperature=0.2,
        )
        response = llm.complete(prompt)
        insight = str(response).strip()
    except Exception:
        logger.exception("Sprint insights LLM call failed for project %s", project_id)
        raise

    if not insight:
        insight = "The model returned an empty analysis. Retry in a moment."

    return SprintInsightsResponse(
        insight=insight,
        sprint_name=sprint_name,
        generated_at=generated_at,
    )
