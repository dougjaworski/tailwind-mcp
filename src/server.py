"""FastMCP server for Tailwind CSS documentation search."""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .git_manager import clone_or_update, is_repo_ready
from .indexer import rebuild_index
from .search import (
    search,
    find_utility_class,
    get_sections,
    search_by_section,
    get_doc_by_slug,
    get_code_examples,
    search_variants
)

# Environment configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DATA_DIR = os.getenv("DATA_DIR", "/app/data")
MCP_PORT = int(os.getenv("MCP_PORT", "8000"))
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_ALLOWED_HOSTS = os.getenv("MCP_ALLOWED_HOSTS", "localhost:*,127.0.0.1:*,0.0.0.0:*")

# Parse allowed hosts from comma-separated string
allowed_hosts_list = [host.strip() for host in MCP_ALLOWED_HOSTS.split(",")]

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Derived paths
REPO_PATH = os.path.join(DATA_DIR, "tailwindcss.com")
DB_PATH = os.path.join(DATA_DIR, "tailwind_docs.db")

# Initialize FastMCP server with security settings
mcp = FastMCP(
    "Tailwind CSS Documentation",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts_list,
        allowed_origins=["*"]  # Allow all origins for MCP client access
    )
)


def initialize_server():
    """Initialize the server by cloning/updating docs and building the index."""
    logger.info("Initializing Tailwind CSS MCP Server...")

    # Ensure data directory exists
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

    # Clone or update repository
    if not is_repo_ready(REPO_PATH):
        logger.info("Repository not found or incomplete, cloning...")
        if not clone_or_update(REPO_PATH):
            logger.error("Failed to clone repository")
            return False
    else:
        logger.info("Repository already exists")

    # Build index if database doesn't exist
    db_file = Path(DB_PATH)
    if not db_file.exists():
        logger.info("Database not found, building index...")
        if not rebuild_index(REPO_PATH, DB_PATH):
            logger.error("Failed to build index")
            return False
        logger.info("Index built successfully")
    else:
        logger.info("Database already exists")

    logger.info("Server initialization complete")
    return True


@mcp.tool()
def search_docs(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search Tailwind CSS documentation using full-text search.

    Args:
        query: Search query string (supports FTS5 syntax)
        limit: Maximum number of results to return (default: 10, max: 50)

    Returns:
        List of search results with title, section, snippet, URL, and relevance score
    """
    logger.info(f"Searching for: {query}")

    # Validate limit
    limit = min(max(1, limit), 50)

    results = search(DB_PATH, query, limit, REPO_PATH)

    if not results:
        return [{
            "message": f"No results found for query: {query}",
            "suggestion": "Try different keywords or check the spelling"
        }]

    return results


@mcp.tool()
def get_utility_class(class_name: str) -> List[Dict[str, Any]]:
    """
    Find documentation pages for a specific Tailwind CSS utility class.

    Args:
        class_name: Utility class name (e.g., "flex-1", "text-center", "bg-blue-500")

    Returns:
        List of documentation pages that reference this utility class
    """
    logger.info(f"Looking up utility class: {class_name}")

    results = find_utility_class(DB_PATH, class_name, REPO_PATH)

    if not results:
        return [{
            "message": f"No documentation found for utility class: {class_name}",
            "suggestion": "Verify the class name or try searching for related terms"
        }]

    return results


@mcp.tool()
def list_sections() -> List[str]:
    """
    List all available documentation sections.

    Returns:
        List of section names (e.g., ["Layout", "Typography", "Backgrounds", ...])
    """
    logger.info("Listing all sections")

    sections = get_sections(DB_PATH)

    if not sections:
        return ["No sections found"]

    return sections


@mcp.tool()
def get_section_docs(section: str) -> List[Dict[str, Any]]:
    """
    Get all documentation pages in a specific section.

    Args:
        section: Section name (use list_sections to see available sections)

    Returns:
        List of documentation pages in the section
    """
    logger.info(f"Getting documents for section: {section}")

    results = search_by_section(DB_PATH, section, REPO_PATH)

    if not results:
        return [{
            "message": f"No documents found in section: {section}",
            "suggestion": "Use list_sections to see available sections"
        }]

    return results


@mcp.tool()
def refresh_docs() -> Dict[str, Any]:
    """
    Update documentation from GitHub and rebuild the search index.

    Returns:
        Status message indicating success or failure
    """
    logger.info("Refreshing documentation...")

    try:
        # Update repository
        if not clone_or_update(REPO_PATH):
            return {
                "success": False,
                "message": "Failed to update repository from GitHub"
            }

        # Rebuild index
        if not rebuild_index(REPO_PATH, DB_PATH):
            return {
                "success": False,
                "message": "Failed to rebuild search index"
            }

        return {
            "success": True,
            "message": "Documentation updated and index rebuilt successfully"
        }

    except Exception as e:
        logger.error(f"Error refreshing docs: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }


@mcp.tool()
def get_full_doc(slug: str) -> Dict[str, Any]:
    """
    Get complete documentation for a specific Tailwind CSS concept by slug.

    Args:
        slug: Documentation page slug (e.g., "flex", "grid", "text-align")

    Returns:
        Complete document with content, code examples, and metadata
    """
    logger.info(f"Getting full documentation for slug: {slug}")

    result = get_doc_by_slug(DB_PATH, slug, REPO_PATH)

    if not result:
        return {
            "message": f"No documentation found for slug: {slug}",
            "suggestion": "Try searching with search_docs or check the exact slug name"
        }

    return result


@mcp.tool()
def get_examples(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get code examples from documentation that match a query.

    Args:
        query: Search query for finding relevant code examples
        limit: Maximum number of results to return (default: 5, max: 10)

    Returns:
        List of documents with code examples showing real usage patterns
    """
    logger.info(f"Getting code examples for: {query}")

    # Validate limit
    limit = min(max(1, limit), 10)

    results = get_code_examples(DB_PATH, query, limit, REPO_PATH)

    if not results:
        return [{
            "message": f"No code examples found for query: {query}",
            "suggestion": "Try different keywords or use search_docs for general search"
        }]

    return results


@mcp.tool()
def search_by_variant(variant: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for documentation about Tailwind variants and modifiers.

    Args:
        variant: Variant name (e.g., "hover", "dark", "responsive", "sm", "group", "focus")
        limit: Maximum number of results to return (default: 10, max: 20)

    Returns:
        List of documents explaining how to use the variant/modifier
    """
    logger.info(f"Searching for variant: {variant}")

    # Validate limit
    limit = min(max(1, limit), 20)

    results = search_variants(DB_PATH, variant, limit, REPO_PATH)

    if not results:
        return [{
            "message": f"No documentation found for variant: {variant}",
            "suggestion": "Try common variants like 'hover', 'dark', 'responsive', or breakpoint names"
        }]

    return results


def main():
    """Main entry point for the server."""
    logger.info("Starting Tailwind CSS MCP Server...")

    # Initialize on startup
    if not initialize_server():
        logger.error("Server initialization failed")
        return

    # Run FastMCP server with HTTP transport
    logger.info(f"Starting MCP server on {MCP_HOST}:{MCP_PORT}")
    logger.info(f"Allowed hosts: {', '.join(allowed_hosts_list)}")
    mcp.run(transport="http", host=MCP_HOST, port=MCP_PORT)


if __name__ == "__main__":
    main()
