# graph/issue_categorizer_node.py
from langgraph.graph import StateGraph
from repo_tools.issue_categorizer_agent import merge_and_categorize_issues
from typing import TypedDict, List, Dict, Any

class CategorizerState(TypedDict, total=False):
    static_issues: List[Any]
    llm_review: Dict[str, Any]  # <--- This holds the LLM issues
    categorized_issues: List[Any]
    categorized_summary: Dict[str, Any]
    
def issue_categorizer_node(state):
    print("🗂️ Running Issue Categorizer...")

    static = state.get("static_issues", [])
    
    # FIX: Read directly from the key your node writes to
    llm_issues = state.get("llm_detected_issues", [])  

    # Merge & Categorize
    categorized = merge_and_categorize_issues(static, llm_issues)

    # ... rest of the logic remains the same ...
    summary = {"total": len(categorized), "by_severity": {}, "by_category": {}}
    for issue in categorized:
        sev = issue.get("severity", "medium")
        summary["by_severity"][sev] = summary["by_severity"].get(sev, 0) + 1
        cat = issue.get("category", "other")
        summary["by_category"][cat] = summary["by_category"].get(cat, 0) + 1

    return {
        "categorized_issues": categorized,
        "categorized_summary": summary
    }


def build_issue_categorizer_graph():
    g = StateGraph(CategorizerState)
    g.add_node("issue_categorizer", issue_categorizer_node)
    g.set_entry_point("issue_categorizer")
    g.set_finish_point("issue_categorizer")
    return g.compile()
