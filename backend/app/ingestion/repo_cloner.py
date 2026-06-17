import os
import shutil
from pathlib import Path
from typing import Dict, Any
import git
from app.config import get_settings

settings = get_settings()

REPO_BASE_DIR = Path("/tmp/repos")


def clone_repository(repo_url: str, review_id: str) -> str:
    """Clone a repository to a local path. Returns the local path."""
    local_path = REPO_BASE_DIR / review_id
    if local_path.exists():
        shutil.rmtree(local_path)
    local_path.mkdir(parents=True, exist_ok=True)

    git.Repo.clone_from(
        repo_url,
        str(local_path),
        depth=1,  # Shallow clone for speed
        no_single_branch=False,
    )
    return str(local_path)


def clone_local_path(source_path: str, review_id: str) -> str:
    """Copy a local directory for review (used for test repos)."""
    local_path = REPO_BASE_DIR / review_id
    if local_path.exists():
        shutil.rmtree(local_path)
    shutil.copytree(source_path, str(local_path))
    return str(local_path)


def cleanup_repo(review_id: str) -> None:
    local_path = REPO_BASE_DIR / review_id
    if local_path.exists():
        shutil.rmtree(local_path)


def detect_stack(local_path: str) -> Dict[str, Any]:
    """Detect language, framework, package manager from file heuristics. No LLM needed."""
    from app.ingestion.metadata_extractor import (
        detect_language,
        detect_framework,
        detect_package_manager,
        find_entry_points,
        find_config_files,
    )

    root = Path(local_path)
    all_files = [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()]

    language = detect_language(all_files)
    framework = detect_framework(all_files, root)
    package_manager = detect_package_manager(all_files)
    entry_points = find_entry_points(all_files, language)
    config_files = find_config_files(all_files)

    return {
        "language": language,
        "framework": framework,
        "package_manager": package_manager,
        "entry_points": entry_points,
        "config_files": config_files,
        "total_files": len(all_files),
    }
