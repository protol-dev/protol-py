"""Shared fixtures for Protol SDK tests."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from protol.client import Protol
from protol.agent import Agent
from protol.models import (
    ActionResponse,
    AgentArchitecture,
    AgentProfile,
    AgentReputation,
    AgentStats,
    IncidentResponse,
    Owner,
    ReputationBreakdown,
)


# ---------------------------------------------------------------------------
# Sample data factories
# ---------------------------------------------------------------------------


def make_owner(**overrides):
    defaults = {
        "owner_id": "owner_test123",
        "display_name": "Test User",
        "verified": True,
    }
    defaults.update(overrides)
    return defaults


def make_architecture(**overrides):
    defaults = {
        "model_provider": "anthropic",
        "model_name": "claude-3.5-sonnet",
        "framework": "langchain",
        "hosting": "cloud",
    }
    defaults.update(overrides)
    return defaults


def make_reputation_breakdown(**overrides):
    defaults = {
        "reliability": 85.0,
        "safety": 95.0,
        "consistency": 80.0,
        "efficiency": 70.0,
        "transparency": 75.0,
    }
    defaults.update(overrides)
    return defaults


def make_reputation(**overrides):
    defaults = {
        "overall_score": 82.5,
        "trust_tier": "Gold",
        "breakdown": make_reputation_breakdown(),
        "trend": "improving",
        "last_computed": datetime.now(timezone.utc).isoformat(),
    }
    defaults.update(overrides)
    return defaults


def make_stats(**overrides):
    defaults = {
        "total_actions": 150,
        "success_rate": 92.0,
        "avg_rating": 4.3,
        "total_earnings_usd": 45.50,
        "active_since": datetime.now(timezone.utc).isoformat(),
        "last_active": datetime.now(timezone.utc).isoformat(),
        "incidents": 0,
    }
    defaults.update(overrides)
    return defaults


def make_agent_profile_dict(**overrides):
    """Create a full agent profile dict matching the API response."""
    defaults = {
        "agent_id": "agt_test1234",
        "name": "test-agent",
        "slug": "test-agent",
        "owner": make_owner(),
        "architecture": make_architecture(),
        "capabilities": ["web_research", "summarization"],
        "category": "research",
        "autonomy_level": "semi",
        "reputation": make_reputation(),
        "stats": make_stats(),
        "status": "active",
        "verification": "verified",
        "description": "A test agent",
        "tags": ["test", "research"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_url": "https://github.com/test/agent",
    }
    defaults.update(overrides)
    return defaults


def make_action_response_dict(**overrides):
    """Create a full action response dict matching the API response."""
    now = datetime.now(timezone.utc).isoformat()
    defaults = {
        "action_id": "act_test1234",
        "agent_id": "agt_test1234",
        "action_type": "task_execution",
        "task_category": "research",
        "description": "Test action",
        "commissioned_by": "user_123",
        "commissioner_type": "human",
        "status": "success",
        "started_at": now,
        "completed_at": now,
        "duration_ms": 1500,
        "cost_usd": 0.03,
        "payment_usd": 0.10,
        "self_reported_confidence": 0.87,
        "commissioner_rating": None,
        "commissioner_feedback": None,
        "error_type": None,
        "error_message": None,
        "verified": False,
        "environment": "production",
        "recorded_at": now,
    }
    defaults.update(overrides)
    return defaults


def make_incident_response_dict(**overrides):
    """Create a full incident response dict."""
    now = datetime.now(timezone.utc).isoformat()
    defaults = {
        "incident_id": "inc_test1234",
        "agent_id": "agt_test1234",
        "reported_by": "owner_test123",
        "incident_type": "hallucination",
        "severity": "medium",
        "title": "Agent hallucinated facts",
        "description": "The agent produced incorrect information about a topic.",
        "evidence_url": None,
        "financial_impact_usd": None,
        "users_affected": None,
        "status": "open",
        "verified": False,
        "created_at": now,
    }
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_agent_profile_dict():
    """Full agent profile dict."""
    return make_agent_profile_dict()


@pytest.fixture
def sample_agent_profile(sample_agent_profile_dict):
    """Full AgentProfile model."""
    return AgentProfile.model_validate(sample_agent_profile_dict)


@pytest.fixture
def sample_action_response_dict():
    """Full action response dict."""
    return make_action_response_dict()


@pytest.fixture
def sample_action_response(sample_action_response_dict):
    """Full ActionResponse model."""
    return ActionResponse.model_validate(sample_action_response_dict)


@pytest.fixture
def aos_local():
    """Protol client in local mode."""
    client = Protol(api_key="test_local_key", local_mode=True)
    yield client
    client.close()


@pytest.fixture
def sample_local_agent(aos_local):
    """An agent registered in local mode."""
    return aos_local.register_agent(
        name="test-local-agent",
        category="research",
        capabilities=["web_research", "summarization"],
        model_provider="anthropic",
        model_name="claude-3.5-sonnet",
        description="Test agent for unit tests",
    )
