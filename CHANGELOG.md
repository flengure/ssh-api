# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-XX

### Added
- **REST API**: HTTP endpoint for SSH command execution with JWT/API key authentication
- **MCP Server**: Model Context Protocol integration for AI assistants
- **Security Features**:
  - Comprehensive input validation and sanitization
  - Directory traversal protection
  - Request size limits
  - Security headers
  - Audit logging
- **Docker Support**: Containerized deployment with docker-compose
- **SSH Features**:
  - Standard OpenSSH client integration
  - Support for SSH config, keys, and known_hosts
  - ProxyJump, timeout, and advanced SSH options
- **Documentation**: Complete API documentation and usage examples

### Security
- Public key authentication only (no password auth)
- Container isolation with read-only filesystem
- Input validation for all parameters
- Protection against directory traversal attacks
- Comprehensive error handling without information leakage

### Technical Details
- Built on Flask for REST API
- JSON-RPC 2.0 for MCP protocol
- Python 3.11+ compatibility
- Multi-architecture Docker images (amd64, arm64)
- Comprehensive logging and monitoring

## [Unreleased]

### Planned
- Additional MCP tools and capabilities
- Performance optimizations
- Enhanced monitoring and metrics
- Rate limiting improvements