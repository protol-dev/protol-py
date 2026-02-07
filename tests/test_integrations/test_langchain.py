"""Tests for LangChain integration."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock

import protol.integrations.langchain as _lc_mod
from protol.client import Protol


class MockRunnable:
    """Mock LangChain Runnable for testing."""

    def invoke(self, input, **kwargs):
        return f"Response to: {input}"

    async def ainvoke(self, input, **kwargs):
        return f"Async response to: {input}"

    def stream(self, input, **kwargs):
        for word in ["Hello", " ", "World"]:
            yield word

    def batch(self, inputs, **kwargs):
        return [f"Response to: {inp}" for inp in inputs]


class MockFailingRunnable:
    """Mock runnable that raises on invoke."""

    def invoke(self, input, **kwargs):
        raise RuntimeError("LangChain invoke failed")

    async def ainvoke(self, input, **kwargs):
        raise RuntimeError("LangChain async invoke failed")


class TestLangChainWrapper:
    @pytest.fixture(autouse=True)
    def _patch_runnable(self, monkeypatch):
        """Allow instantiation even without langchain-core installed."""
        monkeypatch.setattr(_lc_mod, "Runnable", object)

    @pytest.fixture
    def aos_and_agent(self):
        aos = Protol(api_key="test", local_mode=True)
        agent = aos.register_agent(
            name="lc-test-agent",
            category="research",
            capabilities=["summarization"],
        )
        yield aos, agent
        aos.close()

    def test_invoke_logs_success(self, aos_and_agent):
        aos, agent = aos_and_agent
        # Import directly to avoid langchain_core dependency
        from protol.integrations.langchain import LangChainWrapper

        wrapper = LangChainWrapper(
            runnable=MockRunnable(),
            agent=agent,
            task_category="research",
        )

        result = wrapper.invoke("test query")
        assert result == "Response to: test query"

        # Verify action was logged
        actions = agent.get_actions()
        assert len(actions) == 1
        assert actions[0].status == "success"

    def test_invoke_logs_failure(self, aos_and_agent):
        aos, agent = aos_and_agent
        from protol.integrations.langchain import LangChainWrapper

        wrapper = LangChainWrapper(
            runnable=MockFailingRunnable(),
            agent=agent,
            task_category="research",
        )

        with pytest.raises(RuntimeError, match="invoke failed"):
            wrapper.invoke("test query")

        actions = agent.get_actions()
        assert len(actions) == 1
        assert actions[0].status == "failed"

    def test_batch_logs_each(self, aos_and_agent):
        aos, agent = aos_and_agent
        from protol.integrations.langchain import LangChainWrapper

        wrapper = LangChainWrapper(
            runnable=MockRunnable(),
            agent=agent,
            task_category="writing",
        )

        results = wrapper.batch(["q1", "q2", "q3"])
        assert len(results) == 3

        actions = agent.get_actions()
        assert len(actions) == 3

    def test_stream_logs_after_completion(self, aos_and_agent):
        aos, agent = aos_and_agent
        from protol.integrations.langchain import LangChainWrapper

        wrapper = LangChainWrapper(
            runnable=MockRunnable(),
            agent=agent,
            task_category="research",
        )

        chunks = list(wrapper.stream("test input"))
        assert chunks == ["Hello", " ", "World"]

        actions = agent.get_actions()
        assert len(actions) == 1
        assert actions[0].status == "success"
