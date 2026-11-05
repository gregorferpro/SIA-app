#!/bin/bash
# Certificado autofirmado para el laboratorio (sia-nginx, 10.10.10.1).
# El navegador va a advertir que no es de una autoridad pública.
set -euo pipefail

mkdir -p /etc/nginx/ssl

openssl req -x509 -nodes -days 825 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/sia.key \
  -out /etc/nginx/ssl/sia.crt \
  -subj "/CN=sia" \
  -addext "subjectAltName=IP:192.168.26.112,IP:30.30.30.1,IP:127.0.0.1,DNS:localhost,DNS:sia.192.168.26.112.nip.io"

chmod 640 /etc/nginx/ssl/sia.key
echo "Certificado escrito en /etc/nginx/ssl/sia.crt"
