# Antigravity Discord Rich Presence 🚀

> Real-time Discord Rich Presence integration for **Google Antigravity CLI** (`agy`). Displays your active project, agent state, and elapsed session time on your Discord profile.

---

## ✨ Features

- 🌌 **Minimalist Gemini Logo:** Official, cleanly centered Google Gemini star asset designed to look sleek and non-intrusive on Discord.
- 🚦 **Subtle Status Indicators:** Minimalist colored dots that update dynamically with agent state:
  - 🟢 **Green:** Idle / Ready for prompt.
  - 🟡 **Yellow / Amber:** Agent thinking / generating response.
  - 🟠 **Orange:** Running tools, shell commands, or inspecting files.
- 🪟 **Dynamic Window & Focus Tracking:** Working on multiple projects across different terminal windows (Alacritty, Kitty, GNOME Terminal, etc.)? Rich Presence automatically switches to whichever terminal window you currently have focused.
- ⚡ **Instant Startup & Standby:**
  - Fires immediately upon opening `agy` using the `SessionStart` hook (no prompt required to activate).
  - Clears Discord presence immediately (~0.8s) when all terminal windows are closed and enters low-resource standby mode.
  - Wakes up in less than 1 second when any new `agy` session begins.
- 🐧 **Universal Discord Compatibility:** Automatically detects Discord running on Linux via **Flatpak**, **Snap**, native packages (`.deb`, Arch/AUR), or tarballs.
- 📦 **Zero External Dependencies:** Built 100% on the Python 3 standard library. No `pip install`, no virtual environments, no bloat.

---

## 🚀 Quick Installation

Choose whichever method you prefer:

### Option A: Via `npx` (Recommended)
Run directly from GitHub without cloning:
```bash
npx github:GodDoesNotPlayDice/agy-rich-presence
```
Or via the global npm package:
```bash
npx agy-rich-presence
```

### Option B: Via `curl` (One-liner)
```bash
curl -fsSL https://raw.githubusercontent.com/GodDoesNotPlayDice/agy-rich-presence/main/install.sh | bash
```

### Option C: Manual Git Clone
```bash
git clone https://github.com/GodDoesNotPlayDice/agy-rich-presence.git ~/.gemini/config/plugins/agy-rich-presence
```

---

## 🛠️ CLI Management Commands

Once installed, you can manage the plugin anytime using the CLI:

```bash
# Check daemon, Discord socket, and active session status
npx agy-rich-presence status

# Manually start the background daemon
npx agy-rich-presence start

# Stop the daemon and clear Discord presence
npx agy-rich-presence stop

# Restart the daemon
npx agy-rich-presence restart

# Completely remove the plugin and clean up
npx agy-rich-presence uninstall
```

---

## ⚙️ Customization

You can customize the presence title or use your own Discord Application ID by editing `~/.gemini/antigravity-cli/discord_rpc_config.json`:

```json
{
  "client_id": "1510513707073929367",
  "app_name": "Antigravity better all <3"
}
```

> **Note:** If you create a custom application in the [Discord Developer Portal](https://discord.com/developers/applications), put your Application ID in `"client_id"` and your desired name in `"app_name"`.

---

## 📁 Repository Structure

```text
agy-rich-presence/
├── bin/
│   └── cli.js                  # CLI installer and management tool
├── scripts/
│   ├── discord_rpc_daemon.py  # Background daemon (standby, X11 focus tracking)
│   └── discord_rpc_hook.py    # Antigravity lifecycle hooks handler
├── config.json                 # Default configuration template
├── plugin.json                 # Official Antigravity plugin manifest
├── hooks.json                  # Lifecycle hook specifications
├── package.json                # npm package definition
├── install.sh                  # Standalone shell installer
├── uninstall.sh                # Standalone shell uninstaller
├── .gitignore
├── LICENSE                     # MIT License
└── README.md                   # Project documentation
```

---

## 📄 License

MIT License © 2026 Vicente Vasquez ([GodDoesNotPlayDice](https://github.com/GodDoesNotPlayDice))
