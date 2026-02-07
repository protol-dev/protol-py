from protol import Protol

p = Protol(api_key="test", local_mode=True)

agent = p.register_agent(
    name="shravan-agent",
    category="research",
    capabilities=["web_research", "summarization"],
)

print(f"Agent ID: {agent.id}")
print(f"Score before: {agent.reputation_score}")

# Log 10 successful actions
for i in range(10):
    with agent.action(task_category="research") as act:
        act.success(output=f"result {i}", confidence=0.85, cost_usd=0.03)

# Log 1 failure
with agent.action(task_category="research") as act:
    act.fail(error_type="timeout", error_message="timed out")

agent.refresh()
print(f"Score after: {agent.reputation_score}")
print(f"Tier: {agent.trust_tier}")
print(f"Breakdown: {agent.reputation_breakdown()}")

p.close()