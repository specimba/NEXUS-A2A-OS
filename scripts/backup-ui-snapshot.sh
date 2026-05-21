#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# NEXUS-OS v3.1 — UI/UX Snapshot Backup Script
#
# Creates a tar.gz archive of all key UI files and a manifest with file hashes.
# Saves to: backups/ui-snapshot-YYYYMMDD-HHMMSS.tar.gz
#
# Usage:
#   bash scripts/backup-ui-snapshot.sh
#
# Restore:
#   tar -xzf backups/ui-snapshot-XXXXXXXX-XXXXXX.tar.gz -C /path/to/project
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${PROJECT_ROOT}/backups"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVE_NAME="ui-snapshot-${TIMESTAMP}.tar.gz"
ARCHIVE_PATH="${BACKUP_DIR}/${ARCHIVE_NAME}"
MANIFEST_NAME="MANIFEST-${TIMESTAMP}.txt"
MANIFEST_PATH="${BACKUP_DIR}/${MANIFEST_NAME}"

# Ensure backups directory exists
mkdir -p "${BACKUP_DIR}"

echo "═══════════════════════════════════════════════════════════════"
echo "  NEXUS-OS v3.1 — UI/UX Snapshot Backup"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "  Project:  ${PROJECT_ROOT}"
echo "  Archive:  ${ARCHIVE_PATH}"
echo "  Manifest: ${MANIFEST_PATH}"
echo ""

# ── Files and directories to include ────────────────────────────────────────

