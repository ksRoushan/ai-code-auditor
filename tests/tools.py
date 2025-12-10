# -----------------------------
# 1. Imports
# -----------------------------
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
from langchain.messages import (
    SystemMessage,
    HumanMessage,
    ToolMessage,
    AnyMessage
)
from typing_extensions import TypedDict, Annotated
import operator

from langgraph.graph import StateGraph, START, END


# -----------------------------
# 2. Initialize Gemini Model
# -----------------------------
model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",   # YOU CAN CHANGE MODEL HERE
    temperature=0,
    api_key="AIzaSyCL-GilOp59xjcYRXYIa9atEXzpnZYRDmw"        # <- Replace with your key
)


# -----------------------------
# 3. Define Tools
# -----------------------------
@tool
def add(a: int, b: int) -> int:
    """Adds two numbers."""
    return a + b

@tool
def multiply(a: int, b: int) -> int:
    """Multiplies two numbers."""
    return a * b

@tool
def divide(a: int, b: int) -> float:
    """Divides two numbers."""
    return a / b


tools = [add, multiply, divide]
tools_by_name = {t.name: t for t in tools}

# Bind tools to model (VERY IMPORTANT)
model_with_tools = model.bind_tools(tools)


# -----------------------------
# 4. Define Agent State
# -----------------------------
class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int


# -----------------------------
# 5. Node: LLM Call
# -----------------------------
def llm_call(state: MessagesState):
    """Call Gemini and let it decide whether to call a tool."""

    system_prompt = SystemMessage(
        content="You are a helpful assistant that performs arithmetic using tools."
    )

    response = model_with_tools.invoke(
        [system_prompt] + state["messages"]
    )

    return {
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1
    }


# -----------------------------
# 6. Node: Execute Tool
# -----------------------------
def tool_node(state: MessagesState):
    """Executes tool calls returned by the LLM."""

    tool_results = []

    last_msg = state["messages"][-1]

    for call in last_msg.tool_calls:
        tool = tools_by_name[call["name"]]
        result = tool.invoke(call["args"])

        tool_results.append(
            ToolMessage(
                content=str(result),
                tool_call_id=call["id"]
            )
        )

    return {"messages": tool_results}


# -----------------------------
# 7. Control Logic: Should Continue?
# -----------------------------
def should_continue(state: MessagesState):
    """Return next node or END based on tool calls."""

    last_msg = state["messages"][-1]

    if last_msg.tool_calls:   # LLM requested a tool
        return "tool_node"

    return END                # No more tools → end run


# -----------------------------
# 8. Build Graph
# -----------------------------
agent_builder = StateGraph(MessagesState)

agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("tool_node", tool_node)

agent_builder.add_edge(START, "llm_call")

agent_builder.add_conditional_edges(
    "llm_call",
    should_continue,
    ["tool_node", END]
)

agent_builder.add_edge("tool_node", "llm_call")

agent = agent_builder.compile()


# -----------------------------
# 9. RUN INFERENCE
# -----------------------------
if __name__ == "__main__":
    print("\n=== Gemini Tool Agent ===\n")

    user_input = "Multiply 5 and 7, then divide by 2."

    print("User:", user_input)
    result_state = agent.invoke({"messages": [HumanMessage(content=user_input)]})

    print("\n=== Final Messages ===\n")
    for m in result_state["messages"]:
        m.pretty_print()
