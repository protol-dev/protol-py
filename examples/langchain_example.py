"""LangChain integration example.

Install: pip install 'agent-os-sdk[langchain]' langchain-openai

This example demonstrates wrapping a LangChain runnable with AgentOS tracking.
Every invoke/batch/stream call is automatically logged as an action.
"""

from __future__ import annotations

from agent_os import AgentOS
from agent_os.integrations import LangChainWrapper

# --- Minimal mock runnable so the example runs without OpenAI key ---
from langchain_core.runnables import RunnableLambda  # type: ignore[import-untyped]

echo_chain = RunnableLambda(lambda x: f"Echo: {x.get('text', '')}")

# --- Initialize ---
aos = AgentOS(api_key="test", local_mode=True)
agent = aos.register_agent(
    name="lc-agent",
    category="writing",
    capabilities=["summarization", "text_generation"],
    framework="langchain",
)

# Wrap the chain
tracked = LangChainWrapper(
    runnable=echo_chain,
    agent=agent,
    task_category="writing",
)

# --- invoke ---
result = tracked.invoke({"text": "Hello from LangChain"})
print(f"invoke result: {result}")

# --- batch ---
results = tracked.batch([
    {"text": "First item"},
    {"text": "Second item"},
    {"text": "Third item"},
])
print(f"batch results: {results}")

# --- Check reputation after tracked calls ---
agent.refresh()
print(f"\nActions logged: {agent.total_actions}")
print(f"Reputation: {agent.reputation_score} ({agent.trust_tier})")

aos.close()
print("\nDone!")
