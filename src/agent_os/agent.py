"""Agent class for the AgentOS SDK.

Represents a registered agent and provides action logging and reputation querying.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional, Union

from agent_os.action import Action
from agent_os.models import (
    ActionRecord,
    ActionResponse,
    AgentProfile,
    IncidentResponse,
    ReputationBreakdown,
    ReputationHistory,
)

logger = logging.getLogger("agent_os")


class Agent:
    """Represents a registered agent. Use this to log actions and query reputation.

    Created via ``AgentOS.register_agent()`` or ``AgentOS.get_agent()``.
    Do not instantiate directly.
    """

    def __init__(
        self,
        client: Any,
        profile: AgentProfile,
        default_environment: str = "production",
    ) -> None:
        self._client = client
        self._profile = profile
        self._default_environment = default_environment

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def id(self) -> str:
        """The agent's unique ID."""
        return self._profile.agent_id

    @property
    def name(self) -> str:
        """The agent's name."""
        return self._profile.name

    @property
    def reputation_score(self) -> float:
        """The agent's overall reputation score (0-100)."""
        return self._profile.reputation.overall_score

    @property
    def trust_tier(self) -> str:
        """The agent's trust tier."""
        return self._profile.reputation.trust_tier

    @property
    def total_actions(self) -> int:
        """Total number of actions logged by this agent."""
        return self._profile.stats.total_actions

    @property
    def success_rate(self) -> float:
        """Action success rate (0-100)."""
        return self._profile.stats.success_rate

    @property
    def profile(self) -> AgentProfile:
        """Full agent profile."""
        return self._profile

    # ------------------------------------------------------------------
    # Core methods
    # ------------------------------------------------------------------

    def refresh(self) -> Agent:
        """Refresh the agent's profile data from the API.

        Returns:
            Self, with updated profile data.
        """
        data = self._client.get(f"/agents/{self.id}")
        self._profile = AgentProfile.model_validate(data)
        return self

    def action(
        self,
        action_type: str = "task_execution",
        task_category: Optional[str] = None,
        commissioned_by: Optional[str] = None,
        commissioner_type: Optional[str] = None,
        description: Optional[str] = None,
        environment: Optional[str] = None,
    ) -> Action:
        """Create an action context manager for logging.

        Usage::

            with agent.action(task_category="research") as act:
                result = my_agent.run(query)
                act.success(output=result, confidence=0.9)

        Args:
            action_type: Type of action (default: 'task_execution').
            task_category: Category of the task.
            commissioned_by: Who commissioned this action.
            commissioner_type: 'agent' or 'human'.
            description: Human-readable description.
            environment: Override the default environment ('production'/'staging'/'test').

        Returns:
            Action context manager.
        """
        return Action(
            client=self._client,
            agent_id=self.id,
            action_type=action_type,
            task_category=task_category,
            commissioned_by=commissioned_by,
            commissioner_type=commissioner_type,
            description=description,
            environment=environment or self._default_environment,
        )

    def log_action(
        self,
        action_type: str,
        status: str,
        task_category: Optional[str] = None,
        description: Optional[str] = None,
        commissioned_by: Optional[str] = None,
        commissioner_type: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        duration_ms: Optional[int] = None,
        input_hash: Optional[str] = None,
        output_hash: Optional[str] = None,
        input_size_bytes: Optional[int] = None,
        output_size_bytes: Optional[int] = None,
        cost_usd: Optional[float] = None,
        payment_usd: Optional[float] = None,
        self_reported_confidence: Optional[float] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        environment: Optional[str] = None,
    ) -> ActionResponse:
        """Manually log a completed action without using the context manager.

        Useful for retroactive logging or custom workflows.

        Returns:
            ActionResponse from the API.
        """
        now = datetime.now(timezone.utc)
        record = ActionRecord(
            agent_id=self.id,
            action_type=action_type,
            task_category=task_category,
            description=description,
            commissioned_by=commissioned_by,
            commissioner_type=commissioner_type,
            status=status,
            started_at=started_at or now,
            completed_at=completed_at or now,
            duration_ms=duration_ms,
            input_hash=input_hash,
            output_hash=output_hash,
            input_size_bytes=input_size_bytes,
            output_size_bytes=output_size_bytes,
            cost_usd=cost_usd,
            payment_usd=payment_usd,
            self_reported_confidence=self_reported_confidence,
            error_type=error_type,
            error_message=error_message,
            environment=environment or self._default_environment,
        )

        payload = record.model_dump(mode="json", exclude_none=True)
        data = self._client.post(f"/agents/{self.id}/actions", json=payload)
        return ActionResponse.model_validate(data)

    def get_actions(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        task_category: Optional[str] = None,
    ) -> list[ActionResponse]:
        """Get this agent's action history.

        Args:
            limit: Maximum number of actions to return.
            offset: Number of actions to skip.
            status: Filter by status.
            task_category: Filter by task category.

        Returns:
            List of ActionResponse objects.
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        if task_category:
            params["task_category"] = task_category

        data = self._client.get(f"/agents/{self.id}/actions", params=params)

        if isinstance(data, list):
            return [ActionResponse.model_validate(item) for item in data]
        return []

    def reputation_breakdown(self) -> ReputationBreakdown:
        """Get detailed reputation breakdown.

        Returns:
            ReputationBreakdown with reliability, safety, consistency,
            efficiency, and transparency scores.
        """
        return self._profile.reputation.breakdown

    def reputation_history(self, days: int = 90) -> list[ReputationHistory]:
        """Get reputation score history over time.

        Args:
            days: Number of days of history to retrieve (default: 90).

        Returns:
            List of ReputationHistory snapshots.
        """
        data = self._client.get(
            f"/agents/{self.id}/reputation/history",
            params={"days": days},
        )

        if isinstance(data, list):
            return [ReputationHistory.model_validate(item) for item in data]
        return []

    def get_incidents(self) -> list[IncidentResponse]:
        """Get incidents reported against this agent.

        Returns:
            List of IncidentResponse objects.
        """
        data = self._client.get(f"/agents/{self.id}/incidents")
        if isinstance(data, list):
            return [IncidentResponse.model_validate(item) for item in data]
        return []

    def __repr__(self) -> str:
        return (
            f"Agent(id='{self.id}', name='{self.name}', "
            f"score={self.reputation_score}, tier='{self.trust_tier}')"
        )
