#!/usr/bin/env python3
"""
Discord Rich Presence Daemon for Antigravity CLI
- Automatically detects active project via X11 focused terminal window.
- Dynamically updates Discord presence (Project, state, and status dots).
- When all terminals are closed, clears Discord presence immediately and enters standby mode.
- When Antigravity CLI re-opens, immediately wakes up and restores presence in <1 second.
"""
import os
import sys
import time
import json
import socket
import struct
import signal
import uuid
import subprocess
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(SCRIPT_DIR)

CONFIG_DIR = os.path.expanduser("~/.gemini/antigravity-cli")
STATE_FILE = os.path.join(CONFIG_DIR, "discord_rpc_state.json")
PID_FILE = os.path.join(CONFIG_DIR, "discord_rpc_daemon.pid")
USER_CONFIG_FILE = os.path.join(CONFIG_DIR, "discord_rpc_config.json")
DEFAULT_CONFIG_FILE = os.path.join(PLUGIN_ROOT, "config.json")

# Verified assets compatible with Discord image proxy
LOGO_GEMINI = "https://i.imgur.com/YrOxqad.png"
LOGO_ANTIGRAVITY = "https://i.imgur.com/XSSjEth.png"
LOGO_CLAUDE = "https://i.imgur.com/gCQdTjC.png"      # Claude / Anthropic icon

ICON_IDLE = "https://i.imgur.com/uixaTPM.png"       # 🟢 Minimalist Green Dot
ICON_WORKING = "https://i.imgur.com/jjXT03E.png"    # 🟡 Minimalist Yellow Dot
ICON_READING = "https://i.imgur.com/5j7bhv4.png"    # 🔵 Minimalist Blue Dot
ICON_EDITING = "https://i.imgur.com/FsdDnuj.png"    # 🟣 Minimalist Purple Dot
ICON_EXECUTING = "https://i.imgur.com/4axLLtM.png"  # 🟠 Minimalist Orange Dot
ICON_SEARCHING = "https://i.imgur.com/fUGBnFQ.png"  # 🔷 Minimalist Cyan Dot
ICON_TOOL = "https://i.imgur.com/4axLLtM.png"       # 🟠 Minimalist Orange Dot

DEFAULT_CLIENT_ID_ANTIGRAVITY = "1552496441656873172"
DEFAULT_CLIENT_ID_GEMINI = "1552488482918899722"
DEFAULT_APP_NAME = "Antigravity"
DEFAULT_ICON_THEME = "antigravity"

KNOWN_DEFAULT_CLIENT_IDS = {
    DEFAULT_CLIENT_ID_ANTIGRAVITY,
    DEFAULT_CLIENT_ID_GEMINI,
    "1510513707073929367"
}

def load_user_config():
    target_files = [USER_CONFIG_FILE, DEFAULT_CONFIG_FILE]
    for cfg in target_files:
        if os.path.exists(cfg):
            try:
                with open(cfg, "r") as f:
                    data = json.load(f)
                    icon_val = str(data.get("icon", DEFAULT_ICON_THEME)).strip().lower()
                    if icon_val not in ("antigravity", "gemini", "claude", "auto"):
                        icon_val = DEFAULT_ICON_THEME

                    configured_client_id = data.get("client_id")
                    if not configured_client_id or configured_client_id in KNOWN_DEFAULT_CLIENT_IDS:
                        active_client_id = DEFAULT_CLIENT_ID_ANTIGRAVITY if icon_val in ("antigravity", "auto", "claude") else DEFAULT_CLIENT_ID_GEMINI
                    else:
                        active_client_id = configured_client_id

                    return (
                        active_client_id,
                        data.get("app_name", DEFAULT_APP_NAME),
                        icon_val
                    )
            except Exception:
                pass
    return DEFAULT_CLIENT_ID_ANTIGRAVITY, DEFAULT_APP_NAME, DEFAULT_ICON_THEME

