"""
Integration layer for IBM watsonx Orchestrator.

Provides:
- Python tool wrappers that can be registered as Orchestrator tools
- Local adapters to simulate ReAct and Plan-Act flows without LangGraph

This module keeps existing LangGraph workflows intact while enabling a
progressive migration to Orchestrator-native agents.
"""

__all__ = [
    "tools",
]


