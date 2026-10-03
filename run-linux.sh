#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [[ "$#" -eq 1 && "$1" == "-delete" ]]; then
    rm -rf -- .venv .tools .uv-cache .uv-python .playwright-browsers
    echo "Removed the collector's Python environment, uv runtime/cache, and Chromium."
    echo "The saved feed token and Pinterest login were preserved."
    exit 0
fi

export UV_CACHE_DIR="$PWD/.uv-cache"
export UV_PYTHON_INSTALL_DIR="$PWD/.uv-python"
export PLAYWRIGHT_BROWSERS_PATH="$PWD/.playwright-browsers"

mkdir -p .tools
if [[ ! -x .tools/uv ]]; then
    curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="$PWD/.tools" sh
fi

exec .tools/uv run --python 3.12 --no-project bootstrap.py "$@"