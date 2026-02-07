"""Tests for the local store (local_mode)."""

from __future__ import annotations

import pytest

from agent_os.client import AgentOS
from agent_os.exceptions import NotFoundError


class TestLocalStoreBasics:
    def test_register_agent(self, aos_local):
        agent = aos_local.register_agent(
            name="test-agent",
            category="research",
            capabilities=["web_research"],
        )
        assert agent.id.startswith("agt_")
        assert agent.name == "test-agent"
        assert agent.reputation_score == 50.0
        assert agent.trust_tier == "Unverified"

    def test_get_agent(self, aos_local):
        agent = aos_local.register_agent(
            name="stored-agent",
            category="coding",
            capabilities=["python"],
        )
        retrieved = aos_local.get_agent(agent.id)
        assert retrieved.id == agent.id
        assert retrieved.name == "stored-agent"

    def test_get_nonexistent_agent(self, aos_local):
        with pytest.raises(NotFoundError):
            aos_local.get_agent("agt_doesnotexist")

    def test_update_agent(self, aos_local):
        agent = aos_local.register_agent(
            name="updatable",
            category="research",
            capabilities=["test"],
        )
        profile = aos_local.update_agent(agent.id, description="Updated description")
        assert profile.description == "Updated description"

    def test_lookup(self, aos_local):
        agent = aos_local.register_agent(
            name="public-agent",
            category="general",
            capabilities=["chat"],
        )
        profile = aos_local.lookup(agent.id)
        assert profile.agent_id == agent.id
        assert profile.name == "public-agent"

    def test_list_my_agents(self, aos_local):
        aos_local.register_agent(name="agent-one", category="research", capabilities=["test"])
        aos_local.register_agent(name="agent-two", category="coding", capabilities=["test"])
        agents = aos_local.list_my_agents()
        assert len(agents) == 2


class TestLocalStoreActions:
    def test_log_action_success(self, sample_local_agent):
        with sample_local_agent.action(task_category="research") as act:
            act.success(output={"data": "result"}, confidence=0.85, cost_usd=0.02)

        assert act.action_id is not None
        assert act.action_id.startswith("act_")
        assert act.duration_ms is not None

    def test_log_action_failure(self, sample_local_agent):
        with sample_local_agent.action(task_category="coding") as act:
            act.fail(error_type="timeout", error_message="Timed out")

        assert act.action_id is not None

    def test_get_actions(self, sample_local_agent):
        with sample_local_agent.action(task_category="research") as act:
            act.success(output="done")

        actions = sample_local_agent.get_actions()
        assert len(actions) == 1
        assert actions[0].status == "success"

    def test_actions_update_stats(self, sample_local_agent):
        for i in range(5):
            with sample_local_agent.action(task_category="research") as act:
                act.success(output=f"result-{i}", confidence=0.9, cost_usd=0.01)

        sample_local_agent.refresh()
        assert sample_local_agent.total_actions == 5
        assert sample_local_agent.success_rate > 0

    def test_manual_log_action(self, sample_local_agent):
        response = sample_local_agent.log_action(
            action_type="task_execution",
            status="success",
            task_category="data_analysis",
        )
        assert response.action_id.startswith("act_")
        assert response.status == "success"


