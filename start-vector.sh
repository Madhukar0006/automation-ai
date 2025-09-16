#!/bin/sh

# Base configuration file
BASE_CONFIGS="
  --config /etc/vector/config/config.yaml
"

# Start Vector with the specified configuration
exec vector $BASE_CONFIGS