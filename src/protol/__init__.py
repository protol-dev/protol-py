"""Protol Python SDK — The civilization layer for AI agents.

Provides identity, action tracking, and reputation scoring for AI agents.

Quick start::

    from protol import Protol

    p = Protol(api_key="aos_sk_...", local_mode=True)
    agent = p.register_agent(
        name="my-agent", category="research", capabilities=["web_research"]
    )

    with agent.action(task_category="research") as act:
        result = do_some_work()
        act.success(output=result, confidence=0.9)

    print(f"Score: {agent.reputation_score} | Tier: {agent.trust_tier}")
"""

from protol.action import Action
from protol.agent import Agent
from protol.client import Protol, AsyncProtol
from protol.constants import SDK_VERSION as __version__
from protol.exceptions import (
    ActionError,
    ProtolError,
    AuthenticationError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)
from protol.models import (
    ActionResponse,
    AgentProfile,
    AgentReputation,
    EcosystemStats,
    IncidentResponse,
    LeaderboardEntry,
    ReputationBreakdown,
    ReputationHistory,
    SearchResult,
)

# Backward-compatibility aliases
AgentOS = Protol
AsyncAgentOS = AsyncProtol
AgentOSError = ProtolError

__all__ = [
    # Client
    "Protol",
    "AsyncProtol",
    # Backward-compat aliases
    "AgentOS",
    "AsyncAgentOS",
    # Core classes
    "Agent",
    "Action",
    # Models
    "AgentProfile",
    "AgentReputation",
    "ReputationBreakdown",
    "ReputationHistory",
    "ActionResponse",
    "IncidentResponse",
    "SearchResult",
    "LeaderboardEntry",
    "EcosystemStats",
    # Exceptions
    "ProtolError",
    "AgentOSError",
    "AuthenticationError",
    "NotFoundError",
    "ValidationError",
    "RateLimitError",
    "ServerError",
    "NetworkError",
    "ActionError",
    # Version
    "__version__",
]
