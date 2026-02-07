"""Pydantic v2 models for the Protol SDK."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from protol.constants import (
    VALID_ACTION_STATUSES,
    VALID_ACTION_TYPES,
    VALID_AGENT_CATEGORIES,
    VALID_AUTONOMY_LEVELS,
    VALID_ENVIRONMENTS,
    VALID_ERROR_TYPES,
    VALID_INCIDENT_TYPES,
    VALID_SEVERITY_LEVELS,
)

# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------


class AgentRegistration(BaseModel):
    """Data needed to register a new agent."""

    model_config = ConfigDict(strict=True)

    name: str = Field(..., min_length=3, max_length=100)
    category: str
    capabilities: list[str] = Field(..., min_length=1, max_length=20)
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    framework: Optional[str] = None
    hosting: Optional[str] = None
    source_url: Optional[str] = None
    autonomy_level: str = "semi"
    max_spend_per_task: Optional[float] = None
    can_hire_agents: bool = False
    description: Optional[str] = Field(default=None, max_length=500)
    tags: Optional[list[str]] = Field(default=None, max_length=10)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        import re

        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9\-_ ]*$", v):
            raise ValueError(
                "Name must start with alphanumeric and contain only "
                "alphanumeric characters, hyphens, underscores, or spaces."
            )
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in VALID_AGENT_CATEGORIES:
            raise ValueError(
                f"Invalid category '{v}'. Must be one of: {VALID_AGENT_CATEGORIES}"
            )
        return v

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, v: list[str]) -> list[str]:
        for cap in v:
            if not (2 <= len(cap) <= 50):
                raise ValueError(
                    f"Each capability must be 2-50 characters. Got '{cap}' ({len(cap)} chars)."
                )
        return v

    @field_validator("autonomy_level")
    @classmethod
    def validate_autonomy_level(cls, v: str) -> str:
        if v not in VALID_AUTONOMY_LEVELS:
            raise ValueError(
                f"Invalid autonomy_level '{v}'. Must be one of: {VALID_AUTONOMY_LEVELS}"
            )
        return v

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            import re

            if not re.match(r"^https?://", v):
                raise ValueError("source_url must be a valid HTTP/HTTPS URL.")
        return v


class AgentUpdate(BaseModel):
    """Data for updating an existing agent. All fields optional."""

    model_config = ConfigDict(strict=True)

    name: Optional[str] = Field(default=None, min_length=3, max_length=100)
    category: Optional[str] = None
    capabilities: Optional[list[str]] = Field(default=None, min_length=1, max_length=20)
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    framework: Optional[str] = None
    hosting: Optional[str] = None
    source_url: Optional[str] = None
    autonomy_level: Optional[str] = None
    max_spend_per_task: Optional[float] = None
    can_hire_agents: Optional[bool] = None
    description: Optional[str] = Field(default=None, max_length=500)
    tags: Optional[list[str]] = Field(default=None, max_length=10)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_AGENT_CATEGORIES:
            raise ValueError(
                f"Invalid category '{v}'. Must be one of: {VALID_AGENT_CATEGORIES}"
            )
        return v

    @field_validator("autonomy_level")
    @classmethod
    def validate_autonomy_level(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_AUTONOMY_LEVELS:
            raise ValueError(
                f"Invalid autonomy_level '{v}'. Must be one of: {VALID_AUTONOMY_LEVELS}"
            )
        return v


class ActionRecord(BaseModel):
    """Data for recording an action."""

    model_config = ConfigDict(strict=True)

    agent_id: str
    action_type: str
    task_category: Optional[str] = None
    description: Optional[str] = Field(default=None, max_length=500)
    commissioned_by: Optional[str] = None
    commissioner_type: Optional[str] = None
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    input_hash: Optional[str] = None
    output_hash: Optional[str] = None
    input_size_bytes: Optional[int] = None
    output_size_bytes: Optional[int] = None
    cost_usd: Optional[float] = None
    payment_usd: Optional[float] = None
    self_reported_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    error_type: Optional[str] = None
    error_message: Optional[str] = Field(default=None, max_length=500)
    environment: str = "production"

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, v: str) -> str:
        if v not in VALID_ACTION_TYPES:
            raise ValueError(
                f"Invalid action_type '{v}'. Must be one of: {VALID_ACTION_TYPES}"
            )
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_ACTION_STATUSES:
            raise ValueError(
                f"Invalid status '{v}'. Must be one of: {VALID_ACTION_STATUSES}"
            )
        return v

    @field_validator("commissioner_type")
    @classmethod
    def validate_commissioner_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("agent", "human"):
            raise ValueError("commissioner_type must be 'agent' or 'human'.")
        return v

    @field_validator("error_type")
    @classmethod
    def validate_error_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_ERROR_TYPES:
            raise ValueError(
                f"Invalid error_type '{v}'. Must be one of: {VALID_ERROR_TYPES}"
            )
        return v

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        if v not in VALID_ENVIRONMENTS:
            raise ValueError(
                f"Invalid environment '{v}'. Must be one of: {VALID_ENVIRONMENTS}"
            )
        return v


class ActionRating(BaseModel):
    """Rating for a completed action."""

    model_config = ConfigDict(strict=True)

    rating: int = Field(..., ge=1, le=5)
    feedback: Optional[str] = Field(default=None, max_length=500)


class IncidentReport(BaseModel):
    """Report an incident against an agent."""

    model_config = ConfigDict(strict=True)

    agent_id: str
    incident_type: str
    severity: str
    title: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=10, max_length=2000)
    evidence_url: Optional[str] = None
    financial_impact_usd: Optional[float] = None
    users_affected: Optional[int] = None

    @field_validator("incident_type")
    @classmethod
    def validate_incident_type(cls, v: str) -> str:
        if v not in VALID_INCIDENT_TYPES:
            raise ValueError(
                f"Invalid incident_type '{v}'. Must be one of: {VALID_INCIDENT_TYPES}"
            )
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        if v not in VALID_SEVERITY_LEVELS:
            raise ValueError(
                f"Invalid severity '{v}'. Must be one of: {VALID_SEVERITY_LEVELS}"
            )
        return v


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------


class Owner(BaseModel):
    """Agent owner information."""

    owner_id: str
    display_name: str
    verified: bool


class AgentArchitecture(BaseModel):
    """Agent architecture details."""

    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    framework: Optional[str] = None
    hosting: Optional[str] = None


class ReputationBreakdown(BaseModel):
    """Detailed reputation score breakdown across 5 dimensions."""

    reliability: float
    safety: float
    consistency: float
    efficiency: float
    transparency: float


class AgentReputation(BaseModel):
    """Agent reputation information."""

    overall_score: float
    trust_tier: str
    breakdown: ReputationBreakdown
    trend: str  # 'improving' | 'stable' | 'declining'
    last_computed: datetime


class AgentStats(BaseModel):
    """Agent statistics."""

    total_actions: int
    success_rate: float
    avg_rating: Optional[float] = None
    total_earnings_usd: float
    active_since: datetime
    last_active: Optional[datetime] = None
    incidents: int


class AgentProfile(BaseModel):
    """Full agent profile as returned by the API."""

    agent_id: str
    name: str
    slug: str
    owner: Owner
    architecture: AgentArchitecture
    capabilities: list[str]
    category: str
    autonomy_level: str
    reputation: AgentReputation
    stats: AgentStats
    status: str
    verification: str
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    created_at: datetime
    source_url: Optional[str] = None


class ActionResponse(BaseModel):
    """Action as returned by the API."""

    action_id: str
    agent_id: str
    action_type: str
    task_category: Optional[str] = None
    description: Optional[str] = None
    commissioned_by: Optional[str] = None
    commissioner_type: Optional[str] = None
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    cost_usd: Optional[float] = None
    payment_usd: Optional[float] = None
    self_reported_confidence: Optional[float] = None
    commissioner_rating: Optional[int] = None
    commissioner_feedback: Optional[str] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    verified: bool = False
    environment: str = "production"
    recorded_at: datetime


class IncidentResponse(BaseModel):
    """Incident as returned by the API."""

    incident_id: str
    agent_id: str
    reported_by: str
    incident_type: str
    severity: str
    title: str
    description: str
    evidence_url: Optional[str] = None
    financial_impact_usd: Optional[float] = None
    users_affected: Optional[int] = None
    status: str
    verified: bool = False
    created_at: datetime


class ReputationHistory(BaseModel):
    """Single reputation snapshot."""

    overall_score: float
    breakdown: ReputationBreakdown
    trust_tier: str
    actions_in_window: int
    computed_at: datetime


class SearchResult(BaseModel):
    """Paginated search results."""

    agents: list[AgentProfile]
    total: int
    page: int
    per_page: int
    has_more: bool


class LeaderboardEntry(BaseModel):
    """Single leaderboard entry."""

    agent_id: str
    name: str
    category: str
    reputation_score: float
    trust_tier: str
    total_actions: int
    owner: Owner


class EcosystemStats(BaseModel):
    """Ecosystem-wide statistics."""

    total_agents: int
    total_actions: int
    total_incidents: int
    avg_reputation: float
    agents_by_category: dict[str, int]
    agents_by_tier: dict[str, int]
    actions_last_24h: int
    actions_last_7d: int
