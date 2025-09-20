FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /etc/ssh && printf '%s\n' \
    'Host *' \
    '    PreferredAuthentications publickey' \
    '    PasswordAuthentication no' \
    '    KbdInteractiveAuthentication no' \
    > /etc/ssh/ssh_config

RUN useradd -m -u 1000 runner

# Create app directory structure as root
RUN mkdir -p /app/mcp && chown -R runner:runner /app

USER runner
WORKDIR /home/runner

COPY api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY api/api.py /app/api.py
COPY exec_ssh.py /app/exec_ssh.py
COPY mcp/server.py /app/mcp/server.py

ENV PYTHONUNBUFFERED=1 \
    API_PORT=8090 \
    SSH_DIR=/home/runner/.ssh
EXPOSE 8090

# Default to API server, but allow MCP server via command override
ENTRYPOINT ["python", "/app/api.py"]
