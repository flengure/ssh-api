#!/usr/bin/env python3
"""
ssh-api MCP stdio server

Implements the MCP handshake and a single tool:
- ssh: execute a non-interactive SSH command via OpenSSH client

Transport: JSON-RPC 2.0 over stdio (newline-delimited)
"""

import sys
import json
import os
import subprocess
from typing import Any, Dict, Optional
from pathlib import Path

# Import shared core (same repo) with proper error handling
try:
    # Add repo root to sys.path for exec_ssh import
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from exec_ssh import exec_ssh
except ImportError as e:
    print(f"Error: Cannot import exec_ssh module: {e}", file=sys.stderr)
    print("Make sure exec_ssh.py is in the repository root.", file=sys.stderr)
    sys.exit(1)

JSONRPC = "2.0"

# Validation constants
MAX_COMMAND_LENGTH = 8192
MAX_HOST_LENGTH = 253
MAX_USER_LENGTH = 32
MIN_TIMEOUT = 1
MAX_TIMEOUT = 3600
MAX_SSH_DIR_LENGTH = 4096

def validate_ssh_parameters(arguments: Dict[str, Any]) -> Optional[str]:
    """
    Validate SSH parameters and return error message if invalid.

    Args:
        arguments: Dictionary of SSH parameters

    Returns:
        None if valid, error message string if invalid
    """
    # Required parameters
    if not arguments.get("host"):
        return "Missing required parameter: host"
    if not arguments.get("command"):
        return "Missing required parameter: command"

    # Validate host
    host = arguments["host"]
    if not isinstance(host, str) or len(host.strip()) == 0:
        return "Host must be a non-empty string"
    if len(host) > MAX_HOST_LENGTH:
        return f"Host length exceeds maximum of {MAX_HOST_LENGTH} characters"

    # Validate command
    command = arguments["command"]
    if not isinstance(command, str) or len(command.strip()) == 0:
        return "Command must be a non-empty string"
    if len(command) > MAX_COMMAND_LENGTH:
        return f"Command length exceeds maximum of {MAX_COMMAND_LENGTH} characters"

    # Validate optional parameters
    user = arguments.get("user")
    if user is not None:
        if not isinstance(user, str) or len(user) > MAX_USER_LENGTH:
            return f"User must be a string with maximum {MAX_USER_LENGTH} characters"

    port = arguments.get("port")
    if port is not None:
        if not isinstance(port, int) or port < 1 or port > 65535:
            return "Port must be an integer between 1 and 65535"

    timeout = arguments.get("timeout", 60)
    if not isinstance(timeout, int) or timeout < MIN_TIMEOUT or timeout > MAX_TIMEOUT:
        return f"Timeout must be an integer between {MIN_TIMEOUT} and {MAX_TIMEOUT} seconds"

    ssh_dir = arguments.get("ssh_dir")
    if ssh_dir is not None:
        if not isinstance(ssh_dir, str) or len(ssh_dir) > MAX_SSH_DIR_LENGTH:
            return f"SSH directory path must be a string with maximum {MAX_SSH_DIR_LENGTH} characters"

    strict_host_key_checking = arguments.get("strict_host_key_checking")
    if strict_host_key_checking is not None:
        if strict_host_key_checking not in ["yes", "no", "accept-new"]:
            return "strict_host_key_checking must be one of: yes, no, accept-new"

    proxy_jump = arguments.get("proxy_jump")
    if proxy_jump is not None:
        if not isinstance(proxy_jump, str) or len(proxy_jump) > MAX_HOST_LENGTH:
            return f"Proxy jump must be a string with maximum {MAX_HOST_LENGTH} characters"

    allocate_tty = arguments.get("allocate_tty")
    if allocate_tty is not None:
        if not isinstance(allocate_tty, bool):
            return "allocate_tty must be a boolean"

    extra_opts = arguments.get("extra_opts")
    if extra_opts is not None:
        if not isinstance(extra_opts, list):
            return "extra_opts must be an array"
        for opt in extra_opts:
            if not isinstance(opt, str) or len(opt) > 256:
                return "Each extra_opts item must be a string with maximum 256 characters"

    return None

