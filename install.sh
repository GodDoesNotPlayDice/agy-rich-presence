#!/usr/bin/env bash
set -e

PLUGIN_DIR="$HOME/.gemini/config/plugins/agy-rich-presence"
REPO_URL="https://github.com/GodDoesNotPlayDice/agy-rich-presence.git"

echo "✨ Installing Antigravity Discord Rich Presence..."

mkdir -p "$HOME/.gemini/config/plugins"

if [ -d "$PLUGIN_DIR/.git" ]; then
    echo "Updating existing installation..."
    git -C "$PLUGIN_DIR" pull --quiet
else
    echo "Cloning plugin..."
    rm -rf "$PLUGIN_DIR"
    git clone --quiet "$REPO_URL" "$PLUGIN_DIR"
fi

chmod +x "$PLUGIN_DIR"/scripts/*.py "$PLUGIN_DIR"/bin/*.js 2>/dev/null || true

# Launch daemon / trigger SessionStart
python3 "$PLUGIN_DIR/scripts/discord_rpc_hook.py" SessionStart > /dev/null 2>&1 || true

echo "✅ Installed successfully to $PLUGIN_DIR"
echo "✨ Next time you open 'agy' in any terminal, Discord will show your status automatically!"