class TestLocalStoreReputation:
    def test_initial_reputation(self, sample_local_agent):
        assert sample_local_agent.reputation_score == 50.0
        assert sample_local_agent.trust_tier == "Unverified"

    def test_reputation_improves_with_successes(self, sample_local_agent):
        for i in range(20):
            with sample_local_agent.action(task_category="research") as act:
                act.success(
                    output=f"result-{i}",
                    confidence=0.9,
                    cost_usd=0.01,
                )

        sample_local_agent.refresh()
        assert sample_local_agent.reputation_score > 50.0

    def test_reputation_breakdown_dimensions(self, sample_local_agent):
        for i in range(10):
            with sample_local_agent.action(task_category="research") as act:
                act.success(output=f"result-{i}", confidence=0.85, cost_usd=0.02)

        sample_local_agent.refresh()
        breakdown = sample_local_agent.reputation_breakdown()
        assert breakdown.reliability > 50.0
        assert breakdown.safety == 100.0  # No incidents
        assert breakdown.transparency > 0

    def test_trust_tier_progression(self, aos_local):
        """Test that tiers change based on score."""
        agent = aos_local.register_agent(
            name="tier-test",
            category="research",
            capabilities=["test"],
        )

        # Log many successful actions to push score up
        for i in range(50):
            with agent.action(task_category="research") as act:
                act.success(output=f"result-{i}", confidence=0.95, cost_usd=0.01)

        agent.refresh()
        # Score should be well above 50 with all successes
        assert agent.reputation_score > 60

    def test_incidents_reduce_safety(self, aos_local):
        agent = aos_local.register_agent(
            name="incident-test",
            category="research",
            capabilities=["test"],
        )

        # Log some actions first
        for i in range(5):
            with agent.action(task_category="research") as act:
                act.success(output=f"result-{i}")

        # Report an incident
        aos_local.report_incident(
            agent_id=agent.id,
            incident_type="hallucination",
            severity="high",
            title="Agent hallucinated facts about a topic",
            description="The agent produced completely fabricated information.",
        )

        agent.refresh()
        breakdown = agent.reputation_breakdown()
        assert breakdown.safety < 100.0  # Safety should decrease

    def test_reputation_history(self, sample_local_agent):
        with sample_local_agent.action(task_category="research") as act:
            act.success(output="data")

        history = sample_local_agent.reputation_history(days=30)
        assert len(history) >= 1
        assert history[0].overall_score > 0

    def test_efficiency_category_comparison(self, aos_local):
        """Test that efficiency compares against category avg."""
        # Register two agents in the same category
        cheap_agent = aos_local.register_agent(
            name="cheap-agent", category="research", capabilities=["test"]
        )
        expensive_agent = aos_local.register_agent(
            name="expensive-agent", category="research", capabilities=["test"]
        )

        # Cheap agent: low cost
        for i in range(10):
            with cheap_agent.action(task_category="research") as act:
                act.success(output=f"r-{i}", confidence=0.9, cost_usd=0.01)

        # Expensive agent: high cost
        for i in range(10):
            with expensive_agent.action(task_category="research") as act:
                act.success(output=f"r-{i}", confidence=0.9, cost_usd=1.00)

        cheap_agent.refresh()
        expensive_agent.refresh()

        cheap_eff = cheap_agent.reputation_breakdown().efficiency
        expensive_eff = expensive_agent.reputation_breakdown().efficiency

        assert cheap_eff > expensive_eff


class TestLocalStoreSearch:
    def test_search_agents(self, aos_local):
        aos_local.register_agent(
            name="search-agent-1", category="research", capabilities=["test"]
        )
        aos_local.register_agent(
            name="search-agent-2", category="coding", capabilities=["python"]
        )

        results = aos_local.search_agents(category="research")
        assert results.total >= 1
        assert all(a.category == "research" for a in results.agents)

    def test_leaderboard(self, aos_local):
        for i in range(3):
            aos_local.register_agent(
                name=f"leader-{i}", category="research", capabilities=["test"]
            )

        leaders = aos_local.get_leaderboard()
        assert len(leaders) == 3

    def test_ecosystem_stats(self, aos_local):
        aos_local.register_agent(
            name="stats-agent", category="research", capabilities=["test"]
        )
        stats = aos_local.get_ecosystem_stats()
        assert stats.total_agents >= 1


class TestLocalStoreIncidents:
    def test_report_incident(self, aos_local):
        agent = aos_local.register_agent(
            name="incident-agent", category="general", capabilities=["chat"]
        )
        response = aos_local.report_incident(
            agent_id=agent.id,
            incident_type="hallucination",
            severity="medium",
            title="Agent produced incorrect information",
            description="The agent hallucinated facts during a research task.",
        )
        assert response.incident_id.startswith("inc_")
        assert response.severity == "medium"

    def test_get_agent_incidents(self, aos_local):
        agent = aos_local.register_agent(
            name="inc-check-agent", category="general", capabilities=["chat"]
        )
        aos_local.report_incident(
            agent_id=agent.id,
            incident_type="data_leak",
            severity="critical",
            title="Agent exposed sensitive user data",
            description="PII was included in the agent's public output.",
        )

        retrieved = aos_local.get_agent(agent.id)
        incidents = retrieved.get_incidents()
        assert len(incidents) == 1
        assert incidents[0].severity == "critical"