def validate_ssh_directory(ssh_dir: str) -> Optional[str]:
    """
    Validate SSH directory path for security.

    Args:
        ssh_dir: SSH directory path

    Returns:
        None if valid, error message string if invalid
    """
    if not ssh_dir:
        return None

    expanded_path = os.path.expanduser(ssh_dir)

    # Check for directory traversal attempts
    if ".." in ssh_dir or ssh_dir.startswith("/"):
        # Allow absolute paths only if they're in common SSH locations
        allowed_prefixes = ["/home/", "/Users/", os.path.expanduser("~")]
        if not any(expanded_path.startswith(prefix) for prefix in allowed_prefixes):
            return "SSH directory path not allowed"

    # Check if directory exists and is readable
    if not os.path.isdir(expanded_path):
        return f"SSH directory does not exist: {expanded_path}"

    if not os.access(expanded_path, os.R_OK):
        return f"SSH directory is not readable: {expanded_path}"

    return None

def jr(id_: Any, result: Any = None, error: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create a JSON-RPC response.

    Args:
        id_: Request identifier
        result: Success result data
        error: Error object if request failed

    Returns:
        JSON-RPC response dictionary
    """
    if error is not None:
        return {"jsonrpc": JSONRPC, "id": id_, "error": error}
    return {"jsonrpc": JSONRPC, "id": id_, "result": result}

def jerr(id_: Any, code: int, message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create a JSON-RPC error response with optional additional data.

    Args:
        id_: Request identifier
        code: Error code (should use MCPErrorCodes constants)
        message: Human-readable error message
        data: Optional additional error data

    Returns:
        JSON-RPC error response dictionary
    """
    error_obj = {"code": code, "message": message}
    if data:
        error_obj["data"] = data
    return jr(id_, error=error_obj)

# MCP-specific error codes
class MCPErrorCodes:
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    # Custom error codes for SSH operations
    SSH_CONNECTION_ERROR = -32001
    SSH_TIMEOUT_ERROR = -32002
    SSH_VALIDATION_ERROR = -32003
    SSH_DIRECTORY_ERROR = -32004

# ---- MCP handlers ----

def mcp_initialize(_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle MCP initialize request.

    Args:
        _params: Initialize parameters (unused)

    Returns:
        MCP initialize response with server capabilities
    """
    return {
        "protocolVersion": "2024-11-05",  # any recent MCP version string is fine
        "capabilities": {
            "tools": {"listChanged": False}
        },
        "serverInfo": {
            "name": "ssh-api-mcp",
            "version": "1.0.0",
        }
    }

SSH_RUN_INPUT_SCHEMA = {
    "type": "object",
    "required": ["host", "command"],
    "properties": {
        "host": {"type": "string", "description": "SSH host or alias"},
        "command": {"type": "string", "description": "Non-interactive command to run"},
        "user": {"type": "string"},
        "port": {"type": "integer"},
        "ssh_dir": {"type": "string", "description": "Path to ~/.ssh (optional)"},
        "timeout": {"type": "integer", "default": 60},
        "strict_host_key_checking": {
            "type": "string",
            "enum": ["yes", "no", "accept-new"]
        },
        "proxy_jump": {"type": "string", "description": "ProxyJump/-J host"},
        "allocate_tty": {"type": "boolean"},
        "extra_opts": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Raw ssh(1) flags, each item is one token"
        }
    }
}

def mcp_tools_list(_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle MCP tools/list request.

    Args:
        _params: List parameters (unused)

    Returns:
        Available tools list with schemas
    """
    return {
        "tools": [
            {
                "name": "ssh",
                "description": "Execute a non-interactive SSH command and return stdout/stderr/exit_code.",
                "inputSchema": SSH_RUN_INPUT_SCHEMA,
            }
        ]
    }

def mcp_tools_call(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle MCP tool call requests with comprehensive validation.

    Args:
        params: Tool call parameters including name and arguments

    Returns:
        Tool execution result in MCP format

    Raises:
        ValueError: If tool name is unknown or parameters are invalid
    """
    name = params.get("name")
    arguments = params.get("arguments") or {}

    if name != "ssh":
        raise ValueError(f"Unknown tool: {name}")

    # Validate all parameters
    validation_error = validate_ssh_parameters(arguments)
    if validation_error:
        raise ValueError(f"Invalid parameters: {validation_error}")

    # Handle SSH directory with security validation
    ssh_dir = arguments.get("ssh_dir") or os.environ.get("SSH_DIR", "")
    if ssh_dir:
        ssh_dir_error = validate_ssh_directory(ssh_dir)
        if ssh_dir_error:
            raise ValueError(f"SSH directory error: {ssh_dir_error}")
        ssh_dir = os.path.expanduser(ssh_dir)

    # All parameters are validated, safe to call exec_ssh
    res = exec_ssh(
        host=arguments["host"],
        command=arguments["command"],
        user=arguments.get("user"),
        port=arguments.get("port"),
        ssh_dir=ssh_dir,
        strict_host_key_checking=arguments.get("strict_host_key_checking"),
        proxy_jump=arguments.get("proxy_jump"),
        allocate_tty=bool(arguments.get("allocate_tty")),
        extra_opts=arguments.get("extra_opts"),
        timeout=int(arguments.get("timeout", 60)),
    )

    # Return structured result in proper MCP format
    return {
        "content": [
            {
                "type": "text",
                "text": f"SSH command completed on {arguments['host']}:\n"
                       f"Exit code: {res['exit_code']}\n"
                       f"Duration: {res['duration_seconds']}s\n"
                       f"Stdout: {res['stdout']}\n"
                       f"Stderr: {res['stderr']}"
            }
        ],
        "isError": res['exit_code'] != 0
    }

# ---- Dispatch loop ----

def handle(req: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle incoming JSON-RPC requests with comprehensive error handling.

    Args:
        req: JSON-RPC request dictionary

    Returns:
        JSON-RPC response dictionary
    """
    if not isinstance(req, dict) or req.get("jsonrpc") != JSONRPC:
        # Try to extract a valid ID, fall back to 0 if None or invalid
        req_id = req.get("id") if isinstance(req, dict) else 0
        if req_id is None:
            req_id = 0
        return jerr(req_id, MCPErrorCodes.INVALID_REQUEST, "Invalid Request")

    method = req.get("method")
    _id = req.get("id")
    # Ensure ID is never None for proper JSON-RPC compliance
    if _id is None:
        _id = 0
    params = req.get("params") or {}

    try:
        if method == "initialize":
            return jr(_id, mcp_initialize(params))
        elif method == "tools/list":
            return jr(_id, mcp_tools_list(params))
        elif method == "tools/call":
            return jr(_id, mcp_tools_call(params))
        else:
            return jerr(_id, MCPErrorCodes.METHOD_NOT_FOUND,
                       f"Method not found: {method}")

    except ValueError as e:
        error_msg = str(e)
        if "Invalid parameters:" in error_msg:
            return jerr(_id, MCPErrorCodes.SSH_VALIDATION_ERROR, error_msg)
        elif "SSH directory error:" in error_msg:
            return jerr(_id, MCPErrorCodes.SSH_DIRECTORY_ERROR, error_msg)
        else:
            return jerr(_id, MCPErrorCodes.INVALID_PARAMS, error_msg)

    except KeyError as e:
        return jerr(_id, MCPErrorCodes.INVALID_PARAMS,
                   f"Missing required parameter: {e}")

    except subprocess.TimeoutExpired:
        return jerr(_id, MCPErrorCodes.SSH_TIMEOUT_ERROR,
                   "SSH command timed out")

    except subprocess.CalledProcessError as e:
        return jerr(_id, MCPErrorCodes.SSH_CONNECTION_ERROR,
                   f"SSH command failed: {e}", {"exit_code": e.returncode})

    except Exception as e:
        return jerr(_id, MCPErrorCodes.INTERNAL_ERROR,
                   f"Internal server error: {str(e)}")

def main():
    """Main MCP server loop - read JSON-RPC requests from stdin and respond."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            # For parse errors, we can't extract an ID, so omit it per JSON-RPC spec
            error_resp = {"jsonrpc": JSONRPC, "error": {"code": MCPErrorCodes.PARSE_ERROR, "message": "Parse error: Invalid JSON"}}
            print(json.dumps(error_resp), flush=True)
            continue
        resp = handle(req)
        print(json.dumps(resp, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    main()