if sys.platform == "win32":
    try:
        import _winapi
    except ImportError:
        _winapi = None
else:
    _winapi = None

class WindowsPipeSocket:
    """Wrapper around Windows Named Pipe to emulate socket sendall/recv/close."""
    def __init__(self, pipe_path):
        self.pipe_path = pipe_path
        self.handle = None
        self.fp = None
        if _winapi:
            self.handle = _winapi.CreateFile(
                pipe_path,
                _winapi.GENERIC_READ | _winapi.GENERIC_WRITE,
                0,
                _winapi.NULL,
                _winapi.OPEN_EXISTING,
                0,
                _winapi.NULL
            )
        else:
            self.fp = open(pipe_path, "r+b", buffering=0)

    def sendall(self, data):
        if self.handle:
            _winapi.WriteFile(self.handle, data)
        elif self.fp:
            self.fp.write(data)
            self.fp.flush()

    def recv(self, length):
        if self.handle:
            buf = bytearray()
            while len(buf) < length:
                chunk, _ = _winapi.ReadFile(self.handle, length - len(buf))
                if not chunk:
                    break
                buf.extend(chunk)
            return bytes(buf)
        elif self.fp:
            return self.fp.read(length)
        return b""

    def close(self):
        if self.handle:
            try:
                _winapi.CloseHandle(self.handle)
            except Exception:
                pass
            self.handle = None
        if self.fp:
            try:
                self.fp.close()
            except Exception:
                pass
            self.fp = None

def find_discord_socket():
    if sys.platform == "win32":
        for i in range(10):
            pipe_path = rf"\\.\pipe\discord-ipc-{i}"
            if os.path.exists(pipe_path):
                return pipe_path
        return None

    uid = os.getuid() if hasattr(os, "getuid") else 1000
    candidates = [
        f"/run/user/{uid}/app/com.discordapp.Discord/discord-ipc-0",
        f"/run/user/{uid}/discord-ipc-0",
        f"/run/user/{uid}/.flatpak/com.discordapp.Discord/xdg-run/discord-ipc-0",
        "/tmp/discord-ipc-0",
    ]
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{uid}")
    if os.path.isdir(runtime_dir):
        for f in os.listdir(runtime_dir):
            if f.startswith("discord-ipc-"):
                candidates.append(os.path.join(runtime_dir, f))

    for p in candidates:
        if os.path.exists(p):
            std_sock = f"/run/user/{uid}/discord-ipc-0"
            if not os.path.exists(std_sock) and p != std_sock:
                try:
                    os.symlink(p, std_sock)
                except Exception:
                    pass
            return p
    return None

def format_time_deep(seconds):
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds}s deep"
    mins = seconds // 60
    if mins < 60:
        return f"{mins}m deep"
    hours = mins // 60
    rem_mins = mins % 60
    if rem_mins > 0:
        return f"{hours}h {rem_mins}m deep"
    return f"{hours}h deep"

