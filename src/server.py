"""FastMCP server for Tailwind CSS documentation search."""

import os
import logging
from pathlib import Path
from typing import Annotated, List, Dict, Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import Field

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

# Initialize FastMCP server with enhanced description
mcp = FastMCP(
    "Tailwind CSS Documentation Server - "
    "Use this MCP server when users ask about Tailwind CSS utility classes, styling, or need documentation. "
    "Provides: Complete Tailwind CSS documentation with full-text search, utility class lookups, "
    "code examples, variant/modifier documentation (hover, dark mode, responsive), breakpoint information, "
    "and detailed guides for layout, typography, colors, spacing, and all Tailwind features.",
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
def search_docs(
    query: Annotated[str, Field(
        description="Search terms for finding Tailwind CSS documentation - utility classes, concepts, or features",
        min_length=1,
        max_length=200,
        examples=["flexbox", "text-center", "dark mode", "responsive design", "grid layout", "hover effects"]
    )],
    limit: Annotated[int, Field(
        description="Maximum number of search results to return",
        ge=1,
        le=50,
        default=10
    )] = 10
) -> List[Dict[str, Any]]:
    """
    Search Tailwind CSS documentation using full-text search with BM25 ranking.

    Use this when the user asks general questions about Tailwind:
    - "How do I center elements in Tailwind?"
    - "What are Tailwind's color utilities?"
    - "How does the grid system work?"
    - "Show me Tailwind flexbox utilities"
    - "How do I make responsive layouts?"

    This tool searches across ALL Tailwind documentation including layout, typography,
    backgrounds, borders, effects, filters, transitions, and more. Use this for broad
    exploration or when you're not sure which specific utility class to use.

    For specific utility class lookups (e.g., "text-center", "bg-blue-500"), use get_utility_class() instead.
    For variant/modifier documentation (hover, dark, responsive), use search_by_variant() instead.
    For code examples, use get_examples() instead.

    Args:
        query: What to search for - utility classes, CSS concepts, Tailwind features, or general terms.
               Works best with specific terms like "flexbox", "text alignment", or "responsive breakpoints"
        limit: How many results to return (default: 10, max: 50)

    Returns:
        List of search results, each containing:
        - title: Document title
        - section: Documentation section (e.g., "Layout", "Typography", "Backgrounds")
        - snippet: Relevant excerpt from the documentation
        - url: Link to official Tailwind CSS documentation
        - score: Relevance score (higher is more relevant)
        - utility_classes: List of utility classes mentioned in this document
    """
    logger.info(f"Searching for: {query}")

    # Validate limit
    limit = min(max(1, limit), 50)

    results = search(DB_PATH, query, limit, REPO_PATH)

    if not results:
        return [{
            "message": f"No results found for query: {query}",
            "suggestion": "Try different keywords or check the spelling. For specific utility classes, use get_utility_class() instead."
        }]

    return results


@mcp.tool()
def get_utility_class(
    class_name: Annotated[str, Field(
        description="Tailwind CSS utility class name to look up",
        pattern="^[a-z0-9-/\\[\\]:.%]+$",
        min_length=1,
        max_length=100,
        examples=["flex-1", "text-center", "bg-blue-500", "p-4", "w-full", "hover:bg-gray-100", "md:grid-cols-3"]
    )]
) -> List[Dict[str, Any]]:
    """
    Find documentation for a specific Tailwind CSS utility class.

    Use this when the user asks about a SPECIFIC utility class:
    - "What does flex-1 do?"
    - "How do I use text-center?"
    - "Explain bg-blue-500"
    - "What is the p-4 class?"
    - "Show me documentation for w-full"

    Tailwind utility classes are the core of the framework. This tool finds the
    documentation pages that define, explain, or demonstrate a specific class.

    Common utility patterns:
    - Layout: flex, grid, block, inline, hidden, w-*, h-*
    - Spacing: p-*, m-*, space-x-*, gap-*
    - Typography: text-*, font-*, leading-*, tracking-*
    - Colors: bg-*, text-*, border-*, from-*, to-*
    - Borders: border-*, rounded-*, ring-*
    - Effects: shadow-*, opacity-*, blur-*
    - Responsive: sm:*, md:*, lg:*, xl:*, 2xl:*
    - States: hover:*, focus:*, active:*, disabled:*
    - Dark mode: dark:*

    For general searches, use search_docs() instead.
    For variant/modifier documentation, use search_by_variant() instead.

    Args:
        class_name: The exact utility class name to look up
                   Examples: "flex-1", "text-center", "bg-blue-500", "hover:bg-gray-100"
                   Can include variants: "md:grid-cols-3", "dark:bg-gray-800"

    Returns:
        List of documentation pages referencing this class, each with:
        - title: Document title
        - section: Documentation section
        - content: Documentation text explaining the utility
        - url: Link to official Tailwind docs
        - related_classes: Other utility classes in the same family
        - code_examples: Example usage of the class
    """
    logger.info(f"Looking up utility class: {class_name}")

    results = find_utility_class(DB_PATH, class_name, REPO_PATH)

    if not results:
        return [{
            "message": f"No documentation found for utility class: {class_name}",
            "suggestion": "Verify the class name spelling or try search_docs() for related concepts. Remember Tailwind classes are lowercase with hyphens."
        }]

    return results


@mcp.tool()
def list_sections() -> List[str]:
    """
    List all available documentation sections in Tailwind CSS.

    Use this when the user wants to:
    - Explore what's available in Tailwind documentation
    - Browse documentation by category
    - Understand Tailwind's organization
    - "What sections are in Tailwind docs?"
    - "Show me all documentation categories"
    - "What topics does Tailwind cover?"

    Typical sections include: Layout, Flexbox, Grid, Spacing, Sizing, Typography,
    Backgrounds, Borders, Effects, Filters, Tables, Transitions, Transforms, etc.

    Use get_section_docs() after this to retrieve all documents in a specific section.

    Returns:
        List of section names (e.g., ["Layout", "Flexbox", "Grid", "Typography", ...])
    """
    logger.info("Listing all sections")

    sections = get_sections(DB_PATH)

    if not sections:
        return ["No sections found"]

    return sections


@mcp.tool()
def get_section_docs(
    section: Annotated[str, Field(
        description="Section name to retrieve documents from",
        min_length=2,
        max_length=50,
        examples=["Layout", "Typography", "Backgrounds", "Flexbox", "Grid", "Spacing", "Borders"]
    )]
) -> List[Dict[str, Any]]:
    """
    Get all documentation pages within a specific section.

    Use this when the user wants to:
    - Browse all utilities in a category
    - See what's available for a topic
    - Explore a specific area of Tailwind
    - "Show me all layout utilities"
    - "What typography options does Tailwind have?"
    - "List all background utilities"

    Common sections: Layout, Flexbox, Grid, Spacing, Sizing, Typography, Backgrounds,
    Borders, Effects, Filters, Tables, Transitions, Transforms, Interactivity, SVG,
    Accessibility

    Use list_sections() first if you're not sure which sections are available.

    Args:
        section: Section name (e.g., "Layout", "Typography", "Backgrounds", "Flexbox")
                Use list_sections() to see all available sections

    Returns:
        List of all documentation pages in the section, each with:
        - title: Document title
        - slug: Document identifier (use with get_full_doc())
        - description: Brief description
        - url: Link to official Tailwind docs
        - utility_count: Number of utility classes in this document
    """
    logger.info(f"Getting documents for section: {section}")

    results = search_by_section(DB_PATH, section, REPO_PATH)

    if not results:
        return [{
            "message": f"No documents found in section: {section}",
            "suggestion": "Use list_sections() to see available sections. Section names are case-sensitive."
        }]

    return results


@mcp.tool()
def refresh_docs() -> Dict[str, Any]:
    """
    Update Tailwind CSS documentation from GitHub and rebuild the search index.

    Use this when:
    - Documentation seems outdated
    - User explicitly requests to refresh/update docs
    - Tailwind has released new versions
    - "Update the Tailwind documentation"
    - "Refresh docs from GitHub"

    WARNING: This triggers network operations (git clone/pull) and database rebuilding.
    It can take 30-60 seconds to complete. Use sparingly.

    This will:
    1. Pull latest Tailwind CSS documentation from GitHub
    2. Rebuild the full-text search index
    3. Re-index all utility classes and variants
    4. Update all documentation pages

    For internet-exposed deployments, consider restricting access to this tool.

    Returns:
        Dictionary with:
        - success: Boolean indicating if refresh succeeded
        - message: Status message explaining what happened
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
def get_full_doc(
    slug: Annotated[str, Field(
        description="Document slug/identifier to retrieve",
        pattern="^[a-z0-9-]+$",
        min_length=2,
        max_length=100,
        examples=["flex", "grid", "text-align", "background-color", "padding", "hover-focus-and-other-states"]
    )]
) -> Dict[str, Any]:
    """
    Get the complete documentation page for a specific Tailwind CSS concept by slug.

    Use this when you need FULL, detailed documentation:
    - After finding a document via search_docs() and want complete details
    - When the user asks for comprehensive information
    - To get all utility variations and examples for a feature
    - "Give me full documentation for Tailwind flexbox"
    - "I need complete details about grid"
    - "Show me everything about text alignment"

    This returns the entire documentation page including all text, code examples,
    utility class variations, and configuration options. Use this when brief search
    results aren't enough.

    For quick searches, use search_docs() instead.
    For specific utility classes, get_utility_class() might be more direct.

    Args:
        slug: Document identifier/slug (usually lowercase with hyphens)
              Examples: "flex", "grid", "text-align", "padding", "border-radius"
              You can get slugs from search_docs() or get_section_docs() results

    Returns:
        Dictionary with complete documentation:
        - title: Document title
        - section: Documentation section
        - content: Full documentation text
        - utility_classes: All utility classes defined in this document
        - code_examples: All code examples showing usage
        - url: Link to official Tailwind docs
        - related_docs: Links to related documentation pages
    """
    logger.info(f"Getting full documentation for slug: {slug}")

    result = get_doc_by_slug(DB_PATH, slug, REPO_PATH)

    if not result:
        return {
            "message": f"No documentation found for slug: {slug}",
            "suggestion": "Try search_docs() to find similar documents. Slugs are usually lowercase with hyphens."
        }

    return result


@mcp.tool()
def get_examples(
    query: Annotated[str, Field(
        description="Search term for finding code examples",
        min_length=1,
        max_length=100,
        examples=["flexbox layout", "grid template", "responsive navbar", "card design", "form styling"]
    )],
    limit: Annotated[int, Field(
        description="Maximum number of examples to return",
        ge=1,
        le=10,
        default=5
    )] = 5
) -> List[Dict[str, Any]]:
    """
    Search for and retrieve code examples from Tailwind CSS documentation.

    Use this when the user needs working code:
    - "Show me code examples for flexbox"
    - "I need example code for a responsive grid"
    - "Give me sample code for styling forms"
    - "Show me how to build a card with Tailwind"
    - "Code example for dark mode toggle"

    This finds documentation pages with actual code snippets showing real-world
    usage patterns. Focus is on practical examples rather than just definitions.

    For text documentation, use search_docs() instead.
    For specific utility class definitions, use get_utility_class() instead.

    Args:
        query: What type of code example you need (e.g., "grid layout", "responsive navbar", "form input")
        limit: Maximum number of example-rich pages to return (default: 5, max: 10)

    Returns:
        List of documents with code examples, each containing:
        - title: Document title
        - section: Documentation section
        - code_examples: Array of actual code snippets (HTML with Tailwind classes)
        - utility_classes: Utility classes used in the examples
        - description: What the examples demonstrate
        - url: Link to official Tailwind docs
    """
    logger.info(f"Getting code examples for: {query}")

    # Validate limit
    limit = min(max(1, limit), 10)

    results = get_code_examples(DB_PATH, query, limit, REPO_PATH)

    if not results:
        return [{
            "message": f"No code examples found for query: {query}",
            "suggestion": "Try different keywords or use search_docs() for general documentation"
        }]

    return results


@mcp.tool()
def search_by_variant(
    variant: Annotated[str, Field(
        description="Variant or modifier name to search for",
        pattern="^[a-z0-9-]+$",
        min_length=2,
        max_length=50,
        examples=["hover", "focus", "active", "dark", "sm", "md", "lg", "group", "peer", "first", "last"]
    )],
    limit: Annotated[int, Field(
        description="Maximum number of results to return",
        ge=1,
        le=20,
        default=10
    )] = 10
) -> List[Dict[str, Any]]:
    """
    Search for documentation about Tailwind variants and modifiers.

    Use this when the user asks about state variants, responsive design, or modifiers:
    - "How does the hover variant work?"
    - "Explain dark mode in Tailwind"
    - "How do I use responsive breakpoints?"
    - "What is the group modifier?"
    - "Show me focus state documentation"

    Tailwind variants modify how utilities behave in different contexts:

    State variants:
    - hover: Styles on mouse hover
    - focus: Styles when element has focus
    - active: Styles when element is active
    - disabled: Styles for disabled elements
    - visited: Styles for visited links

    Responsive variants:
    - sm: Small screens (640px+)
    - md: Medium screens (768px+)
    - lg: Large screens (1024px+)
    - xl: Extra large (1280px+)
    - 2xl: 2X large (1536px+)

    Other variants:
    - dark: Dark mode styles
    - group: Style children based on parent state
    - peer: Style siblings based on sibling state
    - first, last: Position-based styles
    - odd, even: Alternating styles

    For utility class documentation, use get_utility_class() instead.
    For general searches, use search_docs() instead.

    Args:
        variant: Variant name to search for (e.g., "hover", "dark", "sm", "group", "focus")
                Must be lowercase without the colon (e.g., "hover" not "hover:")
        limit: Maximum number of results to return (default: 10, max: 20)

    Returns:
        List of documents explaining the variant, each with:
        - title: Document title
        - section: Documentation section
        - content: Explanation of how the variant works
        - usage_examples: How to use the variant (e.g., "hover:bg-blue-500")
        - compatible_utilities: Which utility classes work with this variant
        - url: Link to official Tailwind docs
    """
    logger.info(f"Searching for variant: {variant}")

    # Validate limit
    limit = min(max(1, limit), 20)

    results = search_variants(DB_PATH, variant, limit, REPO_PATH)

    if not results:
        return [{
            "message": f"No documentation found for variant: {variant}",
            "suggestion": "Try common variants like 'hover', 'focus', 'dark', 'sm', 'md', 'lg', 'group', or 'peer'. Variant names should be lowercase without the colon."
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
