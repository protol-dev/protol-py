"""Check and compare agent reputation scores."""

from protol import Protol

p = Protol(api_key="test", local_mode=True)

# Register two agents and log actions to build up reputation
agent_a = p.register_agent(
    name="reliable-agent", category="research", capabilities=["web_research"]
)
agent_b = p.register_agent(
    name="flaky-agent", category="research", capabilities=["web_research"]
)

# Agent A: mostly successes
for i in range(10):
    with agent_a.action(task_category="research") as act:
        act.success(output={"data": f"result-{i}"}, confidence=0.9, cost_usd=0.01)

# Agent B: mostly failures
for i in range(10):
    with agent_b.action(task_category="research") as act:
        if i < 3:
            act.success(output={"data": f"result-{i}"}, confidence=0.5, cost_usd=0.05)
        else:
            act.fail(error_type="crash", error_message="Something went wrong")

# Refresh both
agent_a.refresh()
agent_b.refresh()

print("=== Agent Comparison ===\n")
for agent in [agent_a, agent_b]:
    bd = agent.reputation_breakdown()
    print(f"{agent.name}:")
    print(f"  Score: {agent.reputation_score} | Tier: {agent.trust_tier}")
    print(f"  Actions: {agent.total_actions} | Success rate: {agent.success_rate}")
    print(f"  Reliability: {bd.reliability}")
    print(f"  Safety: {bd.safety}")
    print(f"  Consistency: {bd.consistency}")
    print(f"  Efficiency: {bd.efficiency}")
    print(f"  Transparency: {bd.transparency}")
    print()

# Leaderboard
leaderboard = p.get_leaderboard(category="research", limit=10)
print("=== Leaderboard ===")
for entry in leaderboard:
    print(f"  {entry.agent_name}: {entry.reputation_score}")

# Reputation history
history = agent_a.reputation_history(days=30)
print(f"\nReputation history for {agent_a.name}: {len(history)} snapshot(s)")
for snap in history:
    print(f"  {snap.computed_at}: {snap.overall_score}")

p.close()
print("\nDone!")
