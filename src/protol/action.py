"""Action context manager for logging agent actions.

The Action class automatically captures timing, status, and hashed I/O
for every operation an agent performs.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any, Optional, Union

from protol._utils import calculate_size_bytes, hash_data
from protol.exceptions import ActionError
from protol.models import ActionRecord, ActionResponse

logger = logging.getLogger("protol")


class Action:
    """Context manager for logging agent actions.

    Automatically captures start/end time, duration, and status.
    Supports both sync and async context managers.

    Usage::

        with agent.action(task_category="research") as act:
            result = my_function(data)
            act.success(output=result, confidence=0.9)

        # Async:
        async with agent.action(task_category="research") as act:
            result = await my_async_function(data)
            act.success(output=result)

    If an exception occurs and success()/fail() was not called, the action is
    automatically recorded as 'error'. If the block exits cleanly without an
    explicit call, it is recorded as 'success' with a warning.
    """

    def __init__(
        self,
        client: Any,
        agent_id: str,
        action_type: str = "task_execution",
        task_category: Optional[str] = None,
        commissioned_by: Optional[str] = None,
        commissioner_type: Optional[str] = None,
        description: Optional[str] = None,
        environment: str = "production",
    ) -> None:
        self._client = client
        self._agent_id = agent_id
        self._action_type = action_type
        self._task_category = task_category
        self._commissioned_by = commissioned_by
        self._commissioner_type = commissioner_type
        self._description = description
        self._environment = environment
        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None
        self._status: Optional[str] = None
        self._recorded: bool = False
        self._action_response: Optional[ActionResponse] = None
        self._post_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Sync context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> Action:
        self._started_at = datetime.now(timezone.utc)
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Any,
    ) -> bool:
        self._completed_at = datetime.now(timezone.utc)

        if self._recorded:
            return False

        if exc_type is not None:
            self._safe_record(
                status="error",
                error_type="unknown",
                error_message=f"{exc_type.__name__}: {exc_val}",
            )
            return False  # Don't suppress the exception

        # Neither success() nor fail() was called, no exception
        logger.warning(
            "Action for agent %s exited without explicit success()/fail() call. "
            "Recording as success.",
            self._agent_id,
        )
        self._safe_record(status="success")
        return False

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> Action:
        self._started_at = datetime.now(timezone.utc)
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Any,
    ) -> bool:
        self._completed_at = datetime.now(timezone.utc)

        if self._recorded:
            return False

        if exc_type is not None:
            await self._async_safe_record(
                status="error",
                error_type="unknown",
                error_message=f"{exc_type.__name__}: {exc_val}",
            )
            return False

        logger.warning(
            "Action for agent %s exited without explicit success()/fail() call. "
            "Recording as success.",
            self._agent_id,
        )
        await self._async_safe_record(status="success")
        return False

    # ------------------------------------------------------------------
    # Public recording methods
    # ------------------------------------------------------------------

    def success(
        self,
        output: Any = None,
        confidence: Optional[float] = None,
        cost_usd: Optional[float] = None,
        payment_usd: Optional[float] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ActionResponse:
        """Record the action as successful.

        Args:
            output: The output data (will be hashed, NOT stored).
            confidence: Agent's self-reported confidence (0.0-1.0).
            cost_usd: Cost of this action (API costs, compute).
            payment_usd: Payment received for this action.
            metadata: Additional metadata.

        Returns:
            ActionResponse from the API.

        Raises:
            ActionError: If success()/fail() was already called.
        """
        self._guard_duplicate()
        if self._completed_at is None:
            self._completed_at = datetime.now(timezone.utc)

        output_hash = hash_data(output) if output is not None else None
        output_size = calculate_size_bytes(output) if output is not None else None

        return self._record(
            status="success",
            output_hash=output_hash,
            output_size_bytes=output_size,
            self_reported_confidence=confidence,
            cost_usd=cost_usd,
            payment_usd=payment_usd,
        )

    def fail(
        self,
        error_type: str = "unknown",
        error_message: Optional[str] = None,
        cost_usd: Optional[float] = None,
    ) -> ActionResponse:
        """Record the action as failed.

        Args:
            error_type: Type of error (from VALID_ERROR_TYPES).
            error_message: Human-readable error description.
            cost_usd: Cost incurred despite failure.

        Returns:
            ActionResponse from the API.
        """
        self._guard_duplicate()
        if self._completed_at is None:
            self._completed_at = datetime.now(timezone.utc)

        return self._record(
            status="failed",
            error_type=error_type,
            error_message=error_message,
            cost_usd=cost_usd,
        )

    def partial(
        self,
        output: Any = None,
        confidence: Optional[float] = None,
        cost_usd: Optional[float] = None,
        error_message: Optional[str] = None,
    ) -> ActionResponse:
        """Record the action as partially successful.

        Returns:
            ActionResponse from the API.
        """
        self._guard_duplicate()
        if self._completed_at is None:
            self._completed_at = datetime.now(timezone.utc)

        output_hash = hash_data(output) if output is not None else None
        output_size = calculate_size_bytes(output) if output is not None else None

        return self._record(
            status="partial",
            output_hash=output_hash,
            output_size_bytes=output_size,
            self_reported_confidence=confidence,
            cost_usd=cost_usd,
            error_message=error_message,
        )

    def rate(
        self,
        rating: int,
        feedback: Optional[str] = None,
    ) -> ActionResponse:
        """Rate this action (when YOU commissioned another agent).

        Args:
            rating: 1-5 star rating.
            feedback: Optional text feedback.

        Returns:
            Updated ActionResponse.

        Raises:
            ActionError: If the action hasn't been recorded yet.
        """
        if self._action_response is None:
            raise ActionError(
                message="Cannot rate an action that hasn't been recorded yet."
            )

        from protol.models import ActionRating

        ActionRating(rating=rating, feedback=feedback)  # Validate

        data = self._client.patch(
            f"/agents/{self._agent_id}/actions/{self._action_response.action_id}",
            json={"rating": rating, "feedback": feedback},
        )
        self._action_response = ActionResponse.model_validate(data)
        return self._action_response

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def action_id(self) -> Optional[str]:
        """The action ID (available after recording)."""
        return self._action_response.action_id if self._action_response else None

    @property
    def duration_ms(self) -> Optional[int]:
        """Duration in milliseconds (available after recording)."""
        if self._started_at and self._completed_at:
            return int(
                (self._completed_at - self._started_at).total_seconds() * 1000
            )
        return None

    @property
    def response(self) -> Optional[ActionResponse]:
        """The full ActionResponse (available after recording)."""
        return self._action_response

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _guard_duplicate(self) -> None:
        if self._recorded:
            raise ActionError(
                message="Action already recorded. Cannot call success()/fail()/partial() twice."
            )

    def _build_payload(self, **kwargs: Any) -> dict[str, Any]:
        """Build the action record payload."""
        started = self._started_at or datetime.now(timezone.utc)
        completed = self._completed_at

        duration = None
        if started and completed:
            duration = int((completed - started).total_seconds() * 1000)

        record = ActionRecord(
            agent_id=self._agent_id,
            action_type=self._action_type,
            task_category=self._task_category,
            description=self._description,
            commissioned_by=self._commissioned_by,
            commissioner_type=self._commissioner_type,
            status=kwargs.get("status", "success"),
            started_at=started,
            completed_at=completed,
            duration_ms=duration,
            input_hash=kwargs.get("input_hash"),
            output_hash=kwargs.get("output_hash"),
            input_size_bytes=kwargs.get("input_size_bytes"),
            output_size_bytes=kwargs.get("output_size_bytes"),
            cost_usd=kwargs.get("cost_usd"),
            payment_usd=kwargs.get("payment_usd"),
            self_reported_confidence=kwargs.get("self_reported_confidence"),
            error_type=kwargs.get("error_type"),
            error_message=kwargs.get("error_message"),
            environment=self._environment,
        )

        return record.model_dump(mode="json", exclude_none=True)

    def _record(self, **kwargs: Any) -> ActionResponse:
        """Record the action synchronously (may use background thread)."""
        self._recorded = True
        payload = self._build_payload(**kwargs)

        try:
            # For local_mode (LocalStore) we post synchronously as it's instant
            from protol._local_store import LocalStore

            if isinstance(self._client, LocalStore):
                data = self._client.post(
                    f"/agents/{self._agent_id}/actions", json=payload
                )
                self._action_response = ActionResponse.model_validate(data)
                logger.info(
                    "Action %s recorded for agent %s [%s]",
                    self._action_response.action_id,
                    self._agent_id,
                    kwargs.get("status", "success"),
                )
                return self._action_response
        except ImportError:
            pass

        # For HTTP mode, try background thread for performance
        try:
            result_holder: dict[str, Any] = {}

            def _post() -> None:
                try:
                    data = self._client.post(
                        f"/agents/{self._agent_id}/actions", json=payload
                    )
                    result_holder["data"] = data
                except Exception as exc:
                    logger.error(
                        "Failed to record action for agent %s: %s",
                        self._agent_id,
                        exc,
                    )
                    result_holder["error"] = exc

            thread = threading.Thread(target=_post, daemon=True)
            self._post_thread = thread
            thread.start()
            # Wait briefly to allow quick responses (e.g. from mock/local)
            thread.join(timeout=5.0)

            if "data" in result_holder:
                self._action_response = ActionResponse.model_validate(
                    result_holder["data"]
                )
                logger.info(
                    "Action %s recorded for agent %s [%s]",
                    self._action_response.action_id,
                    self._agent_id,
                    kwargs.get("status", "success"),
                )
                return self._action_response
            elif "error" in result_holder:
                logger.warning(
                    "Action recording failed for agent %s, but user code continues: %s",
                    self._agent_id,
                    result_holder["error"],
                )
                return self._make_stub_response(kwargs.get("status", "success"))
            else:
                # Thread still running — return stub, thread will complete in background
                logger.debug(
                    "Action post still in progress for agent %s, returning stub.",
                    self._agent_id,
                )
                return self._make_stub_response(kwargs.get("status", "success"))

        except Exception as exc:
            # Fallback: synchronous post
            logger.warning(
                "Background thread failed, falling back to sync post: %s", exc
            )
            return self._sync_post(payload, kwargs.get("status", "success"))

    def _sync_post(self, payload: dict[str, Any], status: str) -> ActionResponse:
        """Synchronous fallback for recording."""
        try:
            data = self._client.post(
                f"/agents/{self._agent_id}/actions", json=payload
            )
            self._action_response = ActionResponse.model_validate(data)
            return self._action_response
        except Exception as exc:
            logger.error(
                "Sync action recording failed for agent %s: %s",
                self._agent_id,
                exc,
            )
            return self._make_stub_response(status)

    def _make_stub_response(self, status: str) -> ActionResponse:
        """Create a stub ActionResponse when the API call fails."""
        now = datetime.now(timezone.utc)
        stub = ActionResponse(
            action_id="act_pending",
            agent_id=self._agent_id,
            action_type=self._action_type,
            status=status,
            started_at=self._started_at or now,
            completed_at=self._completed_at or now,
            verified=False,
            environment=self._environment,
            recorded_at=now,
        )
        self._action_response = stub
        return stub

    def _safe_record(self, **kwargs: Any) -> None:
        """Record without raising — for use in __exit__."""
        try:
            self._record(**kwargs)
        except Exception as exc:
            logger.error(
                "Failed to record action in __exit__ for agent %s: %s",
                self._agent_id,
                exc,
            )
            self._recorded = True

    async def _async_record(self, **kwargs: Any) -> ActionResponse:
        """Record the action asynchronously."""
        self._recorded = True
        payload = self._build_payload(**kwargs)

        try:
            # Check if client is async
            if hasattr(self._client, "post") and not hasattr(
                self._client.post, "__self__"
            ):
                import asyncio

                data = await self._client.post(
                    f"/agents/{self._agent_id}/actions", json=payload
                )
            else:
                data = self._client.post(
                    f"/agents/{self._agent_id}/actions", json=payload
                )

            self._action_response = ActionResponse.model_validate(data)
            logger.info(
                "Action %s recorded for agent %s [%s]",
                self._action_response.action_id,
                self._agent_id,
                kwargs.get("status", "success"),
            )
            return self._action_response
        except Exception as exc:
            logger.error(
                "Async action recording failed for agent %s: %s",
                self._agent_id,
                exc,
            )
            return self._make_stub_response(kwargs.get("status", "success"))

    async def _async_safe_record(self, **kwargs: Any) -> None:
        """Async record without raising — for use in __aexit__."""
        try:
            await self._async_record(**kwargs)
        except Exception as exc:
            logger.error(
                "Failed to record action in __aexit__ for agent %s: %s",
                self._agent_id,
                exc,
            )
            self._recorded = True

    async def async_success(
        self,
        output: Any = None,
        confidence: Optional[float] = None,
        cost_usd: Optional[float] = None,
        payment_usd: Optional[float] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ActionResponse:
        """Async version of success()."""
        self._guard_duplicate()
        if self._completed_at is None:
            self._completed_at = datetime.now(timezone.utc)

        output_hash = hash_data(output) if output is not None else None
        output_size = calculate_size_bytes(output) if output is not None else None

        return await self._async_record(
            status="success",
            output_hash=output_hash,
            output_size_bytes=output_size,
            self_reported_confidence=confidence,
            cost_usd=cost_usd,
            payment_usd=payment_usd,
        )

    async def async_fail(
        self,
        error_type: str = "unknown",
        error_message: Optional[str] = None,
        cost_usd: Optional[float] = None,
    ) -> ActionResponse:
        """Async version of fail()."""
        self._guard_duplicate()
        if self._completed_at is None:
            self._completed_at = datetime.now(timezone.utc)

        return await self._async_record(
            status="failed",
            error_type=error_type,
            error_message=error_message,
            cost_usd=cost_usd,
        )

    async def async_partial(
        self,
        output: Any = None,
        confidence: Optional[float] = None,
        cost_usd: Optional[float] = None,
        error_message: Optional[str] = None,
    ) -> ActionResponse:
        """Async version of partial()."""
        self._guard_duplicate()
        if self._completed_at is None:
            self._completed_at = datetime.now(timezone.utc)

        output_hash = hash_data(output) if output is not None else None
        output_size = calculate_size_bytes(output) if output is not None else None

        return await self._async_record(
            status="partial",
            output_hash=output_hash,
            output_size_bytes=output_size,
            self_reported_confidence=confidence,
            cost_usd=cost_usd,
            error_message=error_message,
        )
