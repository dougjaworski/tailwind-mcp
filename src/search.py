"""Search functionality for Tailwind CSS documentation."""

import sqlite3
import json
import logging
from typing import List, Dict, Optional
from pathlib import Path

from .parser import get_url_from_filepath

logger = logging.getLogger(__name__)


def search(db_path: str, query: str, limit: int = 10, repo_path: str = "") -> List[Dict]:
    """
    Execute a full-text search query using FTS5 with BM25 ranking.

    Args:
        db_path: Path to the SQLite database file
        query: Search query string
        limit: Maximum number of results to return
        repo_path: Path to repository for URL generation

    Returns:
        List of search results with metadata and snippets
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Use FTS5 MATCH with snippet function for context extraction
        # BM25 ranking is used by default in FTS5
        cursor.execute("""
            SELECT
                filepath,
                title,
                section,
                description,
                snippet(docs_fts, 2, '<mark>', '</mark>', '...', 64) as snippet,
                bm25(docs_fts) as relevance_score
            FROM docs_fts
            WHERE docs_fts MATCH ?
            ORDER BY bm25(docs_fts)
            LIMIT ?
        """, (query, limit))

        rows = cursor.fetchall()
        results = []

        for row in rows:
            filepath, title, section, description, snippet, score = row

            # Generate URL
            url = get_url_from_filepath(filepath, repo_path)

            # Format result
            result = {
                'file': filepath,
                'title': title,
                'section': section,
                'description': description,
                'snippet': snippet,
                'url': url,
                'relevance_score': abs(score)  # BM25 scores are negative, take absolute value
            }
            results.append(result)

        logger.info(f"Search for '{query}' returned {len(results)} results")
        return results

    except sqlite3.OperationalError as e:
        logger.error(f"Search query failed: {e}")
        return []
    finally:
        conn.close()


def find_utility_class(db_path: str, class_name: str, repo_path: str = "") -> List[Dict]:
    """
    Find documentation pages that reference a specific utility class.

    Args:
        db_path: Path to the SQLite database file
        class_name: Tailwind utility class name (e.g., "flex-1")
        repo_path: Path to repository for URL generation

    Returns:
        List of documents that reference this class
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT filepath, title, section, utility_classes
            FROM doc_metadata
            WHERE utility_classes LIKE ?
        """, (f'%"{class_name}"%',))

        rows = cursor.fetchall()
        results = []

        for filepath, title, section, utility_classes_json in rows:
            try:
                utility_classes = json.loads(utility_classes_json)
                if class_name in utility_classes:
                    url = get_url_from_filepath(filepath, repo_path)
                    results.append({
                        'file': filepath,
                        'title': title,
                        'section': section,
                        'url': url,
                        'utility_class': class_name
                    })
            except json.JSONDecodeError:
                continue

        logger.info(f"Found {len(results)} documents for utility class '{class_name}'")
        return results

    finally:
        conn.close()


def get_sections(db_path: str) -> List[str]:
    """
    Get a list of all unique documentation sections.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        List of section names
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT DISTINCT section
            FROM doc_metadata
            WHERE section IS NOT NULL AND section != ''
            ORDER BY section
        """)

        rows = cursor.fetchall()
        sections = [row[0] for row in rows]

        logger.info(f"Found {len(sections)} unique sections")
        return sections

    finally:
        conn.close()


def get_all_documents(db_path: str, repo_path: str = "") -> List[Dict]:
    """
    Get a list of all indexed documents.

    Args:
        db_path: Path to the SQLite database file
        repo_path: Path to repository for URL generation

    Returns:
        List of all documents with metadata
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT filepath, title, section
            FROM doc_metadata
            ORDER BY section, title
        """)

        rows = cursor.fetchall()
        results = []

        for filepath, title, section in rows:
            url = get_url_from_filepath(filepath, repo_path)
            results.append({
                'file': filepath,
                'title': title,
                'section': section,
                'url': url
            })

        return results

    finally:
        conn.close()


def search_by_section(db_path: str, section: str, repo_path: str = "") -> List[Dict]:
    """
    Get all documents in a specific section.

    Args:
        db_path: Path to the SQLite database file
        section: Section name to filter by
        repo_path: Path to repository for URL generation

    Returns:
        List of documents in the section
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT filepath, title, section
            FROM doc_metadata
            WHERE section = ?
            ORDER BY title
        """, (section,))

        rows = cursor.fetchall()
        results = []

        for filepath, title, section in rows:
            url = get_url_from_filepath(filepath, repo_path)
            results.append({
                'file': filepath,
                'title': title,
                'section': section,
                'url': url
            })

        return results

    finally:
        conn.close()


def get_doc_by_slug(db_path: str, slug: str, repo_path: str = "") -> Optional[Dict]:
    """
    Get full documentation for a specific page by slug (e.g., "flex", "grid").

    Args:
        db_path: Path to the SQLite database file
        slug: Documentation page slug (e.g., "flex", "text-align")
        repo_path: Path to repository for URL generation

    Returns:
        Full document with content and metadata, or None if not found
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Search for documents where the filepath ends with the slug
        cursor.execute("""
            SELECT
                dm.filepath,
                dm.title,
                dm.section,
                df.content,
                df.description,
                dm.utility_classes,
                dm.code_examples
            FROM doc_metadata dm
            JOIN docs_fts df ON dm.filepath = df.filepath
            WHERE dm.filepath LIKE ?
            LIMIT 1
        """, (f'%/{slug}.mdx',))

        row = cursor.fetchone()

        if not row:
            return None

        filepath, title, section, content, description, utility_classes_json, code_examples_json = row

        # Parse JSON fields
        try:
            utility_classes = json.loads(utility_classes_json) if utility_classes_json else []
            code_examples = json.loads(code_examples_json) if code_examples_json else []
        except json.JSONDecodeError:
            utility_classes = []
            code_examples = []

        url = get_url_from_filepath(filepath, repo_path)

        return {
            'file': filepath,
            'title': title,
            'section': section,
            'description': description,
            'content': content,
            'url': url,
            'utility_classes': utility_classes,
            'code_examples': code_examples
        }

    finally:
        conn.close()


