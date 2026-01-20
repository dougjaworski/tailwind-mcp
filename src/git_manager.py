"""Git repository management for Tailwind CSS documentation."""

import os
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

TAILWIND_REPO_URL = "https://github.com/tailwindlabs/tailwindcss.com.git"


def clone_or_update(target_path: str) -> bool:
    """
    Clone the Tailwind CSS documentation repository or update if it already exists.

    Args:
        target_path: Directory where the repository should be cloned

    Returns:
        bool: True if successful, False otherwise
    """
    target_dir = Path(target_path)

    try:
        if target_dir.exists() and (target_dir / ".git").exists():
            logger.info(f"Repository already exists at {target_path}, updating...")
            result = subprocess.run(
                ["git", "pull"],
                cwd=target_path,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Git pull output: {result.stdout}")
            logger.info("Repository updated successfully")
            return True
        else:
            logger.info(f"Cloning repository to {target_path}...")
            target_dir.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(
                ["git", "clone", TAILWIND_REPO_URL, str(target_path)],
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Git clone output: {result.stdout}")
            logger.info("Repository cloned successfully")
            return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Git operation failed: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during git operation: {e}")
        return False


def get_docs_path(repo_path: str) -> Path:
    """
    Get the path to the documentation directory within the repository.

    Args:
        repo_path: Root path of the cloned repository

    Returns:
        Path: Path to the docs directory
    """
    return Path(repo_path) / "src" / "docs"


def is_repo_ready(repo_path: str) -> bool:
    """
    Check if the repository is cloned and has documentation files.

    Args:
        repo_path: Root path of the repository

    Returns:
        bool: True if repo is ready, False otherwise
    """
    docs_path = get_docs_path(repo_path)
    return docs_path.exists() and any(docs_path.glob("**/*.mdx"))
