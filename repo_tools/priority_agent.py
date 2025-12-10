# repo_tools/priority_agent.py
from typing import List, Dict, Any

# Priority ranking — full pipeline uses these
PRIORITY_ORDER = ["critical", "high", "medium", "low"]

# Used to rank severity inside logic
SEVERITY_SCORE = {
    "critical": 100,
    "high": 75,
    "medium": 50,
    "low": 25
}

CATEGORY_WEIGHT = {
    "security": 100,
    "performance": 60,
    "bug": 70,
    "maintainability": 40,
    "readability": 20,
    "style": 10,
    "tests": 30,
    "other": 15,
}


def compute_priority_score(issue: Dict[str, Any]) -> float:
    """
    Computes a weighted priority score combining severity + category + confidence.
    Purpose: convert messy inputs into a clean ranking.
    """

    severity = issue.get("severity", "medium").lower()
    category = issue.get("category", "other").lower()
    confidence = issue.get("confidence", 0.6)

    sev_score = SEVERITY_SCORE.get(severity, 50)
    cat_score = CATEGORY_WEIGHT.get(category, 20)

    # Weighted formula — fully deterministic
    score = (sev_score * 0.6) + (cat_score * 0.3) + (confidence * 20)

    return float(score)


def score_to_priority(score: float) -> str:
    """
    Maps numeric score → priority label.
    Adjust thresholds for your needs.
    """
    if score >= 85:
        return "critical"
    if score >= 65:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def assign_priorities(categorized_issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    For each issue:
      - Calculate a numeric priority score
      - Convert to human-friendly priority
      - Sort by highest priority
    """

    results = []

    for it in categorized_issues:
        score = compute_priority_score(it)
        priority = score_to_priority(score)

        new_obj = dict(it)
        new_obj["priority_score"] = score
        new_obj["priority"] = priority

        results.append(new_obj)

    # Sort issues by score DESC, break ties by file name
    results.sort(key=lambda x: (-x["priority_score"], x.get("file", "")))

    return results


def summarize_priorities(issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Creates a summary useful for dashboards:
    {
      "critical": 2,
      "high": 5,
      "medium": 3,
      "low": 1
    }
    """

    summary = {p: 0 for p in PRIORITY_ORDER}
    for it in issues:
        pr = it.get("priority", "medium")
        summary[pr] = summary.get(pr, 0) + 1

    return summary
