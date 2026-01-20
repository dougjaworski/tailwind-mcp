"""SQLite FTS5 indexer for Tailwind CSS documentation."""

import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict

from .parser import parse_mdx_file
from .git_manager import get_docs_path

logger = logging.getLogger(__name__)


def create_database(db_path: str) -> sqlite3.Connection:
    """
    Create SQLite database with FTS5 tables for documentation search.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        sqlite3.Connection: Database connection
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create FTS5 virtual table for full-text search
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
            filepath,
            title,
            content,
            section,
            description
        )
    """)

    # Create metadata table for structured data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS doc_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT UNIQUE,
            title TEXT,
            section TEXT,
            utility_classes TEXT,
            code_examples TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create index on filepath for faster lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_filepath
        ON doc_metadata(filepath)
    """)

    conn.commit()
    logger.info("Database schema created successfully")
    return conn


def index_documentation(repo_path: str, db_path: str) -> int:
    """
    Index all MDX documentation files into the SQLite database.

    Args:
        repo_path: Path to the cloned Tailwind CSS repository
        db_path: Path to the SQLite database file

    Returns:
        int: Number of documents indexed
    """
    docs_path = get_docs_path(repo_path)

    if not docs_path.exists():
        logger.error(f"Documentation path does not exist: {docs_path}")
        return 0

    # Create or connect to database
    conn = create_database(db_path)
    cursor = conn.cursor()

    # Clear existing data
    cursor.execute("DELETE FROM docs_fts")
    cursor.execute("DELETE FROM doc_metadata")
    conn.commit()

    # Find all MDX files
    mdx_files = list(docs_path.glob("**/*.mdx"))
    logger.info(f"Found {len(mdx_files)} MDX files to index")

    indexed_count = 0
    skipped_count = 0

    for mdx_file in mdx_files:
        try:
            # Parse the MDX file
            doc_data = parse_mdx_file(mdx_file)

            if doc_data is None:
                skipped_count += 1
                continue

            # Insert into FTS5 table
            cursor.execute("""
                INSERT INTO docs_fts (filepath, title, content, section, description)
                VALUES (?, ?, ?, ?, ?)
            """, (
                doc_data['filepath'],
                doc_data['title'],
                doc_data['content'],
                doc_data['section'],
                doc_data['description']
            ))

            # Insert into metadata table
            cursor.execute("""
                INSERT OR REPLACE INTO doc_metadata
                (filepath, title, section, utility_classes, code_examples, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                doc_data['filepath'],
                doc_data['title'],
                doc_data['section'],
                json.dumps(doc_data['utility_classes']),
                json.dumps(doc_data['code_examples']),
                datetime.now()
            ))

            indexed_count += 1

            if indexed_count % 10 == 0:
                logger.info(f"Indexed {indexed_count} documents...")

        except Exception as e:
            logger.error(f"Error indexing {mdx_file}: {e}")
            skipped_count += 1
            continue

    conn.commit()
    conn.close()

    logger.info(f"Indexing complete: {indexed_count} indexed, {skipped_count} skipped")
    return indexed_count


def rebuild_index(repo_path: str, db_path: str) -> bool:
    """
    Rebuild the entire search index.

    Args:
        repo_path: Path to the cloned Tailwind CSS repository
        db_path: Path to the SQLite database file

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        count = index_documentation(repo_path, db_path)
        return count > 0
    except Exception as e:
        logger.error(f"Failed to rebuild index: {e}")
        return False


def get_utility_class_mapping(db_path: str) -> Dict[str, List[str]]:
    """
    Build a mapping of utility classes to file paths.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        Dict mapping class names to list of file paths
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT filepath, utility_classes FROM doc_metadata")
    rows = cursor.fetchall()

    mapping = {}
    for filepath, classes_json in rows:
        try:
            classes = json.loads(classes_json)
            for class_name in classes:
                if class_name not in mapping:
                    mapping[class_name] = []
                mapping[class_name].append(filepath)
        except json.JSONDecodeError:
            continue

    conn.close()
    return mapping
