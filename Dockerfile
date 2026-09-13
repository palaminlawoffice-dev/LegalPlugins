FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir .

# Add the official GlobalSign intermediate certificate used by OCS.
RUN curl -fsSL \
    "https://secure.globalsign.com/cacert/gsrsaovsslca2018.crt" \
    -o /usr/local/share/ca-certificates/globalsign-rsa-ov-ssl-ca-2018.crt \
    && update-ca-certificates \
    && cat /usr/local/share/ca-certificates/globalsign-rsa-ov-ssl-ca-2018.crt \
       >> "$(python -c 'import certifi; print(certifi.where())')"

ENV MCP_TRANSPORT=http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000

EXPOSE 8000

CMD ["python", "-m", "thai_legal_mcp.server"]
