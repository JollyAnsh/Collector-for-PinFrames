#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")"

return_to_cli() {
    local result="$1"
    if [[ "${TERM_PROGRAM:-}" == "Apple_Terminal" && -t 0 && -t 1 ]]; then
        echo
        echo "Collector finished. You can continue using this terminal."
        exec "${SHELL:-/bin/zsh}" -l
    fi
    return "$result"
}

if [[ "$#" -eq 1 && "$1" == "-delete" ]]; then
    rm -rf -- .venv .tools .uv-cache .uv-python .playwright-browsers
    echo "Removed the collector's Python environment, uv runtime/cache, and Chromium."
    echo "The saved feed token and Pinterest login were preserved."
    return_to_cli 0
    exit $?
fi

export UV_CACHE_DIR="$PWD/.uv-cache"
export UV_PYTHON_INSTALL_DIR="$PWD/.uv-python"
export PLAYWRIGHT_BROWSERS_PATH="$PWD/.playwright-browsers"

mkdir -p .tools
if [[ ! -x .tools/uv ]]; then
    if ! curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="$PWD/.tools" sh; then
        echo "Failed to download or install uv. Check your internet connection and try again."
        if return_to_cli 1; then
            exit 0
        else
            exit $?
        fi
    fi
fi

if .tools/uv run --python 3.12 --no-project bootstrap.py "$@"; then
    result=0
else
    result=$?
fi

return_to_cli "$result"
exit $result