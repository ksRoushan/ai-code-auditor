# graph/aggregator_node.py
from langgraph.graph import StateGraph

class AggregatorState(dict):
    """
    Expected fields:
      - repo_summary
      - overall_quality_score
      - prioritized_issues
      - priority_summary
      - categorized_summary
    """

def aggregator_node(state: AggregatorState):

    print("📦 Running Final Aggregator...")

    final_output = {
        "project_summary": state.get("repo_summary", {}),
        "quality_score": state.get("overall_quality_score", 5.0),
        "issues": state.get("prioritized_issues", []),
        "priority_summary": state.get("priority_summary", {}),
        "category_summary": state.get("categorized_summary", {}),
        "total_issues": len(state.get("prioritized_issues", [])),
    }

    state["final_output"] = final_output
    return state


def build_aggregator_graph():
    g = StateGraph(AggregatorState)
    g.add_node("aggregator", aggregator_node)
    g.set_entry_point("aggregator")
    g.set_finish_point("aggregator")
    return g.compile()
