"""tests/governor/test_privilege_control.py — ProgentPrivilegeControl tests"""

import pytest
from nexus_os.governor.privilege_control import ProgentPrivilegeControl, PrivilegePolicy
from nexus_os.bridge.gross_bridge import GrossMCPBridge
from nexus_os.mcp.client import MCPToolInfo


class TestProgentPrivilegeControl:

    def test_default_empty_policy_blocks_all(self):
        policy = PrivilegePolicy()
        bouncer = ProgentPrivilegeControl(policy)
        assert bouncer.check_call("read_file", {"AbsolutePath": "C:/temp.txt"}) is False

    def test_allowed_tool_without_constraints(self):
        policy = PrivilegePolicy(
            allowed_tools={
                "read_file": {}  # Empty constraints means allowed globally
            }
        )
        bouncer = ProgentPrivilegeControl(policy)
        assert bouncer.check_call("read_file", {"AbsolutePath": "C:/temp.txt"}) is True
        assert bouncer.check_call("write_file", {"AbsolutePath": "C:/temp.txt"}) is False

    def test_argument_regex_constraints(self):
        policy = PrivilegePolicy(
            allowed_tools={
                "read_file": {
                    "AbsolutePath": [r"^C:/Users/speci\.000/Documents/NEXUS/.*\.py$"]
                }
            }
        )
        bouncer = ProgentPrivilegeControl(policy)
        
        # Valid path matches regex
        assert bouncer.check_call(
            "read_file", 
            {"AbsolutePath": "C:/Users/speci.000/Documents/NEXUS/test.py"}
        ) is True
        
        # Invalid file type
        assert bouncer.check_call(
            "read_file", 
            {"AbsolutePath": "C:/Users/speci.000/Documents/NEXUS/secret.txt"}
        ) is False

        # Invalid base directory
        assert bouncer.check_call(
            "read_file", 
            {"AbsolutePath": "C:/Windows/System32/cmd.exe"}
        ) is False

        # Missing constrained argument
        assert bouncer.check_call("read_file", {}) is False

    def test_monotonic_narrowing(self):
        initial_policy = PrivilegePolicy(
            allowed_tools={
                "read_file": {
                    "AbsolutePath": [
                        r"^C:/Users/speci\.000/Documents/NEXUS/.*\.py$",
                        r"^C:/Users/speci\.000/Documents/NEXUS/.*\.txt$"
                    ]
                },
                "write_file": {}
            }
        )
        bouncer = ProgentPrivilegeControl(initial_policy)

        # Narrowing 1: remove one of the allowed patterns (more restrictive)
        narrowed_policy = PrivilegePolicy(
            allowed_tools={
                "read_file": {
                    "AbsolutePath": [
                        r"^C:/Users/speci\.000/Documents/NEXUS/.*\.py$"
                    ]
                },
                "write_file": {}
            }
        )
        assert bouncer.narrow_policy(narrowed_policy) is True
        assert bouncer.policy == narrowed_policy

        # Expansion 1: Add new tool (should be rejected)
        expanded_policy = PrivilegePolicy(
            allowed_tools={
                "read_file": {
                    "AbsolutePath": [r"^C:/Users/speci\.000/Documents/NEXUS/.*\.py$"]
                },
                "write_file": {},
                "delete_file": {}  # Unapproved tool expansion
            }
        )
        assert bouncer.narrow_policy(expanded_policy) is False

        # Expansion 2: Remove restriction on read_file argument (should be rejected)
        expanded_args_policy = PrivilegePolicy(
            allowed_tools={
                "read_file": {},  # Removed AbsolutePath restriction
                "write_file": {}
            }
        )
        assert bouncer.narrow_policy(expanded_args_policy) is False

    def test_gross_bridge_integration(self):
        # Configure bridge with a custom policy restricting file reading
        policy = PrivilegePolicy(
            allowed_tools={
                "read_file": {
                    "AbsolutePath": [r"^C:/Users/speci\.000/Documents/NEXUS/.*"]
                }
            }
        )
        bridge = GrossMCPBridge(privilege_policy=policy)
        
        # Mock client initialization and list tools
        bridge._registered = True
        bridge._client._tools = {
            "read_file": MCPToolInfo("read_file", "Read file contents", {}),
            "write_file": MCPToolInfo("write_file", "Write file contents", {})
        }

        # Check call_tool validates via privilege control
        # Allowed path
        res_allowed = bridge.call_tool("read_file", {"AbsolutePath": "C:/Users/speci.000/Documents/NEXUS/01_PROJECT_STATE.md"})
        # The privilege check should PASS, but since we are not connected to a real server,
        # the underlying client.call_tool will attempt to make a connection and might fail.
        # However, if it fails at the client level, it is not blocked by privilege control.
        # Let's verify that a blocked call gets intercepted and returns a blocked MCPCallResult directly.
        
        res_blocked_arg = bridge.call_tool("read_file", {"AbsolutePath": "C:/Windows/System32/cmd.exe"})
        assert res_blocked_arg.blocked is True
        assert "Blocked by Progent" in res_blocked_arg.reason

        res_blocked_tool = bridge.call_tool("write_file", {"AbsolutePath": "C:/Users/speci.000/Documents/NEXUS/01_PROJECT_STATE.md"})
        assert res_blocked_tool.blocked is True
        assert "Blocked by Progent" in res_blocked_tool.reason

    def test_interval_constraints(self):
        # 1. Numerical range [10, 100]
        policy_range = PrivilegePolicy(
            allowed_tools={
                "write_file": {
                    "max_bytes": ["[10, 100]"]
                }
            }
        )
        bouncer = ProgentPrivilegeControl(policy_range)
        assert bouncer.check_call("write_file", {"max_bytes": 10}) is True
        assert bouncer.check_call("write_file", {"max_bytes": 50}) is True
        assert bouncer.check_call("write_file", {"max_bytes": 100}) is True
        assert bouncer.check_call("write_file", {"max_bytes": 9}) is False
        assert bouncer.check_call("write_file", {"max_bytes": 101}) is False

        # 2. Open range (10, 100)
        policy_open = PrivilegePolicy(
            allowed_tools={
                "write_file": {
                    "max_bytes": ["(10, 100)"]
                }
            }
        )
        bouncer = ProgentPrivilegeControl(policy_open)
        assert bouncer.check_call("write_file", {"max_bytes": 10}) is False
        assert bouncer.check_call("write_file", {"max_bytes": 50}) is True
        assert bouncer.check_call("write_file", {"max_bytes": 100}) is False

        # 3. Inequality < 100
        policy_lt = PrivilegePolicy(
            allowed_tools={
                "write_file": {
                    "max_bytes": ["< 100"]
                }
            }
        )
        bouncer = ProgentPrivilegeControl(policy_lt)
        assert bouncer.check_call("write_file", {"max_bytes": 99.9}) is True
        assert bouncer.check_call("write_file", {"max_bytes": 100}) is False
        assert bouncer.check_call("write_file", {"max_bytes": -500}) is True

        # 4. Inequality >= 10
        policy_gte = PrivilegePolicy(
            allowed_tools={
                "write_file": {
                    "max_bytes": [">= 10"]
                }
            }
        )
        bouncer = ProgentPrivilegeControl(policy_gte)
        assert bouncer.check_call("write_file", {"max_bytes": 10}) is True
        assert bouncer.check_call("write_file", {"max_bytes": 9.9}) is False

    def test_monotonic_narrowing_intervals(self):
        # Initial policy: allowed space is [10, 100]
        initial_policy = PrivilegePolicy(
            allowed_tools={
                "write_file": {
                    "max_bytes": ["[10, 100]"]
                }
            }
        )
        bouncer = ProgentPrivilegeControl(initial_policy)

        # Narrowing: subset interval [20, 80]
        narrowed = PrivilegePolicy(
            allowed_tools={
                "write_file": {
                    "max_bytes": ["[20, 80]"]
                }
            }
        )
        assert bouncer.narrow_policy(narrowed) is True
        assert bouncer.policy.allowed_tools["write_file"]["max_bytes"] == ["[20, 80]"]

        # Expansion: superset interval [5, 120] (should fail)
        expanded = PrivilegePolicy(
            allowed_tools={
                "write_file": {
                    "max_bytes": ["[5, 120]"]
                }
            }
        )
        assert bouncer.narrow_policy(expanded) is False

        # Narrowing: inequality from < 100 to <= 50
        initial_lt = PrivilegePolicy(
            allowed_tools={
                "write_file": {
                    "max_bytes": ["< 100"]
                }
            }
        )
        bouncer_lt = ProgentPrivilegeControl(initial_lt)
        narrowed_lt = PrivilegePolicy(
            allowed_tools={
                "write_file": {
                    "max_bytes": ["<= 50"]
                }
            }
        )
        assert bouncer_lt.narrow_policy(narrowed_lt) is True

        # Expansion: inequality from < 100 to <= 200 (should fail)
        expanded_lt = PrivilegePolicy(
            allowed_tools={
                "write_file": {
                    "max_bytes": ["<= 200"]
                }
            }
        )
        assert bouncer_lt.narrow_policy(expanded_lt) is False

    def test_deny_override_rules(self):
        # 1. Global block via forbid rule
        policy = PrivilegePolicy(
            allowed_tools={
                "execute_command": {}
            },
            forbidden_tools={
                "execute_command": {}  # Empty dict = global forbid
            }
        )
        bouncer = ProgentPrivilegeControl(policy)
        assert bouncer.check_call("execute_command", {"command": "ls"}) is False

        # 2. Argument-based forbid rule
        policy_arg = PrivilegePolicy(
            allowed_tools={
                "execute_command": {}
            },
            forbidden_tools={
                "execute_command": {
                    "command": [r"^rm.*"]
                }
            }
        )
        bouncer_arg = ProgentPrivilegeControl(policy_arg)
        # allowed because it is not forbidden
        assert bouncer_arg.check_call("execute_command", {"command": "ls"}) is True
        # forbidden because it matches the forbid pattern
        assert bouncer_arg.check_call("execute_command", {"command": "rm -rf /"}) is False

    def test_monotonic_forbid_updates(self):
        # Initial policy: execute_command allowed, but no forbid rules
        initial_policy = PrivilegePolicy(
            allowed_tools={
                "execute_command": {}
            },
            forbidden_tools={
                "execute_command": {
                    "command": [r"^rm.*"]
                }
            }
        )
        bouncer = ProgentPrivilegeControl(initial_policy)

        # Narrowing forbid constraints: make forbid rule broader (forbids more things: e.g. rm and mv)
        narrowed_forbid = PrivilegePolicy(
            allowed_tools={
                "execute_command": {}
            },
            forbidden_tools={
                "execute_command": {
                    "command": [r"^rm.*", r"^mv.*"]
                }
            }
        )
        # Since next_policy forbids more, it's a narrowing, so this is allowed
        # Let's trace ProgentPrivilegeControl:
        # for c_pat in current_patterns (r"^rm.*"):
        #     is c_pat subset of any next_patterns?
        #     Yes, c_pat is equal/subset to n_pat (r"^rm.*" in next_patterns).
        # So is_subset is True. It passes!
        assert bouncer.narrow_policy(narrowed_forbid) is True

        # Expansion forbid constraints: make forbid rule narrower (forbids fewer things: back to just rm)
        # Wait, if we try to narrow the forbid from rm+mv back to just rm, that expands allowed actions (should fail)
        expanded_forbid = PrivilegePolicy(
            allowed_tools={
                "execute_command": {}
            },
            forbidden_tools={
                "execute_command": {
                    "command": [r"^rm.*"]
                }
            }
        )
        assert bouncer.narrow_policy(expanded_forbid) is False