class DiscordRPC:
    def __init__(self, client_id):
        self.client_id = client_id
        self.sock = None
        self.connected = False

    def connect(self):
        sock_path = find_discord_socket()
        if not sock_path:
            self.connected = False
            return False
        try:
            if sys.platform == "win32":
                self.sock = WindowsPipeSocket(sock_path)
            else:
                self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.sock.settimeout(2.0)
                self.sock.connect(sock_path)

            payload = json.dumps({"v": 1, "client_id": self.client_id}).encode("utf-8")
            self.sock.sendall(struct.pack("<II", 0, len(payload)) + payload)
            header = self.sock.recv(8)
            if len(header) < 8:
                self.close()
                return False
            op, length = struct.unpack("<II", header)
            self.sock.recv(length)
            self.connected = True
            return True
        except Exception:
            self.close()
            return False

    def close(self):
        self.connected = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def set_activity(self, app_name, details, state, start_timestamp, status="idle", status_text=None, icon_theme="antigravity", large_text=None):
        if not self.connected:
            if not self.connect():
                return False
        try:
            if status == "reading":
                small_img = ICON_READING
                small_txt = status_text or "Reading files"
            elif status == "editing":
                small_img = ICON_EDITING
                small_txt = status_text or "Editing code"
            elif status == "executing":
                small_img = ICON_EXECUTING
                small_txt = status_text or "Executing command"
            elif status == "searching":
                small_img = ICON_SEARCHING
                small_txt = status_text or "Searching"
            elif status == "working":
                small_img = ICON_WORKING
                small_txt = status_text or "Thinking / Generating response"
            elif status == "tool":
                small_img = ICON_TOOL
                small_txt = status_text or "Running tool"
            else:
                small_img = ICON_IDLE
                small_txt = status_text or "Ready (Waiting for prompt)"

            large_img = LOGO_ANTIGRAVITY if icon_theme == "antigravity" else (LOGO_CLAUDE if icon_theme == "claude" else (LOGO_GEMINI if icon_theme == "gemini" else LOGO_ANTIGRAVITY))
            large_txt = (large_text or app_name)[:128]

            activity = {
                "name": app_name,
                "details": (details or "Antigravity CLI")[:128],
                "state": (state or "Active")[:128],
                "assets": {
                    "large_image": large_img,
                    "large_text": large_txt,
                    "small_image": small_img,
                    "small_text": small_txt[:128]
                },
                "instance": False
            }
            if start_timestamp:
                activity["timestamps"] = {"start": int(start_timestamp)}

            payload = json.dumps({
                "cmd": "SET_ACTIVITY",
                "args": {
                    "pid": os.getpid(),
                    "activity": activity
                },
                "nonce": str(uuid.uuid4())
            }).encode("utf-8")

            self.sock.sendall(struct.pack("<II", 1, len(payload)) + payload)
            header = self.sock.recv(8)
            if len(header) < 8:
                self.close()
                return False
            op, length = struct.unpack("<II", header)
            self.sock.recv(length)
            return True
        except Exception:
            self.close()
            return False

    def clear_activity(self):
        if not self.connected:
            return
        try:
            payload = json.dumps({
                "cmd": "SET_ACTIVITY",
                "args": {
                    "pid": os.getpid(),
                    "activity": None
                },
                "nonce": str(uuid.uuid4())
            }).encode("utf-8")
            self.sock.sendall(struct.pack("<II", 1, len(payload)) + payload)
        except Exception:
            pass
        finally:
            self.close()

def is_pid_alive(pid):
    try:
        pid = int(pid)
        if sys.platform == "win32":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x1000, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        else:
            if os.path.exists(f"/proc/{pid}"):
                return True
            os.kill(pid, 0)
            return True
    except Exception:
        return False

def get_active_window_pid():
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return None
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            return pid.value
        except Exception:
            return None

    display = os.environ.get("DISPLAY", ":0")
    env = dict(os.environ, DISPLAY=display)
    if "XAUTHORITY" not in env:
        env["XAUTHORITY"] = os.path.expanduser("~/.Xauthority")
    try:
        out = subprocess.check_output(["xprop", "-root", "_NET_ACTIVE_WINDOW"],
                                      env=env, stderr=subprocess.DEVNULL).decode("utf-8")
        m = re.search(r"0x[0-9a-fA-F]+", out)
        if not m or m.group(0) == "0x0":
            return None
        win_id = m.group(0)
        out_pid = subprocess.check_output(["xprop", "-id", win_id, "_NET_WM_PID"],
                                          env=env, stderr=subprocess.DEVNULL).decode("utf-8")
        m_pid = re.search(r"=\s*(\d+)", out_pid)
        if m_pid:
            return int(m_pid.group(1))
    except Exception:
        pass
    return None

