"""Tests for the Action context manager."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from protol.action import Action
from protol.exceptions import ActionError


class TestActionContextManager:
    def test_records_start_time(self, sample_local_agent):
        with sample_local_agent.action(task_category="research") as act:
            assert act._started_at is not None
            act.success(output="done")

    def test_success_records_correctly(self, sample_local_agent):
        with sample_local_agent.action(task_category="research") as act:
            act.success(output={"findings": "test"}, confidence=0.87, cost_usd=0.03)

        assert act.action_id is not None
        assert act.duration_ms is not None
        assert act.duration_ms >= 0
        assert act._status is None or act._recorded is True

    def test_fail_records_error(self, sample_local_agent):
        with sample_local_agent.action(task_category="coding") as act:
            act.fail(error_type="timeout", error_message="Connection timed out")

        assert act.action_id is not None
        assert act._recorded is True

    def test_partial_records(self, sample_local_agent):
        with sample_local_agent.action(task_category="research") as act:
            act.partial(
                output="partial result",
                confidence=0.5,
                error_message="Incomplete",
            )

        assert act.action_id is not None

    def test_auto_error_on_exception(self, sample_local_agent):
        with pytest.raises(ValueError, match="intentional"):
            with sample_local_agent.action(task_category="coding") as act:
                raise ValueError("intentional error")

        # Action should have been recorded as error
        assert act._recorded is True
        assert act.action_id is not None

    def test_auto_success_when_no_explicit_call(self, sample_local_agent):
        with sample_local_agent.action(task_category="research") as act:
            _ = "some work"
            # No explicit success()/fail() call

        # Should auto-record as success
        assert act._recorded is True
        assert act.action_id is not None

    def test_duplicate_success_raises(self, sample_local_agent):
        with sample_local_agent.action(task_category="research") as act:
            act.success(output="first")
            with pytest.raises(ActionError, match="already recorded"):
                act.success(output="second")

    def test_duplicate_fail_raises(self, sample_local_agent):
        with sample_local_agent.action(task_category="research") as act:
            act.fail(error_type="timeout")
            with pytest.raises(ActionError, match="already recorded"):
                act.fail(error_type="unknown")

    def test_success_then_fail_raises(self, sample_local_agent):
        with sample_local_agent.action(task_category="research") as act:
            act.success(output="data")
            with pytest.raises(ActionError):
                act.fail()

    def test_duration_calculation(self, sample_local_agent):
        import time

        with sample_local_agent.action(task_category="research") as act:
            time.sleep(0.05)  # 50ms
            act.success(output="done")

        assert act.duration_ms is not None
        assert act.duration_ms >= 40  # At least ~40ms (allowing for timing variance)

    def test_rate_action(self, sample_local_agent):
        with sample_local_agent.action(task_category="research") as act:
            act.success(output="result")

        rated = act.rate(rating=5, feedback="Excellent work")
        assert rated is not None

    def test_rate_before_record_raises(self, sample_local_agent):
        act = sample_local_agent.action(task_category="research")
        with pytest.raises(ActionError, match="hasn't been recorded"):
            act.rate(rating=5)

    def test_action_response_property(self, sample_local_agent):
        with sample_local_agent.action(task_category="research") as act:
            act.success(output="data")

        assert act.response is not None
        assert act.response.action_id == act.action_id

    def test_environment_override(self, sample_local_agent):
        with sample_local_agent.action(
            task_category="research", environment="test"
        ) as act:
            act.success(output="test data")

        assert act.response is not None
        assert act.response.environment == "test"

    def test_hashes_output_never_raw(self, sample_local_agent):
        sensitive_data = {"secret": "super-secret-value", "api_key": "sk_12345"}
        with sample_local_agent.action(task_category="research") as act:
            act.success(output=sensitive_data, confidence=0.9)

        # The response should not contain raw data — only hashes
        response = act.response
        assert response is not None
        # Action response from local store shouldn't have raw secret data
        response_dict = response.model_dump()
        response_str = str(response_dict)
        assert "super-secret-value" not in response_str
        assert "sk_12345" not in response_str


class TestActionAsync:
    @pytest.mark.asyncio
    async def test_async_context_manager(self, sample_local_agent):
        async with sample_local_agent.action(task_category="research") as act:
            act.success(output="async result")

        assert act._recorded is True
        assert act.action_id is not None

    @pytest.mark.asyncio
    async def test_async_auto_error_on_exception(self, sample_local_agent):
        with pytest.raises(RuntimeError, match="async error"):
            async with sample_local_agent.action(task_category="coding") as act:
                raise RuntimeError("async error")

        assert act._recorded is True
