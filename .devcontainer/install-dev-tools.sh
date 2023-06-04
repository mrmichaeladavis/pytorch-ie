#!/bin/bash
export PYTHONFAULTHANDLER=1
export PYTHONHASHSEED=random
export PYTHONUNBUFFERED=1
export DEBIAN_FRONTEND=noninteractive

#/usr/local/bin/code --verbose --cli-data-dir /app/.vscode-cli tunnel --accept-server-license-terms
#/usr/local/bin/code --verbose --cli-data-dir /app/.vscode-cli tunnel service internal-run &

echo "Success! Dev Container Built."
