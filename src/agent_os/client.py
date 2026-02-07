"""Main AgentOS client classes (sync and async).

Entry points for the SDK. Developers instantiate AgentOS or AsyncAgentOS first.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Union

from agent_os._utils import validate_api_key
from agent_os.agent import Agent
from agent_os.constants import (
    DEFAULT_BASE_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
)
from agent_os.exceptions import ValidationError
from agent_os.models import (
    AgentProfile,
    AgentRegistration,
    AgentUpdate,
    EcosystemStats,
    IncidentReport,
    IncidentResponse,
    LeaderboardEntry,
    SearchResult,
)

logger = logging.getLogger("agent_os")


class AgentOS:
    """Main client for the Protol platform.

    Usage::

        aos = AgentOS(api_key="aos_sk_...")
        agent = aos.register_agent(
            name="my-agent", category="research", capabilities=["web_research"]
        )

        # Or connect to existing agent
        agent = aos.get_agent("agt_7x9k2m")

        # Local mode (no backend needed):
        aos = AgentOS(api_key="test", local_mode=True)

    Args:
        api_key: Your AgentOS owner API key (starts with 'aos_sk_').
        base_url: API base URL (override for self-hosted or testing).
        timeout: Request timeout in seconds.
        max_retries: Max retry attempts for failed requests.
        environment: Default environment for all actions ('production'/'staging'/'test').
        local_mode: If True, use in-memory store instead of HTTP calls.

    Raises:
        ValidationError: If api_key format is invalid (when local_mode=False).
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        environment: str = "production",
        local_mode: bool = False,
    ) -> None:
        self._api_key = api_key
        self._environment = environment
        self._local_mode = local_mode

        if local_mode:
            from agent_os._local_store import LocalStore

            self._client: Any = LocalStore(owner_id=f"owner_{api_key[:8]}")
            logger.info("AgentOS initialized in local mode (no HTTP calls).")
        else:
            if not validate_api_key(api_key):
                raise ValidationError(
                    message="Invalid API key format. Must start with 'aos_sk_' "
                    "followed by at least 20 characters."
                )
            from agent_os._http import HttpClient

            self._client = HttpClient(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout,
                max_retries=max_retries,
            )
            logger.info("AgentOS initialized (base_url=%s).", base_url)

    def register_agent(
        self,
        name: str,
        category: str,
        capabilities: list[str],
        model_provider: Optional[str] = None,
        model_name: Optional[str] = None,
        framework: Optional[str] = None,
        hosting: Optional[str] = None,
        source_url: Optional[str] = None,
        autonomy_level: str = "semi",
        max_spend_per_task: Optional[float] = None,
        can_hire_agents: bool = False,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> Agent:
        """Register a new agent with the Protol platform.

        Returns an Agent instance ready for action logging.

        Raises:
            ValidationError: If input data is invalid.
            AuthenticationError: If API key is invalid.
        """
        registration = AgentRegistration(
            name=name,
            category=category,
            capabilities=capabilities,
            model_provider=model_provider,
            model_name=model_name,
            framework=framework,
            hosting=hosting,
            source_url=source_url,
            autonomy_level=autonomy_level,
            max_spend_per_task=max_spend_per_task,
            can_hire_agents=can_hire_agents,
            description=description,
            tags=tags,
        )

        payload = registration.model_dump(mode="json", exclude_none=True)
        data = self._client.post("/agents", json=payload)
        profile = AgentProfile.model_validate(data)

        logger.info("Registered agent '%s' (id=%s).", profile.name, profile.agent_id)
        return Agent(
            client=self._client,
            profile=profile,
            default_environment=self._environment,
        )

    def get_agent(self, agent_id: str) -> Agent:
        """Connect to an existing registered agent.

        Args:
            agent_id: The agent's ID (e.g., 'agt_7x9k2m').

        Returns:
            Agent instance connected to the existing agent.

        Raises:
            NotFoundError: If agent doesn't exist.
        """
        data = self._client.get(f"/agents/{agent_id}")
        profile = AgentProfile.model_validate(data)
        return Agent(
            client=self._client,
            profile=profile,
            default_environment=self._environment,
        )

    def update_agent(self, agent_id: str, **kwargs: Any) -> AgentProfile:
        """Update an existing agent's details.

        Args:
            agent_id: The agent's ID.
            **kwargs: Fields to update (same as register_agent parameters).

        Returns:
            Updated AgentProfile.
        """
        update = AgentUpdate(**kwargs)
        payload = update.model_dump(mode="json", exclude_none=True)
        data = self._client.patch(f"/agents/{agent_id}", json=payload)
        return AgentProfile.model_validate(data)

    def lookup(self, agent_id: str) -> AgentProfile:
        """Look up any agent's public profile (no ownership required).

        Use this to check an agent's reputation before interacting.

        Args:
            agent_id: The agent's ID.

        Returns:
            AgentProfile (read-only).
        """
        data = self._client.get(f"/agents/{agent_id}")
        return AgentProfile.model_validate(data)

    def search_agents(
        self,
        category: Optional[str] = None,
        capabilities: Optional[list[str]] = None,
        min_reputation: Optional[float] = None,
        trust_tier: Optional[str] = None,
        model_provider: Optional[str] = None,
        sort_by: str = "reputation",
        page: int = 1,
        per_page: int = 20,
    ) -> SearchResult:
        """Search and discover agents in the ecosystem.

        Args:
            category: Filter by agent category.
            capabilities: Filter by capabilities.
            min_reputation: Minimum reputation score.
            trust_tier: Filter by trust tier.
            model_provider: Filter by model provider.
            sort_by: Sort order ('reputation'/'actions'/'newest'/'active').
            page: Page number.
            per_page: Results per page.

        Returns:
            SearchResult with matching agents.
        """
        params: dict[str, Any] = {
            "sort_by": sort_by,
            "page": page,
            "per_page": per_page,
        }
        if category:
            params["category"] = category
        if capabilities:
            params["capabilities"] = ",".join(capabilities)
        if min_reputation is not None:
            params["min_reputation"] = min_reputation
        if trust_tier:
            params["trust_tier"] = trust_tier
        if model_provider:
            params["model_provider"] = model_provider

        data = self._client.get("/agents/search", params=params)
        return SearchResult.model_validate(data)

    def get_leaderboard(
        self,
        category: Optional[str] = None,
        limit: int = 20,
    ) -> list[LeaderboardEntry]:
        """Get top agents by reputation score.

        Args:
            category: Filter by category.
            limit: Number of entries to return.

        Returns:
            List of LeaderboardEntry objects.
        """
        params: dict[str, Any] = {"limit": limit}
        if category:
            params["category"] = category

        data = self._client.get("/leaderboard", params=params)
        if isinstance(data, list):
            return [LeaderboardEntry.model_validate(item) for item in data]
        return []

    def get_ecosystem_stats(self) -> EcosystemStats:
        """Get ecosystem-wide statistics.

        Returns:
            EcosystemStats object.
        """
        data = self._client.get("/ecosystem/stats")
        return EcosystemStats.model_validate(data)

    def report_incident(
        self,
        agent_id: str,
        incident_type: str,
        severity: str,
        title: str,
        description: str,
        evidence_url: Optional[str] = None,
        financial_impact_usd: Optional[float] = None,
        users_affected: Optional[int] = None,
    ) -> IncidentResponse:
        """Report an incident against an agent.

        Returns:
            IncidentResponse from the API.
        """
        report = IncidentReport(
            agent_id=agent_id,
            incident_type=incident_type,
            severity=severity,
            title=title,
            description=description,
            evidence_url=evidence_url,
            financial_impact_usd=financial_impact_usd,
            users_affected=users_affected,
        )

        payload = report.model_dump(mode="json", exclude_none=True)
        data = self._client.post("/incidents", json=payload)
        return IncidentResponse.model_validate(data)

    def list_my_agents(self) -> list[AgentProfile]:
        """List all agents owned by the current API key holder.

        Returns:
            List of AgentProfile objects.
        """
        data = self._client.get("/agents")
        if isinstance(data, list):
            return [AgentProfile.model_validate(item) for item in data]
        return []

    def close(self) -> None:
        """Close the HTTP client. Call when done."""
        self._client.close()

    def __enter__(self) -> AgentOS:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class AsyncAgentOS:
    """Async client for the Protol platform.

    Mirrors ``AgentOS`` with all methods as ``async def``.

    Usage::

        async with AsyncAgentOS(api_key="aos_sk_...") as aos:
            agent = await aos.register_agent(
                name="my-agent", category="research", capabilities=["web_research"]
            )
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        environment: str = "production",
        local_mode: bool = False,
    ) -> None:
        self._api_key = api_key
        self._environment = environment
        self._local_mode = local_mode

        if local_mode:
            from agent_os._local_store import LocalStore

            self._client: Any = LocalStore(owner_id=f"owner_{api_key[:8]}")
            logger.info("AsyncAgentOS initialized in local mode.")
        else:
            if not validate_api_key(api_key):
                raise ValidationError(
                    message="Invalid API key format. Must start with 'aos_sk_' "
                    "followed by at least 20 characters."
                )
            from agent_os._http import AsyncHttpClient

            self._client = AsyncHttpClient(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout,
                max_retries=max_retries,
            )

    async def register_agent(
        self,
        name: str,
        category: str,
        capabilities: list[str],
        model_provider: Optional[str] = None,
        model_name: Optional[str] = None,
        framework: Optional[str] = None,
        hosting: Optional[str] = None,
        source_url: Optional[str] = None,
        autonomy_level: str = "semi",
        max_spend_per_task: Optional[float] = None,
        can_hire_agents: bool = False,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> Agent:
        """Register a new agent (async)."""
        registration = AgentRegistration(
            name=name,
            category=category,
            capabilities=capabilities,
            model_provider=model_provider,
            model_name=model_name,
            framework=framework,
            hosting=hosting,
            source_url=source_url,
            autonomy_level=autonomy_level,
            max_spend_per_task=max_spend_per_task,
            can_hire_agents=can_hire_agents,
            description=description,
            tags=tags,
        )

        payload = registration.model_dump(mode="json", exclude_none=True)

        if self._local_mode:
            data = self._client.post("/agents", json=payload)
        else:
            data = await self._client.post("/agents", json=payload)

        profile = AgentProfile.model_validate(data)
        return Agent(
            client=self._client,
            profile=profile,
            default_environment=self._environment,
        )

    async def get_agent(self, agent_id: str) -> Agent:
        """Connect to an existing agent (async)."""
        if self._local_mode:
            data = self._client.get(f"/agents/{agent_id}")
        else:
            data = await self._client.get(f"/agents/{agent_id}")

        profile = AgentProfile.model_validate(data)
        return Agent(
            client=self._client,
            profile=profile,
            default_environment=self._environment,
        )

    async def update_agent(self, agent_id: str, **kwargs: Any) -> AgentProfile:
        """Update an agent (async)."""
        update = AgentUpdate(**kwargs)
        payload = update.model_dump(mode="json", exclude_none=True)

        if self._local_mode:
            data = self._client.patch(f"/agents/{agent_id}", json=payload)
        else:
            data = await self._client.patch(f"/agents/{agent_id}", json=payload)

        return AgentProfile.model_validate(data)

    async def lookup(self, agent_id: str) -> AgentProfile:
        """Look up any agent's public profile (async)."""
        if self._local_mode:
            data = self._client.get(f"/agents/{agent_id}")
        else:
            data = await self._client.get(f"/agents/{agent_id}")

        return AgentProfile.model_validate(data)

    async def search_agents(
        self,
        category: Optional[str] = None,
        capabilities: Optional[list[str]] = None,
        min_reputation: Optional[float] = None,
        trust_tier: Optional[str] = None,
        model_provider: Optional[str] = None,
        sort_by: str = "reputation",
        page: int = 1,
        per_page: int = 20,
    ) -> SearchResult:
        """Search agents (async)."""
        params: dict[str, Any] = {
            "sort_by": sort_by,
            "page": page,
            "per_page": per_page,
        }
        if category:
            params["category"] = category
        if capabilities:
            params["capabilities"] = ",".join(capabilities)
        if min_reputation is not None:
            params["min_reputation"] = min_reputation
        if trust_tier:
            params["trust_tier"] = trust_tier
        if model_provider:
            params["model_provider"] = model_provider

        if self._local_mode:
            data = self._client.get("/agents/search", params=params)
        else:
            data = await self._client.get("/agents/search", params=params)

        return SearchResult.model_validate(data)

    async def get_leaderboard(
        self,
        category: Optional[str] = None,
        limit: int = 20,
    ) -> list[LeaderboardEntry]:
        """Get leaderboard (async)."""
        params: dict[str, Any] = {"limit": limit}
        if category:
            params["category"] = category

        if self._local_mode:
            data = self._client.get("/leaderboard", params=params)
        else:
            data = await self._client.get("/leaderboard", params=params)

        if isinstance(data, list):
            return [LeaderboardEntry.model_validate(item) for item in data]
        return []

    async def get_ecosystem_stats(self) -> EcosystemStats:
        """Get ecosystem stats (async)."""
        if self._local_mode:
            data = self._client.get("/ecosystem/stats")
        else:
            data = await self._client.get("/ecosystem/stats")

        return EcosystemStats.model_validate(data)

    async def report_incident(
        self,
        agent_id: str,
        incident_type: str,
        severity: str,
        title: str,
        description: str,
        evidence_url: Optional[str] = None,
        financial_impact_usd: Optional[float] = None,
        users_affected: Optional[int] = None,
    ) -> IncidentResponse:
        """Report an incident (async)."""
        report = IncidentReport(
            agent_id=agent_id,
            incident_type=incident_type,
            severity=severity,
            title=title,
            description=description,
            evidence_url=evidence_url,
            financial_impact_usd=financial_impact_usd,
            users_affected=users_affected,
        )

        payload = report.model_dump(mode="json", exclude_none=True)

        if self._local_mode:
            data = self._client.post("/incidents", json=payload)
        else:
            data = await self._client.post("/incidents", json=payload)

        return IncidentResponse.model_validate(data)

    async def list_my_agents(self) -> list[AgentProfile]:
        """List all agents owned by current key (async)."""
        if self._local_mode:
            data = self._client.get("/agents")
        else:
            data = await self._client.get("/agents")

        if isinstance(data, list):
            return [AgentProfile.model_validate(item) for item in data]
        return []

    async def close(self) -> None:
        """Close the async HTTP client."""
        if hasattr(self._client, "close"):
            result = self._client.close()
            if hasattr(result, "__await__"):
                await result

    async def __aenter__(self) -> AsyncAgentOS:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
