#!/usr/bin/env bash
set -euo pipefail

API_SPEC_URL=${1:-http://localhost:8000/openapi.json}
OUT_DIR=./clients/ts

echo "Generating TypeScript client from $API_SPEC_URL"

# Ensure output directory exists
mkdir -p "$OUT_DIR"

# Set openapi-generator version
npx @openapitools/openapi-generator-cli version-manager set 7.6.0

# Generate client
npx @openapitools/openapi-generator-cli generate \
  -i "$API_SPEC_URL" \
  -g typescript-fetch \
  -o "$OUT_DIR" \
  --additional-properties=supportsES6=true,useSingleRequestParameter=true,npmName=@docbot/api-client,npmVersion=0.1.0

echo "TypeScript client generated in $OUT_DIR"
