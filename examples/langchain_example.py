"""LangChain integration example.

Install: pip install 'protol-py[langchain]' langchain-openai

This example demonstrates wrapping a LangChain runnable with Protol tracking.
Every invoke/batch/stream call is automatically logged as an action.
"""

from __future__ import annotations

from protol import Protol
from protol.integrations import LangChainWrapper

# --- Minimal mock runnable so the example runs without OpenAI key ---
from langchain_core.runnables import RunnableLambda  # type: ignore[import-untyped]

echo_chain = RunnableLambda(lambda x: f"Echo: {x.get('text', '')}")

# --- Initialize ---
p = Protol(api_key="test", local_mode=True)
agent = p.register_agent(
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

p.close()
print("\nDone!")
