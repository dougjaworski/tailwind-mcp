"""Entry point for FastMCP server - used by FastMCP CLI."""

import sys
sys.path.insert(0, '/app')

from src.server import mcp, initialize_server

# Initialize server before starting
if __name__ == "__main__":
    initialize_server()
