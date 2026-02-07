"""LangChain integration for the AgentOS SDK.

Wraps any LangChain Runnable with automatic action logging.
"""

from __future__ import annotations

import logging
from typing import Any, Iterator, Optional

from agent_os._utils import calculate_size_bytes, hash_data
from agent_os.agent import Agent

logger = logging.getLogger("agent_os")

try:
    from langchain_core.runnables import Runnable  # type: ignore[import-untyped]
except ImportError:
    Runnable = None  # type: ignore[assignment,misc]

_MISSING_MSG = (
    "LangChain integration requires langchain-core. "
    "Install it with: pip install 'agent-os-sdk[langchain]'"
)


class LangChainWrapper:
    """Wraps any LangChain Runnable/Agent with automatic AgentOS action logging.

    Usage::

        from agent_os.integrations import LangChainWrapper

        tracked = LangChainWrapper(
            runnable=my_langchain_agent,
            agent=my_aos_agent,
            task_category="research",
        )

        # Use exactly like a normal LangChain runnable
        result = tracked.invoke("What is quantum computing?")
        # Action is automatically logged with input/output hashes, timing, status
    """

    def __init__(
        self,
        runnable: Any,
        agent: Agent,
        task_category: Optional[str] = None,
        commissioned_by: Optional[str] = None,
        environment: Optional[str] = None,
    ) -> None:
        """Initialize the LangChain wrapper.

        Args:
            runnable: Any LangChain Runnable (chain, agent, LLM, etc.).
            agent: AgentOS Agent instance.
            task_category: Default task category for logged actions.
            commissioned_by: Who commissioned the work.
            environment: Override the agent's default environment.
        """
        if Runnable is None:
            raise ImportError(_MISSING_MSG)
        self._runnable = runnable
        self._agent = agent
        self._task_category = task_category
        self._commissioned_by = commissioned_by
        self._environment = environment

    def invoke(self, input: Any, **kwargs: Any) -> Any:
        """Run the LangChain runnable and log the action.

        Args:
            input: Input data for the runnable.
            **kwargs: Additional keyword arguments passed to the runnable.

        Returns:
            The original result from the runnable.
        """
        with self._agent.action(
            action_type="task_execution",
            task_category=self._task_category,
            commissioned_by=self._commissioned_by,
            description=f"LangChain invoke: {type(self._runnable).__name__}",
            environment=self._environment,
        ) as act:
            try:
                result = self._runnable.invoke(input, **kwargs)
                act.success(output=result, confidence=None)
                return result
            except Exception as exc:
                act.fail(
                    error_type="api_failure",
                    error_message=f"{type(exc).__name__}: {exc}",
                )
                raise

    async def ainvoke(self, input: Any, **kwargs: Any) -> Any:
        """Async version of invoke.

        Args:
            input: Input data for the runnable.
            **kwargs: Additional keyword arguments.

        Returns:
            The original result from the runnable.
        """
        async with self._agent.action(
            action_type="task_execution",
            task_category=self._task_category,
            commissioned_by=self._commissioned_by,
            description=f"LangChain ainvoke: {type(self._runnable).__name__}",
            environment=self._environment,
        ) as act:
            try:
                result = await self._runnable.ainvoke(input, **kwargs)
                act.success(output=result, confidence=None)
                return result
            except Exception as exc:
                act.fail(
                    error_type="api_failure",
                    error_message=f"{type(exc).__name__}: {exc}",
                )
                raise

    def batch(self, inputs: list[Any], **kwargs: Any) -> list[Any]:
        """Run batch and log each invocation as a separate action.

        Args:
            inputs: List of inputs.
            **kwargs: Additional keyword arguments.

        Returns:
            List of results.
        """
        results = []
        for inp in inputs:
            result = self.invoke(inp, **kwargs)
            results.append(result)
        return results

    def stream(self, input: Any, **kwargs: Any) -> Iterator[Any]:
        """Stream the LangChain runnable.

        Logs action after stream completes. Yields chunks as they arrive.

        Args:
            input: Input data.
            **kwargs: Additional keyword arguments.

        Yields:
            Chunks from the runnable's stream.
        """
        chunks: list[Any] = []
        action = self._agent.action(
            action_type="task_execution",
            task_category=self._task_category,
            commissioned_by=self._commissioned_by,
            description=f"LangChain stream: {type(self._runnable).__name__}",
            environment=self._environment,
        )
        action.__enter__()

        try:
            for chunk in self._runnable.stream(input, **kwargs):
                chunks.append(chunk)
                yield chunk

            # Stream completed successfully
            action.success(output=chunks)
        except Exception as exc:
            action.fail(
                error_type="api_failure",
                error_message=f"{type(exc).__name__}: {exc}",
            )
            action.__exit__(type(exc), exc, exc.__traceback__)
            raise
        else:
            action.__exit__(None, None, None)
