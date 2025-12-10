import os
import getpass

from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
load_dotenv()

def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

# Set API key
_set_env("GOOGLE_API_KEY")

# Initialize Gemini model
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    temperature=0.2,
)


from typing_extensions import TypedDict
from langgraph.graph import END, START, StateGraph

class State(TypedDict):
    topic: str
    outline: str
    blog: str
    final_blog: str


def outline_agent(state: State):
    msg = llm.invoke(
        f"""Create a blog outline for the topic: {state['topic']} with:
        1. A catchy headline
        2. An introduction hook
        3. 3-5 main sections with 2-3 bullet points for each
        4. A concluding thought"""
    )
    return {"outline": msg.content}


def writer_agent(state: State):
    msg = llm.invoke(
        f"""Following this outline strictly: {state['outline']}
        Write a brief, 200 to 300-word blog post with an engaging and informative tone."""
    )
    return {"blog": msg.content}


def editor_agent(state: State):
    msg = llm.invoke(
        f"""Edit this draft: {state['blog']}
        Your task is to polish the text by fixing any grammatical errors,
        improving the flow and sentence structure, and enhancing overall clarity."""
    )
    return {"final_blog": msg.content}


workflow = StateGraph(State)

workflow.add_node("outline_agent", outline_agent)
workflow.add_node("writer_agent", writer_agent)
workflow.add_node("editor_agent", editor_agent)

workflow.add_edge(START, "outline_agent")
workflow.add_edge("outline_agent", "writer_agent")
workflow.add_edge("writer_agent", "editor_agent")
workflow.add_edge("editor_agent", END)

agent = workflow.compile()

state = agent.invoke({
    "topic": "Write a blog post about the benefits of multi-agent systems for software developers"
})

print("Outline:")
print(state["outline"])
print("\n--- --- ---\n")

print("Blog:")
print(state["blog"])
print("\n--- --- ---\n")

print("Final Blog:")
print(state["final_blog"])
print("\n--- --- ---\n")
