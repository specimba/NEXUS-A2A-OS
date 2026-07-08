# NEXUS A2A OS — Governed MCP Server Dockerfile
# Phase 6 - Security First

FROM python:3.11-slim

WORKDIR /app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash nexus

# Copy server code
COPY governed_mcp_server.py /app/
COPY security_tests/ /app/security_tests/

# Set ownership
RUN chown -R nexus:nexus /app

USER nexus

ENV PYTHONUNBUFFERED=1
ENV NEXUS_LOG_LEVEL=INFO
ENV NEXUS_TRUSTKERNEL_MODE=stub

# Healthcheck (simple)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import governed_mcp_server; print('healthy')" || exit 1

ENTRYPOINT ["python", "governed_mcp_server.py"]
