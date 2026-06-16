FROM python:3.13-slim

LABEL maintainer="NEXUS OS"
LABEL description="Sterile lab for AI safety stress testing - NO internet, NO build tools, NO persistence"

# NO build-essential, NO curl, NO wget, NO netcat, NO git
# python:3.13-slim already has minimal surface

# Only Python stdlib needed - no pip installs
# The stresslab_v7 scripts only use: json, time, re, os, sys, random, pathlib,
# urllib, dataclasses, typing, uuid, argparse

# Entrypoint must be placed before USER switch (root-owned)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create non-root user and workspace
RUN addgroup --system --gid 1001 lab && \
    adduser --system --uid 1001 --ingroup lab --no-create-home lab && \
    mkdir -p /nexus/scripts /nexus/input /nexus/output && \
    chown -R lab:lab /nexus && \
    chmod -R 750 /nexus

USER lab
WORKDIR /nexus

ENTRYPOINT ["/entrypoint.sh"]
CMD ["--help"]
