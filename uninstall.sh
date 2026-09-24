#!/usr/bin/env bash
set -e

PLUGIN_DIR="$HOME/.gemini/config/plugins/agy-rich-presence"
PID_FILE="$HOME/.gemini/antigravity-cli/discord_rpc_daemon.pid"

echo "🗑️  Uninstalling Antigravity Discord Rich Presence..."

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null || true)
    if [ -n "$PID" ]; then
        kill "$PID" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
fi

pkill -f "discord_rpc_daemon.py" 2>/dev/null || true

rm -rf "$PLUGIN_DIR"
rm -f "$HOME/.gemini/antigravity-cli/discord_rpc_state.json"

echo "✅ Uninstalled successfully."
