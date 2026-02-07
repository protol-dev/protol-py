"""Tests for CrewAI integration."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

import protol.integrations.crewai as _crew_mod
from protol.client import Protol


class MockCrew:
    """Mock CrewAI Crew for testing."""

    def kickoff(self, inputs=None):
        return {"result": "Crew completed successfully", "inputs": inputs}


class MockFailingCrew:
    """Mock Crew that raises on kickoff."""

    def kickoff(self, inputs=None):
        raise RuntimeError("Crew execution failed")


class TestCrewAIWrapper:
    @pytest.fixture(autouse=True)
    def _patch_crew(self, monkeypatch):
        """Allow instantiation even without crewai installed."""
        monkeypatch.setattr(_crew_mod, "Crew", object)

    @pytest.fixture
    def setup(self):
        aos = Protol(api_key="test", local_mode=True)
        researcher = aos.register_agent(
            name="crew-researcher",
            category="research",
            capabilities=["web_research"],
        )
        writer = aos.register_agent(
            name="crew-writer",
            category="writing",
            capabilities=["content_writing"],
        )
        yield aos, researcher, writer
        aos.close()

    def test_kickoff_logs_actions(self, setup):
        aos, researcher, writer = setup
        from protol.integrations.crewai import CrewAIWrapper

        wrapper = CrewAIWrapper(
            crew=MockCrew(),
            agent_mapping={
                "researcher": researcher,
                "writer": writer,
            },
        )

        result = wrapper.kickoff(inputs={"topic": "AI agents"})
        assert result["result"] == "Crew completed successfully"

        # Both agents should have actions logged
        r_actions = researcher.get_actions()
        w_actions = writer.get_actions()
        assert len(r_actions) == 1
        assert len(w_actions) == 1

    def test_kickoff_failure_logs_errors(self, setup):
        aos, researcher, writer = setup
        from protol.integrations.crewai import CrewAIWrapper

        wrapper = CrewAIWrapper(
            crew=MockFailingCrew(),
            agent_mapping={
                "researcher": researcher,
                "writer": writer,
            },
        )

        with pytest.raises(RuntimeError, match="Crew execution failed"):
            wrapper.kickoff()

        # Both agents should have failed actions
        r_actions = researcher.get_actions()
        w_actions = writer.get_actions()
        assert len(r_actions) == 1
        assert len(w_actions) == 1
        assert r_actions[0].status == "failed"
        assert w_actions[0].status == "failed"
