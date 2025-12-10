import subprocess
import json
import os
from radon.complexity import cc_visit
from radon.cli.harvest import CCHarvester


def run_bandit(repo_path):
    """
    Runs Bandit to detect security issues.
    Returns a list of issue dicts.
    """
    try:
        result = subprocess.run(
            ["bandit", "-r", repo_path, "-f", "json"],
            capture_output=True, text=True
        )

        bandit_output = json.loads(result.stdout)
        issues = []

        for item in bandit_output.get("results", []):
            issues.append({
                "file": item.get("filename"),
                "line": item.get("line_number"),
                "severity": item.get("issue_severity"),
                "type": "security",
                "tool": "bandit",
                "message": item.get("issue_text")
            })

        return issues

    except Exception as e:
        print("Bandit failed:", e)
        return []
    

def run_flake8(repo_path):
    """
    Runs flake8 for style issues.
    Returns list of issue dicts.
    """
    try:
        result = subprocess.run(
            ["flake8", repo_path, "--format=%(path)s:::%(row)d:::%(text)s"],
            capture_output=True, text=True
        )

        issues = []
        for line in result.stdout.splitlines():
            try:
                file_path, row, msg = line.split(":::")
                issues.append({
                    "file": file_path,
                    "line": int(row),
                    "type": "style",
                    "tool": "flake8",
                    "message": msg,
                    "severity": "LOW"
                })
            except:
                continue

        return issues

    except Exception as e:
        print("Flake8 failed:", e)
        return []


def run_radon_complexity(file_path):
    """
    Uses radon to compute cyclomatic complexity.
    """
    if not file_path.endswith(".py"):
        return []
    issues = []
    try:
        with open(file_path, "r") as f:
            code = f.read()

        results = cc_visit(code)

        for r in results:
            if r.complexity >= 10:  # threshold
                issues.append({
                    "file": file_path,
                    "line": r.lineno,
                    "type": "complexity",
                    "tool": "radon",
                    "value": r.complexity,
                    "severity": "MEDIUM" if r.complexity < 20 else "HIGH",
                    "message": f"High cyclomatic complexity ({r.complexity}) in function {r.name}"
                })

    except Exception as e:
        print(f"Radon error in {file_path}:", e)

    return issues


def run_static_analyzers(repo_path, code_files):
    """
    Executes Bandit, Flake8, and Radon across repo.
    Returns combined list of issues.
    """

    issues = []

    # 1. Security issues (Bandit)
    issues.extend(run_bandit(repo_path))

    # 2. Style issues (Flake8)
    issues.extend(run_flake8(repo_path))

    # 3. Complexity issues (Radon)
    for file_path in code_files:
        issues.extend(run_radon_complexity(file_path))

    return issues
