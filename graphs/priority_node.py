# graph/priority_node.py
from langgraph.graph import StateGraph
from repo_tools.priority_agent import assign_priorities, summarize_priorities

class PriorityState(dict):
    """
    Expected inputs:
      - categorized_issues: from Agent 4
    """
    
def priority_node(state):
    print("🚦 Running Priority Agent...")
    
    # Read from Agent 4's output
    categorized = state.get("categorized_issues", [])

    # Process
    prioritized = assign_priorities(categorized)
    summary = summarize_priorities(prioritized)

    # Return updates to state
    return {
        "prioritized_issues": prioritized,
        "priority_summary": summary
    }


def build_priority_graph():
    g = StateGraph(PriorityState)
    g.add_node("priority_agent", priority_node)
    g.set_entry_point("priority_agent")
    g.set_finish_point("priority_agent")
    return g.compile()