def get_descendants(pid):
    if sys.platform == "win32":
        descendants = []
        try:
            import ctypes
            from ctypes import wintypes
            class PROCESSENTRY32(ctypes.Structure):
                _fields_ = [
                    ("dwSize", wintypes.DWORD),
                    ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", ctypes.c_long),
                    ("dwFlags", wintypes.DWORD),
                    ("szExeFile", ctypes.c_char * 260)
                ]
            kernel32 = ctypes.windll.kernel32
            hSnapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
            if hSnapshot != -1:
                pe = PROCESSENTRY32()
                pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
                success = kernel32.Process32First(hSnapshot, ctypes.byref(pe))
                parent_map = {}
                while success:
                    parent_map.setdefault(pe.th32ParentProcessID, []).append(pe.th32ProcessID)
                    success = kernel32.Process32Next(hSnapshot, ctypes.byref(pe))
                kernel32.CloseHandle(hSnapshot)
                queue = [pid]
                while queue:
                    curr = queue.pop(0)
                    for child in parent_map.get(curr, []):
                        descendants.append(child)
                        queue.append(child)
        except Exception:
            pass
        return descendants

    descendants = []
    try:
        children_file = f"/proc/{pid}/task/{pid}/children"
        if os.path.exists(children_file):
            with open(children_file) as f:
                children = [int(x) for x in f.read().split()]
        else:
            children = []
            for entry in os.listdir("/proc"):
                if entry.isdigit():
                    try:
                        with open(f"/proc/{entry}/stat") as sf:
                            parts = sf.read().split()
                            if int(parts[3]) == pid:
                                children.append(int(entry))
                    except Exception:
                        pass
        for c in children:
            descendants.append(c)
            descendants.extend(get_descendants(c))
    except Exception:
        pass
    return descendants

def is_foreground_process(pid):
    if sys.platform == "win32":
        return True
    try:
        with open(f"/proc/{pid}/stat") as f:
            parts = f.read().split()
            return parts[4] == parts[7]
    except Exception:
        return False

def get_all_running_agy():
    if sys.platform == "win32":
        results = {}
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as sf:
                    data = json.load(sf)
                    for spid, sess in data.get("sessions", {}).items():
                        try:
                            ipid = int(spid)
                            if is_pid_alive(ipid):
                                results[ipid] = {
                                    "pid": ipid,
                                    "cwd": "",
                                    "project": sess.get("project", "Antigravity CLI"),
                                    "is_foreground": True
                                }
                        except Exception:
                            pass
            except Exception:
                pass
        return results

    uid = os.getuid() if hasattr(os, "getuid") else 1000
    results = {}
    for entry in os.listdir("/proc"):
        if entry.isdigit():
            try:
                pid = int(entry)
                stat_path = f"/proc/{pid}/stat"
                st = os.stat(stat_path)
                if st.st_uid != uid:
                    continue
                cmdline_path = f"/proc/{pid}/cmdline"
                with open(cmdline_path, "rb") as f:
                    cmd = f.read().replace(b"\x00", b" ").decode("utf-8", errors="ignore")
                    parts = cmd.strip().split()
                    if parts and "agy" in os.path.basename(parts[0]):
                        cwd = os.readlink(f"/proc/{pid}/cwd")
                        project = os.path.basename(os.path.normpath(cwd)) or "root"
                        results[pid] = {
                            "pid": pid,
                            "cwd": cwd,
                            "project": project,
                            "is_foreground": is_foreground_process(pid)
                        }
            except Exception:
                continue
    return results

