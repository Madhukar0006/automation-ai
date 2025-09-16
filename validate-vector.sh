#!/bin/sh

# Validate Vector configuration inside the compose service without starting Vector.
# Usage:
#   sh ./validate-vector.sh

set -e

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

docker compose -f "$SCRIPT_DIR/docker-compose-test.yaml" run --rm \
  --entrypoint vector parser-package \
  validate --config /etc/vector/config/config.yaml


