#!/usr/bin/env python3
"""
Discord Rich Presence Lifecycle Hook for Antigravity CLI
Triggers on SessionStart, PreInvocation, PreToolUse, PostInvocation, and Stop events.
"""
import os
import sys
import json
import time
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DAEMON_SCRIPT = os.path.join(SCRIPT_DIR, "discord_rpc_daemon.py")

CONFIG_DIR = os.path.expanduser("~/.gemini/antigravity-cli")
STATE_FILE = os.path.join(CONFIG_DIR, "discord_rpc_state.json")
PID_FILE = os.path.join(CONFIG_DIR, "discord_rpc_daemon.pid")

def get_agy_ancestor():
    curr = os.getppid()
    while curr > 1:
        try:
            with open(f"/proc/{curr}/cmdline", "rb") as f:
                cmd = f.read().replace(b"\x00", b" ").decode(errors="ignore")
                parts = cmd.strip().split()
                if parts and "agy" in os.path.basename(parts[0]):
                    return curr
            with open(f"/proc/{curr}/stat") as sf:
                curr = int(sf.read().split()[3])
        except Exception:
            break
    return os.getppid()

def is_daemon_running():
    if not os.path.exists(PID_FILE):
        return False
    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return True
    except (ValueError, OSError):
        return False

def ensure_daemon():
    if not is_daemon_running() and os.path.exists(DAEMON_SCRIPT):
        try:
            display = os.environ.get("DISPLAY", ":0")
            env = dict(os.environ, DISPLAY=display)
            if "XAUTHORITY" not in env:
                env["XAUTHORITY"] = os.path.expanduser("~/.Xauthority")
            subprocess.Popen(
                [sys.executable, DAEMON_SCRIPT],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                env=env
            )
        except Exception:
            pass

def main():
    event = sys.argv[1] if len(sys.argv) > 1 else "PreInvocation"
    
    payload = {}
    if not sys.stdin.isatty():
        try:
            stdin_data = sys.stdin.read().strip()
            if stdin_data:
                payload = json.loads(stdin_data)
        except Exception:
            pass

    workspace_paths = payload.get("workspacePaths", [])
    workspace_name = "Antigravity CLI"
    if workspace_paths and isinstance(workspace_paths, list):
        workspace_name = os.path.basename(os.path.normpath(workspace_paths[0])) or "Workspace"

    agy_pid = str(get_agy_ancestor())

    # Load state
    state_data = {"sessions": {}}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict) and "sessions" in loaded:
                    state_data = loaded
        except Exception:
            pass

    sessions = state_data.get("sessions", {})
    curr_sess = sessions.get(agy_pid, {})
    start_ts = curr_sess.get("start_timestamp", int(time.time()))

    if event == "SessionStart":
        sessions[agy_pid] = {
            "status": "idle",
            "status_text": "Listo para programar",
            "state": "Idle - Listo",
            "project": workspace_name,
            "start_timestamp": int(time.time()),
            "updated_at": time.time()
        }
    elif event == "PreInvocation":
        sessions[agy_pid] = {
            "status": "working",
            "status_text": "Pensando / Generando respuesta",
            "state": "Agent Working...",
            "project": workspace_name,
            "start_timestamp": int(time.time()),
            "updated_at": time.time()
        }
    elif event == "PreToolUse":
        tool_call = payload.get("toolCall", {})
        tool_name = tool_call.get("name", "tool")
        sessions[agy_pid] = {
            "status": "tool",
            "status_text": f"Ejecutando: {tool_name}",
            "state": f"Running {tool_name}",
            "project": workspace_name,
            "start_timestamp": start_ts,
            "updated_at": time.time()
        }
    elif event in ("PostInvocation", "Stop"):
        sessions[agy_pid] = {
            "status": "idle",
            "status_text": "Listo - Esperando prompt",
            "state": "Idle - Esperando prompt",
            "project": workspace_name,
            "start_timestamp": start_ts,
            "updated_at": time.time()
        }

    # Clean up stale sessions
    clean_sessions = {}
    for spid, sval in sessions.items():
        try:
            pid_int = int(spid)
            if os.path.exists(f"/proc/{pid_int}"):
                clean_sessions[spid] = sval
        except Exception:
            pass
    state_data["sessions"] = clean_sessions

    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state_data, f)
    except Exception:
        pass

    ensure_daemon()

    if event == "PreToolUse":
        print(json.dumps({"decision": "allow"}))
    else:
        print(json.dumps({}))

if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("{}")
