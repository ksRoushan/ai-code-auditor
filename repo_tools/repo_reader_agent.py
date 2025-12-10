import os
import re
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Load Gemini API key from .env
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY missing in .env")

genai.configure(api_key=GOOGLE_API_KEY)

# Initialize Gemini 2.5 Flash
model = genai.GenerativeModel("gemini-2.5-flash")


def summarize_file_structure(repo_path, code_files):
    """
    Build a simple directory tree structure for summarization.
    """
    tree = {}

    for file_path in code_files:
        rel = os.path.relpath(file_path, repo_path)
        parts = rel.split(os.sep)

        node = tree
        for p in parts:
            if p not in node:
                node[p] = {}
            node = node[p]

    return tree


def llm_repo_reader(repo_path, code_files):
    """
    Uses Gemini to summarize the repository.
    Returns a Python dict (parsed JSON).
    """

    file_tree = summarize_file_structure(repo_path, code_files)

    prompt = f"""
You are a senior software engineer. Analyze this repository structure:

Repository path: {repo_path}

Code files:
{code_files}

Directory tree:
{file_tree}

Respond ONLY in valid JSON with keys:
- project_type
- languages
- important_files
- missing_elements
- concerns
"""

    response = model.generate_content(prompt)

    raw = response.text.strip()

    # Parse JSON safely
    clean_json = raw.replace("```json", "").replace("```", "").strip()

    # Parse JSON safely
    try:
        parsed = json.loads(clean_json)
    except json.JSONDecodeError:
        # Fallback: Try to find JSON object with regex if simple strip fails
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except:
                 parsed = {"error": "Regex found JSON-like structure but failed to parse", "raw": raw}
        else:
            parsed = {
                "error": "LLM returned invalid JSON",
                "raw_response": raw
            }

    return parsed