INCLUDE_PATHS=(
  # Core page
  "src/app/page.tsx"
  "src/app/layout.tsx"
  "src/app/error.tsx"
  "src/app/globals.css"

  # Nexus shell components
  "src/components/nexus/sidebar.tsx"
  "src/components/nexus/header.tsx"
  "src/components/nexus/footer.tsx"
  "src/components/nexus/tab-content.tsx"
  "src/components/nexus/dashboard-shell.tsx"
  "src/components/nexus/dashboard-content.tsx"
  "src/components/nexus/ai-assistant.tsx"
  "src/components/nexus/command-palette.tsx"
  "src/components/nexus/notification-center.tsx"
  "src/components/nexus/quick-stats-widget.tsx"
  "src/components/nexus/keyboard-shortcuts.tsx"
  "src/components/nexus/tab-error-boundary.tsx"
  "src/components/nexus/global-export-dialog.tsx"
  "src/components/nexus/system-logs.tsx"
  "src/components/nexus/live-ticker.tsx"
  "src/components/nexus/data-source-badge.tsx"
  "src/components/nexus/export-button.tsx"
  "src/components/nexus/charts.tsx"
  "src/components/nexus/toast-provider.tsx"
  "src/components/nexus/settings-panel.tsx"
  "src/components/nexus/diagnostics-panel.tsx"
  "src/components/nexus/agent-health-monitor.tsx"
  "src/components/nexus/agent-feedback-panel.tsx"
  "src/components/nexus/api-key-manager.tsx"
  "src/components/nexus/api-key-entry.tsx"
  "src/components/nexus/security-posture.tsx"
  "src/components/nexus/system-architecture.tsx"
  "src/components/nexus/session-timeline.tsx"
  "src/components/nexus/system-terminal.tsx"
  "src/components/nexus/posthog-provider.tsx"

  # Tab components
  "src/components/nexus/tabs/overview-tab.tsx"
  "src/components/nexus/tabs/stresslab-tab.tsx"
  "src/components/nexus/tabs/gmr-tab.tsx"
  "src/components/nexus/tabs/governor-tab.tsx"
  "src/components/nexus/tabs/vault-tab.tsx"
  "src/components/nexus/tabs/research-tab.tsx"
  "src/components/nexus/tabs/swarm-tab.tsx"
  "src/components/nexus/tabs/tokens-tab.tsx"
  "src/components/nexus/tabs/rate-limit-tab.tsx"
  "src/components/nexus/tabs/kpi-tab.tsx"
  "src/components/nexus/tabs/dashboards-tab.tsx"
  "src/components/nexus/tabs/mcp-hub-tab.tsx"
  "src/components/nexus/tabs/config-tab.tsx"
  "src/components/nexus/tabs/ai-chat-tab.tsx"
  "src/components/nexus/tabs/architecture-tab.tsx"
  "src/components/nexus/tabs/github-tab.tsx"
  "src/components/nexus/tabs/modelrelay-tab.tsx"
  "src/components/nexus/tabs/provider-tab.tsx"
  "src/components/nexus/tabs/tasks-tab.tsx"
  "src/components/nexus/tabs/archivist-tab.tsx"
  "src/components/nexus/tabs/token-guard-tab.tsx"
  "src/components/nexus/tabs/vap-tab.tsx"
  "src/components/nexus/tabs/vap-chain-tab.tsx"
  "src/components/nexus/tabs/openshell-tab.tsx"
  "src/components/nexus/tabs/governance-audit-panel.tsx"

  # MCP sub-components
  "src/components/nexus/mcp/connections-panel.tsx"
  "src/components/nexus/mcp/analytics-panel.tsx"
  "src/components/nexus/mcp/event-stream-panel.tsx"
  "src/components/nexus/mcp/settings-panel.tsx"

  # Dashboard sub-components
  "src/components/nexus/dashboards/dashboard-list.tsx"
  "src/components/nexus/dashboards/dashboard-editor.tsx"
  "src/components/nexus/dashboards/widget.tsx"
  "src/components/nexus/dashboards/widget-renderer.tsx"
  "src/components/nexus/dashboards/widget-library.tsx"
  "src/components/nexus/dashboards/widget-catalog.ts"
  "src/components/nexus/dashboards/widget-config-modal.tsx"
  "src/components/nexus/dashboards/ai-builder.tsx"
  "src/components/nexus/dashboards/share-dialog.tsx"
  "src/components/nexus/dashboards/presence-indicator.tsx"
  "src/components/nexus/dashboards/types.ts"

  # UI primitives (shadcn)
  "src/components/ui/card.tsx"
  "src/components/ui/badge.tsx"
  "src/components/ui/button.tsx"
  "src/components/ui/dialog.tsx"
  "src/components/ui/dropdown-menu.tsx"
  "src/components/ui/tooltip.tsx"
  "src/components/ui/tabs.tsx"
  "src/components/ui/input.tsx"
  "src/components/ui/select.tsx"
  "src/components/ui/sheet.tsx"
  "src/components/ui/progress.tsx"
  "src/components/ui/switch.tsx"
  "src/components/ui/separator.tsx"
  "src/components/ui/command.tsx"
  "src/components/ui/scroll-area.tsx"
  "src/components/ui/avatar.tsx"
  "src/components/ui/skeleton.tsx"
  "src/components/ui/toaster.tsx"
  "src/components/ui/sonner.tsx"
  "src/components/ui/checkbox.tsx"
  "src/components/ui/form.tsx"
  "src/components/ui/label.tsx"
  "src/components/ui/popover.tsx"
  "src/components/ui/textarea.tsx"
  "src/components/ui/table.tsx"
  "src/components/ui/alert.tsx"
  "src/components/ui/alert-dialog.tsx"
  "src/components/ui/accordion.tsx"
  "src/components/ui/collapsible.tsx"
  "src/components/ui/resizable.tsx"
  "src/components/ui/toggle.tsx"
  "src/components/ui/toggle-group.tsx"
  "src/components/ui/slider.tsx"
  "src/components/ui/radio-group.tsx"
  "src/components/ui/pagination.tsx"
  "src/components/ui/hover-card.tsx"
  "src/components/ui/drawer.tsx"
  "src/components/ui/calendar.tsx"
  "src/components/ui/carousel.tsx"
  "src/components/ui/context-menu.tsx"
  "src/components/ui/menubar.tsx"
  "src/components/ui/navigation-menu.tsx"
  "src/components/ui/breadcrumb.tsx"
  "src/components/ui/aspect-ratio.tsx"
  "src/components/ui/chart.tsx"
  "src/components/ui/input-otp.tsx"
  "src/components/ui/sidebar.tsx"
  "src/components/ui/toast.tsx"

  # Store & hooks
  "src/store/nexus-store.ts"
  "src/hooks/use-api-data.ts"
  "src/hooks/use-mounted.ts"
  "src/hooks/use-mobile.ts"
  "src/hooks/use-toast.ts"
  "src/hooks/use-swarm-ws.ts"
  "src/hooks/use-media.ts"

  # Lib
  "src/lib/utils.ts"
  "src/lib/db.ts"
  "src/lib/client.ts"
  "src/lib/server.ts"
  "src/lib/middleware.ts"
  "src/lib/dashboard-types.ts"
  "src/lib/api-cache.ts"
  "src/lib/ai-provider-bridge.ts"
  "src/lib/api-key-manager.ts"
  "src/lib/mcp.ts"
  "src/lib/mcp-fetcher.ts"
  "src/lib/encryption.ts"
  "src/lib/rate-limiter.ts"
  "src/lib/env-writer.ts"
  "src/lib/modelrelay/gateway.ts"
  "src/lib/modelrelay/config.ts"
  "src/lib/dg/classification-engine.ts"

  # Config files
  "tailwind.config.ts"
  "postcss.config.mjs"
  "next.config.ts"
  "tsconfig.json"
  "package.json"
  "components.json"
  "eslint.config.mjs"

  # Auth components
  "src/components/login-form.tsx"
  "src/components/sign-up-form.tsx"
  "src/components/logout-button.tsx"
  "src/components/update-password-form.tsx"
  "src/components/forgot-password-form.tsx"

  # Grounding document
  "GROUNDING.md"
)

