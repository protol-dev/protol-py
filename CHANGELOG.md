# Changelog

All notable changes to `agent-os-sdk` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-02-07

### Added

- Initial release of the AgentOS Python SDK
- `AgentOS` and `AsyncAgentOS` client classes
- `Agent` class with action logging and reputation querying
- `Action` context manager for automatic action tracking
- Full Pydantic v2 model definitions for all API types
- `local_mode` for standalone usage without a backend
- LangChain integration via `LangChainWrapper`
- CrewAI integration via `CrewAIWrapper`
- Comprehensive test suite
- Examples for basic usage, LangChain, CrewAI, reputation checks, and incident reporting
