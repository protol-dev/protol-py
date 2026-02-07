# test_real_backend.py

from protol import Protol
import requests

# Step 1: Sign up
print("=== Signing up ===")
r = requests.post("http://localhost:8000/v1/auth/signup", json={
    "email": "shravan@protol.dev",
    "password": "SecurePass123",
    "display_name": "Shravan Labs",
})
print(r.status_code, r.json())

# Step 2: Login
print("\n=== Logging in ===")
r = requests.post("http://localhost:8000/v1/auth/login", json={
    "email": "shravan@protol.dev",
    "password": "SecurePass123",
})
tokens = r.json()
print(r.status_code, tokens)
jwt_token = tokens.get("access_token", "")

# Step 3: Create API key
print("\n=== Creating API key ===")
r = requests.post("http://localhost:8000/v1/owners/me/api-keys",
    headers={"Authorization": f"Bearer {jwt_token}"},
    json={"name": "Test Key"},
)
key_data = r.json()
print(r.status_code, key_data)
api_key = key_data.get("key", "")

# Step 4: Use the SDK with real backend
print("\n=== SDK connected to real backend ===")
p = Protol(api_key=api_key, base_url="http://localhost:8000/v1")

agent = p.register_agent(
    name="shravan-research-bot",
    category="research",
    capabilities=["web_research", "summarization"],
    model_provider="anthropic",
    model_name="claude-3.5-sonnet",
)
print(f"Agent registered: {agent.id}")
print(f"Score: {agent.reputation_score}")

# Log some actions
for i in range(10):
    with agent.action(task_category="research") as act:
        act.success(output=f"research result {i}", confidence=0.85, cost_usd=0.03)

print(f"\nLogged 10 actions")

# Refresh and check
agent.refresh()
print(f"Score after actions: {agent.reputation_score}")
print(f"Tier: {agent.trust_tier}")

# Search
results = p.search_agents(category="research")
print(f"\nSearch results: {len(results.agents)} agents found")

# Ecosystem stats
stats = p.get_ecosystem_stats()
print(f"Ecosystem: {stats.total_agents} agents, {stats.total_actions} actions")

p.close()
print("\n=== Done. Backend + SDK working end-to-end. ===")