from langgraph.graph import StateGraph, END
from .nodes import AgentState, analyze_vitals, handle_normal, handle_future, handle_critical

def route_condition(state: AgentState) -> str:
    cond = state.get("condition")
    if cond == "critical":
        return "critical"
    elif cond == "future_alert":
        return "future_alert"
    return "normal"

def build_agent():
    graph = StateGraph(AgentState)
    
    graph.add_node("analyze", analyze_vitals)
    graph.add_node("normal", handle_normal)
    graph.add_node("future_alert", handle_future)
    graph.add_node("critical", handle_critical)
    
    graph.add_conditional_edges(
        "analyze",
        route_condition,
        {
            "normal": "normal",
            "future_alert": "future_alert",
            "critical": "critical"
        }
    )
    
    graph.add_edge("normal", END)
    graph.add_edge("future_alert", END)
    graph.add_edge("critical", END)
    
    graph.set_entry_point("analyze")
    
    return graph.compile()

agent_graph = build_agent()
