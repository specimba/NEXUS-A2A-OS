"""
Tailscale Network Integration for NEXUS OS
Purpose: Provide secure networking layer for agent communication
Integration: Python module for Tailscale network management and monitoring
"""

import subprocess
import json
import logging
import socket
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TailscaleStatus(Enum):
    """Tailscale connection status"""
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    NOT_INSTALLED = "not_installed"


@dataclass
class TailscalePeer:
    """Represents a Tailscale peer/agent in the network"""
    hostname: str
    dns_name: str
    tailscale_ips: List[str]
    os: str
    online: bool
    capabilities: List[str]


@dataclass
class TailscaleNetworkState:
    """Current state of Tailscale network"""
    status: TailscaleStatus
    self_hostname: str
    self_ips: List[str]
    peers: List[TailscalePeer]
    exit_node: Optional[str]
    version: str


class TailscaleManager:
    """
    Tailscale network manager for NEXUS OS.
    
    Provides:
    - Network initialization and authentication
    - Peer discovery and monitoring
    - Network state management
    - Integration with NEXUS governance
    """
    
    def __init__(self, auth_key: Optional[str] = None, hostname: Optional[str] = None):
        """
        Initialize Tailscale manager.
        
        Args:
            auth_key: Tailscale authentication key
            hostname: Desired hostname for this node
        """
        self.auth_key = auth_key
        self.hostname = hostname or "nexus-agent-default"
        self._check_installed()
    
    def _check_installed(self) -> None:
        """Check if Tailscale is installed and accessible"""
        try:
            result = subprocess.run(
                ["tailscale", "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"Tailscale installed: {result.stdout.strip()}")
            else:
                raise RuntimeError("Tailscale command failed")
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            raise RuntimeError("Tailscale is not installed or not accessible") from e
    
    def get_status(self) -> TailscaleNetworkState:
        """
        Get current Tailscale network status.
        
        Returns:
            TailscaleNetworkState with current network information
        """
        try:
            result = subprocess.run(
                ["tailscale", "status", "--json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.error(f"Tailscale status command failed: {result.stderr}")
                return TailscaleNetworkState(
                    status=TailscaleStatus.ERROR,
                    self_hostname="",
                    self_ips=[],
                    peers=[],
                    exit_node=None,
                    version=""
                )
            
            status_data = json.loads(result.stdout)
            
            # Parse self information
            self_info = status_data.get("Self", {})
            self_hostname = self_info.get("HostName", "")
            self_ips = [
                addr.get("Addr", "") 
                for addr in self_info.get("TailscaleIPs", [])
            ]
            
            # Parse peers
            peers = []
            for peer_data in status_data.get("Peer", {}).values():
                peer = TailscalePeer(
                    hostname=peer_data.get("HostName", ""),
                    dns_name=peer_data.get("DNSName", ""),
                    tailscale_ips=peer_data.get("TailscaleIPs", []),
                    os=peer_data.get("OS", ""),
                    online=not peer_data.get("Offline", False),
                    capabilities=peer_data.get("Capabilities", [])
                )
                peers.append(peer)
            
            # Parse exit node
            exit_node = None
            if status_data.get("CurrentExitNode"):
                exit_node = status_data["CurrentExitNode"].get("TailscaleIPs", [""])[0]
            
            return TailscaleNetworkState(
                status=TailscaleStatus.RUNNING,
                self_hostname=self_hostname,
                self_ips=self_ips,
                peers=peers,
                exit_node=exit_node,
                version=status_data.get("Version", "")
            )
            
        except subprocess.TimeoutExpired:
            logger.error("Tailscale status command timed out")
            return TailscaleNetworkState(
                status=TailscaleStatus.ERROR,
                self_hostname="",
                self_ips=[],
                peers=[],
                exit_node=None,
                version=""
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Tailscale status: {e}")
            return TailscaleNetworkState(
                status=TailscaleStatus.ERROR,
                self_hostname="",
                self_ips=[],
                peers=[],
                exit_node=None,
                version=""
            )
    
    def up(self, auth_key: Optional[str] = None, hostname: Optional[str] = None,
           accept_routes: bool = False, advertise_routes: str = "",
           exit_node: str = "") -> bool:
        """
        Connect to Tailscale network.
        
        Args:
            auth_key: Tailscale authentication key (overrides instance key)
            hostname: Desired hostname (overrides instance hostname)
            accept_routes: Whether to accept subnet routes
            advertise_routes: Subnet routes to advertise
            exit_node: Exit node to use
            
        Returns:
            True if connection successful, False otherwise
        """
        auth_key = auth_key or self.auth_key
        hostname = hostname or self.hostname
        
        if not auth_key:
            logger.error("No Tailscale auth key provided")
            return False
        
        try:
            # Build command
            cmd = ["tailscale", "up", "--authkey", auth_key, "--hostname", hostname]
            
            if accept_routes:
                cmd.append("--accept-routes")
            
            if advertise_routes:
                cmd.extend(["--advertise-routes", advertise_routes])
            
            if exit_node:
                cmd.extend(["--exit-node", exit_node])
            
            logger.info(f"Connecting to Tailscale as {hostname}...")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info("Successfully connected to Tailscale")
                return True
            else:
                logger.error(f"Failed to connect to Tailscale: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Tailscale connection attempt timed out")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to Tailscale: {e}")
            return False
    
    def down(self) -> bool:
        """
        Disconnect from Tailscale network.
        
        Returns:
            True if disconnection successful, False otherwise
        """
        try:
            logger.info("Disconnecting from Tailscale...")
            result = subprocess.run(
                ["tailscale", "down"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info("Successfully disconnected from Tailscale")
                return True
            else:
                logger.error(f"Failed to disconnect from Tailscale: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Tailscale disconnect timed out")
            return False
        except Exception as e:
            logger.error(f"Unexpected error disconnecting from Tailscale: {e}")
            return False
    
    def ping(self, peer_hostname: str, count: int = 4) -> Dict[str, any]:
        """
        Ping a Tailscale peer to test connectivity.
        
        Args:
            peer_hostname: Hostname of the peer to ping
            count: Number of ping packets to send
            
        Returns:
            Dictionary with ping results
        """
        try:
            result = subprocess.run(
                ["tailscale", "ping", peer_hostname, "-c", str(count), "--json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": result.stderr,
                    "peer": peer_hostname
                }
            
            ping_data = json.loads(result.stdout)
            
            return {
                "success": True,
                "peer": peer_hostname,
                "results": ping_data
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Ping timed out",
                "peer": peer_hostname
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "peer": peer_hostname
            }
    
    def discover_peers(self) -> List[TailscalePeer]:
        """
        Discover all peers in the Tailscale network.
        
        Returns:
            List of TailscalePeer objects
        """
        state = self.get_status()
        return state.peers
    
    def get_peer_by_hostname(self, hostname: str) -> Optional[TailscalePeer]:
        """
        Find a specific peer by hostname.
        
        Args:
            hostname: Hostname to search for
            
        Returns:
            TailscalePeer if found, None otherwise
        """
        peers = self.discover_peers()
        for peer in peers:
            if peer.hostname == hostname or hostname in peer.dns_name:
                return peer
        return None
    
    def configure_exit_node(self, exit_node: str) -> bool:
        """
        Configure or change exit node.
        
        Args:
            exit_node: Exit node identifier (hostname or IP)
            
        Returns:
            True if configuration successful, False otherwise
        """
        try:
            result = subprocess.run(
                ["tailscale", "up", "--exit-node", exit_node, "--reset"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"Exit node configured: {exit_node}")
                return True
            else:
                logger.error(f"Failed to configure exit node: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Exit node configuration timed out")
            return False
        except Exception as e:
            logger.error(f"Unexpected error configuring exit node: {e}")
            return False
    
    def get_network_metrics(self) -> Dict[str, any]:
        """
        Get network performance metrics.
        
        Returns:
            Dictionary with network metrics
        """
        state = self.get_status()
        
        # Count online/offline peers
        online_peers = sum(1 for peer in state.peers if peer.online)
        offline_peers = len(state.peers) - online_peers
        
        # Ping all peers for latency metrics
        latencies = {}
        for peer in state.peers:
            if peer.online:
                ping_result = self.ping(peer.hostname, count=1)
                if ping_result.get("success") and ping_result.get("results"):
                    results = ping_result["results"]
                    if results and len(results) > 0:
                        latencies[peer.hostname] = results[0].get("LatencySec", 0)
        
        return {
            "status": state.status.value,
            "self_hostname": state.self_hostname,
            "self_ips": state.self_ips,
            "total_peers": len(state.peers),
            "online_peers": online_peers,
            "offline_peers": offline_peers,
            "exit_node": state.exit_node,
            "latencies": latencies,
            "average_latency": sum(latencies.values()) / len(latencies) if latencies else 0,
            "version": state.version
        }


class NexusTailscaleIntegrator:
    """
    Integration layer between Tailscale networking and NEXUS OS governance.
    
    Provides:
    - Network discovery for agent registration
    - Secure channel establishment for agent communication
    - Network health monitoring for anomaly detection
    - Integration with KAIJU governance for network-based policies
    """
    
    def __init__(self, tailscale_manager: TailscaleManager):
        """
        Initialize NEXUS-Tailscale integrator.
        
        Args:
            tailscale_manager: Configured TailscaleManager instance
        """
        self.tailscale = tailscale_manager
        self._peer_cache: Dict[str, TailscalePeer] = {}
        self._last_refresh = 0
        self._cache_ttl = 30  # Cache peer info for 30 seconds
    
    def refresh_peer_cache(self, force: bool = False) -> None:
        """Refresh the peer information cache"""
        import time
        current_time = time.time()
        
        if force or (current_time - self._last_refresh > self._cache_ttl):
            self._peer_cache = {
                peer.hostname: peer 
                for peer in self.tailscale.discover_peers()
            }
            self._last_refresh = current_time
            logger.debug(f"Refreshed peer cache: {len(self._peer_cache)} peers")
    
    def get_agents_in_network(self) -> List[Dict[str, any]]:
        """
        Get all NEXUS agents currently in the Tailscale network.
        
        Returns:
            List of agent information dictionaries
        """
        self.refresh_peer_cache()
        
        agents = []
        for hostname, peer in self._peer_cache.items():
            if peer.online and "nexus" in hostname.lower():
                agents.append({
                    "agent_id": hostname,
                    "hostname": peer.hostname,
                    "dns_name": peer.dns_name,
                    "tailscale_ips": peer.tailscale_ips,
                    "os": peer.os,
                    "capabilities": peer.capabilities,
                    "status": "online" if peer.online else "offline"
                })
        
        return agents
    
    def establish_secure_channel(self, target_hostname: str) -> Optional[str]:
        """
        Establish a secure communication channel to a target agent.
        
        Args:
            target_hostname: Hostname of the target agent
            
        Returns:
            Tailscale IP address if channel established, None otherwise
        """
        peer = self.tailscale.get_peer_by_hostname(target_hostname)
        
        if not peer:
            logger.error(f"Peer not found: {target_hostname}")
            return None
        
        if not peer.online:
            logger.error(f"Peer is offline: {target_hostname}")
            return None
        
        # Test connectivity
        ping_result = self.tailscale.ping(target_hostname, count=1)
        
        if not ping_result.get("success"):
            logger.error(f"Cannot reach peer {target_hostname}: {ping_result.get('error')}")
            return None
        
        # Return first available Tailscale IP
        if peer.tailscale_ips:
            return peer.tailscale_ips[0]
        
        return None
    
    def get_network_health_report(self) -> Dict[str, any]:
        """
        Generate comprehensive network health report.
        
        Returns:
            Dictionary with network health information
        """
        metrics = self.tailscale.get_network_metrics()
        agents = self.get_agents_in_network()
        
        # Calculate health score
        total_peers = metrics["total_peers"]
        online_peers = metrics["online_peers"]
        
        if total_peers == 0:
            health_score = 0
        else:
            health_score = (online_peers / total_peers) * 100
        
        # Determine health status
        if health_score >= 90:
            health_status = "excellent"
        elif health_score >= 75:
            health_status = "good"
        elif health_score >= 50:
            health_status = "degraded"
        else:
            health_status = "poor"
        
        return {
            "health_score": health_score,
            "health_status": health_status,
            "total_agents": len(agents),
            "nexus_agents": len(agents),
            "network_metrics": metrics,
            "recommendations": self._generate_health_recommendations(health_status, metrics)
        }
    
    def _generate_health_recommendations(self, health_status: str, metrics: Dict[str, any]) -> List[str]:
        """Generate health recommendations based on current state"""
        recommendations = []
        
        if health_status == "poor":
            recommendations.append("Critical: Many peers are offline. Check network connectivity.")
        
        if metrics["average_latency"] > 0.1:  # >100ms
            recommendations.append("Network latency is high. Consider optimizing network routes.")
        
        if metrics["offline_peers"] > 0:
            recommendations.append(f"{metrics['offline_peers']} peers are offline. Investigate connectivity issues.")
        
        if not metrics["exit_node"]:
            recommendations.append("No exit node configured. Consider enabling for secure external access.")
        
        return recommendations
    
    def integrate_with_kaiju(self, governor) -> None:
        """
        Integrate network state with KAIJU governance.
        
        This allows KAIJU to make policy decisions based on network state.
        
        Args:
            governor: NexusGovernor instance
        """
        health_report = self.get_network_health_report()
        
        # Update governor context with network state
        if hasattr(governor, 'update_network_context'):
            governor.update_network_context({
                "health_score": health_report["health_score"],
                "health_status": health_report["health_status"],
                "total_agents": health_report["total_agents"],
                "network_metrics": health_report["network_metrics"]
            })
        
        logger.info(f"Network state integrated with KAIJU: {health_report['health_status']}")


# Convenience function for quick setup
def setup_tailscale_network(auth_key: str, hostname: str) -> NexusTailscaleIntegrator:
    """
    Quick setup function for Tailscale networking.
    
    Args:
        auth_key: Tailscale authentication key
        hostname: Desired hostname for this node
        
    Returns:
        Configured NexusTailscaleIntegrator instance
    """
    manager = TailscaleManager(auth_key=auth_key, hostname=hostname)
    
    # Connect to Tailscale
    if not manager.up():
        raise RuntimeError("Failed to connect to Tailscale network")
    
    # Create integrator
    integrator = NexusTailscaleIntegrator(manager)
    
    logger.info(f"Tailscale network setup complete for {hostname}")
    
    return integrator


if __name__ == "__main__":
    # Test script
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python tailscale_integrator.py <auth_key> [hostname]")
        sys.exit(1)
    
    auth_key = sys.argv[1]
    hostname = sys.argv[2] if len(sys.argv) > 2 else "nexus-test-node"
    
    try:
        integrator = setup_tailscale_network(auth_key, hostname)
        
        # Print network status
        health = integrator.get_network_health_report()
        print(json.dumps(health, indent=2))
        
        # Print agents
        agents = integrator.get_agents_in_network()
        print(f"\nAgents in network: {len(agents)}")
        for agent in agents:
            print(f"  - {agent['hostname']}: {agent['tailscale_ips']}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)