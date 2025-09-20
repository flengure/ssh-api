# Docker Hub Deployment Guide

## Repository Setup

### 1. Docker Hub Repository Creation
- **Repository Name**: `flengure/ssh-api`
- **Description**: Containerized OpenSSH Client with REST API & MCP interfaces for remote command execution
- **README**: Link to GitHub repository for full documentation

### 2. Repository Settings
- **Visibility**: Public (for better discoverability)
- **Repository Links**:
  - **Source Repository**: `https://github.com/flengure/ssh-api`
  - **Documentation**: `https://github.com/flengure/ssh-api#readme`
  - **Issue Tracker**: `https://github.com/flengure/ssh-api/issues`

### 3. Automated Builds (Recommended)
Link Docker Hub to GitHub repository for automatic building:
- **Source Type**: GitHub
- **Repository**: `flengure/ssh-api`
- **Build Rules**:
  ```
  Source: main        Docker Tag: latest
  Source: /^v.*$/     Docker Tag: {sourceref}
  ```

## Build Commands

### Manual Build and Push
```bash
# Login to Docker Hub
docker login

# Build for current platform
docker build -f api/Dockerfile -t flengure/ssh-api:latest .

# Push to Docker Hub
docker push flengure/ssh-api:latest
```

### Multi-Architecture Build
```bash
# Create and use buildx builder
docker buildx create --name multiarch --use
docker buildx inspect --bootstrap

# Build and push for multiple architectures
docker buildx build --platform linux/amd64,linux/arm64 \\
  -f api/Dockerfile \\
  -t flengure/ssh-api:latest \\
  --push .
```

### Version Tagging
```bash
# Tag specific version
docker tag flengure/ssh-api:latest flengure/ssh-api:v1.0.0
docker push flengure/ssh-api:v1.0.0

# Tag major version
docker tag flengure/ssh-api:latest flengure/ssh-api:v1
docker push flengure/ssh-api:v1
```

## Docker Hub Description Template

```markdown
# ssh-api

**Containerized OpenSSH Client with REST API & MCP Interfaces**

Transform the standard OpenSSH client into a modern API service. Execute SSH commands remotely through REST endpoints or integrate with AI assistants via Model Context Protocol (MCP).

## Quick Start

```bash
# Using Docker Compose (recommended)
git clone https://github.com/flengure/ssh-api.git
cd ssh-api
docker compose up -d

# Using Docker Run
docker run -d \\
  --name ssh-api \\
  -p 8090:8090 \\
  -v ~/.ssh:/home/runner/.ssh:ro \\
  -e JWT_SECRET=your-secret-here \\
  flengure/ssh-api:latest
```

## Features

- 🌐 **REST API**: HTTP endpoints for SSH command execution
- 🤖 **MCP Server**: AI assistant integration
- 🔒 **Security**: Input validation, container isolation
- 🐳 **Easy Deploy**: Docker Compose setup included

## Documentation

Full documentation available at: https://github.com/flengure/ssh-api

## Supported Tags

- `latest` - Latest stable release
- `v1.0.0` - Specific version releases
- `v1` - Major version tag

## Supported Architectures

- `linux/amd64`
- `linux/arm64`
```

## GitHub Actions Workflow (Optional)

Create `.github/workflows/docker.yml`:

```yaml
name: Docker Build and Push

on:
  push:
    branches: [ main ]
    tags: [ 'v*' ]
  pull_request:
    branches: [ main ]

env:
  REGISTRY: docker.io
  IMAGE_NAME: flengure/ssh-api

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - name: Checkout
      uses: actions/checkout@v4

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Login to Docker Hub
      if: github.event_name != 'pull_request'
      uses: docker/login-action@v3
      with:
        username: ${{ secrets.DOCKERHUB_USERNAME }}
        password: ${{ secrets.DOCKERHUB_TOKEN }}

    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=semver,pattern={{version}}
          type=semver,pattern={{major}}.{{minor}}
          type=semver,pattern={{major}}

    - name: Build and push
      uses: docker/build-push-action@v5
      with:
        context: .
        file: ./api/Dockerfile
        platforms: linux/amd64,linux/arm64
        push: ${{ github.event_name != 'pull_request' }}
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
```

## Required GitHub Secrets

Add these secrets to your GitHub repository settings:
- `DOCKERHUB_USERNAME`: Your Docker Hub username
- `DOCKERHUB_TOKEN`: Docker Hub access token (not password)

## Docker Hub Keywords/Tags

For better discoverability, use these tags:
- ssh
- api
- openssh
- automation
- devops
- docker
- container
- remote-execution
- mcp
- ai-tools

## Testing Docker Images

```bash
# Test the image locally
docker run --rm -it flengure/ssh-api:latest python3 --version

# Test API endpoint
docker run -d --name test-ssh-api -p 8090:8090 flengure/ssh-api:latest
curl http://localhost:8090/healthz
docker stop test-ssh-api && docker rm test-ssh-api

# Test MCP server
docker run --rm -i flengure/ssh-api:latest python3 /app/mcp/server.py <<< '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
```

## Monitoring and Maintenance

### Image Security
- Enable Docker Hub security scanning
- Monitor for base image updates
- Regular dependency updates

### Image Size
- Current image size: ~XXX MB
- Optimize with multi-stage builds if needed
- Consider Alpine-based images for smaller size

### Usage Analytics
- Monitor Docker Hub download statistics
- Track popular tags and architectures
- Use GitHub repository insights