from typing import TypedDict, List, Any, Optional, Dict
from langgraph.graph import StateGraph

# Import your nodes (Ensure folder name is consistent: 'graphs' or 'graph')
from graphs.repo_reader_node import repo_reader_node
from graphs.static_analyzer_node import static_analyzer_node
from graphs.llm_reviewer_node import llm_reviewer_node
from graphs.issue_categorizer_node import issue_categorizer_node
from graphs.priority_node import priority_node
from graphs.aggregator_node import aggregator_node

# --- DEFINING THE SHARED MEMORY (STATE) ---
class MultiAgentState(TypedDict, total=False):
    # Inputs
    repo_input: str
    git_url: Optional[str]
    
    # Agent 1 (Reader)
    repo_path: str
    code_files: List[str]
    repo_summary: Any

    # Agent 2 (Static)
    static_issues: List[Any]

    # Agent 3 (LLM Review)
    llm_detected_issues: List[Dict[str, Any]]
    overall_quality_score: float
    llm_recommendations: List[str]
    llm_raw_response: Optional[str]

    # Agent 4 (Categorizer)
    categorized_issues: List[Dict[str, Any]]
    categorized_summary: Dict[str, Any]

    # Agent 5 (Priority)
    prioritized_issues: List[Dict[str, Any]]
    priority_summary: Dict[str, Any]

    # Agent 6 (Aggregator - Final Output)
    final_output: Dict[str, Any]


def build_full_pipeline():
    # Use the TypedDict State
    graph = StateGraph(MultiAgentState)

    # 1. Register Agents
    graph.add_node("repo_reader", repo_reader_node)
    graph.add_node("static_analyzer", static_analyzer_node)
    graph.add_node("llm_reviewer", llm_reviewer_node)
    graph.add_node("issue_categorizer", issue_categorizer_node)
    graph.add_node("priority_agent", priority_node)
    graph.add_node("aggregator", aggregator_node)

    # 2. Build Linear Flow
    graph.set_entry_point("repo_reader")
    
    graph.add_edge("repo_reader", "static_analyzer")
    graph.add_edge("static_analyzer", "llm_reviewer")
    graph.add_edge("llm_reviewer", "issue_categorizer")
    graph.add_edge("issue_categorizer", "priority_agent")
    graph.add_edge("priority_agent", "aggregator")
    
    graph.set_finish_point("aggregator")

    return graph.compile()