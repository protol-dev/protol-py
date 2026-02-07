"""AgentOS Python SDK — The civilization layer for AI agents.

Provides identity, action tracking, and reputation scoring for AI agents.

Quick start::

    from agent_os import AgentOS

    aos = AgentOS(api_key="aos_sk_...", local_mode=True)
    agent = aos.register_agent(
        name="my-agent", category="research", capabilities=["web_research"]
    )

    with agent.action(task_category="research") as act:
        result = do_some_work()
        act.success(output=result, confidence=0.9)

    print(f"Score: {agent.reputation_score} | Tier: {agent.trust_tier}")
"""

from agent_os.action import Action
from agent_os.agent import Agent
from agent_os.client import AgentOS, AsyncAgentOS
from agent_os.constants import SDK_VERSION as __version__
from agent_os.exceptions import (
    ActionError,
    AgentOSError,
    AuthenticationError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
    ValidationError,
)
from agent_os.models import (
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

__all__ = [
    # Client
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
