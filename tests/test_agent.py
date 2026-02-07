"""Tests for the Agent class."""

from __future__ import annotations

import pytest

from protol.agent import Agent
from protol.models import AgentProfile, ReputationBreakdown, ReputationHistory


class TestAgentProperties:
    def test_id(self, sample_local_agent):
        assert sample_local_agent.id.startswith("agt_")

    def test_name(self, sample_local_agent):
        assert sample_local_agent.name == "test-local-agent"

    def test_reputation_score(self, sample_local_agent):
        assert isinstance(sample_local_agent.reputation_score, float)

    def test_trust_tier(self, sample_local_agent):
        assert sample_local_agent.trust_tier in [
            "Unverified", "Bronze", "Silver", "Gold", "Platinum"
        ]

    def test_total_actions(self, sample_local_agent):
        assert sample_local_agent.total_actions == 0

    def test_success_rate(self, sample_local_agent):
        assert sample_local_agent.success_rate == 0.0

    def test_profile(self, sample_local_agent):
        assert isinstance(sample_local_agent.profile, AgentProfile)


class TestAgentMethods:
    def test_refresh(self, sample_local_agent):
        result = sample_local_agent.refresh()
        assert result is sample_local_agent
        assert result.id == sample_local_agent.id

    def test_action_returns_context_manager(self, sample_local_agent):
        from protol.action import Action

        action = sample_local_agent.action(task_category="research")
        assert isinstance(action, Action)

    def test_action_default_environment(self, aos_local):
        """Test that the agent's default environment flows to actions."""
        # Create a client with test environment
        test_client = AgentProfile  # We'll test through local mode
        agent = aos_local.register_agent(
            name="env-test",
            category="research",
            capabilities=["test"],
        )
        # The default env from aos_local is "production"
        action = agent.action(task_category="research")
        assert action._environment == "production"

    def test_action_environment_override(self, sample_local_agent):
        action = sample_local_agent.action(
            task_category="research", environment="test"
        )
        assert action._environment == "test"

    def test_log_action(self, sample_local_agent):
        response = sample_local_agent.log_action(
            action_type="task_execution",
            status="success",
            task_category="research",
            description="Manual log test",
        )
        assert response.status == "success"
        assert response.action_id.startswith("act_")

    def test_get_actions_empty(self, sample_local_agent):
        actions = sample_local_agent.get_actions()
        assert actions == []

    def test_get_actions_with_data(self, sample_local_agent):
        with sample_local_agent.action(task_category="research") as act:
            act.success(output="result")

        actions = sample_local_agent.get_actions()
        assert len(actions) == 1

    def test_get_actions_filter_by_status(self, sample_local_agent):
        with sample_local_agent.action(task_category="research") as act:
            act.success(output="r1")

        with sample_local_agent.action(task_category="coding") as act:
            act.fail(error_type="timeout")

        successes = sample_local_agent.get_actions(status="success")
        assert len(successes) == 1

    def test_reputation_breakdown(self, sample_local_agent):
        breakdown = sample_local_agent.reputation_breakdown()
        assert isinstance(breakdown, ReputationBreakdown)
        assert hasattr(breakdown, "reliability")
        assert hasattr(breakdown, "safety")
        assert hasattr(breakdown, "consistency")
        assert hasattr(breakdown, "efficiency")
        assert hasattr(breakdown, "transparency")

    def test_reputation_history(self, sample_local_agent):
        with sample_local_agent.action(task_category="research") as act:
            act.success(output="data")

        history = sample_local_agent.reputation_history(days=30)
        assert isinstance(history, list)
        assert len(history) >= 1

    def test_get_incidents_empty(self, sample_local_agent):
        incidents = sample_local_agent.get_incidents()
        assert incidents == []

    def test_repr(self, sample_local_agent):
        r = repr(sample_local_agent)
        assert "Agent(" in r
        assert sample_local_agent.id in r
        assert sample_local_agent.name in r
