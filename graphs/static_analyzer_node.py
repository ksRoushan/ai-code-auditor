from typing import TypedDict, List, Any
from langgraph.graph import StateGraph
from repo_tools.static_analyzer_agent import run_static_analyzers

# Define the schema explicitly
class AnalyzerState(TypedDict, total=False):
    repo_path: str
    code_files: List[str]
    static_issues: List[Any]

def static_analyzer_node(state: AnalyzerState):
    # Now these keys will actually exist
    repo_path = state.get("repo_path") 
    code_files = state.get("code_files")

    if not repo_path:
        return {"static_issues": ["Error: No repo_path provided"]}

    print("🔍 Running Static Analyzer...")
    static_issues = run_static_analyzers(repo_path, code_files)

    return {"static_issues": static_issues}

def build_static_analyzer_graph():
    graph = StateGraph(AnalyzerState)
    graph.add_node("static_analyzer", static_analyzer_node)
    graph.set_entry_point("static_analyzer")
    graph.set_finish_point("static_analyzer")
    return graph.compile()