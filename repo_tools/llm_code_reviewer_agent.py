# repo_tools/llm_code_reviewer_agent.py
import os
import json
import textwrap
from typing import List, Dict, Any, Optional

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

############################
# Helpers
############################
def read_snippet(file_path: str, line: Optional[int], context: int = 6) -> str:
    """
    Return a small snippet centered around `line` (1-indexed).
    If line is None or file not readable, return first ~50 lines truncated.
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e:
        return f"<unable to read file: {e}>"

    if not lines:
        return ""

    if line is None:
        # return first chunk
        snip = lines[: min(len(lines), 120)]
        return "".join(snip)

    # convert to 0-indexed
    idx = max(0, line - 1)
    start = max(0, idx - context)
    end = min(len(lines), idx + context + 1)
    snippet = lines[start:end]
    # show markers for line numbers
    numbered = []
    for i, l in enumerate(snippet, start=start + 1):
        prefix = ">> " if i == line else "   "
        numbered.append(f"{prefix}{i:>4}: {l.rstrip()}")
    return "\n".join(numbered)


def top_flagged_files(static_issues: List[Dict[str, Any]], top_n: int = 8) -> List[str]:
    """
    Choose top files by issue count to include snippets for.
    """
    counts = {}
    for it in static_issues:
        f = it.get("file")
        if not f:
            continue
        counts[f] = counts.get(f, 0) + 1
    # sort by count desc
    sorted_files = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [f for f, _ in sorted_files[:top_n]]


############################
# Main agent function
############################
def llm_code_reviewer(
    repo_path: str,
    code_files: List[str],
    repo_summary: Dict[str, Any],
    static_issues: List[Dict[str, Any]],
    max_files_with_snippets: int = 6,
) -> Dict[str, Any]:
    """
    Use an LLM to produce contextual review feedback.

    Inputs:
      - repo_path: path to extracted repository
      - code_files: list of code file paths (absolute)
      - repo_summary: parsed JSON produced by Agent 1 (dict)
      - static_issues: list of issue dicts produced by Agent 2

    Output (dict):
      {
        "llm_detected_issues": [...],
        "overall_quality_score": float,
        "recommendations": [...]
      }
    """

    # Prepare a concise structured prompt.
    # 1) Build short file list and flagged files with snippets
    code_list_small = []
    for p in code_files:
        rel = os.path.relpath(p, repo_path)
        size = 0
        try:
            size = os.path.getsize(p)
        except:
            pass
        code_list_small.append({"path": rel, "size_bytes": size})

    flagged_files = top_flagged_files(static_issues, top_n=max_files_with_snippets)
    flagged_files = flagged_files[:max_files_with_snippets]

    snippets = {}
    for f in flagged_files:
        # find absolute path in code_files
        candidates = [c for c in code_files if os.path.relpath(c, repo_path) == f or c.endswith(f)]
        if candidates:
            path = candidates[0]
            # choose a representative line if available from static issues
            # pick the first matching issue's line if present
            lines = [it.get("line") for it in static_issues if it.get("file") == f and it.get("line")]
            line = lines[0] if lines else None
            snippets[f] = {
                "rel_path": f,
                "snippet": read_snippet(path, line, context=6),
                "sample_line": line
            }
        else:
            snippets[f] = {"rel_path": f, "snippet": "<file not found on disk>", "sample_line": None}

    # 2) Build structured input JSON (embedded into prompt)
    input_payload = {
        "repo_summary": repo_summary,
        "top_code_files": code_list_small[:200],  # keep it bounded
        "static_issues_sample": static_issues[:200],  # bounded
        "flagged_file_snippets": snippets
    }

    # Create instructions: ask LLM to return strict JSON with schema
    prompt = textwrap.dedent(f"""
    You are an expert senior software engineer and code reviewer.

    You are given structured information about a repository and deterministic static analysis results.
    Your job: analyze the repo context and static issues, then produce:
      1) A list "llm_detected_issues": potential issues not caught (or clarified) by static tools, each with:
         - id (short unique string)
         - file (relative path)
         - line (number or null)
         - category (one of: security, performance, bug, maintainability, readability, style, tests)
         - severity (critical, high, medium, low)
         - description (short explanation of the problem)
         - suggestion (concrete fix or next steps)
      2) overall_quality_score: a float 0.0 - 10.0 (higher is better)
      3) recommendations: ordered list of 1-6 high-level recommendations (short strings)

    IMPORTANT: Respond with **ONLY** a single valid JSON object adhering to the EXACT schema below.
    Do NOT include any extra prose outside the JSON.

    JSON schema:
    {{
      "llm_detected_issues": [
        {{
          "id": "ISSUE-1",
          "file": "path/to/file.py",
          "line": 123,
          "category": "maintainability",
          "severity": "high",
          "description": "...",
          "suggestion": "..."
        }},
        ...
      ],
      "overall_quality_score": 7.1,
      "recommendations": ["Fix X", "Add tests for Y", ...]
    }}

    INPUT DATA (do not modify):
    {json.dumps(input_payload, indent=2)}

    Remember:
    - Be concise but precise.
    - Prefer concrete actionable suggestions.
    - When labeling severity, prefer security as higher priority if it can lead to data loss.
    - If unsure about a specific line, set line to null and explain in description.
    """)

    # Call LLM
    response = model.generate_content(prompt)
    raw = response.text

    # Parse LLM output (should be JSON)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # fallback: try to extract JSON block
        try:
            start = raw.index("{")
            end = raw.rfind("}") + 1
            candidate = raw[start:end]
            parsed = json.loads(candidate)
        except Exception as e:
            # Last resort: return a safe fallback structure
            return {
                "llm_detected_issues": [],
                "overall_quality_score": 5.0,
                "recommendations": [
                    "LLM output could not be parsed; please re-run with a larger model or inspect raw output."
                ],
                "raw_response": raw
            }

    # Ensure keys exist & normalized
    parsed.setdefault("llm_detected_issues", [])
    parsed.setdefault("overall_quality_score", 5.0)
    parsed.setdefault("recommendations", [])

    # Add small normalization: ensure numeric score
    try:
        parsed["overall_quality_score"] = float(parsed.get("overall_quality_score", 5.0))
        if parsed["overall_quality_score"] < 0:
            parsed["overall_quality_score"] = 0.0
        if parsed["overall_quality_score"] > 10:
            parsed["overall_quality_score"] = 10.0
    except:
        parsed["overall_quality_score"] = 5.0

    return parsed
