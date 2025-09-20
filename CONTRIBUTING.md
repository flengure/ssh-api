# Contributing to ssh-api

Thank you for your interest in contributing to ssh-api! This document provides guidelines and information for contributors.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## How to Contribute

### Reporting Bugs
- Use the GitHub issue tracker
- Describe the bug clearly with steps to reproduce
- Include system information (OS, Docker version, etc.)
- Provide logs or error messages when possible

### Suggesting Enhancements
- Open an issue with a clear description of the enhancement
- Explain the use case and expected behavior
- Consider if the enhancement fits the project's scope

### Areas for Contribution
- **Additional MCP tools**: New tools for the MCP server
- **Security improvements**: Enhanced validation, authentication, etc.
- **Performance optimizations**: Faster response times, resource usage
- **Documentation**: Tutorials, examples, API documentation
- **Testing**: Unit tests, integration tests, security tests
- **CI/CD**: GitHub Actions workflows, automated testing

## Development Setup

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- Git

### Local Development
```bash
# Clone your fork
git clone https://github.com/flengure/ssh-api.git
cd ssh-api

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r api/requirements.txt

# Install development dependencies
pip install pytest black flake8 mypy

# Run the API server
cd api && python3 api.py

# Run the MCP server
python3 mcp/server.py
```

### Docker Development
```bash
# Build and run with Docker Compose
docker compose up --build

# Run tests in container
docker compose exec ssh-api pytest tests/
```

## Coding Standards

### Python Code Style
- Follow PEP 8
- Use Black for code formatting: `black .`
- Use flake8 for linting: `flake8 .`
- Use mypy for type checking: `mypy .`

### Code Quality
- Write comprehensive docstrings for all functions
- Include type hints for function parameters and returns
- Use meaningful variable and function names
- Keep functions focused and small
- Add comments for complex logic

### Security Considerations
- Always validate user input
- Use parameterized queries and safe string handling
- Follow the principle of least privilege
- Don't log sensitive information (keys, tokens, passwords)
- Consider security implications of new features

## Testing

### Running Tests
```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# All tests
pytest

# With coverage
pytest --cov=api --cov=mcp
```

### Writing Tests
- Write tests for all new functionality
- Include both positive and negative test cases
- Test edge cases and error conditions
- Mock external dependencies (SSH connections, etc.)
- Use descriptive test names

### Test Structure
```
tests/
├── unit/
│   ├── test_api.py
│   ├── test_mcp.py
│   └── test_validation.py
├── integration/
│   ├── test_api_integration.py
│   └── test_mcp_integration.py
└── fixtures/
    └── sample_configs.py
```

## Pull Request Process

### Before Submitting
1. **Fork the repository** and create a feature branch
2. **Make your changes** following the coding standards
3. **Add tests** for new functionality
4. **Run all tests** and ensure they pass
5. **Update documentation** if needed
6. **Run linting and formatting tools**

### Pull Request Guidelines
1. **Title**: Use a clear, descriptive title
2. **Description**: Explain what changes you made and why
3. **Testing**: Describe how you tested your changes
4. **Breaking Changes**: Highlight any breaking changes
5. **Documentation**: Update README or docs if needed

### Example PR Description
```markdown
## Summary
Add rate limiting to the REST API to prevent abuse.

## Changes
- Added Flask-Limiter dependency
- Implemented per-IP rate limiting (100 requests/hour)
- Added rate limit headers to responses
- Updated configuration documentation

## Testing
- Added unit tests for rate limiting logic
- Tested with high request volumes
- Verified proper error responses when limits exceeded

## Breaking Changes
None - this is additive functionality.
```

### Review Process
1. **Automated Checks**: All CI checks must pass
2. **Code Review**: At least one maintainer review required
3. **Testing**: Reviewer will test functionality if needed
4. **Documentation**: Ensure docs are updated appropriately

## Development Guidelines

### API Changes
- Maintain backward compatibility when possible
- Follow semantic versioning for releases
- Document API changes in CHANGELOG.md
- Update OpenAPI specification if needed

### MCP Protocol
- Follow MCP specification exactly
- Test with multiple MCP clients when possible
- Document new tools and capabilities
- Consider AI assistant use cases

### Security
- All security-related changes require extra scrutiny
- Consider attack vectors and edge cases
- Update security documentation if needed
- Test with security scanning tools

### Docker
- Test on multiple platforms (amd64, arm64)
- Keep container size minimal
- Follow Docker best practices
- Update docker-compose.yml if needed

## Getting Help

### Communication
- **Issues**: Use GitHub issues for bugs and feature requests
- **Discussions**: Use GitHub discussions for questions
- **Security**: Email maintainers directly for security issues

### Documentation
- Check the README for basic information
- Review API documentation for technical details
- Look at existing code for examples
- Ask questions in discussions if unclear

## Recognition

Contributors will be recognized in:
- CHANGELOG.md for significant contributions
- README.md contributors section
- GitHub contributor graphs and statistics

Thank you for contributing to ssh-api! 🎉