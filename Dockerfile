FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir .

# Download the official GlobalSign RSA OV SSL CA 2018
# certificate in DER format and convert it to PEM.
RUN curl -fsSL \
    "https://secure.globalsign.com/cacert/gsrsaovsslca2018.crt" \
    -o /tmp/globalsign-rsa-ov-ssl-ca-2018.der \
    && openssl x509 \
        -inform DER \
        -in /tmp/globalsign-rsa-ov-ssl-ca-2018.der \
        -out /tmp/globalsign-rsa-ov-ssl-ca-2018.pem \
    && cat /tmp/globalsign-rsa-ov-ssl-ca-2018.pem \
        >> "$(python -c 'import certifi; print(certifi.where())')" \
    && rm -f \
        /tmp/globalsign-rsa-ov-ssl-ca-2018.der \
        /tmp/globalsign-rsa-ov-ssl-ca-2018.pem

ENV MCP_TRANSPORT=http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000

EXPOSE 8000

CMD ["python", "-m", "thai_legal_mcp.server"]
