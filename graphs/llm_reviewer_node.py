# graph/llm_reviewer_node.py
from langgraph.graph import StateGraph
from repo_tools.llm_code_reviewer_agent import llm_code_reviewer

class LLMReviewState(dict):
    """
    State object shared in graph pipeline.
    Expected inputs:
      - repo_path
      - code_files
      - repo_summary (dict)    # from Agent 1
      - static_issues (list)  # from Agent 2
    """

def llm_reviewer_node(state: LLMReviewState):
    repo_path = state.get("repo_path")
    code_files = state.get("code_files", [])
    repo_summary = state.get("repo_summary", {})
    static_issues = state.get("static_issues", [])

    print("🧠 Running LLM Code Reviewer...")

    result = llm_code_reviewer(
        repo_path=repo_path,
        code_files=code_files,
        repo_summary=repo_summary,
        static_issues=static_issues
    )

    # merge results into state
    state["llm_detected_issues"] = result.get("llm_detected_issues", [])
    state["overall_quality_score"] = result.get("overall_quality_score", 5.0)
    state["llm_recommendations"] = result.get("recommendations", [])
    # keep raw if present for debugging
    if "raw_response" in result:
        state["llm_raw_response"] = result["raw_response"]

    return state


def build_llm_reviewer_graph():
    graph = StateGraph(LLMReviewState)
    graph.add_node("llm_reviewer", llm_reviewer_node)
    graph.set_entry_point("llm_reviewer")
    graph.set_finish_point("llm_reviewer")
    return graph.compile()