def run_daemon():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    pid = os.getpid()
    with open(PID_FILE, "w") as f:
        f.write(str(pid))

    client_id, app_name, icon_theme = load_user_config()
    rpc = DiscordRPC(client_id)

    def cleanup(signum=None, frame=None):
        rpc.clear_activity()
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, cleanup)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, cleanup)

    last_active_pid = None
    last_sent_activity = None
    default_session_start = int(time.time())
    standby_start_time = None
    was_active = False

    while True:
        try:
            curr_client_id, curr_app_name, curr_icon_theme = load_user_config()
            if curr_client_id != rpc.client_id:
                rpc.clear_activity()
                rpc = DiscordRPC(curr_client_id)
            app_name = curr_app_name
            icon_theme = curr_icon_theme

            all_agy = get_all_running_agy()

            # STANDBY MODE: When all agy processes close
            if not all_agy:
                if was_active or rpc.connected:
                    rpc.clear_activity()
                    last_sent_activity = None
                    was_active = False

                if standby_start_time is None:
                    standby_start_time = time.time()
                elif time.time() - standby_start_time > 900:  # 15 min standby
                    cleanup()

                time.sleep(1.5)
                continue

            # ACTIVE MODE: agy process detected!
            was_active = True
            standby_start_time = None

            # Read sessions state and cumulative stats
            sessions = {}
            cumulative_stats = {}
            session_start_ts = default_session_start
            if os.path.exists(STATE_FILE):
                try:
                    with open(STATE_FILE, "r") as sf:
                        state_json = json.load(sf)
                        sessions = state_json.get("sessions", {})
                        cumulative_stats = state_json.get("cumulative_stats", {})
                        session_start_ts = state_json.get("session_start_timestamp", default_session_start)
                except Exception:
                    sessions = {}

            # Detect focused agy process, prioritizing an active working agy if focused is idle
            active_win_pid = get_active_window_pid()
            focused_agy = None
            if active_win_pid:
                descendants = get_descendants(active_win_pid)
                for d in descendants:
                    if d in all_agy:
                        focused_agy = all_agy[d]
                        break

            # Find any background agy instance that is actively working (status != idle)
            active_working_agy = None
            for pid, a in all_agy.items():
                s = sessions.get(str(pid), {})
                if s.get("status") and s.get("status") != "idle":
                    active_working_agy = a
                    break

            if focused_agy:
                focused_sess = sessions.get(str(focused_agy["pid"]), {})
                if focused_sess.get("status") and focused_sess.get("status") != "idle":
                    target_agy = focused_agy
                elif active_working_agy:
                    target_agy = active_working_agy
                else:
                    target_agy = focused_agy
                last_active_pid = target_agy["pid"]
            elif active_working_agy:
                target_agy = active_working_agy
                last_active_pid = target_agy["pid"]
            elif last_active_pid and last_active_pid in all_agy:
                target_agy = all_agy[last_active_pid]
            else:
                foreground_ones = [a for a in all_agy.values() if a["is_foreground"]]
                target_agy = foreground_ones[0] if foreground_ones else list(all_agy.values())[0]
                last_active_pid = target_agy["pid"]

            # Formulate activity params for selected agy
            target_pid_str = str(target_agy["pid"])
            sess = sessions.get(target_pid_str, {})
            status = sess.get("status", "idle")
            status_text = sess.get("status_text", None)
            current_action = sess.get("state") or status_text

            # 1. Project status calculation across all running agy instances
            projects_status = {}
            for pid, agy_info in all_agy.items():
                proj = agy_info.get("project")
                s = sessions.get(str(pid), {})
                if s.get("project"):
                    proj = s.get("project")
                if not proj or proj in ("Workspace", "root"):
                    proj = target_agy.get("project", "Antigravity CLI")

                st = s.get("status", "idle")
                if proj not in projects_status:
                    projects_status[proj] = []
                projects_status[proj].append(st)

            all_unique_projects = list(projects_status.keys())
            working_projects = [
                p for p, statuses in projects_status.items()
                if any(s != "idle" for s in statuses)
            ]

            num_total = len(all_unique_projects)
            num_working = len(working_projects)

            if num_working == 0:
                # All projects are idle
                status = "idle"
                if num_total > 1:
                    details = f"{num_total} projects active"
                elif num_total == 1:
                    details = "1 project active"
                else:
                    details = "Antigravity CLI active"
                large_text = f"Projects ({num_total}): {', '.join(all_unique_projects)}" if num_total > 1 else app_name
                small_status_text = "Ready (Waiting for prompt)"
            elif num_working == 1:
                # Exactly 1 project is being worked on
                action_suffix = f" · {current_action}" if current_action and current_action not in ("Idle - Ready", "Ready") else ""
                details = f"Working on 1 project{action_suffix}"
                large_text = f"Projects ({num_total}): {', '.join(all_unique_projects)}" if num_total > 1 else app_name
                small_status_text = current_action or status_text or "Agent working..."
            else:
                # 2 or more projects actively being worked on simultaneously
                action_suffix = f" · {current_action}" if current_action and current_action not in ("Idle - Ready", "Ready") else ""
                details = f"Working on {num_working} projects{action_suffix}"
                large_text = f"Projects ({num_total}): {', '.join(all_unique_projects)}" if num_total > 1 else app_name
                small_status_text = current_action or status_text or f"Working on {num_working} projects"

            # 2. Activity metrics counters (edits, cmds, searches, reads, thinks, time deep)
            total_edits = cumulative_stats.get("edits", 0)
            total_cmds = cumulative_stats.get("cmds", 0)
            total_searches = cumulative_stats.get("searches", 0)
            total_reads = cumulative_stats.get("reads", 0)
            total_thinks = cumulative_stats.get("thinks", 0)

            active_edits = sum(s.get("stats", {}).get("edits", 0) for s in sessions.values())
            active_cmds = sum(s.get("stats", {}).get("cmds", 0) for s in sessions.values())
            active_searches = sum(s.get("stats", {}).get("searches", 0) for s in sessions.values())
            active_reads = sum(s.get("stats", {}).get("reads", 0) for s in sessions.values())
            active_thinks = sum(s.get("stats", {}).get("thinks", 0) for s in sessions.values())

            total_edits = max(total_edits, active_edits)
            total_cmds = max(total_cmds, active_cmds)
            total_searches = max(total_searches, active_searches)
            total_reads = max(total_reads, active_reads)
            total_thinks = max(total_thinks, active_thinks)

            elapsed_seconds = max(0, int(time.time() - session_start_ts))

            state_parts = [
                f"{total_edits} edit" if total_edits == 1 else f"{total_edits} edits",
                f"{total_cmds} cmd" if total_cmds == 1 else f"{total_cmds} cmds",
                f"{total_searches} search" if total_searches == 1 else f"{total_searches} searches",
                f"{total_reads} read" if total_reads == 1 else f"{total_reads} reads",
                f"{total_thinks} think" if total_thinks == 1 else f"{total_thinks} thinks",
                format_time_deep(elapsed_seconds)
            ]
            state = " · ".join(state_parts)
            if len(state) > 128:
                state = state[:125] + "..."

            start_ts = sess.get("start_timestamp", session_start_ts)

            # Resolve effective icon_theme based on detected model (for "auto" mode)
            effective_icon_theme = icon_theme
            if icon_theme == "auto":
                detected_model = sess.get("model", "").lower()
                if "claude" in detected_model:
                    effective_icon_theme = "claude"
                elif "gemini" in detected_model:
                    effective_icon_theme = "gemini"
                else:
                    effective_icon_theme = "antigravity"

            current_key = (app_name, details, state, status, small_status_text, effective_icon_theme, large_text, rpc.connected)
            if current_key != last_sent_activity or not rpc.connected:
                success = rpc.set_activity(
                    app_name=app_name,
                    details=details,
                    state=state,
                    start_timestamp=start_ts,
                    status=status,
                    status_text=small_status_text,
                    icon_theme=effective_icon_theme,
                    large_text=large_text
                )
                if success:
                    last_sent_activity = current_key

            time.sleep(0.8)

        except Exception:
            time.sleep(1.5)

    cleanup()

if __name__ == "__main__":
    run_daemon()
