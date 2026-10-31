#!/bin/sh
set -eu
TASK_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export OLLAMA_HOST=127.0.0.1:11434
export OLLAMA_NO_CLOUD=1
export OLLAMA_MODELS="$TASK_ROOT/models"
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_CONTEXT_LENGTH=2048
export OLLAMA_KEEP_ALIVE=2m
# The official first launch creates the separately approved ~/.ollama Ed25519 keypair.
# Suppress startup key printing; inspect service status through the local API.
exec "$TASK_ROOT/.tools/ollama/ollama" serve >/dev/null 2>&1
