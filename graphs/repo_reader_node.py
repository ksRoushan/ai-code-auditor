from langgraph.graph import StateGraph
from repo_tools.repo_loader import load_repository
from repo_tools.repo_reader_agent import llm_repo_reader
from typing import TypedDict, Optional, List, Any


class RepoState(TypedDict, total=False):
    repo_input: Optional[str]
    git_url: Optional[str]
    repo_path: Optional[str]
    code_files: Optional[List[str]]
    repo_summary: Optional[Any]

def repo_reader_node(state: RepoState):
    repo_input = state.get("repo_input")
    git_url = state.get("git_url")

    repo_data = load_repository(
        input_path=repo_input,
        git_url=git_url
    )

    state["repo_path"] = repo_data["repo_path"]
    state["code_files"] = repo_data["code_files"]

    # Run LLM repo reader
    summary = llm_repo_reader(
        repo_data["repo_path"],
        repo_data["code_files"]
    )

    state["repo_summary"] = summary
    return state


def build_repo_reader_graph():
    graph = StateGraph(RepoState)
    graph.add_node("repo_reader", repo_reader_node)
    graph.set_entry_point("repo_reader")
    graph.set_finish_point("repo_reader")
    return graph.compile()