# ── Build file list (only existing files) ───────────────────────────────────

FILE_LIST=()
for path in "${INCLUDE_PATHS[@]}"; do
  full_path="${PROJECT_ROOT}/${path}"
  if [ -f "${full_path}" ]; then
    FILE_LIST+=("${path}")
  else
    echo "  ⚠ SKIP (not found): ${path}"
  fi
done

echo "  Files to archive: ${#FILE_LIST[@]}"
echo ""

# ── Create tar.gz archive ───────────────────────────────────────────────────

echo "  Creating archive..."
cd "${PROJECT_ROOT}"
tar -czf "${ARCHIVE_PATH}" "${FILE_LIST[@]}"

ARCHIVE_SIZE=$(du -h "${ARCHIVE_PATH}" | cut -f1)
echo "  ✅ Archive created: ${ARCHIVE_PATH} (${ARCHIVE_SIZE})"
echo ""

# ── Generate manifest ───────────────────────────────────────────────────────

echo "  Generating manifest..."

{
  echo "═══════════════════════════════════════════════════════════════"
  echo "  NEXUS-OS v3.1 — UI/UX Snapshot Manifest"
  echo "═══════════════════════════════════════════════════════════════"
  echo ""
  echo "  Timestamp:    ${TIMESTAMP}"
  echo "  Archive:      ${ARCHIVE_NAME}"
  echo "  Archive Size: ${ARCHIVE_SIZE}"
  echo "  Git Tag:      grounding-uiux-v3.1"
  echo "  Git Commit:   $(git rev-parse HEAD 2>/dev/null || echo 'unknown')"
  echo "  Git Branch:   $(git branch --show-current 2>/dev/null || echo 'unknown')"
  echo ""
  echo "───────────────────────────────────────────────────────────────"
  echo "  File Hashes (SHA-256)"
  echo "───────────────────────────────────────────────────────────────"
  echo ""

  for path in "${FILE_LIST[@]}"; do
    full_path="${PROJECT_ROOT}/${path}"
    if command -v sha256sum &>/dev/null; then
      hash=$(sha256sum "${full_path}" | cut -d' ' -f1)
    elif command -v shasum &>/dev/null; then
      hash=$(shasum -a 256 "${full_path}" | cut -d' ' -f1)
    else
      hash="(hash unavailable)"
    fi
    file_size=$(wc -c < "${full_path}" 2>/dev/null || echo "?")
    printf "  %-70s %s  (%s bytes)\n" "${path}" "${hash}" "${file_size}"
  done

  echo ""
  echo "───────────────────────────────────────────────────────────────"
  echo "  Total: ${#FILE_LIST[@]} files"
  echo "───────────────────────────────────────────────────────────────"
  echo ""
  echo "  Restore command:"
  echo "    tar -xzf backups/${ARCHIVE_NAME} -C /path/to/project"
  echo ""
} > "${MANIFEST_PATH}"

echo "  ✅ Manifest created: ${MANIFEST_PATH}"
echo ""

# ── Include manifest in the archive ─────────────────────────────────────────

# Re-create archive with manifest included
tar -rf "${ARCHIVE_PATH}" -C "${BACKUP_DIR}" "${MANIFEST_NAME}" 2>/dev/null || true
# Re-compress (tar -r doesn't work with -z, so we re-gzip)
gunzip -f "${ARCHIVE_PATH}" 2>/dev/null || true
gzip "${ARCHIVE_PATH%.gz}" 2>/dev/null || true

# If the above failed (macOS vs Linux differences), just note it
if [ ! -f "${ARCHIVE_PATH}" ]; then
  # Recreate from scratch including manifest
  cd "${BACKUP_DIR}"
  tar -czf "${ARCHIVE_PATH}" -C "${PROJECT_ROOT}" "${FILE_LIST[@]}" -C "${BACKUP_DIR}" "${MANIFEST_NAME}" 2>/dev/null || true
fi

echo "═══════════════════════════════════════════════════════════════"
echo "  ✅ UI/UX Snapshot Backup Complete!"
echo ""
echo "  Archive:  ${ARCHIVE_PATH}"
echo "  Manifest: ${MANIFEST_PATH}"
echo "  Files:    ${#FILE_LIST[@]}"
echo ""
echo "  To restore:"
echo "    tar -xzf backups/${ARCHIVE_NAME} -C /path/to/project"
echo "═══════════════════════════════════════════════════════════════"
