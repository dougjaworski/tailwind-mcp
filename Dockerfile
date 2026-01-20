# Use Python 3.11 slim base image
FROM python:3.11-slim

# Install git (required for cloning the Tailwind CSS repository)
RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY run_server.py .

# Create data directory for repository and database
RUN mkdir -p /app/data

# Set environment variables
ENV DATA_DIR=/app/data
ENV PYTHONUNBUFFERED=1

# Expose MCP port
EXPOSE 8000

# Run the server using fastmcp CLI with HTTP transport (recommended)
CMD ["sh", "-c", "python run_server.py && fastmcp run run_server.py:mcp --transport http --host 0.0.0.0 --port 8000"]
