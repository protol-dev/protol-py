"""In-memory local store for the Protol SDK local_mode.

Drop-in replacement for HttpClient. Stores agents, actions, and incidents in
memory with full 5-dimension reputation scoring.

NOT part of the public API.
"""

from __future__ import annotations

import math
import random
import re
import string
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from protol.constants import VALID_SEVERITY_LEVELS


def _random_id(prefix: str, length: int = 8) -> str:
    """Generate a random ID with the given prefix."""
    chars = string.ascii_lowercase + string.digits
    suffix = "".join(random.choices(chars, k=length))
    return f"{prefix}{suffix}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


class LocalStore:
    """In-memory store that mirrors the Protol HTTP API contract.

    Provides get/post/patch/delete methods matching HttpClient's interface so
    it can be used as a drop-in replacement when ``local_mode=True``.
    """

    def __init__(self, owner_id: str = "owner_local") -> None:
        self._owner_id = owner_id
        # Storage: agent_id -> agent profile dict
        self._agents: Dict[str, Dict[str, Any]] = {}
        # Storage: agent_id -> list of action dicts
        self._actions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        # Storage: agent_id -> list of incident dicts
        self._incidents: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Public interface (matches HttpClient)
    # ------------------------------------------------------------------

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Route a GET request to the appropriate handler."""
        return self._route("GET", path, params=params)

    def post(self, path: str, json: Optional[Dict[str, Any]] = None) -> Any:
        """Route a POST request to the appropriate handler."""
        return self._route("POST", path, json=json)

    def patch(self, path: str, json: Optional[Dict[str, Any]] = None) -> Any:
        """Route a PATCH request to the appropriate handler."""
        return self._route("PATCH", path, json=json)

    def delete(self, path: str) -> Any:
        """Route a DELETE request to the appropriate handler."""
        return self._route("DELETE", path)

    def close(self) -> None:
        """No-op for local store."""
        pass

    # ------------------------------------------------------------------
    # Router
    # ------------------------------------------------------------------

    def _route(
        self,
        method: str,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Match a URL path to a handler."""
        path = path.rstrip("/")

        # POST /agents — register new agent
        if method == "POST" and path == "/agents":
            return self._register_agent(json or {})

        # GET /agents — list my agents
        if method == "GET" and path == "/agents":
            return self._list_agents()

        # GET /agents/search — search agents
        if method == "GET" and path == "/agents/search":
            return self._search_agents(params or {})

        # GET /leaderboard
        if method == "GET" and path == "/leaderboard":
            return self._get_leaderboard(params or {})

        # GET /ecosystem/stats
        if method == "GET" and path == "/ecosystem/stats":
            return self._get_ecosystem_stats()

        # POST /incidents
        if method == "POST" and path == "/incidents":
            return self._report_incident(json or {})

        # Agent-specific routes: /agents/{agent_id}/...
        m = re.match(r"^/agents/([^/]+)(/.*)?$", path)
        if m:
            agent_id = m.group(1)
            sub_path = m.group(2) or ""

            if agent_id == "search":
                # Already handled above
                pass
            elif method == "GET" and sub_path == "":
                return self._get_agent(agent_id)
            elif method == "PATCH" and sub_path == "":
                return self._update_agent(agent_id, json or {})
            elif method == "POST" and sub_path == "/actions":
                return self._record_action(agent_id, json or {})
            elif method == "GET" and sub_path == "/actions":
                return self._get_actions(agent_id, params or {})
            elif method == "GET" and sub_path == "/reputation/history":
                return self._get_reputation_history(agent_id, params or {})
            elif method == "GET" and sub_path == "/incidents":
                return self._get_agent_incidents(agent_id)

            # PATCH /agents/{agent_id}/actions/{action_id} — rate action
            action_match = re.match(r"^/actions/([^/]+)$", sub_path)
            if action_match and method == "PATCH":
                action_id = action_match.group(1)
                return self._rate_action(agent_id, action_id, json or {})

        from protol.exceptions import NotFoundError

        raise NotFoundError(message=f"No local handler for {method} {path}")

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _register_agent(self, data: Dict[str, Any]) -> Dict[str, Any]:
        agent_id = _random_id("agt_")
        slug = data.get("name", "agent").lower().replace(" ", "-")
        now = _now_iso()

        profile: Dict[str, Any] = {
            "agent_id": agent_id,
            "name": data.get("name", "unnamed"),
            "slug": slug,
            "owner": {
                "owner_id": self._owner_id,
                "display_name": "Local User",
                "verified": False,
            },
            "architecture": {
                "model_provider": data.get("model_provider"),
                "model_name": data.get("model_name"),
                "framework": data.get("framework"),
                "hosting": data.get("hosting"),
            },
            "capabilities": data.get("capabilities", []),
            "category": data.get("category", "general"),
            "autonomy_level": data.get("autonomy_level", "semi"),
            "reputation": self._default_reputation(now),
            "stats": {
                "total_actions": 0,
                "success_rate": 0.0,
                "avg_rating": None,
                "total_earnings_usd": 0.0,
                "active_since": now,
                "last_active": None,
                "incidents": 0,
            },
            "status": "active",
            "verification": "unverified",
            "description": data.get("description"),
            "tags": data.get("tags"),
            "created_at": now,
            "source_url": data.get("source_url"),
        }

        self._agents[agent_id] = profile
        return profile

    def _get_agent(self, agent_id: str) -> Dict[str, Any]:
        if agent_id not in self._agents:
            from protol.exceptions import NotFoundError

            raise NotFoundError(message=f"Agent '{agent_id}' not found.")
        return self._agents[agent_id]

    def _update_agent(self, agent_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        profile = self._get_agent(agent_id)
        # Direct fields
        for key in ("name", "category", "capabilities", "autonomy_level",
                     "description", "tags", "source_url"):
            if key in data and data[key] is not None:
                profile[key] = data[key]
        # Architecture fields
        for key in ("model_provider", "model_name", "framework", "hosting"):
            if key in data and data[key] is not None:
                profile["architecture"][key] = data[key]
        return profile

    def _list_agents(self) -> List[Dict[str, Any]]:
        return list(self._agents.values())

    def _record_action(self, agent_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        self._get_agent(agent_id)  # Ensure agent exists
        action_id = _random_id("act_")
        now = _now_iso()

        action: Dict[str, Any] = {
            "action_id": action_id,
            "agent_id": agent_id,
            "action_type": data.get("action_type", "task_execution"),
            "task_category": data.get("task_category"),
            "description": data.get("description"),
            "commissioned_by": data.get("commissioned_by"),
            "commissioner_type": data.get("commissioner_type"),
            "status": data.get("status", "success"),
            "started_at": data.get("started_at", now),
            "completed_at": data.get("completed_at", now),
            "duration_ms": data.get("duration_ms"),
            "cost_usd": data.get("cost_usd"),
            "payment_usd": data.get("payment_usd"),
            "self_reported_confidence": data.get("self_reported_confidence"),
            "commissioner_rating": None,
            "commissioner_feedback": None,
            "error_type": data.get("error_type"),
            "error_message": data.get("error_message"),
            "verified": False,
            "environment": data.get("environment", "production"),
            "recorded_at": now,
            "input_hash": data.get("input_hash"),
            "output_hash": data.get("output_hash"),
            "input_size_bytes": data.get("input_size_bytes"),
            "output_size_bytes": data.get("output_size_bytes"),
        }

        self._actions[agent_id].append(action)

        # Recompute reputation and stats
        self._recompute_reputation(agent_id)

        return action

    def _get_actions(
        self, agent_id: str, params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        self._get_agent(agent_id)
        actions = self._actions.get(agent_id, [])
        status = params.get("status")
        task_category = params.get("task_category")
        if status:
            actions = [a for a in actions if a["status"] == status]
        if task_category:
            actions = [a for a in actions if a["task_category"] == task_category]
        limit = int(params.get("limit", 50))
        offset = int(params.get("offset", 0))
        return actions[offset : offset + limit]

    def _rate_action(
        self, agent_id: str, action_id: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        actions = self._actions.get(agent_id, [])
        for action in actions:
            if action["action_id"] == action_id:
                action["commissioner_rating"] = data.get("rating")
                action["commissioner_feedback"] = data.get("feedback")
                self._recompute_reputation(agent_id)
                return action

        from protol.exceptions import NotFoundError

        raise NotFoundError(message=f"Action '{action_id}' not found.")

    def _get_reputation_history(
        self, agent_id: str, params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        self._get_agent(agent_id)
        profile = self._agents[agent_id]
        rep = profile["reputation"]
        return [
            {
                "overall_score": rep["overall_score"],
                "breakdown": rep["breakdown"],
                "trust_tier": rep["trust_tier"],
                "actions_in_window": profile["stats"]["total_actions"],
                "computed_at": rep["last_computed"],
            }
        ]

    def _get_agent_incidents(self, agent_id: str) -> List[Dict[str, Any]]:
        self._get_agent(agent_id)
        return self._incidents.get(agent_id, [])

    def _report_incident(self, data: Dict[str, Any]) -> Dict[str, Any]:
        agent_id = data.get("agent_id", "")
        self._get_agent(agent_id)
        incident_id = _random_id("inc_")
        now = _now_iso()

        incident: Dict[str, Any] = {
            "incident_id": incident_id,
            "agent_id": agent_id,
            "reported_by": self._owner_id,
            "incident_type": data.get("incident_type", ""),
            "severity": data.get("severity", "low"),
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "evidence_url": data.get("evidence_url"),
            "financial_impact_usd": data.get("financial_impact_usd"),
            "users_affected": data.get("users_affected"),
            "status": "open",
            "verified": False,
            "created_at": now,
        }

        self._incidents[agent_id].append(incident)
        # Update agent stats
        profile = self._agents[agent_id]
        profile["stats"]["incidents"] = len(self._incidents[agent_id])
        self._recompute_reputation(agent_id)
        return incident

    def _search_agents(self, params: Dict[str, Any]) -> Dict[str, Any]:
        agents = list(self._agents.values())

        category = params.get("category")
        if category:
            agents = [a for a in agents if a["category"] == category]

        min_rep = params.get("min_reputation")
        if min_rep is not None:
            min_rep = float(min_rep)
            agents = [a for a in agents if a["reputation"]["overall_score"] >= min_rep]

        trust_tier = params.get("trust_tier")
        if trust_tier:
            agents = [a for a in agents if a["reputation"]["trust_tier"] == trust_tier]

        model_provider = params.get("model_provider")
        if model_provider:
            agents = [
                a for a in agents if a["architecture"]["model_provider"] == model_provider
            ]

        capabilities = params.get("capabilities")
        if capabilities:
            if isinstance(capabilities, str):
                capabilities = [capabilities]
            agents = [
                a
                for a in agents
                if any(c in a["capabilities"] for c in capabilities)
            ]

        sort_by = params.get("sort_by", "reputation")
        if sort_by == "reputation":
            agents.sort(key=lambda a: a["reputation"]["overall_score"], reverse=True)
        elif sort_by == "actions":
            agents.sort(key=lambda a: a["stats"]["total_actions"], reverse=True)
        elif sort_by == "newest":
            agents.sort(key=lambda a: a["created_at"], reverse=True)

        page = int(params.get("page", 1))
        per_page = int(params.get("per_page", 20))
        start = (page - 1) * per_page
        end = start + per_page
        paginated = agents[start:end]

        return {
            "agents": paginated,
            "total": len(agents),
            "page": page,
            "per_page": per_page,
            "has_more": end < len(agents),
        }

    def _get_leaderboard(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        agents = list(self._agents.values())
        category = params.get("category")
        if category:
            agents = [a for a in agents if a["category"] == category]
        agents.sort(key=lambda a: a["reputation"]["overall_score"], reverse=True)
        limit = int(params.get("limit", 20))
        entries = []
        for a in agents[:limit]:
            entries.append(
                {
                    "agent_id": a["agent_id"],
                    "name": a["name"],
                    "category": a["category"],
                    "reputation_score": a["reputation"]["overall_score"],
                    "trust_tier": a["reputation"]["trust_tier"],
                    "total_actions": a["stats"]["total_actions"],
                    "owner": a["owner"],
                }
            )
        return entries

    def _get_ecosystem_stats(self) -> Dict[str, Any]:
        all_agents = list(self._agents.values())
        all_actions: List[Dict[str, Any]] = []
        for acts in self._actions.values():
            all_actions.extend(acts)
        all_incidents: List[Dict[str, Any]] = []
        for incs in self._incidents.values():
            all_incidents.extend(incs)

        by_category: Dict[str, int] = defaultdict(int)
        by_tier: Dict[str, int] = defaultdict(int)
        scores = []
        for a in all_agents:
            by_category[a["category"]] += 1
            by_tier[a["reputation"]["trust_tier"]] += 1
            scores.append(a["reputation"]["overall_score"])

        return {
            "total_agents": len(all_agents),
            "total_actions": len(all_actions),
            "total_incidents": len(all_incidents),
            "avg_reputation": statistics.mean(scores) if scores else 0.0,
            "agents_by_category": dict(by_category),
            "agents_by_tier": dict(by_tier),
            "actions_last_24h": len(all_actions),  # simplified: all actions
            "actions_last_7d": len(all_actions),
        }

    # ------------------------------------------------------------------
    # Reputation scoring — full 5-dimension algorithm
    # ------------------------------------------------------------------

    def _default_reputation(self, now_iso: str) -> Dict[str, Any]:
        return {
            "overall_score": 50.0,
            "trust_tier": "Unverified",
            "breakdown": {
                "reliability": 50.0,
                "safety": 100.0,
                "consistency": 50.0,
                "efficiency": 50.0,
                "transparency": 50.0,
            },
            "trend": "stable",
            "last_computed": now_iso,
        }

    def _recompute_reputation(self, agent_id: str) -> None:
        """Recompute the full 5-dimension reputation for an agent."""
        profile = self._agents[agent_id]
        actions = self._actions.get(agent_id, [])
        incidents = self._incidents.get(agent_id, [])

        if not actions:
            profile["reputation"] = self._default_reputation(_now_iso())
            self._update_stats(agent_id)
            return

        reliability = self._compute_reliability(actions)
        safety = self._compute_safety(actions, incidents)
        consistency = self._compute_consistency(actions)
        efficiency = self._compute_efficiency(agent_id, actions)
        transparency = self._compute_transparency(actions)

        # Weighted average: reliability 30%, safety 25%, consistency 20%,
        # efficiency 15%, transparency 10%
        overall = (
            reliability * 0.30
            + safety * 0.25
            + consistency * 0.20
            + efficiency * 0.15
            + transparency * 0.10
        )

        overall = max(0.0, min(100.0, overall))

        trust_tier = self._score_to_tier(overall)

        # Determine trend (compare to previous score)
        prev_score = profile["reputation"]["overall_score"]
        if overall > prev_score + 2:
            trend = "improving"
        elif overall < prev_score - 2:
            trend = "declining"
        else:
            trend = "stable"

        profile["reputation"] = {
            "overall_score": round(overall, 2),
            "trust_tier": trust_tier,
            "breakdown": {
                "reliability": round(reliability, 2),
                "safety": round(safety, 2),
                "consistency": round(consistency, 2),
                "efficiency": round(efficiency, 2),
                "transparency": round(transparency, 2),
            },
            "trend": trend,
            "last_computed": _now_iso(),
        }

        self._update_stats(agent_id)

    def _compute_reliability(self, actions: List[Dict[str, Any]]) -> float:
        """Reliability: success_rate weighted by action volume.

        More actions → more confident estimate → score moves further
        from 50 (the prior) toward the actual success rate.
        """
        total = len(actions)
        if total == 0:
            return 50.0

        successes = sum(1 for a in actions if a["status"] in ("success", "partial"))
        raw_rate = (successes / total) * 100

        # Bayesian-style blending: confidence grows with sqrt(total)
        confidence = min(1.0, math.sqrt(total) / 10)
        return 50.0 * (1 - confidence) + raw_rate * confidence

    def _compute_safety(
        self, actions: List[Dict[str, Any]], incidents: List[Dict[str, Any]]
    ) -> float:
        """Safety: inverse of incident frequency weighted by severity.

        Severity weights: low=1, medium=3, high=7, critical=15.
        Score = 100 - (weighted_incident_score / max(total_actions, 1)) * factor
        Clamped to [0, 100].
        """
        severity_weights = {"low": 1, "medium": 3, "high": 7, "critical": 15}
        total_actions = max(len(actions), 1)

        weighted_score = sum(
            severity_weights.get(inc.get("severity", "low"), 1) for inc in incidents
        )

        # Scale: a single critical incident per 10 actions ≈ 85 (losing 15 pts)
        raw = 100.0 - (weighted_score / total_actions) * 10.0
        return max(0.0, min(100.0, raw))

    def _compute_consistency(self, actions: List[Dict[str, Any]]) -> float:
        """Consistency: lower stddev of confidence scores → higher score.

        Uses self_reported_confidence from actions that provide it.
        """
        confidences = [
            a["self_reported_confidence"]
            for a in actions
            if a.get("self_reported_confidence") is not None
        ]

        if len(confidences) < 2:
            return 50.0  # Not enough data

        stddev = statistics.stdev(confidences)
        # stddev of 0 → 100, stddev of 0.5 → 0
        raw = max(0.0, 100.0 - stddev * 200.0)
        return max(0.0, min(100.0, raw))

    def _compute_efficiency(
        self, agent_id: str, actions: List[Dict[str, Any]]
    ) -> float:
        """Efficiency: compare agent's avg cost against category average.

        Score = 50 + 50 * (1 - agent_avg / category_avg), clamped to [0, 100].
        If no category peers or no cost data, default to 50.
        """
        profile = self._agents[agent_id]
        category = profile["category"]

        # Get this agent's successful action costs
        agent_costs = [
            a["cost_usd"]
            for a in actions
            if a.get("cost_usd") is not None and a["status"] in ("success", "partial")
        ]

        if not agent_costs:
            return 50.0

        agent_avg = statistics.mean(agent_costs)

        # Get all agents' average costs in the same category
        category_costs: List[float] = []
        for aid, a_profile in self._agents.items():
            if a_profile["category"] != category:
                continue
            a_actions = self._actions.get(aid, [])
            costs = [
                a["cost_usd"]
                for a in a_actions
                if a.get("cost_usd") is not None
                and a["status"] in ("success", "partial")
            ]
            if costs:
                category_costs.append(statistics.mean(costs))

        if not category_costs or statistics.mean(category_costs) == 0:
            return 50.0

        category_avg = statistics.mean(category_costs)
        raw = 50.0 + 50.0 * (1.0 - agent_avg / category_avg)
        return max(0.0, min(100.0, raw))

    def _compute_transparency(self, actions: List[Dict[str, Any]]) -> float:
        """Transparency: ratio of actions with output_hash, input_hash,
        and self_reported_confidence vs. total actions.
        """
        total = len(actions)
        if total == 0:
            return 50.0

        transparent_count = 0
        for a in actions:
            has_output_hash = a.get("output_hash") is not None
            has_input_hash = a.get("input_hash") is not None
            has_confidence = a.get("self_reported_confidence") is not None
            # Count how many of the 3 transparency signals are present
            signals = sum([has_output_hash, has_input_hash, has_confidence])
            transparent_count += signals

        max_possible = total * 3
        return (transparent_count / max_possible) * 100.0

    def _score_to_tier(self, score: float) -> str:
        """Map a reputation score to a trust tier."""
        if score >= 90:
            return "Platinum"
        elif score >= 75:
            return "Gold"
        elif score >= 60:
            return "Silver"
        elif score >= 40:
            return "Bronze"
        else:
            return "Unverified"

    def _update_stats(self, agent_id: str) -> None:
        """Update agent stats from current actions/incidents."""
        profile = self._agents[agent_id]
        actions = self._actions.get(agent_id, [])
        incidents = self._incidents.get(agent_id, [])

        total = len(actions)
        successes = sum(1 for a in actions if a["status"] in ("success", "partial"))
        ratings = [
            a["commissioner_rating"]
            for a in actions
            if a.get("commissioner_rating") is not None
        ]
        earnings = sum(a.get("payment_usd", 0) or 0 for a in actions)

        profile["stats"]["total_actions"] = total
        profile["stats"]["success_rate"] = (successes / total * 100) if total > 0 else 0.0
        profile["stats"]["avg_rating"] = (
            statistics.mean(ratings) if ratings else None
        )
        profile["stats"]["total_earnings_usd"] = earnings
        profile["stats"]["last_active"] = (
            actions[-1].get("completed_at") or actions[-1].get("started_at")
            if actions
            else None
        )
        profile["stats"]["incidents"] = len(incidents)
