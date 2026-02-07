"""CrewAI integration example.

Install: pip install 'protol-py[crewai]' crewai

This example shows how CrewAIWrapper maps crew members to Protol agents
so each member's actions are individually tracked.
"""

from __future__ import annotations

from protol import Protol
from protol.integrations import CrewAIWrapper

# --- Minimal mock crew so the example runs without crewai installed ---
class MockCrewOutput:
    """Simulates crewai.CrewOutput."""
    raw: str = "Research results and written article"
    tasks_output: list = []

class MockCrew:
    """Simulates a crewai.Crew."""
    def kickoff(self, inputs: dict | None = None) -> MockCrewOutput:
        print(f"  [MockCrew] running with inputs={inputs}")
        return MockCrewOutput()

# --- Initialize ---
p = Protol(api_key="test", local_mode=True)

researcher = p.register_agent(
    name="researcher",
    category="research",
    capabilities=["web_research", "analysis"],
    framework="crewai",
)
writer = p.register_agent(
    name="writer",
    category="writing",
    capabilities=["content_writing", "editing"],
    framework="crewai",
)

# Wrap the crew
tracked_crew = CrewAIWrapper(
    crew=MockCrew(),
    agent_mapping={
        "researcher": researcher,
        "writer": writer,
    },
)

# Run
result = tracked_crew.kickoff(inputs={"topic": "AI agent ecosystems"})
print(f"\nCrew result: {result.raw}")

# Check both agents got actions logged
for agent in [researcher, writer]:
    agent.refresh()
    print(f"\n{agent.name}:")
    print(f"  Actions: {agent.total_actions}")
    print(f"  Reputation: {agent.reputation_score} ({agent.trust_tier})")

p.close()
print("\nDone!")
