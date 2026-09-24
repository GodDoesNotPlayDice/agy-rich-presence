# Antigravity Discord Rich Presence CLI 🚀

> Real-time Discord Rich Presence integration for **Google Antigravity CLI** (`agy`). Displays your active project, agent state, and elapsed session time on your Discord profile.

---

## ✨ Features

- 🌌 **Dual Logo Themes:** Choose between the official Google Antigravity colorful arch logo or the minimalist Google Gemini 4-pointed gradient star with instant hot-reloading (`npx agy-rich-presence icon [antigravity|gemini]`).
- 🚦 **Granular Agent Activity & Status Dots:** Real-time state strings and minimalist colored status dots that dynamically reflect exactly what the agent is doing:
  - 🟢 **Green (`Ready`):** Idle, waiting for user prompt (`Idle - Ready`).
  - 🟡 **Yellow (`Thinking`):** Analyzing context and formulating responses (`Thinking...`).
  - 🔵 **Blue (`Reading`):** Inspecting and viewing source files (`Reading app.py`).
  - 🟣 **Purple (`Editing`):** Modifying and writing code (`Editing utils.js`, `Writing component.tsx`).
  - 🟠 **Orange (`Executing`):** Running terminal commands, tests, or background tasks (`Running: npm test`).
  - 🔷 **Cyan (`Searching`):** Searching the web or exploring the codebase graph (`Searching: <query>`).
- 📊 **Multi-Project Counting & Live Activity Metrics:**
  - **Dynamic Project States:** 
    - **When all projects are idle:** Displays `{N} projects active` (e.g. `2 projects active`, `5 projects active`).
    - **When only 1 project is actively working:** Displays `Working on 1 project · <Agent State>` (e.g. `Working on 1 project · Reading app.py`, `Working on 1 project · Running: npm test`).
    - **When 2 or more projects are working simultaneously:** Displays `Working on {N} projects · <Agent State>` (e.g. `Working on 2 projects · Editing cli.js`).
  - **Live Coding Counters:** Tracks cumulative actions across all open CLI sessions in real-time on your Discord profile:
    `3 edits · 17 cmds · 10 searches · 31 reads · 7 thinks · 13m deep`
  - **Informative Tooltips:** Hovering over the large app logo reveals all active project names (`Projects: frontend, backend`), while hovering over the status dot shows the active file or command being processed (`Reading app.py`, `Running: npm test`).
- 🪟 **Dynamic Window & Focus Tracking:** Working on multiple projects across different terminal windows (Alacritty, Kitty, GNOME Terminal, etc.)? Rich Presence automatically switches to whichever terminal window you currently have focused.
- 🪟 **True Cross-Platform Support:**
  - **Linux:** Native packages, Flatpak, Snap, X11 focus tracking.
  - **Windows (Native & WSL):** PowerShell, Windows Terminal, CMD via Win32 Named Pipes and native User32 focus detection.
  - **macOS:** Standard Unix domain sockets.
- ⚡ **Instant Startup & Standby:**
  - Fires immediately upon opening `agy` using the `SessionStart` hook (no prompt required to activate).
  - Clears Discord presence immediately (~0.8s) when all terminal windows are closed and enters low-resource standby mode.
  - Wakes up in less than 1 second when any new `agy` session begins.
- 📦 **Zero External Dependencies:** Built 100% on the Python 3 standard library (`socket`, `_winapi`, `ctypes`). No `pip install`, no virtual environments, no bloat.

---

## 🚀 Quick Installation

Choose whichever method you prefer:

### Option A: Via `npx` (Universal - Linux & Windows)
Run directly from GitHub without cloning:
```bash
npx github:GodDoesNotPlayDice/agy-rich-presence
```
Or via the global npm package:
```bash
npx agy-rich-presence
```

### Option B: Windows (PowerShell One-liner)
Open PowerShell and run:
```powershell
irm https://raw.githubusercontent.com/GodDoesNotPlayDice/agy-rich-presence/main/install.ps1 | iex
```

### Option C: Linux / macOS (`curl` One-liner)
```bash
curl -fsSL https://raw.githubusercontent.com/GodDoesNotPlayDice/agy-rich-presence/main/install.sh | bash
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

You can view or update your configuration at any time:

```bash
# View current config
npx agy-rich-presence config

# Switch icon theme (antigravity or gemini)
npx agy-rich-presence icon antigravity
npx agy-rich-presence icon gemini

# Set custom Client ID and App Name
npx agy-rich-presence config <YOUR_CLIENT_ID> "Antigravity"
```

Or manually edit `~/.gemini/antigravity-cli/discord_rpc_config.json`:

```json
{
  "client_id": "1552488482918899722",
  "app_name": "Antigravity",
  "icon": "antigravity"
}
```

### 🎨 Switching Presence Icons (Antigravity vs. Gemini)

You can toggle the presence icon on the fly with instant daemon hot-reloading:

- **`antigravity`** (Default): Official Google Antigravity colorful arch logo.
- **`gemini`**: Minimalist Google Gemini 4-pointed gradient star.

```bash
# Toggle to Gemini star
npx agy-rich-presence icon gemini

# Toggle back to Antigravity arch
npx agy-rich-presence icon antigravity
```

Both 512x512 transparent PNG assets are included in [`assets/`](assets/):
- [`assets/antigravity.png`](assets/antigravity.png)
- [`assets/gemini.png`](assets/gemini.png)

### 🎨 Customizing the Channel / Voice Member List Icon
In Discord, the small badge icon displayed on the far right of your username in voice channels and server member lists is the **Application Icon** registered in the Discord Developer Portal.

To set your own custom icon (e.g. Google Gemini star):
1. Visit the [Discord Developer Portal](https://discord.com/developers/applications) and click **New Application**.
2. Give it a name (e.g., `Antigravity`).
3. Under **App Icon**, upload [`assets/logo.png`](assets/logo.png) (or your own favorite image).
4. Save Changes, copy your **Application ID**, and run:
   ```bash
   npx agy-rich-presence config <YOUR_APPLICATION_ID> "Antigravity"
   ```
5. The background daemon will hot-reload instantly—no restart needed!

---

## 📁 Repository Structure

```text
agy-rich-presence/
├── assets/
│   ├── antigravity.png         # Official Antigravity arch logo (512x512)
│   ├── gemini.png              # Google Gemini star logo (512x512)
│   └── logo.png                # Default icon asset (512x512)
├── bin/
│   └── cli.js                  # CLI installer and management tool
├── scripts/
│   ├── discord_rpc_daemon.py  # Background daemon (standby, X11 focus tracking)
│   └── discord_rpc_hook.py    # Antigravity lifecycle hooks handler
├── config.json                 # Default configuration template
├── plugin.json                 # Official Antigravity plugin manifest
├── hooks.json                  # Lifecycle hook specifications
├── package.json                # npm package definition
├── install.sh                  # Linux/macOS shell installer
├── uninstall.sh                # Linux/macOS shell uninstaller
├── install.ps1                 # Windows PowerShell installer
├── uninstall.ps1               # Windows PowerShell uninstaller
├── .gitignore
├── LICENSE                     # MIT License
└── README.md                   # Project documentation
```

---

## 📄 License

MIT License © 2026 Vicente Vasquez ([GodDoesNotPlayDice](https://github.com/GodDoesNotPlayDice))
