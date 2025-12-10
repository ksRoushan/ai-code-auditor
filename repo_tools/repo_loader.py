# repo_tools/repo_loader.py
import os
import zipfile
import tempfile
import shutil
import mimetypes
from git import Repo


CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".php",
    ".rb", ".swift", ".kt", ".rs"
}


def is_code_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    return ext in CODE_EXTENSIONS


def extract_zip(zip_path):
    temp_dir = tempfile.mkdtemp(prefix="repo_")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(temp_dir)
    return temp_dir


def clone_git_repo(git_url):
    temp_dir = tempfile.mkdtemp(prefix="repo_")
    Repo.clone_from(git_url, temp_dir)
    return temp_dir


def load_repository(input_path=None, git_url=None):
    """
    Loads a repository from ZIP or Git URL.
    Returns the extracted repo path & list of code files.
    """
    if not input_path and not git_url:
        raise ValueError("Provide either a ZIP file or a Git URL.")

    # Extract files
    if input_path:
        repo_path = extract_zip(input_path)
    else:
        repo_path = clone_git_repo(git_url)

    code_files = []

    # Walk through repo and collect code files
    for root, dirs, files in os.walk(repo_path):
        # Ignore node_modules or other big folders
        if "node_modules" in root or ".git" in root:
            continue

        for f in files:
            full_path = os.path.join(root, f)
            if is_code_file(full_path):
                code_files.append(full_path)

    return {
        "repo_path": repo_path,
        "code_files": code_files
    }
