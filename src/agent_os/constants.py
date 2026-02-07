"""AgentOS SDK constants and default configuration."""

from __future__ import annotations

SDK_VERSION: str = "0.1.0"
DEFAULT_BASE_URL: str = "https://api.protol.dev/v1"
DEFAULT_TIMEOUT: int = 30  # seconds
DEFAULT_MAX_RETRIES: int = 3

VALID_AGENT_CATEGORIES: list[str] = [
    "research",
    "coding",
    "writing",
    "data_analysis",
    "customer_support",
    "sales",
    "marketing",
    "finance",
    "legal",
    "healthcare",
    "education",
    "devops",
    "security",
    "general",
]

VALID_AUTONOMY_LEVELS: list[str] = ["assisted", "semi", "autonomous"]

VALID_ACTION_TYPES: list[str] = [
    "task_execution",
    "agent_hire",
    "api_call",
    "data_access",
    "communication",
    "decision",
]

VALID_ACTION_STATUSES: list[str] = [
    "running",
    "success",
    "partial",
    "failed",
    "timeout",
    "error",
]

VALID_ERROR_TYPES: list[str] = [
    "timeout",
    "hallucination",
    "api_failure",
    "input_invalid",
    "output_invalid",
    "safety_violation",
    "rate_limit",
    "auth_failure",
    "unknown",
]

VALID_INCIDENT_TYPES: list[str] = [
    "data_leak",
    "hallucination",
    "unauthorized_action",
    "financial_error",
    "downtime",
    "safety_violation",
    "prompt_injection",
    "performance_degradation",
]

VALID_SEVERITY_LEVELS: list[str] = ["low", "medium", "high", "critical"]

VALID_ENVIRONMENTS: list[str] = ["production", "staging", "development", "test"]

VALID_TRUST_TIERS: list[str] = ["Unverified", "Bronze", "Silver", "Gold", "Platinum"]
