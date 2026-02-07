"""Tests for Pydantic models."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from protol.models import (
    ActionRating,
    ActionRecord,
    ActionResponse,
    AgentProfile,
    AgentRegistration,
    AgentUpdate,
    EcosystemStats,
    IncidentReport,
    IncidentResponse,
    LeaderboardEntry,
    ReputationBreakdown,
    ReputationHistory,
    SearchResult,
)
from tests.conftest import make_agent_profile_dict, make_action_response_dict


class TestAgentRegistration:
    def test_valid_registration(self):
        reg = AgentRegistration(
            name="my-research-agent",
            category="research",
            capabilities=["web_research", "summarization"],
        )
        assert reg.name == "my-research-agent"
        assert reg.category == "research"
        assert reg.autonomy_level == "semi"

    def test_invalid_category(self):
        with pytest.raises(ValueError, match="Invalid category"):
            AgentRegistration(
                name="test-agent",
                category="invalid_category",
                capabilities=["test"],
            )

    def test_invalid_name_too_short(self):
        with pytest.raises(ValueError):
            AgentRegistration(
                name="ab",
                category="research",
                capabilities=["test"],
            )

    def test_invalid_name_special_chars(self):
        with pytest.raises(ValueError, match="alphanumeric"):
            AgentRegistration(
                name="@invalid!",
                category="research",
                capabilities=["test"],
            )

    def test_empty_capabilities(self):
        with pytest.raises(ValueError):
            AgentRegistration(
                name="test-agent",
                category="research",
                capabilities=[],
            )

    def test_capability_too_short(self):
        with pytest.raises(ValueError, match="2-50 characters"):
            AgentRegistration(
                name="test-agent",
                category="research",
                capabilities=["x"],
            )

    def test_invalid_autonomy_level(self):
        with pytest.raises(ValueError, match="Invalid autonomy_level"):
            AgentRegistration(
                name="test-agent",
                category="research",
                capabilities=["test"],
                autonomy_level="full",
            )

    def test_invalid_source_url(self):
        with pytest.raises(ValueError, match="HTTP/HTTPS"):
            AgentRegistration(
                name="test-agent",
                category="research",
                capabilities=["test"],
                source_url="ftp://invalid.com",
            )

    def test_valid_source_url(self):
        reg = AgentRegistration(
            name="test-agent",
            category="research",
            capabilities=["test"],
            source_url="https://github.com/test",
        )
        assert reg.source_url == "https://github.com/test"

    def test_description_max_length(self):
        with pytest.raises(ValueError):
            AgentRegistration(
                name="test-agent",
                category="research",
                capabilities=["test"],
                description="x" * 501,
            )

    def test_all_fields(self):
        reg = AgentRegistration(
            name="full-agent",
            category="coding",
            capabilities=["python", "javascript"],
            model_provider="openai",
            model_name="gpt-4",
            framework="crewai",
            hosting="cloud",
            source_url="https://example.com",
            autonomy_level="autonomous",
            max_spend_per_task=10.0,
            can_hire_agents=True,
            description="A fully configured agent",
            tags=["prod", "coding"],
        )
        assert reg.can_hire_agents is True
        assert reg.tags == ["prod", "coding"]


class TestAgentUpdate:
    def test_all_optional(self):
        update = AgentUpdate()
        assert update.name is None
        assert update.category is None

    def test_partial_update(self):
        update = AgentUpdate(name="new-name", category="coding")
        assert update.name == "new-name"
        assert update.capabilities is None

    def test_invalid_category(self):
        with pytest.raises(ValueError):
            AgentUpdate(category="bad_category")


class TestActionRecord:
    def test_valid_record(self):
        now = datetime.now(timezone.utc)
        record = ActionRecord(
            agent_id="agt_abc123def",
            action_type="task_execution",
            status="success",
            started_at=now,
        )
        assert record.status == "success"
        assert record.environment == "production"

    def test_invalid_action_type(self):
        with pytest.raises(ValueError, match="Invalid action_type"):
            ActionRecord(
                agent_id="agt_abc123def",
                action_type="invalid_type",
                status="success",
                started_at=datetime.now(timezone.utc),
            )

    def test_invalid_status(self):
        with pytest.raises(ValueError, match="Invalid status"):
            ActionRecord(
                agent_id="agt_abc123def",
                action_type="task_execution",
                status="invalid_status",
                started_at=datetime.now(timezone.utc),
            )

    def test_confidence_range(self):
        with pytest.raises(ValueError):
            ActionRecord(
                agent_id="agt_abc123def",
                action_type="task_execution",
                status="success",
                started_at=datetime.now(timezone.utc),
                self_reported_confidence=1.5,
            )

    def test_invalid_commissioner_type(self):
        with pytest.raises(ValueError, match="agent.*human"):
            ActionRecord(
                agent_id="agt_abc123def",
                action_type="task_execution",
                status="success",
                started_at=datetime.now(timezone.utc),
                commissioner_type="bot",
            )

    def test_invalid_error_type(self):
        with pytest.raises(ValueError, match="Invalid error_type"):
            ActionRecord(
                agent_id="agt_abc123def",
                action_type="task_execution",
                status="failed",
                started_at=datetime.now(timezone.utc),
                error_type="invalid",
            )

    def test_invalid_environment(self):
        with pytest.raises(ValueError, match="Invalid environment"):
            ActionRecord(
                agent_id="agt_abc123def",
                action_type="task_execution",
                status="success",
                started_at=datetime.now(timezone.utc),
                environment="dev",
            )


class TestActionRating:
    def test_valid_rating(self):
        rating = ActionRating(rating=5, feedback="Excellent work")
        assert rating.rating == 5

    def test_rating_too_low(self):
        with pytest.raises(ValueError):
            ActionRating(rating=0)

    def test_rating_too_high(self):
        with pytest.raises(ValueError):
            ActionRating(rating=6)


class TestIncidentReport:
    def test_valid_incident(self):
        report = IncidentReport(
            agent_id="agt_abc123def",
            incident_type="hallucination",
            severity="medium",
            title="Agent produced incorrect facts",
            description="The agent hallucinated details about a research topic.",
        )
        assert report.severity == "medium"

    def test_invalid_incident_type(self):
        with pytest.raises(ValueError, match="Invalid incident_type"):
            IncidentReport(
                agent_id="agt_abc123def",
                incident_type="invalid_type",
                severity="low",
                title="Test incident",
                description="This is a test incident report.",
            )

    def test_title_too_short(self):
        with pytest.raises(ValueError):
            IncidentReport(
                agent_id="agt_abc123def",
                incident_type="hallucination",
                severity="low",
                title="Hi",
                description="This is a test incident report.",
            )


class TestResponseModels:
    def test_agent_profile_roundtrip(self):
        data = make_agent_profile_dict()
        profile = AgentProfile.model_validate(data)
        assert profile.agent_id == "agt_test1234"
        assert profile.reputation.overall_score == 82.5
        assert profile.reputation.breakdown.reliability == 85.0
        dumped = profile.model_dump(mode="json")
        reparsed = AgentProfile.model_validate(dumped)
        assert reparsed.agent_id == profile.agent_id

    def test_action_response_roundtrip(self):
        data = make_action_response_dict()
        response = ActionResponse.model_validate(data)
        assert response.action_id == "act_test1234"
        assert response.status == "success"
        dumped = response.model_dump(mode="json")
        reparsed = ActionResponse.model_validate(dumped)
        assert reparsed.action_id == response.action_id

    def test_search_result(self):
        data = {
            "agents": [make_agent_profile_dict()],
            "total": 1,
            "page": 1,
            "per_page": 20,
            "has_more": False,
        }
        result = SearchResult.model_validate(data)
        assert result.total == 1
        assert len(result.agents) == 1

    def test_ecosystem_stats(self):
        data = {
            "total_agents": 100,
            "total_actions": 5000,
            "total_incidents": 12,
            "avg_reputation": 72.5,
            "agents_by_category": {"research": 30, "coding": 25},
            "agents_by_tier": {"Gold": 20, "Silver": 40},
            "actions_last_24h": 200,
            "actions_last_7d": 1200,
        }
        stats = EcosystemStats.model_validate(data)
        assert stats.total_agents == 100
        assert stats.agents_by_category["research"] == 30

    def test_reputation_breakdown(self):
        data = {
            "reliability": 90.0,
            "safety": 95.0,
            "consistency": 85.0,
            "efficiency": 80.0,
            "transparency": 70.0,
        }
        breakdown = ReputationBreakdown.model_validate(data)
        assert breakdown.reliability == 90.0

    def test_optional_fields_default(self):
        data = make_agent_profile_dict(description=None, tags=None, source_url=None)
        profile = AgentProfile.model_validate(data)
        assert profile.description is None
        assert profile.tags is None
        assert profile.source_url is None
