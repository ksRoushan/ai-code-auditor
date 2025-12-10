# repo_tools/issue_categorizer_agent.py
import hashlib
import re
from typing import List, Dict, Any

# Canonical categories we use across the pipeline
CANONICAL_CATEGORIES = {
    "security", "performance", "bug", "maintainability", "readability", "style", "tests", "other"
}

# Mapping heuristics for static tool types to categories
STATIC_TYPE_TO_CATEGORY = {
    "security": "security",
    "complexity": "maintainability",
    "style": "style",
    "performance": "performance",
    "bug": "bug",
}

# Map various severity tokens to canonical severities
SEVERITY_MAP = {
    # bandit style
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
    # radon style numeric -> map by threshold (handled separately)
    # flake8 / generic
    "CRITICAL": "critical",
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "info": "low",
    "warning": "medium",
}

def _norm_text(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s.strip())

def _fingerprint_issue(file: str, line: Any, description: str) -> str:
    """
    Create a deterministic short id for an issue based on file, line and description.
    """
    key = f"{file}|{line}|{_norm_text(description)[:250]}"
    h = hashlib.md5(key.encode("utf-8")).hexdigest()
    return h[:10].upper()

def _map_severity(raw: Any, tool: str = None, value: Any = None) -> str:
    """
    Normalize severity into critical/high/medium/low.
    raw: could be string like 'HIGH' or numeric.
    tool: optional string name of tool (radon, bandit, flake8)
    value: numeric value (e.g., radon complexity)
    """
    if isinstance(raw, (int, float)):
        # numeric mapping: treat as score (higher = worse)
        v = float(raw)
        if v >= 30:
            return "critical"
        if v >= 20:
            return "high"
        if v >= 10:
            return "medium"
        return "low"

    if value is not None and isinstance(value, (int, float)):
        # e.g., radon complexity value
        v = float(value)
        if v >= 20:
            return "high"
        if v >= 10:
            return "medium"
        return "low"

    if isinstance(raw, str):
        raw_up = raw.strip().upper()
        return SEVERITY_MAP.get(raw_up, SEVERITY_MAP.get(raw.strip().lower(), "medium"))

    return "medium"

def _normalize_category(raw_cat: str, fallback_type: str = None) -> str:
    if not raw_cat:
        # fallback from tool/type
        if fallback_type:
            return STATIC_TYPE_TO_CATEGORY.get(fallback_type, "other")
        return "other"

    cat = raw_cat.strip().lower()
    # try to map known synonyms
    synonyms = {
        "security": "security",
        "sec": "security",
        "perf": "performance",
        "performance": "performance",
        "complexity": "maintainability",
        "maintainability": "maintainability",
        "readability": "readability",
        "style": "style",
        "lint": "style",
        "bug": "bug",
        "error": "bug",
        "tests": "tests",
        "test": "tests",
    }
    for k, v in synonyms.items():
        if cat == k or cat.startswith(k) or k in cat:
            return v

    # if cat already canonical, return it
    if cat in CANONICAL_CATEGORIES:
        return cat

    return "other"

def merge_and_categorize_issues(static_issues: List[Dict[str, Any]], llm_issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Combine static + llm issues, normalize, deduplicate, and return canonical list of issues.
    """
    merged = []

    # Process static issues first
    for it in static_issues or []:
        file = it.get("file") or it.get("filename") or "<unknown>"
        line = it.get("line") or it.get("line_number") or it.get("lineno") or None
        tool = it.get("tool") or it.get("source") or "static"
        raw_type = it.get("type") or it.get("issue_type") or None
        raw_msg = it.get("message") or it.get("issue_text") or str(it)
        value = it.get("value")  # e.g., radon complexity numeric

        category = _normalize_category(raw_type, fallback_type=raw_type)
        severity = _map_severity(it.get("severity") or it.get("issue_severity") or it.get("level"), tool=tool, value=value)

        obj = {
            "id": _fingerprint_issue(file, line, raw_msg),
            "file": file,
            "line": line,
            "category": category,
            "severity": severity,
            "description": _norm_text(raw_msg),
            "source": tool,
            "confidence": 0.9  # static tools are usually reliable
        }
        merged.append(obj)

    # Process LLM-detected issues
    for it in llm_issues or []:
        file = it.get("file") or "<unknown>"
        line = it.get("line") or None
        raw_cat = it.get("category") or ""
        severity_raw = it.get("severity") or it.get("level") or None
        desc = it.get("description") or it.get("suggestion") or str(it)

        category = _normalize_category(raw_cat, fallback_type=None)
        severity = _map_severity(severity_raw, tool="llm")

        obj = {
            "id": _fingerprint_issue(file, line, desc),
            "file": file,
            "line": line,
            "category": category,
            "severity": severity,
            "description": _norm_text(desc),
            "source": "llm",
            # LLM confidence is lower than deterministic static tools by default
            "confidence": float(it.get("confidence", 0.6))
        }
        merged.append(obj)

    # Deduplicate: keep highest-confidence entry per fingerprint
    dedup = {}
    for it in merged:
        fid = it["id"]
        prev = dedup.get(fid)
        if not prev:
            dedup[fid] = it
        else:
            # keep the one with higher confidence; if equal, keep higher severity
            if it.get("confidence", 0.5) > prev.get("confidence", 0.5):
                dedup[fid] = it
            else:
                # maybe update severity to worse one
                severity_rank = {"critical":4, "high":3, "medium":2, "low":1}
                if severity_rank.get(it["severity"],2) > severity_rank.get(prev["severity"],2):
                    prev["severity"] = it["severity"]
                # append notes to description if different
                if it["description"] != prev["description"]:
                    prev["description"] = prev["description"] + " || " + it["description"]

    # Convert to list and sort by severity + confidence
    def severity_score(s):
        mapping = {"critical": 100, "high": 75, "medium": 50, "low": 25}
        return mapping.get(s, 50)

    categorized = list(dedup.values())
    categorized.sort(key=lambda x: ( -severity_score(x.get("severity")), -x.get("confidence", 0.0), x.get("file", "")))

    # Add a small normalized category field to ensure it's canonical
    for it in categorized:
        it["category"] = it.get("category") if it.get("category") in CANONICAL_CATEGORIES else "other"

    return categorized
