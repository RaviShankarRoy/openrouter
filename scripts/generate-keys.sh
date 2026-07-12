#!/usr/bin/env bash
# generate-keys.sh — issue local TLS certs for *.openrouter.local.
# Prefers mkcert (trusted CA installed in OS keychain); falls back to a
# self-signed openssl cert if mkcert is missing.
#
# Output: certs/cert.pem + certs/key.pem at the repo root.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$ROOT_DIR/certs"
mkdir -p "$OUT_DIR"

DOMAINS=(
  "openrouter.local"
  "*.openrouter.local"
  "localhost"
  "127.0.0.1"
)

if command -v mkcert >/dev/null 2>&1; then
  echo "[certs] using mkcert"
  mkcert -install >/dev/null 2>&1 || true
  mkcert -cert-file "$OUT_DIR/cert.pem" -key-file "$OUT_DIR/key.pem" "${DOMAINS[@]}"
elif command -v openssl >/dev/null 2>&1; then
  echo "[certs] mkcert not found — falling back to self-signed openssl cert"
  echo "[certs] (browsers/curl will warn about untrusted cert; use mkcert if you can)"
  SAN=""
  for d in "${DOMAINS[@]}"; do
    if [[ "$d" =~ ^[0-9.]+$ ]]; then
      SAN+="IP:$d,"
    else
      SAN+="DNS:$d,"
    fi
  done
  SAN="${SAN%,}"
  openssl req -x509 -newkey rsa:4096 -sha256 -days 365 -nodes \
    -keyout "$OUT_DIR/key.pem" -out "$OUT_DIR/cert.pem" \
    -subj "/C=US/ST=CA/L=Local/O=OpenRouter Dev/CN=openrouter.local" \
    -addext "subjectAltName=$SAN"
else
  echo "[certs] neither mkcert nor openssl is installed; cannot continue" >&2
  exit 1
fi

chmod 600 "$OUT_DIR/key.pem"
chmod 644 "$OUT_DIR/cert.pem"
echo "[certs] wrote $OUT_DIR/cert.pem + $OUT_DIR/key.pem"
