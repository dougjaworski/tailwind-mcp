# Tailwind CSS MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that provides AI assistants with comprehensive access to Tailwind CSS documentation. This enables Claude and other MCP-compatible AI assistants to accurately reference Tailwind documentation, provide code examples, and suggest the right utility classes for your projects.

Built with [FastMCP](https://github.com/jlowin/fastmcp) and designed for both local and remote access via HTTP transport.

---

## Table of Contents

- [Why Use This?](#why-use-this)
- [Features](#features)
- [Quick Start](#quick-start)
  - [Using Docker Compose (Recommended)](#using-docker-compose-recommended)
  - [Manual Docker Build](#manual-docker-build)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [Configuration Examples](#configuration-examples)
- [Connecting from Claude Code](#connecting-from-claude-code)
- [Available Tools](#available-tools)
- [Architecture](#architecture)
- [Development](#development)
- [Performance](#performance)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)
- [Contributing](#contributing)
- [License](#license)
- [Credits](#credits)

---

## Why Use This?

When working with Tailwind CSS, AI assistants often:
- ❌ Suggest outdated or incorrect utility class names
- ❌ Miss newer Tailwind features and variants
- ❌ Can't reference specific examples from official documentation

This MCP server solves these problems by giving AI assistants direct access to:
- ✅ Complete, up-to-date Tailwind CSS documentation
- ✅ Real code examples from official docs
- ✅ Utility class definitions and usage patterns
- ✅ Variant and modifier documentation (hover, dark mode, responsive, etc.)

---

## Features

- 🔍 **Full-text search** using SQLite FTS5 with BM25 ranking
- 🎯 **Utility class lookup** to find documentation for specific Tailwind classes
- 📚 **Section browsing** to explore documentation by category
- 📖 **Complete documentation retrieval** by slug for in-depth understanding
- 💻 **Code example extraction** to see real-world usage patterns
- 🎨 **Variant/modifier search** to learn about hover, dark mode, responsive design, and more
- 🔄 **Auto-updating** documentation from the official Tailwind CSS repository
- 🐳 **Docker-based** deployment with volume persistence
- 🌐 **HTTP transport** for local and remote access

---

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/dougjaworski/tailwind-mcp.git
cd tailwind-mcp

# Copy and customize the environment configuration
cp .env.example .env
# Edit .env with your preferred settings (optional)

# Build and start the server
docker-compose up -d

# View logs to monitor initialization
docker-compose logs -f

# Stop the server
docker-compose down
```

**On first run, the server will:**
1. Clone the Tailwind CSS documentation repository (~30 seconds)
2. Parse all MDX files and build the search index (~30 seconds)
3. Start the MCP server on the configured port (default: 8000)

### Manual Docker Build

```bash
# Build the image
docker build -t tailwind-mcp .

# Run the container
docker run -d \
  -p 8000:8000 \
  -v tailwind-docs:/app/data \
  --env-file .env \
  --name tailwind-mcp \
  tailwind-mcp
```

---

## Configuration

The server is configured using environment variables. Copy `.env.example` to `.env` and customize as needed:

```bash
cp .env.example .env
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_PORT` | `8000` | Port the MCP server listens on |
| `MCP_HOST` | `0.0.0.0` | Host the MCP server binds to |
| `MCP_ALLOWED_HOSTS` | `localhost:*,127.0.0.1:*,0.0.0.0:*` | Comma-separated list of allowed hostnames for DNS rebinding protection |
| `DATA_DIR` | `/app/data` | Directory where documentation and database are stored |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |

### Configuration Examples

**Local use only:**
```env
MCP_ALLOWED_HOSTS=localhost:*,127.0.0.1:*
```

**Remote access from specific host:**
```env
MCP_ALLOWED_HOSTS=localhost:*,127.0.0.1:*,myserver:*,myserver.example.com:*
```

**Custom port:**
```env
MCP_PORT=9000
```

---

## Connecting from Claude Code

Add the following to your Claude Code MCP settings (`.mcp.json`):

**Local connection:**
```json
{
  "mcpServers": {
    "tailwind-css": {
      "type": "http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

**Remote connection:**
```json
{
  "mcpServers": {
    "tailwind-css": {
      "type": "http",
      "url": "http://your-server-hostname:8000/mcp"
    }
  }
}
```

> **Note:** When connecting remotely, make sure `your-server-hostname` is included in the `MCP_ALLOWED_HOSTS` environment variable.

---

## Available Tools

The server provides 8 MCP tools for accessing Tailwind CSS documentation:

### 1. `search_docs`
Search the Tailwind CSS documentation using full-text search.

**Parameters:**
- `query` (string): Search query (supports FTS5 syntax)
- `limit` (int, optional): Maximum results to return (default: 10, max: 50)

**Returns:** List of search results with snippets, URLs, and relevance scores.

### 2. `get_utility_class`
Find documentation pages for a specific Tailwind CSS utility class.

**Parameters:**
- `class_name` (string): Utility class name (e.g., "flex-1", "text-center")

**Returns:** List of documentation pages that reference this class.

### 3. `list_sections`
Get a list of all documentation sections.

**Returns:** Array of section names (e.g., ["Core", "Layout", "Typography"]).

### 4. `get_section_docs`
Get all documentation pages in a specific section.

**Parameters:**
- `section` (string): Section name (use list_sections to see available sections)

**Returns:** List of documents in the section.

### 5. `get_full_doc`
Get complete documentation for a specific Tailwind CSS concept by slug.

**Parameters:**
- `slug` (string): Documentation page slug (e.g., "flex", "grid", "text-align")

**Returns:** Complete document with content, code examples, and metadata.

### 6. `get_examples`
Get code examples from documentation that match a query.

**Parameters:**
- `query` (string): Search query for finding relevant code examples
- `limit` (int, optional): Maximum results to return (default: 5, max: 10)

**Returns:** List of documents with code examples showing real usage patterns.

### 7. `search_by_variant`
Search for documentation about Tailwind variants and modifiers.

**Parameters:**
- `variant` (string): Variant name (e.g., "hover", "dark", "responsive", "sm")
- `limit` (int, optional): Maximum results to return (default: 10, max: 20)

**Returns:** List of documents explaining how to use the variant/modifier.

### 8. `refresh_docs`
Update documentation from GitHub and rebuild the search index.

**Returns:** Status message indicating success or failure.

---

## Architecture

### Components

- **FastMCP**: Server framework with HTTP transport
- **SQLite FTS5**: Full-text search engine with BM25 ranking
- **python-frontmatter**: YAML metadata extraction from MDX files
- **Git**: Repository management for documentation updates

### Data Flow

1. **Initialization**: Clone Tailwind CSS repo → Parse MDX files → Build SQLite index
2. **Search**: Client query → FTS5 search → Format results → Return to client
3. **Lookup**: Class name → Query metadata → Return matching docs
4. **Refresh**: Git pull → Re-parse files → Rebuild index

### Database Schema

**FTS5 Table (docs_fts):**
```sql
CREATE VIRTUAL TABLE docs_fts USING fts5(
    filepath, title, content, section, description
);
```

**Metadata Table (doc_metadata):**
```sql
CREATE TABLE doc_metadata (
    id INTEGER PRIMARY KEY,
    filepath TEXT UNIQUE,
    title TEXT,
    section TEXT,
    utility_classes TEXT,  -- JSON array
    code_examples TEXT,    -- JSON array
    last_updated TIMESTAMP
);
```

---

## Development

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATA_DIR=./data
export MCP_PORT=8000

# Run server
python -m src.server
```

### Running Tests

```bash
pip install pytest
pytest tests/
```

---

## Performance

| Metric | Time |
|--------|------|
| **First startup** | 1-2 minutes (cloning repo + building index) |
| **Subsequent startups** | <5 seconds (uses cached data) |
| **Search queries** | <100ms for typical queries |
| **Index size** | ~5-10 MB for full documentation |
| **Documents indexed** | ~185 Tailwind CSS documentation pages |

---

## Troubleshooting

### Server won't start

Check logs for errors:
```bash
docker-compose logs -f
```

**Common issues:**
- Port 8000 already in use: Change `MCP_PORT` in `.env`
- Git clone failed: Check network connectivity
- Permission issues: Ensure volume is writable

### Search returns no results

1. Verify index was built:
   ```bash
   docker-compose exec tailwind-mcp ls -la /app/data
   ```

2. Rebuild index using the `refresh_docs` tool from Claude Code

### Connection refused from Claude Code

1. Verify server is running: `docker-compose ps`
2. Check your hostname is in `MCP_ALLOWED_HOSTS`
3. Verify firewall rules allow port 8000

### Update to latest Tailwind CSS documentation

```bash
# Option 1: Use the refresh_docs tool from Claude Code

# Option 2: Delete the volume and restart
docker-compose down -v
docker-compose up -d
```

---

## Security Considerations

### Intended Deployment Model

This MCP server is designed for **local and trusted network environments**:

- ✅ Local Docker containers on your development machine
- ✅ Internal network servers without internet exposure
- ✅ Personal or team development environments
- ✅ Trusted internal infrastructure

**This server is NOT designed to be exposed directly to the internet** without additional security hardening.

### Current Security Posture

The default configuration prioritizes ease of use for local development:

- **No Authentication**: All MCP tools are accessible without authentication
- **No Rate Limiting**: No built-in protection against resource exhaustion
- **HTTP Only**: No TLS/HTTPS encryption by default
- **Host Network Mode**: Container runs in host network mode for MCP compatibility
- **Read-Only Operations**: Server only reads documentation (no user data storage)

### Hardening for Production/Internet Exposure

If you plan to expose this MCP server beyond a trusted local network, consider implementing these security measures:

#### 1. Add Authentication

Implement an authentication layer:
- API key authentication via reverse proxy (nginx, Traefik)
- OAuth2/OIDC integration for user authentication
- Firewall rules limiting access to specific IP addresses

#### 2. Enable TLS/HTTPS

Add a reverse proxy with TLS termination:
```yaml
# Example: nginx with Let's Encrypt
# Place nginx in front of the MCP server
# Configure TLS certificates
# Proxy requests to http://localhost:8000
```

#### 3. Implement Rate Limiting

Protect against resource exhaustion:
- Configure rate limiting in your reverse proxy
- Suggested: 100 requests/minute per IP address
- Monitor for unusual query patterns

#### 4. Network Isolation

Improve container network security:
```yaml
# docker-compose.yml
services:
  tailwind-mcp:
    # Change from host to bridge mode
    # network_mode: host  # Remove this
    ports:
      - "127.0.0.1:8000:8000"  # Bind to localhost only
    networks:
      - internal  # Use isolated network

networks:
  internal:
    driver: bridge
```

#### 5. Input Validation

Add additional validation layers:
- Limit query string lengths (e.g., max 500 characters)
- Validate slug names against whitelist
- Sanitize all user inputs before logging

#### 6. Monitoring and Logging

Implement security monitoring:
- Monitor access logs for unusual patterns
- Set up alerts for high request volumes
- Regularly audit who is accessing the server
- Store logs in a secure, access-controlled location

#### 7. Restrict Dangerous Operations

For internet-exposed deployments:
- Disable or restrict the `refresh_docs` tool (triggers git clone operations)
- Consider making it admin-only via proxy authentication

#### 8. Regular Updates

Maintain security over time:
- Run `pip audit` regularly to check for vulnerable dependencies
- Subscribe to security advisories for FastMCP and dependencies
- Rebuild Docker images monthly to get latest security patches
- Monitor the [FastMCP security advisories](https://github.com/jlowin/fastmcp/security)

### Security Best Practices

Even for local deployments:

1. **Principle of Least Privilege**: Run container as non-root user (already configured)
2. **Network Segmentation**: Keep the Docker host on a separate network segment if possible
3. **Regular Backups**: Although this is a read-only service, backup your database volume
4. **Audit Trail**: Review logs periodically for unusual activity
5. **Update Dependencies**: Keep FastMCP and Python dependencies up to date

### Reporting Security Issues

If you discover a security vulnerability in this project, please report it responsibly:

1. **DO NOT** open a public GitHub issue
2. Email security concerns to the repository maintainer
3. Include details: vulnerability description, reproduction steps, potential impact
4. Allow reasonable time for a fix before public disclosure

### Compliance and Regulatory Considerations

If you're subject to compliance requirements (HIPAA, SOC 2, PCI-DSS, etc.):

- This server stores no user data or PII
- All data comes from public Tailwind CSS documentation
- Implement additional controls based on your compliance framework
- Conduct a security assessment before production use
- Document your deployment architecture and security controls

---

## Contributing

Contributions are welcome! Please feel free to:

- 🐛 Report bugs or issues
- 💡 Suggest new features or improvements
- 📝 Improve documentation
- 🔧 Submit pull requests

### Development Guidelines

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test thoroughly
5. Commit your changes (`git commit -m 'Add some amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

---

## License

MIT License - See [LICENSE](LICENSE) file for details.

The Tailwind CSS documentation accessed by this server is © Tailwind Labs Inc. This project is not affiliated with or endorsed by Tailwind Labs.

---

## Credits

- Built with [FastMCP](https://github.com/jlowin/fastmcp)
- Documentation from [Tailwind CSS](https://tailwindcss.com)
- Powered by [Model Context Protocol](https://modelcontextprotocol.io)

---

<div align="center">

**Made with ❤️ for the Tailwind CSS community**

[Report Bug](https://github.com/dougjaworski/tailwind-mcp/issues) · [Request Feature](https://github.com/dougjaworski/tailwind-mcp/issues) · [Documentation](https://github.com/dougjaworski/tailwind-mcp#readme)

</div>
