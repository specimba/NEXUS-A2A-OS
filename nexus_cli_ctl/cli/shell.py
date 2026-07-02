"""
NEXUS Control Panel TUI (Textual)
A beautiful terminal dashboard that connects to:
- UnifiedStateManager (WebSocket sync with browser dashboard)
- Provider Health Monitor
- NEXUSCLAW orchestrator
- Model Relay status
- A2A bridge status
- Wiki/DoppelGround updates
- Mimo CLI sync
- Active integrations (Tailscale, Zo, Slack, Telegram, Discord)

Can run in terminal OR serve to web browser (Textual's web mode).
"""
import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from textual.app import App, ComposeResult
    from textual.widgets import (
        Header, Footer, Static, DataTable, Label, Button,
        Input, Log, ProgressBar, Sparkline, TabbedContent, TabPane
    )
    from textual.containers import Container, Horizontal, Vertical, Grid
    from textual.reactive import reactive
    from textual.binding import Binding
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False

logger = logging.getLogger("nexus.tui")

if TEXTUAL_AVAILABLE:
    class NexusControlPanel(App):
        """NEXUS Control Panel - 8-pane operator dashboard"""

        CSS = """
        Screen {
            background: #0a0e27;
        }

        Header {
            background: #1a1f3a;
            color: #00ffff;
            text-style: bold;
        }

        Footer {
            background: #1a1f3a;
            color: #00ffff;
        }

        .pane {
            border: solid #2a3f5a;
            background: #0d1530;
            padding: 1;
            margin: 0 1;
        }

        .pane-title {
            color: #00ffff;
            text-style: bold;
            margin-bottom: 1;
        }

        .status-good {
            color: #00ff00;
        }

        .status-warn {
            color: #ffaa00;
        }

        .status-bad {
            color: #ff5555;
        }

        DataTable {
            background: #0a0e27;
            color: #cccccc;
        }

        #command-palette {
            dock: bottom;
            height: 3;
            background: #1a1f3a;
        }

        #command-input {
            background: #2a3f5a;
            color: #ffffff;
        }
        """

        BINDINGS = [
            Binding("q", "quit", "Quit"),
            Binding("r", "refresh", "Refresh"),
            Binding("d", "toggle_dark", "Dark mode"),
            Binding("c", "cycle_check", "Cycle Check"),
            Binding("s", "show_status", "Status"),
            Binding("w", "wiki_check", "Wiki"),
            Binding("h", "show_help", "Help"),
            Binding("1", "tab_command", "Command Center"),
            Binding("2", "tab_agents", "Agent Mesh"),
            Binding("3", "tab_tasks", "Task Queue"),
            Binding("4", "tab_router", "GMR/Router"),
            Binding("5", "tab_providers", "Providers"),
            Binding("6", "tab_diagnostics", "Diagnostics"),
            Binding("7", "tab_evidence", "Evidence"),
            Binding("8", "tab_wiki", "Wiki/DoppelGround"),
            Binding("9", "tab_messaging", "Messaging"),
            Binding("0", "tab_terminal", "Terminal"),
        ]

        title = "NEXUS Control Panel"
        subtitle = "Governed Multi-Agent Operating System"

        # Reactive state
        cli_status = reactive("Initializing...")
        last_refresh = reactive("Never")

        def __init__(self, state_manager=None, brain_api_url="http://127.0.0.1:7352", **kwargs):
            super().__init__(**kwargs)
            self.sm = state_manager
            self.brain_api_url = brain_api_url
            self.refresh_task = None

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)

            with TabbedContent(initial="tab-command"):
                with TabPane("Command Center", id="tab-command"):
                    with Horizontal():
                        with Vertical(classes="pane"):
                            yield Static("System Status", classes="pane-title")
                            yield Static("Loading...", id="sys-status")

                        with Vertical(classes="pane"):
                            yield Static("Quick Actions", classes="pane-title")
                            yield Button("Cycle Check", id="btn-cycle", variant="primary")
                            yield Button("Status", id="btn-status", variant="default")
                            yield Button("Wiki Check", id="btn-wiki", variant="default")
                            yield Button("Doctor", id="btn-doctor", variant="default")
                            yield Button("Refresh All", id="btn-refresh", variant="warning")

                with TabPane("Agent Mesh", id="tab-agents"):
                    with Vertical(classes="pane"):
                        yield Static("Active Agents", classes="pane-title")
                        yield DataTable(id="agents-table")

                with TabPane("Task Queue", id="tab-tasks"):
                    with Vertical(classes="pane"):
                        yield Static("Pending / Running / Completed Tasks", classes="pane-title")
                        yield DataTable(id="tasks-table")

                with TabPane("GMR/Router", id="tab-router"):
                    with Vertical(classes="pane"):
                        yield Static("Model Relay Status", classes="pane-title")
                        yield DataTable(id="router-table")

                with TabPane("Providers", id="tab-providers"):
                    with Vertical(classes="pane"):
                        yield Static("Provider Health (Circuit Breaker Active)", classes="pane-title")
                        yield DataTable(id="providers-table")

                with TabPane("Diagnostics", id="tab-diagnostics"):
                    with Vertical(classes="pane"):
                        yield Static("A2A Bridge / Tailscale / Zo Status", classes="pane-title")
                        yield DataTable(id="diag-table")

                with TabPane("Evidence", id="tab-evidence"):
                    with Vertical(classes="pane"):
                        yield Static("Recent Evidence & Audit", classes="pane-title")
                        yield Log(id="evidence-log", auto_scroll=True)

                with TabPane("Wiki/DoppelGround", id="tab-wiki"):
                    with Vertical(classes="pane"):
                        yield Static("Wiki Pages & Search", classes="pane-title")
                        yield DataTable(id="wiki-table")
                    with Vertical(classes="pane"):
                        yield Static("Wiki Sources", classes="pane-title")
                        yield Static("Loading...", id="wiki-sources")

                with TabPane("Messaging", id="tab-messaging"):
                    with Vertical(classes="pane"):
                        yield Static("Telegram / Slack / Discord", classes="pane-title")
                        yield DataTable(id="messaging-table")
                    with Vertical(classes="pane"):
                        yield Static("Message History", classes="pane-title")
                        yield Log(id="msg-history-log", auto_scroll=True)

                with TabPane("Terminal", id="tab-terminal"):
                    with Vertical(classes="pane"):
                        yield Static("Output Log", classes="pane-title")
                        yield Log(id="terminal-log", auto_scroll=True)

            yield Input(placeholder="Enter nexusctl command and press Enter...", id="command-input")
            yield Footer()

        def on_mount(self) -> None:
            """Initialize tables and start refresh loop"""
            # Initialize tables
            agents_table = self.query_one("#agents-table", DataTable)
            agents_table.add_columns("Agent", "Status", "Trust", "Last Heartbeat")

            tasks_table = self.query_one("#tasks-table", DataTable)
            tasks_table.add_columns("Task ID", "Status", "Priority", "Agent", "Created")

            router_table = self.query_one("#router-table", DataTable)
            router_table.add_columns("Model", "Provider", "Status", "Latency")

            providers_table = self.query_one("#providers-table", DataTable)
            providers_table.add_columns("Provider", "Status", "Failures", "Avg Latency", "Recommendation")

            diag_table = self.query_one("#diag-table", DataTable)
            diag_table.add_columns("Service", "Status", "Details")

            wiki_table = self.query_one("#wiki-table", DataTable)
            wiki_table.add_columns("Slug", "Title", "Words", "Modified")

            messaging_table = self.query_one("#messaging-table", DataTable)
            messaging_table.add_columns("Platform", "Enabled", "Last Send", "Error")

            # Start background refresh
            self.refresh_task = asyncio.create_task(self._refresh_loop())

            self.log_to_terminal("NEXUS Control Panel initialized")

        async def _refresh_loop(self):
            """Refresh dashboard data every 5 seconds"""
            while True:
                try:
                    await self._refresh_all()
                except Exception as e:
                    logger.error(f"Refresh error: {e}")
                await asyncio.sleep(5)

        async def _refresh_all(self):
            """Refresh all data sections"""
            self.last_refresh = datetime.now().strftime("%H:%M:%S")

            # System status
            sys_status = self.query_one("#sys-status", Static)
            if self.sm:
                state = self.sm.get_state()
                uptime_start = state.get("metrics", {}).get("uptime_start", "unknown")
                total_events = state.get("metrics", {}).get("total_events", 0)
                ws_clients = state.get("dashboard", {}).get("connected_clients", 0)
                sys_status.update(
                    f"[green]OK[/] | Events: {total_events} | "
                    f"Dashboard clients: {ws_clients} | "
                    f"Started: {uptime_start[:19] if uptime_start != 'unknown' else 'N/A'}"
                )
            else:
                sys_status.update("[yellow]State manager not connected[/]")

            # Agent mesh
            agents_table = self.query_one("#agents-table", DataTable)
            agents_table.clear()
            if self.sm:
                agents = self.sm.get_state("nexusclaw").get("agents", {})
                for agent_id, info in agents.items():
                    trust = info.get("trust", 0.0)
                    trust_str = f"{trust:.2f}" if trust else "N/A"
                    agents_table.add_row(
                        agent_id,
                        info.get("status", "unknown"),
                        trust_str,
                        info.get("last_heartbeat", "N/A")
                    )

            # Task queue
            tasks_table = self.query_one("#tasks-table", DataTable)
            tasks_table.clear()
            if self.sm:
                tasks = self.sm.get_state("nexusclaw").get("tasks", {})
                for task_id, info in list(tasks.items())[:20]:
                    tasks_table.add_row(
                        task_id[:16],
                        info.get("status", "?"),
                        str(info.get("priority", "?")),
                        info.get("assigned_agent", "unassigned")[:12],
                        info.get("created_at", "N/A")[:19]
                    )

            # Router/Model relay
            router_table = self.query_one("#router-table", DataTable)
            router_table.clear()
            if self.sm:
                models = self.sm.get_state("model_relay").get("models", {})
                for model_id, info in list(models.items())[:15]:
                    router_table.add_row(
                        model_id[:30],
                        info.get("provider", "?"),
                        info.get("status", "?"),
                        f"{info.get('latency_ms', 0):.0f}ms"
                    )

            # Providers
            providers_table = self.query_one("#providers-table", DataTable)
            providers_table.clear()
            if self.sm:
                providers = self.sm.get_state("model_relay").get("providers", {})
                for pid, info in providers.items():
                    status = info.get("status", "unknown")
                    failures = info.get("failure_count", 0)
                    latency = info.get("avg_latency_ms", 0)
                    rec = info.get("recommendation", "?")
                    providers_table.add_row(
                        pid, status, str(failures),
                        f"{latency:.0f}ms", rec
                    )

            # Diagnostics
            diag_table = self.query_one("#diag-table", DataTable)
            diag_table.clear()
            if self.sm:
                integrations = self.sm.get_state("integrations", {})
                a2a = integrations.get("a2a_bridge", {})
                diag_table.add_row(
                    "A2A Bridge",
                    "OK" if a2a.get("alive") else "DOWN",
                    a2a.get("url", "N/A")
                )
                ts = integrations.get("tailscale", {})
                diag_table.add_row(
                    "Tailscale",
                    "OK" if ts.get("connected") else "DOWN",
                    f"Peers: {ts.get('peers', 0)}"
                )
                zo = integrations.get("zo_computer", {})
                diag_table.add_row(
                    "Zo Computer",
                    "OK" if zo.get("reachable") else "DOWN",
                    zo.get("details", "N/A")
                )
                mimo = integrations.get("mimo_cli", {})
                diag_table.add_row(
                    "Mimo CLI",
                    "OK" if mimo.get("configured") else "DOWN",
                    f"Models: {mimo.get('models_synced', 0)}"
                )
                wiki_status = integrations.get("wiki", {})
                diag_table.add_row(
                    "Wiki Pipeline",
                    "OK" if wiki_status.get("running") else "DOWN",
                    f"Pages: {wiki_status.get('pages', 0)}"
                )
                msg_status = integrations.get("messaging", {})
                diag_table.add_row(
                    "Messaging",
                    "OK" if msg_status.get("running") else "DOWN",
                    f"Platforms: {','.join(msg_status.get('enabled_platforms', [])) or 'none'}"
                )

            # Wiki pages
            wiki_table = self.query_one("#wiki-table", DataTable)
            wiki_table.clear()
            wiki_src = self.query_one("#wiki-sources", Static)
            wiki_data = await self._brain_api_get("/api/wiki")
            if wiki_data:
                wiki_pages = await self._brain_api_get("/api/wiki/pages")
                for page in (wiki_pages.get("pages") or [])[:20]:
                    wiki_table.add_row(
                        page.get("slug", "?"),
                        page.get("title", "?"),
                        str(page.get("word_count", "?")),
                        page.get("modified", "?")[:19] if page.get("modified") else "-",
                    )
                sources_data = await self._brain_api_get("/api/wiki/sources")
                source_names = [s.get("name", s.get("path", "?")) for s in (sources_data.get("sources") or [])]
                wiki_src.update(f"Sources: {', '.join(source_names[:5]) or 'none'}")
            elif self.sm:
                wiki_state = self.sm.get_state("wiki")
                pages = wiki_state.get("indexed_topics", [])
                for slug in pages[:20]:
                    wiki_table.add_row(slug, "-", "-", "-")
                wiki_src.update("Sources: (state manager fallback)")

            # Messaging
            messaging_table = self.query_one("#messaging-table", DataTable)
            messaging_table.clear()
            msg_log = self.query_one("#msg-history-log", Log)
            msg_data = await self._brain_api_get("/api/messaging")
            if msg_data:
                for platform in ["telegram", "slack", "discord"]:
                    enabled = msg_data.get(platform, False)
                    messaging_table.add_row(platform, "ON" if enabled else "OFF", "-", "")
                history = await self._brain_api_get("/api/messaging/history")
                for entry in (history.get("messages") or [])[:15]:
                    ts = entry.get("timestamp", "")[:19]
                    msg_log.write_line(f"[{ts}] {entry.get('platform', '?')}: {entry.get('message', '')[:80]}")
            elif self.sm:
                msg_state = self.sm.get_state("messaging")
                for platform in ["telegram", "slack", "discord"]:
                    enabled = msg_state.get(platform, False)
                    messaging_table.add_row(
                        platform,
                        "ON" if enabled else "OFF",
                        "-",
                        "" if enabled else "no token",
                    )

        def log_to_terminal(self, message: str):
            """Add a message to the terminal log"""
            try:
                log = self.query_one("#terminal-log", Log)
                timestamp = datetime.now().strftime("%H:%M:%S")
                log.write_line(f"[{timestamp}] {message}")
            except Exception:
                pass

        def log_evidence(self, message: str):
            """Add a message to the evidence log"""
            try:
                log = self.query_one("#evidence-log", Log)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log.write_line(f"[{timestamp}] {message}")
            except Exception:
                pass

        async def on_button_pressed(self, event: Button.Pressed) -> None:
            """Handle button presses"""
            button_id = event.button.id
            if button_id == "btn-cycle":
                self.log_to_terminal("Running cycle check...")
                await self._run_cli_command("cycle_check")
            elif button_id == "btn-status":
                self.log_to_terminal("Getting status...")
                await self._run_cli_command("status")
            elif button_id == "btn-wiki":
                self.log_to_terminal("Running wiki check...")
                await self._run_cli_command("wiki_check")
            elif button_id == "btn-doctor":
                self.log_to_terminal("Running doctor...")
                await self._run_cli_command("doctor")
            elif button_id == "btn-refresh":
                await self._refresh_all()
                self.log_to_terminal("Refreshed all data")

        async def on_input_submitted(self, event: Input.Submitted) -> None:
            """Handle command input"""
            command = event.value.strip()
            if command:
                self.log_to_terminal(f"$ nexusctl {command}")
                await self._run_cli_command(command)
                event.input.value = ""

        async def _run_cli_command(self, command: str):
            """Execute a nexusctl command and show output"""
            try:
                import subprocess
                result = subprocess.run(
                    ["python", "-m", "nexus_os.cli.nexusctl", *command.split()],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd="C:/Users/speci.000/Documents/NEXUS"
                )
                output = result.stdout or result.stderr or "(no output)"
                for line in output.split('\n')[:30]:
                    self.log_to_terminal(line)
            except subprocess.TimeoutExpired:
                self.log_to_terminal("[red]Command timed out[/]")
            except Exception as e:
                self.log_to_terminal(f"[red]Error: {e}[/]")

        async def _brain_api_get(self, path: str) -> dict:
            """Fetch data from Brain API"""
            import httpx
            try:
                from nexus_os.api.brain_api import get_brain_api_token
                token = get_brain_api_token()
            except Exception:
                token = ""
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    url = f"{self.brain_api_url}{path}"
                    resp = await client.get(url, headers={"X-Api-Key": token})
                    if resp.status_code == 200:
                        return resp.json()
            except Exception as e:
                logger.debug(f"Brain API fetch failed: {e}")
            return {}

        async def action_refresh(self):
            await self._refresh_all()
            self.log_to_terminal("Manual refresh complete")

        async def action_cycle_check(self):
            await self._run_cli_command("cycle_check")

        async def action_show_status(self):
            await self._run_cli_command("status")

        async def action_wiki_check(self):
            data = await self._brain_api_get("/api/wiki")
            pages = data.get("pages", 0)
            dossiers = data.get("dossiers", 0)
            self.log_to_terminal(f"Wiki: {pages} pages, {dossiers} dossiers")

        async def action_show_help(self):
            self.log_to_terminal("Shortcuts: q=quit r=refresh c=cycle s=status w=wiki 1-0=tabs")


async def run_tui(state_manager=None, serve_web=False, web_port=8000):
    """Run the NEXUS TUI"""
    if not TEXTUAL_AVAILABLE:
        print("Textual not installed. Install with: pip install textual")
        return

    app = NexusControlPanel(state_manager=state_manager)

    if serve_web:
        # Textual can serve to web browser!
        await app.run_async(headless=True, port=web_port)
    else:
        await app.run_async()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="NEXUS Control Panel TUI")
    parser.add_argument("--web", action="store_true", help="Serve to web browser")
    parser.add_argument("--port", type=int, default=8000, help="Web port")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_tui(serve_web=args.web, web_port=args.port))
