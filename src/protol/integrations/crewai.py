"""CrewAI integration for the Protol SDK.

Wraps a CrewAI Crew with automatic action logging for all crew members.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from protol.agent import Agent

logger = logging.getLogger("protol")

try:
    from crewai import Crew  # type: ignore[import-untyped]
except ImportError:
    Crew = None  # type: ignore[assignment,misc]

_MISSING_MSG = (
    "CrewAI integration requires crewai. "
    "Install it with: pip install 'protol-sdk[crewai]'"
)


class CrewAIWrapper:
    """Wraps a CrewAI Crew with automatic Protol action logging for all crew members.

    Usage::

        from protol.integrations import CrewAIWrapper

        tracked_crew = CrewAIWrapper(
            crew=my_crew,
            agent_mapping={
                "researcher": researcher_aos_agent,
                "writer": writer_aos_agent,
            }
        )

        result = tracked_crew.kickoff()
        # All agent actions within the crew are individually tracked
    """

    def __init__(
        self,
        crew: Any,
        agent_mapping: Dict[str, Agent],
        environment: Optional[str] = None,
    ) -> None:
        """Initialize the CrewAI wrapper.

        Args:
            crew: CrewAI Crew instance.
            agent_mapping: Mapping of CrewAI agent role names to Protol Agent instances.
            environment: Override the default environment.
        """
        if Crew is None:
            raise ImportError(_MISSING_MSG)
        self._crew = crew
        self._agent_mapping = agent_mapping
        self._environment = environment

    def kickoff(self, inputs: Optional[Dict[str, Any]] = None) -> Any:
        """Run the crew and log all agent actions.

        Each task in the crew is logged as an action for the corresponding
        Protol agent (matched by role name in agent_mapping).

        Args:
            inputs: Optional inputs dict to pass to the crew.

        Returns:
            The original result from the crew.
        """
        # Log a top-level action for each mapped agent
        actions = {}
        for role, aos_agent in self._agent_mapping.items():
            action = aos_agent.action(
                action_type="task_execution",
                task_category="crew_task",
                description=f"CrewAI crew execution (role: {role})",
                environment=self._environment,
            )
            action.__enter__()
            actions[role] = action

        try:
            if inputs:
                result = self._crew.kickoff(inputs=inputs)
            else:
                result = self._crew.kickoff()

            # Mark all actions as successful
            for role, action in actions.items():
                try:
                    action.success(output=result)
                except Exception as exc:
                    logger.warning(
                        "Failed to record success for role '%s': %s", role, exc
                    )
                action.__exit__(None, None, None)

            return result

        except Exception as exc:
            # Mark all actions as failed
            for role, action in actions.items():
                try:
                    action.fail(
                        error_type="api_failure",
                        error_message=f"{type(exc).__name__}: {exc}",
                    )
                except Exception:
                    pass
                action.__exit__(type(exc), exc, exc.__traceback__)
            raise
