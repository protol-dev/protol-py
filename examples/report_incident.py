"""Report an incident against an agent."""

from protol import Protol

p = Protol(api_key="test", local_mode=True)

# Register an agent
agent = p.register_agent(
    name="suspect-agent",
    category="content_generation",
    capabilities=["text_generation"],
)
print(f"Registered agent: {agent.id}")

# Log some actions first
for i in range(5):
    with agent.action(task_category="content_generation") as act:
        act.success(output={"text": f"content-{i}"}, confidence=0.8, cost_usd=0.02)

# Report an incident
incident = p.report_incident(
    agent_id=agent.id,
    incident_type="hallucination",
    severity="high",
    title="Agent fabricated citations",
    description=(
        "The agent produced three academic citations that do not correspond to "
        "any published papers. The DOIs return 404 and the author names appear "
        "to be fabricated."
    ),
)
print(f"\nIncident reported: {incident.id}")
print(f"  Type: {incident.incident_type}")
print(f"  Severity: {incident.severity}")
print(f"  Status: {incident.status}")

# Report a second incident (lower severity)
incident2 = p.report_incident(
    agent_id=agent.id,
    incident_type="data_leak",
    severity="medium",
    title="Agent leaked PII in response",
    description="Agent included email addresses in its public summary.",
)
print(f"\nIncident reported: {incident2.id}")

# Check how incidents affected reputation
agent.refresh()
print(f"\nReputation after incidents: {agent.reputation_score} ({agent.trust_tier})")

breakdown = agent.reputation_breakdown()
print(f"Safety score: {breakdown.safety}")

# View all incidents for this agent
incidents = agent.get_incidents()
print(f"\nTotal incidents: {len(incidents)}")
for inc in incidents:
    print(f"  [{inc.severity}] {inc.title} — {inc.status}")

p.close()
print("\nDone!")
