from flask import Flask, request, jsonify
import os
import jwt
import hmac
import logging
import subprocess
from typing import Optional, Dict, Any, Tuple
from exec_ssh import exec_ssh

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration with validation
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret")
if JWT_SECRET == "dev-secret":
    logger.warning("Using default JWT secret - this is insecure for production!")

SSH_DIR = os.path.expanduser(os.environ.get("SSH_DIR", "~/.ssh"))
API_PORT = int(os.environ.get("API_PORT", "8090"))
API_KEYS = [k.strip() for k in os.environ.get("API_KEYS", "").split(",") if k.strip()]

# Validation constants (same as MCP server)
MAX_COMMAND_LENGTH = 8192
MAX_HOST_LENGTH = 253
MAX_USER_LENGTH = 32
MIN_TIMEOUT = 1
MAX_TIMEOUT = 3600
MAX_SSH_DIR_LENGTH = 4096
MAX_REQUEST_SIZE = 1024 * 1024  # 1MB

def validate_ssh_parameters(data: Dict[str, Any]) -> Optional[str]:
    """
    Validate SSH parameters and return error message if invalid.

    Args:
        data: Dictionary of SSH parameters from request

    Returns:
        None if valid, error message string if invalid
    """
    # Required parameters
    if not data.get("host"):
        return "Missing required parameter: host"
    if not data.get("command"):
        return "Missing required parameter: command"

    # Validate host
    host = data["host"]
    if not isinstance(host, str) or len(host.strip()) == 0:
        return "Host must be a non-empty string"
    if len(host) > MAX_HOST_LENGTH:
        return f"Host length exceeds maximum of {MAX_HOST_LENGTH} characters"

    # Validate command
    command = data["command"]
    if not isinstance(command, str) or len(command.strip()) == 0:
        return "Command must be a non-empty string"
    if len(command) > MAX_COMMAND_LENGTH:
        return f"Command length exceeds maximum of {MAX_COMMAND_LENGTH} characters"

    # Validate optional parameters
    user = data.get("user")
    if user is not None:
        if not isinstance(user, str) or len(user) > MAX_USER_LENGTH:
            return f"User must be a string with maximum {MAX_USER_LENGTH} characters"

    port = data.get("port")
    if port is not None:
        if not isinstance(port, int) or port < 1 or port > 65535:
            return "Port must be an integer between 1 and 65535"

    timeout = data.get("timeout", 60)
    if not isinstance(timeout, int) or timeout < MIN_TIMEOUT or timeout > MAX_TIMEOUT:
        return f"Timeout must be an integer between {MIN_TIMEOUT} and {MAX_TIMEOUT} seconds"

    ssh_dir = data.get("ssh_dir")
    if ssh_dir is not None:
        if not isinstance(ssh_dir, str) or len(ssh_dir) > MAX_SSH_DIR_LENGTH:
            return f"SSH directory path must be a string with maximum {MAX_SSH_DIR_LENGTH} characters"

    strict_host_key_checking = data.get("strict_host_key_checking")
    if strict_host_key_checking is not None:
        if strict_host_key_checking not in ["yes", "no", "accept-new"]:
            return "strict_host_key_checking must be one of: yes, no, accept-new"

    proxy_jump = data.get("proxy_jump")
    if proxy_jump is not None:
        if not isinstance(proxy_jump, str) or len(proxy_jump) > MAX_HOST_LENGTH:
            return f"Proxy jump must be a string with maximum {MAX_HOST_LENGTH} characters"

    allocate_tty = data.get("allocate_tty")
    if allocate_tty is not None:
        if not isinstance(allocate_tty, bool):
            return "allocate_tty must be a boolean"

    extra_opts = data.get("extra_opts")
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

def error_response(message: str, status_code: int = 400):
    """Create a standardized error response."""
    return jsonify({"error": message}), status_code

def verify_jwt(auth_header: str) -> Optional[Dict[str, Any]]:
    """
    Verify JWT token from Authorization header.

    Args:
        auth_header: Authorization header value

    Returns:
        Decoded JWT payload if valid, None otherwise
    """
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        logger.info(f"Valid JWT token for subject: {payload.get('sub', 'unknown')}")
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Invalid JWT token")
        return None
    except Exception as e:
        logger.error(f"JWT verification error: {e}")
        return None

