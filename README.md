# Protol Python SDK

[![PyPI version](https://img.shields.io/pypi/v/protol-py.svg)](https://pypi.org/project/protol-py/)
[![Python versions](https://img.shields.io/pypi/pyversions/protol-py.svg)](https://pypi.org/project/protol-py/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Tests](https://github.com/protol-dev/protol-py/actions/workflows/ci.yml/badge.svg)](https://github.com/protol-dev/protol-py/actions)

**The civilization layer for AI agents** — identity, action tracking, and reputation scoring.

---

## What is Protol?

Protol is a platform that provides AI agents with identity, accountability, and trust. Every agent gets a unique identity, every action is tracked, and reputation scores are computed continuously — creating a transparent ecosystem where agents can be evaluated, compared, and trusted.

`protol-py` is the Python client library for the Protol platform. It lets you register agents, log actions, query reputation scores, and integrate with frameworks like LangChain and CrewAI in minutes.

---

## Installation

```bash
pip install protol-py
```

With LangChain integration:

```bash
pip install 'protol-py[langchain]'
```

With CrewAI integration:

```bash
pip install 'protol-py[crewai]'
```

All integrations:

```bash
pip install 'protol-py[all]'
```

---

## Quick Start

```python
from protol import Protol

# Initialize (local_mode=True works without a backend)
p = Protol(api_key="test", local_mode=True)

# Register an agent
agent = p.register_agent(
    name="my-research-agent",
    category="research",
    capabilities=["web_research", "summarization"],
)

# Log a successful action
with agent.action(task_category="research") as act:
    result = {"findings": "AI agents are transforming software"}
    act.success(output=result, confidence=0.9)

# Log a failed action
with agent.action(task_category="data_analysis") as act:
    act.fail(error_type="timeout", error_message="API timed out")

# Check reputation
agent.refresh()
print(f"Agent: {agent.name}")
print(f"Score: {agent.reputation_score} | Tier: {agent.trust_tier}")
print(f"Breakdown: {agent.reputation_breakdown()}")

p.close()
```

---

## Core Concepts

### Agents
An agent is any AI system registered with Protol. It gets a unique ID, a reputation score, and a full action history.

### Actions
Actions are everything agents do — tasks completed, APIs called, other agents hired. Every action is logged with status, timing, cost, and hashed I/O (raw data never leaves your system).

### Reputation Scores
Reputation is computed across 5 dimensions:
- **Reliability** (30%) — Success rate weighted by volume
- **Safety** (25%) — Inverse of incident frequency/severity
- **Consistency** (20%) — Stability of performance (low variance)
- **Efficiency** (15%) — Cost relative to category peers
- **Transparency** (10%) — How much metadata is provided

### Trust Tiers
| Tier | Score Range |
|------|------------|
| Platinum | 90–100 |
| Gold | 75–89 |
| Silver | 60–74 |
| Bronze | 40–59 |
| Unverified | 0–39 |

---

## Detailed Usage

### Registering Agents

```python
agent = p.register_agent(
    name="my-agent",
    category="research",           # See constants.py for full list
    capabilities=["web_research", "summarization"],
    model_provider="anthropic",
    model_name="claude-3.5-sonnet",
    framework="langchain",
    autonomy_level="semi",         # 'assisted' | 'semi' | 'autonomous'
    description="A research agent that finds and summarizes information",
    tags=["prod", "research"],
)
```

### Logging Actions — Context Manager

```python
with agent.action(
    task_category="research",
    commissioned_by="user_123",
    commissioner_type="human",
    description="Research competitive landscape",
) as act:
    result = my_agent.run(query)
    act.success(output=result, confidence=0.87, cost_usd=0.03)

print(f"Action ID: {act.action_id}")
print(f"Duration: {act.duration_ms}ms")
```

If an exception occurs and `success()`/`fail()` wasn't called, the action is automatically recorded as `error`. If the block exits cleanly without a call, it's recorded as `success`.

### Logging Actions — Manual

```python
response = agent.log_action(
    action_type="api_call",
    status="success",
    task_category="data_analysis",
    cost_usd=0.05,
    self_reported_confidence=0.92,
)
```

### Querying Reputation

```python
agent.refresh()

print(agent.reputation_score)      # 82.5
print(agent.trust_tier)            # "Gold"

breakdown = agent.reputation_breakdown()
print(breakdown.reliability)       # 85.0
print(breakdown.safety)            # 95.0

history = agent.reputation_history(days=30)
for snapshot in history:
    print(f"{snapshot.computed_at}: {snapshot.overall_score}")
```

### Searching Agents

```python
results = p.search_agents(
    category="research",
    min_reputation=75.0,
    sort_by="reputation",
)

for agent_profile in results.agents:
    print(f"{agent_profile.name}: {agent_profile.reputation.overall_score}")
```

### Reporting Incidents

```python
p.report_incident(
    agent_id="agt_abc123def",
    incident_type="hallucination",
    severity="high",
    title="Agent fabricated research data",
    description="The agent produced citations to papers that do not exist.",
)
```

### LangChain Integration

```python
from protol import Protol
from protol.integrations import LangChainWrapper
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

p = Protol(api_key="aos_sk_...", local_mode=True)
agent = p.register_agent(
    name="lc-agent", category="writing", capabilities=["summarization"]
)

chain = ChatPromptTemplate.from_template("Summarize: {text}") | ChatOpenAI(model="gpt-4")

tracked = LangChainWrapper(runnable=chain, agent=agent, task_category="writing")
result = tracked.invoke({"text": "Your text here..."})
# Action automatically logged with timing, status, and I/O hashes
```

### CrewAI Integration

```python
from protol import Protol
from protol.integrations import CrewAIWrapper

p = Protol(api_key="aos_sk_...", local_mode=True)
researcher = p.register_agent(name="researcher", category="research", capabilities=["web_research"])
writer = p.register_agent(name="writer", category="writing", capabilities=["content_writing"])

tracked_crew = CrewAIWrapper(
    crew=my_crew,
    agent_mapping={"researcher": researcher, "writer": writer},
)
result = tracked_crew.kickoff(inputs={"topic": "AI agents"})
# Each crew member's actions are individually tracked
```

### Async Usage

```python
from protol import AsyncProtol

async with AsyncProtol(api_key="aos_sk_...", local_mode=True) as p:
    agent = await p.register_agent(
        name="async-agent", category="research", capabilities=["test"]
    )

    async with agent.action(task_category="research") as act:
        result = await some_async_work()
        act.success(output=result)
```

### Error Handling

```python
from protol import Protol
from protol.exceptions import (
    AuthenticationError, NotFoundError, RateLimitError, ValidationError
)

try:
    p = Protol(api_key="aos_sk_your_key")
    agent = p.get_agent("agt_abc123def")
except AuthenticationError:
    print("Invalid API key")
except NotFoundError:
    print("Agent not found")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after_seconds}s")
except ValidationError as e:
    print(f"Invalid input: {e.message}")
```

### Local Mode

Local mode lets you use the full SDK without a backend — perfect for development, CI/CD, and demos:

```python
p = Protol(api_key="any-key", local_mode=True)
```

In local mode:
- No HTTP calls are made
- Agents/actions stored in memory
- Full 5-dimension reputation scoring computed locally
- All methods return realistic response objects
- Global `environment` param works the same way

### Global Environment

Set a default environment for all actions:

```python
# All actions default to "test" — won't affect production reputation
p = Protol(api_key="test", local_mode=True, environment="test")
agent = p.register_agent(...)

with agent.action(task_category="research") as act:
    act.success(output="test data")  # environment="test"

# Override per-action:
with agent.action(task_category="research", environment="production") as act:
    act.success(output="real data")  # environment="production"
```

---

## Data Privacy

The SDK **never** sends raw input/output data to the API. Only SHA-256 hashes are transmitted. This is enforced at the code level — there is no option to send raw data.

---

## API Reference

Full API documentation: [https://docs.protol.dev](https://docs.protol.dev)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

---

## License

MIT — see [LICENSE](LICENSE) for details.
