from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.ingestion import ingest_node
from agents.validation import validate_node
from agents.approval import approve_node
from agents.payment import pay_node


def route_after_approval(state):
    """Route payment if approved, else end."""
    approval = state.get("approval", {})
    if approval.get("status") == "approved":
        return "pay"
    return END


def build_graph():
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("ingest", ingest_node)
    graph.add_node("validate", validate_node)
    graph.add_node("approve", approve_node)
    graph.add_node("pay", pay_node)

    # Fixed edges
    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "validate")
    graph.add_edge("validate", "approve")

    # Conditional: only pay if approved
    graph.add_conditional_edges("approve", route_after_approval, {"pay": "pay", END: END})
    graph.add_edge("pay", END)

    return graph.compile()