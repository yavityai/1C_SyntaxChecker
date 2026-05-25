# syntaxcheck-mcp + BSL Language Server
FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends wget ca-certificates gnupg \
    && wget -qO - https://packages.adoptium.net/artifactory/api/gpg/key/public \
        | gpg --dearmor -o /usr/share/keyrings/adoptium.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/adoptium.gpg] https://packages.adoptium.net/artifactory/deb bookworm main" \
        > /etc/apt/sources.list.d/adoptium.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends temurin-21-jre \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY vendor/bsl-language-server.jar /app/bsl-language-server.jar

COPY pyproject.toml README.md bsl-language-server.json ./
COPY src ./src

RUN pip install --no-cache-dir .

ENV BSL_JAR=/app/bsl-language-server.jar \
    BSL_CONFIG=/app/bsl-language-server.json \
    BSL_MEMORY_MB=2048 \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8002

EXPOSE 8002

CMD ["python", "-m", "syntaxcheck_mcp"]
