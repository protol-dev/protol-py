from agent_os import AgentOS

aos = AgentOS(api_key="test", local_mode=True)

# Register two agents in the same category
good_agent = aos.register_agent(
    name="reliable-agent",
    category="research",
    capabilities=["web_research"],
)

bad_agent = aos.register_agent(
    name="flaky-agent",
    category="research",
    capabilities=["web_research"],
)

# Good agent: 50 successes, 1 failure
for i in range(50):
    with good_agent.action(task_category="research") as act:
        act.success(output=f"result {i}", confidence=0.9, cost_usd=0.02)

with good_agent.action(task_category="research") as act:
    act.fail(error_type="timeout", error_message="timed out")

# Bad agent: 10 successes, 8 failures
for i in range(10):
    with bad_agent.action(task_category="research") as act:
        act.success(output=f"result {i}", confidence=0.5, cost_usd=0.10)

for i in range(8):
    with bad_agent.action(task_category="research") as act:
        act.fail(error_type="hallucination", error_message="made stuff up")

# Compare them
good_agent.refresh()
bad_agent.refresh()

print(f"GOOD AGENT: {good_agent.reputation_score:.1f} ({good_agent.trust_tier})")
print(f"  {good_agent.reputation_breakdown()}")
print()
print(f"BAD AGENT:  {bad_agent.reputation_score:.1f} ({bad_agent.trust_tier})")
print(f"  {bad_agent.reputation_breakdown()}")

# Search for the best research agent
results = aos.search_agents(category="research", min_reputation=70.0)
print(f"\nAgents with 70+ reputation: {len(results.agents)}")
for a in results.agents:
    print(f"  {a.name}: {a.reputation.overall_score:.1f}")

# Ecosystem stats
stats = aos.get_ecosystem_stats()
print(f"\nEcosystem: {stats.total_agents} agents, {stats.total_actions} actions")

aos.close()