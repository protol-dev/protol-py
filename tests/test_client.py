"""Tests for the AgentOS client."""

from __future__ import annotations

import pytest

from agent_os.client import AgentOS, AsyncAgentOS
from agent_os.exceptions import ValidationError, NotFoundError
from agent_os.models import AgentProfile, EcosystemStats, SearchResult


class TestAgentOSInit:
    def test_local_mode_accepts_any_key(self):
        aos = AgentOS(api_key="any_key", local_mode=True)
        assert aos._local_mode is True
        aos.close()

    def test_invalid_api_key_raises(self):
        with pytest.raises(ValidationError, match="Invalid API key"):
            AgentOS(api_key="bad_key")

    def test_valid_api_key_accepted(self, httpx_mock):
        # With a valid key format, should instantiate without error
        # (no actual HTTP call in constructor)
        aos = AgentOS(api_key="aos_sk_12345678901234567890")
        aos.close()

    def test_default_environment(self):
        aos = AgentOS(api_key="test", local_mode=True)
        assert aos._environment == "production"
        aos.close()

    def test_custom_environment(self):
        aos = AgentOS(api_key="test", local_mode=True, environment="staging")
        assert aos._environment == "staging"
        aos.close()


class TestAgentOSContextManager:
    def test_context_manager(self):
        with AgentOS(api_key="test", local_mode=True) as aos:
            agent = aos.register_agent(
                name="ctx-agent", category="research", capabilities=["test"]
            )
            assert agent.id.startswith("agt_")
        # Should not raise after close


class TestAgentOSRegister:
    def test_register_agent(self, aos_local):
        agent = aos_local.register_agent(
            name="my-agent",
            category="research",
            capabilities=["web_research", "summarization"],
            model_provider="anthropic",
            model_name="claude-3.5-sonnet",
            description="A test agent",
        )
        assert agent.id.startswith("agt_")
        assert agent.name == "my-agent"
        assert agent.trust_tier == "Unverified"

    def test_register_invalid_category(self, aos_local):
        with pytest.raises(Exception):  # ValidationError from Pydantic
            aos_local.register_agent(
                name="bad-agent",
                category="nonexistent",
                capabilities=["test"],
            )

    def test_register_empty_capabilities(self, aos_local):
        with pytest.raises(Exception):
            aos_local.register_agent(
                name="bad-agent",
                category="research",
                capabilities=[],
            )


class TestAgentOSGetAgent:
    def test_get_existing_agent(self, aos_local):
        created = aos_local.register_agent(
            name="existing", category="coding", capabilities=["python"]
        )
        retrieved = aos_local.get_agent(created.id)
        assert retrieved.id == created.id
        assert retrieved.name == "existing"

    def test_get_nonexistent_agent(self, aos_local):
        with pytest.raises(NotFoundError):
            aos_local.get_agent("agt_nonexistent")


class TestAgentOSUpdate:
    def test_update_agent(self, aos_local):
        agent = aos_local.register_agent(
            name="updatable", category="research", capabilities=["test"]
        )
        profile = aos_local.update_agent(agent.id, description="New description")
        assert profile.description == "New description"


class TestAgentOSLookup:
    def test_lookup_returns_profile(self, aos_local):
        agent = aos_local.register_agent(
            name="lookupable", category="general", capabilities=["chat"]
        )
        profile = aos_local.lookup(agent.id)
        assert isinstance(profile, AgentProfile)
        assert profile.agent_id == agent.id


class TestAgentOSSearch:
    def test_search_by_category(self, aos_local):
        aos_local.register_agent(
            name="search-r", category="research", capabilities=["test"]
        )
        aos_local.register_agent(
            name="search-c", category="coding", capabilities=["python"]
        )
        results = aos_local.search_agents(category="research")
        assert isinstance(results, SearchResult)
        assert all(a.category == "research" for a in results.agents)


class TestAgentOSLeaderboard:
    def test_leaderboard(self, aos_local):
        for i in range(3):
            aos_local.register_agent(
                name=f"leader-{i}", category="research", capabilities=["test"]
            )
        leaders = aos_local.get_leaderboard()
        assert len(leaders) == 3


class TestAgentOSEcosystemStats:
    def test_ecosystem_stats(self, aos_local):
        aos_local.register_agent(
            name="stats-agent", category="research", capabilities=["test"]
        )
        stats = aos_local.get_ecosystem_stats()
        assert isinstance(stats, EcosystemStats)
        assert stats.total_agents >= 1


class TestAgentOSReportIncident:
    def test_report_incident(self, aos_local):
        agent = aos_local.register_agent(
            name="inc-agent", category="general", capabilities=["chat"]
        )
        response = aos_local.report_incident(
            agent_id=agent.id,
            incident_type="hallucination",
            severity="medium",
            title="Agent produced incorrect information",
            description="The agent hallucinated details about a topic.",
        )
        assert response.incident_id.startswith("inc_")

    def test_report_incident_invalid_type(self, aos_local):
        agent = aos_local.register_agent(
            name="inc-agent-2", category="general", capabilities=["chat"]
        )
        with pytest.raises(Exception):
            aos_local.report_incident(
                agent_id=agent.id,
                incident_type="invalid_type",
                severity="low",
                title="Test incident for coverage",
                description="This tests invalid incident type validation.",
            )


class TestAgentOSListMyAgents:
    def test_list_empty(self, aos_local):
        agents = aos_local.list_my_agents()
        assert agents == []

    def test_list_with_agents(self, aos_local):
        aos_local.register_agent(name="list-1", category="research", capabilities=["test"])
        aos_local.register_agent(name="list-2", category="coding", capabilities=["test"])
        agents = aos_local.list_my_agents()
        assert len(agents) == 2


class TestEnvironmentPropagation:
    def test_environment_flows_to_agent(self):
        aos = AgentOS(api_key="test", local_mode=True, environment="test")
        agent = aos.register_agent(
            name="env-agent", category="research", capabilities=["test"]
        )
        # Action should default to "test" environment
        action = agent.action(task_category="research")
        assert action._environment == "test"
        aos.close()

    def test_environment_overridable_per_action(self):
        aos = AgentOS(api_key="test", local_mode=True, environment="production")
        agent = aos.register_agent(
            name="env-agent-2", category="research", capabilities=["test"]
        )
        action = agent.action(task_category="research", environment="staging")
        assert action._environment == "staging"
        aos.close()


class TestAsyncAgentOS:
    @pytest.mark.asyncio
    async def test_async_local_mode(self):
        async with AsyncAgentOS(api_key="test", local_mode=True) as aos:
            agent = await aos.register_agent(
                name="async-agent", category="research", capabilities=["test"]
            )
            assert agent.id.startswith("agt_")

    @pytest.mark.asyncio
    async def test_async_invalid_key(self):
        with pytest.raises(ValidationError):
            AsyncAgentOS(api_key="bad_key")

    @pytest.mark.asyncio
    async def test_async_search(self):
        async with AsyncAgentOS(api_key="test", local_mode=True) as aos:
            await aos.register_agent(
                name="async-search", category="coding", capabilities=["python"]
            )
            results = await aos.search_agents(category="coding")
            assert isinstance(results, SearchResult)

    @pytest.mark.asyncio
    async def test_async_ecosystem_stats(self):
        async with AsyncAgentOS(api_key="test", local_mode=True) as aos:
            await aos.register_agent(
                name="async-stats", category="general", capabilities=["test"]
            )
            stats = await aos.get_ecosystem_stats()
            assert stats.total_agents >= 1
