"""Protol integrations for popular agent frameworks."""

from __future__ import annotations


def __getattr__(name: str):  # type: ignore[no-untyped-def]
    if name == "LangChainWrapper":
        try:
            from protol.integrations.langchain import LangChainWrapper

            return LangChainWrapper
        except ImportError:
            raise ImportError(
                "LangChain integration requires langchain-core. "
                "Install it with: pip install 'protol-sdk[langchain]'"
            ) from None

    if name == "CrewAIWrapper":
        try:
            from protol.integrations.crewai import CrewAIWrapper

            return CrewAIWrapper
        except ImportError:
            raise ImportError(
                "CrewAI integration requires crewai. "
                "Install it with: pip install 'protol-sdk[crewai]'"
            ) from None

    raise AttributeError(f"module 'protol.integrations' has no attribute '{name}'")


__all__ = ["LangChainWrapper", "CrewAIWrapper"]
