"""
VitalGuard v2 — LangGraph Agent Pipeline
5-node clinical reasoning chain with shared memory:
  vitals_agent → prediction_agent → risk_agent → action_agent → communication_agent

Rule engine CRITICAL triggers a shortcut path that bypasses prediction/risk.
"""

from langgraph.graph import StateGraph, END
from .nodes import (
    AgentState,
    vitals_agent,
    prediction_agent,
    risk_agent,
    action_agent,
    communication_agent,
)


def _should_skip_to_action(state: AgentState) -> str:
    """
    If rule engine already says CRITICAL (score >= 81), skip prediction
    and risk agents — go straight to action. Speed matters in emergencies.
    For non-critical, run the full pipeline for richer analysis.
    """
    score = state.get("risk_assessment", {}).get("score", 0)
    if score >= 81:
        return "action_agent"
    if score <= 30:
        # Low risk: skip prediction, go to risk for validation
        return "risk_agent"
    return "prediction_agent"


def build_agent():
    """Build the 5-node LangGraph agent pipeline."""
    graph = StateGraph(AgentState)

    # Add all 5 nodes
    graph.add_node("vitals_agent", vitals_agent)
    graph.add_node("prediction_agent", prediction_agent)
    graph.add_node("risk_agent", risk_agent)
    graph.add_node("action_agent", action_agent)
    graph.add_node("communication_agent", communication_agent)

    # Entry point
    graph.set_entry_point("vitals_agent")

    # Conditional routing after vitals analysis
    graph.add_conditional_edges(
        "vitals_agent",
        _should_skip_to_action,
        {
            "prediction_agent": "prediction_agent",
            "risk_agent": "risk_agent",
            "action_agent": "action_agent",
        },
    )

    # Linear chain for the remaining nodes
    graph.add_edge("prediction_agent", "risk_agent")
    graph.add_edge("risk_agent", "action_agent")
    graph.add_edge("action_agent", "communication_agent")
    graph.add_edge("communication_agent", END)

    return graph.compile()


# Build the compiled graph
agent_graph = build_agent()