def verify_api_key(req) -> bool:
    """
    Verify API key from request headers.

    Args:
        req: Flask request object

    Returns:
        True if valid API key found, False otherwise
    """
    key = req.headers.get("X-API-Key")
    if not key:
        auth = req.headers.get("Authorization", "")
        if auth.startswith("ApiKey "):
            key = auth.split(" ", 1)[1]

    if not key or not API_KEYS:
        return False

    for valid in API_KEYS:
        if hmac.compare_digest(key, valid):
            logger.info("Valid API key authentication")
            return True

    logger.warning(f"Invalid API key attempted from {req.remote_addr}")
    return False

@app.before_request
def before_request():
    """Security checks before processing requests."""
    # Check request size
    if request.content_length and request.content_length > MAX_REQUEST_SIZE:
        logger.warning(f"Request too large: {request.content_length} bytes from {request.remote_addr}")
        return jsonify({"error": "Request too large"}), 413

@app.after_request
def after_request(response):
    """Add security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

@app.route("/healthz", methods=["GET"])
def healthz():
    """Health check endpoint."""
    return jsonify({"ok": True}), 200

@app.route("/run", methods=["POST"])
def run_cmd():
    """
    Execute SSH command with comprehensive validation and error handling.

    Returns:
        JSON response with SSH command results or error information
    """
    # Authentication
    auth_jwt = verify_jwt(request.headers.get("Authorization"))
    auth_key = verify_api_key(request)
    if not (auth_jwt or auth_key):
        logger.warning(f"Unauthorized access attempt from {request.remote_addr}")
        return error_response("unauthorized", 401)

    # Parse JSON with error handling
    try:
        if not request.is_json:
            return error_response("Content-Type must be application/json", 400)

        data = request.get_json()
        if data is None:
            return error_response("Invalid JSON in request body", 400)

    except Exception as e:
        logger.error(f"JSON parsing error: {e}")
        return error_response("Invalid JSON format", 400)

    # Validate parameters
    validation_error = validate_ssh_parameters(data)
    if validation_error:
        logger.warning(f"Parameter validation failed: {validation_error}")
        return error_response(validation_error, 400)

    # Handle SSH directory with security validation
    ssh_dir = data.get("ssh_dir", SSH_DIR)
    if ssh_dir:
        ssh_dir_error = validate_ssh_directory(ssh_dir)
        if ssh_dir_error:
            logger.warning(f"SSH directory validation failed: {ssh_dir_error}")
            return error_response(ssh_dir_error, 400)
        ssh_dir = os.path.expanduser(ssh_dir)

    # Log the command execution attempt
    logger.info(f"SSH command execution: {data['host']} - {data['command'][:50]}...")

    # Execute SSH command with error handling
    try:
        res = exec_ssh(
            host=data["host"],
            command=data["command"],
            user=data.get("user"),
            port=data.get("port"),
            ssh_dir=ssh_dir,
            strict_host_key_checking=data.get("strict_host_key_checking"),
            proxy_jump=data.get("proxy_jump"),
            allocate_tty=bool(data.get("allocate_tty")),
            extra_opts=data.get("extra_opts"),
            timeout=int(data.get("timeout", 60)),
        )

        # Log execution results
        if res["exit_code"] == 0:
            logger.info(f"SSH command successful on {data['host']} (duration: {res['duration_seconds']}s)")
        else:
            logger.warning(f"SSH command failed on {data['host']} with exit code {res['exit_code']}")

        return jsonify(res), 200

    except subprocess.TimeoutExpired:
        logger.error(f"SSH command timed out on {data['host']}")
        return error_response("SSH command timed out", 504)

    except subprocess.CalledProcessError as e:
        logger.error(f"SSH process error on {data['host']}: {e}")
        return error_response(f"SSH execution failed: {e}", 500)

    except Exception as e:
        logger.error(f"Unexpected error during SSH execution: {e}")
        return error_response(f"Internal server error: {str(e)}", 500)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=API_PORT)
