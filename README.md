# ssh-api

**Containerized OpenSSH Client with REST API & MCP Interfaces**

Transform the standard OpenSSH client into a modern API service. Execute SSH commands remotely through REST endpoints or integrate with AI assistants via Model Context Protocol (MCP).

[![Docker](https://img.shields.io/badge/docker-available-blue)](https://hub.docker.com/r/flengure/ssh-api)
[![GitHub Actions](https://github.com/flengure/ssh-api/workflows/Docker%20Build%20and%20Push/badge.svg)](https://github.com/flengure/ssh-api/actions)
[![License](https://img.shields.io/badge/license-MIT-green)](#license)
[![MCP](https://img.shields.io/badge/MCP-compatible-purple)](https://modelcontextprotocol.io/)

---

## What is this?

This project wraps the standard **OpenSSH client** (`ssh` command) with modern API interfaces:

- 🌐 **REST API**: HTTP endpoints for remote SSH command execution
- 🤖 **MCP Server**: AI assistant integration via Model Context Protocol
- 🐳 **Containerized**: Secure, isolated execution environment
- 🔑 **SSH Native**: Uses your existing SSH keys, config, and known_hosts

```
HTTP/MCP Client → [ssh-api] → OpenSSH Client → Remote SSH Server
                      ↓
                 REST + MCP APIs
               around standard ssh
```

---

## Features

### 🚀 **REST API**
- Single POST `/run` endpoint for SSH command execution
- JWT token or API key authentication
- Comprehensive input validation and security
- Health check endpoint `/healthz` for monitoring
- Detailed logging and error handling

### 🤖 **MCP Integration**
- Model Context Protocol server for AI assistants
- `ssh.run` tool for AI-powered SSH automation
- JSON-RPC 2.0 over stdio transport
- Compatible with Claude, GPT, and other MCP clients

### 🔒 **Security**
- Uses standard OpenSSH client (battle-tested security)
- Public key authentication only (no passwords)
- Directory traversal protection
- Request size limits and input validation
- Security headers and audit logging

### 🐳 **Container Benefits**
- Isolated SSH execution environment
- Read-only filesystem for security
- Your SSH keys mounted securely
- Multi-architecture support (amd64, arm64)

---

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/flengure/ssh-api.git
cd ssh-api

# Start the service
docker compose up -d
```

Your `~/.ssh` directory is automatically mounted. The API will be available at `http://localhost:8090`.

### Option 2: Docker Run

```bash
docker run -d \\
  --name ssh-api \\
  -p 8090:8090 \\
  -v ~/.ssh:/home/runner/.ssh:ro \\
  -e JWT_SECRET=your-secret-here \\
  flengure/ssh-api:latest
```

### Option 3: Custom SSH Directory

```bash
export SSH_API_SSH_DIR=/path/to/your/ssh/keys
docker compose up -d
```

---

## Usage Examples

### REST API

#### 1. Generate Authentication Token

```bash
# JWT Token
python3 -c "
import jwt, time
print(jwt.encode({
    'sub': 'your-username',
    'exp': int(time.time()) + 3600
}, 'your-jwt-secret', algorithm='HS256'))
"
```

#### 2. Execute SSH Commands

```bash
# Basic command
curl -X POST http://localhost:8090/run \\
  -H "Authorization: Bearer $TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "host": "myserver.com",
    "user": "ubuntu",
    "command": "uptime"
  }'

# Advanced options
curl -X POST http://localhost:8090/run \\
  -H "Authorization: Bearer $TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "host": "webserver",
    "command": "sudo systemctl status nginx",
    "timeout": 30,
    "strict_host_key_checking": "accept-new"
  }'
```

#### 3. Response Format

```json
{
  "exit_code": 0,
  "stdout": " 15:30:01 up 5 days, 2:15, 1 user, load average: 0.15, 0.10, 0.05\\n",
  "stderr": "",
  "duration_seconds": 0.234
}
```

### MCP Integration

#### 1. Start MCP Server

```bash
# Direct execution
python3 mcp/server.py

# Or via Docker
docker run --rm -i \\
  -v ~/.ssh:/home/runner/.ssh:ro \\
  flengure/ssh-api:latest \\
  python3 /app/mcp/server.py
```

#### 2. MCP Client Configuration

Add to your MCP client config:

```json
{
  "mcpServers": {
    "ssh-api": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-v", "/Users/you/.ssh:/home/runner/.ssh:ro",
        "flengure/ssh-api:latest",
        "python3", "/app/mcp/server.py"
      ]
    }
  }
}
```

#### 3. AI Assistant Usage

Once configured, AI assistants can execute SSH commands:

```
User: "Check disk space on my web servers"
AI: I'll check the disk space on your servers using SSH.

[Uses ssh.run tool with command "df -h"]

The disk usage on your servers:
- web1: 45% used (28GB available)
- web2: 62% used (15GB available)
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET` | `dev-secret` | JWT signing secret (⚠️ change in production) |
| `API_PORT` | `8090` | HTTP API port |
| `SSH_DIR` | `/home/runner/.ssh` | SSH directory inside container |
| `API_KEYS` | _(empty)_ | Comma-separated API keys for auth |

### SSH Configuration

The container respects your standard SSH configuration:

- **`~/.ssh/config`**: SSH client configuration
- **`~/.ssh/id_*`**: Private keys (RSA, Ed25519, etc.)
- **`~/.ssh/known_hosts`**: Host key verification
- **`~/.ssh/authorized_keys`**: Not used (this is a client)

### Security Best Practices

```bash
# Use strong JWT secrets
export JWT_SECRET=$(openssl rand -hex 32)

# Use API keys for service-to-service auth
export API_KEYS="$(openssl rand -hex 16),$(openssl rand -hex 16)"

# Limit SSH access with ~/.ssh/config
echo "Host production-*
    User admin
    Port 2222
    StrictHostKeyChecking yes" >> ~/.ssh/config
```

---

## API Reference

### REST Endpoints

#### `POST /run`

Execute SSH command on remote host.

**Authentication**: JWT Bearer token or `X-API-Key` header

**Request Body**:
```json
{
  "host": "server.example.com",
  "command": "ls -la /var/log",
  "user": "ubuntu",
  "port": 22,
  "timeout": 60,
  "strict_host_key_checking": "yes",
  "proxy_jump": "bastion.example.com",
  "allocate_tty": false,
  "extra_opts": ["-v"],
  "ssh_dir": "~/.ssh"
}
```

**Response**: SSH execution results with exit code, stdout, stderr, and duration.

#### `GET /healthz`

Health check endpoint for monitoring and load balancers.

**Response**: `{"ok": true}`

### MCP Tools

#### `ssh.run`

Execute SSH commands via Model Context Protocol.

**Parameters**: Same as REST API `/run` endpoint

**Returns**: Formatted SSH execution results for AI consumption

---

## Use Cases

### 🔧 **DevOps Automation**
- CI/CD pipeline SSH deployments
- Infrastructure health checks
- Log collection and analysis
- Configuration management

### 🤖 **AI-Powered Operations**
- Chatbot server management
- Automated troubleshooting
- Intelligent log analysis
- Natural language server queries

### 🏗️ **Integration Scenarios**
- Kubernetes job SSH execution
- Serverless function remote commands
- Microservice inter-communication
- Legacy system API wrapping

### 📊 **Monitoring & Alerts**
- Custom health checks
- Performance metric collection
- Automated remediation scripts
- Compliance auditing

---

## Development

### Local Development

```bash
# Clone and setup
git clone https://github.com/flengure/ssh-api.git
cd ssh-api

# Install dependencies
pip install -r api/requirements.txt

# Run API server
cd api && python3 api.py

# Run MCP server
python3 mcp/server.py
```

### Testing

```bash
# Test API endpoints
curl http://localhost:8090/healthz

# Test MCP server
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | python3 mcp/server.py
```

### Building Docker Images

```bash
# Build for current platform
docker build -f api/Dockerfile -t ssh-api:latest .

# Multi-architecture build
docker buildx build --platform linux/amd64,linux/arm64 -f api/Dockerfile -t ssh-api:latest .
```

---

## Security Considerations

### ✅ **Security Features**
- OpenSSH client security (battle-tested)
- Public key authentication only
- Input validation and sanitization
- Container isolation and read-only filesystem
- Security headers and audit logging

### ⚠️ **Security Notes**
- **Trust your SSH keys**: Container has access to your private keys
- **Network security**: API should run behind reverse proxy/firewall
- **JWT secrets**: Use strong, unique secrets in production
- **Host verification**: Configure `known_hosts` and `StrictHostKeyChecking`

### 🔒 **Production Deployment**
- Use HTTPS/TLS termination
- Configure proper firewall rules
- Monitor and audit SSH access
- Rotate JWT secrets regularly
- Use dedicated SSH keys for API access

---

## Troubleshooting

### Common Issues

**SSH Authentication Failed**
```bash
# Check SSH key permissions
ls -la ~/.ssh/
chmod 600 ~/.ssh/id_*
chmod 700 ~/.ssh/

# Test SSH connectivity
ssh -i ~/.ssh/id_rsa user@host
```

**Permission Denied in Container**
```bash
# Check SSH directory mounting
docker run --rm -it -v ~/.ssh:/home/runner/.ssh:ro ssh-api:latest ls -la /home/runner/.ssh/
```

**JWT Token Invalid**
```python
# Verify token generation
import jwt
token = "your-token-here"
print(jwt.decode(token, "your-secret", algorithms=["HS256"]))
```

### Debug Mode

```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG
docker compose up

# SSH verbose output
curl -X POST http://localhost:8090/run \\
  -H "Authorization: Bearer $TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"host":"server","command":"echo test","extra_opts":["-vvv"]}'
```

---

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md).

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Areas for Contribution
- Additional MCP tools and capabilities
- Enhanced security features
- Performance optimizations
- Documentation improvements
- Test coverage expansion

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Related Projects

- [OpenSSH](https://www.openssh.com/) - The SSH client this project wraps
- [Model Context Protocol](https://modelcontextprotocol.io/) - AI assistant integration standard
- [Flask](https://flask.palletsprojects.com/) - Web framework for REST API
- [Docker](https://www.docker.com/) - Containerization platform

---

**Keywords**: SSH, API, OpenSSH, MCP, Docker, REST, automation, DevOps, AI, remote execution, containerized SSH client