def get_code_examples(db_path: str, query: str, limit: int = 5, repo_path: str = "") -> List[Dict]:
    """
    Get code examples from documentation that match a query.

    Args:
        db_path: Path to the SQLite database file
        query: Search query for finding relevant code examples
        limit: Maximum number of results to return
        repo_path: Path to repository for URL generation

    Returns:
        List of documents with their code examples
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Search in FTS for relevant documents
        cursor.execute("""
            SELECT
                dm.filepath,
                dm.title,
                dm.section,
                dm.code_examples,
                bm25(docs_fts) as relevance_score
            FROM doc_metadata dm
            JOIN docs_fts ON dm.filepath = docs_fts.filepath
            WHERE docs_fts MATCH ?
            AND dm.code_examples IS NOT NULL
            AND dm.code_examples != '[]'
            ORDER BY bm25(docs_fts)
            LIMIT ?
        """, (query, limit))

        rows = cursor.fetchall()
        results = []

        for filepath, title, section, code_examples_json, score in rows:
            try:
                code_examples = json.loads(code_examples_json) if code_examples_json else []

                if code_examples:
                    url = get_url_from_filepath(filepath, repo_path)
                    results.append({
                        'file': filepath,
                        'title': title,
                        'section': section,
                        'url': url,
                        'code_examples': code_examples,
                        'relevance_score': abs(score)
                    })
            except json.JSONDecodeError:
                continue

        logger.info(f"Found {len(results)} code examples for query '{query}'")
        return results

    finally:
        conn.close()


def search_variants(db_path: str, variant_type: str, limit: int = 10, repo_path: str = "") -> List[Dict]:
    """
    Search for documentation about specific Tailwind variants/modifiers.

    Args:
        db_path: Path to the SQLite database file
        variant_type: Type of variant (e.g., "hover", "dark", "responsive", "group")
        limit: Maximum number of results to return
        repo_path: Path to repository for URL generation

    Returns:
        List of documents that discuss the variant
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Build search query for variants
        # Search for the variant name with common patterns
        # Use quoted strings to handle special characters like ':'
        search_patterns = [
            f'"{variant_type}:"',  # e.g., "hover:", "dark:"
            f'{variant_type}',      # Just the variant name
            f'"{variant_type} state"',
            f'"{variant_type} variant"',
            f'"{variant_type} modifier"'
        ]

        # Combine patterns with OR
        query = ' OR '.join(search_patterns)

        cursor.execute("""
            SELECT
                filepath,
                title,
                section,
                description,
                snippet(docs_fts, 2, '<mark>', '</mark>', '...', 64) as snippet,
                bm25(docs_fts) as relevance_score
            FROM docs_fts
            WHERE docs_fts MATCH ?
            ORDER BY bm25(docs_fts)
            LIMIT ?
        """, (query, limit))

        rows = cursor.fetchall()
        results = []

        for row in rows:
            filepath, title, section, description, snippet, score = row

            url = get_url_from_filepath(filepath, repo_path)

            result = {
                'file': filepath,
                'title': title,
                'section': section,
                'description': description,
                'snippet': snippet,
                'url': url,
                'relevance_score': abs(score),
                'variant_type': variant_type
            }
            results.append(result)

        logger.info(f"Search for variant '{variant_type}' returned {len(results)} results")
        return results

    except sqlite3.OperationalError as e:
        logger.error(f"Variant search query failed: {e}")
        return []
    finally:
        conn.close()
