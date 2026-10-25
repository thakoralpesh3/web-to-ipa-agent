#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Export Gemini API Key from config if present
if [ -f "$HOME/.web2ipa/config.json" ]; then
    export GEMINI_API_KEY=$(python3 -c "import json; print(json.load(open('$HOME/.web2ipa/config.json')).get('gemini_api_key',''))" 2>/dev/null || true)
elif [ -f "$HOME/.web2apk/config.json" ]; then
    export GEMINI_API_KEY=$(python3 -c "import json; print(json.load(open('$HOME/.web2apk/config.json')).get('gemini_api_key',''))" 2>/dev/null || true)
fi

PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python3"
if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi

# Activate Virtualenv
if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
fi

# Run Agent
EXIT_CODE=0
"$PYTHON_BIN" "$SCRIPT_DIR/agent.py" "$@" || EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "⚠️ Web2IPA Agent exited with error code $EXIT_CODE."
    echo "Press Enter to close this window..."
    read -r
fi

exit $EXIT_CODE
