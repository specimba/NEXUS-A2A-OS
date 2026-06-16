FROM python:3.13-slim

LABEL maintainer="NEXUS OS"
LABEL description="NEXUS OS Phase 6 — Governed MCP Bridge Server"

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /nexus

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .[mcp]

COPY . .

EXPOSE 7354

ENV NEXUS_MCP_NAME="nexus-os-governed-mcp" \
    NEXUS_MCP_VERSION="0.6-phase6" \
    NEXUS_TRUSTKERNEL_MODE="real" \
    NEXUS_MCP_ALLOW_SIDE_EFFECTS="false"

ENTRYPOINT ["python", "-m", "nexus_os.mcp.bridge_server"]
