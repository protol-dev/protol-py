"""Basic usage example — runs fully offline with local_mode=True."""

from protol import Protol

# Initialize in local mode (no backend needed)
p = Protol(api_key="test", local_mode=True, environment="development")

# Register an agent
agent = p.register_agent(
    name="demo-research-agent",
    category="research",
    capabilities=["web_research", "summarization"],
    model_provider="anthropic",
    model_name="claude-3.5-sonnet",
    description="A research agent that demonstrates the SDK",
    tags=["demo"],
)
print(f"Registered agent: {agent.id} ({agent.name})")

# --- Log a successful action ---
with agent.action(task_category="research", description="Summarize recent papers") as act:
    # Your agent logic runs here...
    output = {"summary": "Key findings about AI safety in 2024"}
    act.success(output=output, confidence=0.92, cost_usd=0.01)

print(f"Action logged: {act.action_id} (status=success, {act.duration_ms}ms)")

# --- Log a few more actions for richer reputation ---
for i in range(3):
    with agent.action(task_category="data_analysis") as act:
        act.success(output={"result": f"analysis-{i}"}, confidence=0.85, cost_usd=0.02)

# --- Log a failed action ---
with agent.action(task_category="research") as act:
    act.fail(error_type="timeout", error_message="Upstream API timed out after 30s")

print(f"Failure logged: {act.action_id}")

# --- Check reputation ---
agent.refresh()
print(f"\nReputation: {agent.reputation_score} | Tier: {agent.trust_tier}")
print(f"Total actions: {agent.total_actions}")

breakdown = agent.reputation_breakdown()
print(f"Breakdown: reliability={breakdown.reliability}, safety={breakdown.safety}, "
      f"consistency={breakdown.consistency}, efficiency={breakdown.efficiency}, "
      f"transparency={breakdown.transparency}")

# --- Search the ecosystem ---
results = p.search_agents(category="research")
print(f"\nSearch found {results.total} agent(s)")
for ap in results.agents:
    print(f"  {ap.name}: score={ap.reputation.overall_score}, tier={ap.reputation.trust_tier}")

# --- Look up agent profile (read-only) ---
profile = p.lookup(agent.id)
print(f"\nProfile: {profile.name}, created={profile.created_at}")

# Clean up
p.close()
print("\nDone!")
